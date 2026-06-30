"""Named visual style registry used by themes and renderers.

Attributes:
    StyleCategory: Literal category names accepted by ``StyleSheet`` registries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal, TypeAlias, cast, overload

from oodocs.styles.blocks import BoxStyle, ParagraphStyle, RunInTitleStyle
from oodocs.styles.border import BorderStyle
from oodocs.styles.chips import InlineChipStyle
from oodocs.styles.counter import ListStyle
from oodocs.styles.spacing import Padding
from oodocs.styles.tables import TableCellStyle, TableStyle
from oodocs.styles.text import TextStyle


StyleCategory: TypeAlias = Literal[
    "text",
    "paragraph",
    "run_in_title",
    "list",
    "box",
    "table",
    "table_cell",
    "chip",
]

_STYLE_TYPES: dict[StyleCategory, type[object]] = {
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
        styles.register_box("scope", BoxStyle(padding=Padding.all(8)))
        styles.register_table("schema", TableStyle.compact())

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
        sheet.register_paragraph("body", ParagraphStyle())
        sheet.register_paragraph("body.compact", ParagraphStyle(space_after=6.0))
        sheet.register_table("plain", TableStyle.plain())
        sheet.register_table("compact", TableStyle.compact())
        sheet.register_table("evidence", TableStyle.evidence())
        sheet.register_table("booktabs", TableStyle.booktabs())
        sheet.register_table(
            "nomenclature.inner",
            TableStyle(
                header_background_color="FFFFFF",
                border=BorderStyle.none(),
                cell_padding=Padding.all(2.0),
                repeat_header_rows=True,
            ),
        )
        sheet.register_table_cell("emphasis", TableCellStyle(bold=True))
        sheet.register_table_cell("muted", TableCellStyle(text_color="64748B"))
        sheet.register_table_cell("numeric", TableCellStyle(text_alignment="right"))
        sheet.register_box("note", _box_style("64748B", "F8FAFC", "E2E8F0", "0F172A"))
        sheet.register_box("info", _box_style("3B82F6", "EFF6FF", "DBEAFE", "1E3A8A"))
        sheet.register_box("warning", _box_style("D97706", "FFFBEB", "FEF3C7", "78350F"))
        sheet.register_box("danger", _box_style("DC2626", "FEF2F2", "FEE2E2", "7F1D1D"))
        sheet.register_box("success", _box_style("16A34A", "F0FDF4", "DCFCE7", "14532D"))
        sheet.register_chip("tag", InlineChipStyle())
        sheet.register_chip("badge", InlineChipStyle(
            background_color="F3F4F6",
            text_color="1F2937",
            border=BorderStyle.solid("D1D5DB", width=0.5, radius=0.5, radius_unit="em"),
            padding=Padding.symmetric(vertical=0.12, horizontal=0.32, unit="em"),
        ))
        sheet.register_chip("keyboard", InlineChipStyle(
            background_color="F8FAFC",
            text_color="111827",
            border=BorderStyle.solid("CBD5E1", width=0.75, radius=0.22, radius_unit="em"),
            padding=Padding.symmetric(vertical=0.08, horizontal=0.28, unit="em"),
            font_size_delta=-0.5,
            font_name="Courier New",
            bold=False,
        ))
        for name, style in _status_chip_styles().items():
            sheet.register_chip(f"status.{name}", style)
        return sheet

    @overload
    def register(self, category: Literal["text"], name: str, style: TextStyle) -> None:
        ...

    @overload
    def register(
        self,
        category: Literal["paragraph"],
        name: str,
        style: ParagraphStyle,
    ) -> None:
        ...

    @overload
    def register(
        self,
        category: Literal["run_in_title"],
        name: str,
        style: RunInTitleStyle,
    ) -> None:
        ...

    @overload
    def register(self, category: Literal["list"], name: str, style: ListStyle) -> None:
        ...

    @overload
    def register(self, category: Literal["box"], name: str, style: BoxStyle) -> None:
        ...

    @overload
    def register(self, category: Literal["table"], name: str, style: TableStyle) -> None:
        ...

    @overload
    def register(
        self,
        category: Literal["table_cell"],
        name: str,
        style: TableCellStyle,
    ) -> None:
        ...

    @overload
    def register(self, category: Literal["chip"], name: str, style: InlineChipStyle) -> None:
        ...

    def register(self, category: StyleCategory, name: str, style: object) -> None:
        """Register a named style using an explicit category.

        Prefer typed helpers such as ``register_table(...)`` and
        ``register_box(...)`` in ordinary authoring code. This method remains
        useful for dynamic tooling that already stores the category name.

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

    def register_text(self, name: str, style: TextStyle) -> None:
        """Register a named inline text style.

        Args:
            name: Name used by inline text fragments.
            style: Text style object.

        Examples:
            ```python
            styles = StyleSheet()
            styles.register_text("link.emphasis", TextStyle(bold=True))
            ```
        """

        self.register("text", name, style)

    def register_paragraph(self, name: str, style: ParagraphStyle) -> None:
        """Register a named paragraph style.

        Args:
            name: Name used by paragraph-like blocks.
            style: Paragraph style object.

        Examples:
            ```python
            styles = StyleSheet()
            styles.register_paragraph("body.compact", ParagraphStyle(space_after=6))
            ```
        """

        self.register("paragraph", name, style)

    def register_run_in_title(self, name: str, style: RunInTitleStyle) -> None:
        """Register a named run-in title style.

        Args:
            name: Name used by run-in titled blocks.
            style: Run-in title style object.
        """

        self.register("run_in_title", name, style)

    def register_list(self, name: str, style: ListStyle) -> None:
        """Register a named list marker style.

        Args:
            name: Name used by list blocks.
            style: List style object.
        """

        self.register("list", name, style)

    def register_box(self, name: str, style: BoxStyle) -> None:
        """Register a named box style.

        Args:
            name: Name used by boxes and callouts.
            style: Box style object.

        Examples:
            ```python
            styles = StyleSheet()
            styles.register_box("warning", BoxStyle(background_color="FFFBEB"))
            ```
        """

        self.register("box", name, style)

    def register_table(self, name: str, style: TableStyle) -> None:
        """Register a named table style.

        Args:
            name: Name used by tables.
            style: Table style object.

        Examples:
            ```python
            styles = StyleSheet()
            styles.register_table("schema", TableStyle.compact())
            ```
        """

        self.register("table", name, style)

    def register_table_cell(self, name: str, style: TableCellStyle) -> None:
        """Register a named table cell style.

        Args:
            name: Name used by table cells.
            style: Table cell style object.
        """

        self.register("table_cell", name, style)

    def register_chip(self, name: str, style: InlineChipStyle) -> None:
        """Register a named inline chip style.

        Args:
            name: Name used by chip helpers.
            style: Inline chip style object.

        Examples:
            ```python
            styles = StyleSheet()
            styles.register_chip("status.ready", InlineChipStyle(uppercase=True))
            ```
        """

        self.register("chip", name, style)

    def resolve(
        self,
        category: StyleCategory,
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


def _normalize_category(category: str) -> StyleCategory:
    normalized = category.strip().lower().replace("-", "_")
    if normalized not in _STYLE_TYPES:
        supported = ", ".join(sorted(_STYLE_TYPES))
        raise ValueError(f"Unsupported style category {category!r}. Use one of: {supported}")
    return cast(StyleCategory, normalized)


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
    if style_type is TableStyle:
        for field_name in ("top_rule", "header_rule", "bottom_rule"):
            if isinstance(values.get(field_name), dict):
                values[field_name] = BorderStyle(**values[field_name])
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


__all__ = ["StyleCategory", "StyleSheet"]
