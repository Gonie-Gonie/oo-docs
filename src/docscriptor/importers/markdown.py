"""Markdown import helpers for docscriptor documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from docscriptor.components.base import Block
from docscriptor.components.blocks import (
    Box,
    BulletList,
    Chapter,
    CodeBlock,
    Divider,
    NumberedList,
    Paragraph,
    Section,
    Subsection,
    Subsubsection,
)
from docscriptor.components.inline import Text
from docscriptor.components.markup import markup
from docscriptor.components.media import Figure, Table
from docscriptor.components.references import CitationLibrary, CitationSource
from docscriptor.document import Document
from docscriptor.layout.theme import ListStyle
from docscriptor.settings import DocumentSettings


_ATX_HEADING_RE = re.compile(
    r"^ {0,3}(?P<marker>#{1,6})(?:[ \t]+|$)(?P<title>.*?)(?:[ \t]+#+[ \t]*)?$"
)
_SETEXT_HEADING_RE = re.compile(r"^ {0,3}(?P<marker>=+|-+)[ \t]*$")
_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_THEMATIC_BREAK_RE = re.compile(
    r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$"
)
_LIST_RE = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>(?P<number>\d{1,9})[.)]|[-+*])[ \t]+(?P<body>.*)$"
)
_TASK_RE = re.compile(r"^\[([ xX])\][ \t]+(.*)$")
_LINK_REFERENCE_RE = re.compile(
    r"^ {0,3}\[(?P<label>[^\]]+)\]:[ \t]*(?P<target><[^>]+>|\S+)"
    r"(?:[ \t]+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?[ \t]*$"
)
_BLOCK_IMAGE_RE = re.compile(
    r"^ {0,3}!\[(?P<alt>[^\]]*)\]\((?P<target><[^>]+>|\S+)"
    r"(?:[ \t]+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\)[ \t]*$"
)


@dataclass(slots=True)
class _Heading:
    level: int
    title: list[Text]


_MarkdownEvent = Block | _Heading


def parse_markdown(source: str) -> list[Block]:
    """Parse Markdown text into docscriptor block objects.

    The parser targets the Markdown and GitHub Flavored Markdown constructs that
    map cleanly to docscriptor's renderer-neutral model: headings, paragraphs,
    lists, task-list markers, block quotes, code blocks, thematic breaks,
    tables, local images, links, autolinks, emphasis, inline code, and
    strikethrough.
    """

    parser = _MarkdownParser(source)
    return _build_heading_hierarchy(parser.parse())


def from_markdown(
    source: str,
    *,
    title: str | None = None,
    settings: DocumentSettings | None = None,
    citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
) -> Document:
    """Create a ``Document`` from Markdown text.

    When ``title`` is not supplied, the first level-1 heading becomes the
    document title and is not repeated as a chapter. If no level-1 heading is
    present, the title defaults to ``"Markdown Document"``.
    """

    parser = _MarkdownParser(source)
    events = parser.parse()
    document_title = title or _consume_first_h1_title(events) or "Markdown Document"
    return Document(
        document_title,
        _build_heading_hierarchy(events),
        settings=settings,
        citations=citations,
    )


class _MarkdownParser:
    def __init__(self, source: str) -> None:
        normalized_source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.lines = normalized_source.split("\n")
        self.references = _collect_link_references(self.lines)

    def parse(self) -> list[_MarkdownEvent]:
        events: list[_MarkdownEvent] = []
        index = 0
        while index < len(self.lines):
            line = self.lines[index]
            if _is_blank(line) or _is_link_reference(line):
                index += 1
                continue

            fenced_code = self._parse_fenced_code(index)
            if fenced_code is not None:
                block, index = fenced_code
                events.append(block)
                continue

            indented_code = self._parse_indented_code(index)
            if indented_code is not None:
                block, index = indented_code
                events.append(block)
                continue

            heading = self._parse_atx_heading(index)
            if heading is not None:
                events.append(heading)
                index += 1
                continue

            if _THEMATIC_BREAK_RE.match(line):
                events.append(Divider())
                index += 1
                continue

            table = self._parse_table(index)
            if table is not None:
                block, index = table
                events.append(block)
                continue

            setext_heading = self._parse_setext_heading(index)
            if setext_heading is not None:
                heading, index = setext_heading
                events.append(heading)
                continue

            block_quote = self._parse_block_quote(index)
            if block_quote is not None:
                block, index = block_quote
                events.append(block)
                continue

            list_block = self._parse_list(index)
            if list_block is not None:
                block, index = list_block
                events.append(block)
                continue

            block_image = self._parse_block_image(index)
            if block_image is not None:
                block, index = block_image
                events.append(block)
                continue

            paragraph, index = self._parse_paragraph(index)
            events.append(paragraph)

        return events

    def _parse_fenced_code(self, index: int) -> tuple[CodeBlock, int] | None:
        match = _FENCE_RE.match(self.lines[index])
        if match is None:
            return None
        fence = match.group("fence")
        marker = fence[0]
        minimum_length = len(fence)
        language = _normalize_code_info(match.group("info"))
        code_lines: list[str] = []
        index += 1
        while index < len(self.lines):
            line = self.lines[index]
            if re.match(rf"^ {{0,3}}{re.escape(marker)}{{{minimum_length},}}[ \t]*$", line):
                index += 1
                break
            code_lines.append(line)
            index += 1
        return CodeBlock("\n".join(code_lines), language=language), index

    def _parse_indented_code(self, index: int) -> tuple[CodeBlock, int] | None:
        if not _is_indented_code_line(self.lines[index]):
            return None
        code_lines: list[str] = []
        while index < len(self.lines):
            line = self.lines[index]
            if _is_blank(line):
                code_lines.append("")
                index += 1
                continue
            if not _is_indented_code_line(line):
                break
            code_lines.append(_strip_code_indent(line))
            index += 1
        return CodeBlock("\n".join(code_lines)), index

    def _parse_atx_heading(self, index: int) -> _Heading | None:
        match = _ATX_HEADING_RE.match(self.lines[index])
        if match is None:
            return None
        level = len(match.group("marker"))
        title = match.group("title").strip()
        return _Heading(level=level, title=markup(title, references=self.references))

    def _parse_setext_heading(self, index: int) -> tuple[_Heading, int] | None:
        if index + 1 >= len(self.lines):
            return None
        line = self.lines[index]
        underline = self.lines[index + 1]
        if _is_blank(line) or self._is_block_start(index):
            return None
        match = _SETEXT_HEADING_RE.match(underline)
        if match is None:
            return None
        level = 1 if match.group("marker").startswith("=") else 2
        return _Heading(level=level, title=markup(line.strip(), references=self.references)), index + 2

    def _parse_block_quote(self, index: int) -> tuple[Box, int] | None:
        if not self.lines[index].lstrip().startswith(">"):
            return None
        quote_lines: list[str] = []
        while index < len(self.lines):
            line = self.lines[index]
            stripped = line.lstrip()
            if not stripped.startswith(">"):
                break
            content = stripped[1:]
            if content.startswith((" ", "\t")):
                content = content[1:]
            quote_lines.append(content)
            index += 1
        children = parse_markdown("\n".join(quote_lines))
        return Box(*children), index

    def _parse_list(self, index: int) -> tuple[BulletList | NumberedList, int] | None:
        first_match = _LIST_RE.match(self.lines[index])
        if first_match is None:
            return None

        ordered = first_match.group("number") is not None
        start = int(first_match.group("number") or 1)
        items: list[Paragraph] = []
        has_task_marker = False

        while index < len(self.lines):
            match = _LIST_RE.match(self.lines[index])
            if match is None or (match.group("number") is not None) != ordered:
                break
            item_lines = [match.group("body")]
            index += 1

            while index < len(self.lines):
                line = self.lines[index]
                if _is_blank(line):
                    break
                if _LIST_RE.match(line):
                    break
                if self._is_block_start(index) and not _is_list_continuation(line):
                    break
                item_lines.append(_strip_list_continuation(line))
                index += 1

            item_text = "\n".join(item_lines).strip()
            task_match = _TASK_RE.match(item_text)
            prefix = ""
            if task_match is not None:
                has_task_marker = True
                prefix = "[x] " if task_match.group(1).lower() == "x" else "[ ] "
                item_text = task_match.group(2)
            items.append(
                Paragraph(
                    [Text(prefix)] if prefix else [],
                    markup(item_text, references=self.references),
                )
            )

            if index < len(self.lines) and _is_blank(self.lines[index]):
                break

        if has_task_marker:
            task_style = ListStyle(marker_format="none", suffix="")
            return BulletList(*items, style=task_style), index
        if ordered:
            return NumberedList(*items, start=start), index
        return BulletList(*items), index

    def _parse_table(self, index: int) -> tuple[Table, int] | None:
        if index + 1 >= len(self.lines):
            return None
        header_line = self.lines[index]
        delimiter_line = self.lines[index + 1]
        if not _has_unescaped_pipe(header_line):
            return None
        alignments = _parse_table_delimiter(delimiter_line)
        if alignments is None:
            return None

        header_cells = _split_table_row(header_line)
        if len(header_cells) != len(alignments):
            return None

        rows: list[list[Paragraph]] = []
        index += 2
        while index < len(self.lines):
            line = self.lines[index]
            if _is_blank(line) or not _has_unescaped_pipe(line):
                break
            cells = _split_table_row(line)
            cells = (cells + [""] * len(header_cells))[: len(header_cells)]
            rows.append([_markdown_cell(cell, self.references) for cell in cells])
            index += 1

        column_styles = {
            column_index: {"horizontal_alignment": alignment}
            for column_index, alignment in enumerate(alignments)
            if alignment is not None
        }
        return (
            Table(
                headers=[_markdown_cell(cell, self.references) for cell in header_cells],
                rows=rows,
                column_styles=column_styles or None,
            ),
            index,
        )

    def _parse_block_image(self, index: int) -> tuple[Figure | Paragraph, int] | None:
        match = _BLOCK_IMAGE_RE.match(self.lines[index])
        if match is None:
            return None
        alt_text = match.group("alt")
        target = _strip_angle_destination(match.group("target"))
        if _is_remote_url(target):
            return (
                Paragraph(markup(f"{alt_text}: {target}", references=self.references)),
                index + 1,
            )
        return Figure(target, caption=markup(alt_text, references=self.references)), index + 1

    def _parse_paragraph(self, index: int) -> tuple[Paragraph, int]:
        paragraph_lines: list[str] = []
        while index < len(self.lines):
            line = self.lines[index]
            if _is_blank(line) or _is_link_reference(line):
                break
            if paragraph_lines and self._is_block_start(index):
                break
            if self._parse_setext_heading(index) is not None:
                break
            paragraph_lines.append(line.strip())
            index += 1
        return Paragraph(markup("\n".join(paragraph_lines), references=self.references)), index

    def _is_block_start(self, index: int) -> bool:
        line = self.lines[index]
        if _is_blank(line) or _is_link_reference(line):
            return True
        return (
            _FENCE_RE.match(line) is not None
            or _is_indented_code_line(line)
            or _ATX_HEADING_RE.match(line) is not None
            or _THEMATIC_BREAK_RE.match(line) is not None
            or _LIST_RE.match(line) is not None
            or line.lstrip().startswith(">")
            or _BLOCK_IMAGE_RE.match(line) is not None
            or self._parse_table(index) is not None
        )


def _build_heading_hierarchy(events: list[_MarkdownEvent]) -> list[Block]:
    root: list[Block] = []
    stack: list[tuple[int, Section]] = []

    for event in events:
        if isinstance(event, _Heading):
            section = _section_for_heading(event)
            while stack and stack[-1][0] >= event.level:
                stack.pop()
            if stack:
                stack[-1][1].children.append(section)
            else:
                root.append(section)
            stack.append((event.level, section))
            continue

        if stack:
            stack[-1][1].children.append(event)
        else:
            root.append(event)

    return root


def _section_for_heading(heading: _Heading) -> Section:
    if heading.level == 1:
        return Chapter(heading.title)
    if heading.level == 3:
        return Subsection(heading.title)
    if heading.level == 4:
        return Subsubsection(heading.title)
    return Section(heading.title, level=heading.level)


def _consume_first_h1_title(events: list[_MarkdownEvent]) -> str | None:
    for index, event in enumerate(events):
        if isinstance(event, _Heading) and event.level == 1:
            del events[index]
            title = "".join(fragment.plain_text() for fragment in event.title).strip()
            return title or None
    return None


def _collect_link_references(lines: list[str]) -> dict[str, str]:
    references: dict[str, str] = {}
    for line in lines:
        match = _LINK_REFERENCE_RE.match(line)
        if match is None:
            continue
        references.setdefault(
            _normalize_reference_label(match.group("label")),
            _strip_angle_destination(match.group("target")),
        )
    return references


def _is_link_reference(line: str) -> bool:
    return _LINK_REFERENCE_RE.match(line) is not None


def _normalize_reference_label(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _normalize_code_info(value: str) -> str | None:
    info = value.strip()
    if not info:
        return None
    language = info.split()[0]
    if language.startswith("{.") and language.endswith("}"):
        language = language[2:-1]
    return language or None


def _is_blank(line: str) -> bool:
    return not line.strip()


def _is_indented_code_line(line: str) -> bool:
    return line.startswith("    ") or line.startswith("\t")


def _strip_code_indent(line: str) -> str:
    if line.startswith("\t"):
        return line[1:]
    return line[4:]


def _is_list_continuation(line: str) -> bool:
    return line.startswith(("  ", "\t"))


def _strip_list_continuation(line: str) -> str:
    if line.startswith("\t"):
        return line[1:]
    return line[2:] if line.startswith("  ") else line.strip()


def _parse_table_delimiter(line: str) -> list[str | None] | None:
    if not _has_unescaped_pipe(line):
        return None
    alignments: list[str | None] = []
    for cell in _split_table_row(line):
        marker = cell.strip()
        if re.fullmatch(r":?-+:?", marker) is None:
            return None
        starts = marker.startswith(":")
        ends = marker.endswith(":")
        if starts and ends:
            alignments.append("center")
        elif ends:
            alignments.append("right")
        elif starts:
            alignments.append("left")
        else:
            alignments.append(None)
    return alignments


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in stripped:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(character)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _has_unescaped_pipe(line: str) -> bool:
    escaped = False
    for character in line:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == "|":
            return True
    return False


def _markdown_cell(value: str, references: dict[str, str]) -> Paragraph:
    return Paragraph(markup(value.strip(), references=references))


def _strip_angle_destination(value: str) -> str:
    if len(value) >= 2 and value[0] == "<" and value[-1] == ">":
        return value[1:-1]
    return value


def _is_remote_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


__all__ = ["from_markdown", "parse_markdown"]
