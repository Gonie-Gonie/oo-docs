"""Styles for generated pages and generated document summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class TableOfContentsLevelStyle:
    """Optional display overrides for a table-of-contents level.

    Attributes:
        indent: Optional level indent.
        space_before: Optional spacing before entries at this level.
        space_after: Optional spacing after entries at this level.
        font_size_delta: Optional font-size delta from the base contents style.
        bold: Optional bold override.
        italic: Optional italic override.

    Examples:
        ```python
        from oodocs import Document, Section, TableOfContents
        from oodocs.styles.generated import TableOfContentsLevelStyle

        toc = TableOfContents(
            level_styles={1: TableOfContentsLevelStyle(indent=0.25, bold=True)}
        )
        document = Document("Report", toc, Section("Summary"))
        ```
    """

    indent: float | None = None
    space_before: float | None = None
    space_after: float | None = None
    font_size_delta: float | None = None
    bold: bool | None = None
    italic: bool | None = None


TableOfContentsLevelStyleInput = TableOfContentsLevelStyle | Mapping[str, object]


def coerce_table_of_contents_level_style(
    value: TableOfContentsLevelStyleInput,
) -> TableOfContentsLevelStyle:
    """Normalize a table-of-contents level style.

    Args:
        value: Existing style or mapping of ``TableOfContentsLevelStyle`` fields.

    Returns:
        A table-of-contents level style.

    Raises:
        TypeError: If ``value`` cannot be converted.

    Examples:
        ```python
        style = coerce_table_of_contents_level_style({"indent": 0.25, "bold": True})
        ```
    """

    if isinstance(value, TableOfContentsLevelStyle):
        return value
    if isinstance(value, Mapping):
        return TableOfContentsLevelStyle(**dict(value))
    raise TypeError(f"Unsupported table-of-contents level style: {type(value)!r}")


__all__ = ["TableOfContentsLevelStyle"]
