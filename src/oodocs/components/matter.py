"""Explicit front-, main-, and back-matter containers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Iterable, TYPE_CHECKING

from oodocs.components.base import Block, BlockInput, coerce_blocks

if TYPE_CHECKING:
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext


@dataclass(slots=True, init=False)
class DocumentMatter(Block):
    """Internal base for an explicit document-matter region.

    Use :class:`FrontMatter`, :class:`MainMatter`, or :class:`BackMatter` in
    application code. Matter containers are intended to be direct children of
    a document and must not be nested.
    """

    kind: ClassVar[str] = "matter"
    children: list[Block]
    page_break_before: bool
    start_on_new_page: bool

    def __init__(
        self,
        *children: BlockInput,
        page_break_before: bool = False,
        start_on_new_page: bool = False,
    ) -> None:
        self.children = coerce_blocks(children)
        self.page_break_before = bool(page_break_before)
        self.start_on_new_page = bool(start_on_new_page)

    @property
    def requires_page_break(self) -> bool:
        """Return whether this region requests a fresh physical page."""

        return self.page_break_before or self.start_on_new_page

    def add(self, *children: BlockInput) -> DocumentMatter:
        """Append child blocks and return this container."""

        self.children.extend(coerce_blocks(children))
        return self

    def extend(self, children: Iterable[BlockInput]) -> DocumentMatter:
        """Append an iterable of child blocks and return this container."""

        self.children.extend(coerce_blocks(children))
        return self

    def _render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        for child in self.children:
            child._render_to_docx(renderer, container, context)

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        story: list[object] = []
        for child in self.children:
            story.extend(child._render_to_pdf(renderer, context))
        return story

    def _render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        return "".join(child._render_to_html(renderer, context) for child in self.children)


class FrontMatter(DocumentMatter):
    """Explicit front matter such as a preface and generated lists."""

    kind = "front"


class MainMatter(DocumentMatter):
    """Explicit primary document content."""

    kind = "main"


class BackMatter(DocumentMatter):
    """Explicit back matter such as appendices and references."""

    kind = "back"


__all__ = ["FrontMatter", "MainMatter", "BackMatter"]
