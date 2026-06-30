"""Theme configuration and grouped renderer defaults.

Attributes:
    DEFAULT_FOOTNOTE_SYMBOLS: Default cycle for symbolic footnote markers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime
from typing import Literal, Sequence

from oodocs.components.references import (
    normalize_citation_style,
    normalize_reference_sort,
    normalize_reference_style,
)
from oodocs.core import (
    normalize_color,
    normalize_text_alignment,
)
from oodocs.styles.blocks import BoxStyle, ParagraphStyle, RunInTitleStyle
from oodocs.styles.counter import CounterStyle, HeadingNumbering, ListStyle
from oodocs.styles.sheet import StyleSheet
from oodocs.styles.tables import TableStyle
from oodocs.styles.text import TextStyle


DEFAULT_FOOTNOTE_SYMBOLS: tuple[str, ...] = (
    "*",
    "\u2020",
    "\u2021",
    "\u00a7",
    "\u00b6",
    "\u2016",
)


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
class HeadingStyle:
    """Per-level or per-section heading styling.

    Attributes:
        text_style: Inline text defaults applied to the heading title.
        space_before: Spacing before the heading in points.
        space_after: Spacing after the heading in points.
        leading: Heading line spacing in points.
        text_alignment: Heading text alignment.
        numbering: Optional counter style for this heading level.

    Examples:
        ```python
        from oodocs import HeadingStyle, TextStyle

        heading = HeadingStyle(
            text_style=TextStyle(bold=True, font_size=16),
            space_before=18,
            space_after=8,
        )
        ```
    """

    text_style: TextStyle = field(default_factory=TextStyle)
    space_before: float | None = None
    space_after: float | None = None
    leading: float | None = None
    text_alignment: str | None = None
    numbering: CounterStyle | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text_style, TextStyle):
            raise TypeError("HeadingStyle.text_style must be a TextStyle")
        if self.text_alignment is not None:
            self.text_alignment = normalize_text_alignment(self.text_alignment)
        if self.numbering is not None and not isinstance(self.numbering, CounterStyle):
            raise TypeError("HeadingStyle.numbering must be a CounterStyle")
        for field_name in ("space_before", "space_after", "leading"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"HeadingStyle.{field_name} must be >= 0")

    def merged(self, *others: HeadingStyle | None) -> HeadingStyle:
        """Return a new heading style with later values overriding earlier ones.

        Args:
            *others: Heading styles to overlay from left to right.

        Returns:
            New merged heading style.
        """

        merged = HeadingStyle(
            text_style=self.text_style,
            space_before=self.space_before,
            space_after=self.space_after,
            leading=self.leading,
            text_alignment=self.text_alignment,
            numbering=self.numbering,
        )
        for other in others:
            if other is None:
                continue
            if not isinstance(other, HeadingStyle):
                raise TypeError("heading style values must be HeadingStyle instances")
            merged = HeadingStyle(
                text_style=merged.text_style.merged(other.text_style),
                space_before=(
                    merged.space_before
                    if other.space_before is None
                    else other.space_before
                ),
                space_after=(
                    merged.space_after
                    if other.space_after is None
                    else other.space_after
                ),
                leading=merged.leading if other.leading is None else other.leading,
                text_alignment=(
                    merged.text_alignment
                    if other.text_alignment is None
                    else other.text_alignment
                ),
                numbering=merged.numbering if other.numbering is None else other.numbering,
            )
        return merged


@dataclass(slots=True)
class FootnoteStyle:
    """Marker style for one footnote stream.

    Attributes:
        marker: Counter style used for numeric, alphabetic, roman, or custom
            prefixed footnote markers.
        symbols: Optional symbol sequence used instead of ``marker``.

    Examples:
        ```python
        from oodocs import FootnoteStyle

        symbol_notes = FootnoteStyle.symbol()
        assert symbol_notes.format_value(1) == "*"
        ```
    """

    marker: CounterStyle = field(default_factory=CounterStyle)
    symbols: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.marker, CounterStyle):
            raise TypeError("FootnoteStyle.marker must be a CounterStyle")
        if self.symbols is not None:
            self.symbols = tuple(str(symbol) for symbol in self.symbols)
            if not self.symbols or any(not symbol for symbol in self.symbols):
                raise ValueError("FootnoteStyle.symbols must not contain empty symbols")

    @classmethod
    def symbol(cls, symbols: Sequence[str] = DEFAULT_FOOTNOTE_SYMBOLS) -> FootnoteStyle:
        """Return a symbol-based footnote style.

        Args:
            symbols: Symbol sequence. Values repeat when the stream has more
                footnotes than symbols.

        Returns:
            Symbol-marker footnote style.
        """

        return cls(symbols=tuple(symbols))

    def format_value(self, value: int) -> str:
        """Format one footnote marker value.

        Args:
            value: One-based stream-local footnote number.

        Returns:
            Marker text for the footnote reference.
        """

        if self.symbols is None:
            return self.marker.format_value(value)
        if value < 1:
            raise ValueError("Footnote marker value must be >= 1")
        index = (value - 1) % len(self.symbols)
        repeats = (value - 1) // len(self.symbols) + 1
        return self.symbols[index] * repeats

    def is_native_docx_compatible(self) -> bool:
        """Return whether Word native footnotes can represent this style.

        Returns:
            ``True`` for the default plain decimal marker only.
        """

        return (
            self.symbols is None
            and self.marker.counter_format == "decimal"
            and self.marker.prefix == ""
            and self.marker.suffix == ""
            and self.marker.start == 1
        )


@dataclass(slots=True)
class FootnoteDefaults:
    """Document-wide footnote stream and marker defaults.

    Attributes:
        default_style: Marker style for the default stream.
        stream_styles: Marker styles keyed by stream name.

    Examples:
        ```python
        from oodocs import CounterStyle, FootnoteDefaults, FootnoteStyle, Theme

        theme = Theme(
            footnotes=FootnoteDefaults(
                stream_styles={
                    "symbols": FootnoteStyle.symbol(),
                    "review": FootnoteStyle(CounterStyle(prefix="R")),
                }
            )
        )
        ```
    """

    default_style: FootnoteStyle = field(default_factory=FootnoteStyle)
    stream_styles: dict[str, FootnoteStyle] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.default_style, FootnoteStyle):
            raise TypeError("FootnoteDefaults.default_style must be a FootnoteStyle")
        self.stream_styles = {
            self._normalize_stream_name(name): self._coerce_style(style)
            for name, style in self.stream_styles.items()
        }

    def style_for_stream(self, stream: str) -> FootnoteStyle:
        """Return the marker style for a footnote stream.

        Args:
            stream: Footnote stream name.

        Returns:
            Configured stream style or ``default_style``.
        """

        return self.stream_styles.get(self._normalize_stream_name(stream), self.default_style)

    def format_marker(self, stream: str, number: int) -> str:
        """Format a stream-local footnote marker.

        Args:
            stream: Footnote stream name.
            number: One-based stream-local footnote number.

        Returns:
            Marker text for the footnote reference.
        """

        return self.style_for_stream(stream).format_value(number)

    def is_native_docx_compatible(self, stream: str) -> bool:
        """Return whether native Word footnotes can represent a stream.

        Args:
            stream: Footnote stream name.

        Returns:
            ``True`` only for the default stream with the plain decimal style.
        """

        return (
            self._normalize_stream_name(stream) == "default"
            and self.style_for_stream("default").is_native_docx_compatible()
        )

    @staticmethod
    def _coerce_style(style: FootnoteStyle) -> FootnoteStyle:
        if not isinstance(style, FootnoteStyle):
            raise TypeError("FootnoteDefaults.stream_styles values must be FootnoteStyle instances")
        return style

    @staticmethod
    def _normalize_stream_name(value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("Footnote stream names must not be empty")
        return normalized


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
        reference_sort: Reference list sort style.

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
    reference_sort: str = "citation"

    def __post_init__(self) -> None:
        self.citation_style = normalize_citation_style(self.citation_style)
        self.reference_style = normalize_reference_style(self.reference_style)
        self.reference_sort = normalize_reference_sort(self.reference_sort)


@dataclass(slots=True)
class LinkDefaults:
    """Grouped hyperlink styling defaults for ``Theme``.

    Attributes:
        text_style: Inline text style used for hyperlink labels unless a link
            supplies its own style.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, LinkDefaults, Paragraph, TextStyle, Theme, link

        theme = Theme(links=LinkDefaults(TextStyle(text_color="C00000", underline=False)))
        document = Document(
            "Links",
            Paragraph("Open ", link("https://example.com", "Example")),
            settings=DocumentSettings(theme=theme),
        )
        ```
    """

    text_style: TextStyle = field(
        default_factory=lambda: TextStyle(text_color="0563C1", underline=True)
    )

    def __post_init__(self) -> None:
        if not isinstance(self.text_style, TextStyle):
            raise TypeError("LinkDefaults.text_style must be a TextStyle")


@dataclass(slots=True)
class GeneratedContentDefaults:
    """Grouped generated-content titles and layout defaults.

    Attributes:
        list_of_tables_title: Default title for generated table lists.
        list_of_figures_title: Default title for generated figure lists.
        list_of_algorithms_title: Default title for generated algorithm lists.
        list_of_comments_title: Default title for generated comment lists.
        list_of_footnotes_title: Default title for generated footnote lists.
        list_of_references_title: Default title for generated reference lists.
        list_of_glossary_terms_title: Default title for generated glossary lists.
        table_of_contents_title: Default title for generated tables of contents.
        generated_heading_level: Heading level used by generated content.
        generated_content_page_breaks: Whether generated content starts on new
            pages when supported.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, GeneratedContentDefaults, ListOfReferences, Theme

        theme = Theme(generated_content=GeneratedContentDefaults(list_of_references_title="Bibliography"))
        document = Document("Paper", ListOfReferences(), settings=DocumentSettings(theme=theme))
        ```
    """

    list_of_tables_title: str = "List of Tables"
    list_of_figures_title: str = "List of Figures"
    list_of_algorithms_title: str = "List of Algorithms"
    list_of_comments_title: str = "Comments"
    list_of_footnotes_title: str = "Footnotes"
    list_of_references_title: str = "References"
    list_of_glossary_terms_title: str = "Glossary"
    table_of_contents_title: str = "Contents"
    generated_heading_level: int = 2
    generated_content_page_breaks: bool = True


def _normalize_language_tag(value: str) -> str:
    normalized = str(value).strip().replace("_", "-")
    if not normalized:
        raise ValueError("language_tag must not be empty")
    aliases = {
        "en": "en-US",
        "en-us": "en-US",
        "ko": "ko-KR",
        "ko-kr": "ko-KR",
    }
    alias = aliases.get(normalized.lower())
    if alias is not None:
        return alias
    pieces = [piece for piece in normalized.split("-") if piece]
    if not pieces:
        raise ValueError("language_tag must not be empty")
    language = pieces[0].lower()
    tail = [
        piece.upper() if len(piece) == 2 and piece.isalpha() else piece
        for piece in pieces[1:]
    ]
    return "-".join([language, *tail])


@dataclass(slots=True)
class LocaleDefaults:
    """Grouped document language, localized labels, and date defaults.

    Args:
        language_tag: BCP 47-style document language tag, such as
            ``"en-US"`` or ``"ko-KR"``.
        date_format: ``str.format`` template used by ``format_date``.
        captions: Localized caption and reference labels.
        generated_content: Localized generated-page titles.
        glossary_headers: Localized glossary table headers.
        typography: Optional locale-specific font defaults.
        pdf_font_fallbacks: Human-readable font family suggestions for PDF
            output when the locale needs fonts outside ReportLab's built-ins.

    Examples:
        ```python
        from datetime import date
        from oodocs import Theme

        theme = Theme.from_locale("ko-KR")
        assert theme.format_date(date(2026, 6, 29)) == "2026. 6. 29."
        ```
    """

    language_tag: str = "en-US"
    date_format: str = "{month_name} {day}, {year}"
    captions: CaptionDefaults = field(default_factory=CaptionDefaults)
    generated_content: GeneratedContentDefaults = field(default_factory=GeneratedContentDefaults)
    glossary_headers: tuple[str, str] = ("Term", "Definition")
    typography: TypographyDefaults | None = None
    pdf_font_fallbacks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.language_tag = _normalize_language_tag(self.language_tag)
        if not isinstance(self.date_format, str) or not self.date_format.strip():
            raise ValueError("LocaleDefaults.date_format must not be empty")
        if not isinstance(self.captions, CaptionDefaults):
            raise TypeError("LocaleDefaults.captions must be a CaptionDefaults")
        if not isinstance(self.generated_content, GeneratedContentDefaults):
            raise TypeError(
                "LocaleDefaults.generated_content must be a GeneratedContentDefaults"
            )
        if len(self.glossary_headers) != 2:
            raise ValueError("LocaleDefaults.glossary_headers must contain two labels")
        self.glossary_headers = (
            str(self.glossary_headers[0]),
            str(self.glossary_headers[1]),
        )
        if self.typography is not None and not isinstance(
            self.typography,
            TypographyDefaults,
        ):
            raise TypeError("LocaleDefaults.typography must be a TypographyDefaults")
        self.pdf_font_fallbacks = tuple(
            fallback
            for fallback in (str(item).strip() for item in self.pdf_font_fallbacks)
            if fallback
        )

    @classmethod
    def from_locale(cls, language_tag: str) -> LocaleDefaults:
        """Return a built-in locale bundle.

        Args:
            language_tag: Locale tag. Supported built-ins are ``"en-US"`` and
                ``"ko-KR"``; ``"en"`` and ``"ko"`` are accepted aliases.

        Returns:
            Locale defaults for the requested locale.

        Raises:
            ValueError: If the locale is not built in.
        """

        normalized = _normalize_language_tag(language_tag)
        if normalized == "en-US":
            return cls()
        if normalized == "ko-KR":
            return cls(
                language_tag="ko-KR",
                date_format="{year}. {month}. {day}.",
                captions=CaptionDefaults(table_label="표", figure_label="그림"),
                generated_content=GeneratedContentDefaults(
                    list_of_tables_title="표 목록",
                    list_of_figures_title="그림 목록",
                    list_of_algorithms_title="알고리즘 목록",
                    list_of_comments_title="주석",
                    list_of_footnotes_title="각주",
                    list_of_references_title="참고문헌",
                    list_of_glossary_terms_title="용어집",
                    table_of_contents_title="목차",
                ),
                glossary_headers=("용어", "정의"),
                typography=TypographyDefaults(
                    body_font_name="Malgun Gothic",
                    monospace_font_name="D2Coding",
                ),
                pdf_font_fallbacks=(
                    "Malgun Gothic",
                    "NanumGothic",
                    "Noto Sans CJK KR",
                ),
            )
        raise ValueError(f"unsupported built-in locale: {language_tag!r}")

    def format_date(self, value: date_type | datetime | str) -> str:
        """Format a date with this locale's date template.

        Args:
            value: ``date``, ``datetime``, or ISO ``YYYY-MM-DD`` string.

        Returns:
            Localized date string.
        """

        if isinstance(value, datetime):
            date_value = value.date()
        elif isinstance(value, date_type):
            date_value = value
        elif isinstance(value, str):
            try:
                date_value = date_type.fromisoformat(value)
            except ValueError:
                date_value = datetime.fromisoformat(value).date()
        else:
            raise TypeError("format_date value must be date, datetime, or ISO date text")
        month_names = (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        )
        return self.date_format.format(
            year=date_value.year,
            month=date_value.month,
            day=date_value.day,
            month_name=month_names[date_value.month - 1],
        )


@dataclass(slots=True)
class PageNumberDefaults:
    """Grouped footer page-number defaults.

    Attributes:
        show_page_numbers: Whether renderers should emit footer page numbers.
        page_number_alignment: Footer page-number alignment.
        page_number_template: Footer text template containing ``{page}``.
        front_matter_counter: Front-matter page counter style.
        main_matter_counter: Main-matter page counter style.
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
    front_matter_counter: CounterStyle = field(
        default_factory=lambda: CounterStyle(counter_format="lower-roman")
    )
    main_matter_counter: CounterStyle = field(default_factory=CounterStyle)
    page_number_font_size: float = 9.0

    def __post_init__(self) -> None:
        if self.page_number_alignment not in {"left", "center", "right"}:
            raise ValueError(
                f"Unsupported page number alignment: {self.page_number_alignment!r}"
            )
        if not isinstance(self.front_matter_counter, CounterStyle):
            raise TypeError("front_matter_counter must be a CounterStyle")
        if not isinstance(self.main_matter_counter, CounterStyle):
            raise TypeError("main_matter_counter must be a CounterStyle")
        if "{page}" not in self.page_number_template:
            raise ValueError("page_number_template must contain a '{page}' placeholder")


