"""Jupyter notebook import helpers for OODocs documents."""

from __future__ import annotations

import json
from base64 import b64decode
from collections.abc import Mapping, Sequence as SequenceABC
from dataclasses import dataclass
from os import PathLike as OsPathLike
from pathlib import Path
from typing import Sequence

from oodocs.components.base import Block
from oodocs.components.blocks import Chapter, CodeBlock, Section
from oodocs.components.media import Figure, ImageData
from oodocs.components.references import CitationLibrary, CitationSource
from oodocs.document import Document
from oodocs.importers.markdown import parse_markdown
from oodocs.importers.results import ImportIssue, ImportResult, resolve_import_result
from oodocs.settings import DocumentSettings


NotebookSource = str | OsPathLike[str] | Mapping[str, object]


@dataclass(frozen=True, slots=True)
class NotebookImportOptions:
    """Options controlling how notebook cells and outputs are imported.

    Attributes:
        include_outputs: Whether code cell outputs should be imported.
        include_code: Whether code cell source should be imported.
        include_markdown: Whether Markdown cells should be imported.
        include_raw: Whether raw cells should be imported as text code blocks.
        code_language: Optional language override for imported code blocks.
        exclude_tags: Notebook cell tags that should be skipped.
        max_output_lines: Optional maximum number of text output lines.
        image_caption: Optional format string used for image output captions.
        include_error_outputs: Whether error outputs should be imported.

    Examples:
        Limit noisy notebook outputs while keeping code and Markdown cells:

        ```python
        from oodocs import NotebookImportOptions, from_ipynb

        options = NotebookImportOptions(max_output_lines=25, exclude_tags=("skip-doc",))
        doc = from_ipynb("analysis.ipynb", options=options)
        ```

        Import only narrative Markdown cells:

        ```python
        options = NotebookImportOptions(include_code=False, include_outputs=False)
        doc = from_ipynb("analysis.ipynb", options=options, title="Narrative Summary")
        ```

    Notes:
        Explicit keyword arguments passed to notebook import functions override
        values from this options object. Use the object for reusable defaults
        and per-call keywords for one-off changes.

    See Also:
        ``parse_ipynb`` for editable imported blocks and ``from_ipynb`` for a
        renderable ``Document``.
    """

    include_outputs: bool = True
    include_code: bool = True
    include_markdown: bool = True
    include_raw: bool = True
    code_language: str | None = None
    exclude_tags: tuple[str, ...] = ()
    max_output_lines: int | None = None
    image_caption: str | None = None
    include_error_outputs: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize notebook import options.

        Raises:
            ValueError: If ``max_output_lines`` is less than 1.
        """

        if self.max_output_lines is not None and self.max_output_lines < 1:
            raise ValueError("NotebookImportOptions.max_output_lines must be >= 1")
        object.__setattr__(self, "exclude_tags", tuple(str(tag) for tag in self.exclude_tags))


def parse_ipynb(
    source: NotebookSource,
    *,
    options: NotebookImportOptions | None = None,
    include_outputs: bool | None = None,
    include_code: bool | None = None,
    include_markdown: bool | None = None,
    include_raw: bool | None = None,
    code_language: str | None = None,
    numbered: bool = True,
    toc: bool | None = None,
    heading_level_shift: int = 0,
    base_dir: str | OsPathLike[str] | None = None,
    diagnostics: bool = False,
    import_policy: str = "lossy",
) -> list[Block] | ImportResult:
    """Parse a Jupyter notebook into oodocs block objects.

    Markdown cells are parsed through ``parse_markdown(...)``. Code cells become
    ``CodeBlock`` objects. Textual cell outputs are imported as unlabeled text
    code blocks when ``include_outputs`` is true.

    Args:
        source: Notebook path, JSON text, or decoded notebook mapping.
        options: Base import options. Explicit keyword options override this
            object when supplied.
        include_outputs: Optional override for output import.
        include_code: Optional override for code cell source import.
        include_markdown: Optional override for Markdown cell import.
        include_raw: Optional override for raw cell import.
        code_language: Optional language override for code blocks.
        numbered: Whether imported Markdown headings should be numbered.
        toc: Whether imported Markdown headings should appear in generated
            contents pages.
        heading_level_shift: Signed offset applied to Markdown heading levels.
        base_dir: Directory used to resolve local Markdown image paths.
        diagnostics: Whether to return ``ImportResult`` with diagnostics.
        import_policy: Policy for diagnostics produced by lossy imports.

    Returns:
        Imported block objects, or an ``ImportResult`` when ``diagnostics`` is
        true.

    Raises:
        ImportPolicyError: If strict import policy rejects collected issues.
        TypeError: If ``source`` is not a supported notebook source.
        ValueError: If options or shifted headings are invalid.

    Examples:
        Parse notebook blocks and collect diagnostics:

        ```python
        from oodocs.importers.notebook import parse_ipynb
        from oodocs.importers.results import ImportResult

        result = parse_ipynb("analysis.ipynb", diagnostics=True, include_outputs=False)
        assert isinstance(result, ImportResult)
        ```
    """

    notebook = _load_notebook(source)
    resolved_options = _resolve_options(
        options,
        include_outputs=include_outputs,
        include_code=include_code,
        include_markdown=include_markdown,
        include_raw=include_raw,
        code_language=code_language,
    )
    language = resolved_options.code_language or _notebook_language(notebook) or "python"
    markdown_base_dir = Path(base_dir) if base_dir is not None else _source_base_dir(source)
    blocks: list[Block] = []
    heading_stack: list[Section] = []
    issues: list[ImportIssue] = []

    for cell_index, cell in enumerate(_notebook_cells(notebook), start=1):
        excluded_tags = set(_cell_tags(cell)) & set(resolved_options.exclude_tags)
        if excluded_tags:
            issues.append(
                ImportIssue(
                    "info",
                    "notebook-cell-excluded",
                    f"Cell skipped by tag filter: {', '.join(sorted(excluded_tags))}.",
                    source=f"cell[{cell_index}]",
                )
            )
            continue

        cell_type = str(cell.get("cell_type", "")).strip().lower()
        cell_source = _join_source(cell.get("source", ""))

        # Markdown cells may introduce nested sections, so imported blocks are
        # appended through the heading stack rather than directly to root.
        if cell_type == "markdown":
            if resolved_options.include_markdown and cell_source.strip():
                markdown_result = parse_markdown(
                    cell_source,
                    numbered=numbered,
                    toc=toc,
                    heading_level_shift=heading_level_shift,
                    base_dir=markdown_base_dir,
                    diagnostics=True,
                    import_policy=import_policy,
                    source_name=f"cell[{cell_index}]",
                )
                assert isinstance(markdown_result, ImportResult)
                issues.extend(markdown_result.issues)
                for block in markdown_result.blocks:
                    _append_notebook_block(blocks, heading_stack, block)
            continue

        if cell_type == "code":
            if resolved_options.include_code and cell_source.strip():
                _append_notebook_block(
                    blocks,
                    heading_stack,
                    CodeBlock(cell_source.rstrip("\n"), language=language),
                )
            if resolved_options.include_outputs:
                for block in _cell_output_blocks(
                    cell,
                    options=resolved_options,
                    issues=issues,
                    cell_index=cell_index,
                    numbered=numbered,
                    toc=toc,
                    heading_level_shift=heading_level_shift,
                    base_dir=markdown_base_dir,
                    import_policy=import_policy,
                ):
                    _append_notebook_block(blocks, heading_stack, block)
            continue

        if resolved_options.include_raw and cell_source.strip():
            _append_notebook_block(
                blocks,
                heading_stack,
                CodeBlock(
                    cell_source.rstrip("\n"),
                    language="text",
                    show_language=False,
                ),
            )

    return resolve_import_result(
        blocks,
        issues,
        diagnostics=diagnostics,
        import_policy=import_policy,
    )


def from_ipynb(
    source: NotebookSource,
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
    numbered: bool = True,
    toc: bool | None = None,
    heading_level_shift: int = 0,
    base_dir: str | OsPathLike[str] | None = None,
    import_policy: str = "lossy",
) -> Document:
    """Create a ``Document`` from a Jupyter notebook.

    When ``title`` is not supplied, the first imported level-1 Markdown heading
    becomes the document title. If no level-1 heading is present, notebook
    metadata is checked before falling back to ``"Notebook Document"``.

    Args:
        source: Notebook path, JSON text, or decoded notebook mapping.
        title: Optional document title.
        settings: Optional document settings.
        citations: Optional citation library, source list, or BibTeX text.
        options: Base import options. Explicit keyword options override this
            object when supplied.
        include_outputs: Optional override for output import.
        include_code: Optional override for code cell source import.
        include_markdown: Optional override for Markdown cell import.
        include_raw: Optional override for raw cell import.
        code_language: Optional language override for code blocks.
        numbered: Whether imported Markdown headings should be numbered.
        toc: Whether imported Markdown headings should appear in generated
            contents pages.
        heading_level_shift: Signed offset applied to Markdown heading levels.
        base_dir: Directory used to resolve local Markdown image paths.
        import_policy: Policy for diagnostics produced by lossy imports.

    Returns:
        Document populated with imported notebook content.

    Raises:
        ImportPolicyError: If strict import policy rejects collected issues.
        TypeError: If ``source`` is not a supported notebook source.
        ValueError: If options or shifted headings are invalid.

    Examples:
        ```python
        from oodocs import NotebookImportOptions, from_ipynb

        doc = from_ipynb(
            "analysis.ipynb",
            title="Analysis Report",
            options=NotebookImportOptions(image_caption="Output {output_index}"),
        )
        doc.save_all("dist", formats=("pdf", "html"))
        ```
    """

    notebook = _load_notebook(source)
    markdown_base_dir = Path(base_dir) if base_dir is not None else _source_base_dir(source)
    blocks = parse_ipynb(
        notebook,
        options=options,
        include_outputs=include_outputs,
        include_code=include_code,
        include_markdown=include_markdown,
        include_raw=include_raw,
        code_language=code_language,
        numbered=numbered,
        toc=toc,
        heading_level_shift=heading_level_shift,
        base_dir=markdown_base_dir,
        import_policy=import_policy,
    )
    assert isinstance(blocks, list)
    document_title = title
    if document_title is None:
        document_title = _consume_first_chapter_title(blocks)
    document_title = document_title or _notebook_title(notebook) or "Notebook Document"

    return Document(
        document_title,
        blocks,
        settings=settings,
        citations=citations,
    )


def _load_notebook(source: NotebookSource) -> Mapping[str, object]:
    if isinstance(source, Mapping):
        return source

    if isinstance(source, (str, OsPathLike)):
        if isinstance(source, str) and source.lstrip().startswith("{"):
            notebook = json.loads(source)
        else:
            notebook = json.loads(Path(source).resolve().read_text(encoding="utf-8"))
        if not isinstance(notebook, Mapping):
            raise TypeError("Notebook JSON must decode to an object")
        return notebook

    raise TypeError(f"Unsupported notebook source: {type(source)!r}")


def _source_base_dir(source: NotebookSource) -> Path | None:
    if isinstance(source, Mapping):
        return None
    if isinstance(source, str) and source.lstrip().startswith("{"):
        return None
    if isinstance(source, (str, OsPathLike)):
        return Path(source).resolve().parent
    return None


def _resolve_options(
    options: NotebookImportOptions | None,
    *,
    include_outputs: bool | None,
    include_code: bool | None,
    include_markdown: bool | None,
    include_raw: bool | None,
    code_language: str | None,
) -> NotebookImportOptions:
    base = options or NotebookImportOptions()
    return NotebookImportOptions(
        include_outputs=base.include_outputs if include_outputs is None else include_outputs,
        include_code=base.include_code if include_code is None else include_code,
        include_markdown=base.include_markdown if include_markdown is None else include_markdown,
        include_raw=base.include_raw if include_raw is None else include_raw,
        code_language=base.code_language if code_language is None else code_language,
        exclude_tags=base.exclude_tags,
        max_output_lines=base.max_output_lines,
        image_caption=base.image_caption,
        include_error_outputs=base.include_error_outputs,
    )


def _notebook_cells(notebook: Mapping[str, object]) -> list[Mapping[str, object]]:
    cells = notebook.get("cells", [])
    if not isinstance(cells, SequenceABC) or isinstance(cells, (str, bytes)):
        return []
    normalized: list[Mapping[str, object]] = []
    for cell in cells:
        if isinstance(cell, Mapping):
            normalized.append(cell)
    return normalized


def _cell_tags(cell: Mapping[str, object]) -> tuple[str, ...]:
    metadata = cell.get("metadata")
    if not isinstance(metadata, Mapping):
        return ()
    tags = metadata.get("tags", ())
    if not isinstance(tags, SequenceABC) or isinstance(tags, (str, bytes)):
        return ()
    return tuple(str(tag) for tag in tags)


def _join_source(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes)):
        return "".join(str(part) for part in value)
    if value is None:
        return ""
    return str(value)


def _notebook_language(notebook: Mapping[str, object]) -> str | None:
    metadata = notebook.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    language_info = metadata.get("language_info")
    if isinstance(language_info, Mapping):
        name = language_info.get("name")
        if name:
            return str(name)
    kernelspec = metadata.get("kernelspec")
    if isinstance(kernelspec, Mapping):
        language = kernelspec.get("language")
        if language:
            return str(language)
        name = kernelspec.get("name")
        if name:
            return str(name)
    return None


def _notebook_title(notebook: Mapping[str, object]) -> str | None:
    metadata = notebook.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    for key in ("title", "name"):
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _consume_first_chapter_title(blocks: list[Block]) -> str | None:
    for index, block in enumerate(blocks):
        if isinstance(block, Chapter):
            del blocks[index]
            blocks[index:index] = block.children
            title = block.plain_title().strip()
            return title or None
    return None


def _append_notebook_block(
    root: list[Block],
    heading_stack: list[Section],
    block: Block,
) -> None:
    if isinstance(block, Section):
        while heading_stack and heading_stack[-1].level >= block.level:
            heading_stack.pop()
        if heading_stack:
            heading_stack[-1].children.append(block)
        else:
            root.append(block)
        heading_stack.append(block)
        _extend_stack_to_trailing_heading(heading_stack, block)
        return

    if heading_stack:
        heading_stack[-1].children.append(block)
    else:
        root.append(block)


def _extend_stack_to_trailing_heading(
    heading_stack: list[Section],
    block: Section,
) -> None:
    current = block
    while current.children and isinstance(current.children[-1], Section):
        current = current.children[-1]
        heading_stack.append(current)


def _cell_output_blocks(
    cell: Mapping[str, object],
    *,
    options: NotebookImportOptions,
    issues: list[ImportIssue],
    cell_index: int,
    numbered: bool,
    toc: bool | None,
    heading_level_shift: int,
    base_dir: Path | None,
    import_policy: str,
) -> list[Block]:
    outputs = cell.get("outputs", [])
    if not isinstance(outputs, SequenceABC) or isinstance(outputs, (str, bytes)):
        return []

    blocks: list[Block] = []
    for output_index, output in enumerate(outputs, start=1):
        if not isinstance(output, Mapping):
            continue
        blocks.extend(
            _output_blocks(
                output,
                options=options,
                issues=issues,
                cell_index=cell_index,
                output_index=output_index,
                numbered=numbered,
                toc=toc,
                heading_level_shift=heading_level_shift,
                base_dir=base_dir,
                import_policy=import_policy,
            )
        )
    return blocks


def _output_blocks(
    output: Mapping[str, object],
    *,
    options: NotebookImportOptions,
    issues: list[ImportIssue],
    cell_index: int,
    output_index: int,
    numbered: bool,
    toc: bool | None,
    heading_level_shift: int,
    base_dir: Path | None,
    import_policy: str,
) -> list[Block]:
    output_type = str(output.get("output_type", "")).strip()

    if output_type == "stream":
        return _plain_output_blocks(
            _join_source(output.get("text", "")),
            options=options,
            issues=issues,
            cell_index=cell_index,
            output_index=output_index,
        )

    if output_type in {"display_data", "execute_result"}:
        data = output.get("data")
        if isinstance(data, Mapping):
            # Prefer rich Markdown when available, then image payloads, and
            # finally text/plain so the most semantic representation survives.
            if "text/markdown" in data:
                markdown = _join_source(data["text/markdown"])
                if markdown.strip():
                    markdown_result = parse_markdown(
                        markdown,
                        numbered=numbered,
                        toc=toc,
                        heading_level_shift=heading_level_shift,
                        base_dir=base_dir,
                        diagnostics=True,
                        import_policy=import_policy,
                        source_name=f"cell[{cell_index}].outputs[{output_index}]",
                    )
                    assert isinstance(markdown_result, ImportResult)
                    issues.extend(markdown_result.issues)
                    return list(markdown_result.blocks)
            image = _output_image(
                data,
                options=options,
                cell_index=cell_index,
                output_index=output_index,
            )
            if image is not None:
                return [image]
            if "text/plain" in data:
                return _plain_output_blocks(
                    _join_source(data["text/plain"]),
                    options=options,
                    issues=issues,
                    cell_index=cell_index,
                    output_index=output_index,
                )
            _add_unsupported_mime_issue(data, issues, cell_index, output_index)
        return []

    if output_type == "error":
        if not options.include_error_outputs:
            issues.append(
                ImportIssue(
                    "info",
                    "notebook-error-output-skipped",
                    "Notebook error output was skipped by import options.",
                    source=f"cell[{cell_index}].outputs[{output_index}]",
                )
            )
            return []
        traceback = output.get("traceback")
        if isinstance(traceback, SequenceABC) and not isinstance(traceback, (str, bytes)):
            return _plain_output_blocks(
                "\n".join(str(line) for line in traceback),
                options=options,
                issues=issues,
                cell_index=cell_index,
                output_index=output_index,
            )
        ename = str(output.get("ename", "")).strip()
        evalue = str(output.get("evalue", "")).strip()
        return _plain_output_blocks(
            ": ".join(part for part in (ename, evalue) if part),
            options=options,
            issues=issues,
            cell_index=cell_index,
            output_index=output_index,
        )

    return []


def _plain_output_blocks(
    text: str,
    *,
    options: NotebookImportOptions,
    issues: list[ImportIssue],
    cell_index: int,
    output_index: int,
) -> list[Block]:
    if not text.strip():
        return []
    output_text = text.rstrip("\n")
    lines = output_text.splitlines()
    if options.max_output_lines is not None and len(lines) > options.max_output_lines:
        output_text = "\n".join(lines[: options.max_output_lines])
        issues.append(
            ImportIssue(
                "warning",
                "notebook-output-truncated",
                f"Output was truncated to {options.max_output_lines} line(s).",
                source=f"cell[{cell_index}].outputs[{output_index}]",
            )
        )
    return [
        CodeBlock(
            output_text,
            language="text",
            show_language=False,
        )
    ]


def _output_image(
    data: Mapping[str, object],
    *,
    options: NotebookImportOptions,
    cell_index: int,
    output_index: int,
) -> Figure | None:
    for mime_type, image_format in (
        ("image/png", "png"),
        ("image/jpeg", "jpeg"),
        ("image/jpg", "jpeg"),
    ):
        if mime_type not in data:
            continue
        encoded = _join_source(data[mime_type])
        if not encoded.strip():
            return None
        caption = (
            options.image_caption.format(
                cell_index=cell_index,
                output_index=output_index,
                mime_type=mime_type,
            )
            if options.image_caption
            else None
        )
        return Figure(
            ImageData(b64decode(encoded), format=image_format),
            caption=caption,
            format=image_format,
        )
    return None


def _add_unsupported_mime_issue(
    data: Mapping[str, object],
    issues: list[ImportIssue],
    cell_index: int,
    output_index: int,
) -> None:
    supported = {
        "text/markdown",
        "text/plain",
        "image/png",
        "image/jpeg",
        "image/jpg",
    }
    unsupported = [
        str(mime_type)
        for mime_type in data
        if "/" in str(mime_type) and str(mime_type) not in supported
    ]
    if unsupported:
        issues.append(
            ImportIssue(
                "warning",
                "unsupported-notebook-mime-type",
                "Unsupported notebook output MIME type(s): "
                + ", ".join(sorted(unsupported)),
                source=f"cell[{cell_index}].outputs[{output_index}]",
            )
        )


parse_notebook = parse_ipynb
from_notebook = from_ipynb


__all__ = [
    "NotebookImportOptions",
    "NotebookSource",
    "from_ipynb",
    "from_notebook",
    "parse_ipynb",
    "parse_notebook",
]
