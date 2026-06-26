"""Document template presets for common manuscript-shaped documents."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from oodocs.components.base import Block, BlockInput, coerce_blocks
from oodocs.components.blocks import Paragraph, Section
from oodocs.components.generated import ReferenceList, TableOfContents
from oodocs.components.inline import InlineInput, Text, bold
from oodocs.components.people import AuthorInput, AuthorLayout
from oodocs.components.references import CitationLibrary, CitationSource
from oodocs.document import Document
from oodocs.layout.theme import (
    BlockDefaults,
    CaptionDefaults,
    GeneratedContentDefaults,
    PageNumberDefaults,
    TitleMatterDefaults,
    TypographyDefaults,
    Theme,
)
from oodocs.settings import DocumentSettings, PageMargins, PageSize


SectionContentInput = str | Block | Sequence[BlockInput]
AbstractInput = SectionContentInput
StatementInput = SectionContentInput


def _default_journal_theme() -> Theme:
    """Return manuscript defaults suitable for a conventional journal draft."""

    return Theme(
        TypographyDefaults(
            body_font_name="Times New Roman",
            body_font_size=11.0,
            title_font_size=16.0,
            heading_sizes=(13.0, 12.0, 11.0, 11.0),
            caption_font_size=10.0,
        ),
        CaptionDefaults(
            caption_alignment="left",
            table_caption_position="above",
            figure_caption_position="below",
        ),
        GeneratedContentDefaults(
            generated_heading_level=1,
            generated_content_page_breaks=False,
        ),
        PageNumberDefaults(
            show_page_numbers=True,
            page_number_alignment="center",
        ),
        TitleMatterDefaults(
            title_alignment="center",
            subtitle_alignment="center",
            author_alignment="center",
            affiliation_alignment="center",
            author_detail_alignment="center",
        ),
        BlockDefaults(
            paragraph_text_alignment="justify",
            table_alignment="center",
            figure_alignment="center",
        ),
    )


@dataclass(slots=True)
class ManuscriptSection:
    """A lightweight section descriptor accepted by article templates.

    Attributes:
        title: Section title inline content.
        children: Section child blocks.
        level: Heading level.
        numbered: Whether the section should be numbered.

    Examples:
        ```python
        from oodocs import Paragraph
        from oodocs.presets import JournalArticleTemplate, ManuscriptSection

        section = ManuscriptSection("Methods", [Paragraph("Cohort details.")])
        document = JournalArticleTemplate().build("Clinical Study", sections=[section])
        ```
    """

    title: InlineInput
    children: Sequence[BlockInput] = ()
    level: int = 1
    numbered: bool = True

    def to_section(self) -> Section:
        """Return a concrete section block.

        Returns:
            ``Section`` built from this descriptor.

        Examples:
            ```python
            concrete = ManuscriptSection("Results", ["Model accuracy improved."]).to_section()
            ```
        """

        return Section(
            self.title,
            *self.children,
            level=self.level,
            numbered=self.numbered,
        )


ArticleSectionInput = Section | ManuscriptSection | tuple[InlineInput, Sequence[BlockInput]]


@dataclass(slots=True)
class JournalArticleTemplate:
    """Build a journal-style manuscript from content-oriented inputs.

    Attributes:
        name: Template display name.
        theme: Document theme used by generated documents.
        page_size: Default page size.
        page_margins: Default page margins.
        author_layout: Default author title-matter layout.
        include_contents: Whether to include a table of contents by default.
        include_references: Whether to include a references page by default.
        cover_page: Whether to render title matter on a cover page by default.

    Examples:
        Build a compact article from content-oriented inputs:

        ```python
        from oodocs.presets import JournalArticleTemplate

        document = JournalArticleTemplate().build(
            "Clinical Benchmark",
            abstract="We compared model outputs across held-out tasks.",
            sections=[("Results", ["The calibrated model reduced error."])],
            keywords=["benchmark", "validation"],
        )
        ```

        Reuse a configured template for multiple manuscripts:

        ```python
        from oodocs import Author
        from oodocs.presets import JournalArticleTemplate

        template = JournalArticleTemplate(include_contents=True, cover_page=True)
        document = template.build(
            "Release Evidence",
            abstract="Validation evidence for the release.",
            sections=[("Evaluation", ["All required checks passed."])],
            authors=[Author("Jane Doe", affiliations=["Example Lab"])],
        )
        ```

    Notes:
        The template produces a normal ``Document``. Callers can still append
        blocks, validate, or render the returned document with the standard
        document APIs.

    See Also:
        ``ManuscriptSection`` for reusable section descriptors and
        ``DocumentSettings`` for the settings object created by the template.
    """

    name: str = "Journal article"
    theme: Theme = field(default_factory=_default_journal_theme)
    page_size: PageSize = field(default_factory=PageSize.a4)
    page_margins: PageMargins = field(default_factory=PageMargins)
    author_layout: AuthorLayout = field(default_factory=AuthorLayout)
    include_contents: bool = False
    include_references: bool = True
    cover_page: bool = False

    def build(
        self,
        title: str,
        *,
        abstract: AbstractInput | None = None,
        sections: Sequence[ArticleSectionInput] = (),
        authors: Sequence[AuthorInput] | None = None,
        keywords: Sequence[str] | None = None,
        subtitle: InlineInput | None = None,
        acknowledgements: StatementInput | None = None,
        data_availability: StatementInput | None = None,
        summary: str | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        include_contents: bool | None = None,
        include_references: bool | None = None,
        cover_page: bool | None = None,
    ) -> Document:
        """Build a document from manuscript-shaped inputs.

        Args:
            title: Document title.
            abstract: Optional abstract content.
            sections: Authored manuscript sections.
            authors: Optional document authors.
            keywords: Optional keyword list.
            subtitle: Optional subtitle inline content.
            acknowledgements: Optional acknowledgements content.
            data_availability: Optional data availability statement content.
            summary: Optional metadata summary. Defaults to ``title``.
            citations: Optional citation library, citation sources, or BibTeX.
            include_contents: Override for table-of-contents inclusion.
            include_references: Override for references-page inclusion.
            cover_page: Override for cover-page title matter.

        Returns:
            Built document.

        Examples:
            ```python
            template = JournalArticleTemplate(include_contents=True)
            document = template.build(
                "Release Evidence",
                abstract="This report summarizes validation evidence.",
                sections=[("Evaluation", ["All required checks passed."])],
            )
            ```
        """

        include_contents_value = self.include_contents if include_contents is None else include_contents
        include_references_value = self.include_references if include_references is None else include_references

        children: list[BlockInput] = []
        if include_contents_value:
            children.append(TableOfContents(show_page_numbers=False, max_level=3))
        if abstract is not None:
            children.append(
                Section(
                    "Abstract",
                    *self._abstract_blocks(abstract),
                    level=1,
                    numbered=False,
                )
            )
        if keywords:
            children.append(
                Paragraph(
                    bold("Keywords: "),
                    Text(", ".join(keywords)),
                    space_after=18.0,
                    keep_with_next=True,
                )
            )
        children.extend(self._coerce_sections(sections))
        if acknowledgements is not None:
            children.append(self._statement_section("Acknowledgements", acknowledgements))
        if data_availability is not None:
            children.append(self._statement_section("Data Availability", data_availability))
        if include_references_value:
            children.append(ReferenceList())

        settings = DocumentSettings(
            authors=authors,
            author_layout=self.author_layout,
            subtitle=subtitle,
            summary=summary or title,
            cover_page=self.cover_page if cover_page is None else cover_page,
            page_size=self.page_size,
            page_margins=self.page_margins,
            theme=self.theme,
        )
        return Document(title, *children, settings=settings, citations=citations)

    def _abstract_blocks(self, abstract: AbstractInput) -> list[BlockInput]:
        return self._content_blocks(abstract)

    def _content_blocks(self, content: SectionContentInput) -> list[BlockInput]:
        if isinstance(content, Block):
            return [content]
        if isinstance(content, str):
            return [Paragraph(content)]
        return coerce_blocks(content)

    def _statement_section(self, title: str, content: StatementInput) -> Section:
        return Section(
            title,
            *self._content_blocks(content),
            level=1,
            numbered=False,
        )

    def _coerce_sections(self, sections: Sequence[ArticleSectionInput]) -> list[Section]:
        return [self._coerce_section(section) for section in sections]

    def _coerce_section(self, section: ArticleSectionInput) -> Section:
        if isinstance(section, Section):
            return section
        if isinstance(section, ManuscriptSection):
            return section.to_section()
        title, children = section
        return Section(title, *children, level=1)


__all__ = [
    "JournalArticleTemplate",
    "ManuscriptSection",
]
