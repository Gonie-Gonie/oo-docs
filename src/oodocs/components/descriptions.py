"""Semantic term-and-definition list blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, TYPE_CHECKING

from oodocs.components.base import Block, BlockInput, coerce_blocks
from oodocs.components.inline import InlineInput, Text, coerce_inlines
from oodocs.styles.descriptions import (
    DescriptionListLayout,
    DescriptionListStyle,
    description_list_style_with_overrides,
)

if TYPE_CHECKING:
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext
    from oodocs.styles import ParagraphStyle, TextStyle


@dataclass(slots=True, init=False)
class DescriptionItem:
    """One inline term followed by one or more block definitions."""

    term: list[Text]
    children: list[Block]

    def __init__(self, term: InlineInput, *children: BlockInput) -> None:
        self.term = coerce_inlines((term,))
        self.children = coerce_blocks(children)

    def add(self, *children: BlockInput) -> DescriptionItem:
        """Append definition blocks and return this item."""

        self.children.extend(coerce_blocks(children))
        return self

    def plain_term(self) -> str:
        """Return the term as unstyled plain text."""

        return "".join(fragment.plain_text() for fragment in self.term)

    def plain_definition(self) -> str:
        """Return definition blocks as newline-separated plain text."""

        return "\n".join(
            text for child in self.children if (text := _block_plain_text(child))
        )


@dataclass(slots=True, init=False)
class DescriptionList(Block):
    """A semantic list of terms and block-level definitions.

    Strings passed as definition children are normalized to ``Paragraph``
    blocks by the shared block coercion rules. Rich definitions can therefore
    contain lists, code blocks, equations, and paragraphs with links or
    footnotes without reducing them to table-cell text.
    """

    items: list[DescriptionItem]
    style: DescriptionListStyle | str

    def __init__(
        self,
        items: Iterable[DescriptionItem] | None = None,
        *,
        style: DescriptionListStyle | str | None = None,
        layout: DescriptionListLayout | None = None,
        term_width: float | None = None,
        term_text_style: TextStyle | None = None,
        definition_style: ParagraphStyle | None = None,
        item_spacing: float | None = None,
        term_gap: float | None = None,
        unit: str | None = None,
    ) -> None:
        self.items = []
        if items is not None:
            for item in items:
                if not isinstance(item, DescriptionItem):
                    raise TypeError("DescriptionList items must be DescriptionItem objects")
                self.items.append(item)
        self.style = description_list_style_with_overrides(
            style,
            layout=layout,
            term_width=term_width,
            term_text_style=term_text_style,
            definition_style=definition_style,
            item_spacing=item_spacing,
            term_gap=term_gap,
            unit=unit,
        )

    def add(self, term: InlineInput, *children: BlockInput) -> DescriptionList:
        """Append a term and its definition blocks, returning this list."""

        self.items.append(DescriptionItem(term, *children))
        return self

    def extend(self, items: Iterable[DescriptionItem]) -> DescriptionList:
        """Append existing description items, returning this list."""

        for item in items:
            if not isinstance(item, DescriptionItem):
                raise TypeError("DescriptionList items must be DescriptionItem objects")
            self.items.append(item)
        return self

    def as_records(self) -> list[dict[str, str]]:
        """Return raw plain-text ``term`` and ``definition`` records."""

        return [
            {
                "term": item.plain_term(),
                "definition": item.plain_definition(),
            }
            for item in self.items
        ]

    def _render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        renderer.render_description_list(container, self, context)

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        return renderer.render_description_list(self, context)

    def _render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        return renderer.render_description_list(self, context)


def _block_plain_text(block: Block) -> str:
    plain_text = getattr(block, "plain_text", None)
    if callable(plain_text):
        return str(plain_text())

    code = getattr(block, "code", None)
    if isinstance(code, str):
        return code

    items = getattr(block, "items", None)
    if isinstance(items, list):
        item_text = [
            _block_plain_text(item)
            for item in items
            if isinstance(item, Block)
        ]
        if item_text:
            return "\n".join(text for text in item_text if text)

    children = getattr(block, "children", None)
    if isinstance(children, list):
        return "\n".join(
            text
            for child in children
            if isinstance(child, Block) and (text := _block_plain_text(child))
        )
    return ""


__all__ = ["DescriptionItem", "DescriptionList"]
