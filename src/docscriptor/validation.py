"""Document validation helpers for authoring-time checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Iterable, Literal, Sequence, TYPE_CHECKING

from docscriptor.compatibility import (
    OUTPUT_FORMATS,
    OutputFormat,
    format_output_formats,
    normalize_output_formats,
)
from docscriptor.components.base import Block
from docscriptor.components.blocks import (
    Box,
    BulletList,
    CodeBlock,
    ColumnSpan,
    Divider,
    Equation,
    MultiColumn,
    NumberedList,
    PageBreak,
    Paragraph,
    Part,
    Section,
    VerticalSpace,
)
from docscriptor.components.generated import (
    CommentsPage,
    FigureList,
    FootnotesPage,
    ReferencesPage,
    TableList,
    TableOfContents,
)
from docscriptor.components.inline import (
    BlockReference,
    Citation,
    Comment,
    Footnote,
    Hyperlink,
    Text,
)
from docscriptor.components.media import Figure, SubFigure, SubFigureGroup, Table
from docscriptor.components.positioning import ImageBox, Shape, TextBox
from docscriptor.components.references import CitationSource
from docscriptor.core import DocscriptorError

if TYPE_CHECKING:
    from docscriptor.document import Document
    from docscriptor.layout.indexing import RenderIndex


ValidationSeverity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One authoring issue found in a document tree."""

    severity: ValidationSeverity
    code: str
    message: str
    path: str = "document"
    formats: tuple[OutputFormat, ...] = OUTPUT_FORMATS

    def applies_to(self, formats: Iterable[str] | None = None) -> bool:
        requested_formats = normalize_output_formats(formats)
        return bool(set(self.formats) & set(requested_formats))

    def __str__(self) -> str:
        return (
            f"{self.severity.upper()} {self.code} "
            f"[{format_output_formats(self.formats)}] at {self.path}: {self.message}"
        )


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validation issues plus table-style display helpers."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    def errors_for(
        self,
        formats: Iterable[str] | None = None,
    ) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.errors
            if issue.applies_to(formats)
        )

    def warnings_for(
        self,
        formats: Iterable[str] | None = None,
    ) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.warnings
            if issue.applies_to(formats)
        )

    def issues_for(
        self,
        formats: Iterable[str] | None = None,
    ) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.applies_to(formats))

    def ok_for(self, formats: Iterable[str] | None = None) -> bool:
        return not self.errors_for(formats)

    def for_formats(self, formats: Iterable[str] | None = None) -> ValidationResult:
        return ValidationResult(self.issues_for(formats))

    def format_table(self, *, formats: Iterable[str] | None = None) -> str:
        issues = self.issues_for(formats)
        errors = tuple(issue for issue in issues if issue.severity == "error")
        warnings = tuple(issue for issue in issues if issue.severity == "warning")
        scope = format_output_formats(normalize_output_formats(formats))
        status = "ok" if not errors else "failed"
        heading = (
            f"Docscriptor validation {status} for {scope}: "
            f"{len(errors)} error(s), {len(warnings)} warning(s)"
        )
        if not issues:
            return heading

        rows = [
            (
                issue.severity.upper(),
                format_output_formats(issue.formats),
                issue.code,
                issue.path,
                issue.message,
            )
            for issue in issues
        ]
        return "\n".join([heading, _format_issue_table(rows)])

    def __str__(self) -> str:
        return self.format_table()


class DocumentValidationError(DocscriptorError):
    """Raised when document validation blocks rendering."""

    result: ValidationResult

    def __init__(
        self,
        result: ValidationResult | Sequence[ValidationIssue],
        *,
        formats: Iterable[str] | None = None,
    ) -> None:
        self.result = (
            result
            if isinstance(result, ValidationResult)
            else ValidationResult(tuple(result))
        )
        self.formats = normalize_output_formats(formats)
        super().__init__(self.result.format_table(formats=self.formats))

    @property
    def issues(self) -> tuple[ValidationIssue, ...]:
        return self.result.issues_for(self.formats)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return self.result.errors_for(self.formats)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return self.result.warnings_for(self.formats)


def validate_document(
    document: Document,
    *,
    raise_on_error: bool = False,
    formats: Iterable[str] | None = None,
) -> ValidationResult:
    """Validate a document tree and return a structured result object."""

    result = ValidationResult(tuple(_ValidationContext(document).validate()))
    if raise_on_error and not result.ok_for(formats):
        raise DocumentValidationError(result, formats=formats)
    return result


