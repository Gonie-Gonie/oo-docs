"""Inline chip style objects and presets."""

from __future__ import annotations

from dataclasses import dataclass, field

from oodocs.core import normalize_color
from oodocs.styles.base import _normalize_css_class
from oodocs.styles.border import BorderStyle
from oodocs.styles.spacing import Padding

_INLINE_CHIP_STYLE_FIELDS = (
    "css_class",
    "background_color",
    "text_color",
    "border",
    "padding",
    "font_size_delta",
    "font_name",
    "bold",
    "italic",
    "uppercase",
)


@dataclass(slots=True)
class InlineChipStyle:
    """Visual style for compact inline label chips.

    Padding and radius are typically expressed in em units so chips scale with
    the surrounding font. Border width and font size delta are expressed in
    points by default.

    Attributes:
        background_color: Chip background color as a hex string.
        text_color: Chip text color as a hex string.
        border: Chip border and corner radius.
        padding: Chip padding in em units.
        font_size_delta: Font-size delta in points.
        font_name: Optional font family override.
        bold: Whether chip text is bold.
        italic: Whether chip text is italic.
        uppercase: Whether display text is uppercased.
        css_class: Optional HTML class name or class list.

    Examples:
        ```python
        from oodocs import Document, InlineChipStyle, Paragraph, tag

        fragment = tag("beta", chip_style=InlineChipStyle(background_color="EEF2FF"))
        document = Document("Roadmap", Paragraph("Release channel: ", fragment))
        ```
    """

    css_class: str | None = None
    background_color: str = "E8F1FF"
    text_color: str = "1F3A5F"
    border: BorderStyle = field(
        default_factory=lambda: BorderStyle.solid(
            "A7C7E7",
            width=0.5,
            radius=0.5,
            radius_unit="em",
        )
    )
    padding: Padding = field(
        default_factory=lambda: Padding.symmetric(vertical=0.12, horizontal=0.38, unit="em")
    )
    font_size_delta: float = -0.5
    font_name: str | None = None
    bold: bool = True
    italic: bool = False
    uppercase: bool = False

    def __post_init__(self) -> None:
        self.css_class = _normalize_css_class(self.css_class)
        self.background_color = normalize_color(self.background_color) or "E8F1FF"
        self.text_color = normalize_color(self.text_color) or "1F3A5F"
        if not isinstance(self.border, BorderStyle):
            raise TypeError("InlineChipStyle.border must be a BorderStyle")
        if not isinstance(self.padding, Padding):
            raise TypeError("InlineChipStyle.padding must be a Padding")

    def merged(self, **overrides: object) -> InlineChipStyle:
        """Return a copy with selected fields replaced.

        Args:
            **overrides: Field values to replace.

        Returns:
            New chip style with the overrides applied.

        Raises:
            TypeError: If an override name is not a style field.
            ValueError: If resulting color or dimension values are invalid.

        Examples:
            ```python
            style = InlineChipStyle().merged(background_color="ECFDF3", text_color="166534")
            ```
        """

        values = {
            field_name: getattr(self, field_name)
            for field_name in _INLINE_CHIP_STYLE_FIELDS
        }
        for field_name, value in overrides.items():
            if field_name not in values:
                raise TypeError(f"Unsupported InlineChipStyle field: {field_name}")
            values[field_name] = value
        return InlineChipStyle(**values)


_DEFAULT_CHIP_STYLES = {
    "chip": InlineChipStyle(),
    "tag": InlineChipStyle(
        background_color="E8F1FF",
        text_color="1F3A5F",
        border=BorderStyle.solid("A7C7E7", width=0.5, radius=0.5, radius_unit="em"),
    ),
    "badge": InlineChipStyle(
        background_color="F3F4F6",
        text_color="1F2937",
        border=BorderStyle.solid("D1D5DB", width=0.5, radius=0.5, radius_unit="em"),
        padding=Padding.symmetric(vertical=0.12, horizontal=0.32, unit="em"),
    ),
    "status": InlineChipStyle(
        background_color="F3F4F6",
        text_color="374151",
        border=BorderStyle.solid("D1D5DB", width=0.5, radius=0.5, radius_unit="em"),
        uppercase=True,
    ),
    "keyboard": InlineChipStyle(
        background_color="F8FAFC",
        text_color="111827",
        border=BorderStyle.solid("CBD5E1", width=0.75, radius=0.22, radius_unit="em"),
        padding=Padding.symmetric(vertical=0.08, horizontal=0.28, unit="em"),
        font_size_delta=-0.5,
        font_name="Courier New",
        bold=False,
    ),
}

_STATUS_CHIP_STYLES = {
    "neutral": _DEFAULT_CHIP_STYLES["status"],
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
    "muted": InlineChipStyle(
        background_color="F3F4F6",
        text_color="374151",
        border=BorderStyle.solid("D1D5DB", width=0.5, radius=0.5, radius_unit="em"),
        uppercase=True,
    ),
}

__all__ = [
    "InlineChipStyle",
    "_DEFAULT_CHIP_STYLES",
    "_STATUS_CHIP_STYLES",
]
