"""Public style objects and theme configuration."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Sequence

from oodocs.core import (
    format_counter_value,
    length_to_inches,
    normalize_color,
    normalize_counter_format,
    normalize_length_unit,
    normalize_text_alignment,
    normalize_vertical_alignment,
)
from oodocs.components.references import (
    normalize_citation_format,
    normalize_reference_format,
)

_UNSET = object()


def _style_with_overrides(
    style: object | None,
    style_type: type,
    overrides: dict[str, object | None],
) -> object:
    values = {name: value for name, value in overrides.items() if value is not None}
    if style is None:
        return style_type(**values)
    if not values:
        return style
    merged = {style_field.name: getattr(style, style_field.name) for style_field in fields(style_type)}
    merged.update(values)
    return style_type(**merged)


def paragraph_style_with_overrides(
    style: ParagraphStyle | None,
    **overrides: object | None,
) -> ParagraphStyle:
    """Return a paragraph style with direct keyword overrides applied.

    Args:
        style: Base paragraph style or ``None``.
        **overrides: Paragraph style fields to override when not ``None``.

    Returns:
        Existing style, copied style, or a new style with overrides applied.
    """

    return _style_with_overrides(style, ParagraphStyle, overrides)  # type: ignore[return-value]


def box_style_with_overrides(
    style: BoxStyle | None,
    **overrides: object | None,
) -> BoxStyle:
    """Return a box style with direct keyword overrides applied.

    Args:
        style: Base box style or ``None``.
        **overrides: Box style fields to override when not ``None``.

    Returns:
        Existing style, copied style, or a new style with overrides applied.
    """

    return _style_with_overrides(style, BoxStyle, overrides)  # type: ignore[return-value]


def table_style_with_overrides(
    style: TableStyle | None,
    **overrides: object | None,
) -> TableStyle:
    """Return a table style with direct keyword overrides applied.

    Args:
        style: Base table style or ``None``.
        **overrides: Table style fields to override when not ``None``.

    Returns:
        Existing style, copied style, or a new style with overrides applied.
    """

    return _style_with_overrides(style, TableStyle, overrides)  # type: ignore[return-value]


def list_style_with_overrides(
    style: ListStyle | None,
    *,
    ordered: bool,
    **overrides: object | None,
) -> ListStyle | None:
    """Return a concrete list style when direct list keyword overrides are used.

    Args:
        style: Base list style or ``None``.
        ordered: Whether the target list is ordered.
        **overrides: List style fields to override when not ``None``.

    Returns:
        ``None`` when no style is needed, otherwise a concrete list style.
    """

    values = {name: value for name, value in overrides.items() if value is not None}
    if style is None and not values:
        return None
    base = style or (
        ListStyle()
        if ordered
        else ListStyle(marker_format="bullet", suffix="")
    )
    merged = {style_field.name: getattr(base, style_field.name) for style_field in fields(ListStyle)}
    merged.update(values)
    return ListStyle(**merged)


@dataclass(slots=True)
class TextStyle:
    """Inline text styling overrides.

    Each field is optional so styles can be layered and merged.

    Attributes:
        font_name: Optional font family.
        font_size: Optional font size.
        color: Optional text color as a hex string.
        highlight_color: Optional highlight color as a hex string.
        bold: Optional bold override.
        italic: Optional italic override.
        underline: Optional underline override.
        strikethrough: Optional strikethrough override.
        small_caps: Optional small-caps override.
        all_caps: Optional all-caps override.
        subscript: Optional subscript override.
        superscript: Optional superscript override.
    """

    font_name: str | None = None
    font_size: float | None = None
    color: str | None = None
    highlight_color: str | None = None
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    strikethrough: bool | None = None
    small_caps: bool | None = None
    all_caps: bool | None = None
    subscript: bool | None = None
    superscript: bool | None = None

    def __post_init__(self) -> None:
        self.color = normalize_color(self.color)
        self.highlight_color = normalize_color(self.highlight_color)
        if self.subscript and self.superscript:
            raise ValueError("TextStyle cannot set both subscript and superscript")

    def merged(self, *others: TextStyle | None) -> TextStyle:
        """Return a new style with later values overriding earlier ones.

        Args:
            *others: Styles to overlay from left to right.

        Returns:
            New merged text style.

        Raises:
            ValueError: If the merged style sets both subscript and superscript.
        """

        merged = TextStyle(
            font_name=self.font_name,
            font_size=self.font_size,
            color=self.color,
            highlight_color=self.highlight_color,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strikethrough=self.strikethrough,
            small_caps=self.small_caps,
            all_caps=self.all_caps,
            subscript=self.subscript,
            superscript=self.superscript,
        )
        for other in others:
            if other is None:
                continue
            for field_name in (
                "font_name",
                "font_size",
                "color",
                "highlight_color",
                "bold",
                "italic",
                "underline",
                "strikethrough",
                "small_caps",
                "all_caps",
                "subscript",
                "superscript",
            ):
                value = getattr(other, field_name)
                if value is not None:
                    setattr(merged, field_name, value)
        if merged.subscript and merged.superscript:
            raise ValueError("TextStyle cannot set both subscript and superscript")
        return merged


@dataclass(slots=True)
class ParagraphStyle:
    """Block-level paragraph spacing and alignment settings.

    Attributes:
        alignment: Optional text alignment.
        space_before: Optional spacing before the paragraph.
        space_after: Optional spacing after the paragraph.
        leading: Optional line spacing.
        left_indent: Optional left indent.
        right_indent: Optional right indent.
        first_line_indent: Optional first-line indent.
        keep_together: Optional keep-together flag.
        keep_with_next: Optional keep-with-next flag.
        page_break_before: Optional page-break-before flag.
        widow_control: Optional widow-control flag.
        unit: Unit for length values.
    """

    alignment: str | None = None
    space_before: float | None = None
    space_after: float | None = 12.0
    leading: float | None = None
    left_indent: float | None = None
    right_indent: float | None = None
    first_line_indent: float | None = None
    keep_together: bool | None = None
    keep_with_next: bool | None = None
    page_break_before: bool | None = None
    widow_control: bool | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        self.alignment = (
            normalize_text_alignment(self.alignment)
            if self.alignment is not None
            else None
        )
        self.unit = normalize_length_unit(self.unit) if self.unit is not None else None
        if self.space_before is not None and self.space_before < 0:
            raise ValueError("ParagraphStyle.space_before must be >= 0")
        if self.space_after is not None and self.space_after < 0:
            raise ValueError("ParagraphStyle.space_after must be >= 0")
        if self.leading is not None and self.leading <= 0:
            raise ValueError("ParagraphStyle.leading must be > 0")
        if self.left_indent is not None and self.left_indent < 0:
            raise ValueError("ParagraphStyle.left_indent must be >= 0")
        if self.right_indent is not None and self.right_indent < 0:
            raise ValueError("ParagraphStyle.right_indent must be >= 0")

    @classmethod
    def hanging(
        cls,
        left: float = 0.5,
        *,
        by: float | None = None,
        alignment: str | None = None,
        space_before: float | None = None,
        space_after: float | None = 12.0,
        leading: float | None = None,
        keep_together: bool | None = None,
        keep_with_next: bool | None = None,
        page_break_before: bool | None = None,
        widow_control: bool | None = None,
        unit: str | None = None,
    ) -> ParagraphStyle:
        """Create a hanging-indent paragraph style.

        Args:
            left: Left indent.
            by: Hanging amount. Defaults to ``left``.
            alignment: Optional text alignment.
            space_before: Optional spacing before the paragraph.
            space_after: Optional spacing after the paragraph.
            leading: Optional line spacing.
            keep_together: Optional keep-together flag.
            keep_with_next: Optional keep-with-next flag.
            page_break_before: Optional page-break-before flag.
            widow_control: Optional widow-control flag.
            unit: Unit for length values.

        Returns:
            Paragraph style with a negative first-line indent.

        Raises:
            ValueError: If ``by`` is negative.
        """

        hanging_by = left if by is None else by
        if hanging_by < 0:
            raise ValueError("ParagraphStyle.hanging by must be >= 0")
        return cls(
            alignment=alignment,
            space_before=space_before,
            space_after=space_after,
            leading=leading,
            left_indent=left,
            first_line_indent=-hanging_by,
            keep_together=keep_together,
            keep_with_next=keep_with_next,
            page_break_before=page_break_before,
            widow_control=widow_control,
            unit=unit,
        )

    def left_indent_in_inches(self, default_unit: str) -> float | None:
        """Return left indent in inches.

        Args:
            default_unit: Unit to use when this style has no explicit unit.

        Returns:
            Left indent in inches, or ``None``.
        """

        return self._indent_in_inches(self.left_indent, default_unit)

    def right_indent_in_inches(self, default_unit: str) -> float | None:
        """Return right indent in inches.

        Args:
            default_unit: Unit to use when this style has no explicit unit.

        Returns:
            Right indent in inches, or ``None``.
        """

        return self._indent_in_inches(self.right_indent, default_unit)

    def first_line_indent_in_inches(self, default_unit: str) -> float | None:
        """Return first-line indent in inches.

        Args:
            default_unit: Unit to use when this style has no explicit unit.

        Returns:
            First-line indent in inches, or ``None``.
        """

        return self._indent_in_inches(self.first_line_indent, default_unit)

    def _indent_in_inches(self, value: float | None, default_unit: str) -> float | None:
        if value is None:
            return None
        return length_to_inches(value, self.unit or default_unit)


@dataclass(slots=True)
class HeadingNumbering:
    """Configurable hierarchical numbering for authored headings.

    Attributes:
        enabled: Whether heading numbering is enabled.
        formats: Counter formats for successive heading levels.
        separator: Separator between level counters.
        prefix: Prefix before the full label.
        suffix: Suffix after the full label.
    """

    enabled: bool = True
    formats: tuple[str, ...] = ("decimal", "decimal", "decimal", "decimal")
    separator: str = "."
    prefix: str = ""
    suffix: str = ""

    def __post_init__(self) -> None:
        self.formats = tuple(normalize_counter_format(value) for value in self.formats)
        if not self.formats:
            raise ValueError("HeadingNumbering.formats must not be empty")

    def format_label(self, counters: Sequence[int]) -> str | None:
        """Render a heading label such as ``1.2.3`` from nested counters.

        Args:
            counters: Counter values from top-level heading through current
                heading.

        Returns:
            Formatted heading label, or ``None`` when numbering is disabled.
        """

        if not self.enabled:
            return None

        pieces = [
            format_counter_value(value, self.formats[min(index, len(self.formats) - 1)])
            for index, value in enumerate(counters)
        ]
        return f"{self.prefix}{self.separator.join(pieces)}{self.suffix}"


@dataclass(slots=True)
class ListStyle:
    """Marker formatting for bullet and ordered lists.

    Attributes:
        marker_format: Counter format for markers.
        bullet: Bullet glyph when ``marker_format`` is ``"bullet"``.
        prefix: Marker prefix.
        suffix: Marker suffix.
        start: First counter value for ordered markers.
        indent: List indent in inches.
        marker_gap: Gap between marker and item text in inches.
    """

    marker_format: str = "decimal"
    bullet: str = "\u2022"
    prefix: str = ""
    suffix: str = "."
    start: int = 1
    indent: float = 0.25
    marker_gap: float = 0.1

    def __post_init__(self) -> None:
        self.marker_format = normalize_counter_format(self.marker_format)
        if self.start < 1:
            raise ValueError("ListStyle.start must be >= 1")
        if self.indent < 0:
            raise ValueError("ListStyle.indent must be >= 0")
        if self.marker_gap < 0:
            raise ValueError("ListStyle.marker_gap must be >= 0")

    def marker_for(self, index: int) -> str:
        """Return the rendered marker for a zero-based list item index.

        Args:
            index: Zero-based list item index.

        Returns:
            Rendered marker string.
        """

        if self.marker_format == "none":
            return ""

        marker_value = format_counter_value(
            index + self.start,
            self.marker_format,
            bullet=self.bullet,
        )
        return f"{self.prefix}{marker_value}{self.suffix}"


@dataclass(slots=True)
class BoxStyle:
    """Shared box styling for visually grouped content."""

    border_color: str = "B7C2D0"
    background_color: str = "F7FAFC"
    title_background_color: str | None = None
    title_text_color: str | None = None
    border_width: float = 0.75
    padding: float = 6.0
    padding_top: float | None = None
    padding_right: float | None = None
    padding_bottom: float | None = None
    padding_left: float | None = None
    space_after: float = 12.0
    width: float | None = None
    unit: str | None = None
    alignment: str | None = None

    def __post_init__(self) -> None:
        self.border_color = normalize_color(self.border_color) or "B7C2D0"
        self.background_color = normalize_color(self.background_color) or "F7FAFC"
        self.title_background_color = normalize_color(self.title_background_color)
        self.title_text_color = normalize_color(self.title_text_color)
        self.unit = normalize_length_unit(self.unit) if self.unit is not None else None
        if self.border_width < 0:
            raise ValueError("BoxStyle.border_width must be >= 0")
        if self.padding < 0:
            raise ValueError("BoxStyle.padding must be >= 0")
        for field_name in ("padding_top", "padding_right", "padding_bottom", "padding_left"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"BoxStyle.{field_name} must be >= 0")
        if self.space_after < 0:
            raise ValueError("BoxStyle.space_after must be >= 0")
        if self.width is not None and self.width <= 0:
            raise ValueError("BoxStyle.width must be > 0")
        if self.alignment is not None and self.alignment not in {"left", "center", "right"}:
            raise ValueError(f"Unsupported BoxStyle alignment: {self.alignment!r}")

    def resolved_padding(self) -> tuple[float, float, float, float]:
        """Return top, right, bottom, and left padding in points.

        Returns:
            ``(top, right, bottom, left)`` padding values.
        """

        return (
            self.padding if self.padding_top is None else self.padding_top,
            self.padding if self.padding_right is None else self.padding_right,
            self.padding if self.padding_bottom is None else self.padding_bottom,
            self.padding if self.padding_left is None else self.padding_left,
        )


@dataclass(slots=True)
class TableStyle:
    """Renderer-neutral table styling options."""

    header_background_color: str = "E8EDF5"
    header_text_color: str = "000000"
    border_color: str = "B7C2D0"
    body_background_color: str | None = None
    alternate_row_background_color: str | None = None
    cell_horizontal_alignment: str | None = None
    cell_vertical_alignment: str | None = None
    header_horizontal_alignment: str | None = None
    header_vertical_alignment: str | None = None
    cell_padding: float = 5.0
    cell_padding_top: float | None = None
    cell_padding_right: float | None = None
    cell_padding_bottom: float | None = None
    cell_padding_left: float | None = None
    border_width: float = 0.5
    repeat_header_rows: bool = False

    def __post_init__(self) -> None:
        self.header_background_color = normalize_color(self.header_background_color) or "E8EDF5"
        self.header_text_color = normalize_color(self.header_text_color) or "000000"
        self.border_color = normalize_color(self.border_color) or "B7C2D0"
        self.body_background_color = normalize_color(self.body_background_color)
        self.alternate_row_background_color = normalize_color(self.alternate_row_background_color)
        self.cell_horizontal_alignment = (
            normalize_text_alignment(self.cell_horizontal_alignment)
            if self.cell_horizontal_alignment is not None
            else None
        )
        self.cell_vertical_alignment = (
            normalize_vertical_alignment(self.cell_vertical_alignment)
            if self.cell_vertical_alignment is not None
            else None
        )
        self.header_horizontal_alignment = (
            normalize_text_alignment(self.header_horizontal_alignment)
            if self.header_horizontal_alignment is not None
            else None
        )
        self.header_vertical_alignment = (
            normalize_vertical_alignment(self.header_vertical_alignment)
            if self.header_vertical_alignment is not None
            else None
        )
        if self.cell_padding < 0:
            raise ValueError("TableStyle.cell_padding must be >= 0")
        for field_name in (
            "cell_padding_top",
            "cell_padding_right",
            "cell_padding_bottom",
            "cell_padding_left",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"TableStyle.{field_name} must be >= 0")
        if self.border_width < 0:
            raise ValueError("TableStyle.border_width must be >= 0")

    @classmethod
    def plain(cls) -> TableStyle:
        """Create a minimally styled table preset.

        Returns:
            Plain table style.
        """

        return cls(
            header_background_color="FFFFFF",
            border_color="DADDE3",
            cell_padding=5.0,
            border_width=0.5,
        )

    @classmethod
    def compact(cls) -> TableStyle:
        """Create a dense preset for compact data tables.

        Returns:
            Compact table style.
        """

        return cls(
            header_background_color="F1F4F8",
            border_color="C9D2DE",
            alternate_row_background_color="FAFBFC",
            cell_padding=3.0,
            border_width=0.4,
            repeat_header_rows=True,
        )

    @classmethod
    def evidence(cls) -> TableStyle:
        """Create a preset for release evidence and audit tables.

        Returns:
            Evidence-oriented table style.
        """

        return cls(
            header_background_color="E7EEF7",
            border_color="AEBBCC",
            body_background_color="FFFFFF",
            alternate_row_background_color="F8FBFD",
            cell_padding=4.0,
            border_width=0.5,
            repeat_header_rows=True,
        )

    def resolved_cell_padding(self) -> tuple[float, float, float, float]:
        """Return top, right, bottom, and left cell padding in points.

        Returns:
            ``(top, right, bottom, left)`` cell padding values.
        """

        return (
            self.cell_padding if self.cell_padding_top is None else self.cell_padding_top,
            self.cell_padding if self.cell_padding_right is None else self.cell_padding_right,
            self.cell_padding if self.cell_padding_bottom is None else self.cell_padding_bottom,
            self.cell_padding if self.cell_padding_left is None else self.cell_padding_left,
        )


@dataclass(slots=True)
class TypographyOptions:
    """Grouped document-wide font and size defaults for ``Theme``."""

    body_font_name: str = "Times New Roman"
    monospace_font_name: str = "Courier New"
    title_font_size: float = 22.0
    body_font_size: float = 11.0
    heading_sizes: tuple[float, ...] = (18.0, 15.0, 13.0, 11.5)
    caption_font_size: float | None = None


@dataclass(slots=True)
class CaptionOptions:
    """Grouped caption labels, reference labels, positions, and alignment."""

    caption_alignment: str = "center"
    table_caption_position: str = "above"
    figure_caption_position: str = "below"
    table_label: str = "Table"
    figure_label: str = "Figure"
    table_caption_label: str | None = None
    figure_caption_label: str | None = None
    table_reference_label: str | None = None
    figure_reference_label: str | None = None


@dataclass(slots=True)
class CitationOptions:
    """Grouped citation and bibliography formatting defaults."""

    citation_format: str = "numeric"
    reference_format: str = "plain"


@dataclass(slots=True)
class GeneratedPageOptions:
    """Grouped generated-page titles and generated-page layout defaults."""

    list_of_tables_title: str = "List of Tables"
    list_of_figures_title: str = "List of Figures"
    comments_title: str = "Comments"
    footnotes_title: str = "Footnotes"
    references_title: str = "References"
    contents_title: str = "Contents"
    generated_section_level: int = 2
    generated_page_breaks: bool = True


@dataclass(slots=True)
class PageNumberOptions:
    """Grouped footer page-number defaults."""

    show_page_numbers: bool = False
    page_number_alignment: str = "center"
    page_number_format: str = "{page}"
    front_matter_page_number_format: str = "lower-roman"
    main_matter_page_number_format: str = "decimal"
    page_number_font_size: float = 9.0


@dataclass(slots=True)
class TitleMatterOptions:
    """Grouped title, subtitle, author, and affiliation alignment defaults."""

    title_alignment: str = "center"
    subtitle_alignment: str = "center"
    author_alignment: str = "center"
    affiliation_alignment: str = "center"
    author_detail_alignment: str = "center"


@dataclass(slots=True)
class BlockOptions:
    """Grouped block-level document defaults for ``Theme``."""

    page_background_color: str = "FFFFFF"
    paragraph_alignment: str = "justify"
    table_alignment: str = "center"
    figure_alignment: str = "center"
    box_alignment: str = "center"
    part_label: str = "Part"
    part_number_format: str = "upper-roman"
    footnote_placement: str = "page"
    auto_footnotes_page: bool = True
    heading_numbering: HeadingNumbering = field(default_factory=HeadingNumbering)
    bullet_list_style: ListStyle = field(
        default_factory=lambda: ListStyle(marker_format="bullet", suffix="")
    )
    numbered_list_style: ListStyle = field(default_factory=ListStyle)


@dataclass(slots=True, init=False)
class Theme:
    """Document-wide renderer defaults.

    Args:
        *options: Optional grouped option objects. Supported types are
            ``TypographyOptions``, ``CaptionOptions``, ``CitationOptions``,
            ``GeneratedPageOptions``, ``PageNumberOptions``,
            ``TitleMatterOptions``, and ``BlockOptions``.
        typography: Optional typography option group.
        captions: Optional caption option group.
        citation_options: Optional citation option group.
        generated_pages: Optional generated-page option group.
        page_numbers: Optional page-number option group.
        title_matter: Optional title-matter option group.
        blocks: Optional block option group.
        **direct_options: Individual theme field overrides. Direct options take
            precedence over grouped option values.

    Raises:
        TypeError: If a positional option is not a supported option group.
        ValueError: If alignment, format, numbering, or color values are
            invalid.
    """

    typography: TypographyOptions
    captions: CaptionOptions
    citation_options: CitationOptions
    generated_pages: GeneratedPageOptions
    page_numbers: PageNumberOptions
    title_matter: TitleMatterOptions
    blocks: BlockOptions
    page_background_color: str = "FFFFFF"
    body_font_name: str = "Times New Roman"
    monospace_font_name: str = "Courier New"
    title_font_size: float = 22.0
    body_font_size: float = 11.0
    paragraph_alignment: str = "justify"
    heading_sizes: tuple[float, ...] = (18.0, 15.0, 13.0, 11.5)
    caption_font_size: float | None = None
    caption_alignment: str = "center"
    table_alignment: str = "center"
    figure_alignment: str = "center"
    box_alignment: str = "center"
    table_caption_position: str = "above"
    figure_caption_position: str = "below"
    table_label: str = "Table"
    figure_label: str = "Figure"
    part_label: str = "Part"
    part_number_format: str = "upper-roman"
    table_caption_label: str | None = None
    figure_caption_label: str | None = None
    table_reference_label: str | None = None
    figure_reference_label: str | None = None
    citation_format: str = "numeric"
    reference_format: str = "plain"
    list_of_tables_title: str = "List of Tables"
    list_of_figures_title: str = "List of Figures"
    comments_title: str = "Comments"
    footnotes_title: str = "Footnotes"
    references_title: str = "References"
    contents_title: str = "Contents"
    generated_section_level: int = 2
    generated_page_breaks: bool = True
    footnote_placement: str = "page"
    auto_footnotes_page: bool = True
    show_page_numbers: bool = False
    page_number_alignment: str = "center"
    page_number_format: str = "{page}"
    front_matter_page_number_format: str = "lower-roman"
    main_matter_page_number_format: str = "decimal"
    page_number_font_size: float = 9.0
    title_alignment: str = "center"
    subtitle_alignment: str = "center"
    author_alignment: str = "center"
    affiliation_alignment: str = "center"
    author_detail_alignment: str = "center"
    heading_numbering: HeadingNumbering = field(default_factory=HeadingNumbering)
    bullet_list_style: ListStyle = field(
        default_factory=lambda: ListStyle(marker_format="bullet", suffix="")
    )
    numbered_list_style: ListStyle = field(default_factory=ListStyle)

    def __init__(
        self,
        *options: object,
        typography: TypographyOptions | None = None,
        captions: CaptionOptions | None = None,
        citation_options: CitationOptions | None = None,
        generated_pages: GeneratedPageOptions | None = None,
        page_numbers: PageNumberOptions | None = None,
        title_matter: TitleMatterOptions | None = None,
        blocks: BlockOptions | None = None,
        page_background_color: str | object = _UNSET,
        body_font_name: str | object = _UNSET,
        monospace_font_name: str | object = _UNSET,
        title_font_size: float | object = _UNSET,
        body_font_size: float | object = _UNSET,
        paragraph_alignment: str | object = _UNSET,
        heading_sizes: tuple[float, ...] | object = _UNSET,
        caption_font_size: float | None | object = _UNSET,
        caption_alignment: str | object = _UNSET,
        table_alignment: str | object = _UNSET,
        figure_alignment: str | object = _UNSET,
        box_alignment: str | object = _UNSET,
        table_caption_position: str | object = _UNSET,
        figure_caption_position: str | object = _UNSET,
        table_label: str | object = _UNSET,
        figure_label: str | object = _UNSET,
        part_label: str | object = _UNSET,
        part_number_format: str | object = _UNSET,
        table_caption_label: str | None | object = _UNSET,
        figure_caption_label: str | None | object = _UNSET,
        table_reference_label: str | None | object = _UNSET,
        figure_reference_label: str | None | object = _UNSET,
        citation_format: str | object = _UNSET,
        reference_format: str | object = _UNSET,
        list_of_tables_title: str | object = _UNSET,
        list_of_figures_title: str | object = _UNSET,
        comments_title: str | object = _UNSET,
        footnotes_title: str | object = _UNSET,
        references_title: str | object = _UNSET,
        contents_title: str | object = _UNSET,
        generated_section_level: int | object = _UNSET,
        generated_page_breaks: bool | object = _UNSET,
        footnote_placement: str | object = _UNSET,
        auto_footnotes_page: bool | object = _UNSET,
        show_page_numbers: bool | object = _UNSET,
        page_number_alignment: str | object = _UNSET,
        page_number_format: str | object = _UNSET,
        front_matter_page_number_format: str | object = _UNSET,
        main_matter_page_number_format: str | object = _UNSET,
        page_number_font_size: float | object = _UNSET,
        title_alignment: str | object = _UNSET,
        subtitle_alignment: str | object = _UNSET,
        author_alignment: str | object = _UNSET,
        affiliation_alignment: str | object = _UNSET,
        author_detail_alignment: str | object = _UNSET,
        heading_numbering: HeadingNumbering | object = _UNSET,
        bullet_list_style: ListStyle | object = _UNSET,
        numbered_list_style: ListStyle | object = _UNSET,
    ) -> None:
        option_groups = {
            TypographyOptions: None,
            CaptionOptions: None,
            CitationOptions: None,
            GeneratedPageOptions: None,
            PageNumberOptions: None,
            TitleMatterOptions: None,
            BlockOptions: None,
        }
        for option in options:
            matching_type = next(
                (
                    option_type
                    for option_type in option_groups
                    if isinstance(option, option_type)
                ),
                None,
            )
            if matching_type is None:
                raise TypeError(
                    "Theme positional options must be TypographyOptions, "
                    "CaptionOptions, CitationOptions, GeneratedPageOptions, "
                    "PageNumberOptions, TitleMatterOptions, or BlockOptions"
                )
            option_groups[matching_type] = option

        keyword_groups = {
            TypographyOptions: typography,
            CaptionOptions: captions,
            CitationOptions: citation_options,
            GeneratedPageOptions: generated_pages,
            PageNumberOptions: page_numbers,
            TitleMatterOptions: title_matter,
            BlockOptions: blocks,
        }
        option_groups.update(
            {
                option_type: option
                for option_type, option in keyword_groups.items()
                if option is not None
            }
        )

        self.typography = option_groups[TypographyOptions] or TypographyOptions()
        self.captions = option_groups[CaptionOptions] or CaptionOptions()
        self.citation_options = option_groups[CitationOptions] or CitationOptions()
        self.generated_pages = option_groups[GeneratedPageOptions] or GeneratedPageOptions()
        self.page_numbers = option_groups[PageNumberOptions] or PageNumberOptions()
        self.title_matter = option_groups[TitleMatterOptions] or TitleMatterOptions()
        self.blocks = option_groups[BlockOptions] or BlockOptions()

        grouped_values: dict[str, object] = {}
        for group_type, group in (
            (BlockOptions, self.blocks),
            (TypographyOptions, self.typography),
            (CaptionOptions, self.captions),
            (CitationOptions, self.citation_options),
            (GeneratedPageOptions, self.generated_pages),
            (PageNumberOptions, self.page_numbers),
            (TitleMatterOptions, self.title_matter),
        ):
            grouped_values.update(
                {
                    group_field.name: getattr(group, group_field.name)
                    for group_field in fields(group_type)
                }
            )

        direct_values = {
            "page_background_color": page_background_color,
            "body_font_name": body_font_name,
            "monospace_font_name": monospace_font_name,
            "title_font_size": title_font_size,
            "body_font_size": body_font_size,
            "paragraph_alignment": paragraph_alignment,
            "heading_sizes": heading_sizes,
            "caption_font_size": caption_font_size,
            "caption_alignment": caption_alignment,
            "table_alignment": table_alignment,
            "figure_alignment": figure_alignment,
            "box_alignment": box_alignment,
            "table_caption_position": table_caption_position,
            "figure_caption_position": figure_caption_position,
            "table_label": table_label,
            "figure_label": figure_label,
            "part_label": part_label,
            "part_number_format": part_number_format,
            "table_caption_label": table_caption_label,
            "figure_caption_label": figure_caption_label,
            "table_reference_label": table_reference_label,
            "figure_reference_label": figure_reference_label,
            "citation_format": citation_format,
            "reference_format": reference_format,
            "list_of_tables_title": list_of_tables_title,
            "list_of_figures_title": list_of_figures_title,
            "comments_title": comments_title,
            "footnotes_title": footnotes_title,
            "references_title": references_title,
            "contents_title": contents_title,
            "generated_section_level": generated_section_level,
            "generated_page_breaks": generated_page_breaks,
            "footnote_placement": footnote_placement,
            "auto_footnotes_page": auto_footnotes_page,
            "show_page_numbers": show_page_numbers,
            "page_number_alignment": page_number_alignment,
            "page_number_format": page_number_format,
            "front_matter_page_number_format": front_matter_page_number_format,
            "main_matter_page_number_format": main_matter_page_number_format,
            "page_number_font_size": page_number_font_size,
            "title_alignment": title_alignment,
            "subtitle_alignment": subtitle_alignment,
            "author_alignment": author_alignment,
            "affiliation_alignment": affiliation_alignment,
            "author_detail_alignment": author_detail_alignment,
            "heading_numbering": heading_numbering,
            "bullet_list_style": bullet_list_style,
            "numbered_list_style": numbered_list_style,
        }
        grouped_values.update(
            {
                name: value
                for name, value in direct_values.items()
                if value is not _UNSET
            }
        )
        for name, value in grouped_values.items():
            setattr(self, name, value)

        self.__post_init__()
        self._sync_option_groups()

    def __post_init__(self) -> None:
        self.page_background_color = normalize_color(self.page_background_color) or "FFFFFF"
        self.paragraph_alignment = normalize_text_alignment(self.paragraph_alignment)
        if self.caption_alignment not in {"left", "center", "right", "justify"}:
            raise ValueError(
                f"Unsupported caption alignment: {self.caption_alignment!r}"
            )
        for field_name in (
            "table_alignment",
            "figure_alignment",
            "box_alignment",
        ):
            value = getattr(self, field_name)
            if value not in {"left", "center", "right"}:
                raise ValueError(f"Unsupported alignment for {field_name}: {value!r}")
        if self.table_caption_position not in {"above", "below"}:
            raise ValueError(
                "table_caption_position must be 'above' or 'below'"
            )
        if self.figure_caption_position not in {"above", "below"}:
            raise ValueError(
                "figure_caption_position must be 'above' or 'below'"
            )
        self.citation_format = normalize_citation_format(self.citation_format)
        self.reference_format = normalize_reference_format(self.reference_format)
        if self.footnote_placement not in {"page", "document"}:
            raise ValueError(
                "footnote_placement must be 'page' or 'document'"
            )
        if self.page_number_alignment not in {"left", "center", "right"}:
            raise ValueError(
                f"Unsupported page number alignment: {self.page_number_alignment!r}"
            )
        self.front_matter_page_number_format = normalize_counter_format(
            self.front_matter_page_number_format
        )
        self.main_matter_page_number_format = normalize_counter_format(
            self.main_matter_page_number_format
        )
        self.part_number_format = normalize_counter_format(self.part_number_format)
        if "{page}" not in self.page_number_format:
            raise ValueError("page_number_format must contain a '{page}' placeholder")
        for field_name in (
            "title_alignment",
            "subtitle_alignment",
            "author_alignment",
            "affiliation_alignment",
            "author_detail_alignment",
        ):
            value = getattr(self, field_name)
            if value not in {"left", "center", "right", "justify"}:
                raise ValueError(f"Unsupported alignment for {field_name}: {value!r}")

    def _sync_option_groups(self) -> None:
        self.typography = TypographyOptions(
            body_font_name=self.body_font_name,
            monospace_font_name=self.monospace_font_name,
            title_font_size=self.title_font_size,
            body_font_size=self.body_font_size,
            heading_sizes=self.heading_sizes,
            caption_font_size=self.caption_font_size,
        )
        self.captions = CaptionOptions(
            caption_alignment=self.caption_alignment,
            table_caption_position=self.table_caption_position,
            figure_caption_position=self.figure_caption_position,
            table_label=self.table_label,
            figure_label=self.figure_label,
            table_caption_label=self.table_caption_label,
            figure_caption_label=self.figure_caption_label,
            table_reference_label=self.table_reference_label,
            figure_reference_label=self.figure_reference_label,
        )
        self.citation_options = CitationOptions(
            citation_format=self.citation_format,
            reference_format=self.reference_format,
        )
        self.generated_pages = GeneratedPageOptions(
            list_of_tables_title=self.list_of_tables_title,
            list_of_figures_title=self.list_of_figures_title,
            comments_title=self.comments_title,
            footnotes_title=self.footnotes_title,
            references_title=self.references_title,
            contents_title=self.contents_title,
            generated_section_level=self.generated_section_level,
            generated_page_breaks=self.generated_page_breaks,
        )
        self.page_numbers = PageNumberOptions(
            show_page_numbers=self.show_page_numbers,
            page_number_alignment=self.page_number_alignment,
            page_number_format=self.page_number_format,
            front_matter_page_number_format=self.front_matter_page_number_format,
            main_matter_page_number_format=self.main_matter_page_number_format,
            page_number_font_size=self.page_number_font_size,
        )
        self.title_matter = TitleMatterOptions(
            title_alignment=self.title_alignment,
            subtitle_alignment=self.subtitle_alignment,
            author_alignment=self.author_alignment,
            affiliation_alignment=self.affiliation_alignment,
            author_detail_alignment=self.author_detail_alignment,
        )
        self.blocks = BlockOptions(
            page_background_color=self.page_background_color,
            paragraph_alignment=self.paragraph_alignment,
            table_alignment=self.table_alignment,
            figure_alignment=self.figure_alignment,
            box_alignment=self.box_alignment,
            part_label=self.part_label,
            part_number_format=self.part_number_format,
            footnote_placement=self.footnote_placement,
            auto_footnotes_page=self.auto_footnotes_page,
            heading_numbering=self.heading_numbering,
            bullet_list_style=self.bullet_list_style,
            numbered_list_style=self.numbered_list_style,
        )

    def heading_size(self, level: int) -> float:
        """Return the configured font size for a heading level.

        Args:
            level: One-based heading level.

        Returns:
            Font size for the nearest configured level.
        """

        index = min(max(level - 1, 0), len(self.heading_sizes) - 1)
        return self.heading_sizes[index]

    def heading_emphasis(self, level: int) -> tuple[bool, bool]:
        """Return heading emphasis for a heading level.

        Args:
            level: One-based heading level.

        Returns:
            ``(bold, italic)`` emphasis flags.
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
        """

        return "left"

    def resolve_paragraph_alignment(self, style: ParagraphStyle) -> str:
        """Return a paragraph style's alignment or the document-wide default.

        Args:
            style: Paragraph style to resolve.

        Returns:
            Effective paragraph alignment.
        """

        return style.alignment or self.paragraph_alignment

    def table_caption_label_text(self) -> str:
        """Return the label used in table captions and generated table lists.

        Returns:
            Effective table caption label.
        """

        return self.table_caption_label or self.table_label

    def figure_caption_label_text(self) -> str:
        """Return the label used in figure captions and generated figure lists.

        Returns:
            Effective figure caption label.
        """

        return self.figure_caption_label or self.figure_label

    def table_reference_label_text(self) -> str:
        """Return the label used for inline table references.

        Returns:
            Effective table reference label.
        """

        return self.table_reference_label or self.table_label

    def figure_reference_label_text(self) -> str:
        """Return the label used for inline figure and subfigure references.

        Returns:
            Effective figure reference label.
        """

        return self.figure_reference_label or self.figure_label

    def caption_size(self) -> float:
        """Return the effective caption font size.

        Returns:
            Caption font size, falling back to body font size.
        """

        return self.body_font_size if self.caption_font_size is None else self.caption_font_size

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
        """

        marker_format = (
            self.front_matter_page_number_format
            if front_matter
            else self.main_matter_page_number_format
        )
        page_label = format_counter_value(page_number, marker_format)
        return self.page_number_format.format(page=page_label)

    def format_heading_label(self, counters: Sequence[int]) -> str | None:
        """Render a heading numbering label for nested section counters.

        Args:
            counters: Counter values from top-level heading through current
                heading.

        Returns:
            Formatted heading label, or ``None`` when numbering is disabled.
        """

        return self.heading_numbering.format_label(counters)

    def format_part_label(self, value: int) -> str | None:
        """Render a part label such as ``Part I`` from an independent counter.

        Args:
            value: Part counter value.

        Returns:
            Formatted part label, or ``None`` when heading numbering is
            disabled.
        """

        if not self.heading_numbering.enabled:
            return None
        marker = format_counter_value(value, self.part_number_format)
        return f"{self.part_label} {marker}".strip()

    def list_style(self, *, ordered: bool) -> ListStyle:
        """Return the default style for bullet or ordered lists.

        Args:
            ordered: Whether to return the ordered-list style.

        Returns:
            Default list style for the requested list kind.
        """

        return self.numbered_list_style if ordered else self.bullet_list_style


__all__ = [
    "BlockOptions",
    "BoxStyle",
    "CaptionOptions",
    "CitationOptions",
    "GeneratedPageOptions",
    "HeadingNumbering",
    "ListStyle",
    "PageNumberOptions",
    "ParagraphStyle",
    "TableStyle",
    "TextStyle",
    "TitleMatterOptions",
    "TypographyOptions",
    "Theme",
]