class _ValidationContext:
    def __init__(self, document: Document) -> None:
        self.document = document
        self.issues: list[ValidationIssue] = []
        self.block_paths: dict[int, str] = {}
        self.referenceable_paths: dict[int, str] = {}
        self.references: list[tuple[BlockReference, str]] = []
        self.citations: list[tuple[Citation, str]] = []
        self.generated_pages: list[tuple[object, str]] = []

    def validate(self) -> list[ValidationIssue]:
        if not str(self.document.title).strip():
            self._add(
                "error",
                "blank-document-title",
                "Document title must not be empty.",
                "document.title",
            )

        self._collect_blocks(self.document.body.children, "document.body", parent_level=None)
        for index, item in enumerate(self.document.settings.page_items):
            self._collect_positioned_item(
                item,
                f"document.settings.page_items[{index}]",
            )

        self._validate_citations()
        render_index = self._build_render_index_if_possible()
        self._validate_references(render_index)
        if render_index is not None:
            self._validate_generated_pages(render_index)
        return self.issues

    def _add(
        self,
        severity: ValidationSeverity,
        code: str,
        message: str,
        path: str,
        *,
        formats: Iterable[str] | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                severity=severity,
                code=code,
                message=message,
                path=path,
                formats=normalize_output_formats(formats),
            )
        )

    def _collect_blocks(
        self,
        blocks: Sequence[Block],
        path: str,
        *,
        parent_level: int | None,
    ) -> None:
        for index, block in enumerate(blocks):
            self._collect_block(
                block,
                f"{path}.children[{index}]",
                parent_level=parent_level,
            )

    def _collect_block(
        self,
        block: Block,
        path: str,
        *,
        parent_level: int | None,
    ) -> None:
        self._register_block(block, path)

        if isinstance(block, Paragraph):
            self._register_referenceable(block, path)
            self._scan_inlines(block.content, f"{path}.content")
            return

        if isinstance(block, (BulletList, NumberedList)):
            if len(block.item_children) != len(block.items):
                self._add(
                    "error",
                    "list-children-mismatch",
                    "List item_children must match the number of list items.",
                    path,
                )
            for item_index, item in enumerate(block.items):
                item_path = f"{path}.items[{item_index}]"
                self._register_referenceable(item, item_path)
                self._scan_inlines(item.content, f"{item_path}.content")
                child_lists = (
                    block.item_children[item_index]
                    if item_index < len(block.item_children)
                    else []
                )
                self._collect_blocks(
                    child_lists,
                    item_path,
                    parent_level=parent_level,
                )
            return

        if isinstance(block, (CodeBlock, Equation, Box)):
            self._register_referenceable(block, path)
            if isinstance(block, Box):
                if block.title is not None:
                    self._scan_inlines(block.title, f"{path}.title")
                self._collect_blocks(
                    block.children,
                    path,
                    parent_level=parent_level,
                )
            return

        if isinstance(block, (ColumnSpan, MultiColumn)):
            self._collect_blocks(
                block.children,
                path,
                parent_level=parent_level,
            )
            return

        if isinstance(block, Part):
            self._register_referenceable(block, path)
            self._validate_title(block.title, f"{path}.title", "Part title must not be empty.")
            self._scan_inlines(block.title, f"{path}.title")
            self._collect_blocks(
                block.children,
                path,
                parent_level=block.level,
            )
            return

        if isinstance(block, Section):
            self._register_referenceable(block, path)
            self._validate_title(block.title, f"{path}.title", "Section title must not be empty.")
            self._scan_inlines(block.title, f"{path}.title")
            self._validate_heading_level(block, path, parent_level)
            self._collect_blocks(
                block.children,
                path,
                parent_level=block.level,
            )
            return

        if isinstance(
            block,
            (
                TableList,
                FigureList,
                ReferencesPage,
                CommentsPage,
                FootnotesPage,
                TableOfContents,
            ),
        ):
            self.generated_pages.append((block, path))
            if block.title is not None:
                self._scan_inlines(block.title, f"{path}.title")
            return

        if isinstance(block, Table):
            self._register_referenceable(block, path)
            self._validate_table(block, path)
            return

        if isinstance(block, Figure):
            self._register_referenceable(block, path)
            self._validate_figure(block, path)
            return

        if isinstance(block, SubFigureGroup):
            self._register_referenceable(block, path)
            for subfigure_index, subfigure in enumerate(block.subfigures):
                subfigure_path = f"{path}.subfigures[{subfigure_index}]"
                self._register_referenceable(subfigure, subfigure_path)
                self._validate_figure(subfigure, subfigure_path)
            if block.caption is not None:
                self._scan_inlines(block.caption.content, f"{path}.caption")
            return

        if isinstance(block, (TextBox, Shape, ImageBox)):
            self._collect_positioned_item(block, path)
            return

        if isinstance(block, (Divider, PageBreak, VerticalSpace)):
            return

        self._add(
            "error",
            "unsupported-block",
            f"Unsupported block object: {type(block)!r}.",
            path,
        )

    def _register_block(self, block: Block, path: str) -> None:
        block_id = id(block)
        existing_path = self.block_paths.get(block_id)
        if existing_path is not None:
            self._add(
                "error",
                "duplicate-block-instance",
                f"The same {type(block).__name__} object is inserted more than once "
                f"({existing_path} and {path}). Create a separate object for each location.",
                path,
            )
            return
        self.block_paths[block_id] = path

    def _register_referenceable(self, target: object, path: str) -> None:
        target_id = id(target)
        existing_path = self.referenceable_paths.get(target_id)
        if existing_path is not None and existing_path != path:
            self._add(
                "error",
                "duplicate-reference-target",
                f"The same {type(target).__name__} object is present at both "
                f"{existing_path} and {path}. References need a single document location.",
                path,
            )
            return
        self.referenceable_paths[target_id] = path

    def _scan_inlines(self, fragments: Sequence[Text], path: str) -> None:
        for index, fragment in enumerate(fragments):
            fragment_path = f"{path}[{index}]"
            if isinstance(fragment, BlockReference):
                self.references.append((fragment, fragment_path))
                if fragment.label is not None:
                    self._scan_inlines(fragment.label, f"{fragment_path}.label")
                continue
            if isinstance(fragment, Citation):
                self.citations.append((fragment, fragment_path))
                continue
            if isinstance(fragment, Hyperlink):
                self._scan_inlines(fragment.label, f"{fragment_path}.label")
                continue
            if isinstance(fragment, Comment):
                self._scan_inlines(fragment.comment, f"{fragment_path}.comment")
                continue
            if isinstance(fragment, Footnote):
                self._scan_inlines(fragment.note, f"{fragment_path}.note")

    def _validate_title(self, title: Sequence[Text], path: str, message: str) -> None:
        if not _plain_text(title).strip():
            self._add("error", "blank-heading-title", message, path)

    def _validate_heading_level(
        self,
        section: Section,
        path: str,
        parent_level: int | None,
    ) -> None:
        if parent_level is None:
            if section.numbered and section.level > 1:
                self._add(
                    "warning",
                    "top-level-heading-below-chapter",
                    "A numbered top-level section starts below chapter level. "
                    "Wrap it in a Chapter(...) or set numbered=False for front matter.",
                    path,
                )
            return

        if section.level > parent_level + 1:
            self._add(
                "warning",
                "skipped-heading-level",
                f"Heading level jumps from {parent_level} to {section.level}. "
                "Consider inserting the missing intermediate section level.",
                path,
            )

    def _validate_table(self, table: Table, path: str) -> None:
        layout = table.layout()
        if layout.column_count < 1:
            self._add(
                "error",
                "empty-table",
                "Table must contain at least one rendered column.",
                path,
            )
        if table.column_widths is not None:
            for index, width in enumerate(table.column_widths):
                if width <= 0:
                    self._add(
                        "error",
                        "invalid-column-width",
                        "Table column widths must be greater than zero.",
                        f"{path}.column_widths[{index}]",
                    )

        for row_index, row in enumerate(table.header_rows):
            for cell_index, cell in enumerate(row):
                self._scan_inlines(
                    cell.content.content,
                    f"{path}.header_rows[{row_index}][{cell_index}].content",
                )
        for row_index, row in enumerate(table.rows):
            for cell_index, cell in enumerate(row):
                self._scan_inlines(
                    cell.content.content,
                    f"{path}.rows[{row_index}][{cell_index}].content",
                )
        if table.caption is not None:
            self._scan_inlines(table.caption.content, f"{path}.caption")

    def _validate_figure(self, figure: Figure | SubFigure, path: str) -> None:
        for field_name in ("width", "height"):
            value = getattr(figure, field_name)
            if value is not None and value <= 0:
                self._add(
                    "error",
                    "invalid-figure-size",
                    f"{type(figure).__name__}.{field_name} must be greater than "
                    "zero when supplied.",
                    f"{path}.{field_name}",
                )
        if not isinstance(figure.format, str) or not figure.format.strip():
            self._add(
                "error",
                "invalid-image-format",
                f"{type(figure).__name__}.format must not be empty.",
                f"{path}.format",
            )
        if figure.dpi is not None and figure.dpi <= 0:
            self._add(
                "error",
                "invalid-image-dpi",
                f"{type(figure).__name__}.dpi must be greater than zero.",
                f"{path}.dpi",
            )
        self._validate_image_source(figure.image_source, path)
        if figure.caption is not None:
            self._scan_inlines(figure.caption.content, f"{path}.caption")

    def _validate_image_source(self, source: object, path: str) -> None:
        if isinstance(source, Path):
            if not source.exists():
                self._add(
                    "error",
                    "missing-image-file",
                    f"Image file does not exist: {source}.",
                    f"{path}.image_source",
                )
                return
            if not source.is_file():
                self._add(
                    "error",
                    "invalid-image-file",
                    f"Image source is not a file: {source}.",
                    f"{path}.image_source",
                )
            return

        if not hasattr(source, "savefig"):
            self._add(
                "error",
                "unsupported-image-source",
                "Image source must be a filesystem path or an object with savefig(...).",
                f"{path}.image_source",
            )

    def _collect_positioned_item(self, item: object, path: str) -> None:
        if isinstance(item, TextBox):
            self._scan_inlines(item.content, f"{path}.content")
            return
        if isinstance(item, ImageBox):
            if not isinstance(item.format, str) or not item.format.strip():
                self._add(
                    "error",
                    "invalid-image-format",
                    "ImageBox.format must not be empty.",
                    f"{path}.format",
                )
            if item.dpi is not None and item.dpi <= 0:
                self._add(
                    "error",
                    "invalid-image-dpi",
                    "ImageBox.dpi must be greater than zero.",
                    f"{path}.dpi",
                )
            self._validate_image_source(item.image_source, path)
            return
        if isinstance(item, Shape):
            return

        self._add(
            "error",
            "unsupported-positioned-item",
            f"Unsupported positioned item: {type(item)!r}.",
            path,
        )

    def _validate_citations(self) -> None:
        for citation, path in self.citations:
            target = citation.target
            if isinstance(target, CitationSource):
                continue
            if target not in self.document.citations.entries:
                self._add(
                    "error",
                    "unresolved-citation",
                    f"Citation key {target!r} is not present in the document citation library.",
                    path,
                )

    def _build_render_index_if_possible(self) -> RenderIndex | None:
        if any(issue.severity == "error" for issue in self.issues):
            return None

        from docscriptor.layout.indexing import build_render_index

        try:
            return build_render_index(self.document)
        except DocscriptorError as exc:
            self._add(
                "error",
                "indexing-error",
                str(exc),
                "document",
            )
            return None

    def _validate_references(self, render_index: RenderIndex | None) -> None:
        for reference, path in self.references:
            self._validate_reference(reference, path, render_index)

    def _validate_reference(
        self,
        reference: BlockReference,
        path: str,
        render_index: RenderIndex | None,
    ) -> None:
        target = reference.target
        target_path = self.referenceable_paths.get(id(target))
        if target_path is None:
            self._add(
                "error",
                "missing-reference-target",
                f"Referenced {type(target).__name__} is not included in this document body.",
                path,
            )
            return

        has_custom_label = reference.label is not None
        if isinstance(target, Table):
            if target.caption is None:
                self._add(
                    "error",
                    "uncaptioned-reference-target",
                    "Table references require the target table to have a caption.",
                    path,
                )
            return

        if isinstance(target, (Figure, SubFigureGroup)):
            if target.caption is None:
                self._add(
                    "error",
                    "uncaptioned-reference-target",
                    f"{type(target).__name__} references require the target to have a caption.",
                    path,
                )
            return

        if isinstance(target, SubFigure):
            if render_index is not None and render_index.subfigure_label(target) is None:
                self._add(
                    "error",
                    "unanchored-subfigure-reference",
                    "SubFigure references require the target to belong to a "
                    "captioned SubFigureGroup.",
                    path,
                )
            return

        if isinstance(target, (Part, Section)):
            if target.numbered:
                return
            if not has_custom_label:
                self._add(
                    "error",
                    "unnumbered-heading-reference",
                    f"{type(target).__name__} references without a custom label "
                    "require numbered=True.",
                    path,
                )
                return
            if render_index is not None and render_index.heading_anchor(target) is None:
                self._add(
                    "warning",
                    "unanchored-labeled-reference",
                    "This labeled heading reference has no internal anchor. "
                    "Set toc=True or numbered=True if it should link to the heading.",
                    path,
                )
            return

        if isinstance(target, (Paragraph, Equation, CodeBlock, Box)):
            return

        self._add(
            "error",
            "unsupported-reference-target",
            f"Unsupported reference target: {type(target)!r}.",
            path,
        )

    def _validate_generated_pages(self, render_index: RenderIndex) -> None:
        for page, path in self.generated_pages:
            if isinstance(page, TableOfContents):
                if page.show_page_numbers:
                    self._add(
                        "warning",
                        "html-toc-page-numbers",
                        "HTML output does not have stable rendered page numbers, "
                        "so the TOC is link-only there.",
                        path,
                        formats=("html",),
                    )
                if not any(page.includes_level(entry.level) for entry in render_index.headings):
                    self._add(
                        "warning",
                        "empty-table-of-contents",
                        "TableOfContents has no matching headings to display.",
                        path,
                    )
                continue
            if isinstance(page, TableList) and not render_index.tables:
                self._add(
                    "warning",
                    "empty-table-list",
                    "TableList has no captioned tables to display.",
                    path,
                )
                continue
            if isinstance(page, FigureList) and not render_index.figures:
                self._add(
                    "warning",
                    "empty-figure-list",
                    "FigureList has no captioned figures to display.",
                    path,
                )
                continue
            if isinstance(page, ReferencesPage) and not render_index.citations:
                self._add(
                    "warning",
                    "empty-references-page",
                    "ReferencesPage has no cited sources to display.",
                    path,
                )
                continue
            if isinstance(page, CommentsPage) and not render_index.comments:
                self._add(
                    "warning",
                    "empty-comments-page",
                    "CommentsPage has no comments to display.",
                    path,
                )
                continue
            if isinstance(page, FootnotesPage) and not render_index.footnotes:
                self._add(
                    "warning",
                    "empty-footnotes-page",
                    "FootnotesPage has no footnotes to display.",
                    path,
                )


