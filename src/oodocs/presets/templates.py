"""Document template presets for common manuscript-shaped documents."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from oodocs.components.base import Block, BlockInput, coerce_blocks
from oodocs.components.blocks import Appendix, Chapter, Paragraph, Part, Section
from oodocs.components.generated import ListOfReferences, TableOfContents
from oodocs.components.inline import InlineInput, Text, bold
from oodocs.components.people import AuthorInput, AuthorLayout
from oodocs.components.positioning import PositionedItem, Shape, TextBox
from oodocs.components.references import CitationLibrary, CitationSource
from oodocs.core import normalize_color
from oodocs.document import Document
from oodocs.styles import (
    BlockDefaults,
    CaptionDefaults,
    GeneratedContentDefaults,
    PageNumberDefaults,
    StrokeStyle,
    TitleMatterDefaults,
    TypographyDefaults,
    Theme,
)
from oodocs.settings import DocumentMetadata, DocumentSettings, PageLayout, PageMargins, PageSize


SectionContentInput = str | Block | Sequence[BlockInput]
AbstractInput = SectionContentInput
StatementInput = SectionContentInput


def _default_journal_theme() -> Theme:
    """Return manuscript defaults suitable for a conventional journal draft."""

    return Theme(
        typography=TypographyDefaults(
            body_font_name="Times New Roman",
            body_font_size=11.0,
            title_font_size=16.0,
            heading_sizes=(13.0, 12.0, 11.0, 11.0),
            caption_font_size=10.0,
        ),
        captions=CaptionDefaults(
            caption_text_alignment="left",
            table_caption_position="above",
            figure_caption_position="below",
        ),
        generated_content=GeneratedContentDefaults(
            generated_heading_level=1,
            generated_content_page_breaks=False,
        ),
        page_numbers=PageNumberDefaults(
            show_page_numbers=True,
            page_number_alignment="center",
        ),
        title_matter=TitleMatterDefaults(
            title_text_alignment="center",
            subtitle_text_alignment="center",
            author_text_alignment="center",
            affiliation_text_alignment="center",
            author_detail_text_alignment="center",
        ),
        blocks=BlockDefaults(
            paragraph_text_alignment="justify",
            table_block_alignment="center",
            figure_block_alignment="center",
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
ReportSectionInput = ArticleSectionInput
ManualSectionInput = ArticleSectionInput
BookChapterInput = Section | ManuscriptSection | tuple[InlineInput, Sequence[BlockInput]]
BookPartInput = Part | tuple[InlineInput, Sequence[BookChapterInput]]
MatterInput = BlockInput | Sequence[BlockInput]


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
            children.append(ListOfReferences())

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


def _default_report_theme() -> Theme:
    """Return defaults for technical report and software manual templates."""

    return Theme(
        typography=TypographyDefaults(
            body_font_name="Arial",
            body_font_size=10.5,
            title_font_size=18.0,
            heading_sizes=(15.0, 13.0, 11.5, 11.0),
            caption_font_size=9.5,
        ),
        captions=CaptionDefaults(
            caption_text_alignment="left",
            table_caption_position="above",
            figure_caption_position="below",
        ),
        generated_content=GeneratedContentDefaults(
            generated_heading_level=1,
            generated_content_page_breaks=True,
        ),
        page_numbers=PageNumberDefaults(
            show_page_numbers=True,
            page_number_alignment="right",
        ),
        title_matter=TitleMatterDefaults(
            title_text_alignment="left",
            subtitle_text_alignment="left",
            author_text_alignment="left",
            affiliation_text_alignment="left",
            author_detail_text_alignment="left",
        ),
        blocks=BlockDefaults(
            paragraph_text_alignment="justify",
            table_block_alignment="center",
            figure_block_alignment="center",
        ),
    )


def _default_book_theme() -> Theme:
    """Return defaults for book-like documents with front matter."""

    return Theme(
        typography=TypographyDefaults(
            body_font_name="Georgia",
            body_font_size=11.0,
            title_font_size=20.0,
            heading_sizes=(17.0, 14.0, 12.5, 11.5),
            caption_font_size=10.0,
        ),
        captions=CaptionDefaults(
            caption_text_alignment="left",
            table_caption_position="above",
            figure_caption_position="below",
        ),
        generated_content=GeneratedContentDefaults(
            generated_heading_level=1,
            generated_content_page_breaks=True,
        ),
        page_numbers=PageNumberDefaults(
            show_page_numbers=True,
            page_number_alignment="center",
        ),
        title_matter=TitleMatterDefaults(
            title_text_alignment="center",
            subtitle_text_alignment="center",
            author_text_alignment="center",
            affiliation_text_alignment="center",
            author_detail_text_alignment="center",
        ),
        blocks=BlockDefaults(
            paragraph_text_alignment="justify",
            table_block_alignment="center",
            figure_block_alignment="center",
        ),
    )


def _default_cover_theme() -> Theme:
    """Return title-matter defaults for a simple cover page preset."""

    return Theme(
        typography=TypographyDefaults(
            body_font_name="Arial",
            body_font_size=10.5,
            title_font_size=22.0,
            heading_sizes=(15.0, 13.0, 11.5, 11.0),
            caption_font_size=9.5,
        ),
        page_numbers=PageNumberDefaults(
            show_page_numbers=True,
            page_number_alignment="right",
        ),
        title_matter=TitleMatterDefaults(
            title_text_alignment="left",
            subtitle_text_alignment="left",
            author_text_alignment="left",
            affiliation_text_alignment="left",
            author_detail_text_alignment="left",
        ),
        blocks=BlockDefaults(
            page_background_color="F8FAFC",
            paragraph_text_alignment="justify",
        ),
    )


def _default_cover_page_layout() -> PageLayout:
    return PageLayout(
        PageSize.a4(),
        PageMargins.symmetric(vertical=1.0, horizontal=1.15, unit="in"),
    )


def _template_content_blocks(content: MatterInput | None) -> list[Block]:
    if content is None:
        return []
    if isinstance(content, Block):
        return [content]
    if isinstance(content, str):
        return [Paragraph(content)]
    return coerce_blocks(content)


def _statement_section(title: str, content: MatterInput) -> Section:
    return Section(title, *_template_content_blocks(content), level=1, numbered=False)


def _keyword_paragraph(keywords: Sequence[str]) -> Paragraph:
    return Paragraph(
        bold("Keywords: "),
        Text(", ".join(keywords)),
        space_after=18.0,
        keep_with_next=True,
    )


def _coerce_report_section(section: ReportSectionInput) -> Section:
    if isinstance(section, Section):
        return section
    if isinstance(section, ManuscriptSection):
        return section.to_section()
    title, children = section
    return Section(title, *children, level=1)


def _coerce_report_sections(sections: Sequence[ReportSectionInput]) -> list[Section]:
    return [_coerce_report_section(section) for section in sections]


def _coerce_chapter(chapter: BookChapterInput) -> Section:
    if isinstance(chapter, Section):
        return chapter
    if isinstance(chapter, ManuscriptSection):
        return Chapter(
            chapter.title,
            *chapter.children,
            numbered=chapter.numbered,
            toc=chapter.numbered,
        )
    title, children = chapter
    return Chapter(title, *children)


def _coerce_chapters(chapters: Sequence[BookChapterInput]) -> list[Section]:
    return [_coerce_chapter(chapter) for chapter in chapters]


def _coerce_part(part: BookPartInput) -> Part:
    if isinstance(part, Part):
        return part
    title, chapters = part
    return Part(title, *_coerce_chapters(chapters))


def _coerce_parts(parts: Sequence[BookPartInput]) -> list[Part]:
    return [_coerce_part(part) for part in parts]


@dataclass(slots=True)
class CoverPagePreset:
    """Reusable cover-page settings for report-style documents.

    Attributes:
        name: Preset display name.
        accent_color: Accent color used by cover-only page decorations.
        muted_color: Secondary decoration color.
        footer_label: Optional small footer label on the cover page.
        page_layout: Page geometry used by generated settings.
        theme: Theme used by generated settings.
        author_layout: Structured author layout used by generated settings.

    Examples:
        ```python
        from oodocs import Author, Document, Paragraph
        from oodocs.presets import CoverPagePreset

        cover = CoverPagePreset.eplus_simple(footer_label="Internal review")
        document = Document(
            "Validation Report",
            Paragraph("Findings."),
            settings=cover.settings(
                subtitle="Release gate evidence",
                authors=[Author("QA Team")],
            ),
        )
        ```
    """

    name: str = "EPlusSimple cover"
    accent_color: str = "2563EB"
    muted_color: str = "64748B"
    footer_label: str | None = "EPlusSimple"
    page_layout: PageLayout = field(default_factory=_default_cover_page_layout)
    theme: Theme = field(default_factory=_default_cover_theme)
    author_layout: AuthorLayout = field(
        default_factory=lambda: AuthorLayout(
            mode="stacked",
            affiliation_label_format="{label}",
        )
    )

    def __post_init__(self) -> None:
        self.accent_color = normalize_color(self.accent_color) or "2563EB"
        self.muted_color = normalize_color(self.muted_color) or "64748B"
        if not isinstance(self.page_layout, PageLayout):
            raise TypeError("CoverPagePreset.page_layout must be a PageLayout")
        if not isinstance(self.theme, Theme):
            raise TypeError("CoverPagePreset.theme must be a Theme")
        if not isinstance(self.author_layout, AuthorLayout):
            raise TypeError("CoverPagePreset.author_layout must be an AuthorLayout")

    @classmethod
    def eplus_simple(
        cls,
        *,
        accent_color: str = "2563EB",
        muted_color: str = "64748B",
        footer_label: str | None = "EPlusSimple",
        page_layout: PageLayout | None = None,
        theme: Theme | None = None,
    ) -> CoverPagePreset:
        """Return the EPlusSimple-style cover preset.

        Args:
            accent_color: Cover accent color.
            muted_color: Secondary cover decoration color.
            footer_label: Optional footer label rendered only on the cover page.
            page_layout: Optional page geometry override.
            theme: Optional theme override.

        Returns:
            Configured cover page preset.
        """

        return cls(
            accent_color=accent_color,
            muted_color=muted_color,
            footer_label=footer_label,
            page_layout=page_layout or _default_cover_page_layout(),
            theme=theme or _default_cover_theme(),
        )

    def page_items(self) -> tuple[PositionedItem, ...]:
        """Return cover-scoped page decorations for this preset.

        Returns:
            Page-positioned items scoped to the cover page.
        """

        page_width = self.page_layout.page_width_in_inches("in")
        page_height = self.page_layout.page_height_in_inches("in")
        content_width = max(page_width - 1.45, 0.5)
        accent_height = max(page_height - 1.1, 0.5)
        items: list[PositionedItem] = [
            Shape.rect(
                x=0.55,
                y=0.55,
                width=0.09,
                height=accent_height,
                fill_color=self.accent_color,
                stroke=StrokeStyle.none(),
                unit="in",
                z_index=0,
                scope="cover",
            ),
            Shape.rect(
                x=0.72,
                y=0.55,
                width=content_width,
                height=0.025,
                fill_color=self.muted_color,
                stroke=StrokeStyle.none(),
                unit="in",
                z_index=0,
                scope="cover",
            ),
        ]
        if self.footer_label:
            items.append(
                TextBox(
                    self.footer_label,
                    x=0.72,
                    y=max(page_height - 0.85, 0.1),
                    width=content_width,
                    height=0.3,
                    font_size=8.0,
                    unit="in",
                    z_index=1,
                    scope="cover",
                )
            )
        return tuple(items)

    def settings(
        self,
        *,
        metadata: DocumentMetadata | None = None,
        metadata_author: str | None = None,
        summary: str | None = None,
        subtitle: InlineInput | None = None,
        authors: Sequence[AuthorInput] | None = None,
        page_items: Sequence[PositionedItem] | None = None,
        theme: Theme | None = None,
    ) -> DocumentSettings:
        """Return ``DocumentSettings`` configured for this cover preset.

        Args:
            metadata: Optional file/browser metadata.
            metadata_author: Optional file metadata author.
            summary: Optional document summary.
            subtitle: Optional visible subtitle.
            authors: Optional structured authors.
            page_items: Additional page items appended after preset items.
            theme: Optional theme override for the returned settings.

        Returns:
            Document settings with cover page enabled.
        """

        return DocumentSettings(
            metadata=metadata,
            metadata_author=metadata_author,
            summary=summary,
            subtitle=subtitle,
            authors=authors,
            author_layout=self.author_layout,
            cover_page=True,
            page_layout=self.page_layout,
            page_items=(*self.page_items(), *(page_items or ())),
            theme=theme or self.theme,
        )


@dataclass(slots=True)
class TechnicalReportTemplate:
    """Build a report-style document from front, main, and back matter.

    Attributes:
        name: Template display name.
        theme: Document theme used by generated reports.
        page_size: Default page size.
        page_margins: Default page margins.
        author_layout: Default author title-matter layout.
        include_contents: Whether to include a table of contents by default.
        include_references: Whether to include a references page by default.
        cover_page: Whether to render title matter on a cover page by default.

    Examples:
        ```python
        from oodocs.presets import TechnicalReportTemplate

        document = TechnicalReportTemplate().build(
            "Validation Report",
            executive_summary="All release checks passed.",
            sections=[("Findings", ["The evidence set is complete."])],
        )
        ```
    """

    name: str = "Technical report"
    theme: Theme = field(default_factory=_default_report_theme)
    page_size: PageSize = field(default_factory=PageSize.a4)
    page_margins: PageMargins = field(default_factory=PageMargins)
    author_layout: AuthorLayout = field(default_factory=AuthorLayout)
    include_contents: bool = True
    include_references: bool = True
    cover_page: bool = True

    def build(
        self,
        title: str,
        *,
        executive_summary: MatterInput | None = None,
        abstract: MatterInput | None = None,
        sections: Sequence[ReportSectionInput] = (),
        appendices: Sequence[BookChapterInput] = (),
        front_matter: MatterInput | None = None,
        back_matter: MatterInput | None = None,
        authors: Sequence[AuthorInput] | None = None,
        keywords: Sequence[str] | None = None,
        subtitle: InlineInput | None = None,
        summary: str | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        include_contents: bool | None = None,
        include_references: bool | None = None,
        cover_page: bool | None = None,
    ) -> Document:
        """Build a technical report document.

        Args:
            title: Document title.
            executive_summary: Optional unnumbered executive summary content.
            abstract: Optional unnumbered abstract content.
            sections: Main numbered report sections.
            appendices: Appendix chapters grouped under an appendix separator.
            front_matter: Extra blocks before the main numbered body.
            back_matter: Extra blocks after appendices and before references.
            authors: Optional document authors.
            keywords: Optional keyword list rendered near the front matter.
            subtitle: Optional subtitle inline content.
            summary: Optional metadata summary. Defaults to ``title``.
            citations: Optional citation library, citation sources, or BibTeX.
            include_contents: Override for table-of-contents inclusion.
            include_references: Override for references-page inclusion.
            cover_page: Override for cover-page title matter.

        Returns:
            Built report document.
        """

        include_contents_value = self.include_contents if include_contents is None else include_contents
        include_references_value = self.include_references if include_references is None else include_references

        children: list[BlockInput] = []
        if include_contents_value:
            children.append(TableOfContents(show_page_numbers=True, max_level=3))
        children.extend(_template_content_blocks(front_matter))
        if executive_summary is not None:
            children.append(_statement_section("Executive Summary", executive_summary))
        if abstract is not None:
            children.append(_statement_section("Abstract", abstract))
        if keywords:
            children.append(_keyword_paragraph(keywords))
        children.extend(_coerce_report_sections(sections))
        if appendices:
            children.append(Appendix(*_coerce_chapters(appendices)))
        children.extend(_template_content_blocks(back_matter))
        if include_references_value:
            children.append(ListOfReferences())

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


@dataclass(slots=True)
class SoftwareManualTemplate:
    """Build a user-facing software manual or procedural guide.

    Attributes:
        name: Template display name.
        theme: Document theme used by generated manuals.
        page_size: Default page size.
        page_margins: Default page margins.
        author_layout: Default author title-matter layout.
        include_contents: Whether to include a table of contents by default.
        include_references: Whether to include a references page by default.
        cover_page: Whether to render title matter on a cover page by default.

    Examples:
        ```python
        from oodocs.presets import SoftwareManualTemplate

        document = SoftwareManualTemplate().build(
            "Command Manual",
            overview="This manual explains the release command workflow.",
            sections=[("Install", ["Install the package before running commands."])],
        )
        ```
    """

    name: str = "Software manual"
    theme: Theme = field(default_factory=_default_report_theme)
    page_size: PageSize = field(default_factory=PageSize.a4)
    page_margins: PageMargins = field(default_factory=PageMargins)
    author_layout: AuthorLayout = field(default_factory=AuthorLayout)
    include_contents: bool = True
    include_references: bool = False
    cover_page: bool = True

    def build(
        self,
        title: str,
        *,
        overview: MatterInput | None = None,
        sections: Sequence[ManualSectionInput] = (),
        appendices: Sequence[BookChapterInput] = (),
        front_matter: MatterInput | None = None,
        back_matter: MatterInput | None = None,
        authors: Sequence[AuthorInput] | None = None,
        subtitle: InlineInput | None = None,
        summary: str | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        include_contents: bool | None = None,
        include_references: bool | None = None,
        cover_page: bool | None = None,
    ) -> Document:
        """Build a software manual document.

        Args:
            title: Document title.
            overview: Optional unnumbered overview content.
            sections: Main manual sections.
            appendices: Appendix chapters grouped under an appendix separator.
            front_matter: Extra blocks before the main numbered body.
            back_matter: Extra blocks after appendices and before references.
            authors: Optional document authors.
            subtitle: Optional subtitle inline content.
            summary: Optional metadata summary. Defaults to ``title``.
            citations: Optional citation library, citation sources, or BibTeX.
            include_contents: Override for table-of-contents inclusion.
            include_references: Override for references-page inclusion.
            cover_page: Override for cover-page title matter.

        Returns:
            Built manual document.
        """

        include_contents_value = self.include_contents if include_contents is None else include_contents
        include_references_value = self.include_references if include_references is None else include_references

        children: list[BlockInput] = []
        if include_contents_value:
            children.append(TableOfContents(show_page_numbers=True, max_level=3))
        children.extend(_template_content_blocks(front_matter))
        if overview is not None:
            children.append(_statement_section("Overview", overview))
        children.extend(_coerce_report_sections(sections))
        if appendices:
            children.append(Appendix(*_coerce_chapters(appendices)))
        children.extend(_template_content_blocks(back_matter))
        if include_references_value:
            children.append(ListOfReferences())

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


@dataclass(slots=True)
class BookTemplate:
    """Build a book-like document with front matter, parts, and appendices.

    Attributes:
        name: Template display name.
        theme: Document theme used by generated books.
        page_size: Default page size.
        page_margins: Default page margins.
        author_layout: Default author title-matter layout.
        include_contents: Whether to include a table of contents by default.
        include_references: Whether to include a references page by default.
        cover_page: Whether to render title matter on a cover page by default.

    Examples:
        ```python
        from oodocs.presets import BookTemplate

        document = BookTemplate().build(
            "Engineering Handbook",
            front_matter=["Preface text."],
            chapters=[("Getting Started", ["The first chapter."])],
        )
        ```
    """

    name: str = "Book"
    theme: Theme = field(default_factory=_default_book_theme)
    page_size: PageSize = field(default_factory=PageSize.a4)
    page_margins: PageMargins = field(default_factory=PageMargins)
    author_layout: AuthorLayout = field(default_factory=AuthorLayout)
    include_contents: bool = True
    include_references: bool = False
    cover_page: bool = True

    def build(
        self,
        title: str,
        *,
        front_matter: MatterInput | None = None,
        parts: Sequence[BookPartInput] = (),
        chapters: Sequence[BookChapterInput] = (),
        appendices: Sequence[BookChapterInput] = (),
        back_matter: MatterInput | None = None,
        authors: Sequence[AuthorInput] | None = None,
        subtitle: InlineInput | None = None,
        summary: str | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        include_contents: bool | None = None,
        include_references: bool | None = None,
        cover_page: bool | None = None,
    ) -> Document:
        """Build a book-style document.

        Args:
            title: Document title.
            front_matter: Blocks before the main numbered body.
            parts: Optional book parts containing chapters.
            chapters: Main chapters outside any part.
            appendices: Appendix chapters grouped under an appendix separator.
            back_matter: Extra blocks after appendices and before references.
            authors: Optional document authors.
            subtitle: Optional subtitle inline content.
            summary: Optional metadata summary. Defaults to ``title``.
            citations: Optional citation library, citation sources, or BibTeX.
            include_contents: Override for table-of-contents inclusion.
            include_references: Override for references-page inclusion.
            cover_page: Override for cover-page title matter.

        Returns:
            Built book document.
        """

        include_contents_value = self.include_contents if include_contents is None else include_contents
        include_references_value = self.include_references if include_references is None else include_references

        children: list[BlockInput] = []
        if include_contents_value:
            children.append(TableOfContents(show_page_numbers=True, max_level=3))
        children.extend(_template_content_blocks(front_matter))
        children.extend(_coerce_parts(parts))
        children.extend(_coerce_chapters(chapters))
        if appendices:
            children.append(Appendix(*_coerce_chapters(appendices)))
        children.extend(_template_content_blocks(back_matter))
        if include_references_value:
            children.append(ListOfReferences())

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


__all__ = [
    "BookTemplate",
    "CoverPagePreset",
    "JournalArticleTemplate",
    "ManuscriptSection",
    "SoftwareManualTemplate",
    "TechnicalReportTemplate",
]
