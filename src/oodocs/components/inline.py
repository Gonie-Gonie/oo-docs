"""Inline authoring fragments and helper constructors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence, TYPE_CHECKING

from oodocs.components.equations import equation_plain_text
from oodocs.core import normalize_color
from oodocs.layout.theme import TextStyle

if TYPE_CHECKING:
    from oodocs.components.references import CitationSource


@dataclass(slots=True)
class Text:
    """Base inline text fragment.

    Args:
        value: Literal text content.
        style: Optional inline style overrides.

    Examples:
        ```python
        from oodocs import Paragraph, Text, TextStyle

        paragraph = Paragraph(Text("Important", style=TextStyle(bold=True)))
        ```
    """

    value: str
    style: TextStyle = field(default_factory=TextStyle)

    def plain_text(self) -> str:
        """Return the fragment without styling metadata.

        Returns:
            Literal text content for this fragment.
        """

        return self.value

    @classmethod
    def styled(cls, value: str, **style_values: object) -> Text:
        """Create a plain text fragment with inline style values.

        Args:
            value: Literal text content.
            **style_values: Keyword arguments passed to ``TextStyle``.

        Returns:
            Styled text fragment.

        Examples:
            ```python
            fragment = Text.styled("Approved", color="008000", bold=True)
            ```
        """

        return cls(value=value, style=TextStyle(**style_values))

    @classmethod
    def bold(cls, value: str, style: TextStyle | None = None) -> Bold:
        """Create a bold text fragment.

        Args:
            value: Literal text content.
            style: Additional style values to merge.

        Returns:
            Bold text fragment.
        """

        return Bold(value, style=style)

    @classmethod
    def italic(cls, value: str, style: TextStyle | None = None) -> Italic:
        """Create an italic text fragment.

        Args:
            value: Literal text content.
            style: Additional style values to merge.

        Returns:
            Italic text fragment.
        """

        return Italic(value, style=style)

    @classmethod
    def code(cls, value: str, style: TextStyle | None = None) -> Monospace:
        """Create a monospace text fragment.

        Args:
            value: Literal text content.
            style: Additional style values to merge.

        Returns:
            Monospace text fragment.
        """

        return Monospace(value, style=style)

    @classmethod
    def color(
        cls,
        value: str,
        color: str,
        style: TextStyle | None = None,
    ) -> Text:
        """Create a colored text fragment.

        Args:
            value: Literal text content.
            color: Text color as a hex string.
            style: Additional style values to merge.

        Returns:
            Text fragment with the requested color.
        """

        return cls(
            value=value,
            style=TextStyle(color=color).merged(style),
        )

    @classmethod
    def highlight(
        cls,
        value: str,
        color: str = "FFFF00",
        style: TextStyle | None = None,
    ) -> Highlight:
        """Create a highlighted text fragment.

        Args:
            value: Literal text content.
            color: Highlight color as a hex string.
            style: Additional style values to merge.

        Returns:
            Highlighted text fragment.
        """

        return Highlight(value, color=color, style=style)

    @classmethod
    def strikethrough(
        cls,
        value: str,
        style: TextStyle | None = None,
    ) -> Strikethrough:
        """Create a strikethrough text fragment.

        Args:
            value: Literal text content.
            style: Additional style values to merge.

        Returns:
            Strikethrough text fragment.
        """

        return Strikethrough(value, style=style)

    @classmethod
    def superscript(
        cls,
        value: object,
        style: TextStyle | None = None,
    ) -> Text:
        """Create superscript inline text.

        Args:
            value: Value converted to text.
            style: Additional style values to merge.

        Returns:
            Superscript text fragment.
        """

        return cls(value=str(value), style=TextStyle(superscript=True).merged(style))

    @classmethod
    def subscript(
        cls,
        value: object,
        style: TextStyle | None = None,
    ) -> Text:
        """Create subscript inline text.

        Args:
            value: Value converted to text.
            style: Additional style values to merge.

        Returns:
            Subscript text fragment.
        """

        return cls(value=str(value), style=TextStyle(subscript=True).merged(style))

    @classmethod
    def from_markup(
        cls,
        source: str,
        *,
        style: TextStyle | None = None,
    ) -> list[Text]:
        """Parse simple markdown-like markup into inline fragments.

        Args:
            source: Markup source text.
            style: Base style applied to parsed fragments.

        Returns:
            Parsed inline fragments.

        Examples:
            ```python
            fragments = Text.from_markup("Use **bold** and `code` inline.")
            ```
        """

        from oodocs.components.markup import markup

        return markup(source, style=style)


class Bold(Text):
    """Bold inline text.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Examples:
        ```python
        from oodocs.components.inline import Bold

        fragment = Bold("required")
        ```
    """

    def __init__(self, value: str, style: TextStyle | None = None) -> None:
        super().__init__(value=value, style=TextStyle(bold=True).merged(style))


class Italic(Text):
    """Italic inline text.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Examples:
        ```python
        from oodocs.components.inline import Italic

        fragment = Italic("optional")
        ```
    """

    def __init__(self, value: str, style: TextStyle | None = None) -> None:
        super().__init__(value=value, style=TextStyle(italic=True).merged(style))


class Monospace(Text):
    """Monospace inline text.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Examples:
        ```python
        from oodocs.components.inline import Monospace

        fragment = Monospace("pip install oodocs")
        ```
    """

    def __init__(self, value: str, style: TextStyle | None = None) -> None:
        super().__init__(
            value=value,
            style=TextStyle(font_name="Courier New").merged(style),
        )


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
        from oodocs import InlineChipStyle, tag

        fragment = tag("beta", chip_style=InlineChipStyle(background_color="EEF2FF"))
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


class InlineChip(Text):
    """Compact inline visual token for tags, badges, status, and key labels.

    Args:
        value: Display value converted to text.
        chip_style: Optional visual chip style. Defaults depend on ``kind``.
        kind: Chip kind used for default styling.
        style: Optional surrounding text style.

    Raises:
        ValueError: If ``kind`` is invalid.

    Examples:
        ```python
        from oodocs import InlineChip

        chip = InlineChip("approved", kind="status")
        ```
    """

    __slots__ = ("chip_style", "kind")

    def __init__(
        self,
        value: object,
        *,
        chip_style: InlineChipStyle | None = None,
        kind: str = "chip",
        style: TextStyle | None = None,
    ) -> None:
        normalized_kind = _normalize_chip_kind(kind)
        super().__init__(value=str(value), style=style or TextStyle())
        self.chip_style = chip_style or _default_chip_style(normalized_kind)
        self.kind = normalized_kind

    def display_text(self) -> str:
        """Return display text after chip style transforms.

        Returns:
            Uppercased or original chip text depending on the style.

        Examples:
            ```python
            chip = InlineChip("approved", kind="status")
            assert chip.display_text() == "APPROVED"
            ```
        """

        return self.value.upper() if self.chip_style.uppercase else self.value

    def plain_text(self) -> str:
        """Return the chip display text for plain-text output.

        Returns:
            Display text after chip style transforms.
        """

        return self.display_text()


class Highlight(Text):
    """Highlighted inline text.

    Args:
        value: Literal text content.
        color: Highlight color as a hex string.
        style: Additional style values to merge.

    Examples:
        ```python
        from oodocs.components.inline import Highlight

        fragment = Highlight("changed", color="FFF3B0")
        ```
    """

    def __init__(
        self,
        value: str,
        *,
        color: str = "FFFF00",
        style: TextStyle | None = None,
    ) -> None:
        super().__init__(
            value=value,
            style=TextStyle(highlight_color=color).merged(style),
        )


class Strikethrough(Text):
    """Strikethrough inline text.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Examples:
        ```python
        from oodocs.components.inline import Strikethrough

        fragment = Strikethrough("deprecated")
        ```
    """

    def __init__(self, value: str, style: TextStyle | None = None) -> None:
        super().__init__(
            value=value,
            style=TextStyle(strikethrough=True).merged(style),
        )


class LineBreak(Text):
    """Manual line break inside a paragraph.

    Attributes:
        value: Newline text emitted for plain-text extraction.
        style: Text style inherited from ``Text``.

    Examples:
        ```python
        from oodocs import Paragraph, line_break

        paragraph = Paragraph("First line", line_break(), "Second line")
        ```
    """

    def __init__(self) -> None:
        super().__init__(value="\n")

    def plain_text(self) -> str:
        """Return the line break as a newline in plain text.

        Returns:
            A newline character.

        Examples:
            ```python
            assert LineBreak().plain_text() == "\\n"
            ```
        """

        return "\n"


class BlockReference(Text):
    """Inline reference to a numbered or anchored document object.

    Args:
        target: Document object to reference.
        *label: Optional inline label override.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import Paragraph

        target = Paragraph("Details")
        reference = target.reference("the details")
        ```
    """

    __slots__ = ("target", "label")

    def __init__(
        self,
        target: object,
        *label: InlineInput,
        style: TextStyle | None = None,
    ) -> None:
        super().__init__(value="", style=style or TextStyle())
        self.target = target
        self.label = coerce_inlines(label) if label else None

    def plain_text(self) -> str:
        """Return placeholder reference text before numbering is resolved.

        Returns:
            Custom label plain text or an automatic label with ``?``.
        """

        if self.label is not None:
            return "".join(fragment.plain_text() for fragment in self.label)
        return f"{_reference_label_prefix(self.target)} ?"


def _reference_label_prefix(target: object) -> str:
    countable_block = _as_countable_block(target)
    if countable_block is not None:
        return countable_block.reference_label
    target_name = type(target).__name__
    if target_name == "Table":
        return "Table"
    if target_name in {"Figure", "SubFigure", "SubFigureGroup"}:
        return "Figure"
    if target_name == "Equation":
        return "Equation"
    if target_name == "Paragraph":
        return "Paragraph"
    if target_name == "CodeBlock":
        return "Code block"
    if target_name == "Box":
        return "Box"
    if target_name == "Part":
        return "Part"
    if target_name in {"Chapter", "Section", "Subsection", "Subsubsection"}:
        return "Section"
    return type(target).__name__


def reference(
    target: object,
    *label: InlineInput,
    style: TextStyle | None = None,
) -> BlockReference:
    """Create an explicit inline reference to a document object.

    Args:
        target: Document object to reference.
        *label: Optional inline label override.
        style: Optional inline style.

    Returns:
        Inline reference fragment.

    Raises:
        TypeError: If ``target`` is not referenceable.

    Examples:
        ```python
        from oodocs import Figure, Paragraph, reference

        figure = Figure("diagram.png", caption="System diagram")
        paragraph = Paragraph("See ", reference(figure), ".")
        ```
    """

    if not _is_referenceable(target):
        raise TypeError(f"Unsupported reference target: {type(target)!r}")
    return BlockReference(target, *label, style=style)


class Citation(Text):
    """Inline citation rendered from a bibliography entry or key.

    Args:
        target: Citation source object or citation key.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import CitationSource, cite

        source = CitationSource("Doe 2024", author="Doe", title="A Study")
        citation = cite(source)
        ```
    """

    __slots__ = ("target",)

    def __init__(self, target: CitationSource | str, style: TextStyle | None = None) -> None:
        super().__init__(value="", style=style or TextStyle())
        self.target = target

    def plain_text(self) -> str:
        """Return a placeholder citation label.

        Returns:
            Placeholder citation text used before render indexing.
        """

        return "[?]"

    @classmethod
    def reference(
        cls,
        target: CitationSource | str,
        *,
        style: TextStyle | None = None,
    ) -> Citation:
        """Create an inline citation fragment.

        Args:
            target: Citation source object or citation key.
            style: Optional inline style.

        Returns:
            Inline citation fragment.
        """

        return cls(target, style=style)


def cite(target: CitationSource | str, *, style: TextStyle | None = None) -> Citation:
    """Create an inline citation fragment.

    Args:
        target: Citation source object or citation key.
        style: Optional inline style.

    Returns:
        Inline citation fragment.

    Examples:
        ```python
        from oodocs import Paragraph, cite

        paragraph = Paragraph("Prior work supports this ", cite("doe2024"), ".")
        ```
    """

    return Citation.reference(target, style=style)


class Hyperlink(Text):
    """Inline hyperlink to an external URL or internal anchor.

    Args:
        target: External URL or internal anchor target.
        *label: Optional visible label. Defaults to ``target``.
        internal: Whether the target is an internal anchor.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import Paragraph, link

        paragraph = Paragraph("Open ", link("https://example.com", "the dashboard"))
        ```
    """

    __slots__ = ("target", "label", "internal")

    def __init__(
        self,
        target: str,
        *label: InlineInput,
        internal: bool = False,
        style: TextStyle | None = None,
    ) -> None:
        super().__init__(
            value="",
            style=TextStyle(color="0563C1", underline=True).merged(style),
        )
        self.target = target
        self.label = coerce_inlines(label or (target,))
        self.internal = internal

    def plain_text(self) -> str:
        """Return the visible hyperlink label.

        Returns:
            Plain text for the link label.
        """

        return "".join(fragment.plain_text() for fragment in self.label)

    @classmethod
    def external(
        cls,
        target: str,
        *label: InlineInput,
        style: TextStyle | None = None,
    ) -> Hyperlink:
        """Create an external hyperlink.

        Args:
            target: External URL.
            *label: Optional visible label. Defaults to ``target``.
            style: Optional inline style.

        Returns:
            External hyperlink fragment.
        """

        return cls(target, *label, internal=False, style=style)

    @classmethod
    def internal_anchor(
        cls,
        target: str,
        *label: InlineInput,
        style: TextStyle | None = None,
    ) -> Hyperlink:
        """Create an internal hyperlink.

        Args:
            target: Internal anchor target.
            *label: Optional visible label. Defaults to ``target``.
            style: Optional inline style.

        Returns:
            Internal hyperlink fragment.
        """

        return cls(target, *label, internal=True, style=style)


class Comment(Text):
    """Inline text annotated with a numbered comment.

    Args:
        value: Visible inline text.
        *comment: Comment body content.
        author: Optional comment author.
        initials: Optional author initials.
        style: Optional inline style for the visible text.

    Examples:
        ```python
        from oodocs import comment

        fragment = comment("metric", "Confirm source before publishing.", author="QA")
        ```
    """

    __slots__ = ("comment", "author", "initials")

    def __init__(
        self,
        value: str,
        *comment: InlineInput,
        author: str | None = None,
        initials: str | None = None,
        style: TextStyle | None = None,
    ) -> None:
        super().__init__(value=value, style=style or TextStyle())
        self.comment = coerce_inlines(comment)
        self.author = author
        self.initials = initials

    def plain_text(self) -> str:
        """Return the visible inline text with a placeholder marker.

        Returns:
            Text plus a placeholder comment marker.
        """

        return f"{self.value}[?]"

    @classmethod
    def annotated(
        cls,
        value: str,
        *note: InlineInput,
        author: str | None = None,
        initials: str | None = None,
        style: TextStyle | None = None,
    ) -> Comment:
        """Create inline text with an attached numbered comment.

        Args:
            value: Visible inline text.
            *note: Comment body content.
            author: Optional comment author.
            initials: Optional author initials.
            style: Optional inline style for the visible text.

        Returns:
            Inline comment fragment.
        """

        return cls(
            value,
            *note,
            author=author,
            initials=initials,
            style=style,
        )


def comment(
    value: str,
    *note: InlineInput,
    author: str | None = None,
    initials: str | None = None,
    style: TextStyle | None = None,
) -> Comment:
    """Create inline text with an attached numbered comment.

    Args:
        value: Visible inline text.
        *note: Comment body content.
        author: Optional comment author.
        initials: Optional author initials.
        style: Optional inline style for the visible text.

    Returns:
        Inline comment fragment.

    Examples:
        ```python
        fragment = comment("estimate", "Needs finance review.", initials="FR")
        ```
    """

    return Comment.annotated(
        value,
        *note,
        author=author,
        initials=initials,
        style=style,
    )


class Footnote(Text):
    """Inline text annotated with a numbered portable footnote.

    Args:
        value: Visible inline text.
        *note: Footnote body content.
        style: Optional inline style for the visible text.

    Examples:
        ```python
        from oodocs import footnote

        fragment = footnote("SLA", "Service-level agreement.")
        ```
    """

    __slots__ = ("note",)

    def __init__(
        self,
        value: str,
        *note: InlineInput,
        style: TextStyle | None = None,
    ) -> None:
        super().__init__(value=value, style=style or TextStyle())
        self.note = coerce_inlines(note)

    def plain_text(self) -> str:
        """Return the visible inline text with a placeholder marker.

        Returns:
            Text plus a placeholder footnote marker.
        """

        return f"{self.value}[?]"

    @classmethod
    def annotated(
        cls,
        value: str,
        *note: InlineInput,
        style: TextStyle | None = None,
    ) -> Footnote:
        """Create inline text with an attached numbered footnote.

        Args:
            value: Visible inline text.
            *note: Footnote body content.
            style: Optional inline style for the visible text.

        Returns:
            Inline footnote fragment.
        """

        return cls(value, *note, style=style)


def footnote(
    value: str,
    *note: InlineInput,
    style: TextStyle | None = None,
) -> Footnote:
    """Create inline text with an attached numbered footnote.

    Args:
        value: Visible inline text.
        *note: Footnote body content.
        style: Optional inline style for the visible text.

    Returns:
        Inline footnote fragment.

    Examples:
        ```python
        fragment = footnote("baseline", "Measured on 2026-06-01.")
        ```
    """

    return Footnote.annotated(value, *note, style=style)


class Math(Text):
    """Inline math fragment written in lightweight LaTeX syntax.

    Args:
        value: LaTeX-like math source.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import Paragraph, math

        paragraph = Paragraph("Energy is ", math(r"E = mc^2"), ".")
        ```
    """

    def __init__(self, value: str, style: TextStyle | None = None) -> None:
        super().__init__(value=value, style=TextStyle().merged(style))

    def plain_text(self) -> str:
        """Return a readable plain-text math approximation.

        Returns:
            Plain-text approximation of the math source.
        """

        return equation_plain_text(self.value)

    @classmethod
    def inline(cls, value: str, *, style: TextStyle | None = None) -> Math:
        """Create an inline math fragment.

        Args:
            value: LaTeX-like math source.
            style: Optional inline style.

        Returns:
            Inline math fragment.
        """

        return cls(value, style=style)


def math(value: str, *, style: TextStyle | None = None) -> Math:
    """Create an inline math fragment.

    Args:
        value: LaTeX-like math source.
        style: Optional inline style.

    Returns:
        Inline math fragment.

    Examples:
        ```python
        fragment = math(r"\alpha + \beta")
        ```
    """

    return Math.inline(value, style=style)


def styled(value: str, **style_values: object) -> Text:
    """Create a plain text fragment with inline style values.

    Args:
        value: Literal text content.
        **style_values: Keyword arguments passed to ``TextStyle``.

    Returns:
        Styled text fragment.

    Examples:
        ```python
        fragment = styled("Green", color="008000", bold=True)
        ```
    """

    return Text.styled(value, **style_values)


def bold(value: str, *, style: TextStyle | None = None) -> Bold:
    """Create a bold text fragment.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Returns:
        Bold text fragment.

    Examples:
        ```python
        fragment = bold("required")
        ```
    """

    return Text.bold(value, style=style)


def italic(value: str, *, style: TextStyle | None = None) -> Italic:
    """Create an italic text fragment.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Returns:
        Italic text fragment.

    Examples:
        ```python
        fragment = italic("optional")
        ```
    """

    return Text.italic(value, style=style)


def code(value: str, *, style: TextStyle | None = None) -> Monospace:
    """Create a monospace text fragment.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Returns:
        Monospace text fragment.

    Examples:
        ```python
        fragment = code("pip install oodocs")
        ```
    """

    return Text.code(value, style=style)


def superscript(value: object, *, style: TextStyle | None = None) -> Text:
    """Create superscript inline text.

    Args:
        value: Value converted to text.
        style: Additional style values to merge.

    Returns:
        Superscript text fragment.

    Examples:
        ```python
        fragment = superscript(2)
        ```
    """

    return Text.superscript(value, style=style)


def subscript(value: object, *, style: TextStyle | None = None) -> Text:
    """Create subscript inline text.

    Args:
        value: Value converted to text.
        style: Additional style values to merge.

    Returns:
        Subscript text fragment.

    Examples:
        ```python
        fragment = subscript("n")
        ```
    """

    return Text.subscript(value, style=style)


def prescript(
    superscript_value: object,
    subscript_value: object,
    body: InlineInput,
    *,
    style: TextStyle | None = None,
) -> list[Text]:
    """Create front superscript/subscript fragments before inline content.

    Args:
        superscript_value: Value used for the prescript superscript.
        subscript_value: Value used for the prescript subscript.
        body: Inline content following the prescripts.
        style: Optional inline style for the prescript fragments.

    Returns:
        Inline fragments containing prescripts and body content.

    Examples:
        ```python
        fragments = prescript(14, 6, "C")
        ```
    """

    return [
        superscript(superscript_value, style=style),
        subscript(subscript_value, style=style),
        *coerce_inlines((body,)),
    ]


def _normalize_chip_kind(kind: str) -> str:
    normalized = kind.strip().lower().replace("_", "-")
    if not normalized or any(not (char.isalnum() or char == "-") for char in normalized):
        raise ValueError(f"Unsupported inline chip kind: {kind!r}")
    return normalized


def _default_chip_style(kind: str) -> InlineChipStyle:
    normalized = _normalize_chip_kind(kind)
    style = _DEFAULT_CHIP_STYLES.get(normalized, _DEFAULT_CHIP_STYLES["chip"])
    return style.merged()


def _default_status_chip_style(state: str) -> InlineChipStyle:
    normalized = state.strip().lower().replace("_", "-")
    style = _STATUS_CHIP_STYLES.get(normalized)
    if style is None:
        allowed = ", ".join(sorted(_STATUS_CHIP_STYLES))
        raise ValueError(f"Unsupported status state: {state!r}; expected one of {allowed}")
    return style.merged()


def _chip(
    value: object,
    *,
    kind: str,
    chip_style: InlineChipStyle | None = None,
    style: TextStyle | None = None,
    **style_values: object,
) -> InlineChip:
    resolved_style = chip_style or _default_chip_style(kind)
    if style_values:
        resolved_style = resolved_style.merged(**style_values)
    return InlineChip(value, chip_style=resolved_style, kind=kind, style=style)


def tag(
    value: object,
    *,
    chip_style: InlineChipStyle | None = None,
    style: TextStyle | None = None,
    **style_values: object,
) -> InlineChip:
    """Create a category or keyword chip.

    Args:
        value: Display value converted to text.
        chip_style: Optional visual chip style.
        style: Optional surrounding text style.
        **style_values: Chip style field overrides.

    Returns:
        Inline chip fragment.

    Examples:
        ```python
        fragment = tag("api")
        ```
    """

    return _chip(value, kind="tag", chip_style=chip_style, style=style, **style_values)


def badge(
    value: object,
    *,
    chip_style: InlineChipStyle | None = None,
    style: TextStyle | None = None,
    **style_values: object,
) -> InlineChip:
    """Create a count, label, or small emphasis chip.

    Args:
        value: Display value converted to text.
        chip_style: Optional visual chip style.
        style: Optional surrounding text style.
        **style_values: Chip style field overrides.

    Returns:
        Inline chip fragment.

    Examples:
        ```python
        fragment = badge("v1.2")
        ```
    """

    return _chip(value, kind="badge", chip_style=chip_style, style=style, **style_values)


def status(
    value: object,
    *,
    state: str = "neutral",
    chip_style: InlineChipStyle | None = None,
    style: TextStyle | None = None,
    **style_values: object,
) -> InlineChip:
    """Create a state indicator chip.

    Args:
        value: Display value converted to text.
        state: Named status palette to use when ``chip_style`` is omitted.
        chip_style: Optional visual chip style.
        style: Optional surrounding text style.
        **style_values: Chip style field overrides.

    Returns:
        Inline chip fragment.

    Raises:
        ValueError: If ``state`` is not supported.

    Examples:
        ```python
        fragment = status("passed", state="success")
        ```
    """

    resolved_style = chip_style or _default_status_chip_style(state)
    if style_values:
        resolved_style = resolved_style.merged(**style_values)
    return InlineChip(value, chip_style=resolved_style, kind="status", style=style)


def keyboard(
    value: object,
    *,
    chip_style: InlineChipStyle | None = None,
    style: TextStyle | None = None,
    **style_values: object,
) -> InlineChip:
    """Create a keyboard key chip.

    Args:
        value: Display value converted to text.
        chip_style: Optional visual chip style.
        style: Optional surrounding text style.
        **style_values: Chip style field overrides.

    Returns:
        Inline chip fragment.

    Examples:
        ```python
        fragment = keyboard("Ctrl+S")
        ```
    """

    return _chip(value, kind="keyboard", chip_style=chip_style, style=style, **style_values)


def color(
    value: str,
    color: str,
    *,
    style: TextStyle | None = None,
) -> Text:
    """Create a colored text fragment.

    Args:
        value: Literal text content.
        color: Text color as a hex string.
        style: Additional style values to merge.

    Returns:
        Text fragment with the requested color.

    Examples:
        ```python
        fragment = color("Alert", "C00000")
        ```
    """

    return Text.color(value, color, style=style)


def highlight(
    value: str,
    color: str = "FFFF00",
    *,
    style: TextStyle | None = None,
) -> Highlight:
    """Create a highlighted text fragment.

    Args:
        value: Literal text content.
        color: Highlight color as a hex string.
        style: Additional style values to merge.

    Returns:
        Highlighted text fragment.

    Examples:
        ```python
        fragment = highlight("review")
        ```
    """

    return Text.highlight(value, color=color, style=style)


def strike(value: str, *, style: TextStyle | None = None) -> Strikethrough:
    """Create a strikethrough text fragment.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Returns:
        Strikethrough text fragment.

    Examples:
        ```python
        fragment = strike("deprecated")
        ```
    """

    return Text.strikethrough(value, style=style)


def strikethrough(value: str, *, style: TextStyle | None = None) -> Strikethrough:
    """Create a strikethrough text fragment.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Returns:
        Strikethrough text fragment.

    Examples:
        ```python
        fragment = strikethrough("removed")
        ```
    """

    return Text.strikethrough(value, style=style)


def line_break() -> LineBreak:
    """Create a manual line break inside a paragraph.

    Returns:
        Line break inline fragment.

    Examples:
        ```python
        from oodocs import Paragraph, line_break

        paragraph = Paragraph("Line 1", line_break(), "Line 2")
        ```
    """

    return LineBreak()


def link(
    target: str,
    *label: InlineInput,
    style: TextStyle | None = None,
) -> Hyperlink:
    """Create an external hyperlink.

    Args:
        target: External URL.
        *label: Optional visible label. Defaults to ``target``.
        style: Optional inline style.

    Returns:
        External hyperlink fragment.

    Examples:
        ```python
        fragment = link("https://example.com", "Example")
        ```
    """

    return Hyperlink.external(target, *label, style=style)


InlineInput = Text | str | Sequence["InlineInput"] | None | object


def coerce_inlines(values: Iterable[InlineInput]) -> list[Text]:
    """Normalize supported inline inputs into text fragments.

    Args:
        values: Inline fragments, strings, nested inline sequences, positioned
            inline blocks, or ``None``.

    Returns:
        A flat list of text-like inline fragments.

    Raises:
        TypeError: If a value cannot be converted or must be referenced
            explicitly.

    Examples:
        ```python
        fragments = coerce_inlines(["A ", bold("word"), None])
        ```
    """

    normalized: list[Text] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, Text):
            normalized.append(value)
            continue
        if _is_positioned_inline(value):
            normalized.append(value)  # type: ignore[arg-type]
            continue
        if _is_referenceable(value):
            raise TypeError(
                "Document objects must be cited explicitly with reference(obj) "
                "or obj.reference() before they are placed inside Paragraph(...)"
            )
        if isinstance(value, str):
            normalized.append(Text(value))
            continue
        if isinstance(value, Sequence):
            normalized.extend(coerce_inlines(value))
            continue
        raise TypeError(f"Unsupported inline value: {type(value)!r}")
    return normalized


def _is_referenceable(value: object) -> bool:
    if _as_countable_block(value) is not None:
        return True
    block_name = type(value).__name__
    return block_name in {
        "Box",
        "Chapter",
        "CodeBlock",
        "Equation",
        "Figure",
        "Paragraph",
        "Part",
        "Section",
        "SubFigure",
        "SubFigureGroup",
        "Subsection",
        "Subsubsection",
        "Table",
    }


def _as_countable_block(value: object) -> object | None:
    try:
        from oodocs.components.blocks import CountableBlock
    except ImportError:
        return None
    if isinstance(value, CountableBlock):
        return value
    return None


def _is_positioned_inline(value: object) -> bool:
    value_type = type(value)
    return (
        value_type.__module__ == "oodocs.components.positioning"
        and value_type.__name__ in {"ImageBox", "Shape", "TextBox"}
    )


_BlockReference = BlockReference

__all__ = [
    "Bold",
    "Citation",
    "Comment",
    "Footnote",
    "Highlight",
    "Hyperlink",
    "InlineChip",
    "InlineChipStyle",
    "Italic",
    "LineBreak",
    "Math",
    "Monospace",
    "Strikethrough",
    "Text",
    "_BlockReference",
    "badge",
    "bold",
    "code",
    "color",
    "coerce_inlines",
    "cite",
    "comment",
    "footnote",
    "highlight",
    "italic",
    "keyboard",
    "link",
    "line_break",
    "math",
    "prescript",
    "reference",
    "status",
    "strike",
    "strikethrough",
    "styled",
    "subscript",
    "superscript",
    "tag",
]
