"""Styles for semantic description-list blocks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from oodocs.core import length_to_inches, normalize_length_unit
from oodocs.styles.base import _style_with_overrides
from oodocs.styles.blocks import ParagraphStyle
from oodocs.styles.text import TextStyle


DescriptionListLayout: TypeAlias = Literal["hanging", "stacked", "run-in"]


def description_list_style_with_overrides(
    style: DescriptionListStyle | str | None,
    **overrides: object | None,
) -> DescriptionListStyle | str:
    """Return a description-list style with non-``None`` overrides applied."""

    return _style_with_overrides(style, DescriptionListStyle, overrides)  # type: ignore[return-value]


@dataclass(slots=True)
class DescriptionListStyle:
    """Layout and typography for a semantic description list.

    ``term_width`` and ``term_gap`` use ``unit``. ``item_spacing`` is measured
    in points, matching paragraph spacing throughout OODocs.
    """

    layout: DescriptionListLayout = "hanging"
    term_width: float | None = 1.5
    term_text_style: TextStyle = field(default_factory=lambda: TextStyle(bold=True))
    definition_style: ParagraphStyle = field(
        default_factory=lambda: ParagraphStyle(space_after=0.0)
    )
    item_spacing: float = 8.0
    term_gap: float = 0.2
    unit: str = "in"

    def __post_init__(self) -> None:
        if self.layout not in {"hanging", "stacked", "run-in"}:
            raise ValueError(
                "DescriptionListStyle.layout must be 'hanging', 'stacked', or 'run-in'"
            )
        if self.term_width is not None and self.term_width <= 0:
            raise ValueError("DescriptionListStyle.term_width must be > 0")
        if self.item_spacing < 0:
            raise ValueError("DescriptionListStyle.item_spacing must be >= 0")
        if self.term_gap < 0:
            raise ValueError("DescriptionListStyle.term_gap must be >= 0")
        self.unit = normalize_length_unit(self.unit)

    def term_width_in_inches(self, default_unit: str = "in") -> float | None:
        """Return the preferred term width in inches."""

        if self.term_width is None:
            return None
        return length_to_inches(self.term_width, self.unit or default_unit)

    def term_gap_in_inches(self, default_unit: str = "in") -> float:
        """Return the gap between term and definition in inches."""

        return length_to_inches(self.term_gap, self.unit or default_unit)


__all__ = [
    "DescriptionListLayout",
    "DescriptionListStyle",
    "description_list_style_with_overrides",
]
