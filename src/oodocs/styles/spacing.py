"""Spacing primitives shared by visual style objects."""

from __future__ import annotations

from dataclasses import dataclass

from oodocs.core import length_to_inches, normalize_length_unit


@dataclass(slots=True)
class Padding:
    """Four-sided padding with an explicit unit.

    Args:
        top: Top padding value.
        right: Right padding value.
        bottom: Bottom padding value.
        left: Left padding value.
        unit: Unit for all side values.

    Examples:
        Apply symmetric padding to a report box:

        ```python
        from oodocs import Box, BoxStyle, Document, Padding, Paragraph

        padding = Padding.symmetric(vertical=6, horizontal=10)
        box = Box(Paragraph("Review scope."), style=BoxStyle(padding=padding))
        document = Document("Notes", box)
        ```

        Use compact table cell padding:

        ```python
        from oodocs import Padding, Table, TableStyle

        table = Table(
            ["Metric", "Value"],
            [["Latency", "42 ms"]],
            style=TableStyle(cell_padding=Padding.symmetric(vertical=3, horizontal=5)),
        )
        ```
    """

    top: float
    right: float
    bottom: float
    left: float
    unit: str = "pt"

    def __post_init__(self) -> None:
        for field_name in ("top", "right", "bottom", "left"):
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"Padding.{field_name} must be >= 0")
        normalized = self.unit.strip().lower()
        self.unit = "em" if normalized == "em" else normalize_length_unit(normalized)

    @classmethod
    def all(cls, value: float, *, unit: str = "pt") -> Padding:
        """Create equal padding on every side.

        Args:
            value: Padding value applied to all four sides.
            unit: Unit for the padding value.

        Returns:
            Padding with equal top, right, bottom, and left values.

        Examples:
            ```python
            from oodocs import Padding, TableStyle

            table_style = TableStyle(cell_padding=Padding.all(4))
            ```
        """

        return cls(value, value, value, value, unit=unit)

    @classmethod
    def symmetric(
        cls,
        *,
        vertical: float,
        horizontal: float,
        unit: str = "pt",
    ) -> Padding:
        """Create vertical and horizontal padding pairs.

        Args:
            vertical: Top and bottom padding.
            horizontal: Left and right padding.
            unit: Unit for all sides.

        Returns:
            Padding with paired vertical and horizontal values.

        Examples:
            ```python
            from oodocs import BoxStyle, Padding

            style = BoxStyle(padding=Padding.symmetric(vertical=8, horizontal=12))
            ```
        """

        return cls(vertical, horizontal, vertical, horizontal, unit=unit)

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return ``(top, right, bottom, left)`` in the stored unit.

        Returns:
            Four padding side values in logical CSS order.

        Examples:
            ```python
            padding = Padding.symmetric(vertical=2, horizontal=4)
            top, right, bottom, left = padding.as_tuple()
            ```
        """

        return (self.top, self.right, self.bottom, self.left)

    def to_points(self, default_unit: str = "pt") -> tuple[float, float, float, float]:
        """Return ``(top, right, bottom, left)`` converted to points.

        Args:
            default_unit: Unit to use when no unit is stored. Present for API
                symmetry with other length helpers.

        Returns:
            Padding side values in points.

        Raises:
            ValueError: If this padding uses ``"em"``. Em-relative padding
                needs font-size context and should use ``as_tuple()``.
        """

        unit = self.unit or default_unit
        if unit == "em":
            raise ValueError("em padding cannot be converted to points without font context")
        top, right, bottom, left = self.as_tuple()
        return (
            length_to_inches(top, unit) * 72.0,
            length_to_inches(right, unit) * 72.0,
            length_to_inches(bottom, unit) * 72.0,
            length_to_inches(left, unit) * 72.0,
        )


__all__ = ["Padding"]