def _plain_text(fragments: Sequence[Text]) -> str:
    return "".join(fragment.plain_text() for fragment in fragments)


def _format_issue_table(rows: Sequence[tuple[str, str, str, str, str]]) -> str:
    headers = ("Severity", "Formats", "Code", "Path", "Message")
    max_widths = (8, 14, 30, 42, 72)
    widths = [
        min(
            max(len(headers[index]), *(len(row[index]) for row in rows)),
            max_widths[index],
        )
        for index in range(len(headers))
    ]
    border = _table_border(widths)
    lines = [
        border,
        _table_row(headers, widths),
        border,
    ]
    for row in rows:
        for wrapped_row in _wrap_row(row, widths):
            lines.append(_table_row(wrapped_row, widths))
        lines.append(border)
    return "\n".join(lines)


def _table_border(widths: Sequence[int]) -> str:
    return "+" + "+".join("-" * (width + 2) for width in widths) + "+"


def _table_row(values: Sequence[str], widths: Sequence[int]) -> str:
    cells = [
        f" {value:<{width}} "
        for value, width in zip(values, widths)
    ]
    return "|" + "|".join(cells) + "|"


def _wrap_row(values: Sequence[str], widths: Sequence[int]) -> list[tuple[str, ...]]:
    wrapped_cells = [
        wrap(value, width=width, break_long_words=True, break_on_hyphens=False)
        or [""]
        for value, width in zip(values, widths)
    ]
    row_count = max(len(cell) for cell in wrapped_cells)
    return [
        tuple(
            wrapped_cells[column][row_index]
            if row_index < len(wrapped_cells[column])
            else ""
            for column in range(len(values))
        )
        for row_index in range(row_count)
    ]


__all__ = [
    "DocumentValidationError",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "validate_document",
]
