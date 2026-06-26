"""Theme configuration and grouped renderer defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from oodocs.components.references import normalize_citation_style, normalize_reference_style
from oodocs.core import (
    format_counter_value,
    normalize_color,
    normalize_counter_format,
    normalize_text_alignment,
)
from oodocs.styles.blocks import BoxStyle, ParagraphStyle, RunInTitleStyle
from oodocs.styles.counter import HeadingNumbering, ListStyle
from oodocs.styles.tables import TableStyle
from oodocs.styles.text import TextStyle

@dataclass(slots=True)
class TypographyDefaults:
    """Grouped document-wide font and size defaults for ``Theme``.

    Attributes:
        body_font_name: Default proportional font name.
        monospace_font_name: Default monospace font name.
        title_font_size: Title font size in points.
        body_font_size: Body font size in points.
        heading_sizes: Heading font sizes by level.
        caption_font_size: Optional caption font size override.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, Paragraph, Theme, TypographyDefaults

        theme = Theme(typography=TypographyDefaults(body_font_name="Arial", body_font_size=10.5))
        document = Document("Report", Paragraph("Body"), settings=DocumentSettings(theme=theme))
        ```
    """

    body_font_name: str = "Times New Roman"
    monospace_font_name: str = "Courier New"
    title_font_size: float = 22.0
    body_font_size: float = 11.0
    heading_sizes: tuple[float, ...] = (18.0, 15.0, 13.0, 11.5)
    caption_font_size: float | None = None


@dataclass(slots=True)
class CaptionDefaults:
    """Grouped caption labels, reference labels, positions, and text alignment.

    Attributes:
        caption_text_alignment: Caption paragraph text alignment.
        table_caption_position: Table caption position.
        figure_caption_position: Figure caption position.
        table_label: Default table label text.
        figure_label: Default figure label text.
        table_caption_label: Optional table caption label override.
        figure_caption_label: Optional figure caption label override.
        table_reference_label: Optional table reference label override.
        figure_reference_label: Optional figure reference label override.

    Examples:
        ```python
        from oodocs import CaptionDefaults, Document, DocumentSettings, Table, Theme

        theme = Theme(captions=CaptionDefaults(table_caption_position="below"))
        document = Document(
            "Metrics",
            Table(["Metric"], [["Latency"]], caption="Runtime metric"),
            settings=DocumentSettings(theme=theme),
        )
        ```
    """

    caption_text_alignment: str = "center"
    table_caption_position: str = "above"
    figure_caption_position: str = "below"
    table_label: str = "Table"
    figure_label: str = "Figure"
    table_caption_label: str | None = None
    figure_caption_label: str | None = None
    table_reference_label: str | None = None
    figure_reference_label: str | None = None

    def __post_init__(self) -> None:
        self.caption_text_alignment = normalize_text_alignment(self.caption_text_alignment)
        if self.table_caption_position not in {"above", "below"}:
            raise ValueError("table_caption_position must be 'above' or 'below'")
        if self.figure_caption_position not in {"above", "below"}:
            raise ValueError("figure_caption_position must be 'above' or 'below'")


@dataclass(slots=True)
class CitationDefaults:
    """Grouped citation and bibliography formatting defaults.

    Attributes:
        citation_style: Inline citation style identifier.
        reference_style: Reference list style identifier.

    Examples:
        ```python
        from oodocs import CitationDefaults, CitationSource, Document, DocumentSettings, Paragraph, Theme, cite

        theme = Theme(citations=CitationDefaults(citation_style="author-year"))
        source = CitationSource("Reliable APIs", key="api2024", authors=("Jane Doe",))
        document = Document(
            "Paper",
            Paragraph("Prior work ", cite("api2024"), "."),
            settings=DocumentSettings(theme=theme),
            citations=[source],
        )
        ```
    """

    citation_style: str = "numeric"
    reference_style: str = "plain"

    def __post_init__(self) -> None:
        self.citation_style = normalize_citation_style(self.citation_style)
        self.reference_style = normalize_reference_style(self.reference_style)


@dataclass(slots=True)
class GeneratedContentDefaults:
    """Grouped generated-content titles and layout defaults.

    Attributes:
        list_of_tables_title: Default title for generated table lists.
        list_of_figures_title: Default title for generated figure lists.
        comment_list_title: Default title for generated comment lists.
        footnote_list_title: Default title for generated footnote lists.
        reference_list_title: Default title for generated reference lists.
        table_of_contents_title: Default title for generated tables of contents.
        generated_heading_level: Heading level used by generated content.
        generated_content_page_breaks: Whether generated content starts on new
            pages when supported.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, GeneratedContentDefaults, ReferenceList, Theme

        theme = Theme(generated_content=GeneratedContentDefaults(reference_list_title="Bibliography"))
        document = Document("Paper", ReferenceList(), settings=DocumentSettings(theme=theme))
        ```
    """

    list_of_tables_title: str = "List of Tables"
    list_of_figures_title: str = "List of Figures"
    comment_list_title: str = "Comments"
    footnote_list_title: str = "Footnotes"
    reference_list_title: str = "References"
    table_of_contents_title: str = "Contents"
    generated_heading_level: int = 2
    generated_content_page_breaks: bool = True


@dataclass(slots=True)
class PageNumberDefaults:
    """Grouped footer page-number defaults.

    Attributes:
        show_page_numbers: Whether renderers should emit footer page numbers.
        page_number_alignment: Footer page-number alignment.
        page_number_template: Footer text template containing ``{page}``.
        front_matter_counter_format: Front-matter page counter style.
        main_matter_counter_format: Main-matter page counter style.
        page_number_font_size: Footer page-number font size in points.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, PageNumberDefaults, Paragraph, Theme

        theme = Theme(page_numbers=PageNumberDefaults(show_page_numbers=True))
        document = Document("Report", Paragraph("Body"), settings=DocumentSettings(theme=theme))
        ```
    """

    show_page_numbers: bool = False
    page_number_alignment: str = "center"
    page_number_template: str = "{page}"
    front_matter_counter_format: str = "lower-roman"
    main_matter_counter_format: str = "decimal"
    page_number_font_size: float = 9.0

    def __post_init__(self) -> None:
        if self.page_number_alignment not in {"left", "center", "right"}:
            raise ValueError(
                f"Unsupported page number alignment: {self.page_number_alignment!r}"
            )
        self.front_matter_counter_format = normalize_counter_format(
            self.front_matter_counter_format
        )
        self.main_matter_counter_format = normalize_counter_format(
            self.main_matter_counter_format
        )
        if "{page}" not in self.page_number_template:
            raise ValueError("page_number_template must contain a '{page}' placeholder")


@dataclass(slots=True)
class TitleMatterDefaults:
    """Grouped title, subtitle, author, and affiliation text alignment defaults.

    Attributes:
        title_text_alignment: Title text alignment.
        subtitle_text_alignment: Subtitle text alignment.
        author_text_alignment: Author line text alignment.
        affiliation_text_alignment: Affiliation line text alignment.
        author_detail_text_alignment: Author detail line text alignment.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, Paragraph, Theme, TitleMatterDefaults

        theme = Theme(title_matter=TitleMatterDefaults(title_text_alignment="left"))
        document = Document("Report", Paragraph("Body"), settings=DocumentSettings(theme=theme))
        ```
    """

    title_text_alignment: str = "center"
    subtitle_text_alignment: str = "center"
    author_text_alignment: str = "center"
    affiliation_text_alignment: str = "center"
    author_detail_text_alignment: str = "center"

    def __post_init__(self) -> None:
        for field_name in (
            "title_text_alignment",
            "subtitle_text_alignment",
            "author_text_alignment",
            "affiliation_text_alignment",
            "author_detail_text_alignment",
        ):
            setattr(self, field_name, normalize_text_alignment(getattr(self, field_name)))


@dataclass(slots=True)
class BlockDefaults:
    """Grouped block-level document defaults for ``Theme``.

    Attributes:
        page_background_color: Hex page background color.
        paragraph_text_alignment: Default paragraph alignment.
        table_block_alignment: Default table block placement alignment.
        figure_block_alignment: Default figure block placement alignment.
        box_block_alignment: Default box block placement alignment.
        part_label: Label used for numbered part pages.
        part_counter_format: Counter format used for parts.
        footnote_placement: Native or generated content footnote placement.
        auto_footnotes_page: Whether missing footnote pages are auto-rendered.
        run_in_title_style: Default style for run-in paragraph titles.
        heading_numbering: Heading numbering configuration.
        bullet_list_style: Default bullet list style.
        numbered_list_style: Default numbered list style.

    Examples:
        ```python
        from oodocs import BlockDefaults, Document, DocumentSettings, HeadingNumbering, Paragraph, Section, Theme

        theme = Theme(blocks=BlockDefaults(heading_numbering=HeadingNumbering(enabled=False)))
        document = Document(
            "Report",
            Section("Unnumbered", Paragraph("Body", title="Scope")),
            settings=DocumentSettings(theme=theme),
        )
        ```
    """

    page_background_color: str = "FFFFFF"
    paragraph_text_alignment: str = "justify"
    table_block_alignment: str = "center"
    figure_block_alignment: str = "center"
    box_block_alignment: str = "center"
    part_label: str = "Part"
    part_counter_format: str = "upper-roman"
    footnote_placement: str = "page"
    auto_footnotes_page: bool = True
    run_in_title_style: RunInTitleStyle = field(default_factory=RunInTitleStyle)
    heading_numbering: HeadingNumbering = field(default_factory=HeadingNumbering)
    bullet_list_style: ListStyle = field(
        default_factory=lambda: ListStyle(marker_counter_format="bullet", suffix="")
    )
    numbered_list_style: ListStyle = field(default_factory=ListStyle)

    def __post_init__(self) -> None:
        self.page_background_color = normalize_color(self.page_background_color) or "FFFFFF"
        self.paragraph_text_alignment = normalize_text_alignment(self.paragraph_text_alignment)
        for field_name in (
            "table_block_alignment",
            "figure_block_alignment",
            "box_block_alignment",
        ):
            value = getattr(self, field_name)
            if value not in {"left", "center", "right"}:
                raise ValueError(f"Unsupported alignment for {field_name}: {value!r}")
        self.part_counter_format = normalize_counter_format(self.part_counter_format)
        if self.footnote_placement not in {"page", "document"}:
            raise ValueError("footnote_placement must be 'page' or 'document'")
        if not isinstance(self.run_in_title_style, RunInTitleStyle):
            raise TypeError("run_in_title_style must be a RunInTitleStyle")
        if not isinstance(self.heading_numbering, HeadingNumbering):
            raise TypeError("heading_numbering must be a HeadingNumbering")
        if not isinstance(self.bullet_list_style, ListStyle):
            raise TypeError("bullet_list_style must be a ListStyle")
        if not isinstance(self.numbered_list_style, ListStyle):
            raise TypeError("numbered_list_style must be a ListStyle")


@dataclass(slots=True, init=False)
class Theme:
    """Document-wide renderer defaults.

    Args:
        typography: Optional typography defaults group.
        captions: Optional caption defaults group.
        citations: Optional citation defaults group.
        generated_content: Optional generated-content defaults group.
        page_numbers: Optional page-number defaults group.
        title_matter: Optional title-matter defaults group.
        blocks: Optional block defaults group.

    Attributes:
        typography: Resolved typography defaults group.
        captions: Resolved caption defaults group.
        citations: Resolved citation defaults group.
        generated_content: Resolved generated-content defaults group.
        page_numbers: Resolved page-number defaults group.
        title_matter: Resolved title-matter defaults group.
        blocks: Resolved block defaults group.

    Raises:
        TypeError: If a grouped defaults argument has the wrong type.
        ValueError: If alignment, format, numbering, or color values are
            invalid.

    Examples:
        Configure typography and paragraph defaults:

        ```python
        from oodocs import BlockDefaults, Document, DocumentSettings, Paragraph, Theme, TypographyDefaults

        theme = Theme(
            typography=TypographyDefaults(body_font_name="Arial"),
            blocks=BlockDefaults(paragraph_text_alignment="left"),
        )
        document = Document("Report", Paragraph("Body"), settings=DocumentSettings(theme=theme))
        ```

        Customize generated content titles and page numbers together:

        ```python
        from oodocs import Document, DocumentSettings, GeneratedContentDefaults, PageNumberDefaults, ReferenceList, Theme

        theme = Theme(
            generated_content=GeneratedContentDefaults(reference_list_title="Bibliography"),
            page_numbers=PageNumberDefaults(show_page_numbers=True, page_number_template="Page {page}"),
        )
        document = Document("Paper", ReferenceList(), settings=DocumentSettings(theme=theme))
        ```

    Notes:
        Theme construction is grouped by concern. Put font values in
        ``TypographyDefaults``, caption labels and positions in
        ``CaptionDefaults``, page-number settings in ``PageNumberDefaults``,
        and block-level defaults in ``BlockDefaults``.

    See Also:
        ``TypographyDefaults``, ``CaptionDefaults``, ``CitationDefaults``,
        ``GeneratedContentDefaults``, ``PageNumberDefaults``, ``TitleMatterDefaults``,
        and ``BlockDefaults`` for grouped configuration.
    """

    typography: TypographyDefaults
    captions: CaptionDefaults
    citations: CitationDefaults
    generated_content: GeneratedContentDefaults
    page_numbers: PageNumberDefaults
    title_matter: TitleMatterDefaults
    blocks: BlockDefaults

    def __init__(
        self,
        *,
        typography: TypographyDefaults | None = None,
        captions: CaptionDefaults | None = None,
        citations: CitationDefaults | None = None,
        generated_content: GeneratedContentDefaults | None = None,
        page_numbers: PageNumberDefaults | None = None,
        title_matter: TitleMatterDefaults | None = None,
        blocks: BlockDefaults | None = None,
    ) -> None:
        expected_types = {
            "typography": (typography, TypographyDefaults),
            "captions": (captions, CaptionDefaults),
            "citations": (citations, CitationDefaults),
            "generated_content": (generated_content, GeneratedContentDefaults),
            "page_numbers": (page_numbers, PageNumberDefaults),
            "title_matter": (title_matter, TitleMatterDefaults),
            "blocks": (blocks, BlockDefaults),
        }
        for argument_name, (value, expected_type) in expected_types.items():
            if value is not None and not isinstance(value, expected_type):
                raise TypeError(
                    f"Theme.{argument_name} must be a {expected_type.__name__}"
                )

        self.typography = typography or TypographyDefaults()
        self.captions = captions or CaptionDefaults()
        self.citations = citations or CitationDefaults()
        self.generated_content = generated_content or GeneratedContentDefaults()
        self.page_numbers = page_numbers or PageNumberDefaults()
        self.title_matter = title_matter or TitleMatterDefaults()
        self.blocks = blocks or BlockDefaults()

    def heading_size(self, level: int) -> float:
        """Return the configured font size for a heading level.

        Args:
            level: One-based heading level.

        Returns:
            Font size for the nearest configured level.

        Examples:
            ```python
            assert Theme(typography=TypographyDefaults(heading_sizes=(20.0, 16.0))).heading_size(3) == 16.0
            ```
        """

        index = min(max(level - 1, 0), len(self.typography.heading_sizes) - 1)
        return self.typography.heading_sizes[index]

    def heading_emphasis(self, level: int) -> tuple[bool, bool]:
        """Return heading emphasis for a heading level.

        Args:
            level: One-based heading level.

        Returns:
            ``(bold, italic)`` emphasis flags.

        Examples:
            ```python
            assert Theme().heading_emphasis(1) == (True, False)
            ```
        """

        emphasis = (
            (True, False),
            (True, False),
            (True, True),
            (False, True),
        )
        index = min(max(level - 1, 0), len(emphasis) - 1)
        return emphasis[index]

    def heading_alignment(self, level: int) -> str:
        """Return the alignment to use for the given heading level.

        Args:
            level: One-based heading level.

        Returns:
            Heading alignment.

        Examples:
            ```python
            assert Theme().heading_alignment(2) == "left"
            ```
        """

        return "left"

    def resolve_paragraph_text_alignment(self, style: ParagraphStyle) -> str:
        """Return a paragraph style's alignment or the document-wide default.

        Args:
            style: Paragraph style to resolve.

        Returns:
            Effective paragraph alignment.

        Examples:
            ```python
            theme = Theme(blocks=BlockDefaults(paragraph_text_alignment="left"))
            assert theme.resolve_paragraph_text_alignment(ParagraphStyle()) == "left"
            ```
        """

        return style.text_alignment or self.blocks.paragraph_text_alignment

    def resolve_run_in_title_style(
        self,
        paragraph_override: RunInTitleStyle | None = None,
        scope_style: RunInTitleStyle | None = None,
    ) -> RunInTitleStyle:
        """Return the effective run-in title style.

        Args:
            paragraph_override: Title style set directly on a paragraph.
            scope_style: Title style inherited from the nearest section or
                chapter.

        Returns:
            Effective run-in title style.

        Examples:
            ```python
            from oodocs import RunInTitleStyle, TextStyle, Theme

            style = Theme().resolve_run_in_title_style(
                RunInTitleStyle(TextStyle(bold=True, italic=True))
            )
            ```
        """

        return paragraph_override or scope_style or self.blocks.run_in_title_style

    def table_caption_label_text(self) -> str:
        """Return the label used in table captions and generated table lists.

        Returns:
            Effective table caption label.

        Examples:
            ```python
            theme = Theme(captions=CaptionDefaults(table_caption_label="Tbl."))
            assert theme.table_caption_label_text() == "Tbl."
            ```
        """

        return self.captions.table_caption_label or self.captions.table_label

    def figure_caption_label_text(self) -> str:
        """Return the label used in figure captions and generated figure lists.

        Returns:
            Effective figure caption label.

        Examples:
            ```python
            theme = Theme(captions=CaptionDefaults(figure_caption_label="Fig."))
            assert theme.figure_caption_label_text() == "Fig."
            ```
        """

        return self.captions.figure_caption_label or self.captions.figure_label

    def table_reference_label_text(self) -> str:
        """Return the label used for inline table references.

        Returns:
            Effective table reference label.

        Examples:
            ```python
            theme = Theme(captions=CaptionDefaults(table_reference_label="Tbl."))
            assert theme.table_reference_label_text() == "Tbl."
            ```
        """

        return self.captions.table_reference_label or self.captions.table_label

    def figure_reference_label_text(self) -> str:
        """Return the label used for inline figure and subfigure references.

        Returns:
            Effective figure reference label.

        Examples:
            ```python
            theme = Theme(captions=CaptionDefaults(figure_reference_label="Fig."))
            assert theme.figure_reference_label_text() == "Fig."
            ```
        """

        return self.captions.figure_reference_label or self.captions.figure_label

    def caption_size(self) -> float:
        """Return the effective caption font size.

        Returns:
            Caption font size, falling back to body font size.

        Examples:
            ```python
            assert Theme(typography=TypographyDefaults(body_font_size=11.0)).caption_size() == 11.0
            ```
        """

        return (
            self.typography.body_font_size
            if self.typography.caption_font_size is None
            else self.typography.caption_font_size
        )

    def format_page_number(
        self,
        page_number: int,
        *,
        front_matter: bool = False,
    ) -> str:
        """Render the footer page number string for a page.

        Args:
            page_number: One-based logical page number.
            front_matter: Whether to use front-matter numbering format.

        Returns:
            Formatted page number text.

        Examples:
            ```python
            theme = Theme(page_numbers=PageNumberDefaults(page_number_template="Page {page}"))
            assert theme.format_page_number(3) == "Page 3"
            ```
        """

        counter_format = (
            self.page_numbers.front_matter_counter_format
            if front_matter
            else self.page_numbers.main_matter_counter_format
        )
        page_label = format_counter_value(page_number, counter_format)
        return self.page_numbers.page_number_template.format(page=page_label)

    def format_heading_label(self, counters: Sequence[int]) -> str | None:
        """Render a heading numbering label for nested section counters.

        Args:
            counters: Counter values from top-level heading through current
                heading.

        Returns:
            Formatted heading label, or ``None`` when numbering is disabled.

        Examples:
            ```python
            assert Theme().format_heading_label([1, 2]) == "1.2"
            ```
        """

        return self.blocks.heading_numbering.format_label(counters)

    def format_part_label(self, value: int) -> str | None:
        """Render a part label such as ``Part I`` from an independent counter.

        Args:
            value: Part counter value.

        Returns:
            Formatted part label, or ``None`` when heading numbering is
            disabled.

        Examples:
            ```python
            assert Theme().format_part_label(2) == "Part II"
            ```
        """

        if not self.blocks.heading_numbering.enabled:
            return None
        marker = format_counter_value(value, self.blocks.part_counter_format)
        return f"{self.blocks.part_label} {marker}".strip()

    def list_style(self, *, ordered: bool) -> ListStyle:
        """Return the default style for bullet or ordered lists.

        Args:
            ordered: Whether to return the ordered-list style.

        Returns:
            Default list style for the requested list kind.

        Examples:
            ```python
            assert Theme().list_style(ordered=True).marker_for(0) == "1."
            ```
        """

        return self.blocks.numbered_list_style if ordered else self.blocks.bullet_list_style

__all__ = [
    "BlockDefaults",
    "BoxStyle",
    "CaptionDefaults",
    "CitationDefaults",
    "GeneratedContentDefaults",
    "HeadingNumbering",
    "ListStyle",
    "PageNumberDefaults",
    "ParagraphStyle",
    "RunInTitleStyle",
    "TableStyle",
    "TextStyle",
    "TitleMatterDefaults",
    "TypographyDefaults",
    "Theme",
]