_HEADER_FOOTER_TEMPLATE_FIELDS = (
    "header_left",
    "header_center",
    "header_right",
    "footer_left",
    "footer_center",
    "footer_right",
    "first_header_left",
    "first_header_center",
    "first_header_right",
    "first_footer_left",
    "first_footer_center",
    "first_footer_right",
    "even_header_left",
    "even_header_center",
    "even_header_right",
    "even_footer_left",
    "even_footer_center",
    "even_footer_right",
)


class _HeaderFooterTokenMap(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


@dataclass(slots=True)
class HeaderFooterDefaults:
    """Grouped page header and footer templates.

    Attributes:
        header_left: Left header template for ordinary pages.
        header_center: Center header template for ordinary pages.
        header_right: Right header template for ordinary pages.
        footer_left: Left footer template for ordinary pages.
        footer_center: Center footer template for ordinary pages.
        footer_right: Right footer template for ordinary pages.
        first_header_left: Left header override for first pages.
        first_header_center: Center header override for first pages.
        first_header_right: Right header override for first pages.
        first_footer_left: Left footer override for first pages.
        first_footer_center: Center footer override for first pages.
        first_footer_right: Right footer override for first pages.
        even_header_left: Left header override for even pages.
        even_header_center: Center header override for even pages.
        even_header_right: Right header override for even pages.
        even_footer_left: Left footer override for even pages.
        even_footer_center: Center footer override for even pages.
        even_footer_right: Right footer override for even pages.
        different_first_page: Whether first pages use first-page overrides.
        different_odd_even_pages: Whether even pages use even-page overrides.
        font_size: Optional header/footer font size in points.

    Notes:
        Templates support ``{page}``, ``{title}``, ``{chapter}``, and
        ``{section}``. DOCX renders ``{page}``, ``{chapter}``, and
        ``{section}`` as Word fields; PDF and HTML resolve them at render time.

    Examples:
        ```python
        from oodocs import HeaderFooterDefaults, Theme

        theme = Theme(
            header_footer=HeaderFooterDefaults(
                header_left="{chapter}",
                header_right="{page}",
                footer_center="{title}",
                different_first_page=True,
            )
        )
        ```
    """

    header_left: str | None = None
    header_center: str | None = None
    header_right: str | None = None
    footer_left: str | None = None
    footer_center: str | None = None
    footer_right: str | None = None
    first_header_left: str | None = None
    first_header_center: str | None = None
    first_header_right: str | None = None
    first_footer_left: str | None = None
    first_footer_center: str | None = None
    first_footer_right: str | None = None
    even_header_left: str | None = None
    even_header_center: str | None = None
    even_header_right: str | None = None
    even_footer_left: str | None = None
    even_footer_center: str | None = None
    even_footer_right: str | None = None
    different_first_page: bool = False
    different_odd_even_pages: bool = False
    font_size: float | None = None

    def __post_init__(self) -> None:
        token_map = _HeaderFooterTokenMap(
            page="1",
            title="Document",
            chapter="Chapter",
            section="Section",
        )
        for field_name in _HEADER_FOOTER_TEMPLATE_FIELDS:
            value = getattr(self, field_name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"HeaderFooterDefaults.{field_name} must be a string")
            try:
                value.format_map(token_map)
            except ValueError as exc:
                raise ValueError(
                    f"HeaderFooterDefaults.{field_name} has an invalid format string"
                ) from exc
        self.different_first_page = bool(self.different_first_page)
        self.different_odd_even_pages = bool(self.different_odd_even_pages)
        if self.font_size is not None and self.font_size <= 0:
            raise ValueError("HeaderFooterDefaults.font_size must be > 0")

    def has_content(self) -> bool:
        """Return whether any header/footer slot has visible template text.

        Returns:
            ``True`` when at least one header or footer template is configured.
        """

        return any(
            bool(getattr(self, field_name))
            for field_name in _HEADER_FOOTER_TEMPLATE_FIELDS
        )

    def content_for(
        self,
        region: Literal["header", "footer"],
        position: Literal["left", "center", "right"],
        *,
        page_kind: Literal["default", "first", "even"] = "default",
    ) -> str | None:
        """Return the template for one header/footer slot.

        Args:
            region: Header/footer region to resolve.
            position: Horizontal slot within the region.
            page_kind: Page variant to resolve.

        Returns:
            Template string for the requested slot, or ``None`` when unset.

        Raises:
            ValueError: If ``region`` or ``position`` is unsupported.
        """

        if region not in {"header", "footer"}:
            raise ValueError("region must be 'header' or 'footer'")
        if position not in {"left", "center", "right"}:
            raise ValueError("position must be 'left', 'center', or 'right'")
        if page_kind == "first" and self.different_first_page:
            override = getattr(self, f"first_{region}_{position}")
            if override is not None:
                return override
        if page_kind == "even" and self.different_odd_even_pages:
            override = getattr(self, f"even_{region}_{position}")
            if override is not None:
                return override
        return getattr(self, f"{region}_{position}")


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
        part_counter: Counter style used for parts.
        footnote_placement: Native or generated content footnote placement.
        auto_footnotes_page: Whether missing footnote pages are auto-rendered.
        run_in_title_style: Default style for run-in paragraph titles.
        heading_styles: Per-level heading style overrides keyed by heading level.
        heading_numbering: Heading numbering configuration.
        bullet_list_style: Default bullet list style.
        numbered_list_style: Default numbered list style.

    Examples:
        ```python
        from oodocs import BlockDefaults, Document, DocumentSettings, HeadingNumbering, HeadingStyle, Paragraph, Section, TextStyle, Theme

        theme = Theme(
            blocks=BlockDefaults(
                heading_numbering=HeadingNumbering(enabled=False),
                heading_styles={1: HeadingStyle(text_style=TextStyle(font_size=18))},
            )
        )
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
    part_counter: CounterStyle = field(
        default_factory=lambda: CounterStyle(counter_format="upper-roman")
    )
    footnote_placement: str = "page"
    auto_footnotes_page: bool = True
    run_in_title_style: RunInTitleStyle = field(default_factory=RunInTitleStyle)
    heading_styles: dict[int, HeadingStyle] = field(default_factory=dict)
    heading_numbering: HeadingNumbering = field(default_factory=HeadingNumbering)
    bullet_list_style: ListStyle = field(
        default_factory=lambda: ListStyle(
            marker=CounterStyle(counter_format="bullet", suffix="")
        )
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
        if not isinstance(self.part_counter, CounterStyle):
            raise TypeError("part_counter must be a CounterStyle")
        if self.footnote_placement not in {"page", "document"}:
            raise ValueError("footnote_placement must be 'page' or 'document'")
        if not isinstance(self.run_in_title_style, RunInTitleStyle):
            raise TypeError("run_in_title_style must be a RunInTitleStyle")
        self.heading_styles = dict(self.heading_styles)
        for level, style in self.heading_styles.items():
            if not isinstance(level, int) or level < 1:
                raise ValueError("heading_styles keys must be positive heading levels")
            if not isinstance(style, HeadingStyle):
                raise TypeError("heading_styles values must be HeadingStyle instances")
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
        links: Optional hyperlink defaults group.
        footnotes: Optional footnote defaults group.
        generated_content: Optional generated-content defaults group.
        locale: Optional document language and localization defaults group.
        page_numbers: Optional page-number defaults group.
        header_footer: Optional page header/footer template defaults group.
        title_matter: Optional title-matter defaults group.
        blocks: Optional block defaults group.
        stylesheet: Optional named style registry.

    Attributes:
        typography: Resolved typography defaults group.
        captions: Resolved caption defaults group.
        citations: Resolved citation defaults group.
        links: Resolved hyperlink defaults group.
        footnotes: Resolved footnote defaults group.
        generated_content: Resolved generated-content defaults group.
        locale: Resolved document language and localization defaults group.
        page_numbers: Resolved page-number defaults group.
        header_footer: Resolved page header/footer template defaults group.
        title_matter: Resolved title-matter defaults group.
        blocks: Resolved block defaults group.
        stylesheet: Resolved named style registry.

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
        from oodocs import Document, DocumentSettings, GeneratedContentDefaults, PageNumberDefaults, ListOfReferences, Theme

        theme = Theme(
            generated_content=GeneratedContentDefaults(list_of_references_title="Bibliography"),
            page_numbers=PageNumberDefaults(show_page_numbers=True, page_number_template="Page {page}"),
        )
        document = Document("Paper", ListOfReferences(), settings=DocumentSettings(theme=theme))
        ```

    Notes:
        Theme construction is grouped by concern. Put font values in
        ``TypographyDefaults``, caption labels and positions in
        ``CaptionDefaults``, page-number settings in ``PageNumberDefaults``,
        and block-level defaults in ``BlockDefaults``.

    See Also:
        ``TypographyDefaults``, ``CaptionDefaults``, ``CitationDefaults``,
        ``LinkDefaults``, ``FootnoteDefaults``, ``GeneratedContentDefaults``,
        ``LocaleDefaults``, ``PageNumberDefaults``, ``HeaderFooterDefaults``,
        ``TitleMatterDefaults``, and ``BlockDefaults`` for grouped
        configuration.
    """

    typography: TypographyDefaults
    captions: CaptionDefaults
    citations: CitationDefaults
    links: LinkDefaults
    footnotes: FootnoteDefaults
    generated_content: GeneratedContentDefaults
    locale: LocaleDefaults
    page_numbers: PageNumberDefaults
    header_footer: HeaderFooterDefaults
    title_matter: TitleMatterDefaults
    blocks: BlockDefaults
    stylesheet: StyleSheet

    def __init__(
        self,
        *,
        typography: TypographyDefaults | None = None,
        captions: CaptionDefaults | None = None,
        citations: CitationDefaults | None = None,
        links: LinkDefaults | None = None,
        footnotes: FootnoteDefaults | None = None,
        generated_content: GeneratedContentDefaults | None = None,
        locale: LocaleDefaults | str | None = None,
        page_numbers: PageNumberDefaults | None = None,
        header_footer: HeaderFooterDefaults | None = None,
        title_matter: TitleMatterDefaults | None = None,
        blocks: BlockDefaults | None = None,
        stylesheet: StyleSheet | None = None,
    ) -> None:
        if locale is None:
            locale_defaults = LocaleDefaults()
        elif isinstance(locale, str):
            locale_defaults = LocaleDefaults.from_locale(locale)
        elif isinstance(locale, LocaleDefaults):
            locale_defaults = locale
        else:
            raise TypeError("Theme.locale must be a LocaleDefaults")

        expected_types = {
            "typography": (typography, TypographyDefaults),
            "captions": (captions, CaptionDefaults),
            "citations": (citations, CitationDefaults),
            "links": (links, LinkDefaults),
            "footnotes": (footnotes, FootnoteDefaults),
            "generated_content": (generated_content, GeneratedContentDefaults),
            "page_numbers": (page_numbers, PageNumberDefaults),
            "header_footer": (header_footer, HeaderFooterDefaults),
            "title_matter": (title_matter, TitleMatterDefaults),
            "blocks": (blocks, BlockDefaults),
            "stylesheet": (stylesheet, StyleSheet),
        }
        for argument_name, (value, expected_type) in expected_types.items():
            if value is not None and not isinstance(value, expected_type):
                raise TypeError(
                    f"Theme.{argument_name} must be a {expected_type.__name__}"
                )

        self.locale = locale_defaults
        self.typography = typography or self.locale.typography or TypographyDefaults()
        self.captions = captions or self.locale.captions
        self.citations = citations or CitationDefaults()
        self.links = links or LinkDefaults()
        self.footnotes = footnotes or FootnoteDefaults()
        self.generated_content = generated_content or self.locale.generated_content
        self.page_numbers = page_numbers or PageNumberDefaults()
        self.header_footer = header_footer or HeaderFooterDefaults()
        self.title_matter = title_matter or TitleMatterDefaults()
        self.blocks = blocks or BlockDefaults()
        self.stylesheet = stylesheet or StyleSheet.default()

    @classmethod
    def from_locale(cls, language_tag: str, **overrides: object) -> Theme:
        """Create a theme from a built-in locale bundle.

        Args:
            language_tag: Built-in locale tag such as ``"en-US"`` or
                ``"ko-KR"``.
            **overrides: Any regular ``Theme`` keyword overrides.

        Returns:
            Theme with localized caption labels, generated-page titles,
            glossary labels, date formatting, and locale typography.

        Examples:
            ```python
            theme = Theme.from_locale("ko-KR")
            assert theme.resolve_language_tag() == "ko-KR"
            ```
        """

        return cls(locale=LocaleDefaults.from_locale(language_tag), **overrides)

    def resolve_body_font(self) -> str:
        """Return the document-wide proportional font name.

        Returns:
            Body font family used for ordinary text and generated content.

        Examples:
            ```python
            from oodocs import Theme, TypographyDefaults

            theme = Theme(typography=TypographyDefaults(body_font_name="Arial"))
            assert theme.resolve_body_font() == "Arial"
            ```
        """

        return self.typography.body_font_name

    def resolve_language_tag(self) -> str:
        """Return the document language tag used by renderers.

        Returns:
            BCP 47-style language tag such as ``"en-US"`` or ``"ko-KR"``.
        """

        return self.locale.language_tag

    def resolve_monospace_font(self) -> str:
        """Return the document-wide monospace font name.

        Returns:
            Monospace font family used for code spans and code blocks.

        Examples:
            ```python
            from oodocs import Theme, TypographyDefaults

            theme = Theme(typography=TypographyDefaults(monospace_font_name="Consolas"))
            assert theme.resolve_monospace_font() == "Consolas"
            ```
        """

        return self.typography.monospace_font_name

    def resolve_heading_style(
        self,
        level: int,
        override: HeadingStyle | None = None,
    ) -> HeadingStyle:
        """Return the effective heading style for a heading level.

        Args:
            level: One-based heading level.
            override: Optional section-specific heading style.

        Returns:
            Effective heading style after theme defaults, per-level defaults,
            and the direct override are merged.

        Examples:
            ```python
            from oodocs import BlockDefaults, HeadingStyle, TextStyle, Theme

            theme = Theme(
                blocks=BlockDefaults(
                    heading_styles={2: HeadingStyle(text_style=TextStyle(font_size=14))}
                )
            )
            assert theme.resolve_heading_style(2).text_style.font_size == 14
            ```
        """

        if override is not None and not isinstance(override, HeadingStyle):
            raise TypeError("override must be a HeadingStyle")
        base = HeadingStyle(
            text_style=TextStyle(
                font_size=self._default_heading_size(level),
                bold=self._default_heading_emphasis(level)[0],
                italic=self._default_heading_emphasis(level)[1],
            ),
            space_before=18 if level == 1 else 12,
            space_after=10 if level == 1 else 6,
            leading=self._default_heading_size(level) * 1.2,
            text_alignment="left",
        )
        return base.merged(self.blocks.heading_styles.get(level), override)

    def resolve_heading_size(self, level: int) -> float:
        """Return the configured font size for a heading level.

        Args:
            level: One-based heading level.

        Returns:
            Font size for the nearest configured level.

        Examples:
            ```python
            assert Theme(typography=TypographyDefaults(heading_sizes=(20.0, 16.0))).resolve_heading_size(3) == 16.0
            ```
        """

        return self.resolve_heading_style(level).text_style.font_size or self._default_heading_size(level)

    def _default_heading_size(self, level: int) -> float:
        index = min(max(level - 1, 0), len(self.typography.heading_sizes) - 1)
        return self.typography.heading_sizes[index]

    def resolve_heading_emphasis(self, level: int) -> tuple[bool, bool]:
        """Return heading emphasis for a heading level.

        Args:
            level: One-based heading level.

        Returns:
            ``(bold, italic)`` emphasis flags.

        Examples:
            ```python
            assert Theme().resolve_heading_emphasis(1) == (True, False)
            ```
        """

        style = self.resolve_heading_style(level)
        return bool(style.text_style.bold), bool(style.text_style.italic)

    def _default_heading_emphasis(self, level: int) -> tuple[bool, bool]:
        emphasis = (
            (True, False),
            (True, False),
            (True, True),
            (False, True),
        )
        index = min(max(level - 1, 0), len(emphasis) - 1)
        return emphasis[index]

    def resolve_heading_text_alignment(self, level: int) -> str:
        """Return the alignment to use for the given heading level.

        Args:
            level: One-based heading level.

        Returns:
            Heading alignment.

        Examples:
            ```python
            assert Theme().resolve_heading_text_alignment(2) == "left"
            ```
        """

        return self.resolve_heading_style(level).text_alignment or "left"

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

    def resolve_link_text_style(self, override: TextStyle | None = None) -> TextStyle:
        """Return the effective text style for hyperlink labels.

        Args:
            override: Optional per-link style.

        Returns:
            Theme link style merged with the per-link override.
        """

        return self.links.text_style.merged(override)

    def resolve_caption_label(
        self,
        kind: Literal["table", "figure"],
        context: Literal["caption", "reference"],
    ) -> str:
        """Return the effective label for captions or inline references.

        Args:
            kind: Label target, either ``"table"`` or ``"figure"``.
            context: Label context, either ``"caption"`` or ``"reference"``.

        Returns:
            Effective caption or reference label.

        Raises:
            ValueError: If ``kind`` or ``context`` is unsupported.

        Examples:
            ```python
            theme = Theme(captions=CaptionDefaults(table_caption_label="Tbl."))
            assert theme.resolve_caption_label("table", "caption") == "Tbl."
            ```
        """

        if kind not in {"table", "figure"}:
            raise ValueError("caption label kind must be 'table' or 'figure'")
        if context not in {"caption", "reference"}:
            raise ValueError("caption label context must be 'caption' or 'reference'")
        if kind == "table" and context == "caption":
            return self.captions.table_caption_label or self.captions.table_label
        if kind == "table":
            return self.captions.table_reference_label or self.captions.table_label
        if context == "caption":
            return self.captions.figure_caption_label or self.captions.figure_label
        return self.captions.figure_reference_label or self.captions.figure_label

    def resolve_generated_page_title(
        self,
        kind: Literal[
            "list_of_tables",
            "list_of_figures",
            "list_of_algorithms",
            "list_of_comments",
            "list_of_footnotes",
            "list_of_references",
            "list_of_glossary_terms",
            "table_of_contents",
        ],
    ) -> str:
        """Return the default title for generated document content.

        Args:
            kind: Generated content kind. Supported values are
                ``"list_of_tables"``, ``"list_of_figures"``,
                ``"list_of_algorithms"``,
                ``"list_of_comments"``, ``"list_of_footnotes"``,
                ``"list_of_references"``, ``"list_of_glossary_terms"``, and
                ``"table_of_contents"``.

        Returns:
            Default title text for the generated content block.

        Raises:
            ValueError: If ``kind`` is unsupported.

        Examples:
            ```python
            from oodocs import GeneratedContentDefaults, Theme

            theme = Theme(
                generated_content=GeneratedContentDefaults(list_of_references_title="Bibliography")
            )
            assert theme.resolve_generated_page_title("list_of_references") == "Bibliography"
            ```
        """

        titles = {
            "list_of_tables": self.generated_content.list_of_tables_title,
            "list_of_figures": self.generated_content.list_of_figures_title,
            "list_of_algorithms": self.generated_content.list_of_algorithms_title,
            "list_of_comments": self.generated_content.list_of_comments_title,
            "list_of_footnotes": self.generated_content.list_of_footnotes_title,
            "list_of_references": self.generated_content.list_of_references_title,
            "list_of_glossary_terms": self.generated_content.list_of_glossary_terms_title,
            "table_of_contents": self.generated_content.table_of_contents_title,
        }
        try:
            return titles[kind]
        except KeyError as exc:
            raise ValueError(f"unsupported generated content kind: {kind!r}") from exc

    def resolve_glossary_headers(self) -> tuple[str, str]:
        """Return default glossary table headers for the active locale.

        Returns:
            ``(term_header, definition_header)`` labels.
        """

        return self.locale.glossary_headers

    def format_date(self, value: date_type | datetime | str) -> str:
        """Format a date using the active locale defaults.

        Args:
            value: Date, datetime, or ISO date string to format.

        Returns:
            Localized date text.
        """

        return self.locale.format_date(value)

    def pdf_font_fallback_guide(self) -> str:
        """Return a concise PDF font fallback guide for the active locale.

        Returns:
            Human-readable PDF font fallback guidance.
        """

        if not self.locale.pdf_font_fallbacks:
            return (
                "PDF output uses the theme typography fonts and ReportLab's "
                "built-in fallbacks."
            )
        fallback_list = ", ".join(self.locale.pdf_font_fallbacks)
        return (
            f"PDF output for {self.locale.language_tag} should use a font with "
            f"script coverage, for example: {fallback_list}."
        )

    def effective_header_footer(self) -> HeaderFooterDefaults:
        """Return configured header/footer templates, including legacy page numbers.

        Returns:
            Effective header/footer defaults for renderers.
        """

        if self.header_footer.has_content():
            return self.header_footer
        if not self.page_numbers.show_page_numbers:
            return self.header_footer
        slots = {
            f"footer_{self.page_numbers.page_number_alignment}": (
                self.page_numbers.page_number_template
            )
        }
        return HeaderFooterDefaults(
            **slots,
            font_size=self.page_numbers.page_number_font_size,
        )

    def uses_header_footer(self) -> bool:
        """Return whether renderers should emit a header/footer layer.

        Returns:
            ``True`` when any effective header or footer template is configured.
        """

        return self.effective_header_footer().has_content()

    def resolve_header_footer_font_size(self) -> float:
        """Return effective header/footer font size in points.

        Returns:
            Header/footer font size in points.
        """

        return (
            self.effective_header_footer().font_size
            or self.page_numbers.page_number_font_size
        )

    def resolve_header_footer_template(
        self,
        region: Literal["header", "footer"],
        position: Literal["left", "center", "right"],
        *,
        page_kind: Literal["default", "first", "even"] = "default",
    ) -> str | None:
        """Return a raw header/footer template for one slot.

        Args:
            region: Header/footer region to resolve.
            position: Horizontal slot within the region.
            page_kind: Page variant to resolve.

        Returns:
            Raw template for the requested slot, or ``None`` when unset.
        """

        return self.effective_header_footer().content_for(
            region,
            position,
            page_kind=page_kind,
        )

    def format_header_footer_text(
        self,
        template: str | None,
        *,
        page_number: int,
        front_matter: bool = False,
        title: str = "",
        chapter: str = "",
        section: str = "",
    ) -> str:
        """Resolve a header/footer template to plain text.

        Args:
            template: Header/footer template to resolve.
            page_number: One-based logical page number.
            front_matter: Whether to use front-matter numbering.
            title: Current document title.
            chapter: Current chapter title.
            section: Current section title.

        Returns:
            Plain text header/footer content.
        """

        if not template:
            return ""
        page_label = self.format_page_number(page_number, front_matter=front_matter)
        values = _HeaderFooterTokenMap(
            page=page_label,
            title=title,
            chapter=chapter,
            section=section,
        )
        return template.format_map(values)

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

        counter = (
            self.page_numbers.front_matter_counter
            if front_matter
            else self.page_numbers.main_matter_counter
        )
        page_label = counter.format_value(page_number)
        return self.page_numbers.page_number_template.format(page=page_label)

    def format_heading_label(
        self,
        counters: Sequence[int],
        heading_style: HeadingStyle | None = None,
    ) -> str | None:
        """Render a heading numbering label for nested section counters.

        Args:
            counters: Counter values from top-level heading through current
                heading.
            heading_style: Optional style override for the current heading.

        Returns:
            Formatted heading label, or ``None`` when numbering is disabled.

        Examples:
            ```python
            assert Theme().format_heading_label([1, 2]) == "1.2"
            ```
        """

        if not self.blocks.heading_numbering.enabled:
            return None
        level = len(counters)
        resolved_style = self.resolve_heading_style(level, heading_style)
        if resolved_style.numbering is None:
            return self.blocks.heading_numbering.format_label(counters)
        pieces = []
        for index, value in enumerate(counters):
            counter_style = self.blocks.heading_numbering.level_styles[
                min(index, len(self.blocks.heading_numbering.level_styles) - 1)
            ]
            if index == level - 1:
                counter_style = resolved_style.numbering
            pieces.append(counter_style.format_value(value))
        return (
            f"{self.blocks.heading_numbering.prefix}"
            f"{self.blocks.heading_numbering.separator.join(pieces)}"
            f"{self.blocks.heading_numbering.suffix}"
        )

    def format_appendix_heading_label(self, counters: Sequence[int]) -> str | None:
        """Render an appendix heading label such as ``A.1``.

        Args:
            counters: Counter values from the appendix chapter through the
                current heading.

        Returns:
            Formatted appendix heading label, or ``None`` when heading
            numbering is disabled.

        Examples:
            ```python
            assert Theme().format_appendix_heading_label([2, 3]) == "B.3"
            ```
        """

        if not self.blocks.heading_numbering.enabled:
            return None
        if not counters:
            return None
        appendix_styles = (
            CounterStyle(counter_format="upper-alpha"),
            *self.blocks.heading_numbering.level_styles[1:],
        )
        pieces = [
            appendix_styles[min(index, len(appendix_styles) - 1)].format_value(value)
            for index, value in enumerate(counters)
        ]
        return (
            f"{self.blocks.heading_numbering.prefix}"
            f"{self.blocks.heading_numbering.separator.join(pieces)}"
            f"{self.blocks.heading_numbering.suffix}"
        )

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
        marker = self.blocks.part_counter.format_value(value)
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
    "CounterStyle",
    "DEFAULT_FOOTNOTE_SYMBOLS",
    "FootnoteDefaults",
    "FootnoteStyle",
    "GeneratedContentDefaults",
    "HeaderFooterDefaults",
    "HeadingStyle",
    "HeadingNumbering",
    "LinkDefaults",
    "ListStyle",
    "LocaleDefaults",
    "PageNumberDefaults",
    "ParagraphStyle",
    "RunInTitleStyle",
    "TableStyle",
    "TextStyle",
    "TitleMatterDefaults",
    "TypographyDefaults",
    "Theme",
]
