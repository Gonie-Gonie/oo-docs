"""Common structural and block-level document components.

Attributes:
    CodeLanguagePosition: Type alias for code block language-label positions.
    MIN_SECTION_LEVEL: Lowest supported heading level.
    MAX_SECTION_LEVEL: Highest supported heading level.
    DEFAULT_COUNTABLE_COUNTER: Default counter key for generated countable
        blocks.
    THEOREM_COUNTER: Shared counter key for theorem-like generated blocks.
    Definition: Generated countable block class for definitions.
    Lemma: Generated countable block class for lemmas.
    Proposition: Generated countable block class for propositions.
    Theorem: Generated countable block class for theorems.
    Corollary: Generated countable block class for corollaries.
    Proof: Generated unnumbered block class for proofs.
    Example: Generated countable block class for examples.
    Remark: Generated countable block class for remarks.
    Assumption: Generated countable block class for assumptions.
    Axiom: Generated countable block class for axioms.
    Claim: Generated countable block class for claims.
    Conjecture: Generated countable block class for conjectures.
    Algorithm: Countable algorithm block with input/output clauses and
        prose or code-style pseudocode.
    Appendix: Container for document appendices with alphabetic chapter
        numbering.
    CellInput: Type alias for values accepted by table cells.
"""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass, replace
from pathlib import Path
import re
from typing import TYPE_CHECKING, Iterable, Literal, Sequence

from oodocs.components.base import Block, BlockInput, coerce_blocks
from oodocs.components.equations import equation_plain_text
from oodocs.components.inline import InlineInput, Text, coerce_inlines
from oodocs.core import (
    PathLike,
    length_to_inches,
    normalize_color,
    normalize_length_unit,
    normalize_text_alignment,
)
from oodocs.styles import (
    BorderStyle,
    BoxStyle,
    CounterStyle,
    HeadingStyle,
    ListStyle,
    Padding,
    ParagraphStyle,
    RunInTitleStyle,
    TextStyle,
    box_style_with_overrides,
    list_style_with_overrides,
    paragraph_style_with_overrides,
)

if TYPE_CHECKING:
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext


CodeLanguagePosition = Literal["top-left", "top-right", "bottom-left", "bottom-right"]
AlgorithmBodyStyle = Literal["prose", "code"]
MIN_SECTION_LEVEL = 1
MAX_SECTION_LEVEL = 6
DEFAULT_COUNTABLE_COUNTER = "countable"
THEOREM_COUNTER = "theorem"
ALGORITHM_COUNTER = "algorithm"


