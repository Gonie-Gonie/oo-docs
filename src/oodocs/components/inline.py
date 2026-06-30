"""Inline authoring fragments and helper constructors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence, TYPE_CHECKING

from oodocs.components.equations import equation_plain_text
from oodocs.styles import (
    InlineChipStyle,
    StyleSheet,
    TextStyle,
)

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
        from oodocs import Document, Paragraph, Text, TextStyle

        paragraph = Paragraph(Text("Important", style=TextStyle(bold=True)))
        document = Document("Notes", paragraph)
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
            fragment = Text.styled("Approved", text_color="008000", bold=True)
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
    def inline_code(cls, value: str, style: TextStyle | None = None) -> InlineCode:
        """Create a monospace text fragment.

        Args:
            value: Literal text content.
            style: Additional style values to merge.

        Returns:
            InlineCode text fragment.
        """

        return InlineCode(value, style=style)

    @classmethod
    def text_color(
        cls,
        value: str,
        text_color: str,
        style: TextStyle | None = None,
    ) -> Text:
        """Create a colored text fragment.

        Args:
            value: Literal text content.
            text_color: Text color as a hex string.
            style: Additional style values to merge.

        Returns:
            Text fragment with the requested color.
        """

        return cls(
            value=value,
            style=TextStyle(text_color=text_color).merged(style),
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
        from oodocs import Document, Paragraph
        from oodocs.components.inline import Bold

        document = Document("Checklist", Paragraph("Approval is ", Bold("required"), "."))
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
        from oodocs import Document, Paragraph
        from oodocs.components.inline import Italic

        document = Document("Checklist", Paragraph("This step is ", Italic("optional"), "."))
        ```
    """

    def __init__(self, value: str, style: TextStyle | None = None) -> None:
        super().__init__(value=value, style=TextStyle(italic=True).merged(style))


