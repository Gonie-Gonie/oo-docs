"""Inline chip style objects and presets."""

from __future__ import annotations

from dataclasses import dataclass

from oodocs.core import normalize_color

_INLINE_CHIP_STYLE_FIELDS = (
    "background_color",
    "text_color",
    "border_color",
    "border_width",
    "padding_x",
    "padding_y",
    "radius",
    "font_size_delta",
    "font_name",
    "bold",
    "italic",
    "uppercase",
)


@dataclass(slots=True)
class InlineChipStyle:
    """Visual style for compact inline label chips.

    Padding and radius are expressed in em units so chips scale with the
    surrounding font. Border width and font size delta are expressed in points.

    Attributes:
        background_color: Chip background color as a hex string.
        text_color: Chip text color as a hex string.
        border_color: Optional chip border color as a hex string.
        border_width: Border width in points.
        padding_x: Horizontal padding in em units.
        padding_y: Vertical padding in em units.
        radius: Corner radius in em units.
        font_size_delta: Font-size delta in points.
        font_name: Optional font family override.
        bold: Whether chip text is bold.
        italic: Whether chip text is italic.
        uppercase: Whether display text is uppercased.

    Examples:
        ```python
        from oodocs import Document, InlineChipStyle, Paragraph, tag

        fragment = tag("beta", chip_style=InlineChipStyle(background_color="EEF2FF"))
        document = Document("Roadmap", Paragraph("Release channel: ", fragment))
        ```
    """

    background_color: str = "E8F1FF"
    text_color: str = "1F3A5F"
    border_color: str | None = "A7C7E7"
    border_width: float = 0.5
    padding_x: float = 0.38
    padding_y: float = 0.12
    radius: float = 0.5
    font_size_delta: float = -0.5
    font_name: str | None = None
    bold: bool = True
    italic: bool = False
    uppercase: bool = False

    def __post_init__(self) -> None:
        self.background_color = normalize_color(self.background_color) or "E8F1FF"
        self.text_color = normalize_color(self.text_color) or "1F3A5F"
        self.border_color = normalize_color(self.border_color)
        if self.border_width < 0:
            raise ValueError("InlineChipStyle.border_width must be >= 0")
        if self.padding_x < 0:
            raise ValueError("InlineChipStyle.padding_x must be >= 0")
        if self.padding_y < 0:
            raise ValueError("InlineChipStyle.padding_y must be >= 0")
        if self.radius < 0:
            raise ValueError("InlineChipStyle.radius must be >= 0")

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
        border_color="A7C7E7",
    ),
    "badge": InlineChipStyle(
        background_color="F3F4F6",
        text_color="1F2937",
        border_color="D1D5DB",
        padding_x=0.32,
    ),
    "status": InlineChipStyle(
        background_color="F3F4F6",
        text_color="374151",
        border_color="D1D5DB",
        uppercase=True,
    ),
    "keyboard": InlineChipStyle(
        background_color="F8FAFC",
        text_color="111827",
        border_color="CBD5E1",
        border_width=0.75,
        padding_x=0.28,
        padding_y=0.08,
        radius=0.22,
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
        border_color="BBF7D0",
        uppercase=True,
    ),
    "info": InlineChipStyle(
        background_color="E0F2FE",
        text_color="075985",
        border_color="BAE6FD",
        uppercase=True,
    ),
    "warning": InlineChipStyle(
        background_color="FEF3C7",
        text_color="92400E",
        border_color="FDE68A",
        uppercase=True,
    ),
    "danger": InlineChipStyle(
        background_color="FEE2E2",
        text_color="991B1B",
        border_color="FECACA",
        uppercase=True,
    ),
    "muted": InlineChipStyle(
        background_color="F3F4F6",
        text_color="374151",
        border_color="D1D5DB",
        uppercase=True,
    ),
}

__all__ = [
    "InlineChipStyle",
    "_DEFAULT_CHIP_STYLES",
    "_STATUS_CHIP_STYLES",
]
