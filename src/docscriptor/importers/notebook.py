"""Jupyter notebook import helpers for docscriptor documents."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence as SequenceABC
from os import PathLike as OsPathLike
from pathlib import Path
from typing import Sequence

from docscriptor.components.base import Block
from docscriptor.components.blocks import Chapter, CodeBlock, Paragraph, Section
from docscriptor.components.references import CitationLibrary, CitationSource
from docscriptor.document import Document
from docscriptor.importers.markdown import parse_markdown
from docscriptor.settings import DocumentSettings


NotebookSource = str | OsPathLike[str] | Mapping[str, object]


def parse_ipynb(
    source: NotebookSource,
    *,
    include_outputs: bool = True,
    include_code: bool = True,
    include_markdown: bool = True,
    include_raw: bool = True,
    code_language: str | None = None,
) -> list[Block]:
    """Parse a Jupyter notebook into docscriptor block objects.

    Markdown cells are parsed through ``parse_markdown(...)``. Code cells become
    ``CodeBlock`` objects. Textual cell outputs are imported as unlabeled text
    code blocks when ``include_outputs`` is true.
    """

    notebook = _load_notebook(source)
    language = code_language or _notebook_language(notebook) or "python"
    blocks: list[Block] = []
    heading_stack: list[Section] = []

    for cell in _notebook_cells(notebook):
        cell_type = str(cell.get("cell_type", "")).strip().lower()
        cell_source = _join_source(cell.get("source", ""))

        if cell_type == "markdown":
            if include_markdown and cell_source.strip():
                for block in parse_markdown(cell_source):
                    _append_notebook_block(blocks, heading_stack, block)
            continue

        if cell_type == "code":
            if include_code and cell_source.strip():
                _append_notebook_block(
                    blocks,
                    heading_stack,
                    CodeBlock(cell_source.rstrip("\n"), language=language),
                )
            if include_outputs:
                for block in _cell_output_blocks(cell):
                    _append_notebook_block(blocks, heading_stack, block)
            continue

        if include_raw and cell_source.strip():
            _append_notebook_block(
                blocks,
                heading_stack,
                CodeBlock(
                    cell_source.rstrip("\n"),
                    language="text",
                    show_language=False,
                ),
            )

    return blocks


def from_ipynb(
    source: NotebookSource,
    *,
    title: str | None = None,
    settings: DocumentSettings | None = None,
    citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
    include_outputs: bool = True,
    include_code: bool = True,
    include_markdown: bool = True,
    include_raw: bool = True,
    code_language: str | None = None,
) -> Document:
    """Create a ``Document`` from a Jupyter notebook.

    When ``title`` is not supplied, the first imported level-1 Markdown heading
    becomes the document title. If no level-1 heading is present, notebook
    metadata is checked before falling back to ``"Notebook Document"``.
    """

    notebook = _load_notebook(source)
    blocks = parse_ipynb(
        notebook,
        include_outputs=include_outputs,
        include_code=include_code,
        include_markdown=include_markdown,
        include_raw=include_raw,
        code_language=code_language,
    )
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
            notebook = json.loads(Path(source).read_text(encoding="utf-8"))
        if not isinstance(notebook, Mapping):
            raise TypeError("Notebook JSON must decode to an object")
        return notebook

    raise TypeError(f"Unsupported notebook source: {type(source)!r}")


def _notebook_cells(notebook: Mapping[str, object]) -> list[Mapping[str, object]]:
    cells = notebook.get("cells", [])
    if not isinstance(cells, SequenceABC) or isinstance(cells, (str, bytes)):
        return []
    normalized: list[Mapping[str, object]] = []
    for cell in cells:
        if isinstance(cell, Mapping):
            normalized.append(cell)
    return normalized


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


def _cell_output_blocks(cell: Mapping[str, object]) -> list[Block]:
    outputs = cell.get("outputs", [])
    if not isinstance(outputs, SequenceABC) or isinstance(outputs, (str, bytes)):
        return []

    blocks: list[Block] = []
    for output in outputs:
        if not isinstance(output, Mapping):
            continue
        text = _output_text(output)
        if not text.strip():
            continue
        blocks.append(
            CodeBlock(
                text.rstrip("\n"),
                language="text",
                show_language=False,
            )
        )
    return blocks


def _output_text(output: Mapping[str, object]) -> str:
    output_type = str(output.get("output_type", "")).strip()

    if output_type == "stream":
        return _join_source(output.get("text", ""))

    if output_type in {"display_data", "execute_result"}:
        data = output.get("data")
        if isinstance(data, Mapping):
            for mime_type in ("text/plain", "text/markdown"):
                if mime_type in data:
                    return _join_source(data[mime_type])
        return ""

    if output_type == "error":
        traceback = output.get("traceback")
        if isinstance(traceback, SequenceABC) and not isinstance(traceback, (str, bytes)):
            return "\n".join(str(line) for line in traceback)
        ename = str(output.get("ename", "")).strip()
        evalue = str(output.get("evalue", "")).strip()
        return ": ".join(part for part in (ename, evalue) if part)

    return ""


parse_notebook = parse_ipynb
from_notebook = from_ipynb


__all__ = [
    "NotebookSource",
    "from_ipynb",
    "from_notebook",
    "parse_ipynb",
    "parse_notebook",
]