class InlineCode(Text):
    """Inline code text.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Examples:
        ```python
        from oodocs import Document, Paragraph
        from oodocs.components.inline import InlineCode

        document = Document("Install", Paragraph("Run ", InlineCode("pip install oodocs"), "."))
        ```
    """

    def __init__(self, value: str, style: TextStyle | None = None) -> None:
        super().__init__(
            value=value,
            style=TextStyle(font_name="Courier New").merged(style),
        )


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
        from oodocs import Document, InlineChip, Paragraph

        chip = InlineChip("approved", kind="status")
        document = Document("Review", Paragraph("Status: ", chip))
        ```
    """

    __slots__ = ("chip_style", "kind")

    def __init__(
        self,
        value: object,
        *,
        chip_style: InlineChipStyle | str | None = None,
        kind: str = "chip",
        style: TextStyle | None = None,
    ) -> None:
        normalized_kind = _normalize_chip_kind(kind)
        super().__init__(value=str(value), style=style or TextStyle())
        self.chip_style = chip_style or _default_chip_style(normalized_kind)
        self.kind = normalized_kind

    def display_text(self, chip_style: InlineChipStyle | None = None) -> str:
        """Return display text after chip style transforms.

        Returns:
            Uppercased or original chip text depending on the style.

        Examples:
            ```python
            chip = InlineChip("approved", kind="status")
            assert chip.display_text() == "APPROVED"
            ```
        """

        style = chip_style or self.chip_style
        return self.value.upper() if isinstance(style, InlineChipStyle) and style.uppercase else self.value

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
        from oodocs import Document, Paragraph
        from oodocs.components.inline import Highlight

        document = Document("Diff", Paragraph("Field ", Highlight("changed", color="FFF3B0")))
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
        from oodocs import Document, Paragraph
        from oodocs.components.inline import Strikethrough

        document = Document("Plan", Paragraph(Strikethrough("deprecated"), " option removed."))
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
        from oodocs import Document, Paragraph, line_break

        paragraph = Paragraph("First line", line_break(), "Second line")
        document = Document("Two-Line Note", paragraph)
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


@dataclass(slots=True, init=False)
class ReferenceFormat:
    """Formatting options for object references.

    Args:
        label: Optional singular label override such as ``"Fig."``.
        plural_label: Optional plural label for ``refs(...)`` when all targets
            share the same reference kind.
        capitalized: Whether to capitalize the rendered label.
        prefix: Text inserted before the rendered reference.
        suffix: Text inserted after the rendered reference.
        separator: Separator between reference items.
        last_separator: Separator before the final item.
        range_separator: Separator between the first and last item for
            ``ref_range(...)``.
        page: Whether the author requested a page-aware reference. Renderers
            currently degrade this to an ordinary reference and validation emits
            a compatibility warning.

    Examples:
        ```python
        from oodocs import refs
        from oodocs.references import ReferenceFormat

        fragments = refs([figure_a, figure_b], reference_format=ReferenceFormat(plural_label="Figures"))
        ```
    """

    label: str | None
    plural_label: str | None
    capitalized: bool
    prefix: str
    suffix: str
    separator: str
    last_separator: str
    range_separator: str
    page: bool

    def __init__(
        self,
        *,
        label: str | None = None,
        plural_label: str | None = None,
        capitalized: bool = False,
        prefix: str = "",
        suffix: str = "",
        separator: str = ", ",
        last_separator: str = " and ",
        range_separator: str = "-",
        page: bool = False,
    ) -> None:
        self.label = _normalize_optional_reference_text(label, "label")
        self.plural_label = _normalize_optional_reference_text(plural_label, "plural_label")
        self.capitalized = bool(capitalized)
        self.prefix = str(prefix)
        self.suffix = str(suffix)
        self.separator = str(separator)
        self.last_separator = str(last_separator)
        self.range_separator = str(range_separator)
        self.page = bool(page)

    def merged(self, **overrides: object) -> ReferenceFormat:
        """Return a copy with selected fields overridden."""

        values = {
            "label": self.label,
            "plural_label": self.plural_label,
            "capitalized": self.capitalized,
            "prefix": self.prefix,
            "suffix": self.suffix,
            "separator": self.separator,
            "last_separator": self.last_separator,
            "range_separator": self.range_separator,
            "page": self.page,
        }
        values.update(overrides)
        return ReferenceFormat(**values)


def _normalize_optional_reference_text(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"ReferenceFormat.{name} must not be empty")
    return normalized


class BlockReference(Text):
    """Inline reference to a numbered or anchored document object.

    Args:
        target: Document object to reference.
        *label: Optional inline label override.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import Document, Paragraph

        target = Paragraph("Details")
        document = Document("Report", target, Paragraph("See ", target.reference("the details"), "."))
        ```
    """

    __slots__ = ("target", "label", "reference_format")

    def __init__(
        self,
        target: object,
        *label: InlineInput,
        style: TextStyle | None = None,
        reference_format: ReferenceFormat | None = None,
    ) -> None:
        super().__init__(value="", style=style or TextStyle())
        self.target = target
        self.label = coerce_inlines(label) if label else None
        self.reference_format = reference_format or ReferenceFormat()

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
    if target_name in {"SubTable", "SubTableGroup"}:
        return "Table"
    reference_label = getattr(target, "reference_label", None)
    if isinstance(reference_label, str) and reference_label:
        return reference_label
    if target_name == "Paragraph":
        return "Paragraph"
    if target_name == "CodeBlock":
        return "Code block"
    if target_name == "Box":
        return "Box"
    if target_name == "Part":
        return "Part"
    if target_name in {"Chapter", "Section", "Subsection", "SubSubsection"}:
        return "Section"
    return type(target).__name__


def reference(
    target: object,
    *label: InlineInput,
    style: TextStyle | None = None,
    reference_format: ReferenceFormat | None = None,
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
        from oodocs import Figure, Paragraph
        from oodocs.references import reference

        figure = Figure("diagram.png", caption="System diagram")
        paragraph = Paragraph("See ", reference(figure), ".")
        ```
    """

    if not _is_referenceable(target):
        raise TypeError(f"Unsupported reference target: {type(target)!r}")
    return BlockReference(target, *label, style=style, reference_format=reference_format)


def ref(
    target: object,
    *label: InlineInput,
    style: TextStyle | None = None,
    reference_format: ReferenceFormat | None = None,
) -> BlockReference:
    """Create an inline object reference.

    This is a shorter alias for ``reference(...)`` matching common LaTeX
    ``cleveref`` authoring style.
    """

    return reference(target, *label, style=style, reference_format=reference_format)


