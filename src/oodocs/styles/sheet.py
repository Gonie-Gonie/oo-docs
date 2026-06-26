"""Named visual style registry used by themes and renderers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from oodocs.styles.blocks import BoxStyle, ParagraphStyle, RunInTitleStyle
from oodocs.styles.border import BorderStyle
from oodocs.styles.chips import InlineChipStyle
from oodocs.styles.counter import ListStyle
from oodocs.styles.spacing import Padding
from oodocs.styles.tables import TableCellStyle, TableStyle
from oodocs.styles.text import TextStyle


_STYLE_TYPES = {
    "text": TextStyle,
    "paragraph": ParagraphStyle,
    "run_in_title": RunInTitleStyle,
    "list": ListStyle,
    "box": BoxStyle,
    "table": TableStyle,
    "table_cell": TableCellStyle,
    "chip": InlineChipStyle,
}


@dataclass(slots=True)
class StyleSheet:
    """Named style registry attached to a ``Theme``.

    Attributes:
        text: Named inline text styles.
        paragraph: Named paragraph styles.
        run_in_title: Named run-in title styles.
        list: Named list marker styles.
        box: Named box styles.
        table: Named table styles.
        table_cell: Named table cell styles.
        chip: Named inline chip styles.

    Examples:
        Register reusable table and box styles, then attach them to a theme:

        ```python
        from oodocs import Box, Document, DocumentSettings, Paragraph, StyleSheet, Table, Theme
        from oodocs.styles import BoxStyle, Padding, TableStyle

        styles = StyleSheet.default()
        styles.register("box", "scope", BoxStyle(padding=Padding.all(8)))
        styles.register("table", "schema", TableStyle.compact())

        document = Document(
            "Named Styles",
            Box(Paragraph("Scope text"), style="scope"),
            Table(["Field"], [["name"]], style="schema"),
            settings=DocumentSettings(theme=Theme(stylesheet=styles)),
        )
        ```
    """

    text: dict[str, TextStyle] = field(default_factory=dict)
    paragraph: dict[str, ParagraphStyle] = field(default_factory=dict)
    run_in_title: dict[str, RunInTitleStyle] = field(default_factory=dict)
    list: dict[str, ListStyle] = field(default_factory=dict)
    box: dict[str, BoxStyle] = field(default_factory=dict)
    table: dict[str, TableStyle] = field(default_factory=dict)
    table_cell: dict[str, TableCellStyle] = field(default_factory=dict)
    chip: dict[str, InlineChipStyle] = field(default_factory=dict)

    @classmethod
    def default(cls) -> StyleSheet:
        """Create a stylesheet with built-in named styles.

        Returns:
            StyleSheet populated with the standard OODocs names.

        Examples:
            ```python
            styles = StyleSheet.default()
            compact_table_style = styles.resolve("table", "compact")
            ```
        """

        sheet = cls()
        sheet.register("paragraph", "body", ParagraphStyle())
        sheet.register("paragraph", "body.compact", ParagraphStyle(space_after=6.0))
        sheet.register("table", "plain", TableStyle.plain())
        sheet.register("table", "compact", TableStyle.compact())
        sheet.register("table", "evidence", TableStyle.evidence())
        sheet.register("table_cell", "emphasis", TableCellStyle(bold=True))
        sheet.register("table_cell", "muted", TableCellStyle(text_color="64748B"))
        sheet.register("table_cell", "numeric", TableCellStyle(text_alignment="right"))
        sheet.register("box", "note", _box_style("64748B", "F8FAFC", "E2E8F0", "0F172A"))
        sheet.register("box", "info", _box_style("3B82F6", "EFF6FF", "DBEAFE", "1E3A8A"))
        sheet.register("box", "warning", _box_style("D97706", "FFFBEB", "FEF3C7", "78350F"))
        sheet.register("box", "success", _box_style("16A34A", "F0FDF4", "DCFCE7", "14532D"))
        sheet.register("chip", "tag", InlineChipStyle())
        sheet.register("chip", "badge", InlineChipStyle(
            background_color="F3F4F6",
            text_color="1F2937",
            border=BorderStyle.solid("D1D5DB", width=0.5, radius=0.5, radius_unit="em"),
            padding=Padding.symmetric(vertical=0.12, horizontal=0.32, unit="em"),
        ))
        sheet.register("chip", "keyboard", InlineChipStyle(
            background_color="F8FAFC",
            text_color="111827",
            border=BorderStyle.solid("CBD5E1", width=0.75, radius=0.22, radius_unit="em"),
            padding=Padding.symmetric(vertical=0.08, horizontal=0.28, unit="em"),
            font_size_delta=-0.5,
            font_name="Courier New",
            bold=False,
        ))
        for name, style in _status_chip_styles().items():
            sheet.register("chip", f"status.{name}", style)
        return sheet

    def register(self, category: str, name: str, style: object) -> None:
        """Register a named style.

        Args:
            category: Style category such as ``"table"`` or ``"box"``.
            name: Name used by components.
            style: Style object for the category.

        Raises:
            ValueError: If the category or name is invalid.
            TypeError: If the style object does not match the category.

        Examples:
            ```python
            styles = StyleSheet()
            styles.register("paragraph", "body.compact", ParagraphStyle(space_after=6))
            ```
        """

        normalized_category = _normalize_category(category)
        normalized_name = _normalize_name(name)
        expected_type = _STYLE_TYPES[normalized_category]
        if not isinstance(style, expected_type):
            raise TypeError(
                f"StyleSheet.{normalized_category} styles must be {expected_type.__name__}"
            )
        getattr(self, normalized_category)[normalized_name] = style

    def resolve(
        self,
        category: str,
        value: str | object | None,
        default: object | None = None,
    ) -> object:
        """Resolve a style name or pass through a concrete style object.

        Args:
            category: Style category to resolve.
            value: Style name, concrete style object, or ``None``.
            default: Value returned when ``value`` is ``None``.

        Returns:
            Concrete style object or ``default``.

        Raises:
            KeyError: If a named style is missing.
            TypeError: If a concrete style object belongs to another category.

        Examples:
            ```python
            styles = StyleSheet.default()
            table_style = styles.resolve("table", "compact")
            ```
        """

        normalized_category = _normalize_category(category)
        if value is None:
            return default
        expected_type = _STYLE_TYPES[normalized_category]
        if isinstance(value, str):
            styles = getattr(self, normalized_category)
            normalized_name = _normalize_name(value)
            if normalized_name in styles:
                return styles[normalized_name]
            prefixed = normalized_name.removeprefix(f"{normalized_category}.")
            if prefixed in styles:
                return styles[prefixed]
            raise KeyError(f"Unknown {normalized_category} style: {value!r}")
        if not isinstance(value, expected_type):
            raise TypeError(
                f"Expected {expected_type.__name__} for {normalized_category} style, got {type(value).__name__}"
            )
        return value

    def to_dict(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Serialize named styles to plain dictionaries.

        Returns:
            Mapping from category to named dataclass payloads.

        Examples:
            ```python
            data = StyleSheet.default().to_dict()
            ```
        """

        return {
            category: {
                name: asdict(style)
                for name, style in getattr(self, category).items()
            }
            for category in _STYLE_TYPES
        }

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, dict[str, Any]]]) -> StyleSheet:
        """Create a stylesheet from ``to_dict()`` payloads.

        Args:
            data: Serialized stylesheet data.

        Returns:
            Reconstructed stylesheet.

        Raises:
            ValueError: If a category or style name is invalid.
            TypeError: If a style payload is invalid.

        Examples:
            ```python
            styles = StyleSheet.from_dict(StyleSheet.default().to_dict())
            ```
        """

        sheet = cls()
        for category, styles in data.items():
            normalized_category = _normalize_category(category)
            style_type = _STYLE_TYPES[normalized_category]
            for name, payload in styles.items():
                sheet.register(
                    normalized_category,
                    name,
                    _style_from_payload(style_type, payload),
                )
        return sheet


