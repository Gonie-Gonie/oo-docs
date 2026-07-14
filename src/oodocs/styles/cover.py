"""Visual policy for standalone cover pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from oodocs.core import normalize_color, normalize_length_unit
from oodocs.styles.text import TextStyle


CoverAlignment = Literal["left", "center", "right"]
CoverVerticalAlignment = Literal["top", "center"]


@dataclass(frozen=True, slots=True)
class CoverPageStyle:
    """Layout, spacing, text, and logo sizing for a cover page."""

    name: str = "Cover page"
    text_alignment: CoverAlignment = "left"
    vertical_alignment: CoverVerticalAlignment = "top"
    top_spacing: float = 0.75
    section_spacing: float = 0.22
    logo_max_width: float = 2.0
    logo_max_height: float = 1.4
    unit: str = "in"
    accent_color: str | None = None
    accent_width: float = 0.08
    eyebrow_style: TextStyle = field(
        default_factory=lambda: TextStyle(font_size=10, uppercase=True)
    )
    organization_style: TextStyle = field(default_factory=lambda: TextStyle(font_size=11))
    date_style: TextStyle = field(default_factory=lambda: TextStyle(font_size=10))
    footer_style: TextStyle = field(default_factory=lambda: TextStyle(font_size=9))

    def __post_init__(self) -> None:
        if self.text_alignment not in {"left", "center", "right"}:
            raise ValueError("CoverPageStyle.text_alignment must be left, center, or right")
        if self.vertical_alignment not in {"top", "center"}:
            raise ValueError("CoverPageStyle.vertical_alignment must be top or center")
        object.__setattr__(self, "unit", normalize_length_unit(self.unit))
        object.__setattr__(self, "accent_color", normalize_color(self.accent_color))

    @classmethod
    def accented(
        cls,
        *,
        accent_color: str = "2563EB",
        text_alignment: CoverAlignment = "left",
    ) -> CoverPageStyle:
        """Return a left-accent cover style."""

        return cls(
            name="Accented cover",
            text_alignment=text_alignment,
            accent_color=accent_color,
        )

    @classmethod
    def centered_logo(cls) -> CoverPageStyle:
        """Return a centered cover style sized for a logo."""

        return cls(
            name="Centered logo cover",
            text_alignment="center",
            vertical_alignment="center",
            top_spacing=0.35,
            logo_max_width=2.4,
            logo_max_height=1.6,
        )

    @classmethod
    def named(cls, name: str) -> CoverPageStyle:
        """Resolve a built-in style name."""

        normalized = name.strip().casefold().replace("_", "-").replace(" ", "-")
        if normalized in {"accented", "accented-cover"}:
            return cls.accented()
        if normalized in {"centered-logo", "centered-logo-cover"}:
            return cls.centered_logo()
        raise KeyError(f"Unknown cover page style: {name!r}")


__all__ = ["CoverAlignment", "CoverPageStyle", "CoverVerticalAlignment"]
