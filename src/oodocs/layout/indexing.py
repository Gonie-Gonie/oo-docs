"""Document indexing utilities used by renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from oodocs.components.base import Block
from oodocs.components.blocks import (
    Appendix,
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
    ListOfComments,
    GeneratedListScope,
    ListOfAlgorithms,
    ListOfFigures,
    ListOfFootnotes,
    ListOfReferences,
    ListOfTables,
    TableOfContents,
)
from oodocs.components.inline import (
    BlockReference,
    Citation,
    Comment,
    Footnote,
    Hyperlink,
    ReferenceFormat,
    Text,
)
from oodocs.components.media import Figure, SubFigure, SubFigureGroup, SubTable, SubTableGroup, Table
from oodocs.components.references import CitationLibrary, CitationSource, normalize_reference_sort
from oodocs.core import OODocsError
from oodocs.document import Document
from oodocs.styles import Theme


@dataclass(slots=True)
class CitationReferenceEntry:
    """A cited bibliography entry with its assigned reference number.

    Attributes:
        number: Assigned citation number.
        source: Cited bibliography source.
        anchor: Anchor used by renderers for links.

    Examples:
        ```python
        from oodocs import CitationSource
        from oodocs.layout.indexing import CitationReferenceEntry

        source = CitationSource("Validation Study", key="study")
        entry = CitationReferenceEntry(1, source, "citation_1")
        ```
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

    Examples:
        ```python
        from oodocs import comment
        from oodocs.layout.indexing import CommentReferenceEntry

        entry = CommentReferenceEntry(1, comment("Needs reviewer confirmation"))
        ```
    """

    number: int
    comment: Comment


@dataclass(slots=True)
class FootnoteReferenceEntry:
    """A numbered portable footnote encountered during indexing.

    Attributes:
        number: Assigned footnote number.
        footnote: Inline footnote fragment.
        stream: Footnote stream name.
        anchor: Stable generated-list anchor.

    Examples:
        ```python
        from oodocs import footnote
        from oodocs.layout.indexing import FootnoteReferenceEntry

        entry = FootnoteReferenceEntry(1, footnote("Measured on the validation split."))
        ```
    """

    number: int
    footnote: Footnote
    stream: str = "default"
    anchor: str = ""


@dataclass(slots=True, frozen=True)
class EntryScope:
    """Ancestor scope for generated lists and index entries.

    Attributes:
        part_id: Identity of the nearest enclosing ``Part``.
        chapter_id: Identity of the nearest enclosing level-1 ``Section``.
        heading_path: Ancestor section identities from outermost heading to
            innermost heading.
    """

    part_id: int | None = None
    chapter_id: int | None = None
    heading_path: tuple[int, ...] = ()

    def with_part(self, part: Part) -> EntryScope:
        """Return a scope for descendants of ``part``.

        Args:
            part: Part whose descendants should inherit the new scope.

        Returns:
            Entry scope rooted at the part.
        """

        return EntryScope(part_id=id(part))

    def with_section(self, section: Section) -> EntryScope:
        """Return a scope for descendants of ``section``.

        Args:
            section: Section whose descendants should inherit the new scope.

        Returns:
            Entry scope extended with the section.
        """

        section_id = id(section)
        chapter_id = section_id if section.level == 1 else self.chapter_id
        return EntryScope(
            part_id=self.part_id,
            chapter_id=chapter_id,
            heading_path=self.heading_path + (section_id,),
        )


@dataclass(slots=True)
class HeadingEntry:
    """A heading included in the generated table of contents.

    Attributes:
        level: Heading level.
        title: Heading title fragments.
        number: Optional rendered heading number.
        anchor: Optional heading anchor.
        scope: Ancestor scope containing this heading.

    Examples:
        ```python
        from oodocs import Text
        from oodocs.layout.indexing import HeadingEntry

        entry = HeadingEntry(level=1, title=[Text("Methods")], number="1", anchor="heading_1")
        ```
    """

    level: int
    title: list[Text]
    number: str | None = None
    anchor: str | None = None
    scope: EntryScope = field(default_factory=EntryScope)


@dataclass(slots=True)
class CaptionEntry:
    """A numbered caption entry for a table or figure block.

    Attributes:
        number: Assigned caption number.
        block: Captioned table or figure block.
        anchor: Anchor used by renderers for links.
        scope: Ancestor scope containing this caption.

    Examples:
        ```python
        from oodocs import Table
        from oodocs.layout.indexing import CaptionEntry

        table = Table(["Metric"], [["Accuracy"]], caption="Evaluation metrics")
        entry = CaptionEntry(1, table, "table_1")
        ```
    """

    number: int
    block: Table | SubTableGroup | Figure | SubFigureGroup
    anchor: str
    scope: EntryScope = field(default_factory=EntryScope)


@dataclass(slots=True)
class CountableEntry:
    """A numbered theorem-like block entry.

    Attributes:
        number: Assigned counter value.
        block: Countable block.
        counter: Counter namespace.
        anchor: Anchor used by renderers for links.
        scope: Ancestor scope used by generated lists.

    Examples:
        ```python
        from oodocs.structure import Theorem
        from oodocs.layout.indexing import CountableEntry

        theorem = Theorem("Every release has an audit trail.")
        entry = CountableEntry(1, theorem, "theorem", "countable_1")
        ```
    """

    number: int
    block: CountableBlock
    counter: str
    anchor: str
    scope: EntryScope = field(default_factory=EntryScope)


@dataclass(slots=True)
class ResolvedBlockReference:
    """Resolved label, number text, and anchor for an object reference.

    Attributes:
        label: Effective reference label.
        value: Rendered reference number or value.
        anchor: Optional internal link anchor.
    """

    label: str
    value: str
    anchor: str | None

    def text(self, reference_format: ReferenceFormat | None = None) -> str:
        """Return the formatted reference text.

        Args:
            reference_format: Optional formatting overrides.

        Returns:
            Formatted reference text.
        """

        return _format_reference_text(self, reference_format or ReferenceFormat())


@dataclass(slots=True)
class ReferenceTextPiece:
    """Text plus optional internal anchor for formatted references.

    Attributes:
        text: Text content for this reference segment.
        anchor: Optional internal link anchor.
    """

    text: str
    anchor: str | None = None


@dataclass(slots=True)
class RenderIndex:
    """Numbering and lookup information derived from a document tree.

    Attributes:
        tables: Indexed caption entries for tables.
        figures: Indexed caption entries for figures and figure groups.
        table_numbers: Table numbers keyed by table identity.
        figure_numbers: Figure numbers keyed by figure identity.
        subfigure_labels: Subfigure labels keyed by subfigure identity.
        subfigure_reference_labels: Formatted subfigure reference suffixes keyed
            by subfigure identity.
        subtable_labels: Subtable labels keyed by subtable identity.
        subtable_reference_labels: Formatted subtable reference suffixes keyed
            by subtable identity.
        citations: Indexed citation references.
        citation_library: Optional citation library used for uncited reference
            list entries.
        citation_numbers: Citation numbers keyed by citation key.
        citation_source_numbers: Citation numbers keyed by source identity.
        comments: Indexed inline comments.
        comment_numbers: Comment numbers keyed by comment identity.
        footnotes: Indexed footnote references.
        footnote_numbers: Footnote numbers keyed by footnote identity.
        footnote_anchors: Generated-list anchors keyed by footnote identity.
        footnote_stream_counts: Latest footnote number keyed by stream name.
        headings: Indexed heading entries.
        heading_numbers: Heading numbers keyed by heading identity.
        heading_anchors: Heading anchors keyed by heading identity.
        paragraph_numbers: Paragraph numbers keyed by paragraph identity.
        equation_numbers: Equation numbers keyed by equation identity.
        code_block_numbers: Code-block numbers keyed by code block identity.
        box_numbers: Box numbers keyed by box identity.
        countables: Indexed theorem-like countable blocks.
        countable_numbers: Countable block numbers keyed by block identity.
        countable_counters: Latest counter value keyed by countable kind.
        block_anchors: Stable anchors keyed by block identity.
        generated_scopes: Ancestor scopes keyed by generated block identity.

    Examples:
        ```python
        from oodocs import Document, Table
        from oodocs.layout.indexing import build_render_index

        table = Table(["Metric"], [["Accuracy"]], caption="Evaluation metrics")
        index = build_render_index(Document("Report", table))
        assert index.table_number(table) == 1
        ```
    """

    tables: list[CaptionEntry] = field(default_factory=list)
    figures: list[CaptionEntry] = field(default_factory=list)
    table_numbers: dict[int, int] = field(default_factory=dict)
    figure_numbers: dict[int, int] = field(default_factory=dict)
    subfigure_labels: dict[int, str] = field(default_factory=dict)
    subfigure_reference_labels: dict[int, str] = field(default_factory=dict)
    subtable_labels: dict[int, str] = field(default_factory=dict)
    subtable_reference_labels: dict[int, str] = field(default_factory=dict)
    citations: list[CitationReferenceEntry] = field(default_factory=list)
    citation_library: CitationLibrary | None = None
    citation_numbers: dict[str, int] = field(default_factory=dict)
    citation_source_numbers: dict[int, int] = field(default_factory=dict)
    comments: list[CommentReferenceEntry] = field(default_factory=list)
    comment_numbers: dict[int, int] = field(default_factory=dict)
    footnotes: list[FootnoteReferenceEntry] = field(default_factory=list)
    footnote_numbers: dict[int, int] = field(default_factory=dict)
    footnote_anchors: dict[int, str] = field(default_factory=dict)
    footnote_stream_counts: dict[str, int] = field(default_factory=dict)
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
    generated_scopes: dict[int, EntryScope] = field(default_factory=dict)

    def scoped_headings(self, block: TableOfContents) -> list[HeadingEntry]:
        """Return TOC headings visible to ``block`` after scope filtering.

        Args:
            block: Table of contents block requesting scoped entries.

        Returns:
            Heading entries visible to the block.
        """

        return [
            entry
            for entry in self.headings
            if block.includes_level(entry.level)
            and self._entry_in_scope(entry.scope, block.scope, self.generated_scope(block))
        ]

    def scoped_tables(self, block: ListOfTables) -> list[CaptionEntry]:
        """Return table-list entries visible to ``block`` after scope filtering.

        Args:
            block: List of tables block requesting scoped entries.

        Returns:
            Table caption entries visible to the block.
        """

        return [
            entry
            for entry in self.tables
            if self._entry_in_scope(entry.scope, block.scope, self.generated_scope(block))
        ]

    def scoped_figures(self, block: ListOfFigures) -> list[CaptionEntry]:
        """Return figure-list entries visible to ``block`` after scope filtering.

        Args:
            block: List of figures block requesting scoped entries.

        Returns:
            Figure caption entries visible to the block.
        """

        return [
            entry
            for entry in self.figures
            if self._entry_in_scope(entry.scope, block.scope, self.generated_scope(block))
        ]

    def scoped_algorithms(self, block: ListOfAlgorithms) -> list[CountableEntry]:
        """Return algorithm-list entries visible to ``block`` after scope filtering.

        Args:
            block: List of algorithms block requesting scoped entries.

        Returns:
            Algorithm entries visible to the block.
        """

        return [
            entry
            for entry in self.countables
            if entry.counter == "algorithm"
            and self._entry_in_scope(entry.scope, block.scope, self.generated_scope(block))
        ]

    def reference_entries(
        self,
        block: ListOfReferences,
        *,
        reference_sort: str = "citation",
    ) -> list[CitationReferenceEntry]:
        """Return reference-list entries after uncited and sort policy.

        Args:
            block: Reference list block requesting entries.
            reference_sort: Theme-level sort style.

        Returns:
            Citation entries to display in the generated reference list.
        """

        entries = list(self.citations)
        if block.include_uncited and self.citation_library is not None:
            seen_keys = {entry.source.key for entry in entries if entry.source.key is not None}
            seen_sources = {id(entry.source) for entry in entries}
            next_number = len(entries) + 1
            for source in self.citation_library.entries.values():
                if id(source) in seen_sources or (source.key is not None and source.key in seen_keys):
                    continue
                entries.append(
                    CitationReferenceEntry(
                        number=next_number,
                        source=source,
                        anchor=f"citation_{next_number}",
                    )
                )
                next_number += 1
                seen_sources.add(id(source))
                if source.key is not None:
                    seen_keys.add(source.key)

        sort_style = block.sort_style(reference_sort)
        if sort_style == "citation":
            return entries
        return sorted(entries, key=lambda entry: _reference_entry_sort_key(entry, sort_style))

    def generated_scope(self, block: object) -> EntryScope:
        """Return the ancestor scope where a generated block appears.

        Args:
            block: Generated list block to look up.

        Returns:
            Ancestor scope where the generated block appears.
        """

        return self.generated_scopes.get(id(block), EntryScope())

    def _entry_in_scope(
        self,
        entry_scope: EntryScope,
        requested_scope: GeneratedListScope,
        generated_scope: EntryScope,
    ) -> bool:
        if requested_scope == "document":
            return True
        if requested_scope == "part":
            return (
                generated_scope.part_id is not None
                and entry_scope.part_id == generated_scope.part_id
            )
        if requested_scope == "chapter":
            return (
                generated_scope.chapter_id is not None
                and entry_scope.chapter_id == generated_scope.chapter_id
            )
        if requested_scope == "section":
            if not generated_scope.heading_path:
                return False
            return generated_scope.heading_path[-1] in entry_scope.heading_path
        return False

    def table_number(self, table: Table | SubTable | SubTableGroup) -> int | None:
        """Return the assigned table number for a captioned table.

        Args:
            table: Table to look up.

        Returns:
            Assigned table number, or ``None`` when uncaptioned.

        Examples:
            ```python
            number = render_index.table_number(table)
            ```
        """

        return self.table_numbers.get(id(table))

    def figure_number(self, figure: Figure | SubFigure | SubFigureGroup) -> int | None:
        """Return the assigned figure number for a captioned figure.

        Args:
            figure: Figure, subfigure, or subfigure group to look up.

        Returns:
            Assigned figure number, or ``None`` when uncaptioned.

        Examples:
            ```python
            number = render_index.figure_number(figure)
            ```
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

    def subfigure_reference_label(self, subfigure: SubFigure) -> str | None:
        """Return the formatted child suffix for a subfigure reference.

        Args:
            subfigure: Subfigure to look up.

        Returns:
            Formatted subfigure reference suffix, or ``None`` when unanchored.
        """

        return self.subfigure_reference_labels.get(id(subfigure))

    def subtable_label(self, subtable: SubTable) -> str | None:
        """Return the assigned label for a subtable inside a numbered group.

        Args:
            subtable: Subtable to look up.

        Returns:
            Assigned subtable label, or ``None`` when unanchored.
        """

        return self.subtable_labels.get(id(subtable))

    def subtable_reference_label(self, subtable: SubTable) -> str | None:
        """Return the formatted child suffix for a subtable reference.

        Args:
            subtable: Subtable to look up.

        Returns:
            Formatted subtable reference suffix, or ``None`` when unanchored.
        """

        return self.subtable_reference_labels.get(id(subtable))

    def citation_number(self, target: CitationSource | str) -> int:
        """Return the assigned citation number for a source or key.

        Args:
            target: Citation source object or key.

        Returns:
            Assigned citation number.

        Raises:
            OODocsError: If the target was not indexed.

        Examples:
            ```python
            number = render_index.citation_number("smith2024")
            ```
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

        Examples:
            ```python
            entry = render_index.citation_entry("smith2024")
            ```
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

    def footnote_anchor(self, target: Footnote) -> str:
        """Return the generated-list anchor for a footnote.

        Args:
            target: Footnote fragment to look up.

        Returns:
            Stable anchor used by HTML footnote references.

        Raises:
            OODocsError: If the target was not indexed.
        """

        if id(target) not in self.footnote_anchors:
            raise OODocsError(f"Unknown footnote target: {target.value!r}")
        return self.footnote_anchors[id(target)]

    def heading_number(self, target: object) -> str | None:
        """Return the numbering label assigned to a section heading.

        Args:
            target: Heading block to look up.

        Returns:
            Heading number label, or ``None`` when unnumbered.
        """

        return self.heading_numbers.get(id(target))

    def table_anchor(self, table: Table | SubTable | SubTableGroup) -> str | None:
        """Return the bookmark name for a captioned table.

        Args:
            table: Table to look up.

        Returns:
            Table anchor, or ``None`` when uncaptioned.
        """

        number = self.table_number(table)
        if number is None:
            return None
        if isinstance(table, SubTable):
            label = self.subtable_label(table)
            if label is not None:
                return f"table_{number}_{label}"
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

        Examples:
            ```python
            anchor = render_index.citation_anchor("smith2024")
            ```
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

    def anchors(self) -> set[str]:
        """Return all internal anchor names generated for this document.

        Returns:
            Heading, block, caption, subcaption, citation, and countable anchors.
        """

        anchors = set(self.heading_anchors.values()) | set(self.block_anchors.values())
        anchors.update(entry.anchor for entry in self.tables)
        anchors.update(entry.anchor for entry in self.figures)
        anchors.update(entry.anchor for entry in self.citations)
        anchors.update(entry.anchor for entry in self.countables)
        for entry in self.tables:
            if isinstance(entry.block, SubTableGroup):
                for subtable in entry.block.subtables:
                    anchor = self.table_anchor(subtable)
                    if anchor is not None:
                        anchors.add(anchor)
        for entry in self.figures:
            if isinstance(entry.block, SubFigureGroup):
                for subfigure in entry.block.subfigures:
                    anchor = self.figure_anchor(subfigure)
                    if anchor is not None:
                        anchors.add(anchor)
        return anchors


def resolve_block_reference(
    target: object,
    theme: Theme,
    render_index: RenderIndex,
) -> ResolvedBlockReference:
    """Resolve a document object reference into label, value, and anchor.

    Args:
        target: Document object to reference.
        theme: Theme used to resolve table and figure reference labels.
        render_index: Render index containing assigned numbers and anchors.

    Returns:
        Resolved reference label, value, and anchor.

    Raises:
        OODocsError: If the target is unsupported or has not been indexed.
    """

    if isinstance(target, (Table, SubTable, SubTableGroup)):
        number = render_index.table_number(target)
        if number is None:
            raise OODocsError(
                "Table references require the target table to have a caption and be included in the document"
            )
        label = theme.resolve_caption_label("table", "reference")
        if isinstance(target, SubTable):
            subtable_label = render_index.subtable_reference_label(target)
            if subtable_label is None:
                raise OODocsError(
                    "Subtable references require the target subtable to belong to a captioned SubTableGroup"
                )
            return ResolvedBlockReference(
                label,
                f"{number}{subtable_label}",
                render_index.table_anchor(target),
            )
        return ResolvedBlockReference(label, str(number), render_index.table_anchor(target))

    if isinstance(target, (Figure, SubFigure, SubFigureGroup)):
        number = render_index.figure_number(target)
        if number is None:
            raise OODocsError(
                "Figure references require the target figure to have a caption and be included in the document"
            )
        label = theme.resolve_caption_label("figure", "reference")
        if isinstance(target, SubFigure):
            subfigure_label = render_index.subfigure_label(target)
            if subfigure_label is None:
                raise OODocsError(
                    "Subfigure references require the target subfigure to belong to a captioned SubFigureGroup"
                )
            reference_label = render_index.subfigure_reference_label(target)
            return ResolvedBlockReference(
                label,
                f"{number}{reference_label or f'({subfigure_label})'}",
                render_index.figure_anchor(target),
            )
        return ResolvedBlockReference(label, str(number), render_index.figure_anchor(target))

    if isinstance(target, Part):
        number_label = render_index.heading_number(target)
        if number_label is None:
            raise OODocsError("Part references require the target part to be numbered and included in the document")
        return ResolvedBlockReference("", number_label, render_index.heading_anchor(target))

    if isinstance(target, Section):
        number_label = render_index.heading_number(target)
        if number_label is None:
            raise OODocsError("Section references require the target section to be numbered and included in the document")
        label = "Chapter" if target.level == 1 else "Section"
        return ResolvedBlockReference(label, number_label, render_index.heading_anchor(target))

    if isinstance(target, Equation):
        number = render_index.equation_number(target)
        if number is None:
            raise OODocsError(
                "Equation references require the target equation to be numbered and included in the document, "
                "or the reference must provide a custom label"
            )
        return ResolvedBlockReference(
            target.reference_label,
            str(number),
            render_index.block_anchor(target),
        )

    if isinstance(target, Paragraph):
        number = render_index.paragraph_number(target)
        if number is None:
            raise OODocsError("Paragraph references require the target paragraph to be included in the document")
        return ResolvedBlockReference("Paragraph", str(number), render_index.block_anchor(target))

    if isinstance(target, CodeBlock):
        number = render_index.code_block_number(target)
        if number is None:
            raise OODocsError("Code block references require the target code block to be included in the document")
        return ResolvedBlockReference("Code block", str(number), render_index.block_anchor(target))

    if isinstance(target, Box):
        number = render_index.box_number(target)
        if number is None:
            raise OODocsError("Box references require the target box to be included in the document")
        return ResolvedBlockReference("Box", str(number), render_index.block_anchor(target))

    if isinstance(target, CountableBlock):
        number = render_index.countable_number(target)
        if number is None:
            raise OODocsError(
                "CountableBlock references require the target to be numbered and included in the document, "
                "or the reference must provide a custom label"
            )
        return ResolvedBlockReference(
            target.reference_label,
            str(number),
            render_index.block_anchor(target),
        )

    raise OODocsError(f"Unsupported reference target: {type(target)!r}")


def reference_text_pieces(
    targets: Sequence[object],
    reference_format: ReferenceFormat,
    theme: Theme,
    render_index: RenderIndex,
    *,
    range_reference: bool = False,
) -> list[ReferenceTextPiece]:
    """Return text/link pieces for one or more object references.

    Args:
        targets: Document objects to reference.
        reference_format: Formatting options for labels and separators.
        theme: Theme used to resolve reference labels.
        render_index: Render index containing assigned numbers and anchors.
        range_reference: Whether to render the first and last target as a range.

    Returns:
        Text and link pieces for renderer-specific reference output.
    """

    resolved = [
        resolve_block_reference(target, theme, render_index)
        for target in targets
    ]
    if not resolved:
        return []
    if range_reference:
        return _wrap_reference_pieces(
            _range_reference_pieces(resolved[0], resolved[-1], reference_format),
            reference_format,
        )
    if len(resolved) == 1:
        return _wrap_reference_pieces(
            [ReferenceTextPiece(resolved[0].text(reference_format), resolved[0].anchor)],
            reference_format,
        )
    return _wrap_reference_pieces(
        _multi_reference_pieces(resolved, reference_format),
        reference_format,
    )


def _multi_reference_pieces(
    resolved: Sequence[ResolvedBlockReference],
    reference_format: ReferenceFormat,
) -> list[ReferenceTextPiece]:
    labels = {
        _effective_reference_label(item.label, reference_format)
        for item in resolved
    }
    if len(labels) == 1 and next(iter(labels)):
        label = _plural_reference_label(next(iter(labels)), reference_format)
        pieces = [ReferenceTextPiece(_apply_reference_case(label, reference_format) + " ")]
        pieces.extend(
            _join_reference_value_pieces(resolved, reference_format)
        )
        return pieces
    return _join_reference_text_pieces(resolved, reference_format)


def _range_reference_pieces(
    start: ResolvedBlockReference,
    end: ResolvedBlockReference,
    reference_format: ReferenceFormat,
) -> list[ReferenceTextPiece]:
    start_label = _effective_reference_label(start.label, reference_format)
    end_label = _effective_reference_label(end.label, reference_format)
    if start_label == end_label and start_label:
        label = _plural_reference_label(start_label, reference_format)
        return [
            ReferenceTextPiece(_apply_reference_case(label, reference_format) + " "),
            ReferenceTextPiece(start.value, start.anchor),
            ReferenceTextPiece(reference_format.range_separator),
            ReferenceTextPiece(end.value, end.anchor),
        ]
    return [
        ReferenceTextPiece(_format_reference_text(start, reference_format), start.anchor),
        ReferenceTextPiece(reference_format.range_separator),
        ReferenceTextPiece(_format_reference_text(end, reference_format), end.anchor),
    ]


def _join_reference_value_pieces(
    resolved: Sequence[ResolvedBlockReference],
    reference_format: ReferenceFormat,
) -> list[ReferenceTextPiece]:
    pieces: list[ReferenceTextPiece] = []
    for index, item in enumerate(resolved):
        if index:
            pieces.append(ReferenceTextPiece(_reference_separator(index, len(resolved), reference_format)))
        pieces.append(ReferenceTextPiece(item.value, item.anchor))
    return pieces


def _join_reference_text_pieces(
    resolved: Sequence[ResolvedBlockReference],
    reference_format: ReferenceFormat,
) -> list[ReferenceTextPiece]:
    pieces: list[ReferenceTextPiece] = []
    for index, item in enumerate(resolved):
        if index:
            pieces.append(ReferenceTextPiece(_reference_separator(index, len(resolved), reference_format)))
        pieces.append(ReferenceTextPiece(_format_reference_text(item, reference_format), item.anchor))
    return pieces


def _wrap_reference_pieces(
    pieces: list[ReferenceTextPiece],
    reference_format: ReferenceFormat,
) -> list[ReferenceTextPiece]:
    if reference_format.prefix:
        pieces.insert(0, ReferenceTextPiece(reference_format.prefix))
    if reference_format.suffix:
        pieces.append(ReferenceTextPiece(reference_format.suffix))
    return pieces


def _format_reference_text(
    reference: ResolvedBlockReference,
    reference_format: ReferenceFormat,
) -> str:
    label = _effective_reference_label(reference.label, reference_format)
    label = _apply_reference_case(label, reference_format)
    if not label:
        return reference.value
    return f"{label} {reference.value}"


def _effective_reference_label(
    label: str,
    reference_format: ReferenceFormat,
) -> str:
    return reference_format.label if reference_format.label is not None else label


def _plural_reference_label(
    label: str,
    reference_format: ReferenceFormat,
) -> str:
    if reference_format.plural_label is not None:
        return reference_format.plural_label
    if label.endswith(".") or label.endswith("s"):
        return label
    return f"{label}s"


def _apply_reference_case(
    label: str,
    reference_format: ReferenceFormat,
) -> str:
    if not reference_format.capitalized or not label:
        return label
    return label[:1].upper() + label[1:]


def _reference_separator(
    index: int,
    total: int,
    reference_format: ReferenceFormat,
) -> str:
    if index == total - 1 and total > 1:
        return reference_format.last_separator
    return reference_format.separator


def _reference_entry_sort_key(
    entry: CitationReferenceEntry,
    sort_style: str,
) -> tuple[object, ...]:
    normalized = normalize_reference_sort(sort_style)
    source = entry.source
    if normalized == "author":
        author = source.authors[0] if source.authors else source.organization or ""
        return (not bool(author), author.lower(), source.year or "", source.title.lower(), entry.number)
    if normalized == "year":
        year = source.year or ""
        return (not bool(year), year, source.title.lower(), entry.number)
    if normalized == "title":
        return (source.title.lower(), entry.number)
    if normalized == "key":
        key = source.key or ""
        return (not bool(key), key.lower(), source.title.lower(), entry.number)
    return (entry.number,)


def build_render_index(document: Document) -> RenderIndex:
    """Scan a document tree and assign render-time numbering.

    Args:
        document: Document to index.

    Returns:
        Render index containing numbering, anchors, and generated-page entries.

    Examples:
        ```python
        from oodocs import Document, Section
        from oodocs.layout.indexing import build_render_index

        section = Section("Results", "All checks passed.")
        index = build_render_index(Document("Report", section))
        assert index.heading_number(section) == "1"
        ```
    """

    render_index = RenderIndex()
    render_index.citation_library = document.citations
    _index_blocks(
        document.body.children,
        render_index,
        document.citations,
        document.settings.theme,
        heading_counters=[],
        part_counter=[0],
        scope=EntryScope(),
        appendix=False,
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
    custom_anchor = getattr(block, "anchor", None)
    anchor = str(custom_anchor) if custom_anchor else f"heading_{len(render_index.heading_anchors) + 1}"
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
    scope: EntryScope,
    appendix: bool,
) -> None:
    for block in blocks:
        if isinstance(block, Paragraph):
            if id(block) not in render_index.paragraph_numbers:
                render_index.paragraph_numbers[id(block)] = len(render_index.paragraph_numbers) + 1
            _register_block_anchor(render_index, block, "paragraph")
            if block.title is not None:
                _index_inlines(block.title, render_index, citations)
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
                    scope=scope,
                    appendix=appendix,
                )
            continue
        if isinstance(block, CodeBlock):
            if id(block) not in render_index.code_block_numbers:
                render_index.code_block_numbers[id(block)] = len(render_index.code_block_numbers) + 1
            _register_block_anchor(render_index, block, "code")
            if block.caption is not None:
                _index_inlines(block.caption.content, render_index, citations)
            continue
        if isinstance(block, Equation):
            if block.numbered and id(block) not in render_index.equation_numbers:
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
                scope=scope,
                appendix=appendix,
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
                        scope=scope,
                    )
                )
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=heading_counters,
                part_counter=part_counter,
                scope=scope,
                appendix=appendix,
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
                scope=scope,
                appendix=appendix,
            )
            continue
        if isinstance(block, Appendix):
            _index_inlines(block.title, render_index, citations)
            anchor = _register_heading_anchor(render_index, block) if block.toc else None
            if block.toc:
                render_index.headings.append(
                    HeadingEntry(
                        level=block.level,
                        title=block.title,
                        number=None,
                        anchor=anchor,
                        scope=scope,
                    )
                )
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=[],
                part_counter=part_counter,
                scope=scope.with_part(block),
                appendix=True,
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
                        scope=scope,
                    )
                )
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=heading_counters,
                part_counter=part_counter,
                scope=scope.with_part(block),
                appendix=appendix,
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
                number_label = (
                    theme.format_appendix_heading_label(current_counters[: block.level])
                    if appendix
                    else theme.format_heading_label(
                        current_counters[: block.level],
                        block.heading_style,
                    )
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
                        scope=scope,
                    )
                )
            _index_blocks(
                block.children,
                render_index,
                citations,
                theme,
                heading_counters=current_counters,
                part_counter=part_counter,
                scope=scope.with_section(block),
                appendix=appendix,
            )
            continue
        if isinstance(
            block,
            (
                ListOfTables,
                ListOfFigures,
                ListOfAlgorithms,
                ListOfReferences,
                ListOfComments,
                ListOfFootnotes,
                TableOfContents,
            ),
        ):
            if block.title is not None:
                _index_inlines(block.title, render_index, citations)
            render_index.generated_scopes[id(block)] = scope
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
                        scope=scope,
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
                        scope=scope,
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
                        scope=scope,
                    )
                )
                render_index.figure_numbers[id(block)] = number
                for index, subfigure in enumerate(block.subfigures):
                    label = block.label_for_index(index)
                    render_index.figure_numbers[id(subfigure)] = number
                    render_index.subfigure_labels[id(subfigure)] = label
                    render_index.subfigure_reference_labels[id(subfigure)] = (
                        block.formatted_reference_label_for_index(index)
                    )
            continue
        if isinstance(block, SubTableGroup):
            for subtable in block.subtables:
                table = subtable.table
                for header_row in table.header_rows:
                    for header in header_row:
                        _index_inlines(header.content.content, render_index, citations)
                for row in table.rows:
                    for cell in row:
                        _index_inlines(cell.content.content, render_index, citations)
                if subtable.caption is not None:
                    _index_inlines(subtable.caption.content, render_index, citations)
            if block.caption is not None:
                _index_inlines(block.caption.content, render_index, citations)
                number = len(render_index.tables) + 1
                render_index.tables.append(
                    CaptionEntry(
                        number=number,
                        block=block,
                        anchor=f"table_{number}",
                        scope=scope,
                    )
                )
                render_index.table_numbers[id(block)] = number
                for index, subtable in enumerate(block.subtables):
                    label = block.label_for_index(index)
                    render_index.table_numbers[id(subtable)] = number
                    render_index.subtable_labels[id(subtable)] = label
                    render_index.subtable_reference_labels[id(subtable)] = (
                        block.formatted_reference_label_for_index(index)
                    )


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
            number = render_index.footnote_stream_counts.get(fragment.stream, 0) + 1
            render_index.footnote_stream_counts[fragment.stream] = number
            anchor = f"footnote_{len(render_index.footnotes) + 1}"
            render_index.footnotes.append(
                FootnoteReferenceEntry(
                    number=number,
                    footnote=fragment,
                    stream=fragment.stream,
                    anchor=anchor,
                )
            )
            render_index.footnote_numbers[id(fragment)] = number
            render_index.footnote_anchors[id(fragment)] = anchor
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
    "EntryScope",
    "FootnoteReferenceEntry",
    "HeadingEntry",
    "ReferenceTextPiece",
    "RenderIndex",
    "ResolvedBlockReference",
    "build_render_index",
    "reference_text_pieces",
    "resolve_block_reference",
]
