"""Counter and list marker style objects."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Sequence

from oodocs.core import format_counter_value, normalize_counter_format

@dataclass(slots=True)
class HeadingNumbering:
    """Configurable hierarchical numbering for authored headings.

    Attributes:
        enabled: Whether heading numbering is enabled.
        level_counter_formats: Counter formats for successive heading levels.
        separator: Separator between level counters.
        prefix: Prefix before the full label.
        suffix: Suffix after the full label.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, Section, Theme

        numbering = HeadingNumbering(level_counter_formats=("upper-roman", "decimal"))
        theme = Theme(blocks=BlockDefaults(heading_numbering=numbering))
        document = Document("Report", Section("Methods"), settings=DocumentSettings(theme=theme))
        ```
    """

    enabled: bool = True
    level_counter_formats: tuple[str, ...] = ("decimal", "decimal", "decimal", "decimal")
    separator: str = "."
    prefix: str = ""
    suffix: str = ""

    def __post_init__(self) -> None:
        self.level_counter_formats = tuple(
            normalize_counter_format(value) for value in self.level_counter_formats
        )
        if not self.level_counter_formats:
            raise ValueError("HeadingNumbering.level_counter_formats must not be empty")

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
            format_counter_value(
                value,
                self.level_counter_formats[
                    min(index, len(self.level_counter_formats) - 1)
                ],
            )
            for index, value in enumerate(counters)
        ]
        return f"{self.prefix}{self.separator.join(pieces)}{self.suffix}"


@dataclass(slots=True)
class ListStyle:
    """Marker counter formatting for bullet and ordered lists.

    Attributes:
        marker_counter_format: Counter format for markers.
        bullet: Bullet glyph when ``marker_counter_format`` is ``"bullet"``.
        prefix: Marker prefix.
        suffix: Marker suffix.
        start: First counter value for ordered markers.
        indent: List indent in inches.
        marker_gap: Gap between marker and item text in inches.

    Examples:
        ```python
        from oodocs import Document, NumberedList

        list_block = NumberedList("Install", "Run", style=ListStyle(marker_counter_format="lower-alpha"))
        document = Document("Procedure", list_block)
        ```
    """

    marker_counter_format: str = "decimal"
    bullet: str = "\u2022"
    prefix: str = ""
    suffix: str = "."
    start: int = 1
    indent: float = 0.25
    marker_gap: float = 0.1

    def __post_init__(self) -> None:
        self.marker_counter_format = normalize_counter_format(self.marker_counter_format)
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

        if self.marker_counter_format == "none":
            return ""

        marker_value = format_counter_value(
            index + self.start,
            self.marker_counter_format,
            bullet=self.bullet,
        )
        return f"{self.prefix}{marker_value}{self.suffix}"


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

    Examples:
        ```python
        style = list_style_with_overrides(None, ordered=True, marker_counter_format="lower-alpha")
        ```
    """

    values = {name: value for name, value in overrides.items() if value is not None}
    if style is None and not values:
        return None
    base = style or (
        ListStyle()
        if ordered
        else ListStyle(marker_counter_format="bullet", suffix="")
    )
    merged = {style_field.name: getattr(base, style_field.name) for style_field in fields(ListStyle)}
    merged.update(values)
    return ListStyle(**merged)


__all__ = ["HeadingNumbering", "ListStyle", "list_style_with_overrides"]