def Ref(
    target: object,
    *label: InlineInput,
    style: TextStyle | None = None,
    reference_format: ReferenceFormat | None = None,
) -> BlockReference:
    """Create a capitalized inline object reference."""

    base = reference_format or ReferenceFormat()
    return reference(
        target,
        *label,
        style=style,
        reference_format=base.merged(capitalized=True),
    )


class ReferenceGroup(Text):
    """Inline reference to multiple document objects.

    Args:
        targets: Reference targets.
        reference_format: Formatting rules for labels and separators.
        range_reference: Whether to render the targets as a range.
        style: Optional inline style.
    """

    __slots__ = ("targets", "reference_format", "range_reference")

    def __init__(
        self,
        targets: Sequence[object],
        *,
        reference_format: ReferenceFormat | None = None,
        range_reference: bool = False,
        style: TextStyle | None = None,
    ) -> None:
        if isinstance(targets, (str, bytes)):
            raise TypeError("ReferenceGroup targets must be document objects")
        normalized = tuple(targets)
        minimum = 2 if range_reference else 1
        if len(normalized) < minimum:
            raise ValueError(
                "ref_range requires two targets"
                if range_reference
                else "refs requires at least one target"
            )
        for target in normalized:
            if not _is_referenceable(target):
                raise TypeError(f"Unsupported reference target: {type(target)!r}")
        super().__init__(value="", style=style or TextStyle())
        self.targets = normalized
        self.reference_format = reference_format or ReferenceFormat()
        self.range_reference = range_reference

    def plain_text(self) -> str:
        """Return placeholder reference text before numbering is resolved."""

        if self.range_reference:
            return f"{_reference_label_prefix(self.targets[0])} ?{self.reference_format.range_separator}?"
        return self.reference_format.separator.join(
            f"{_reference_label_prefix(target)} ?" for target in self.targets
        )


def refs(
    targets: Sequence[object],
    *,
    style: TextStyle | None = None,
    reference_format: ReferenceFormat | None = None,
    label: str | None = None,
    plural_label: str | None = None,
    separator: str | None = None,
    last_separator: str | None = None,
) -> ReferenceGroup:
    """Create an inline reference list for several document objects."""

    base = reference_format or ReferenceFormat()
    overrides: dict[str, object] = {}
    if label is not None:
        overrides["label"] = label
    if plural_label is not None:
        overrides["plural_label"] = plural_label
    if separator is not None:
        overrides["separator"] = separator
    if last_separator is not None:
        overrides["last_separator"] = last_separator
    return ReferenceGroup(
        targets,
        style=style,
        reference_format=base.merged(**overrides) if overrides else base,
    )


def ref_range(
    start: object,
    end: object,
    *,
    style: TextStyle | None = None,
    reference_format: ReferenceFormat | None = None,
    label: str | None = None,
    plural_label: str | None = None,
    range_separator: str | None = None,
) -> ReferenceGroup:
    """Create an inline reference range from two document objects."""

    base = reference_format or ReferenceFormat()
    overrides: dict[str, object] = {}
    if label is not None:
        overrides["label"] = label
    if plural_label is not None:
        overrides["plural_label"] = plural_label
    if range_separator is not None:
        overrides["range_separator"] = range_separator
    return ReferenceGroup(
        (start, end),
        style=style,
        reference_format=base.merged(**overrides) if overrides else base,
        range_reference=True,
    )


def paren_ref(
    target: object,
    *,
    style: TextStyle | None = None,
    reference_format: ReferenceFormat | None = None,
) -> BlockReference:
    """Create a parenthesized inline object reference."""

    base = reference_format or ReferenceFormat()
    return reference(
        target,
        style=style,
        reference_format=base.merged(prefix="(", suffix=")"),
    )


def page_ref(
    target: object,
    *,
    style: TextStyle | None = None,
    reference_format: ReferenceFormat | None = None,
) -> BlockReference:
    """Create a page-aware reference request.

    Renderers currently degrade this to an ordinary reference and validation
    reports a warning so authors can decide whether that is acceptable.
    """

    base = reference_format or ReferenceFormat()
    return reference(
        target,
        style=style,
        reference_format=base.merged(page=True),
    )


