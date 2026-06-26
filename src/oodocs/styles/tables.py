"""Table style objects."""

from __future__ import annotations

from dataclasses import dataclass

from oodocs.core import normalize_color, normalize_text_alignment, normalize_vertical_alignment
from oodocs.styles.base import _style_with_overrides


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
class TableStyle:
    """Renderer-neutral table styling options.

    Attributes:
        header_background_color: Hex fill color for header cells.
        header_text_color: Hex text color for header cells.
        border_color: Hex table border color.
        body_background_color: Optional body cell fill color.
        alternate_row_background_color: Optional alternating row fill color.
        cell_text_alignment: Optional body cell text alignment.
        cell_vertical_alignment: Optional body cell vertical alignment.
        header_text_alignment: Optional header cell text alignment.
        header_vertical_alignment: Optional header cell vertical alignment.
        cell_padding: Default cell padding in points.
        cell_padding_top: Optional top cell padding override in points.
        cell_padding_right: Optional right cell padding override in points.
        cell_padding_bottom: Optional bottom cell padding override in points.
        cell_padding_left: Optional left cell padding override in points.
        border_width: Border width in points.
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
    border_color: str = "B7C2D0"
    body_background_color: str | None = None
    alternate_row_background_color: str | None = None
    cell_text_alignment: str | None = None
    cell_vertical_alignment: str | None = None
    header_text_alignment: str | None = None
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

        Examples:
            ```python
            style = TableStyle.plain()
            ```
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

        Examples:
            ```python
            style = TableStyle.compact()
            ```
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

        Examples:
            ```python
            style = TableStyle.evidence()
            ```
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

__all__ = ["TableStyle", "table_style_with_overrides"]
