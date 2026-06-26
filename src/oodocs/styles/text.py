"""Inline text style objects."""

from __future__ import annotations

from dataclasses import dataclass

from oodocs.core import normalize_color

@dataclass(slots=True)
class TextStyle:
    """Inline text styling overrides.

    Each field is optional so styles can be layered and merged.

    Attributes:
        font_name: Optional font family.
        font_size: Optional font size.
        text_color: Optional text color as a hex string.
        highlight_color: Optional highlight color as a hex string.
        bold: Optional bold override.
        italic: Optional italic override.
        underline: Optional underline override.
        strikethrough: Optional strikethrough override.
        small_caps: Optional small-caps override.
        uppercase: Optional uppercase override.
        subscript: Optional subscript override.
        superscript: Optional superscript override.

    Examples:
        ```python
        from oodocs import Document, Paragraph, Text, TextStyle

        fragment = Text("Important", style=TextStyle(bold=True))
        document = Document("Notes", Paragraph("Status: ", fragment))
        ```
    """

    font_name: str | None = None
    font_size: float | None = None
    text_color: str | None = None
    highlight_color: str | None = None
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    strikethrough: bool | None = None
    small_caps: bool | None = None
    uppercase: bool | None = None
    subscript: bool | None = None
    superscript: bool | None = None

    def __post_init__(self) -> None:
        self.text_color = normalize_color(self.text_color)
        self.highlight_color = normalize_color(self.highlight_color)
        if self.subscript and self.superscript:
            raise ValueError("TextStyle cannot set both subscript and superscript")

    def merged(self, *others: TextStyle | None) -> TextStyle:
        """Return a new style with later values overriding earlier ones.

        Args:
            *others: Styles to overlay from left to right.

        Returns:
            New merged text style.

        Raises:
            ValueError: If the merged style sets both subscript and superscript.
        """

        merged = TextStyle(
            font_name=self.font_name,
            font_size=self.font_size,
            text_color=self.text_color,
            highlight_color=self.highlight_color,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strikethrough=self.strikethrough,
            small_caps=self.small_caps,
            uppercase=self.uppercase,
            subscript=self.subscript,
            superscript=self.superscript,
        )
        for other in others:
            if other is None:
                continue
            for field_name in (
                "font_name",
                "font_size",
                "text_color",
                "highlight_color",
                "bold",
                "italic",
                "underline",
                "strikethrough",
                "small_caps",
                "uppercase",
                "subscript",
                "superscript",
            ):
                value = getattr(other, field_name)
                if value is not None:
                    setattr(merged, field_name, value)
        if merged.subscript and merged.superscript:
            raise ValueError("TextStyle cannot set both subscript and superscript")
        return merged

__all__ = ["TextStyle"]