class Citation(Text):
    """Inline citation rendered from a bibliography entry or key.

    Args:
        target: Citation source object or citation key.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import CitationSource, Document, Paragraph, cite

        source = CitationSource("A Study", key="doe2024", authors=("Doe",), year="2024")
        document = Document("Paper", Paragraph("Prior work ", cite("doe2024"), "."), citations=[source])
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
        from oodocs import Document, Paragraph, link

        paragraph = Paragraph("Open ", link("https://example.com", "the dashboard"))
        document = Document("Operations", paragraph)
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
            style=TextStyle().merged(style),
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


_URL_SOFT_BREAK = "\u200b"
_URL_BREAK_AFTER = frozenset("/?#&=:%._-~")
_URL_MAX_UNBROKEN_SEGMENT = 24


def _breakable_url_label(value: str) -> str:
    text = str(value)
    if _URL_SOFT_BREAK in text:
        return text
    parts: list[str] = []
    segment_length = 0
    last_index = len(text) - 1
    for index, character in enumerate(text):
        parts.append(character)
        segment_length += 1
        if index == last_index:
            continue
        if character in _URL_BREAK_AFTER or segment_length >= _URL_MAX_UNBROKEN_SEGMENT:
            parts.append(_URL_SOFT_BREAK)
            segment_length = 0
    return "".join(parts)


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
        from oodocs import Document, Paragraph, comment

        fragment = comment("metric", "Confirm source before publishing.", author="QA")
        document = Document("Review", Paragraph("Check ", fragment, "."))
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


class Todo(Comment):
    """Inline TODO annotation rendered through the comment workflow.

    Args:
        *note: TODO note body.
        owner: Optional responsible person.
        status: Short TODO status label.
        value: Visible inline anchor text. Defaults to ``"TODO"``.
        initials: Optional Word-comment initials.
        style: Optional inline style for the visible text.

    Examples:
        ```python
        from oodocs import Paragraph
        from oodocs.review import Todo

        paragraph = Paragraph("Units ", Todo("Verify unit conversion.", owner="QA"))
        ```
    """

    __slots__ = ("owner", "status")

    def __init__(
        self,
        *note: InlineInput,
        owner: str | None = None,
        status: str = "todo",
        value: str = "TODO",
        initials: str | None = None,
        style: TextStyle | None = None,
    ) -> None:
        normalized_status = str(status).strip()
        if not normalized_status:
            raise ValueError("Todo.status must not be empty")
        self.owner = str(owner).strip() if owner is not None else None
        self.status = normalized_status
        super().__init__(
            value,
            *note,
            author=self.owner,
            initials=initials,
            style=style,
        )


def todo(
    *note: InlineInput,
    owner: str | None = None,
    status: str = "todo",
    value: str = "TODO",
    initials: str | None = None,
    style: TextStyle | None = None,
) -> Todo:
    """Create an inline TODO annotation.

    Args:
        *note: TODO note body.
        owner: Optional responsible person.
        status: Short TODO status label.
        value: Visible inline anchor text.
        initials: Optional Word-comment initials.
        style: Optional inline style.

    Returns:
        Inline TODO fragment.
    """

    return Todo(
        *note,
        owner=owner,
        status=status,
        value=value,
        initials=initials,
        style=style,
    )


class MarginNote(Comment):
    """Inline margin note with renderer-specific fallback behavior.

    Args:
        *note: Margin note body.
        side: Preferred side, ``"left"`` or ``"right"``.
        value: Optional visible inline anchor text.
        author: Optional comment author used by DOCX fallback.
        initials: Optional Word-comment initials.
        style: Optional inline style for the visible anchor.

    Examples:
        ```python
        from oodocs import Paragraph
        from oodocs.review import MarginNote

        paragraph = Paragraph("Assumption", MarginNote("Check this assumption."))
        ```
    """

    __slots__ = ("side",)

    def __init__(
        self,
        *note: InlineInput,
        side: str = "right",
        value: str = "",
        author: str | None = None,
        initials: str | None = None,
        style: TextStyle | None = None,
    ) -> None:
        if side not in {"left", "right"}:
            raise ValueError("MarginNote.side must be 'left' or 'right'")
        self.side = side
        super().__init__(
            value,
            *note,
            author=author,
            initials=initials,
            style=style,
        )


def margin_note(
    *note: InlineInput,
    side: str = "right",
    value: str = "",
    author: str | None = None,
    initials: str | None = None,
    style: TextStyle | None = None,
) -> MarginNote:
    """Create an inline margin note.

    Args:
        *note: Margin note body.
        side: Preferred side, ``"left"`` or ``"right"``.
        value: Optional visible inline anchor text.
        author: Optional comment author used by DOCX fallback.
        initials: Optional Word-comment initials.
        style: Optional inline style.

    Returns:
        Inline margin-note fragment.
    """

    return MarginNote(
        *note,
        side=side,
        value=value,
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
        stream: Footnote stream name. Streams are numbered independently and
            can use separate marker styles through ``Theme(footnotes=...)``.

    Examples:
        ```python
        from oodocs import Document, Paragraph, footnote

        fragment = footnote("SLA", "Service-level agreement.")
        document = Document("Report", Paragraph("The SLA", fragment, " was met."))
        ```
    """

    __slots__ = ("note", "stream")

    def __init__(
        self,
        value: str,
        *note: InlineInput,
        style: TextStyle | None = None,
        stream: str = "default",
    ) -> None:
        super().__init__(value=value, style=style or TextStyle())
        self.note = coerce_inlines(note)
        self.stream = _normalize_footnote_stream(stream)

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
        stream: str = "default",
    ) -> Footnote:
        """Create inline text with an attached numbered footnote.

        Args:
            value: Visible inline text.
            *note: Footnote body content.
            style: Optional inline style for the visible text.
            stream: Footnote stream name.

        Returns:
            Inline footnote fragment.
        """

        return cls(value, *note, style=style, stream=stream)


