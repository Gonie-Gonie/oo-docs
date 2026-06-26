"""Table style objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from oodocs.core import normalize_color, normalize_text_alignment, normalize_vertical_alignment
from oodocs.styles.base import _style_with_overrides
from oodocs.styles.border import BorderStyle
from oodocs.styles.spacing import Padding
from oodocs.styles.text import TextStyle


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

    Examples:
        ```python
        style = table_style_with_overrides(None, repeat_header_rows=True)
        ```
    """

    return _style_with_overrides(style, TableStyle, overrides)  # type: ignore[return-value]


@dataclass(slots=True)
class TableCellStyle:
    """Cell-level table styling that can be applied to cells, rows, or columns.

    Attributes:
        background_color: Optional background color as a hex string.
        text_color: Optional text color as a hex string.
        bold: Optional bold override.
        italic: Optional italic override.
        text_alignment: Optional cell text alignment override.
        vertical_alignment: Optional vertical alignment override.

    Examples:
        ```python
        from oodocs import Document, Table, TableCellStyle

        style = TableCellStyle(background_color="F8FAFC", bold=True)
        table = Table(["Metric", "Value"], [["Latency", "42 ms"]], column_styles={0: style})
        document = Document("Metrics", table)
        ```
    """

    background_color: str | None = None
    text_color: str | None = None
    bold: bool | None = None
    italic: bool | None = None
    text_alignment: str | None = None
    vertical_alignment: str | None = None

    def __post_init__(self) -> None:
        self.background_color = normalize_color(self.background_color)
        self.text_color = normalize_color(self.text_color)
        self.text_alignment = (
            normalize_text_alignment(self.text_alignment)
            if self.text_alignment is not None
            else None
        )
        self.vertical_alignment = (
            normalize_vertical_alignment(self.vertical_alignment)
            if self.vertical_alignment is not None
            else None
        )

    def merged(self, *others: TableCellStyle | None) -> TableCellStyle:
        """Return a new style with later non-``None`` values overriding earlier ones.

        Args:
            *others: Styles to overlay from left to right.

        Returns:
            New merged table cell style.

        Examples:
            ```python
            base = TableCellStyle(background_color="FFFFFF")
            merged = base.merged(TableCellStyle(text_color="111827", bold=True))
            ```
        """

        merged = TableCellStyle(
            background_color=self.background_color,
            text_color=self.text_color,
            bold=self.bold,
            italic=self.italic,
            text_alignment=self.text_alignment,
            vertical_alignment=self.vertical_alignment,
        )
        for other in others:
            if other is None:
                continue
            for field_name in (
                "background_color",
                "text_color",
                "bold",
                "italic",
                "text_alignment",
                "vertical_alignment",
            ):
                value = getattr(other, field_name)
                if value is not None:
                    setattr(merged, field_name, value)
        return merged

    def text_style(self) -> TextStyle:
        """Return the inline text defaults represented by this cell style.

        Returns:
            Text style containing text color, bold, and italic values.

        Examples:
            ```python
            style = TableCellStyle(text_color="111827", bold=True)
            text_style = style.text_style()
            ```
        """

        return TextStyle(
            text_color=self.text_color,
            bold=self.bold,
            italic=self.italic,
        )


TableCellStyleInput = TableCellStyle | Mapping[str, object] | str


def coerce_table_cell_style(value: TableCellStyleInput) -> TableCellStyle | str:
    """Normalize a table cell style object or mapping.

    Args:
        value: Existing style or mapping of ``TableCellStyle`` fields.

    Returns:
        A table cell style.

    Raises:
        TypeError: If ``value`` cannot be converted.

    Examples:
        ```python
        style = coerce_table_cell_style({"background_color": "EEF2FF"})
        ```
    """

    if isinstance(value, TableCellStyle):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return TableCellStyle(**dict(value))
    raise TypeError(f"Unsupported table cell style: {type(value)!r}")