@dataclass(slots=True, init=False)
class Paragraph(Block):
    """A paragraph built from inline fragments.

    Args:
        *content: Inline fragments or strings to include in the paragraph.
        title: Optional run-in paragraph title rendered before ``content``.
        title_style: Optional title style override for this paragraph.
        style: Base paragraph style.
        text_alignment: Optional text alignment override.
        space_before: Optional spacing before the paragraph.
        space_after: Optional spacing after the paragraph.
        leading: Optional line spacing.
        left_indent: Optional left indent.
        right_indent: Optional right indent.
        first_line_indent: Optional first-line indent.
        keep_together: Whether renderers should keep the paragraph on one page.
        keep_with_next: Whether renderers should keep this paragraph with the
            following block.
        page_break_before: Whether renderers should start a new page before the
            paragraph.
        widow_control: Whether renderers should avoid widowed lines.
        unit: Unit for length overrides.

    Examples:
        ```python
        from oodocs import Document, Paragraph, RunInTitleStyle, TextStyle, bold, link

        paragraph = Paragraph(
            "Read the ",
            link("release notes", "https://example.com/releases"),
            " before approving ",
            bold("production"),
            ".",
            title="Action",
            title_style=RunInTitleStyle(TextStyle(bold=True), separator=": "),
        )
        document = Document("Approval Notes", paragraph)
        ```
    """

    content: list[Text]
    title: list[Text] | None
    title_style: RunInTitleStyle | None
    style: ParagraphStyle | str

    def __init__(
        self,
        *content: InlineInput,
        title: InlineInput | None = None,
        title_style: RunInTitleStyle | None = None,
        style: ParagraphStyle | str | None = None,
        text_alignment: str | None = None,
        space_before: float | None = None,
        space_after: float | None = None,
        leading: float | None = None,
        left_indent: float | None = None,
        right_indent: float | None = None,
        first_line_indent: float | None = None,
        keep_together: bool | None = None,
        keep_with_next: bool | None = None,
        page_break_before: bool | None = None,
        widow_control: bool | None = None,
        unit: str | None = None,
    ) -> None:
        self.content = coerce_inlines(content)
        self.title = coerce_inlines((title,)) if title is not None else None
        self.title_style = title_style
        self.style = paragraph_style_with_overrides(
            style,
            text_alignment=text_alignment,
            space_before=space_before,
            space_after=space_after,
            leading=leading,
            left_indent=left_indent,
            right_indent=right_indent,
            first_line_indent=first_line_indent,
            keep_together=keep_together,
            keep_with_next=keep_with_next,
            page_break_before=page_break_before,
            widow_control=widow_control,
            unit=unit,
        )

    def plain_text(self) -> str:
        """Return the paragraph content without styling metadata.

        Returns:
            Concatenated plain text for all inline fragments.
        """

        if self.title is not None:
            title_text = "".join(fragment.plain_text() for fragment in self.title)
            separator = (self.title_style or RunInTitleStyle()).separator
            return title_text + separator + "".join(fragment.plain_text() for fragment in self.content)
        return "".join(fragment.plain_text() for fragment in self.content)

    def render_content(self, title_style: RunInTitleStyle) -> list[Text]:
        """Return inline fragments with the effective run-in title prepended.

        Args:
            title_style: Effective title style for this paragraph.

        Returns:
            Paragraph title fragments, separator, and content fragments.
        """

        if self.title is None:
            return self.content
        titled: list[Text] = [
            _inline_with_style(
                fragment,
                title_style.text_style.merged(fragment.style),
            )
            for fragment in self.title
        ]
        if title_style.separator:
            titled.append(Text(title_style.separator))
        return [*titled, *self.content]

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this paragraph into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_paragraph(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this paragraph into PDF flowables.

        Args:
            renderer: PDF renderer instance.
            context: Shared PDF render context.

        Returns:
            ReportLab flowables for this paragraph.
        """

        return renderer.render_paragraph(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this paragraph into HTML markup.

        Args:
            renderer: HTML renderer instance.
            context: Shared HTML render context.

        Returns:
            HTML markup for this paragraph.
        """

        return renderer.render_paragraph(self, context)


def _inline_with_style(fragment: Text, style: TextStyle) -> Text:
    cloned = copy(fragment)
    cloned.style = style
    return cloned


ListInput = Paragraph | InlineInput


def coerce_list_item(value: ListInput) -> Paragraph:
    """Normalize a list item into a paragraph.

    Args:
        value: Existing paragraph or inline paragraph content.

    Returns:
        A paragraph suitable for use as a list item.

    Examples:
        ```python
        item = coerce_list_item("First task")
        assert item.plain_text() == "First task"
        ```
    """

    if isinstance(value, Paragraph):
        return value
    return Paragraph(value)


@dataclass(slots=True, init=False)
class ListBlock(Block):
    """Shared implementation for bullet and ordered lists.

    Args:
        *items: Paragraphs or inline values used as list items.
        ordered: Whether the list should use ordered markers.
        style: Base list style.
        marker: Optional marker counter style override.
        indent: Optional list indent.
        marker_gap: Optional gap between marker and item text.
        item_children: Optional nested lists for each list item.

    Raises:
        ValueError: If ``item_children`` does not match the number of items.
    """

    items: list[Paragraph]
    item_children: list[list["ListBlock"]]
    ordered: bool
    style: ListStyle | str | None

    def __init__(
        self,
        *items: ListInput,
        ordered: bool = False,
        style: ListStyle | str | None = None,
        marker: CounterStyle | None = None,
        indent: float | None = None,
        marker_gap: float | None = None,
        item_children: Sequence[Sequence["ListBlock"]] | None = None,
    ) -> None:
        self.items = [coerce_list_item(item) for item in items if item is not None]
        if item_children is None:
            self.item_children = [[] for _ in self.items]
        else:
            self.item_children = [list(children) for children in item_children]
            if len(self.item_children) != len(self.items):
                raise ValueError("item_children must match the number of list items")
        self.ordered = ordered
        self.style = list_style_with_overrides(
            style,
            ordered=ordered,
            marker=marker,
            indent=indent,
            marker_gap=marker_gap,
        )

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this list into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_list(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this list into PDF flowables.

        Args:
            renderer: PDF renderer instance.
            context: Shared PDF render context.

        Returns:
            ReportLab flowables for this list.
        """

        return renderer.render_list(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this list into HTML markup.

        Args:
            renderer: HTML renderer instance.
            context: Shared HTML render context.

        Returns:
            HTML markup for this list.
        """

        return renderer.render_list(self, context)


class BulletList(ListBlock):
    """An unordered list of paragraph items.

    Args:
        *items: Paragraphs or inline values used as list items.
        style: Base list style.
        marker: Optional marker counter style override.
        indent: Optional list indent.
        marker_gap: Optional gap between marker and item text.
        item_children: Optional nested lists for each list item.

    Examples:
        ```python
        from oodocs import BulletList, Document, Section

        tasks = BulletList("Collect metrics", "Review failures", "Publish report")
        document = Document("Release Checklist", Section("Tasks", tasks))
        ```
    """

    def __init__(
        self,
        *items: ListInput,
        style: ListStyle | str | None = None,
        marker: CounterStyle | None = None,
        indent: float | None = None,
        marker_gap: float | None = None,
        item_children: Sequence[Sequence[ListBlock]] | None = None,
    ) -> None:
        super().__init__(
            *items,
            ordered=False,
            style=style,
            marker=marker,
            indent=indent,
            marker_gap=marker_gap,
            item_children=item_children,
        )


class NumberedList(ListBlock):
    """An ordered list of paragraph items.

    Args:
        *items: Paragraphs or inline values used as list items.
        style: Base list style.
        marker: Optional marker counter style override.
        indent: Optional list indent.
        marker_gap: Optional gap between marker and item text.
        item_children: Optional nested lists for each list item.

    Examples:
        ```python
        from oodocs import Document, NumberedList, Section

        steps = NumberedList("Install", "Configure", "Run", start=1)
        document = Document("Runbook", Section("Procedure", steps))
        ```
    """

    def __init__(
        self,
        *items: ListInput,
        style: ListStyle | str | None = None,
        marker: CounterStyle | None = None,
        indent: float | None = None,
        marker_gap: float | None = None,
        item_children: Sequence[Sequence[ListBlock]] | None = None,
    ) -> None:
        super().__init__(
            *items,
            ordered=True,
            style=style,
            marker=marker,
            indent=indent,
            marker_gap=marker_gap,
            item_children=item_children,
        )


@dataclass(slots=True, init=False)
class CodeBlock(Block):
    """A preformatted code snippet.

    Args:
        code: Source code text.
        language: Optional lexer or language label.
        show_language: Whether to render the language label.
        language_position: Where to place the language label.
        caption: Optional caption rendered with the code block number.
        identifier: Optional stable identifier for downstream renderers or tools.
        line_numbers: Whether to render source line numbers.
        highlight_lines: One-based source line numbers to highlight.
        style: Base paragraph style for the code block.
        text_alignment: Optional text alignment override.
        space_before: Optional spacing before the block.
        space_after: Optional spacing after the block.
        leading: Optional line spacing.
        left_indent: Optional left indent.
        right_indent: Optional right indent.
        first_line_indent: Optional first-line indent.
        keep_together: Whether renderers should keep the block on one page.
        keep_with_next: Whether renderers should keep this block with the next.
        page_break_before: Whether renderers should start a new page first.
        widow_control: Whether renderers should avoid widowed lines.
        unit: Unit for length overrides.

    Raises:
        ValueError: If ``language_position`` is not supported.

    Examples:
        ```python
        from oodocs import CodeBlock, Document, Section

        snippet = CodeBlock(
            "print('hello')",
            language="python",
            caption="Minimal example",
            line_numbers=True,
            highlight_lines={1},
        )
        document = Document("Developer Notes", Section("Example", snippet))
        ```
    """

    code: str
    language: str | None
    show_language: bool
    language_position: CodeLanguagePosition
    caption: Paragraph | None
    identifier: str | None
    line_numbers: bool
    highlight_lines: frozenset[int]
    style: ParagraphStyle | str

    def __init__(
        self,
        code: str,
        language: str | None = None,
        *,
        show_language: bool = True,
        language_position: CodeLanguagePosition = "top-right",
        caption: CellInput | None = None,
        identifier: str | None = None,
        line_numbers: bool = False,
        highlight_lines: Iterable[int] | None = None,
        style: ParagraphStyle | str | None = None,
        text_alignment: str | None = None,
        space_before: float | None = None,
        space_after: float | None = None,
        leading: float | None = None,
        left_indent: float | None = None,
        right_indent: float | None = None,
        first_line_indent: float | None = None,
        keep_together: bool | None = None,
        keep_with_next: bool | None = None,
        page_break_before: bool | None = None,
        widow_control: bool | None = None,
        unit: str | None = None,
    ) -> None:
        if language_position not in {"top-left", "top-right", "bottom-left", "bottom-right"}:
            raise ValueError("CodeBlock language_position must be top-left, top-right, bottom-left, or bottom-right")
        self.code = code
        self.language = language
        self.show_language = show_language
        self.language_position = language_position
        self.caption = coerce_cell(caption) if caption is not None else None
        self.identifier = identifier
        self.line_numbers = bool(line_numbers)
        self.highlight_lines = _normalize_code_highlight_lines(highlight_lines)
        self.style = paragraph_style_with_overrides(
            style or ParagraphStyle(text_alignment="left", space_after=12.0),
            text_alignment=text_alignment,
            space_before=space_before,
            space_after=space_after,
            leading=leading,
            left_indent=left_indent,
            right_indent=right_indent,
            first_line_indent=first_line_indent,
            keep_together=keep_together,
            keep_with_next=keep_with_next,
            page_break_before=page_break_before,
            widow_control=widow_control,
            unit=unit,
        )

    @classmethod
    def from_file(
        cls,
        path: PathLike,
        language: str | None = None,
        *,
        encoding: str = "utf-8",
        **kwargs: object,
    ) -> CodeBlock:
        """Create a code block from a source file.

        Args:
            path: File path to read.
            language: Optional language override. Defaults to the file suffix.
            encoding: Text encoding used to read the file.
            **kwargs: Additional ``CodeBlock`` constructor options.

        Returns:
            Code block containing the file contents.

        Examples:
            ```python
            block = CodeBlock.from_file("example.py", caption="Full source")
            ```
        """

        source_path = Path(path)
        inferred_language = source_path.suffix.lstrip(".") or None
        return cls(
            source_path.read_text(encoding=encoding),
            language=language or inferred_language,
            **kwargs,
        )

    def normalized_lines(self) -> list[str]:
        """Return source lines with normalized newlines.

        Returns:
            Source lines split on ``\\n`` after normalizing CRLF and CR.
        """

        return self.code.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    def line_number_width(self) -> int:
        """Return the display width required for line-number prefixes.

        Returns:
            Number of digits required to display the largest source line number.
        """

        return max(1, len(str(len(self.normalized_lines()))))

    def line_prefix(self, line_number: int) -> str:
        """Return the formatted line-number prefix for a source line.

        Args:
            line_number: One-based line number.

        Returns:
            Prefix text, or an empty string when line numbers are disabled.
        """

        if not self.line_numbers:
            return ""
        return f"{line_number:>{self.line_number_width()}} | "

    def display_line(self, line_number: int, text: str) -> str:
        """Return one rendered source line including any line-number prefix.

        Args:
            line_number: One-based line number.
            text: Source text for the line.

        Returns:
            Display line text.
        """

        return f"{self.line_prefix(line_number)}{text}"

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this code block into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_code_block(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this code block into PDF flowables.

        Returns:
            ReportLab flowables for this code block.
        """

        return renderer.render_code_block(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this code block into HTML markup.

        Returns:
            HTML markup for this code block.
        """

        return renderer.render_code_block(self, context)


def _normalize_code_highlight_lines(lines: Iterable[int] | None) -> frozenset[int]:
    if lines is None:
        return frozenset()
    normalized = frozenset(int(line) for line in lines)
    if any(line < 1 for line in normalized):
        raise ValueError("CodeBlock highlight_lines values must be >= 1")
    return normalized


@dataclass(slots=True, init=False)
class Equation(Block):
    """A centered block equation written in lightweight LaTeX syntax.

    Args:
        expression: LaTeX-like equation source.
        style: Base paragraph style.
        text_alignment: Optional text alignment override.
        space_before: Optional spacing before the equation.
        space_after: Optional spacing after the equation.
        leading: Optional line spacing.
        left_indent: Optional left indent.
        right_indent: Optional right indent.
        first_line_indent: Optional first-line indent.
        keep_together: Whether renderers should keep the equation on one page.
        keep_with_next: Whether renderers should keep this equation with the
            following block.
        page_break_before: Whether renderers should start a new page first.
        widow_control: Whether renderers should avoid widowed lines.
        unit: Unit for length overrides.

    Examples:
        ```python
        from oodocs import Document, Equation, Section

        energy = Equation(r"E = mc^2")
        document = Document("Physics Note", Section("Energy", energy))
        ```
    """

    expression: str
    style: ParagraphStyle | str

    def __init__(
        self,
        expression: str,
        *,
        style: ParagraphStyle | str | None = None,
        text_alignment: str | None = None,
        space_before: float | None = None,
        space_after: float | None = None,
        leading: float | None = None,
        left_indent: float | None = None,
        right_indent: float | None = None,
        first_line_indent: float | None = None,
        keep_together: bool | None = None,
        keep_with_next: bool | None = None,
        page_break_before: bool | None = None,
        widow_control: bool | None = None,
        unit: str | None = None,
    ) -> None:
        self.expression = expression
        self.style = paragraph_style_with_overrides(
            style or ParagraphStyle(text_alignment="center", space_after=12.0),
            text_alignment=text_alignment,
            space_before=space_before,
            space_after=space_after,
            leading=leading,
            left_indent=left_indent,
            right_indent=right_indent,
            first_line_indent=first_line_indent,
            keep_together=keep_together,
            keep_with_next=keep_with_next,
            page_break_before=page_break_before,
            widow_control=widow_control,
            unit=unit,
        )

    def plain_text(self) -> str:
        """Return a readable plain-text equation approximation.

        Returns:
            Plain-text approximation of the equation source.
        """

        return equation_plain_text(self.expression)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this equation into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_equation(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this equation into PDF flowables.

        Returns:
            ReportLab flowables for this equation.
        """

        return renderer.render_equation(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this equation into HTML markup.

        Returns:
            HTML markup for this equation.
        """

        return renderer.render_equation(self, context)


@dataclass(slots=True)
class PageBreak(Block):
    """Explicit page break in the document flow.

    Attributes:
        None: The block is a marker and carries no additional configuration.

    Examples:
        ```python
        from oodocs import Document, PageBreak, Paragraph

        document = Document("Report", Paragraph("Cover"), PageBreak(), Paragraph("Body"))
        ```
    """

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this page break into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_page_break(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this page break into PDF flowables.

        Returns:
            ReportLab flowables for this page break.
        """

        return renderer.render_page_break(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this page break into HTML markup.

        Returns:
            HTML markup for this page break.
        """

        return renderer.render_page_break(self, context)


@dataclass(slots=True, init=False)
class VerticalSpace(Block):
    """A vertical spacer in the document flow.

    Args:
        height: Spacer height in ``unit``.
        unit: Length unit for ``height``.

    Raises:
        ValueError: If ``height`` is negative.

    Examples:
        ```python
        from oodocs import Document, Paragraph, VerticalSpace

        document = Document(
            "Agenda",
            Paragraph("Morning session"),
            VerticalSpace(18, unit="pt"),
            Paragraph("Afternoon session"),
        )
        ```
    """

    height: float
    unit: str

    def __init__(self, height: float = 12.0, *, unit: str = "pt") -> None:
        if height < 0:
            raise ValueError("VerticalSpace height must be >= 0")
        self.height = float(height)
        self.unit = normalize_length_unit(unit)

    def height_in_points(self) -> float:
        """Return the spacer height in typographic points.

        Returns:
            The spacer height converted to points.
        """

        return length_to_inches(self.height, self.unit) * 72.0

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this spacer into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_vertical_space(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this spacer into PDF flowables.

        Returns:
            ReportLab flowables for this spacer.
        """

        return renderer.render_vertical_space(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this spacer into HTML markup.

        Returns:
            HTML markup for this spacer.
        """

        return renderer.render_vertical_space(self, context)


@dataclass(slots=True, init=False)
class Divider(Block):
    """A horizontal divider similar to Notion's separator block.

    Args:
        color: Divider line color as a hex string.
        thickness: Divider thickness.
        space_before: Spacing before the divider.
        space_after: Spacing after the divider.
        width: Optional divider width. Defaults to full available width.
        alignment: Divider alignment when ``width`` is set.
        unit: Unit for thickness, spacing, and width values.

    Raises:
        ValueError: If dimensions or alignment are invalid.

    Examples:
        ```python
        from oodocs import Divider, Document, Paragraph

        document = Document(
            "Summary",
            Paragraph("Findings"),
            Divider(color="B7C2D0", width=3.5, unit="in"),
            Paragraph("Appendix"),
        )
        ```
    """

    color: str
    thickness: float
    space_before: float
    space_after: float
    width: float | None
    alignment: str
    unit: str | None

    def __init__(
        self,
        *,
        color: str = "DADDE3",
        thickness: float = 0.75,
        space_before: float = 8.0,
        space_after: float = 8.0,
        width: float | None = None,
        alignment: str = "center",
        unit: str | None = None,
    ) -> None:
        if thickness <= 0:
            raise ValueError("Divider thickness must be > 0")
        if space_before < 0:
            raise ValueError("Divider space_before must be >= 0")
        if space_after < 0:
            raise ValueError("Divider space_after must be >= 0")
        if width is not None and width < 0:
            raise ValueError("Divider width must be >= 0")
        normalized_alignment = normalize_text_alignment(alignment)
        if normalized_alignment == "justify":
            raise ValueError("Divider alignment must be left, center, or right")
        self.color = normalize_color(color) or "DADDE3"
        self.thickness = float(thickness)
        self.space_before = float(space_before)
        self.space_after = float(space_after)
        self.width = float(width) if width is not None else None
        self.alignment = normalized_alignment
        self.unit = normalize_length_unit(unit) if unit is not None else None

    def width_in_inches(self, default_unit: str) -> float | None:
        """Return the optional rule width in inches.

        Args:
            default_unit: Unit to use when the divider has no explicit unit.

        Returns:
            Divider width in inches, or ``None`` for full available width.
        """

        if self.width is None:
            return None
        return length_to_inches(self.width, self.unit or default_unit)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this divider into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_divider(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this divider into PDF flowables.

        Returns:
            ReportLab flowables for this divider.
        """

        return renderer.render_divider(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this divider into HTML markup.

        Returns:
            HTML markup for this divider.
        """

        return renderer.render_divider(self, context)


@dataclass(slots=True, init=False)
class ColumnSpan(Block):
    """Full-width content inside a ``MultiColumn`` block.

    Args:
        *children: Block content that should span every column.

    Examples:
        ```python
        from oodocs import ColumnSpan, Document, MultiColumn, Paragraph

        layout = MultiColumn(
            Paragraph("Left column."),
            ColumnSpan(Paragraph("This paragraph spans all columns.")),
            Paragraph("Right column."),
            columns=2,
        )
        document = Document("Layout", layout)
        ```
    """

    children: list[Block]

    def __init__(self, *children: BlockInput) -> None:
        self.children = coerce_blocks(children)

    def add(self, *children: BlockInput) -> ColumnSpan:
        """Append full-width children.

        Args:
            *children: Block content to append.

        Returns:
            This column span, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> ColumnSpan:
        """Append an iterable of full-width children.

        Args:
            children: Block content to append.

        Returns:
            This column span, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this column span into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_column_span(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this column span into PDF flowables.

        Returns:
            ReportLab flowables for this column span.
        """

        return renderer.render_column_span(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this column span into HTML markup.

        Returns:
            HTML markup for this column span.
        """

        return renderer.render_column_span(self, context)


@dataclass(slots=True, init=False)
class MultiColumn(Block):
    """A document flow container rendered across multiple columns.

    Args:
        *children: Block content for the column flow.
        columns: Number of columns.
        column_gap: Gap between columns in ``unit``.
        unit: Unit for ``column_gap``. Defaults to the document unit.
        span_wide_media: Whether wide tables and figures should span all
            columns automatically.

    Raises:
        ValueError: If ``columns`` is less than one or ``column_gap`` is
            negative.

    Examples:
        ```python
        from oodocs import Document, MultiColumn, Paragraph

        layout = MultiColumn(
            Paragraph("Left flow."),
            Paragraph("Right flow."),
            columns=2,
        )
        document = Document("Newsletter", layout)
        ```
    """

    children: list[Block]
    columns: int
    column_gap: float
    unit: str | None
    span_wide_media: bool

    def __init__(
        self,
        *children: BlockInput,
        columns: int = 2,
        column_gap: float = 0.25,
        unit: str | None = None,
        span_wide_media: bool = True,
    ) -> None:
        if columns < 1:
            raise ValueError("MultiColumn columns must be >= 1")
        if column_gap < 0:
            raise ValueError("MultiColumn column_gap must be >= 0")
        self.children = coerce_blocks(children)
        self.columns = columns
        self.column_gap = float(column_gap)
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.span_wide_media = bool(span_wide_media)

    def add(self, *children: BlockInput) -> MultiColumn:
        """Append children using constructor-compatible coercion.

        Args:
            *children: Block content to append.

        Returns:
            This multi-column block, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> MultiColumn:
        """Append an iterable of children.

        Args:
            children: Block content to append.

        Returns:
            This multi-column block, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def column_gap_in_inches(self, default_unit: str) -> float:
        """Return the gap between columns in inches.

        Args:
            default_unit: Unit to use when this block has no explicit unit.

        Returns:
            Column gap converted to inches.
        """

        return length_to_inches(self.column_gap, self.unit or default_unit)

    def column_width_in_inches(self, available_width: float, default_unit: str) -> float:
        """Return the width available to a single column in inches.

        Args:
            available_width: Total available width in inches.
            default_unit: Unit to use when this block has no explicit unit.

        Returns:
            Width available to one column in inches.
        """

        if self.columns <= 1:
            return max(available_width, 0)
        total_gap = self.column_gap_in_inches(default_unit) * (self.columns - 1)
        return max((available_width - total_gap) / self.columns, 0)

    def _child_spans_columns(
        self,
        child: Block,
        *,
        available_width: float,
        default_unit: str,
    ) -> bool:
        if isinstance(child, (ColumnSpan, PageBreak)):
            return True
        if not self.span_wide_media or self.columns <= 1:
            return False

        from oodocs.components.media import Figure, SubFigureGroup, SubTableGroup, Table

        column_width = self.column_width_in_inches(available_width, default_unit)
        if isinstance(child, Figure):
            figure_width = child.width_in_inches(default_unit)
            return figure_width is None or figure_width > column_width
        if isinstance(child, Table):
            column_widths = child._column_widths_in_inches(
                default_unit,
                available_width=column_width,
            )
            return column_widths is None or sum(column_widths) > column_width
        if isinstance(child, SubFigureGroup):
            row = child.subfigures[: child.columns]
            if not row:
                return False
            widths = [subfigure.width_in_inches(default_unit) for subfigure in row]
            if any(width is None for width in widths):
                return True
            # Only the first visual row determines whether the group can fit in
            # a column, matching how renderers lay out subfigure grids.
            group_gap = length_to_inches(child.column_gap, child.unit or default_unit)
            group_width = sum(width for width in widths if width is not None)
            group_width += group_gap * max(len(row) - 1, 0)
            return group_width > column_width
        if isinstance(child, SubTableGroup):
            row = child.subtables[: child.columns]
            if not row:
                return False
            group_gap = length_to_inches(child.column_gap, child.unit or default_unit)
            available_child_width = max(
                (column_width - group_gap * max(child.columns - 1, 0)) / child.columns,
                0,
            )
            widths = [
                subtable.width_in_inches(
                    default_unit,
                    available_width=available_child_width,
                )
                for subtable in row
            ]
            if any(width is None for width in widths):
                return True
            group_width = sum(width for width in widths if width is not None)
            group_width += group_gap * max(len(row) - 1, 0)
            return group_width > column_width
        return False

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this multi-column block into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_multi_column(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this multi-column block into PDF flowables.

        Returns:
            ReportLab flowables for this multi-column block.
        """

        return renderer.render_multi_column(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this multi-column block into HTML markup.

        Returns:
            HTML markup for this multi-column block.
        """

        return renderer.render_multi_column(self, context)


@dataclass(slots=True, init=False)
class Part(Block):
    """Top-level document division rendered on its own separator page.

    Args:
        title: Part title inline content.
        *children: Child block content.
        numbered: Whether the part should be numbered.
        toc: Whether the part should appear in generated tables of contents.
            Defaults to ``numbered``.

    Attributes:
        level: Fixed heading level used for part separator pages.

    Examples:
        ```python
        from oodocs import Chapter, Document, Part

        part = Part("Methods", Chapter("Data Collection"))
        document = Document("Study Protocol", part)
        ```
    """

    title: list[Text]
    children: list[Block]
    numbered: bool
    toc: bool
    level: int

    def __init__(
        self,
        title: InlineInput,
        *children: BlockInput,
        numbered: bool = True,
        toc: bool | None = None,
    ) -> None:
        self.title = coerce_inlines((title,))
        self.children = coerce_blocks(children)
        self.numbered = numbered
        self.toc = numbered if toc is None else bool(toc)
        self.level = 0

    def add(self, *children: BlockInput) -> Part:
        """Append child blocks.

        Args:
            *children: Block content to append.

        Returns:
            This part, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> Part:
        """Append an iterable of child blocks.

        Args:
            children: Block content to append.

        Returns:
            This part, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def plain_title(self) -> str:
        """Return the title without styling metadata.

        Returns:
            Concatenated plain text for the title fragments.
        """

        return "".join(fragment.plain_text() for fragment in self.title)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this part into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_part(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this part into PDF flowables.

        Returns:
            ReportLab flowables for this part.
        """

        return renderer.render_part(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this part into HTML markup.

        Returns:
            HTML markup for this part.
        """

        return renderer.render_part(self, context)


@dataclass(slots=True, init=False)
class Appendix(Part):
    """Appendix container that switches child heading numbers to letters.

    Args:
        *children: Appendix block content. Level-1 headings inside the appendix
            are numbered ``A``, ``B``, ``C``, and nested headings become
            ``A.1``, ``A.1.1``, and so on.
        title: Appendix separator title.
        toc: Whether the appendix separator should appear in generated tables
            of contents.

    Examples:
        ```python
        from oodocs import Appendix, Chapter, Document, Paragraph

        appendix = Appendix(
            Chapter("Input Data Schema", Paragraph("Field definitions.")),
            Chapter("Validation Cases", Paragraph("Reference checks.")),
        )
        document = Document("Report", appendix)
        ```
    """

    def __init__(
        self,
        *children: BlockInput,
        title: InlineInput = "Appendices",
        toc: bool = True,
    ) -> None:
        Part.__init__(self, title, *children, numbered=False, toc=toc)

    def add(self, *children: BlockInput) -> Appendix:
        """Append child blocks.

        Args:
            *children: Appendix block content to append.

        Returns:
            This appendix, enabling fluent construction.
        """

        Part.add(self, *children)
        return self

    def extend(self, children: Iterable[BlockInput]) -> Appendix:
        """Append an iterable of child blocks.

        Args:
            children: Appendix block content to append.

        Returns:
            This appendix, enabling fluent construction.
        """

        Part.extend(self, children)
        return self


@dataclass(slots=True, init=False)
class Box(Block):
    """Bordered container for grouped block content.

    Args:
        *children: Child block content.
        title: Optional box title.
        style: Base box style.
        border: Optional border style override.
        background_color: Optional body background color override.
        title_background_color: Optional title band background override.
        title_text_color: Optional title text color override.
        padding: Optional padding override.
        space_after: Optional spacing after the box.
        width: Optional preferred box width.
        unit: Unit for length overrides.
        block_alignment: Optional block placement alignment.

    Examples:
        Place a styled note box inside a document:

        ```python
        from oodocs import BorderStyle, Box, Document, Padding, Paragraph

        note = Box(
            Paragraph("Review this before release."),
            title="Note",
            border=BorderStyle.solid("CBD5E1", width=0.75),
            padding=Padding.symmetric(vertical=8, horizontal=12),
        )
        document = Document("Release Notes", note)
        ```
    """

    children: list[Block]
    title: list[Text] | None
    style: BoxStyle | str

    def __init__(
        self,
        *children: BlockInput,
        title: InlineInput | None = None,
        style: BoxStyle | str | None = None,
        border: BorderStyle | None = None,
        background_color: str | None = None,
        title_background_color: str | None = None,
        title_text_color: str | None = None,
        padding: Padding | None = None,
        space_after: float | None = None,
        width: float | None = None,
        unit: str | None = None,
        block_alignment: str | None = None,
    ) -> None:
        self.children = coerce_blocks(children)
        self.title = coerce_inlines((title,)) if title is not None else None
        self.style = box_style_with_overrides(
            style,
            border=border,
            background_color=background_color,
            title_background_color=title_background_color,
            title_text_color=title_text_color,
            padding=padding,
            space_after=space_after,
            width=width,
            unit=unit,
            block_alignment=block_alignment,
        )

    def add(self, *children: BlockInput) -> Box:
        """Append boxed content.

        Args:
            *children: Block content to append.

        Returns:
            This box, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> Box:
        """Append an iterable of boxed content.

        Args:
            children: Block content to append.

        Returns:
            This box, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this box into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_box(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this box into PDF flowables.

        Returns:
            ReportLab flowables for this box.
        """

        return renderer.render_box(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this box into HTML markup.

        Returns:
            HTML markup for this box.
        """

        return renderer.render_box(self, context)


@dataclass(slots=True, init=False)
class CountableBlock(Block):
    """A theorem-like block with document-wide numbering.

    Args:
        kind: Visible block kind, such as ``"Theorem"``.
        *children: Child block content.
        title: Optional block title.
        numbered: Whether the block participates in numbering.
        counter: Counter namespace. Blocks with the same counter share a
            sequence.
        reference_label: Label prefix used by automatic inline references.
        label_suffix: Punctuation appended to heading labels.

    Raises:
        TypeError: If ``label_suffix`` is not a string.
        ValueError: If kind, counter, or reference label values are invalid.

    Examples:
        ```python
        from oodocs import CountableBlock, Document, Paragraph

        theorem = CountableBlock(
            "Theorem",
            Paragraph("Every finite tree has at least one leaf."),
            title="Leaf existence",
            counter="theorem",
        )
        document = Document("Proof Notes", theorem)
        ```
    """

    kind: str
    children: list[Block]
    title: list[Text] | None
    numbered: bool
    counter: str | None
    reference_label: str
    label_suffix: str

    def __init__(
        self,
        kind: str,
        *children: BlockInput,
        title: InlineInput | None = None,
        numbered: bool = True,
        counter: str | None = DEFAULT_COUNTABLE_COUNTER,
        reference_label: str | None = None,
        label_suffix: str = ".",
    ) -> None:
        normalized_kind = str(kind).strip()
        if not normalized_kind:
            raise ValueError("CountableBlock kind must not be empty")
        if not isinstance(label_suffix, str):
            raise TypeError("CountableBlock label_suffix must be a string")
        normalized_counter = None if counter is None else str(counter).strip()
        if numbered and not normalized_counter:
            raise ValueError("Numbered CountableBlock objects require a non-empty counter")
        normalized_reference_label = (
            normalized_kind
            if reference_label is None
            else str(reference_label).strip()
        )
        if not normalized_reference_label:
            raise ValueError("CountableBlock reference_label must not be empty")

        self.kind = normalized_kind
        self.children = coerce_blocks(children)
        self.title = coerce_inlines((title,)) if title is not None else None
        self.numbered = bool(numbered)
        self.counter = normalized_counter if self.numbered else None
        self.reference_label = normalized_reference_label
        self.label_suffix = label_suffix

    def add(self, *children: BlockInput) -> CountableBlock:
        """Append child blocks.

        Args:
            *children: Block content to append.

        Returns:
            This countable block, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> CountableBlock:
        """Append an iterable of child blocks.

        Args:
            children: Block content to append.

        Returns:
            This countable block, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def heading_label(self, number: int | None) -> str:
        """Return the visible heading label, including punctuation.

        Args:
            number: Assigned number, or ``None`` for unnumbered display.

        Returns:
            Display label for the block heading.
        """

        if self.numbered and number is not None:
            return f"{self.kind} {number}{self.label_suffix}"
        return f"{self.kind}{self.label_suffix}"

    def reference_text(self, number: int) -> str:
        """Return the default inline reference label.

        Args:
            number: Assigned block number.

        Returns:
            Inline reference text for this block.
        """

        return f"{self.reference_label} {number}"

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this countable block into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_countable_block(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this countable block into PDF flowables.

        Returns:
            ReportLab flowables for this countable block.
        """

        return renderer.render_countable_block(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this countable block into HTML markup.

        Returns:
            HTML markup for this countable block.
        """

        return renderer.render_countable_block(self, context)


@dataclass(slots=True, init=False)
class Algorithm(CountableBlock):
    """A numbered algorithm block with optional pseudocode structure.

    Args:
        name: Algorithm name. Used as the heading title when ``caption`` is
            omitted.
        *children: Additional child blocks appended after generated clauses and
            steps.
        inputs: Optional input clauses.
        outputs: Optional output clauses.
        steps: Optional prose or pseudocode steps.
        code: Optional code-style pseudocode body. Mutually exclusive with
            ``steps``.
        language: Optional Pygments lexer for ``code`` or code-style steps.
        caption: Optional heading caption shown after ``Algorithm N.``.
        body_style: ``"prose"`` renders steps as a list; ``"code"`` renders
            them as a code-style pseudocode block.
        line_numbers: Whether step lists or code-style pseudocode should show
            line numbers.
        numbered: Whether the algorithm participates in numbering.
        counter: Counter namespace for algorithm numbering.
        reference_label: Label prefix used by automatic inline references.

    Raises:
        ValueError: If ``body_style`` is unsupported or ``steps`` and ``code``
            are both provided.

    Examples:
        ```python
        from oodocs import Algorithm, Document, Paragraph

        algorithm = Algorithm(
            "Coverage aggregation",
            inputs=["test results", "coverage map"],
            outputs=["coverage summary"],
            steps=[
                "Load evidence records.",
                "Group records by feature.",
                "Compute pass/fail counts.",
            ],
            caption="Coverage aggregation algorithm.",
        )
        document = Document("Methods", Paragraph("See ", algorithm.reference(), "."), algorithm)
        ```
    """

    name: list[Text]
    inputs: tuple[InlineInput, ...]
    outputs: tuple[InlineInput, ...]
    steps: tuple[InlineInput, ...]
    code: str | None
    language: str | None
    body_style: AlgorithmBodyStyle
    line_numbers: bool

    def __init__(
        self,
        name: InlineInput,
        *children: BlockInput,
        inputs: InlineInput | Sequence[InlineInput] | None = None,
        outputs: InlineInput | Sequence[InlineInput] | None = None,
        steps: InlineInput | Sequence[InlineInput] | None = None,
        code: str | None = None,
        language: str | None = None,
        caption: InlineInput | None = None,
        body_style: AlgorithmBodyStyle = "prose",
        line_numbers: bool = True,
        numbered: bool = True,
        counter: str | None = ALGORITHM_COUNTER,
        reference_label: str | None = "Algorithm",
    ) -> None:
        if body_style not in {"prose", "code"}:
            raise ValueError("Algorithm body_style must be 'prose' or 'code'")
        if steps is not None and code is not None:
            raise ValueError("Algorithm steps and code are mutually exclusive")

        self.name = coerce_inlines((name,))
        self.inputs = _normalize_algorithm_items(inputs)
        self.outputs = _normalize_algorithm_items(outputs)
        self.steps = _normalize_algorithm_items(steps)
        self.code = code
        self.language = language
        self.body_style = body_style
        self.line_numbers = bool(line_numbers)

        generated_children = self._generated_children()
        CountableBlock.__init__(
            self,
            "Algorithm",
            *generated_children,
            *children,
            title=caption if caption is not None else name,
            numbered=numbered,
            counter=counter,
            reference_label=reference_label,
        )

    def _generated_children(self) -> list[Block]:
        children: list[Block] = []
        if self.inputs:
            children.append(_algorithm_clause("Input", self.inputs))
        if self.outputs:
            children.append(_algorithm_clause("Output", self.outputs))
        if self.code is not None:
            children.append(
                CodeBlock(
                    self.code,
                    language=self.language,
                    show_language=False,
                    line_numbers=self.line_numbers,
                )
            )
        elif self.steps:
            if self.body_style == "code":
                children.append(
                    CodeBlock(
                        "\n".join(_algorithm_step_text(step) for step in self.steps),
                        language=self.language or "text",
                        show_language=False,
                        line_numbers=self.line_numbers,
                    )
                )
            elif self.line_numbers:
                children.append(NumberedList(*self.steps))
            else:
                children.append(BulletList(*self.steps))
        return children

    @property
    def caption(self) -> list[Text] | None:
        """Return the algorithm heading caption.

        Returns:
            Caption fragments shown after the ``Algorithm N.`` label.
        """

        return self.title


def _normalize_algorithm_items(
    values: InlineInput | Sequence[InlineInput] | None,
) -> tuple[InlineInput, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        return (values,)
    if isinstance(values, Sequence):
        return tuple(values)
    return (values,)


def _algorithm_clause(label: str, values: Sequence[InlineInput]) -> Paragraph:
    content: list[InlineInput] = [Text(f"{label}: ", style=TextStyle(bold=True))]
    for index, value in enumerate(values):
        if index:
            content.append(Text(", "))
        content.extend(coerce_inlines((value,)))
    return Paragraph(*content, space_after=2)


def _algorithm_step_text(step: InlineInput) -> str:
    return coerce_cell(step).plain_text()


def create_countable_block_type(
    kind: str,
    *,
    counter: str | None = DEFAULT_COUNTABLE_COUNTER,
    numbered: bool = True,
    reference_label: str | None = None,
    label_suffix: str = ".",
) -> type[CountableBlock]:
    """Create a reusable theorem-like block class.

    Args:
        kind: Visible block kind for the generated class.
        counter: Default counter namespace for generated instances.
        numbered: Default numbering behavior.
        reference_label: Default automatic reference label prefix.
        label_suffix: Default punctuation appended to heading labels.

    Returns:
        A ``CountableBlock`` subclass preconfigured with the supplied defaults.

    Raises:
        ValueError: If ``kind`` is empty.

    Examples:
        ```python
        from oodocs import Paragraph, create_countable_block_type

        Requirement = create_countable_block_type("Requirement", counter="requirement")
        item = Requirement(Paragraph("The API must render to HTML."))
        ```
    """

    normalized_kind = str(kind).strip()
    if not normalized_kind:
        raise ValueError("create_countable_block_type kind must not be empty")

    class CustomCountableBlock(CountableBlock):
        def __init__(
            self,
            *children: BlockInput,
            title: InlineInput | None = None,
            numbered: bool = numbered,
            counter: str | None = counter,
            reference_label: str | None = reference_label,
            label_suffix: str = label_suffix,
        ) -> None:
            super().__init__(
                normalized_kind,
                *children,
                title=title,
                numbered=numbered,
                counter=counter,
                reference_label=reference_label,
                label_suffix=label_suffix,
            )

    CustomCountableBlock.__name__ = _countable_class_name(normalized_kind)
    CustomCountableBlock.__qualname__ = CustomCountableBlock.__name__
    CustomCountableBlock.__module__ = __name__
    CustomCountableBlock.__doc__ = f"A preconfigured countable block for {normalized_kind}."
    return CustomCountableBlock


def _countable_class_name(kind: str) -> str:
    pieces = re.findall(r"[A-Za-z0-9]+", kind)
    name = "".join(piece[:1].upper() + piece[1:] for piece in pieces)
    if not name or name[0].isdigit():
        return "CustomCountableBlock"
    return name


Definition = create_countable_block_type("Definition", counter=THEOREM_COUNTER)
Lemma = create_countable_block_type("Lemma", counter=THEOREM_COUNTER)
Proposition = create_countable_block_type("Proposition", counter=THEOREM_COUNTER)
Theorem = create_countable_block_type("Theorem", counter=THEOREM_COUNTER)
Corollary = create_countable_block_type("Corollary", counter=THEOREM_COUNTER)
Proof = create_countable_block_type("Proof", numbered=False, counter=None)
Example = create_countable_block_type("Example", counter=THEOREM_COUNTER)
Remark = create_countable_block_type("Remark", counter=THEOREM_COUNTER)
Assumption = create_countable_block_type("Assumption", counter=THEOREM_COUNTER)
Axiom = create_countable_block_type("Axiom", counter=THEOREM_COUNTER)
Claim = create_countable_block_type("Claim", counter=THEOREM_COUNTER)
Conjecture = create_countable_block_type("Conjecture", counter=THEOREM_COUNTER)


@dataclass(slots=True, init=False)
class Section(Block):
    """A titled section containing nested blocks.

    Args:
        title: Section title inline content.
        *children: Child block content.
        level: Heading level from 1 through 6.
        numbered: Whether the heading should be numbered.
        toc: Whether the section should appear in generated tables of contents.
            Defaults to ``numbered``.
        anchor: Optional stable heading anchor used by renderers for internal
            links.
        run_in_title_style: Optional run-in title style inherited by
            paragraphs in this section subtree.
        heading_style: Optional direct style override for this section heading.

    Raises:
        ValueError: If ``level`` is less than one.

    Examples:
        ```python
        from oodocs import Document, HeadingStyle, Paragraph, RunInTitleStyle, Section, TextStyle

        section = Section(
            "Results",
            Paragraph("The benchmark passed.", title="Outcome"),
            level=2,
            heading_style=HeadingStyle(text_style=TextStyle(font_size=14)),
            run_in_title_style=RunInTitleStyle(TextStyle(bold=True), separator=". "),
        )
        document = Document("Benchmark", section)
        ```
    """

    title: list[Text]
    children: list[Block]
    level: int
    numbered: bool
    toc: bool
    anchor: str | None
    run_in_title_style: RunInTitleStyle | None
    heading_style: HeadingStyle | None

    def __init__(
        self,
        title: InlineInput,
        *children: BlockInput,
        level: int = 2,
        numbered: bool = True,
        toc: bool | None = None,
        anchor: str | None = None,
        run_in_title_style: RunInTitleStyle | None = None,
        heading_style: HeadingStyle | None = None,
    ) -> None:
        if level < 1:
            raise ValueError("Section level must be >= 1")
        if heading_style is not None and not isinstance(heading_style, HeadingStyle):
            raise TypeError("heading_style must be a HeadingStyle")
        self.title = coerce_inlines((title,))
        self.children = coerce_blocks(children)
        self.level = level
        self.numbered = numbered
        self.toc = numbered if toc is None else bool(toc)
        self.anchor = anchor
        self.run_in_title_style = run_in_title_style
        self.heading_style = heading_style

    def add(self, *children: BlockInput) -> Section:
        """Append child blocks.

        Args:
            *children: Block content to append.

        Returns:
            This section, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> Section:
        """Append an iterable of child blocks.

        Args:
            children: Block content to append.

        Returns:
            This section, enabling fluent construction.
        """

        self.children.extend(coerce_blocks(children))
        return self

    def plain_title(self) -> str:
        """Return the title without styling metadata.

        Returns:
            Concatenated plain text for the title fragments.
        """

        return "".join(fragment.plain_text() for fragment in self.title)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this section and its children into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.add_heading(
            container,
            self.title,
            self.level,
            context,
            number_label=(
                context.render_index.heading_number(self)
                if self.numbered
                else None
            ),
            anchor=context.render_index.heading_anchor(self),
            toc=self.toc,
            heading_style=self.heading_style,
        )
        child_context = context
        if self.run_in_title_style is not None:
            child_context = replace(context, run_in_title_style=self.run_in_title_style)
        for child in self.children:
            child.render_to_docx(renderer, container, child_context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this section and its children into PDF flowables.

        Returns:
            ReportLab flowables for this section subtree.
        """

        return renderer.render_section(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this section and its children into HTML markup.

        Returns:
            HTML markup for this section subtree.
        """

        return renderer.render_section(self, context)


class Chapter(Section):
    """First-level document division.

    Args:
        title: Chapter title inline content.
        *children: Child block content.
        numbered: Whether the chapter should be numbered.
        toc: Whether the chapter should appear in generated tables of contents.
        anchor: Optional stable heading anchor used by renderers for internal
            links.
        run_in_title_style: Optional run-in title style inherited by
            paragraphs in this chapter subtree.
        heading_style: Optional direct style override for this chapter heading.

    Examples:
        ```python
        from oodocs import Chapter, Document, Paragraph

        chapter = Chapter("Introduction", Paragraph("This report summarizes the release."))
        document = Document("Release Report", chapter)
        ```
    """

    def __init__(
        self,
        title: InlineInput,
        *children: BlockInput,
        numbered: bool = True,
        toc: bool | None = None,
        anchor: str | None = None,
        run_in_title_style: RunInTitleStyle | None = None,
        heading_style: HeadingStyle | None = None,
    ) -> None:
        super().__init__(
            title,
            *children,
            level=1,
            numbered=numbered,
            toc=toc,
            anchor=anchor,
            run_in_title_style=run_in_title_style,
            heading_style=heading_style,
        )


class Subsection(Section):
    """Third-level document division.

    Args:
        title: Subsection title inline content.
        *children: Child block content.
        numbered: Whether the subsection should be numbered.
        toc: Whether the subsection should appear in generated tables of
            contents.
        anchor: Optional stable heading anchor used by renderers for internal
            links.
        run_in_title_style: Optional run-in title style inherited by
            paragraphs in this subsection subtree.
        heading_style: Optional direct style override for this subsection heading.

    Examples:
        ```python
        from oodocs import Chapter, Document, Paragraph, Subsection

        subsection = Subsection("Validation", Paragraph("All checks passed."))
        document = Document("Release Report", Chapter("Evidence", subsection))
        ```
    """

    def __init__(
        self,
        title: InlineInput,
        *children: BlockInput,
        numbered: bool = True,
        toc: bool | None = None,
        anchor: str | None = None,
        run_in_title_style: RunInTitleStyle | None = None,
        heading_style: HeadingStyle | None = None,
    ) -> None:
        super().__init__(
            title,
            *children,
            level=3,
            numbered=numbered,
            toc=toc,
            anchor=anchor,
            run_in_title_style=run_in_title_style,
            heading_style=heading_style,
        )


class SubSubsection(Section):
    """Fourth-level document division.

    Args:
        title: Fourth-level section title inline content.
        *children: Child block content.
        numbered: Whether the fourth-level section should be numbered.
        toc: Whether the fourth-level section should appear in generated tables of
            contents.
        anchor: Optional stable heading anchor used by renderers for internal
            links.
        run_in_title_style: Optional run-in title style inherited by
            paragraphs in this fourth-level section subtree.
        heading_style: Optional direct style override for this heading.

    Examples:
        ```python
        from oodocs import Chapter, Document, Paragraph, Subsection, SubSubsection

        subsection = SubSubsection("Audit Evidence", Paragraph("Evidence was archived."))
        document = Document("Release Report", Chapter("Evidence", Subsection("Validation", subsection)))
        ```
    """

    def __init__(
        self,
        title: InlineInput,
        *children: BlockInput,
        numbered: bool = True,
        toc: bool | None = None,
        anchor: str | None = None,
        run_in_title_style: RunInTitleStyle | None = None,
        heading_style: HeadingStyle | None = None,
    ) -> None:
        super().__init__(
            title,
            *children,
            level=4,
            numbered=numbered,
            toc=toc,
            anchor=anchor,
            run_in_title_style=run_in_title_style,
            heading_style=heading_style,
        )


def section_for_level(
    title: InlineInput,
    *children: BlockInput,
    level: int,
    numbered: bool = True,
    toc: bool | None = None,
    min_level: int = MIN_SECTION_LEVEL,
    max_level: int = MAX_SECTION_LEVEL,
    anchor: str | None = None,
    run_in_title_style: RunInTitleStyle | None = None,
    heading_style: HeadingStyle | None = None,
) -> Section:
    """Create the section-like object that best matches a heading level.

    Args:
        title: Section title inline content.
        *children: Child block content.
        level: Desired heading level.
        numbered: Whether the section should be numbered.
        toc: Whether the section should appear in generated tables of contents.
        min_level: Lowest accepted heading level.
        max_level: Highest accepted heading level.
        anchor: Optional stable heading anchor used by renderers for internal
            links.
        run_in_title_style: Optional run-in title style inherited by
            paragraphs in this section subtree.
        heading_style: Optional direct style override for this heading.

    Returns:
        ``Chapter``, ``Subsection``, ``SubSubsection``, or ``Section`` based on
        ``level``.

    Raises:
        ValueError: If ``level`` is outside the allowed range.

    Examples:
        ```python
        from oodocs import Paragraph, section_for_level

        heading = section_for_level("Details", Paragraph("More context."), level=3)
        ```
    """

    _validate_section_level(level, min_level=min_level, max_level=max_level)
    if level == 1:
        return Chapter(
            title,
            *children,
            numbered=numbered,
            toc=toc,
            anchor=anchor,
            run_in_title_style=run_in_title_style,
            heading_style=heading_style,
        )
    if level == 3:
        return Subsection(
            title,
            *children,
            numbered=numbered,
            toc=toc,
            anchor=anchor,
            run_in_title_style=run_in_title_style,
            heading_style=heading_style,
        )
    if level == 4:
        return SubSubsection(
            title,
            *children,
            numbered=numbered,
            toc=toc,
            anchor=anchor,
            run_in_title_style=run_in_title_style,
            heading_style=heading_style,
        )
    return Section(
        title,
        *children,
        level=level,
        numbered=numbered,
        toc=toc,
        anchor=anchor,
        run_in_title_style=run_in_title_style,
        heading_style=heading_style,
    )


def shift_heading_levels(
    blocks: Sequence[Block],
    delta: int,
    *,
    min_level: int = MIN_SECTION_LEVEL,
    max_level: int = MAX_SECTION_LEVEL,
) -> list[Block]:
    """Return blocks with section heading levels shifted by ``delta``.

    Paragraphs and non-heading blocks are returned unchanged. Section-like
    blocks are rebuilt at their new levels, and nested section children are
    shifted recursively.

    Args:
        blocks: Blocks to shift.
        delta: Heading-level offset to apply.
        min_level: Lowest accepted heading level after shifting.
        max_level: Highest accepted heading level after shifting.

    Returns:
        New block list with shifted section levels where applicable.

    Raises:
        ValueError: If a shifted heading level is outside the allowed range.

    Examples:
        ```python
        from oodocs import Chapter, shift_heading_levels

        shifted = shift_heading_levels([Chapter("Imported")], delta=1)
        ```
    """

    return [
        shift_heading_level(
            block,
            delta,
            min_level=min_level,
            max_level=max_level,
        )
        for block in blocks
    ]


def shift_heading_level(
    block: Block,
    delta: int,
    *,
    min_level: int = MIN_SECTION_LEVEL,
    max_level: int = MAX_SECTION_LEVEL,
) -> Block:
    """Return one block with section heading levels shifted by ``delta``.

    Args:
        block: Block to shift.
        delta: Heading-level offset to apply.
        min_level: Lowest accepted heading level after shifting.
        max_level: Highest accepted heading level after shifting.

    Returns:
        The original block when it is not a section, otherwise a rebuilt
        section-like block with shifted descendants.

    Raises:
        ValueError: If a shifted heading level is outside the allowed range.

    Examples:
        ```python
        from oodocs import Section, shift_heading_level

        subsection = shift_heading_level(Section("Imported", level=2), delta=1)
        ```
    """

    if not isinstance(block, Section):
        return block

    shifted_level = block.level + delta
    _validate_section_level(shifted_level, min_level=min_level, max_level=max_level)
    shifted_children = shift_heading_levels(
        block.children,
        delta,
        min_level=min_level,
        max_level=max_level,
    )
    return section_for_level(
        block.title,
        shifted_children,
        level=shifted_level,
        numbered=block.numbered,
        toc=block.toc,
        min_level=min_level,
        max_level=max_level,
        anchor=block.anchor,
        run_in_title_style=block.run_in_title_style,
        heading_style=block.heading_style,
    )


def _validate_section_level(
    level: int,
    *,
    min_level: int,
    max_level: int,
) -> None:
    if min_level < 1:
        raise ValueError("min_level must be >= 1 for section headings")
    if max_level < min_level:
        raise ValueError("max_level must be >= min_level")
    if level < min_level or level > max_level:
        raise ValueError(
            f"Heading level {level} is outside the supported range "
            f"{min_level}..{max_level}"
        )


CellInput = Paragraph | InlineInput


def coerce_cell(value: CellInput) -> Paragraph:
    """Normalize table or figure caption content into a paragraph.

    Args:
        value: Existing paragraph or inline paragraph content.

    Returns:
        A paragraph suitable for a table cell or caption.

    Examples:
        ```python
        cell = coerce_cell("Accuracy")
        assert cell.plain_text() == "Accuracy"
        ```
    """

    if isinstance(value, Paragraph):
        return value
    return Paragraph(value)


__all__ = [
    "Algorithm",
    "Box",
    "BulletList",
    "Chapter",
    "CellInput",
    "CodeBlock",
    "ColumnSpan",
    "CountableBlock",
    "DEFAULT_COUNTABLE_COUNTER",
    "Definition",
    "Divider",
    "Equation",
    "Example",
    "MAX_SECTION_LEVEL",
    "MIN_SECTION_LEVEL",
    "Lemma",
    "MultiColumn",
    "NumberedList",
    "PageBreak",
    "Paragraph",
    "Part",
    "Proof",
    "Remark",
    "Section",
    "Subsection",
    "SubSubsection",
    "THEOREM_COUNTER",
    "VerticalSpace",
    "Assumption",
    "Appendix",
    "Axiom",
    "Claim",
    "Conjecture",
    "Corollary",
    "Theorem",
    "Proposition",
    "coerce_cell",
    "coerce_list_item",
    "create_countable_block_type",
    "section_for_level",
    "shift_heading_level",
    "shift_heading_levels",
]
