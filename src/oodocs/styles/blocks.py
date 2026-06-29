"""Block-level style objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from oodocs.core import (
    length_to_inches,
    normalize_color,
    normalize_length_unit,
    normalize_text_alignment,
)
from oodocs.styles.base import _normalize_css_class, _style_with_overrides
from oodocs.styles.border import BorderStyle
from oodocs.styles.spacing import Padding
from oodocs.styles.text import TextStyle


BoxTitlePosition = Literal["top", "side"]


def paragraph_style_with_overrides(
    style: ParagraphStyle | str | None,
    **overrides: object | None,
) -> ParagraphStyle | str:
    """Return a paragraph style with direct keyword overrides applied.

    Args:
        style: Base paragraph style or ``None``.
        **overrides: Paragraph style fields to override when not ``None``.

    Returns:
        Existing named style, copied style, or a new style with overrides
        applied.

    Examples:
        ```python
        style = paragraph_style_with_overrides(None, text_alignment="center")
        ```
    """

    return _style_with_overrides(style, ParagraphStyle, overrides)  # type: ignore[return-value]


def box_style_with_overrides(
    style: BoxStyle | str | None,
    **overrides: object | None,
) -> BoxStyle | str:
    """Return a box style with direct keyword overrides applied.

    Args:
        style: Base box style or ``None``.
        **overrides: Box style fields to override when not ``None``.

    Returns:
        Existing named style, copied style, or a new style with overrides
        applied.

    Examples:
        ```python
        style = box_style_with_overrides(None, background_color="F8FAFC")
        ```
    """

    return _style_with_overrides(style, BoxStyle, overrides)  # type: ignore[return-value]


@dataclass(slots=True)
class ParagraphStyle:
    """Block-level paragraph spacing and alignment settings.

    Attributes:
        text_alignment: Optional text alignment.
        space_before: Optional spacing before the paragraph.
        space_after: Optional spacing after the paragraph.
        leading: Optional line spacing.
        left_indent: Optional left indent.
        right_indent: Optional right indent.
        first_line_indent: Optional first-line indent.
        keep_together: Optional keep-together flag.
        keep_with_next: Optional keep-with-next flag.
        page_break_before: Optional page-break-before flag.
        widow_control: Optional widow-control flag.
        unit: Unit for length values.
        css_class: Optional HTML class name or class list.

    Examples:
        ```python
        from oodocs import Document, Paragraph, ParagraphStyle

        paragraph = Paragraph("Indented text", style=ParagraphStyle.hanging())
        document = Document("Notes", paragraph)
        ```
    """

    text_alignment: str | None = None
    space_before: float | None = None
    space_after: float | None = 12.0
    leading: float | None = None
    left_indent: float | None = None
    right_indent: float | None = None
    first_line_indent: float | None = None
    keep_together: bool | None = None
    keep_with_next: bool | None = None
    page_break_before: bool | None = None
    widow_control: bool | None = None
    unit: str | None = None
    css_class: str | None = None

    def __post_init__(self) -> None:
        self.css_class = _normalize_css_class(self.css_class)
        self.text_alignment = (
            normalize_text_alignment(self.text_alignment)
            if self.text_alignment is not None
            else None
        )
        self.unit = normalize_length_unit(self.unit) if self.unit is not None else None
        if self.space_before is not None and self.space_before < 0:
            raise ValueError("ParagraphStyle.space_before must be >= 0")
        if self.space_after is not None and self.space_after < 0:
            raise ValueError("ParagraphStyle.space_after must be >= 0")
        if self.leading is not None and self.leading <= 0:
            raise ValueError("ParagraphStyle.leading must be > 0")
        if self.left_indent is not None and self.left_indent < 0:
            raise ValueError("ParagraphStyle.left_indent must be >= 0")
        if self.right_indent is not None and self.right_indent < 0:
            raise ValueError("ParagraphStyle.right_indent must be >= 0")

    @classmethod
    def hanging(
        cls,
        left: float = 0.5,
        *,
        by: float | None = None,
        text_alignment: str | None = None,
        space_before: float | None = None,
        space_after: float | None = 12.0,
        leading: float | None = None,
        keep_together: bool | None = None,
        keep_with_next: bool | None = None,
        page_break_before: bool | None = None,
        widow_control: bool | None = None,
        unit: str | None = None,
        css_class: str | None = None,
    ) -> ParagraphStyle:
        """Create a hanging-indent paragraph style.

        Args:
            left: Left indent.
            by: Hanging amount. Defaults to ``left``.
            text_alignment: Optional text alignment.
            space_before: Optional spacing before the paragraph.
            space_after: Optional spacing after the paragraph.
            leading: Optional line spacing.
            keep_together: Optional keep-together flag.
            keep_with_next: Optional keep-with-next flag.
            page_break_before: Optional page-break-before flag.
            widow_control: Optional widow-control flag.
            unit: Unit for length values.
            css_class: Optional HTML class name or class list.

        Returns:
            Paragraph style with a negative first-line indent.

        Raises:
            ValueError: If ``by`` is negative.

        Examples:
            ```python
            style = ParagraphStyle.hanging(left=0.5, by=0.25, unit="in")
            ```
        """

        hanging_by = left if by is None else by
        if hanging_by < 0:
            raise ValueError("ParagraphStyle.hanging by must be >= 0")
        return cls(
            text_alignment=text_alignment,
            space_before=space_before,
            space_after=space_after,
            leading=leading,
            left_indent=left,
            first_line_indent=-hanging_by,
            keep_together=keep_together,
            keep_with_next=keep_with_next,
            page_break_before=page_break_before,
            widow_control=widow_control,
            unit=unit,
            css_class=css_class,
        )

    def left_indent_in_inches(self, default_unit: str) -> float | None:
        """Return left indent in inches.

        Args:
            default_unit: Unit to use when this style has no explicit unit.

        Returns:
            Left indent in inches, or ``None``.
        """

        return self._indent_in_inches(self.left_indent, default_unit)

    def right_indent_in_inches(self, default_unit: str) -> float | None:
        """Return right indent in inches.

        Args:
            default_unit: Unit to use when this style has no explicit unit.

        Returns:
            Right indent in inches, or ``None``.
        """

        return self._indent_in_inches(self.right_indent, default_unit)

    def first_line_indent_in_inches(self, default_unit: str) -> float | None:
        """Return first-line indent in inches.

        Args:
            default_unit: Unit to use when this style has no explicit unit.

        Returns:
            First-line indent in inches, or ``None``.
        """

        return self._indent_in_inches(self.first_line_indent, default_unit)

    def _indent_in_inches(self, value: float | None, default_unit: str) -> float | None:
        if value is None:
            return None
        return length_to_inches(value, self.unit or default_unit)


@dataclass(slots=True)
class RunInTitleStyle:
    """Run-in title styling for titled paragraphs.

    Attributes:
        text_style: Inline styling applied to the paragraph title.
        separator: Text inserted between the title and paragraph body.

    Examples:
        ```python
        from oodocs import Document, Paragraph, RunInTitleStyle, TextStyle

        paragraph = Paragraph(
            "The rollout completed successfully.",
            title="Outcome",
            title_style=RunInTitleStyle(TextStyle(bold=True, text_color="166534")),
        )
        document = Document("Release Notes", paragraph)
        ```
    """

    text_style: TextStyle = field(default_factory=lambda: TextStyle(bold=True))
    separator: str = " "

    def __post_init__(self) -> None:
        if not isinstance(self.separator, str):
            raise TypeError("RunInTitleStyle.separator must be a string")

@dataclass(slots=True)
class BoxStyle:
    """Shared box styling for visually grouped content.

    Attributes:
        border: Border style.
        background_color: Hex fill color.
        title_background_color: Optional title band fill color.
        title_text_color: Optional title text color.
        title_position: Title placement, either ``"top"`` or ``"side"``.
        shadow: Whether HTML output should render a tcolorbox-like shadow.
        padding: Inner padding.
        space_after: Space after the box in points.
        width: Optional box width in ``unit``.
        unit: Unit for ``width`` when a physical width is set.
        block_alignment: Optional block placement alignment override.
        css_class: Optional HTML class name or class list.

    Examples:
        Style a callout box with grouped border and padding objects:

        ```python
        from oodocs import BorderStyle, Box, BoxStyle, Document, Padding, Paragraph

        style = BoxStyle(
            border=BorderStyle.solid("CBD5E1", width=0.75),
            padding=Padding.symmetric(vertical=8, horizontal=12),
            background_color="F7FAFC",
        )
        box = Box(Paragraph("Review scope before release."), title="Note", style=style)
        document = Document("Notes", box)
        ```
    """

    border: BorderStyle = field(
        default_factory=lambda: BorderStyle.solid("B7C2D0", width=0.75)
    )
    background_color: str = "F7FAFC"
    title_background_color: str | None = None
    title_text_color: str | None = None
    title_position: BoxTitlePosition = "top"
    shadow: bool = False
    padding: Padding = field(default_factory=lambda: Padding.all(6.0))
    space_after: float = 12.0
    width: float | None = None
    unit: str | None = None
    block_alignment: str | None = None
    css_class: str | None = None

    def __post_init__(self) -> None:
        self.css_class = _normalize_css_class(self.css_class)
        if not isinstance(self.border, BorderStyle):
            raise TypeError("BoxStyle.border must be a BorderStyle")
        if not isinstance(self.padding, Padding):
            raise TypeError("BoxStyle.padding must be a Padding")
        self.background_color = normalize_color(self.background_color) or "F7FAFC"
        self.title_background_color = normalize_color(self.title_background_color)
        self.title_text_color = normalize_color(self.title_text_color)
        if self.title_position not in {"top", "side"}:
            raise ValueError("BoxStyle.title_position must be 'top' or 'side'")
        if not isinstance(self.shadow, bool):
            raise TypeError("BoxStyle.shadow must be a bool")
        self.unit = normalize_length_unit(self.unit) if self.unit is not None else None
        if self.space_after < 0:
            raise ValueError("BoxStyle.space_after must be >= 0")
        if self.width is not None and self.width <= 0:
            raise ValueError("BoxStyle.width must be > 0")
        if self.block_alignment is not None and self.block_alignment not in {"left", "center", "right"}:
            raise ValueError(f"Unsupported BoxStyle block_alignment: {self.block_alignment!r}")

__all__ = [
    "BoxStyle",
    "ParagraphStyle",
    "RunInTitleStyle",
    "box_style_with_overrides",
    "paragraph_style_with_overrides",
]
