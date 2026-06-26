"""Border primitives shared by visual style objects."""

from __future__ import annotations

from dataclasses import dataclass

from oodocs.core import length_to_inches, normalize_color, normalize_length_unit


@dataclass(slots=True)
class BorderStyle:
    """Border stroke, optional radius, and unit.

    Args:
        color: Optional border color as a hex string. ``None`` disables color.
        width: Border width.
        radius: Optional corner radius.
        width_unit: Unit for ``width``.
        radius_unit: Unit for ``radius``. Defaults to ``width_unit`` when
            omitted.

    Examples:
        Use a border style inside a box style:

        ```python
        from oodocs import BorderStyle, Box, BoxStyle, Document, Paragraph

        style = BoxStyle(border=BorderStyle.solid("CBD5E1", width=0.75))
        document = Document("Notes", Box(Paragraph("Review scope."), style=style))
        ```

        Give an inline chip a point-sized border and em-sized corner radius:

        ```python
        from oodocs import BorderStyle, InlineChipStyle, Paragraph, tag

        chip_style = InlineChipStyle(
            border=BorderStyle.solid("BAE6FD", width=0.5, radius=0.45, radius_unit="em"),
        )
        paragraph = Paragraph("Status: ", tag("beta", chip_style=chip_style))
        ```
    """

    color: str | None = None
    width: float = 0.0
    radius: float | None = None
    width_unit: str = "pt"
    radius_unit: str | None = None

    def __post_init__(self) -> None:
        self.color = normalize_color(self.color)
        if self.width < 0:
            raise ValueError("BorderStyle.width must be >= 0")
        if self.radius is not None and self.radius < 0:
            raise ValueError("BorderStyle.radius must be >= 0")
        self.width_unit = self._normalize_unit(self.width_unit)
        radius_unit = self.width_unit if self.radius_unit is None else self.radius_unit
        self.radius_unit = self._normalize_unit(radius_unit)

    @staticmethod
    def _normalize_unit(unit: str) -> str:
        normalized = unit.strip().lower()
        return "em" if normalized == "em" else normalize_length_unit(normalized)

    @classmethod
    def none(cls) -> BorderStyle:
        """Create a borderless style.

        Returns:
            Border style with no color and zero width.

        Examples:
            ```python
            from oodocs import BorderStyle, TableStyle

            table_style = TableStyle(border=BorderStyle.none())
            ```
        """

        return cls(color=None, width=0.0)

    @classmethod
    def solid(
        cls,
        color: str,
        *,
        width: float = 0.5,
        radius: float | None = None,
        width_unit: str = "pt",
        radius_unit: str | None = None,
    ) -> BorderStyle:
        """Create a solid border style.

        Args:
            color: Border color.
            width: Border width.
            radius: Optional corner radius.
            width_unit: Unit for ``width``.
            radius_unit: Unit for ``radius``. Defaults to ``width_unit``.

        Returns:
            Border style configured with a visible color.

        Examples:
            ```python
            from oodocs import BorderStyle, Padding, TableStyle

            style = TableStyle(
                border=BorderStyle.solid("CBD5E1", width=0.5),
                cell_padding=Padding.symmetric(vertical=3, horizontal=5),
            )
            ```
        """

        return cls(
            color=color,
            width=width,
            radius=radius,
            width_unit=width_unit,
            radius_unit=radius_unit,
        )

    def width_points(self, default_unit: str = "pt") -> float:
        """Return border width converted to points.

        Args:
            default_unit: Unit to use when the width unit is empty.

        Returns:
            Width in points.

        Raises:
            ValueError: If ``width_unit`` is ``"em"``.

        Examples:
            ```python
            border = BorderStyle.solid("CBD5E1", width=0.5)
            width_points = border.width_points()
            ```
        """

        unit = self.width_unit or default_unit
        if unit == "em":
            raise ValueError("em border width cannot be converted to points without font context")
        return length_to_inches(self.width, unit) * 72.0

    def radius_em(self, default_unit: str = "em") -> float:
        """Return corner radius in em units.

        Args:
            default_unit: Unit used when the radius unit is empty.

        Returns:
            Radius in em units. Returns ``0.0`` when radius is unset.

        Raises:
            ValueError: If the radius uses an absolute unit.

        Examples:
            ```python
            border = BorderStyle.solid("BAE6FD", radius=0.45, radius_unit="em")
            radius = border.radius_em()
            ```
        """

        if self.radius is None:
            return 0.0
        unit = self.radius_unit or default_unit
        if unit != "em":
            raise ValueError("absolute border radius cannot be converted to em without font context")
        return self.radius

    def radius_points(self, default_unit: str = "pt") -> float:
        """Return corner radius converted to points.

        Args:
            default_unit: Unit to use when the radius unit is empty.

        Returns:
            Radius in points. Returns ``0.0`` when radius is unset.

        Raises:
            ValueError: If ``radius_unit`` is ``"em"``.

        Examples:
            ```python
            border = BorderStyle.solid("CBD5E1", radius=3)
            radius_points = border.radius_points()
            ```
        """

        if self.radius is None:
            return 0.0
        unit = self.radius_unit or default_unit
        if unit == "em":
            raise ValueError("em border radius cannot be converted to points without font context")
        return length_to_inches(self.radius, unit) * 72.0