def _normalize_category(category: str) -> str:
    normalized = category.strip().lower().replace("-", "_")
    if normalized not in _STYLE_TYPES:
        supported = ", ".join(sorted(_STYLE_TYPES))
        raise ValueError(f"Unsupported style category {category!r}. Use one of: {supported}")
    return normalized


def _normalize_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError("Style name must not be empty")
    return normalized


def _box_style(
    border_color: str,
    background_color: str,
    title_background_color: str,
    title_text_color: str,
) -> BoxStyle:
    return BoxStyle(
        border=BorderStyle.solid(border_color, width=0.75),
        background_color=background_color,
        title_background_color=title_background_color,
        title_text_color=title_text_color,
    )


def _status_chip_styles() -> dict[str, InlineChipStyle]:
    base = InlineChipStyle(
        background_color="F3F4F6",
        text_color="374151",
        border=BorderStyle.solid("D1D5DB", width=0.5, radius=0.5, radius_unit="em"),
        uppercase=True,
    )
    return {
        "neutral": base,
        "success": InlineChipStyle(
            background_color="ECFDF3",
            text_color="166534",
            border=BorderStyle.solid("BBF7D0", width=0.5, radius=0.5, radius_unit="em"),
            uppercase=True,
        ),
        "info": InlineChipStyle(
            background_color="E0F2FE",
            text_color="075985",
            border=BorderStyle.solid("BAE6FD", width=0.5, radius=0.5, radius_unit="em"),
            uppercase=True,
        ),
        "warning": InlineChipStyle(
            background_color="FEF3C7",
            text_color="92400E",
            border=BorderStyle.solid("FDE68A", width=0.5, radius=0.5, radius_unit="em"),
            uppercase=True,
        ),
        "danger": InlineChipStyle(
            background_color="FEE2E2",
            text_color="991B1B",
            border=BorderStyle.solid("FECACA", width=0.5, radius=0.5, radius_unit="em"),
            uppercase=True,
        ),
        "muted": base,
    }


def _style_from_payload(style_type: type, payload: dict[str, Any]) -> object:
    values = dict(payload)
    if style_type in {BoxStyle, TableStyle, InlineChipStyle} and isinstance(values.get("border"), dict):
        values["border"] = BorderStyle(**values["border"])
    if style_type is BoxStyle and isinstance(values.get("padding"), dict):
        values["padding"] = Padding(**values["padding"])
    if style_type is TableStyle and isinstance(values.get("cell_padding"), dict):
        values["cell_padding"] = Padding(**values["cell_padding"])
    if style_type is InlineChipStyle and isinstance(values.get("padding"), dict):
        values["padding"] = Padding(**values["padding"])
    if style_type is RunInTitleStyle and isinstance(values.get("text_style"), dict):
        values["text_style"] = TextStyle(**values["text_style"])
    if not is_dataclass(style_type):
        raise TypeError(f"Unsupported style payload type: {style_type!r}")
    return style_type(**values)


__all__ = ["StyleSheet"]
