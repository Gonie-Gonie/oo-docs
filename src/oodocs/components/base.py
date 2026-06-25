"""Base block protocol and shared body container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from oodocs.components.inline import BlockReference, InlineInput
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext


class Block:
    """Base class for block-level document objects.

    Attributes:
        None: Subclasses define concrete block data and renderer behavior.

    Notes:
        Application code usually instantiates concrete subclasses such as
        ``Paragraph``, ``Table``, or ``Figure``. Custom block implementations
        should override the renderer hooks.

    Examples:
        ```python
        from oodocs import Document, Paragraph

        target = Paragraph("Deployment note")
        paragraph = Paragraph("See ", target.reference("the deployment note"))
        document = Document("Release Notes", target, paragraph)
        ```
    """

    def reference(
        self,
        *label: InlineInput,
    ) -> BlockReference:
        """Create an explicit inline reference to this block.

        Args:
            *label: Optional inline content to use instead of the automatic
                reference label.

        Returns:
            An inline block reference targeting this block.

        Examples:
            ```python
            from oodocs import Paragraph

            target = Paragraph("Important details")
            reference = target.reference("details")
            ```
        """

        from oodocs.components.inline import reference

        return reference(self, *label)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render the block into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.

        Raises:
            NotImplementedError: Always raised by the base implementation.
        """

        raise NotImplementedError

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render the block into one or more PDF flowables.

        Args:
            renderer: PDF renderer instance.
            context: Shared PDF render context.

        Returns:
            ReportLab flowables for this block.

        Raises:
            NotImplementedError: Always raised by the base implementation.
        """

        raise NotImplementedError

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render the block into HTML markup.

        Args:
            renderer: HTML renderer instance.
            context: Shared HTML render context.

        Returns:
            HTML markup for this block.

        Raises:
            NotImplementedError: Always raised by the base implementation.
        """

        raise NotImplementedError


BlockInput = Block | str | Sequence["BlockInput"] | None


def coerce_blocks(values: Iterable[BlockInput]) -> list[Block]:
    """Normalize supported block inputs into block objects.

    Args:
        values: Block instances, strings, nested block sequences, or ``None``.

    Returns:
        A flat list of block objects.

    Raises:
        TypeError: If a value cannot be converted to a block.

    Examples:
        ```python
        blocks = coerce_blocks(["Intro", None, ["Nested paragraph"]])
        assert len(blocks) == 2
        ```
    """

    from oodocs.components.blocks import Paragraph

    normalized: list[Block] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, Block):
            normalized.append(value)
            continue
        if isinstance(value, str):
            normalized.append(Paragraph(value))
            continue
        if isinstance(value, Sequence):
            normalized.extend(coerce_blocks(value))
            continue
        raise TypeError(f"Unsupported block value: {type(value)!r}")
    return normalized


@dataclass(slots=True, init=False)
class Body(Block):
    """Top-level block container used by ``Document``.

    Args:
        *children: Initial block content using ``coerce_blocks`` rules.

    Examples:
        ```python
        from oodocs import Document

        body = Body("Intro").add("Next paragraph")
        document = Document("Report", body=body)
        ```
    """

    children: list[Block]

    def __init__(self, *children: BlockInput) -> None:
        self.children = coerce_blocks(children)

    def add(self, *children: BlockInput) -> Body:
        """Append children using the same coercion rules as the constructor.

        Args:
            *children: Block content to append.

        Returns:
            This body, enabling fluent construction.

        Examples:
            ```python
            body = Body()
            body.add("Executive summary", "Evidence")
            ```
        """

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> Body:
        """Append an iterable of children.

        Args:
            children: Block content to append.

        Returns:
            This body, enabling fluent construction.

        Examples:
            ```python
            body = Body()
            body.extend(["First paragraph", "Second paragraph"])
            ```
        """

        self.children.extend(coerce_blocks(children))
        return self

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render all children into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        for child in self.children:
            child.render_to_docx(renderer, container, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render all children into PDF flowables.

        Args:
            renderer: PDF renderer instance.
            context: Shared PDF render context.

        Returns:
            A flattened list of child flowables.
        """

        story: list[object] = []
        for child in self.children:
            story.extend(child.render_to_pdf(renderer, context))
        return story

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render all children into HTML markup.

        Args:
            renderer: HTML renderer instance.
            context: Shared HTML render context.

        Returns:
            Concatenated child HTML.
        """

        return "".join(child.render_to_html(renderer, context) for child in self.children)


__all__ = ["Block", "BlockInput", "Body", "coerce_blocks"]