@dataclass(slots=True)
class StrokeStyle:
    """Vector stroke color, width, and unit.

    Args:
        color: Optional stroke color as a hex string. ``None`` disables the
            stroke.
        width: Stroke width.
        unit: Unit for ``width``.

    Examples:
        Apply a stroke to a positioned shape:

        ```python
        from oodocs import Document, DocumentSettings, Shape, StrokeStyle

        frame = Shape.rect(
            width=2.0,
            height=0.8,
            stroke=StrokeStyle.solid("476172", width=1.2),
            fill_color="EEF6FF",
        )
        document = Document("Cover", settings=DocumentSettings(page_items=[frame]))
        ```
    """

    color: str | None = None
    width: float = 0.0
    unit: str = "pt"

    def __post_init__(self) -> None:
        self.color = normalize_color(self.color)
        if self.width < 0:
            raise ValueError("StrokeStyle.width must be >= 0")
        normalized = self.unit.strip().lower()
        self.unit = normalize_length_unit(normalized)

    @classmethod
    def none(cls) -> StrokeStyle:
        """Create a stroke-free style.

        Returns:
            Stroke style with no color and zero width.

        Examples:
            ```python
            from oodocs import Shape, StrokeStyle

            shape = Shape.rect(width=2, height=1, stroke=StrokeStyle.none())
            ```
        """

        return cls(color=None, width=0.0)

    @classmethod
    def solid(
        cls,
        color: str,
        *,
        width: float = 1.0,
        unit: str = "pt",
    ) -> StrokeStyle:
        """Create a visible solid stroke.

        Args:
            color: Stroke color.
            width: Stroke width.
            unit: Unit for ``width``.

        Returns:
            Stroke style configured with a visible color.

        Examples:
            ```python
            from oodocs import Shape, StrokeStyle

            shape = Shape.line(width=3, height=0, stroke=StrokeStyle.solid("334155", width=0.75))
            ```
        """

        return cls(color=color, width=width, unit=unit)

    def width_points(self, default_unit: str = "pt") -> float:
        """Return stroke width converted to points.

        Args:
            default_unit: Unit to use when the stroke unit is empty.

        Returns:
            Width in points.

        Examples:
            ```python
            stroke = StrokeStyle.solid("334155", width=0.75)
            width_points = stroke.width_points()
            ```
        """

        return length_to_inches(self.width, self.unit or default_unit) * 72.0


__all__ = ["BorderStyle", "StrokeStyle"]