@dataclass(slots=True)
class TableStyle:
    """Renderer-neutral table styling options.

    Attributes:
        header_background_color: Hex fill color for header cells.
        header_text_color: Hex text color for header cells.
        border: Table border style.
        body_background_color: Optional body cell fill color.
        alternate_row_background_color: Optional alternating row fill color.
        cell_text_alignment: Optional body cell text alignment.
        cell_vertical_alignment: Optional body cell vertical alignment.
        header_text_alignment: Optional header cell text alignment.
        header_vertical_alignment: Optional header cell vertical alignment.
        cell_padding: Cell padding.
        repeat_header_rows: Whether renderers should repeat header rows.

    Examples:
        ```python
        from oodocs import Document, Table, TableStyle

        table = Table(["A"], [[1]], style=TableStyle.compact())
        document = Document("Metrics", table)
        ```
    """

    header_background_color: str = "E8EDF5"
    header_text_color: str = "000000"
    border: BorderStyle = field(
        default_factory=lambda: BorderStyle.solid("B7C2D0", width=0.5)
    )
    body_background_color: str | None = None
    alternate_row_background_color: str | None = None
    cell_text_alignment: str | None = None
    cell_vertical_alignment: str | None = None
    header_text_alignment: str | None = None
    header_vertical_alignment: str | None = None
    cell_padding: Padding = field(default_factory=lambda: Padding.all(5.0))
    repeat_header_rows: bool = False

    def __post_init__(self) -> None:
        self.header_background_color = normalize_color(self.header_background_color) or "E8EDF5"
        self.header_text_color = normalize_color(self.header_text_color) or "000000"
        if not isinstance(self.border, BorderStyle):
            raise TypeError("TableStyle.border must be a BorderStyle")
        if not isinstance(self.cell_padding, Padding):
            raise TypeError("TableStyle.cell_padding must be a Padding")
        self.body_background_color = normalize_color(self.body_background_color)
        self.alternate_row_background_color = normalize_color(self.alternate_row_background_color)
        self.cell_text_alignment = (
            normalize_text_alignment(self.cell_text_alignment)
            if self.cell_text_alignment is not None
            else None
        )
        self.cell_vertical_alignment = (
            normalize_vertical_alignment(self.cell_vertical_alignment)
            if self.cell_vertical_alignment is not None
            else None
        )
        self.header_text_alignment = (
            normalize_text_alignment(self.header_text_alignment)
            if self.header_text_alignment is not None
            else None
        )
        self.header_vertical_alignment = (
            normalize_vertical_alignment(self.header_vertical_alignment)
            if self.header_vertical_alignment is not None
            else None
        )
    @classmethod
    def plain(cls) -> TableStyle:
        """Create a minimally styled table preset.

        Returns:
            Plain table style.

        Examples:
            ```python
            style = TableStyle.plain()
            ```
        """

        return cls(
            header_background_color="FFFFFF",
            border=BorderStyle.solid("DADDE3", width=0.5),
            cell_padding=Padding.all(5.0),
        )

    @classmethod
    def compact(cls) -> TableStyle:
        """Create a dense preset for compact data tables.

        Returns:
            Compact table style.

        Examples:
            ```python
            style = TableStyle.compact()
            ```
        """

        return cls(
            header_background_color="F1F4F8",
            border=BorderStyle.solid("C9D2DE", width=0.4),
            alternate_row_background_color="FAFBFC",
            cell_padding=Padding.all(3.0),
            repeat_header_rows=True,
        )

    @classmethod
    def evidence(cls) -> TableStyle:
        """Create a preset for release evidence and audit tables.

        Returns:
            Evidence-oriented table style.

        Examples:
            ```python
            style = TableStyle.evidence()
            ```
        """

        return cls(
            header_background_color="E7EEF7",
            border=BorderStyle.solid("AEBBCC", width=0.5),
            body_background_color="FFFFFF",
            alternate_row_background_color="F8FBFD",
            cell_padding=Padding.all(4.0),
            repeat_header_rows=True,
        )

__all__ = [
    "TableCellStyle",
    "TableCellStyleInput",
    "TableStyle",
    "coerce_table_cell_style",
    "table_style_with_overrides",
]
