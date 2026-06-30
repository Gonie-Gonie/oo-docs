"""Base block protocol and shared body container.

Attributes:
    BlockInput: Recursive block input accepted by block containers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from oodocs.components.inline import BlockReference, InlineInput, ReferenceFormat
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext
    from oodocs.styles import TextStyle


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
        paragraph = Paragraph("See ", target.ref("the deployment note"))
        document = Document("Release Notes", target, paragraph)
        ```
    """

    def ref(
        self,
        *label: InlineInput,
        style: TextStyle | None = None,
        reference_format: ReferenceFormat | None = None,
    ) -> BlockReference:
        """Create an explicit inline reference to this block.

        Args:
            *label: Optional inline content to use instead of the automatic
                reference label.
            style: Optional inline style.
            reference_format: Optional automatic reference formatting rules.

        Returns:
            An inline block reference targeting this block.

        Examples:
            ```python
            from oodocs import Paragraph

            target = Paragraph("Important details")
            reference = target.ref("details")
            ```
        """

        from oodocs.components.inline import ref

        return ref(self, *label, style=style, reference_format=reference_format)

    def _render_to_docx(
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

    def _render_to_pdf(
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

    def _render_to_html(
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


class Component(Block):
    """Composable block extension base class.

    Custom components can describe themselves with ordinary OODocs blocks by
    overriding ``compose``. Renderers, validation, and document indexing then
    operate on those composed blocks instead of requiring renderer hook
    implementations.

    Examples:
        ```python
        from oodocs import Paragraph, Table
        from oodocs.components import Component

        class EvidenceSummary(Component):
            def compose(self):
                table = Table(["Metric", "Value"], [["status", "pass"]])
                return [Paragraph("Validation summary."), table]
        ```
    """

    _composed_blocks_cache: tuple[Block, ...] | None = None

    def compose(self) -> Iterable[BlockInput]:
        """Return the ordinary blocks that implement this component.

        Returns:
            Block inputs accepted by normal document containers.

        Raises:
            NotImplementedError: Always raised by the base implementation.
        """

        raise NotImplementedError

    def composed_blocks(self) -> tuple[Block, ...]:
        """Return cached composed blocks for rendering and validation.

        Returns:
            Normalized block tuple produced by ``compose``.
        """

        if self._composed_blocks_cache is None:
            self._composed_blocks_cache = tuple(coerce_blocks(self.compose()))
        return self._composed_blocks_cache

    def reset_composed_blocks(self) -> None:
        """Clear cached composed blocks after mutating component state."""

        self._composed_blocks_cache = None

    def _render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render composed blocks into a DOCX container."""

        for child in self.composed_blocks():
            child._render_to_docx(renderer, container, context)

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render composed blocks into PDF flowables."""

        story: list[object] = []
        for child in self.composed_blocks():
            story.extend(child._render_to_pdf(renderer, context))
        return story

    def _render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render composed blocks into HTML markup."""

        return "".join(child._render_to_html(renderer, context) for child in self.composed_blocks())


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
        *children: Initial block content, accepting blocks, strings, nested
            sequences, or ``None``.

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

    def _render_to_docx(
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
            child._render_to_docx(renderer, container, context)

    def _render_to_pdf(
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
            story.extend(child._render_to_pdf(renderer, context))
        return story

    def _render_to_html(
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

        return "".join(child._render_to_html(renderer, context) for child in self.children)


__all__ = ["Block", "BlockInput", "Body", "Component"]
