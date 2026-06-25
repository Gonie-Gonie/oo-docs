"""Document indexing utilities used by renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from oodocs.components.base import Block
from oodocs.components.blocks import (
    Box,
    BulletList,
    CodeBlock,
    ColumnSpan,
    CountableBlock,
    Equation,
    MultiColumn,
    NumberedList,
    Paragraph,
    Part,
    Section,
)
from oodocs.components.generated import (
    CommentsPage,
    FigureList,
    FootnotesPage,
    ReferencesPage,
    TableList,
    TableOfContents,
)
from oodocs.components.inline import BlockReference, Citation, Comment, Footnote, Hyperlink, Text
from oodocs.components.media import Figure, SubFigure, SubFigureGroup, Table
from oodocs.components.references import CitationLibrary, CitationSource
from oodocs.core import OODocsError
from oodocs.document import Document
from oodocs.layout.theme import Theme


@dataclass(slots=True)
class CitationReferenceEntry:
    """A cited bibliography entry with its assigned reference number.

    Attributes:
        number: Assigned citation number.
        source: Cited bibliography source.
        anchor: Anchor used by renderers for links.
    """

    number: int
    source: CitationSource
    anchor: str


@dataclass(slots=True)
class CommentReferenceEntry:
    """A numbered inline comment encountered during indexing.

    Attributes:
        number: Assigned comment number.
        comment: Inline comment fragment.
    """

    number: int
    comment: Comment


@dataclass(slots=True)
class FootnoteReferenceEntry:
    """A numbered portable footnote encountered during indexing.

    Attributes:
        number: Assigned footnote number.
        footnote: Inline footnote fragment.
    """

    number: int
    footnote: Footnote


@dataclass(slots=True)
class HeadingEntry:
    """A heading included in the generated table of contents.

    Attributes:
        level: Heading level.
        title: Heading title fragments.
        number: Optional rendered heading number.
        anchor: Optional heading anchor.
    """

    level: int
    title: list[Text]
    number: str | None = None
    anchor: str | None = None


@dataclass(slots=True)
class CaptionEntry:
    """A numbered caption entry for a table or figure block.

    Attributes:
        number: Assigned caption number.
        block: Captioned table or figure block.
        anchor: Anchor used by renderers for links.
    """

    number: int
    block: Table | Figure | SubFigureGroup
    anchor: str


@dataclass(slots=True)
class CountableEntry:
    """A numbered theorem-like block entry.

    Attributes:
        number: Assigned counter value.
        block: Countable block.
        counter: Counter namespace.
        anchor: Anchor used by renderers for links.
    """

    number: int
    block: CountableBlock
    counter: str
    anchor: str


@dataclass(slots=True)
class RenderIndex:
    """Numbering and lookup information derived from a document tree."""

    tables: list[CaptionEntry] = field(default_factory=list)
    figures: list[CaptionEntry] = field(default_factory=list)
    table_numbers: dict[int, int] = field(default_factory=dict)
    figure_numbers: dict[int, int] = field(default_factory=dict)
    subfigure_labels: dict[int, str] = field(default_factory=dict)
    citations: list[CitationReferenceEntry] = field(default_factory=list)
    citation_numbers: dict[str, int] = field(default_factory=dict)
    citation_source_numbers: dict[int, int] = field(default_factory=dict)
    comments: list[CommentReferenceEntry] = field(default_factory=list)
    comment_numbers: dict[int, int] = field(default_factory=dict)
    footnotes: list[FootnoteReferenceEntry] = field(default_factory=list)
    footnote_numbers: dict[int, int] = field(default_factory=dict)
    headings: list[HeadingEntry] = field(default_factory=list)
    heading_numbers: dict[int, str] = field(default_factory=dict)
    heading_anchors: dict[int, str] = field(default_factory=dict)
    paragraph_numbers: dict[int, int] = field(default_factory=dict)
    equation_numbers: dict[int, int] = field(default_factory=dict)
    code_block_numbers: dict[int, int] = field(default_factory=dict)
    box_numbers: dict[int, int] = field(default_factory=dict)
    countables: list[CountableEntry] = field(default_factory=list)
    countable_numbers: dict[int, int] = field(default_factory=dict)
    countable_counters: dict[str, int] = field(default_factory=dict)
    block_anchors: dict[int, str] = field(default_factory=dict)

    def table_number(self, table: Table) -> int | None:
        """Return the assigned table number for a captioned table.

        Args:
            table: Table to look up.

        Returns:
            Assigned table number, or ``None`` when uncaptioned.
        """

        return self.table_numbers.get(id(table))

    def figure_number(self, figure: Figure | SubFigure | SubFigureGroup) -> int | None:
        """Return the assigned figure number for a captioned figure.

        Args:
            figure: Figure, subfigure, or subfigure group to look up.

        Returns:
            Assigned figure number, or ``None`` when uncaptioned.
        """

        return self.figure_numbers.get(id(figure))

    def subfigure_label(self, subfigure: SubFigure) -> str | None:
        """Return the assigned label for a subfigure inside a numbered group.

        Args:
            subfigure: Subfigure to look up.

        Returns:
            Assigned subfigure label, or ``None`` when unanchored.
        """

        return self.subfigure_labels.get(id(subfigure))

    def citation_number(self, target: CitationSource | str) -> int:
        """Return the assigned citation number for a source or key.

        Args:
            target: Citation source object or key.

        Returns:
            Assigned citation number.

        Raises:
            OODocsError: If the target was not indexed.
        """

        if isinstance(target, CitationSource):
            if target.key is not None and target.key in self.citation_numbers:
                return self.citation_numbers[target.key]
            source_id = id(target)
            if source_id in self.citation_source_numbers:
                return self.citation_source_numbers[source_id]
            raise OODocsError(f"Unknown citation source: {target.title!r}")
        if target not in self.citation_numbers:
            raise OODocsError(f"Unknown citation key: {target!r}")
        return self.citation_numbers[target]

    def citation_entry(self, target: CitationSource | str) -> CitationReferenceEntry:
        """Return the indexed citation entry for a source or key.

        Args:
            target: Citation source object or key.

        Returns:
            Indexed citation entry.

        Raises:
            OODocsError: If the target was not indexed.
        """

        number = self.citation_number(target)
        try:
            entry = self.citations[number - 1]
        except IndexError as exc:
            raise OODocsError(f"Unknown citation number: {number!r}") from exc
        if entry.number == number:
            return entry
        for entry in self.citations:
            if entry.number == number:
                return entry
        raise OODocsError(f"Unknown citation number: {number!r}")

    def comment_number(self, target: Comment) -> int:
        """Return the assigned inline comment number.

        Args:
            target: Comment fragment to look up.

        Returns:
            Assigned comment number.

        Raises:
            OODocsError: If the target was not indexed.
        """

        if id(target) not in self.comment_numbers:
            raise OODocsError(f"Unknown comment target: {target.value!r}")
        return self.comment_numbers[id(target)]

    def footnote_number(self, target: Footnote) -> int:
        """Return the assigned footnote number.

        Args:
            target: Footnote fragment to look up.

        Returns:
            Assigned footnote number.

        Raises:
            OODocsError: If the target was not indexed.
        """

        if id(target) not in self.footnote_numbers:
            raise OODocsError(f"Unknown footnote target: {target.value!r}")
        return self.footnote_numbers[id(target)]

    def heading_number(self, target: object) -> str | None:
        """Return the numbering label assigned to a section heading.

        Args:
            target: Heading block to look up.

        Returns:
            Heading number label, or ``None`` when unnumbered.
        """

        return self.heading_numbers.get(id(target))

    def table_anchor(self, table: Table) -> str | None:
        """Return the bookmark name for a captioned table.

        Args:
            table: Table to look up.

        Returns:
            Table anchor, or ``None`` when uncaptioned.
        """

        number = self.table_number(table)
        if number is None:
            return None
        return f"table_{number}"

    def figure_anchor(self, figure: Figure | SubFigure | SubFigureGroup) -> str | None:
        """Return the bookmark name for a captioned figure.

        Args:
            figure: Figure, subfigure, or subfigure group to look up.

        Returns:
            Figure anchor, or ``None`` when uncaptioned.
        """

        number = self.figure_number(figure)
        if number is None:
            return None
        if isinstance(figure, SubFigure):
            label = self.subfigure_label(figure)
            if label is not None:
                return f"figure_{number}_{label}"
        return f"figure_{number}"

    def citation_anchor(self, target: CitationSource | str) -> str:
        """Return the bookmark name for a cited reference entry.

        Args:
            target: Citation source object or key.

        Returns:
            Citation anchor.

        Raises:
            OODocsError: If the target was not indexed.
        """

        return f"citation_{self.citation_number(target)}"

    def heading_anchor(self, target: object) -> str | None:
        """Return the bookmark name for a numbered heading.

        Args:
            target: Heading block to look up.

        Returns:
            Heading anchor, or ``None`` when unanchored.
        """

        return self.heading_anchors.get(id(target))

    def paragraph_number(self, target: Paragraph) -> int | None:
        """Return the assigned paragraph reference number.

        Args:
            target: Paragraph to look up.

        Returns:
            Assigned paragraph number, or ``None``.
        """

        return self.paragraph_numbers.get(id(target))

    def equation_number(self, target: Equation) -> int | None:
        """Return the assigned equation reference number.

        Args:
            target: Equation to look up.

        Returns:
            Assigned equation number, or ``None``.
        """

        return self.equation_numbers.get(id(target))

    def code_block_number(self, target: CodeBlock) -> int | None:
        """Return the assigned code block reference number.

        Args:
            target: Code block to look up.

        Returns:
            Assigned code block number, or ``None``.
        """

        return self.code_block_numbers.get(id(target))

    def box_number(self, target: Box) -> int | None:
        """Return the assigned box reference number.

        Args:
            target: Box to look up.

        Returns:
            Assigned box number, or ``None``.
        """

        return self.box_numbers.get(id(target))

    def countable_number(self, target: CountableBlock) -> int | None:
        """Return the assigned number for a theorem-like block.

        Args:
            target: Countable block to look up.

        Returns:
            Assigned countable number, or ``None``.
        """

        return self.countable_numbers.get(id(target))

    def block_anchor(self, target: object) -> str | None:
        """Return the bookmark name for a generically anchored block.

        Args:
            target: Block object to look up.

        Returns:
            Block anchor, or ``None`` when no generic anchor was assigned.
        """

        return self.block_anchors.get(id(target))


def build_render_index(document: Document) -> RenderIndex:
    """Scan a document tree and assign render-time numbering.

    Args:
        document: Document to index.

    Returns:
        Render index containing numbering, anchors, and generated-page entries.
    """

    render_index = RenderIndex()
    _index_blocks(
        document.body.children,
        render_index,
        document.citations,
        document.settings.theme,
        heading_counters=[],
        part_counter=[0],
    )
    return render_index


def _advance_heading_counters(counters: list[int], level: int) -> list[int]:
    while len(counters) < level:
        counters.append(0)
    for index in range(max(level - 1, 0)):
        if counters[index] == 0:
            counters[index] = 1
    counters[level - 1] += 1
    # Truncate deeper counters after moving to a shallower heading so sibling
    # numbering restarts correctly.
    del counters[level:]
    return counters


def _register_block_anchor(render_index: RenderIndex, block: object, prefix: str) -> str:
    anchor = render_index.block_anchors.get(id(block))
    if anchor is not None:
        return anchor
    anchor = f"{prefix}_{len(render_index.block_anchors) + 1}"
    render_index.block_anchors[id(block)] = anchor
    return anchor


def _register_heading_anchor(render_index: RenderIndex, block: object) -> str:
    anchor = render_index.heading_anchors.get(id(block))
    if anchor is not None:
        return anchor
    anchor = f"heading_{len(render_index.heading_anchors) + 1}"
    render_index.heading_anchors[id(block)] = anchor
    return anchor


def _index_blocks(
    blocks: Sequence[Block],
    render_index: RenderIndex,
    citations: CitationLibrary,
    theme: Theme,
    *,
    heading_counters: list[int],
    part_counter: list[int],
) -> None:
    for block in blocks:
        if isinstance(block, Paragraph):
            if id(block) not in render_index.paragraph_numbers:
                render_index.paragraph_numbers[id(block)] = len(render_index.paragraph_numbers) + 1
            _register_block_anchor(render_index, block, "paragraph")
            _index_inlines(block.content, render_index, citations)
            continue
        if isinstance(block, (BulletList, NumberedList)):
            for item, child_lists in zip(block.items, block.item_children):
                if id(item) not in render_index.paragraph_numbers:
                    render_index.paragraph_numbers[id(item)] = len(render_index.paragraph_numbers) + 1
                _register_block_anchor(render_index, item, "paragraph")
                _index_inlines(item.content, render_index, citations)
                _index_blocks(
                    child_lists,
                    render_index,
                    citations,
                    theme,
                    heading_counters=heading_counters,
                    part_counter=part_counter,
                )
            continue
        if isinstance(block, CodeBlock):
            if id(block) not in render_index.code_block_numbers:
                render_index.code_block_numbers[id(block)] = len(render_index.code_block_numbers) + 1
            _register_block_anchor(render_index, block, "code")
            continue
        if isinstance(block, Equation):
            if id(block) not in render_index.equation_numbers:
                render_index.equation_numbers[id(block)] = len(render_index.equation_numbers) + 1
            _register_block_anchor(render_index, block, "equation")
            continue
        if isinstance(block, Box):
            if id(block) not in render_index.box_numbers:
                render_index.box_numbers[id(block)] = len(render_index.box_numbers) + 1
            _register_block_anchor(render_index, block, "box")
            if block.title is not None:
                _index_inlines(block.title, render_index, citations)
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=heading_counters,
                part_counter=part_counter,
            )
            continue
        if isinstance(block, CountableBlock):
            anchor = _register_block_anchor(render_index, block, "countable")
            if block.title is not None:
                _index_inlines(block.title, render_index, citations)
            if block.numbered and block.counter is not None and id(block) not in render_index.countable_numbers:
                # Countable blocks use named counter namespaces so theorem-like
                # families can share or separate numbering sequences.
                number = render_index.countable_counters.get(block.counter, 0) + 1
                render_index.countable_counters[block.counter] = number
                render_index.countable_numbers[id(block)] = number
                render_index.countables.append(
                    CountableEntry(
                        number=number,
                        block=block,
                        counter=block.counter,
                        anchor=anchor,
                    )
                )
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=heading_counters,
                part_counter=part_counter,
            )
            continue
        if isinstance(block, (ColumnSpan, MultiColumn)):
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=heading_counters,
                part_counter=part_counter,
            )
            continue
        if isinstance(block, Part):
            _index_inlines(block.title, render_index, citations)
            number_label: str | None = None
            if block.numbered:
                part_counter[0] += 1
                number_label = theme.format_part_label(part_counter[0])
                render_index.heading_numbers[id(block)] = number_label
            anchor = (
                _register_heading_anchor(render_index, block)
                if (block.numbered or block.toc)
                else None
            )
            if block.toc:
                render_index.headings.append(
                    HeadingEntry(
                        level=block.level,
                        title=block.title,
                        number=number_label,
                        anchor=anchor,
                    )
                )
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=heading_counters,
                part_counter=part_counter,
            )
            continue
        if isinstance(block, Section):
            _index_inlines(block.title, render_index, citations)
            current_counters = heading_counters
            number_label: str | None = None
            if block.numbered:
                current_counters = _advance_heading_counters(
                    heading_counters,
                    block.level,
                )
                number_label = theme.format_heading_label(
                    current_counters[: block.level]
                )
                render_index.heading_numbers[id(block)] = number_label
            anchor = (
                _register_heading_anchor(render_index, block)
                if (block.numbered or block.toc)
                else None
            )
            if block.toc:
                render_index.headings.append(
                    HeadingEntry(
                        level=block.level,
                        title=block.title,
                        number=number_label,
                        anchor=anchor,
                    )
                )
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=current_counters,
                part_counter=part_counter,
            )
            continue
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
            if block.title is not None:
                _index_inlines(block.title, render_index, citations)
            continue
        if isinstance(block, Table):
            for header_row in block.header_rows:
                for header in header_row:
                    _index_inlines(header.content.content, render_index, citations)
            for row in block.rows:
                for cell in row:
                    _index_inlines(cell.content.content, render_index, citations)
            if block.caption is not None:
                _index_inlines(block.caption.content, render_index, citations)
                number = len(render_index.tables) + 1
                render_index.tables.append(
                    CaptionEntry(
                        number=number,
                        block=block,
                        anchor=f"table_{number}",
                    )
                )
                render_index.table_numbers[id(block)] = number
            continue
        if isinstance(block, Figure):
            if block.caption is not None:
                _index_inlines(block.caption.content, render_index, citations)
                number = len(render_index.figures) + 1
                render_index.figures.append(
                    CaptionEntry(
                        number=number,
                        block=block,
                        anchor=f"figure_{number}",
                    )
                )
                render_index.figure_numbers[id(block)] = number
            continue
        if isinstance(block, SubFigureGroup):
            for subfigure in block.subfigures:
                if subfigure.caption is not None:
                    _index_inlines(subfigure.caption.content, render_index, citations)
            if block.caption is not None:
                _index_inlines(block.caption.content, render_index, citations)
                number = len(render_index.figures) + 1
                render_index.figures.append(
                    CaptionEntry(
                        number=number,
                        block=block,
                        anchor=f"figure_{number}",
                    )
                )
                render_index.figure_numbers[id(block)] = number
                for index, subfigure in enumerate(block.subfigures):
                    label = block.label_for_index(index)
                    render_index.figure_numbers[id(subfigure)] = number
                    render_index.subfigure_labels[id(subfigure)] = label


def _index_inlines(
    fragments: Sequence[Text],
    render_index: RenderIndex,
    citations: CitationLibrary,
) -> None:
    for fragment in fragments:
        if isinstance(fragment, BlockReference):
            if fragment.label is not None:
                _index_inlines(fragment.label, render_index, citations)
            continue
        if isinstance(fragment, Hyperlink):
            _index_inlines(fragment.label, render_index, citations)
            continue
        if isinstance(fragment, Comment):
            _index_inlines(fragment.comment, render_index, citations)
            if id(fragment) in render_index.comment_numbers:
                continue
            number = len(render_index.comments) + 1
            render_index.comments.append(
                CommentReferenceEntry(number=number, comment=fragment)
            )
            render_index.comment_numbers[id(fragment)] = number
            continue
        if isinstance(fragment, Footnote):
            _index_inlines(fragment.note, render_index, citations)
            if id(fragment) in render_index.footnote_numbers:
                continue
            number = len(render_index.footnotes) + 1
            render_index.footnotes.append(
                FootnoteReferenceEntry(number=number, footnote=fragment)
            )
            render_index.footnote_numbers[id(fragment)] = number
            continue
        if isinstance(fragment, Citation):
            target = fragment.target
            if isinstance(target, CitationSource):
                if target.key is not None and target.key in render_index.citation_numbers:
                    continue
                if id(target) in render_index.citation_source_numbers:
                    continue
                source = target
            else:
                if target in render_index.citation_numbers:
                    continue
                source = citations.resolve(target)

            number = len(render_index.citations) + 1
            render_index.citations.append(
                CitationReferenceEntry(
                    number=number,
                    source=source,
                    anchor=f"citation_{number}",
                )
            )
            render_index.citation_source_numbers[id(source)] = number
            if source.key is not None:
                render_index.citation_numbers[source.key] = number


__all__ = [
    "CaptionEntry",
    "CitationReferenceEntry",
    "CommentReferenceEntry",
    "CountableEntry",
    "FootnoteReferenceEntry",
    "HeadingEntry",
    "RenderIndex",
    "build_render_index",
]
