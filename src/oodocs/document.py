"""Document root object and renderer entry points."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Sequence, TYPE_CHECKING

from oodocs.compatibility import normalize_output_format, normalize_output_formats
from oodocs.components.base import BlockInput, Body
from oodocs.components.references import CitationLibrary, CitationSource, coerce_citation_library
from oodocs.core import PathLike
from oodocs.settings import DocumentSettings

if TYPE_CHECKING:
    from oodocs.importers.notebook import NotebookImportOptions
    from oodocs.validation import ValidationResult


@dataclass(slots=True, init=False)
class Document:
    """Top-level renderable document.

    Args:
        title: Document title rendered at the top of the output.
        *children: Top-level blocks. Mutually exclusive with ``body=...``.
        body: Optional pre-built ``Body`` container.
        settings: Optional document metadata, page geometry, overlays, and
            rendering settings.
        citations: Bibliography metadata supplied as a library, a sequence of
            ``CitationSource`` objects, or BibTeX text.

    Examples:
        Build a small document and write multiple formats:

        ```python
        from oodocs import Chapter, Document, Paragraph

        doc = Document(
            "Quarterly Review",
            Chapter("Summary", Paragraph("Revenue grew 12%.")),
        )
        outputs = doc.save_all("dist", formats=("docx", "html"))
        ```

        Combine document settings, citations, and authored content:

        ```python
        from oodocs import CitationSource, Document, DocumentSettings, Paragraph, PageMargins, cite

        source = CitationSource("Reliable APIs", key="api2024", authors=("Jane Doe",))
        settings = DocumentSettings(page_margins=PageMargins.all(1.0, unit="in"))
        doc = Document(
            "Research Note",
            Paragraph("Prior work ", cite("api2024"), " motivates the design."),
            settings=settings,
            citations=[source],
        )
        ```

    Notes:
        ``Document`` owns the top-level body, settings, and citation library.
        Renderers consume this object directly; most user code should build
        blocks and settings first, then pass them into ``Document``.

    See Also:
        ``DocumentSettings`` for metadata and layout configuration,
        ``save_document_outputs`` for workflow-oriented rendering, and
        ``from_markdown`` for importing Markdown into a document.
    """

    title: str
    body: Body
    settings: DocumentSettings
    citations: CitationLibrary

    def __init__(
        self,
        title: str,
        *children: BlockInput,
        body: Body | None = None,
        settings: DocumentSettings | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
    ) -> None:
        if body is not None and children:
            raise ValueError("Pass either body=... or positional blocks, not both")

        self.title = title
        self.body = body if body is not None else Body(*children)
        self.settings = settings or DocumentSettings()
        self.citations = coerce_citation_library(citations)

    def add(self, *children: BlockInput) -> Document:
        """Append top-level blocks.

        Args:
            *children: Blocks or block-coercible values to append.

        Returns:
            This document, enabling fluent construction.

        Examples:
            ```python
            from oodocs import Chapter, Document, Paragraph

            doc = Document("Plan").add(
                Chapter("Scope", Paragraph("Ship the first milestone."))
            )
            ```
        """

        self.body.add(*children)
        return self

    def extend(self, children: Iterable[BlockInput]) -> Document:
        """Append an iterable of top-level blocks.

        Args:
            children: Blocks or block-coercible values to append.

        Returns:
            This document, enabling fluent construction.

        Examples:
            ```python
            from oodocs import Document, Paragraph

            doc = Document("Log").extend(
                [Paragraph("Started."), Paragraph("Finished.")]
            )
            ```
        """

        self.body.extend(children)
        return self

    @classmethod
    def from_markdown(
        cls,
        source: str,
        *,
        title: str | None = None,
        settings: DocumentSettings | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        numbered: bool = True,
        toc: bool | None = None,
        heading_level_shift: int = 0,
        base_dir: str | Path | None = None,
    ) -> Document:
        """Create a document from Markdown text.

        Args:
            source: Markdown source text.
            title: Optional document title. When omitted, the importer derives
                one from the first heading or a fallback.
            settings: Optional document settings.
            citations: Optional citation library, citation sources, or BibTeX.
            numbered: Whether imported headings should be numbered by default.
            toc: Whether to add a table of contents.
            heading_level_shift: Number of levels to shift imported headings.
            base_dir: Directory used to resolve relative media paths.

        Returns:
            A document built from the Markdown source.

        Examples:
            ```python
            from oodocs import Document

            doc = Document.from_markdown("# Overview\\n\\nImported content.")
            doc.save_html("overview.html")
            ```
        """

        from oodocs.importers.markdown import from_markdown

        return from_markdown(
            source,
            title=title,
            settings=settings,
            citations=citations,
            numbered=numbered,
            toc=toc,
            heading_level_shift=heading_level_shift,
            base_dir=base_dir,
        )

    @classmethod
    def from_markdown_file(
        cls,
        path: str | Path,
        *,
        title: str | None = None,
        settings: DocumentSettings | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        numbered: bool = True,
        toc: bool | None = None,
        heading_level_shift: int = 0,
    ) -> Document:
        """Create a document from a Markdown file.

        Args:
            path: Markdown file path.
            title: Optional document title override.
            settings: Optional document settings.
            citations: Optional citation library, citation sources, or BibTeX.
            numbered: Whether imported headings should be numbered by default.
            toc: Whether to add a table of contents.
            heading_level_shift: Number of levels to shift imported headings.

        Returns:
            A document built from the Markdown file.

        Examples:
            ```python
            from oodocs import Document

            doc = Document.from_markdown_file("README.md", title="Project Notes")
            ```
        """

        from oodocs.importers.markdown import from_markdown_file

        return from_markdown_file(
            path,
            title=title,
            settings=settings,
            citations=citations,
            numbered=numbered,
            toc=toc,
            heading_level_shift=heading_level_shift,
        )

    @classmethod
    def from_notebook(
        cls,
        source: object,
        *,
        title: str | None = None,
        settings: DocumentSettings | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        options: NotebookImportOptions | None = None,
        include_outputs: bool | None = None,
        include_code: bool | None = None,
        include_markdown: bool | None = None,
        include_raw: bool | None = None,
        code_language: str | None = None,
        base_dir: str | Path | None = None,
        numbered: bool = True,
        toc: bool | None = None,
        heading_level_shift: int = 0,
        import_policy: str = "lossy",
    ) -> Document:
        """Create a document from a Jupyter notebook.

        Args:
            source: Notebook path, JSON string, or parsed notebook mapping.
            title: Optional document title override.
            settings: Optional document settings.
            citations: Optional citation library, citation sources, or BibTeX.
            options: Notebook import options object.
            include_outputs: Override for output cell inclusion.
            include_code: Override for code cell inclusion.
            include_markdown: Override for Markdown cell inclusion.
            include_raw: Override for raw cell inclusion.
            code_language: Language label for imported code blocks.
            base_dir: Directory used to resolve relative media paths.
            numbered: Whether imported headings should be numbered by default.
            toc: Whether to add a table of contents.
            heading_level_shift: Number of levels to shift imported headings.
            import_policy: Policy for lossy imports and warnings.

        Returns:
            A document built from the notebook.

        Examples:
            ```python
            from oodocs import Document, NotebookImportOptions

            doc = Document.from_notebook(
                "analysis.ipynb",
                options=NotebookImportOptions(max_output_lines=20),
            )
            ```
        """

        from oodocs.importers.notebook import from_notebook

        return from_notebook(
            source,
            title=title,
            settings=settings,
            citations=citations,
            options=options,
            include_outputs=include_outputs,
            include_code=include_code,
            include_markdown=include_markdown,
            include_raw=include_raw,
            code_language=code_language,
            base_dir=base_dir,
            numbered=numbered,
            toc=toc,
            heading_level_shift=heading_level_shift,
            import_policy=import_policy,
        )

    def split_top_level_children(self) -> tuple[list[object], list[object]]:
        """Split top-level blocks into front matter and main matter.

        Front matter is defined as every top-level block that appears before the
        first numbered part or level-1 heading.

        Returns:
            A ``(front_matter, main_matter)`` tuple.

        Notes:
            Renderers use this split to separate cover/front matter from the
            numbered body when page numbering or cover-page behavior requires
            different sections.
        """

        for index, child in enumerate(self.body.children):
            level = getattr(child, "level", None)
            numbered = getattr(child, "numbered", False)
            if level in {0, 1} and numbered:
                return self.body.children[:index], self.body.children[index:]
        return list(self.body.children), []

    def validate(
        self,
        *,
        raise_on_error: bool = False,
        formats: Iterable[str] | None = None,
    ) -> ValidationResult:
        """Validate the document tree.

        Args:
            raise_on_error: Whether to raise ``DocumentValidationError`` when
                blocking errors are present.
            formats: Output formats to validate for. Defaults to all formats.

        Returns:
            A structured validation result.

        Raises:
            DocumentValidationError: If ``raise_on_error`` is true and the
                document has blocking errors for the requested formats.

        Examples:
            ```python
            result = doc.validate(formats=("pdf", "html"))
            if not result.ok:
                print(result.format_table())
            ```
        """

        from oodocs.validation import validate_document

        return validate_document(
            self,
            raise_on_error=raise_on_error,
            formats=formats,
        )

    def _ensure_valid(self, formats: Iterable[str]) -> None:
        from oodocs.validation import DocumentValidationError

        result = self.validate(formats=formats)
        if not result.ok_for(formats):
            raise DocumentValidationError(result, formats=formats)

    def save_docx(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document to DOCX.

        Args:
            path: Output ``.docx`` path.
            validate: Whether to validate the document before rendering.

        Returns:
            The written output path.

        Examples:
            ```python
            doc.save_docx("report.docx")
            ```
        """

        if validate:
            self._ensure_valid(("docx",))

        from oodocs.renderers.docx import DocxRenderer

        return DocxRenderer().render(self, path)

    def save_pdf(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document to PDF.

        Args:
            path: Output ``.pdf`` path.
            validate: Whether to validate the document before rendering.

        Returns:
            The written output path.

        Examples:
            ```python
            doc.save_pdf("report.pdf")
            ```
        """

        if validate:
            self._ensure_valid(("pdf",))

        from oodocs.renderers.pdf import PdfRenderer

        return PdfRenderer().render(self, path)

    def save_html(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document to HTML.

        Args:
            path: Output ``.html`` path.
            validate: Whether to validate the document before rendering.

        Returns:
            The written output path.

        Examples:
            ```python
            doc.save_html("report.html")
            ```
        """

        if validate:
            self._ensure_valid(("html",))

        from oodocs.renderers.html import HtmlRenderer

        return HtmlRenderer().render(self, path)

    def save(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document using the output path extension.

        Supported extensions are ``.docx``, ``.pdf``, and ``.html``. The
        format-specific methods remain available when code wants to be explicit,
        but this helper keeps first scripts small and readable.

        Args:
            path: Output path whose extension selects the renderer.
            validate: Whether to validate the document before rendering.

        Returns:
            The written output path.

        Raises:
            ValueError: If the extension is not a supported output format.

        Examples:
            ```python
            doc.save("report.pdf")
            doc.save("report.html")
            ```
        """

        output_format = normalize_output_format(Path(path).suffix)
        if output_format == "docx":
            return self.save_docx(path, validate=validate)
        if output_format == "pdf":
            return self.save_pdf(path, validate=validate)
        return self.save_html(path, validate=validate)

    def save_all(
        self,
        output_dir: PathLike,
        *,
        stem: str | None = None,
        formats: Sequence[str] = ("docx", "pdf", "html"),
        validate: bool = True,
        verbose: bool = False,
    ) -> dict[str, Path]:
        """Render the document to multiple output formats.

        Args:
            output_dir: Directory where rendered files should be written.
            stem: Base filename without extension. Defaults to a filename-safe
                version of the document title.
            formats: Iterable of output formats. Supported values are
                ``"docx"``, ``"pdf"``, and ``"html"`` with or without a
                leading dot.
            validate: Whether to validate once for all requested formats before
                rendering.
            verbose: Print slow major steps. Steps under one second are omitted,
                and at most ten progress lines are printed.

        Returns:
            A mapping from normalized format name to the written path.

        Examples:
            ```python
            outputs = doc.save_all("dist", stem="release-notes")
            print(outputs["pdf"])
            ```
        """

        directory = Path(output_dir)
        output_stem = stem or self._default_output_stem()
        normalized_formats = normalize_output_formats(formats)
        progress_lines = 0

        def report_step(label: str, start: float) -> None:
            nonlocal progress_lines
            elapsed = perf_counter() - start
            if not verbose or elapsed < 1.0 or progress_lines >= 10:
                return
            print(f"{label} ({elapsed:.1f}s)")
            progress_lines += 1

        if validate:
            start = perf_counter()
            self._ensure_valid(normalized_formats)
            report_step("Validated document", start)

        outputs: dict[str, Path] = {}
        for output_format in normalized_formats:
            start = perf_counter()
            outputs[output_format] = self.save(
                directory / f"{output_stem}.{output_format}",
                validate=False,
            )
            report_step(f"Rendered {output_format.upper()}", start)
        return outputs

    def _default_output_stem(self) -> str:
        pieces: list[str] = []
        previous_was_separator = False
        # Collapse runs of punctuation and whitespace into a single hyphen so
        # generated filenames stay short and portable.
        for character in self.title.strip().lower():
            if character.isalnum():
                pieces.append(character)
                previous_was_separator = False
            elif not previous_was_separator:
                pieces.append("-")
                previous_was_separator = True
        stem = "".join(pieces).strip("-")
        return stem or "document"