def footnote(
    value: str,
    *note: InlineInput,
    style: TextStyle | None = None,
    stream: str = "default",
) -> Footnote:
    """Create inline text with an attached numbered footnote.

    Args:
        value: Visible inline text.
        *note: Footnote body content.
        style: Optional inline style for the visible text.
        stream: Footnote stream name.

    Returns:
        Inline footnote fragment.

    Examples:
        ```python
        fragment = footnote("baseline", "Measured on 2026-06-01.")
        ```
    """

    return Footnote.annotated(value, *note, style=style, stream=stream)


def _normalize_footnote_stream(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("Footnote stream must not be empty")
    return normalized


class Math(Text):
    """Inline math fragment written in lightweight LaTeX syntax.

    Args:
        value: LaTeX-like math source.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import Document, Paragraph, math

        paragraph = Paragraph("Energy is ", math(r"E = mc^2"), ".")
        document = Document("Physics Note", paragraph)
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
        fragment = styled("Green", text_color="008000", bold=True)
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


def inline_code(value: str, *, style: TextStyle | None = None) -> InlineCode:
    """Create a monospace text fragment.

    Args:
        value: Literal text content.
        style: Additional style values to merge.

    Returns:
        InlineCode text fragment.

    Examples:
        ```python
        fragment = inline_code("pip install oodocs")
        ```
    """

    return Text.inline_code(value, style=style)


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


_STATUS_STYLE_NAMES = {
    "neutral",
    "success",
    "info",
    "warning",
    "danger",
    "muted",
}


def _default_chip_style(kind: str) -> str:
    normalized = _normalize_chip_kind(kind)
    if normalized in {"tag", "badge", "keyboard"}:
        return normalized
    if normalized == "status":
        return "status.neutral"
    return "tag"


def _default_status_chip_style(state: str) -> str:
    normalized = state.strip().lower().replace("_", "-")
    if normalized not in _STATUS_STYLE_NAMES:
        allowed = ", ".join(sorted(_STATUS_STYLE_NAMES))
        raise ValueError(f"Unsupported status state: {state!r}; expected one of {allowed}")
    return f"status.{normalized}"


def _default_chip_style_object(style_name: str) -> InlineChipStyle:
    style = StyleSheet.default().resolve("chip", style_name)
    if not isinstance(style, InlineChipStyle):
        raise TypeError(f"Default chip style {style_name!r} did not resolve to InlineChipStyle")
    return style


def _chip(
    value: object,
    *,
    kind: str,
    chip_style: InlineChipStyle | str | None = None,
    style: TextStyle | None = None,
    **style_values: object,
) -> InlineChip:
    default_style_name = _default_chip_style(kind)
    resolved_style = chip_style or default_style_name
    if style_values:
        if chip_style is None:
            resolved_style = _default_chip_style_object(default_style_name)
        elif isinstance(resolved_style, str):
            raise TypeError("Named chip styles cannot be combined with direct style overrides")
        resolved_style = resolved_style.merged(**style_values)
    return InlineChip(value, chip_style=resolved_style, kind=kind, style=style)


def tag(
    value: object,
    *,
    chip_style: InlineChipStyle | str | None = None,
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
    chip_style: InlineChipStyle | str | None = None,
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
    chip_style: InlineChipStyle | str | None = None,
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

    default_style_name = _default_status_chip_style(state)
    resolved_style = chip_style or default_style_name
    if style_values:
        if chip_style is None:
            resolved_style = _default_chip_style_object(default_style_name)
        elif isinstance(resolved_style, str):
            raise TypeError("Named chip styles cannot be combined with direct style overrides")
        resolved_style = resolved_style.merged(**style_values)
    return InlineChip(value, chip_style=resolved_style, kind="status", style=style)


def keyboard(
    value: object,
    *,
    chip_style: InlineChipStyle | str | None = None,
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


def text_color(
    value: str,
    text_color: str,
    *,
    style: TextStyle | None = None,
) -> Text:
    """Create a colored text fragment.

    Args:
        value: Literal text content.
        text_color: Text color as a hex string.
        style: Additional style values to merge.

    Returns:
        Text fragment with the requested color.

    Examples:
        ```python
        fragment = text_color("Alert", "C00000")
        ```
    """

    return Text.text_color(value, text_color, style=style)


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


def url(
    target: str,
    label: InlineInput | None = None,
    *,
    breakable: bool = True,
    style: TextStyle | None = None,
) -> Hyperlink:
    """Create a display-friendly external URL hyperlink.

    Args:
        target: External URL. The link target is preserved exactly.
        label: Optional visible label. Defaults to the URL itself.
        breakable: Whether to insert zero-width soft break points in the
            visible URL label.
        style: Optional inline style.

    Returns:
        External hyperlink fragment.

    Examples:
        ```python
        fragment = url("https://example.com/releases/latest")
        labeled = url("https://example.com", label="Project site")
        ```
    """

    visible_label: InlineInput
    if label is None:
        visible_label = _breakable_url_label(target) if breakable else target
    else:
        visible_label = label
    return Hyperlink.external(target, visible_label, style=style)


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
    if _as_equation(value) is not None:
        return True
    block_name = type(value).__name__
    return block_name in {
        "Box",
        "Chapter",
        "CodeBlock",
        "Figure",
        "Paragraph",
        "Part",
        "Section",
            "SubFigure",
            "SubFigureGroup",
            "SubTable",
            "SubTableGroup",
            "Subsection",
        "SubSubsection",
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


def _as_equation(value: object) -> object | None:
    try:
        from oodocs.components.blocks import Equation
    except ImportError:
        return None
    if isinstance(value, Equation):
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
    "Italic",
    "LineBreak",
    "MarginNote",
    "Math",
    "InlineCode",
    "ReferenceFormat",
    "ReferenceGroup",
    "Strikethrough",
    "Text",
    "Todo",
    "_BlockReference",
    "badge",
    "bold",
    "coerce_inlines",
    "cite",
    "comment",
    "footnote",
    "highlight",
    "italic",
    "keyboard",
    "link",
    "line_break",
    "margin_note",
    "math",
    "prescript",
    "Ref",
    "ref",
    "reference",
    "ref_range",
    "refs",
    "page_ref",
    "paren_ref",
    "status",
    "inline_code",
    "strikethrough",
    "styled",
    "subscript",
    "superscript",
    "tag",
    "text_color",
    "todo",
    "url",
]
