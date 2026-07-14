"""Counter and list marker style objects."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Sequence

from oodocs.core import format_counter_value, normalize_counter_format


@dataclass(slots=True)
class CounterStyle:
    """Reusable counter formatting rules.

    Attributes:
        counter_format: Counter format name such as ``"decimal"`` or
            ``"upper-roman"``.
        prefix: Text prepended to each formatted value.
        suffix: Text appended to each formatted value.
        separator: Separator used by ``format_sequence``. Defaults to ``"."``.
        start: First counter value for zero-based consumers such as lists.
        bullet: Bullet glyph used when ``counter_format`` is ``"bullet"``.

    Examples:
        Format an ordered-list marker:

        ```python
        from oodocs.styles import CounterStyle

        marker = CounterStyle(counter_format="upper-roman", prefix="(", suffix=")")
        assert marker.format_value(3) == "(III)"
        ```
    """

    counter_format: str = "decimal"
    prefix: str = ""
    suffix: str = ""
    separator: str | None = None
    start: int = 1
    bullet: str = "\u2022"

    def __post_init__(self) -> None:
        self.counter_format = normalize_counter_format(self.counter_format)
        if self.start < 1:
            raise ValueError("CounterStyle.start must be >= 1")

    def format_value(self, value: int) -> str:
        """Format one counter value.

        Args:
            value: One-based counter value.

        Returns:
            Formatted counter value with prefix and suffix.
        """

        if self.counter_format == "none":
            return ""
        marker = format_counter_value(
            value,
            self.counter_format,
            bullet=self.bullet,
        )
        return f"{self.prefix}{marker}{self.suffix}"

    def format_sequence(self, values: Sequence[int]) -> str:
        """Format a sequence of counter values.

        Args:
            values: One-based counter values.

        Returns:
            Formatted values joined by ``separator``.
        """

        separator = "." if self.separator is None else self.separator
        return separator.join(self.format_value(value) for value in values)


@dataclass(slots=True)
class HeadingNumbering:
    """Configurable hierarchical numbering for authored headings.

    Attributes:
        enabled: Whether heading numbering is enabled.
        level_styles: Counter styles for successive heading levels.
        separator: Separator between level counters.
        prefix: Prefix before the full label.
        suffix: Suffix after the full label.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, Section, Theme
        from oodocs.styles import BlockDefaults, CounterStyle, HeadingNumbering

        numbering = HeadingNumbering(
            level_styles=(
                CounterStyle(counter_format="upper-roman"),
                CounterStyle(counter_format="decimal"),
            )
        )
        theme = Theme(blocks=BlockDefaults(heading_numbering=numbering))
        document = Document("Report", Section("Methods"), settings=DocumentSettings(theme=theme))
        ```
    """

    enabled: bool = True
    level_styles: tuple[CounterStyle, ...] = field(
        default_factory=lambda: (
            CounterStyle(),
            CounterStyle(),
            CounterStyle(),
            CounterStyle(),
        )
    )
    separator: str = "."
    prefix: str = ""
    suffix: str = ""

    def __post_init__(self) -> None:
        self.level_styles = tuple(_coerce_counter_style(value) for value in self.level_styles)
        if not self.level_styles:
            raise ValueError("HeadingNumbering.level_styles must not be empty")

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
            self.level_styles[min(index, len(self.level_styles) - 1)].format_value(value)
            for index, value in enumerate(counters)
        ]
        return f"{self.prefix}{self.separator.join(pieces)}{self.suffix}"


@dataclass(slots=True)
class ListStyle:
    """Marker styling for bullet and ordered lists.

    Attributes:
        marker: Counter style used for the marker.
        indent: List indent in inches.
        marker_gap: Gap between marker and item text in inches.
        item_spacing: Space after each list item paragraph in points.
        block_spacing: Space after the whole list in points.

    Examples:
        ```python
        from oodocs import Document, NumberedList
        from oodocs.styles import CounterStyle

        list_block = NumberedList(
            "Install",
            "Run",
            marker=CounterStyle(counter_format="lower-alpha", suffix=")"),
        )
        document = Document("Procedure", list_block)
        ```
    """

    marker: CounterStyle = field(default_factory=lambda: CounterStyle(suffix="."))
    indent: float = 0.25
    marker_gap: float = 0.1
    item_spacing: float = 3.0
    block_spacing: float = 8.0

    def __post_init__(self) -> None:
        self.marker = _coerce_counter_style(self.marker)
        if self.indent < 0:
            raise ValueError("ListStyle.indent must be >= 0")
        if self.marker_gap < 0:
            raise ValueError("ListStyle.marker_gap must be >= 0")
        if self.item_spacing < 0:
            raise ValueError("ListStyle.item_spacing must be >= 0")
        if self.block_spacing < 0:
            raise ValueError("ListStyle.block_spacing must be >= 0")

    def marker_for(self, index: int) -> str:
        """Return the rendered marker for a zero-based list item index.

        Args:
            index: Zero-based list item index.

        Returns:
            Rendered marker string.
        """

        return self.marker.format_value(index + self.marker.start)


def list_style_with_overrides(
    style: ListStyle | str | None,
    *,
    ordered: bool,
    **overrides: object | None,
) -> ListStyle | str | None:
    """Return a concrete list style when direct list keyword overrides are used.

    Args:
        style: Base list style, named list style, or ``None``.
        ordered: Whether the target list is ordered.
        **overrides: List style fields to override when not ``None``.

    Returns:
        ``None`` when no style is needed, otherwise a named or concrete list
        style.

    Examples:
        ```python
        style = list_style_with_overrides(
            None,
            ordered=True,
            marker=CounterStyle(counter_format="lower-alpha", suffix=")"),
        )
        ```
    """

    values = {name: value for name, value in overrides.items() if value is not None}
    if isinstance(style, str):
        if values:
            raise TypeError("Named list styles cannot be combined with direct style overrides")
        return style
    if style is None and not values:
        return None
    base = style or _default_list_style(ordered=ordered)
    merged = {
        style_field.name: getattr(base, style_field.name)
        for style_field in fields(ListStyle)
    }
    merged.update(values)
    return ListStyle(**merged)


def _default_list_style(*, ordered: bool) -> ListStyle:
    return (
        ListStyle()
        if ordered
        else ListStyle(marker=CounterStyle(counter_format="bullet", suffix=""))
    )


def _coerce_counter_style(value: CounterStyle | object) -> CounterStyle:
    if isinstance(value, CounterStyle):
        return value
    raise TypeError("counter style values must be CounterStyle instances")


__all__ = [
    "CounterStyle",
    "HeadingNumbering",
    "ListStyle",
    "list_style_with_overrides",
]
