"""HTML renderer."""

from __future__ import annotations

from base64 import b64encode
from dataclasses import replace
from html import escape
from mimetypes import guess_type
from pathlib import Path

from oodocs.components.blocks import (
    Box,
    BulletList,
    CodeBlock,
    ColumnSpan,
    CountableBlock,
    Divider,
    Equation,
    MultiColumn,
    NumberedList,
    PageBreak,
    Paragraph,
    Part,
    Section,
    VerticalSpace,
)
from oodocs.components.generated import (
    CommentList,
    ListOfAlgorithms,
    ListOfFigures,
    FootnoteList,
    ReferenceList,
    ListOfTables,
    TableOfContents,
    TocLevelStyle,
)
from oodocs.components.inline import (
    _BlockReference,
    Citation,
    Comment,
    Footnote,
    Hyperlink,
    InlineChip,
    Math,
    Text,
)
from oodocs.components.media import (
    Figure,
    PdfPages,
    SubFigure,
    SubFigureGroup,
    SubTable,
    SubTableGroup,
    Table,
    TablePlacement,
    build_table_layout,
    image_source_to_bytes,
    processed_image_source_to_buffer,
)
from oodocs.components.people import AuthorTitleLine
from oodocs.components.positioning import (
    ImageBox,
    PositionedBox,
    PositionedItem,
    Shape,
    TextBox,
    resolve_positioned_boxes,
)
from oodocs.components.references import format_citation_label, reference_entry_marker
from oodocs.core import OODocsError, PathLike, length_to_inches
from oodocs.document import Document
from oodocs.components.equations import SUBSCRIPT, SUPERSCRIPT, parse_latex_segments
from oodocs.layout.indexing import RenderIndex, build_render_index
from oodocs.styles import BoxStyle, HeadingStyle, ParagraphStyle, TableStyle, Theme
from oodocs.renderers.context import HtmlRenderContext
from oodocs.renderers.syntax import _syntax_line_html, syntax_html


def _countable_entry_fragments(entry: object) -> list[Text]:
    label = entry.block.reference_text(entry.number)
    if entry.block.title is None:
        return [Text(label)]
    return [Text(f"{label}. ")] + entry.block.title


class HtmlRenderer:
    """Render OODocs documents into standalone HTML files.

    The renderer exposes ``render_*`` methods so block classes and custom
    extensions can dispatch HTML rendering through a shared context.

    Attributes:
        None: The renderer is stateless between ``render`` calls.
    """

    def render(self, document: Document, output_path: PathLike) -> Path:
        """Render an OODocs document to an HTML file.

        Args:
            document: Document to render.
            output_path: Destination ``.html`` path.

        Returns:
            Output path that was written.
        """

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        settings = document.settings
        render_index = build_render_index(document)
        context = HtmlRenderContext(
            theme=settings.theme,
            render_index=render_index,
            settings=settings,
            unit=settings.unit,
        )
        front_children, main_children = document.split_top_level_children()
        has_front_matter = settings.cover_page or bool(front_children)

        body_parts = [
            '<div class="oodocs-page-frame">',
            self._page_items_html(document, context),
            '<div class="oodocs-document">',
            self._render_title_matter(
                document,
                context,
                page_break_after=settings.cover_page and (bool(front_children) or bool(main_children)),
            ),
        ]

        if has_front_matter:
            if front_children:
                body_parts.append(
                    '<section class="oodocs-front-matter">'
                    + self._render_children(front_children, context)
                    + "</section>"
                )
            if main_children:
                body_parts.append(
                    '<section class="oodocs-main-matter oodocs-page-break-before">'
                    + self._render_children(main_children, context)
                    + "</section>"
                )
        else:
            body_parts.append(
                '<section class="oodocs-main-matter">'
                + self._render_children(main_children, context)
                + "</section>"
            )

        if self._should_auto_render_footnote_list(document, render_index):
            body_parts.append(self.render_footnote_list(FootnoteList(), context))

        body_parts.append("</div>")
        body_parts.append("</div>")

        html = "\n".join(
            [
                "<!DOCTYPE html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8" />',
                '  <meta name="viewport" content="width=device-width, initial-scale=1" />',
                f"  <title>{escape(document.title)}</title>",
                f"  <meta name=\"description\" content=\"{escape(settings.summary or document.title)}\" />",
                "  <style>",
                self._stylesheet(settings),
                "  </style>",
                "</head>",
                "<body>",
                *body_parts,
                "</body>",
                "</html>",
            ]
        )
        path.write_text(html, encoding="utf-8")
        return path

    def render_paragraph(self, block: Paragraph, context: HtmlRenderContext) -> str:
        """Render a paragraph block into HTML.

        Args:
            block: Paragraph block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the paragraph.
        """

        anchor = context.render_index.block_anchor(block)
        anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
        title_style = context.theme.resolve_run_in_title_style(
            block.title_style,
            context.run_in_title_style,
        )
        paragraph_style = context.stylesheet.resolve("paragraph", block.style, ParagraphStyle())
        class_attr = self._html_class_attr("oodocs-paragraph", paragraph_style.css_class)
        return (
            f'<p{anchor_attr}{class_attr} style="{self._paragraph_style_css(paragraph_style, context.theme, default_unit=context.unit)}">'
            + self._inline_html(
                block.render_content(title_style),
                context.theme,
                context.render_index,
            )
            + "</p>"
        )

    def render_part(self, block: Part, context: HtmlRenderContext) -> str:
        """Render a part separator page and its child blocks into HTML.

        Args:
            block: Part block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the part separator and children.
        """

        number_label = context.render_index.heading_number(block) if block.numbered else None
        anchor = context.render_index.heading_anchor(block)
        anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
        label_html = (
            '<p class="oodocs-part-label">'
            + self._inline_html(
                [Text(number_label)],
                context.theme,
                context.render_index,
                base_bold=True,
                base_size=max(context.theme.typography.body_font_size + 3, 14),
            )
            + "</p>"
            if number_label
            else ""
        )
        title_html = (
            '<h1 class="oodocs-part-title">'
            + self._inline_html(
                block.title,
                context.theme,
                context.render_index,
                base_bold=True,
                base_size=max(context.theme.typography.title_font_size, context.theme.resolve_heading_size(1) + 2),
            )
            + "</h1>"
        )
        children_html = self._render_children(block.children, context)
        return (
            '<section class="oodocs-part">'
            f'<section{anchor_attr} class="oodocs-part-page oodocs-page-break-before oodocs-page-break-after">'
            + label_html
            + title_html
            + "</section>"
            + children_html
            + "</section>"
        )

    def render_list(
        self,
        block: BulletList | NumberedList,
        context: HtmlRenderContext,
    ) -> str:
        """Render a list block into HTML.

        Args:
            block: Bullet or numbered list block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the list.
        """

        return self._render_list(block, context, depth=0)

    def _render_list(
        self,
        block: BulletList | NumberedList,
        context: HtmlRenderContext,
        *,
        depth: int,
    ) -> str:
        list_style = context.stylesheet.resolve(
            "list",
            block.style,
            context.theme.list_style(ordered=isinstance(block, NumberedList)),
        )
        if depth:
            list_style = replace(list_style, indent=list_style.indent + depth * 0.22)
        items = []
        for index, item in enumerate(block.items):
            marker = escape(list_style.marker_for(index))
            anchor = context.render_index.block_anchor(item)
            anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
            child_html = "".join(
                self._render_list(child_list, context, depth=depth + 1)
                for child_list in block.item_children[index]
            )
            item_style = context.stylesheet.resolve("paragraph", item.style, ParagraphStyle())
            items.append(
                (
                    '<div class="oodocs-list-item" '
                    f'style="column-gap: {list_style.marker_gap:.2f}in; padding-left: {list_style.indent:.2f}in;">'
                    f'<div class="oodocs-list-marker">{marker}</div>'
                    '<div class="oodocs-list-content">'
                    f'<p{anchor_attr} class="oodocs-paragraph" style="{self._paragraph_style_css(item_style, context.theme, default_space_after=3.0, default_unit=context.unit)}">'
                    + self._inline_html(
                        item.content,
                        context.theme,
                        context.render_index,
                    )
                    + "</p>"
                    + child_html
                    + "</div>"
                    + "</div>"
                )
            )
        list_class = "oodocs-numbered-list" if isinstance(block, NumberedList) else "oodocs-bullet-list"
        return f'<div class="oodocs-list {list_class}">{"".join(items)}</div>'

    def render_code_block(
        self,
        block: CodeBlock,
        context: HtmlRenderContext,
    ) -> str:
        """Render a code block into HTML.

        Args:
            block: Code block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the code block.
        """

        show_label = bool(block.language and block.show_language)
        label = (
            f'<div class="oodocs-code-language oodocs-code-language-{escape(block.language_position)}">'
            f"{escape(block.language.upper())}</div>"
            if show_label
            else ""
        )
        code_classes = ["oodocs-code"]
        if show_label:
            code_classes.append(f"oodocs-code-has-label-{block.language_position.split('-', 1)[0]}")
        anchor = context.render_index.block_anchor(block)
        anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
        identifier_attr = f' data-oodocs-identifier="{escape(block.identifier)}"' if block.identifier else ""
        code_style = context.stylesheet.resolve("paragraph", block.style, ParagraphStyle())
        caption_html = ""
        if block.caption is not None:
            caption_html = (
                '<div class="oodocs-caption oodocs-code-caption" '
                f'style="text-align: {context.theme.captions.caption_text_alignment}; '
                f'font-size: {context.theme.caption_size():.1f}pt;">'
                + self._inline_html(
                    self._caption_fragments("Code block", context.render_index.code_block_number(block), block.caption),
                    context.theme,
                    context.render_index,
                    base_size=context.theme.caption_size(),
                )
                + "</div>"
            )
        return (
            f'<section{anchor_attr}{identifier_attr} class="oodocs-code-block oodocs-code-label-{escape(block.language_position)}">'
            + label
            + f'<pre class="{" ".join(code_classes)}" style="margin-bottom: {(code_style.space_after or 0):.1f}pt;">'
            + self._code_block_html(block)
            + "</pre>"
            + caption_html
            + "</section>"
        )

    def _code_block_html(self, block: CodeBlock) -> str:
        lines: list[str] = []
        for line_number, line in enumerate(block.normalized_lines(), start=1):
            classes = ["oodocs-code-line"]
            if line_number in block.highlight_lines:
                classes.append("oodocs-code-line-highlight")
            prefix = ""
            if block.line_numbers:
                prefix = (
                    '<span class="oodocs-code-line-number" '
                    'style="color: #6F7D90; user-select: none;">'
                    f"{escape(block.line_prefix(line_number))}</span>"
                )
            line_html = _syntax_line_html(line, block.language) or " "
            highlight_style = " background-color: #FFF3B0;" if line_number in block.highlight_lines else ""
            lines.append(
                f'<span class="{" ".join(classes)}" style="display: block;{highlight_style}">'
                + prefix
                + line_html
                + "</span>"
            )
        return "\n".join(lines)

    def render_equation(
        self,
        block: Equation,
        context: HtmlRenderContext,
    ) -> str:
        """Render a block equation into HTML.

        Args:
            block: Equation block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the equation.
        """

        equation_style = context.stylesheet.resolve("paragraph", block.style, ParagraphStyle())
        line_height = equation_style.leading or max(context.theme.typography.body_font_size + 1, 12) * 1.3
        anchor = context.render_index.block_anchor(block)
        anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
        number = context.render_index.equation_number(block)
        number_html = f'<span class="oodocs-equation-number">({number})</span>' if number is not None else ""
        return (
            f'<div{anchor_attr} class="oodocs-equation" '
            f'style="text-align: {context.theme.resolve_paragraph_text_alignment(equation_style)}; margin: 0 0 {(equation_style.space_after or 0):.1f}pt; line-height: {line_height:.1f}pt;">'
            + self._math_html(
                Math(block.expression),
                context.theme,
                base_size=max(context.theme.typography.body_font_size + 1, 12),
            )
            + number_html
            + "</div>"
        )

    def render_page_break(
        self,
        block: PageBreak,
        context: HtmlRenderContext,
    ) -> str:
        """Render an explicit page break into HTML.

        Args:
            block: Page break block to render.
            context: Current HTML render context.

        Returns:
            HTML page-break marker.
        """

        return '<div class="oodocs-page-break"></div>'

    def render_vertical_space(
        self,
        block: VerticalSpace,
        context: HtmlRenderContext,
    ) -> str:
        """Render a LaTeX-like vertical spacer into HTML.

        Args:
            block: Vertical space block to render.
            context: Current HTML render context.

        Returns:
            HTML spacer fragment.
        """

        return (
            '<div class="oodocs-vertical-space" aria-hidden="true" '
            f'style="height: {block.height_in_points():.1f}pt;"></div>'
        )

    def render_divider(
        self,
        block: Divider,
        context: HtmlRenderContext,
    ) -> str:
        """Render a horizontal divider into HTML.

        Args:
            block: Divider block to render.
            context: Current HTML render context.

        Returns:
            HTML divider fragment.
        """

        width = block.width_in_inches(context.unit)
        width_style = "width: 100%;" if width is None else f"width: {width:.4f}in;"
        return (
            '<hr class="oodocs-divider" '
            f'style="border: 0; border-top: {block.thickness:.2f}pt solid #{block.color}; '
            f'margin-top: {block.space_before:.1f}pt; margin-bottom: {block.space_after:.1f}pt; '
            f'{width_style} {self._block_alignment_css(block.alignment)}" />'
        )

    def render_box(self, block: Box, context: HtmlRenderContext) -> str:
        """Render a box and its children into HTML.

        Args:
            block: Box block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the box and child content.
        """

        self._assert_box_children_supported(block.children)
        box_style = self._effective_box_style(block, context.theme)
        title_fragments = block.title_fragments()
        if title_fragments is None and box_style.title_position == "side":
            box_style = replace(box_style, title_position="top")
        title_is_side = title_fragments is not None and box_style.title_position == "side"
        title_html = ""
        if title_fragments is not None:
            title_html = (
                '<div class="oodocs-box-title" '
                f'style="{self._box_title_css(box_style, context.theme, side=title_is_side)}">'
                + self._inline_html(
                    title_fragments,
                    context.theme,
                    context.render_index,
                    base_bold=True,
                )
                + "</div>"
            )
        children_html = "".join(
            child.render_to_html(
                self,
                HtmlRenderContext(
                    theme=context.theme,
                    render_index=context.render_index,
                    settings=context.settings,
                    unit=context.unit,
                    in_box=True,
                ),
            )
            for child in block.children
        )
        anchor = context.render_index.block_anchor(block)
        anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
        class_attr = self._html_class_attr("oodocs-box", box_style.css_class)
        body_html = (
            '<div class="oodocs-box-body" style="min-width: 0;">'
            + children_html
            + "</div>"
            if title_is_side
            else children_html
        )
        return (
            f'<section{anchor_attr}{class_attr} '
            f'style="{self._box_css(box_style, context.theme, context.unit)}">'
            + title_html
            + body_html
            + "</section>"
        )

    def render_countable_block(
        self,
        block: CountableBlock,
        context: HtmlRenderContext,
    ) -> str:
        """Render a theorem-like countable block into HTML.

        Args:
            block: Countable block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the countable block.
        """

        if block.box_style is not None:
            boxed_block = Box(
                *block.children,
                title=block.heading_fragments(context.render_index.countable_number(block)),
                style=block.box_style,
            )
            anchor = context.render_index.block_anchor(block)
            if anchor is not None:
                context.render_index.block_anchors[id(boxed_block)] = anchor
            return self.render_box(boxed_block, context)

        number = context.render_index.countable_number(block)
        anchor = context.render_index.block_anchor(block)
        anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
        title_html = (
            ' <span class="oodocs-countable-title">'
            + self._inline_html(
                block.title,
                context.theme,
                context.render_index,
                base_italic=True,
            )
            + "</span>"
            if block.title is not None
            else ""
        )
        return (
            f'<section{anchor_attr} class="oodocs-countable-block oodocs-countable-{escape(block.kind.lower().replace(" ", "-"))}">'
            '<p class="oodocs-countable-heading">'
            f'<strong class="oodocs-countable-label">{escape(block.heading_label(number))}</strong>'
            + title_html
            + "</p>"
            + self._render_children(block.children, context)
            + "</section>"
        )

    def render_column_span(self, block: ColumnSpan, context: HtmlRenderContext) -> str:
        """Render full-width content from a multicolumn flow.

        Args:
            block: Column-span block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment spanning all columns.
        """

        return (
            '<div class="oodocs-column-span">'
            + self._render_children(block.children, context)
            + "</div>"
        )

    def render_multi_column(self, block: MultiColumn, context: HtmlRenderContext) -> str:
        """Render a multicolumn flow into HTML.

        Args:
            block: Multi-column block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment containing grouped column content.
        """

        if block.columns == 1:
            return self._render_children(block.children, context)

        current_group: list[object] = []
        parts: list[str] = []
        available_width = context.settings.text_width_in_inches()

        def flush_group() -> None:
            if not current_group:
                return
            parts.append(self._multi_column_group_html(block, current_group, context))
            current_group.clear()

        for child in block.children:
            # Full-width children split the current column group so they can
            # occupy the full page width between ordinary multi-column runs.
            if block._child_spans_columns(
                child,
                available_width=available_width,
                default_unit=context.unit,
            ):
                flush_group()
                if isinstance(child, ColumnSpan):
                    parts.append(child.render_to_html(self, context))
                else:
                    parts.append(
                        '<div class="oodocs-column-span">'
                        + child.render_to_html(self, context)
                        + "</div>"
                    )
                continue
            current_group.append(child)
        flush_group()
        return '<section class="oodocs-multi-column-layout">' + "".join(parts) + "</section>"

    def render_shape(self, block: Shape, context: HtmlRenderContext) -> str:
        """Render a shape into HTML.

        Args:
            block: Shape to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the positioned or inline shape.
        """

        return self._positioned_item_html(self._inline_or_page_box(block, context), context)

    def render_text_box(self, block: TextBox, context: HtmlRenderContext) -> str:
        """Render a textbox into HTML.

        Args:
            block: Text box to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the positioned or inline text box.
        """

        return self._positioned_item_html(self._inline_or_page_box(block, context), context)

    def render_image_box(self, block: ImageBox, context: HtmlRenderContext) -> str:
        """Render an image box into HTML.

        Args:
            block: Image box to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the positioned or inline image.
        """

        return self._positioned_item_html(self._inline_or_page_box(block, context), context)

    def render_section(self, block: Section, context: HtmlRenderContext) -> str:
        """Render a titled section and its children into HTML.

        Args:
            block: Section block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the heading and child blocks.
        """

        heading_tag = self._heading_tag(block.level)
        number_label = context.render_index.heading_number(block) if block.numbered else None
        anchor = context.render_index.heading_anchor(block)
        heading_style = context.theme.resolve_heading_style(block.level, block.heading_style)
        heading_text_style = heading_style.text_style
        child_context = (
            replace(context, run_in_title_style=block.run_in_title_style)
            if block.run_in_title_style is not None
            else context
        )
        children_html = "".join(
            child.render_to_html(self, child_context)
            for child in block.children
        )
        heading_html = (
            f"<{heading_tag}"
            + (f' id="{escape(anchor)}"' if anchor else "")
            + f' class="oodocs-heading oodocs-heading-level-{block.level}"'
            + f' style="{self._heading_css(block.level, context.theme, block.heading_style)}">'
            + self._inline_html(
                self._heading_fragments(block.title, number_label),
                context.theme,
                context.render_index,
                base_bold=bool(heading_text_style.bold),
                base_italic=bool(heading_text_style.italic),
                base_size=heading_text_style.font_size or context.theme.resolve_heading_size(block.level),
            )
            + f"</{heading_tag}>"
        )
        return (
            f'<section class="oodocs-section oodocs-section-level-{block.level}">'
            + heading_html
            + children_html
            + "</section>"
        )

    def render_table(self, block: Table, context: HtmlRenderContext) -> str:
        """Render a table block into HTML.

        Args:
            block: Table block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the table wrapper, caption, and table element.
        """

        table_style = context.stylesheet.resolve("table", block.style, TableStyle())
        layout = build_table_layout(block.header_rows, block.rows)
        split_table = block._resolve_split()
        placement = block._resolve_placement()
        colgroup = ""
        column_widths = block._column_widths_in_inches(
            context.unit,
            available_width=context.settings.text_width_in_inches(),
        )
        if column_widths is not None:
            columns = "".join(
                f'<col style="width: {width:.2f}in;" />'
                for width in column_widths
            )
            colgroup = f"<colgroup>{columns}</colgroup>"

        thead_html = self._table_section_html(
            layout,
            header=True,
            block=block,
            context=context,
            table_style=table_style,
        )
        tbody_html = self._table_section_html(
            layout,
            header=False,
            block=block,
            context=context,
            table_style=table_style,
        )
        caption_html = (
            self._caption_html(
                block.caption,
                label=context.theme.resolve_caption_label("table", "caption"),
                number=context.render_index.table_number(block),
                anchor=context.render_index.table_anchor(block),
                context=context,
                kind="table",
            )
            if block.caption is not None
            else ""
        )
        table_class_attr = self._html_class_attr("oodocs-table", table_style.css_class)
        continuation_attrs = self._table_continuation_attrs(block)
        table_html = (
            '<div class="oodocs-table-wrapper '
            f'oodocs-placement-{placement} '
            f'{"oodocs-table-split" if split_table else "oodocs-table-keep"}" '
            f'style="{self._table_wrapper_css(context.theme, in_box=context.in_box)} {self._media_placement_css(placement, in_box=context.in_box)}">'
            + (
                caption_html
                if block.caption is not None and context.theme.captions.table_caption_position == "above"
                else ""
            )
            + f"<table{table_class_attr}{continuation_attrs}>"
            + colgroup
            + (f"<thead>{thead_html}</thead>" if thead_html else "")
            + (f"<tbody>{tbody_html}</tbody>" if tbody_html else "")
            + "</table>"
            + (
                caption_html
                if block.caption is not None and context.theme.captions.table_caption_position == "below"
                else ""
            )
            + "</div>"
        )
        return table_html

    def _table_continuation_attrs(self, block: Table) -> str:
        attrs = []
        if block.continuation_label is not None:
            attrs.append(
                f' data-continuation-label="{escape(block.continuation_label)}"'
            )
        continued_caption = block.continued_caption_text()
        if continued_caption is not None:
            attrs.append(
                f' data-continued-caption="{escape(continued_caption)}"'
            )
        return "".join(attrs)

    def render_pdf_pages(self, block: PdfPages, context: HtmlRenderContext) -> str:
        """Render an HTML fallback for external PDF pages."""

        label = escape(block.title or block.source.name)
        href = escape(str(block.source))
        pages = escape(block.page_label())
        return (
            '<div class="oodocs-pdf-pages" '
            f'style="{self._table_wrapper_css(context.theme, in_box=context.in_box)}">'
            f'<a href="{href}">PDF pages: {label}</a> '
            f'<span class="oodocs-pdf-pages-selection">({pages})</span>'
            "</div>"
        )

    def render_figure(self, block: Figure, context: HtmlRenderContext) -> str:
        """Render a figure block into HTML.

        Args:
            block: Figure block to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the figure and optional caption.
        """

        placement = block.resolved_placement()
        image_style = ""
        resolved_width = block.width_in_inches(context.unit)
        resolved_height = block.height_in_inches(context.unit)
        image_styles = []
        if resolved_width is not None:
            image_styles.append(f"width: {resolved_width:.2f}in")
            image_styles.append("max-width: 100%")
        if resolved_height is not None:
            image_styles.append(f"height: {resolved_height:.2f}in")
            image_styles.append("max-height: 100%")
        if resolved_width is None and resolved_height is not None:
            image_styles.append("width: auto")
        if resolved_height is None:
            image_styles.append("height: auto")
        if image_styles:
            image_style = f' style="{"; ".join(image_styles)};"'
        alt_text = self._figure_alt_text(block, "Figure")
        image_html = (
            f'<img class="oodocs-figure-image" src="{self._figure_src(block, context.unit)}" '
            f'alt="{escape(alt_text)}"{image_style} />'
        )
        caption_html = (
            self._caption_html(
                block.caption,
                label=context.theme.resolve_caption_label("figure", "caption"),
                number=context.render_index.figure_number(block),
                anchor=context.render_index.figure_anchor(block),
                context=context,
                kind="figure",
            )
            if block.caption is not None
            else ""
        )
        content_parts = []
        if block.caption is not None and context.theme.captions.figure_caption_position == "above":
            content_parts.append(caption_html)
        content_parts.append(image_html)
        if block.caption is not None and context.theme.captions.figure_caption_position == "below":
            content_parts.append(caption_html)
        return (
            f'<figure class="oodocs-figure oodocs-placement-{placement}" '
            f'style="{self._figure_css(context.theme, in_box=context.in_box)} {self._media_placement_css(placement, in_box=context.in_box)}">'
            + "".join(content_parts)
            + "</figure>"
        )

    def render_subfigure_group(self, block: SubFigureGroup, context: HtmlRenderContext) -> str:
        """Render a subfigure group into HTML.

        Args:
            block: Subfigure group to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the grouped subfigures and optional caption.
        """

        placement = block.resolved_placement()
        caption_html = (
            self._caption_html(
                block.caption,
                label=context.theme.resolve_caption_label("figure", "caption"),
                number=context.render_index.figure_number(block),
                anchor=context.render_index.figure_anchor(block),
                context=context,
                kind="figure",
            )
            if block.caption is not None
            else ""
        )
        subfigures = "".join(
            self._subfigure_html(subfigure, index, block, context)
            for index, subfigure in enumerate(block.subfigures)
        )
        grid_style = (
            f"display: grid; grid-template-columns: repeat({block.columns}, minmax(0, 1fr)); "
            f"gap: {length_to_inches(block.column_gap, block.unit or context.unit):.2f}in;"
        )
        content_parts = []
        if block.caption is not None and context.theme.captions.figure_caption_position == "above":
            content_parts.append(caption_html)
        content_parts.append(f'<div class="oodocs-subfigure-grid" style="{grid_style}">{subfigures}</div>')
        if block.caption is not None and context.theme.captions.figure_caption_position == "below":
            content_parts.append(caption_html)
        return (
            f'<figure class="oodocs-figure oodocs-subfigure-group oodocs-placement-{placement}" '
            f'style="{self._figure_css(context.theme, in_box=context.in_box)} {self._media_placement_css(placement, in_box=context.in_box)}">'
            + "".join(content_parts)
            + "</figure>"
        )

    def _subfigure_html(
        self,
        subfigure: SubFigure,
        index: int,
        group: SubFigureGroup,
        context: HtmlRenderContext,
    ) -> str:
        image_styles = []
        resolved_width = subfigure.width_in_inches(context.unit)
        resolved_height = subfigure.height_in_inches(context.unit)
        if resolved_width is not None:
            image_styles.append(f"width: {resolved_width:.2f}in")
            image_styles.append("max-width: 100%")
        if resolved_height is not None:
            image_styles.append(f"height: {resolved_height:.2f}in")
            image_styles.append("max-height: 100%")
        if resolved_width is None and resolved_height is not None:
            image_styles.append("width: auto")
        if resolved_height is None:
            image_styles.append("height: auto")
        image_style = f' style="{"; ".join(image_styles)};"' if image_styles else ""
        anchor = context.render_index.figure_anchor(subfigure)
        caption_html = ""
        container_anchor = f' id="{escape(anchor)}"' if anchor and subfigure.caption is None else ""
        if subfigure.caption is not None:
            anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
            caption_html = (
                f'<figcaption{anchor_attr} class="oodocs-caption oodocs-subfigure-caption" '
                f'style="text-align: {context.theme.captions.caption_text_alignment}; font-size: {context.theme.caption_size():.1f}pt;">'
                + self._inline_html(
                    self._subfigure_caption_fragments(
                        group.formatted_label_for_index(index),
                        subfigure.caption,
                    ),
                    context.theme,
                    context.render_index,
                    base_size=context.theme.caption_size(),
                )
                + "</figcaption>"
            )
        alt_text = self._figure_alt_text(subfigure, "Subfigure")
        return (
            f'<figure{container_anchor} class="oodocs-subfigure" style="margin: 0; text-align: {context.theme.blocks.figure_block_alignment};">'
            f'<img class="oodocs-figure-image" src="{self._figure_src(subfigure, context.unit)}" alt="{escape(alt_text)}"{image_style} />'
            + caption_html
            + "</figure>"
        )

    def render_subtable_group(self, block: SubTableGroup, context: HtmlRenderContext) -> str:
        """Render a subtable group into HTML.

        Args:
            block: Subtable group to render.
            context: Current HTML render context.

        Returns:
            HTML fragment for the grouped subtables and optional caption.
        """

        placement = block.resolved_placement()
        caption_html = (
            self._caption_html(
                block.caption,
                label=context.theme.resolve_caption_label("table", "caption"),
                number=context.render_index.table_number(block),
                anchor=context.render_index.table_anchor(block),
                context=context,
                kind="table",
            )
            if block.caption is not None
            else ""
        )
        subtables = "".join(
            self._subtable_html(subtable, index, block, context)
            for index, subtable in enumerate(block.subtables)
        )
        grid_style = (
            f"display: grid; grid-template-columns: repeat({block.columns}, minmax(0, 1fr)); "
            f"gap: {length_to_inches(block.column_gap, block.unit or context.unit):.2f}in;"
        )
        content_parts = []
        if block.caption is not None and context.theme.captions.table_caption_position == "above":
            content_parts.append(caption_html)
        content_parts.append(f'<div class="oodocs-subtable-grid" style="{grid_style}">{subtables}</div>')
        if block.caption is not None and context.theme.captions.table_caption_position == "below":
            content_parts.append(caption_html)
        return (
            '<div class="oodocs-table-wrapper oodocs-subtable-group '
            f'oodocs-placement-{placement}" '
            f'style="{self._table_wrapper_css(context.theme, in_box=context.in_box)} '
            f'{self._media_placement_css(placement, in_box=context.in_box)}">'
            + "".join(content_parts)
            + "</div>"
        )

    def _subtable_html(
        self,
        subtable: SubTable,
        index: int,
        group: SubTableGroup,
        context: HtmlRenderContext,
    ) -> str:
        anchor = context.render_index.table_anchor(subtable)
        caption_html = ""
        container_anchor = f' id="{escape(anchor)}"' if anchor and subtable.caption is None else ""
        if subtable.caption is not None:
            anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
            caption_html = (
                f'<div{anchor_attr} class="oodocs-caption oodocs-subtable-caption" '
                f'style="text-align: {context.theme.captions.caption_text_alignment}; '
                f'font-size: {context.theme.caption_size():.1f}pt;">'
                + self._inline_html(
                    self._subfigure_caption_fragments(
                        group.formatted_label_for_index(index),
                        subtable.caption,
                    ),
                    context.theme,
                    context.render_index,
                    base_size=context.theme.caption_size(),
                )
                + "</div>"
            )
        return (
            f'<div{container_anchor} class="oodocs-subtable" style="margin: 0;">'
            + self.render_table(subtable.table_without_caption(), context)
            + caption_html
            + "</div>"
        )

    def render_list_of_tables(
        self,
        block: ListOfTables,
        context: HtmlRenderContext,
    ) -> str:
        """Render the generated list of tables into HTML.

        Args:
            block: Generated table-list block.
            context: Current HTML render context.

        Returns:
            HTML fragment for the generated list of tables.
        """

        return self._render_caption_list(
            title=block.title,
            entries=context.render_index.scoped_tables(block),
            default_title=context.theme.resolve_generated_page_title("list_of_tables"),
            label=context.theme.resolve_caption_label("table", "caption"),
            context=context,
            section_class="oodocs-generated-page oodocs-table-list",
        )

    def render_list_of_figures(
        self,
        block: ListOfFigures,
        context: HtmlRenderContext,
    ) -> str:
        """Render the generated list of figures into HTML.

        Args:
            block: Generated figure-list block.
            context: Current HTML render context.

        Returns:
            HTML fragment for the generated list of figures.
        """

        return self._render_caption_list(
            title=block.title,
            entries=context.render_index.scoped_figures(block),
            default_title=context.theme.resolve_generated_page_title("list_of_figures"),
            label=context.theme.resolve_caption_label("figure", "caption"),
            context=context,
            section_class="oodocs-generated-page oodocs-figure-list",
        )

    def render_list_of_algorithms(
        self,
        block: ListOfAlgorithms,
        context: HtmlRenderContext,
    ) -> str:
        """Render the generated list of algorithms into HTML.

        Args:
            block: Generated algorithm-list block.
            context: Current HTML render context.

        Returns:
            HTML fragment for the generated list of algorithms.
        """

        return self._render_countable_list(
            title=block.title,
            entries=context.render_index.scoped_algorithms(block),
            default_title=context.theme.resolve_generated_page_title("list_of_algorithms"),
            context=context,
            section_class="oodocs-generated-page oodocs-algorithm-list",
        )

    def render_comment_list(
        self,
        block: CommentList,
        context: HtmlRenderContext,
    ) -> str:
        """Render the generated comments page into HTML.

        Args:
            block: Generated comments page block.
            context: Current HTML render context.

        Returns:
            HTML fragment for the generated comments page.
        """

        entries = "".join(
            (
                f'<p class="oodocs-generated-entry" id="comment_{entry.number}">'
                f'<span class="oodocs-generated-marker">[{entry.number}]</span> '
                + self._inline_html(
                    entry.comment.comment,
                    context.theme,
                    context.render_index,
                )
                + "</p>"
            )
            for entry in context.render_index.comments
        )
        return self._generated_page_html(
            title=block.title or [Text(context.theme.resolve_generated_page_title("comment_list"))],
            body=entries,
            context=context,
            section_class="oodocs-generated-page oodocs-comments-page",
        )

    def render_footnote_list(
        self,
        block: FootnoteList,
        context: HtmlRenderContext,
    ) -> str:
        """Render the generated footnotes page into HTML.

        Args:
            block: Generated footnotes page block.
            context: Current HTML render context.

        Returns:
            HTML fragment for the generated footnotes page.
        """

        entries = "".join(
            (
                f'<p class="oodocs-generated-entry" id="footnote_{entry.number}">'
                f'<span class="oodocs-generated-marker">[{entry.number}]</span> '
                + self._inline_html(
                    entry.footnote.note,
                    context.theme,
                    context.render_index,
                )
                + "</p>"
            )
            for entry in context.render_index.footnotes
        )
        return self._generated_page_html(
            title=block.title or [Text(context.theme.resolve_generated_page_title("footnote_list"))],
            body=entries,
            context=context,
            section_class="oodocs-generated-page oodocs-footnotes-page",
        )

    def render_reference_list(
        self,
        block: ReferenceList,
        context: HtmlRenderContext,
    ) -> str:
        """Render the generated references page into HTML.

        Args:
            block: Generated references page block.
            context: Current HTML render context.

        Returns:
            HTML fragment for the generated references page.
        """

        entries = "".join(
            (
                f'<p class="oodocs-generated-entry" id="{escape(entry.anchor)}">'
                + (
                    f'<span class="oodocs-generated-marker">{escape(marker)}</span> '
                    if (marker := reference_entry_marker(
                        entry.number,
                        citation_style=context.theme.citations.citation_style,
                        reference_style=context.theme.citations.reference_style,
                    ))
                    else ""
                )
                + self._inline_html(
                    entry.source.reference_fragments(context.theme.citations.reference_style),
                    context.theme,
                    context.render_index,
                )
                + "</p>"
            )
            for entry in context.render_index.citations
        )
        return self._generated_page_html(
            title=block.title or [Text(context.theme.resolve_generated_page_title("reference_list"))],
            body=entries,
            context=context,
            section_class="oodocs-generated-page oodocs-references-page",
        )

    def render_table_of_contents(
        self,
        block: TableOfContents,
        context: HtmlRenderContext,
    ) -> str:
        """Render the generated table of contents into HTML.

        Args:
            block: Generated table-of-contents block.
            context: Current HTML render context.

        Returns:
            HTML fragment for the generated table of contents.
        """

        entries = "".join(
            self._toc_entry_html(block, entry, context)
            for entry in context.render_index.scoped_headings(block)
        )
        return self._generated_page_html(
            title=block.title or [Text(context.theme.resolve_generated_page_title("table_of_contents"))],
            body='<nav class="oodocs-toc">' + entries + "</nav>",
            context=context,
            section_class="oodocs-generated-page oodocs-toc-page",
        )

    def _toc_entry_html(
        self,
        block: TableOfContents,
        entry: object,
        context: HtmlRenderContext,
    ) -> str:
        toc_style = self._toc_level_style(block, entry.level)
        label_html = self._link_html(
            entry.anchor,
            self._inline_html(
                self._heading_fragments(entry.title, entry.number),
                context.theme,
                context.render_index,
            ),
            internal=True,
        )
        styles = [
            f"margin-left: {toc_style.indent:.2f}in",
            f"margin-top: {toc_style.space_before:.1f}pt",
            f"margin-bottom: {toc_style.space_after:.1f}pt",
            f"font-size: {context.theme.typography.body_font_size + toc_style.font_size_delta:.1f}pt",
            f"font-weight: {'700' if toc_style.bold else '400'}",
            f"font-style: {'italic' if toc_style.italic else 'normal'}",
        ]
        return (
            f'<div class="oodocs-toc-entry oodocs-toc-entry-no-page oodocs-toc-entry-level-{entry.level}" '
            f'style="{"; ".join(styles)};">'
            f'<span class="oodocs-toc-label">{label_html}</span>'
            + "</div>"
        )

    def _render_children(
        self,
        children: list[object],
        context: HtmlRenderContext,
    ) -> str:
        return "".join(child.render_to_html(self, context) for child in children)

    def _multi_column_group_html(
        self,
        block: MultiColumn,
        children: list[object],
        context: HtmlRenderContext,
    ) -> str:
        style = (
            f"column-count: {block.columns}; "
            f"column-gap: {block.column_gap_in_inches(context.unit):.2f}in;"
        )
        return (
            f'<div class="oodocs-multi-column-group" style="{style}">'
            + self._render_children(children, context)
            + "</div>"
        )

    def _should_auto_render_footnote_list(
        self,
        document: Document,
        render_index: RenderIndex,
    ) -> bool:
        return (
            document.settings.theme.blocks.auto_footnotes_page
            and bool(render_index.footnotes)
            and not any(isinstance(child, FootnoteList) for child in document.body.children)
        )

    def _render_title_matter(
        self,
        document: Document,
        context: HtmlRenderContext,
        *,
        page_break_after: bool,
    ) -> str:
        settings = document.settings
        classes = ["oodocs-title-matter"]
        if settings.cover_page:
            classes.append("oodocs-cover-page")
        if page_break_after:
            classes.append("oodocs-page-break-after")

        lines = [
            self._title_line_html(
                [Text(document.title)],
                font_size=context.theme.typography.title_font_size,
                alignment=context.theme.title_matter.title_text_alignment,
                bold=True,
                class_name="oodocs-title",
                theme=context.theme,
            )
        ]
        if settings.subtitle is not None:
            lines.append(
                self._title_line_html(
                    settings.subtitle,
                    font_size=max(context.theme.typography.body_font_size + 1, 12),
                    alignment=context.theme.title_matter.subtitle_text_alignment,
                    italic=True,
                    class_name="oodocs-subtitle",
                    theme=context.theme,
                    space_after=10,
                )
            )
        author_lines = list(document.settings.iter_author_title_lines())
        for index, (line, _is_last_for_author) in enumerate(author_lines):
            lines.append(
                self._title_line_html(
                    list(line.fragments),
                    font_size=self._title_line_font_size(line, context.theme),
                    alignment=self._title_line_alignment(line, context.theme),
                    italic=line.kind == "affiliation",
                    class_name=self._title_line_class(line),
                    theme=context.theme,
                    space_after=self._author_title_line_space_after(author_lines, index, last_space=10),
                )
            )
        return f'<header class="{" ".join(classes)}">{"".join(lines)}</header>'

    def _title_line_html(
        self,
        fragments: list[Text],
        *,
        font_size: float,
        alignment: str,
        class_name: str,
        theme: Theme,
        bold: bool = False,
        italic: bool = False,
        space_after: float = 0,
    ) -> str:
        tag = "h1" if class_name == "oodocs-title" else "p"
        return (
            f'<{tag} class="{class_name}" style="text-align: {alignment}; font-size: {font_size:.1f}pt; margin: 0 0 {space_after:.1f}pt;">'
            + self._inline_html(
                fragments,
                theme,
                RenderIndex(),
                base_bold=bold,
                base_italic=italic,
                base_size=font_size,
            )
            + f"</{tag}>"
        )

    def _title_line_alignment(self, line: AuthorTitleLine, theme: Theme) -> str:
        if line.kind == "name":
            return theme.title_matter.author_text_alignment
        if line.kind == "affiliation":
            return theme.title_matter.affiliation_text_alignment
        return theme.title_matter.author_detail_text_alignment

    def _title_line_font_size(self, line: AuthorTitleLine, theme: Theme) -> float:
        if line.kind == "name":
            return theme.typography.body_font_size
        if line.kind == "affiliation":
            return max(theme.typography.body_font_size - 0.5, 9)
        return max(theme.typography.body_font_size - 1, 9)

    def _author_title_line_space_after(
        self,
        lines: list[tuple[AuthorTitleLine, bool]],
        index: int,
        *,
        last_space: float,
    ) -> float:
        line, is_last = lines[index]
        if is_last:
            return last_space
        next_line = lines[index + 1][0] if index + 1 < len(lines) else None
        if line.kind == "name":
            return 8
        if line.kind == "affiliation" and next_line is not None and next_line.kind == "detail":
            return 7
        return 3

    def _title_line_class(self, line: AuthorTitleLine) -> str:
        if line.kind == "name":
            return "oodocs-author"
        if line.kind == "affiliation":
            return "oodocs-affiliation"
        return "oodocs-author-detail"

    def _render_caption_list(
        self,
        *,
        title: list[Text] | None,
        entries: list[object],
        default_title: str,
        label: str,
        context: HtmlRenderContext,
        section_class: str,
    ) -> str:
        items = "".join(
            (
                '<div class="oodocs-caption-list-entry">'
                + self._link_html(
                    entry.anchor,
                    self._inline_html(
                        self._caption_fragments(
                            label,
                            entry.number,
                            entry.block.caption,
                        ),
                        context.theme,
                        context.render_index,
                    ),
                    internal=True,
                )
                + "</div>"
            )
            for entry in entries
        )
        return self._generated_page_html(
            title=title or [Text(default_title)],
            body=items,
            context=context,
            section_class=section_class,
        )

    def _render_countable_list(
        self,
        *,
        title: list[Text] | None,
        entries: list[object],
        default_title: str,
        context: HtmlRenderContext,
        section_class: str,
    ) -> str:
        items = "".join(
            (
                '<div class="oodocs-caption-list-entry">'
                + self._link_html(
                    entry.anchor,
                    self._inline_html(
                        _countable_entry_fragments(entry),
                        context.theme,
                        context.render_index,
                    ),
                    internal=True,
                )
                + "</div>"
            )
            for entry in entries
        )
        return self._generated_page_html(
            title=title or [Text(default_title)],
            body=items,
            context=context,
            section_class=section_class,
        )

    def _generated_page_html(
        self,
        *,
        title: list[Text],
        body: str,
        context: HtmlRenderContext,
        section_class: str,
    ) -> str:
        level = context.theme.generated_content.generated_heading_level
        heading_tag = self._heading_tag(level)
        heading_html = (
            f"<{heading_tag} class=\"oodocs-generated-title\" style=\"{self._heading_css(level, context.theme)}\">"
            + self._inline_html(
                title,
                context.theme,
                context.render_index,
                base_bold=context.theme.resolve_heading_emphasis(level)[0],
                base_italic=context.theme.resolve_heading_emphasis(level)[1],
                base_size=context.theme.resolve_heading_size(level),
            )
            + f"</{heading_tag}>"
        )
        return f'<section class="{section_class}">{heading_html}{body}</section>'

    def _table_section_html(
        self,
        layout: object,
        *,
        header: bool,
        block: Table,
        context: HtmlRenderContext,
        table_style: TableStyle,
    ) -> str:
        rows: dict[int, list[TablePlacement]] = {}
        for placement in layout.placements:
            if placement.header != header:
                continue
            rows.setdefault(placement.row, []).append(placement)
        html_rows: list[str] = []
        tag = "th" if header else "td"
        for row_index in sorted(rows):
            cells = []
            for placement in sorted(rows[row_index], key=lambda value: value.column):
                cells.append(
                    self._table_cell_html(
                        placement,
                        tag,
                        block,
                        context,
                        table_style,
                        layout=layout,
                    )
                )
            html_rows.append("<tr>" + "".join(cells) + "</tr>")
        return "".join(html_rows)

    def _table_cell_html(
        self,
        placement: TablePlacement,
        tag: str,
        block: Table,
        context: HtmlRenderContext,
        table_style: TableStyle,
        layout: object,
    ) -> str:
        style_parts = []
        style_parts.extend(
            self._table_border_css(
                table_style._border_edges(
                    row=placement.row,
                    rowspan=placement.cell.rowspan,
                    row_count=layout.row_count,
                    header_row_count=layout.header_row_count,
                )
            )
        )
        top_padding, right_padding, bottom_padding, left_padding = table_style.cell_padding.to_points()
        style_parts.append(
            f"padding: {top_padding:.1f}pt {right_padding:.1f}pt {bottom_padding:.1f}pt {left_padding:.1f}pt"
        )
        effective_style = block._effective_cell_style(
            placement,
            stylesheet=context.stylesheet,
            table_style=table_style,
        )
        text_alignment = self._table_cell_text_alignment(
            placement,
            block,
            context.stylesheet,
            table_style,
        ) or "left"
        vertical_alignment = self._table_cell_vertical_alignment(
            placement,
            block,
            context.stylesheet,
            table_style,
        )
        style_parts.append(f"text-align: {text_alignment}")
        style_parts.append(
            f"vertical-align: {vertical_alignment}" if vertical_alignment is not None else "vertical-align: top"
        )
        if effective_style.background_color is not None:
            style_parts.append(f"background: #{effective_style.background_color}")
        if effective_style.text_color is not None:
            style_parts.append(f"color: #{effective_style.text_color}")
        if effective_style.bold is not None:
            style_parts.append(f"font-weight: {'700' if effective_style.bold else '400'}")
        if effective_style.italic is not None:
            style_parts.append(f"font-style: {'italic' if effective_style.italic else 'normal'}")
        if not block._column_wrap_enabled(placement.column):
            style_parts.append("white-space: nowrap")
        attrs = []
        if placement.cell.colspan > 1:
            attrs.append(f' colspan="{placement.cell.colspan}"')
        if placement.cell.rowspan > 1:
            attrs.append(f' rowspan="{placement.cell.rowspan}"')
        cell_paragraph_style = context.stylesheet.resolve(
            "paragraph",
            placement.cell.content.style,
            ParagraphStyle(),
        )
        paragraph_html = (
            '<p class="oodocs-paragraph" '
            f'style="{self._paragraph_style_css(cell_paragraph_style, context.theme, default_unit=context.unit, alignment=text_alignment)}">'
            + self._inline_html(
                placement.cell.content.content,
                context.theme,
                context.render_index,
                base_bold=bool(effective_style.bold),
                base_italic=bool(effective_style.italic),
            )
            + "</p>"
        )
        return (
            f"<{tag}{''.join(attrs)} style=\"{'; '.join(style_parts)}\">"
            + paragraph_html
            + f"</{tag}>"
        )

    def _table_border_css(self, edges: dict[str, object]) -> list[str]:
        default = edges["top"]
        if all(edges[edge_name] == default for edge_name in ("right", "bottom", "left")):
            if default.color is not None and default.width > 0:
                return [f"border: {default.width_points():.2f}pt solid #{default.color}"]
            return ["border: none"]

        styles = ["border: none"]
        for edge_name in ("top", "right", "bottom", "left"):
            border = edges[edge_name]
            if border.color is not None and border.width > 0:
                styles.append(
                    f"border-{edge_name}: {border.width_points():.2f}pt solid #{border.color}"
                )
        return styles

    def _table_cell_text_alignment(
        self,
        placement: TablePlacement,
        block: Table,
        stylesheet: object | None = None,
        table_style: TableStyle | None = None,
    ) -> str | None:
        return block._effective_cell_style(
            placement,
            stylesheet=stylesheet,
            table_style=table_style,
        ).text_alignment

    def _table_cell_vertical_alignment(
        self,
        placement: TablePlacement,
        block: Table,
        stylesheet: object | None = None,
        table_style: TableStyle | None = None,
    ) -> str | None:
        return block._effective_cell_style(
            placement,
            stylesheet=stylesheet,
            table_style=table_style,
        ).vertical_alignment

    def _caption_html(
        self,
        caption: Paragraph | None,
        *,
        label: str,
        number: int | None,
        anchor: str | None,
        context: HtmlRenderContext,
        kind: str,
    ) -> str:
        if caption is None:
            return ""
        tag = "figcaption" if kind == "figure" else "div"
        anchor_attr = f' id="{escape(anchor)}"' if anchor else ""
        return (
            f"<{tag}{anchor_attr} class=\"oodocs-caption oodocs-{kind}-caption\" "
            f'style="text-align: {context.theme.captions.caption_text_alignment}; font-size: {context.theme.caption_size():.1f}pt;">'
            + self._inline_html(
                self._caption_fragments(label, number, caption),
                context.theme,
                context.render_index,
                base_size=context.theme.caption_size(),
            )
            + f"</{tag}>"
        )

    def _inline_html(
        self,
        fragments: list[Text],
        theme: Theme,
        render_index: RenderIndex,
        *,
        base_bold: bool = False,
        base_italic: bool = False,
        base_size: float | None = None,
    ) -> str:
        return "".join(
            self._fragment_html(
                fragment,
                theme,
                render_index,
                base_bold=base_bold,
                base_italic=base_italic,
                base_size=base_size,
            )
            for fragment in fragments
        ) or "&nbsp;"

    def _page_items_html(self, document: Document, context: HtmlRenderContext) -> str:
        if not document.settings.page_items:
            return ""
        return (
            '<div class="oodocs-page-items" aria-hidden="true">'
            + "".join(
                self._positioned_item_html(box, context)
                for box in resolve_positioned_boxes(
                    document.settings.page_items,
                    document.settings,
                    context.unit,
                )
            )
            + "</div>"
        )

    def _inline_or_page_box(
        self,
        item: PositionedItem,
        context: HtmlRenderContext,
    ) -> PositionedBox:
        if item.placement == "inline":
            return PositionedBox(
                item=item,
                x=0.0,
                y=0.0,
                width=length_to_inches(item.width, item.unit or context.unit),
                height=length_to_inches(item.height, item.unit or context.unit),
            )
        return resolve_positioned_boxes([item], context.settings, context.unit)[0]

    def _positioned_item_html(
        self,
        box: PositionedBox,
        context: HtmlRenderContext,
    ) -> str:
        if isinstance(box.item, TextBox):
            return self._text_box_html(box.item, box, context)
        if isinstance(box.item, ImageBox):
            return self._image_box_html(box.item, box)
        return self._shape_html(box.item, box)

    def _position_css(self, box: PositionedBox) -> str:
        if box.item.placement == "inline":
            return (
                "position: relative; display: inline-block; "
                f"width: {box.width:.4f}in; height: {box.height:.4f}in; "
                "vertical-align: middle; box-sizing: border-box;"
            )
        return (
            f"position: absolute; left: {box.x:.4f}in; top: {box.y:.4f}in; "
            f"width: {box.width:.4f}in; height: {box.height:.4f}in; "
            f"z-index: {box.item.z_index}; box-sizing: border-box;"
        )

    def _text_box_html(
        self,
        item: TextBox,
        box: PositionedBox,
        context: HtmlRenderContext,
    ) -> str:
        align_items = {"top": "flex-start", "middle": "center", "bottom": "flex-end"}[
            item.vertical_alignment
        ]
        font_size = item.font_size or context.theme.typography.body_font_size
        return (
            '<div class="oodocs-page-item oodocs-textbox" '
            f'style="{self._position_css(box)} '
            f'display: flex; align-items: {align_items}; justify-content: stretch; text-align: {item.text_alignment}; '
            f'font-size: {font_size:.1f}pt; line-height: {font_size * 1.22:.1f}pt; box-sizing: border-box;">'
            '<div style="width: 100%;">'
            + self._inline_html(
                item.content,
                context.theme,
                context.render_index,
                base_size=font_size,
            )
            + "</div></div>"
        )

    def _shape_html(
        self,
        item: Shape,
        box: PositionedBox,
    ) -> str:
        stroke = f"#{item.stroke.color}" if item.stroke.color is not None else "transparent"
        stroke_points = item.stroke.width_points() if item.stroke.width > 0 else 0.0
        fill = f"#{item.fill_color}" if item.fill_color is not None else "transparent"
        if item.kind == "line":
            return (
                '<svg class="oodocs-page-item oodocs-shape" '
                f'style="{self._position_css(box)} overflow: visible;">'
                f'<line x1="0" y1="0" x2="{box.width:.4f}in" y2="{box.height:.4f}in" stroke="{stroke}" stroke-width="{stroke_points:.2f}pt" />'
                "</svg>"
            )
        border_radius = "50%" if item.kind == "ellipse" else "0"
        return (
            '<div class="oodocs-page-item oodocs-shape" '
            f'style="{self._position_css(box)} '
            f'border: {stroke_points:.2f}pt solid {stroke}; background: {fill}; border-radius: {border_radius}; box-sizing: border-box;"></div>'
        )

    def _image_box_html(
        self,
        item: ImageBox,
        box: PositionedBox,
    ) -> str:
        object_fit = "fill" if item.fit == "stretch" else "contain"
        return (
            '<img class="oodocs-page-item oodocs-imagebox" '
            f'src="{self._image_box_src(item)}" alt="" '
            f'style="{self._position_css(box)} '
            f'object-fit: {object_fit}; object-position: center; box-sizing: border-box;" />'
        )

    def _image_box_src(self, image_box: ImageBox) -> str:
        source = image_box.image_source
        if isinstance(source, Path):
            image_bytes = source.read_bytes()
            mime_type = guess_type(source.name)[0] or self._mime_type_for_format(
                source.suffix.lstrip(".") or image_box.image_format
            )
        else:
            image_bytes = image_source_to_bytes(
                source,
                image_format=image_box.image_format,
                image_dpi=image_box.image_dpi,
                usage="HTML positioned image rendering",
            )
            mime_type = self._mime_type_for_format(image_box.image_format)
        return f"data:{mime_type};base64,{b64encode(image_bytes).decode('ascii')}"

    def _fragment_html(
        self,
        fragment: Text,
        theme: Theme,
        render_index: RenderIndex,
        *,
        base_bold: bool,
        base_italic: bool,
        base_size: float | None,
    ) -> str:
        if isinstance(fragment, (ImageBox, Shape, TextBox)):
            fragment_unit = fragment.unit or "in"
            inline_box = PositionedBox(
                item=fragment,
                x=0.0,
                y=0.0,
                width=length_to_inches(fragment.width, fragment_unit),
                height=length_to_inches(fragment.height, fragment_unit),
            )
            return self._positioned_item_html(
                inline_box,
                HtmlRenderContext(
                    theme=theme,
                    render_index=render_index,
                    settings=object(),
                    unit=fragment_unit,
                ),
            )
        if isinstance(fragment, Hyperlink):
            return self._link_html(
                fragment.target,
                self._inline_html(
                    fragment.label,
                    theme,
                    render_index,
                    base_size=base_size,
                ),
                internal=fragment.internal,
            )
        if isinstance(fragment, InlineChip):
            return self._inline_chip_html(
                fragment,
                theme,
                base_size=base_size,
            )
        if isinstance(fragment, _BlockReference):
            label_html = (
                self._inline_html(
                    fragment.label,
                    theme,
                    render_index,
                    base_bold=base_bold,
                    base_italic=base_italic,
                    base_size=base_size,
                )
                if fragment.label is not None
                else self._styled_text_html(
                    self._resolve_block_reference(fragment.target, theme, render_index),
                    fragment,
                    theme,
                    base_bold=base_bold,
                    base_italic=base_italic,
                    base_size=base_size,
                )
            )
            return self._link_html(
                self._block_reference_anchor(fragment.target, render_index),
                label_html,
                internal=True,
            )
        if isinstance(fragment, Citation):
            citation_entry = render_index.citation_entry(fragment.target)
            citation_label = format_citation_label(
                citation_entry.source,
                citation_entry.number,
                theme.citations.citation_style,
            )
            return self._link_html(
                citation_entry.anchor,
                self._styled_text_html(
                    citation_label,
                    fragment,
                    theme,
                    base_bold=base_bold,
                    base_italic=base_italic,
                    base_size=base_size,
                ),
                internal=True,
            )
        if isinstance(fragment, Comment):
            comment_number = render_index.comment_number(fragment)
            visible = self._styled_text_html(
                fragment.value,
                fragment,
                theme,
                base_bold=base_bold,
                base_italic=base_italic,
                base_size=base_size,
            )
            marker = self._link_html(
                f"comment_{comment_number}",
                f"[{comment_number}]",
                internal=True,
            )
            return f"{visible}<sup>{marker}</sup>"
        if isinstance(fragment, Footnote):
            footnote_number = render_index.footnote_number(fragment)
            visible = self._styled_text_html(
                fragment.value,
                fragment,
                theme,
                base_bold=base_bold,
                base_italic=base_italic,
                base_size=base_size,
            )
            marker = self._link_html(
                f"footnote_{footnote_number}",
                str(footnote_number),
                internal=True,
            )
            return f"{visible}<sup>{marker}</sup>"
        if isinstance(fragment, Math):
            return self._math_html(
                fragment,
                theme,
                base_bold=base_bold,
                base_italic=base_italic,
                base_size=base_size,
            )
        return self._styled_text_html(
            self._resolve_fragment_text(fragment, theme, render_index),
            fragment,
            theme,
            base_bold=base_bold,
            base_italic=base_italic,
            base_size=base_size,
        )

    def _inline_chip_html(
        self,
        fragment: InlineChip,
        theme: Theme,
        *,
        base_size: float | None,
    ) -> str:
        chip_style = theme.stylesheet.resolve("chip", fragment.chip_style, None)
        text = escape(fragment.display_text(chip_style)).replace("\n", " ")
        base_size = fragment.style.font_size or base_size or theme.typography.body_font_size
        font_size = max(base_size + chip_style.font_size_delta, 6.0)
        top_padding, right_padding, bottom_padding, left_padding = chip_style.padding.as_tuple()
        if chip_style.padding.unit == "em":
            padding_css = (
                f"{top_padding:.2f}em {right_padding:.2f}em "
                f"{bottom_padding:.2f}em {left_padding:.2f}em"
            )
        else:
            top_pt, right_pt, bottom_pt, left_pt = chip_style.padding.to_points()
            padding_css = (
                f"{top_pt:.2f}pt {right_pt:.2f}pt "
                f"{bottom_pt:.2f}pt {left_pt:.2f}pt"
            )
        if chip_style.border.radius_unit == "em":
            border_radius_css = f"{chip_style.border.radius_em():.2f}em"
        else:
            border_radius_css = f"{chip_style.border.radius_points():.2f}pt"
        styles = [
            "display: inline-block",
            f"padding: {padding_css}",
            f"border-radius: {border_radius_css}",
            f"background-color: #{chip_style.background_color}",
            f"color: #{chip_style.text_color}",
            f"font-size: {font_size:.1f}pt",
            f"font-weight: {'700' if chip_style.bold else '400'}",
            f"font-style: {'italic' if chip_style.italic else 'normal'}",
            "line-height: 1",
            "vertical-align: baseline",
            "white-space: nowrap",
            "box-decoration-break: clone",
        ]
        font_name = chip_style.font_name or fragment.style.font_name
        if font_name is not None:
            styles.append(f"font-family: {self._css_font_family(font_name)}")
        if chip_style.border.color is not None and chip_style.border.width > 0:
            styles.append(
                f"border: {chip_style.border.width_points():.1f}pt solid #{chip_style.border.color}"
            )
        class_attr = self._html_class_attr(
            "oodocs-inline-chip",
            f"oodocs-inline-chip-{fragment.kind}",
            chip_style.css_class,
        )
        return f'<span{class_attr} style="{"; ".join(styles)}">{text}</span>'

    def _styled_text_html(
        self,
        text_value: str,
        fragment: Text,
        theme: Theme,
        *,
        base_bold: bool = False,
        base_italic: bool = False,
        base_size: float | None = None,
    ) -> str:
        rendered_text = text_value.upper() if fragment.style.uppercase else text_value
        text = escape(rendered_text).replace("\n", "<br/>")
        styles: list[str] = []
        effective_bold = base_bold if fragment.style.bold is None else fragment.style.bold
        effective_italic = base_italic if fragment.style.italic is None else fragment.style.italic
        if fragment.style.font_name is not None:
            styles.append(f"font-family: {self._css_font_family(fragment.style.font_name)}")
        if fragment.style.font_size is not None and fragment.style.font_size != base_size:
            styles.append(f"font-size: {fragment.style.font_size:.1f}pt")
        if effective_bold != base_bold:
            styles.append(f"font-weight: {'700' if effective_bold else '400'}")
        if effective_italic != base_italic:
            styles.append(f"font-style: {'italic' if effective_italic else 'normal'}")
        decorations: list[str] = []
        if fragment.style.underline:
            decorations.append("underline")
        if fragment.style.strikethrough:
            decorations.append("line-through")
        if decorations:
            styles.append(f"text-decoration: {' '.join(decorations)}")
        if fragment.style.text_color is not None:
            styles.append(f"color: #{fragment.style.text_color}")
        if fragment.style.highlight_color is not None:
            styles.append(f"background-color: #{fragment.style.highlight_color}")
        if fragment.style.small_caps:
            styles.append("font-variant: small-caps")
        if fragment.style.uppercase:
            styles.append("text-transform: uppercase")
        if fragment.style.superscript:
            styles.append("vertical-align: super")
            styles.append("font-size: 75%")
        if fragment.style.subscript:
            styles.append("vertical-align: sub")
            styles.append("font-size: 75%")
        if not styles:
            return text
        return f'<span style="{"; ".join(styles)}">{text}</span>'

    def _math_html(
        self,
        fragment: Math,
        theme: Theme,
        *,
        base_bold: bool = False,
        base_italic: bool = False,
        base_size: float | None = None,
    ) -> str:
        parts: list[str] = []
        for segment in parse_latex_segments(fragment.value):
            piece = self._styled_text_html(
                segment.text,
                fragment,
                theme,
                base_bold=base_bold,
                base_italic=base_italic,
                base_size=base_size,
            )
            if segment.vertical_align == SUPERSCRIPT:
                piece = f"<sup>{piece}</sup>"
            elif segment.vertical_align == SUBSCRIPT:
                piece = f"<sub>{piece}</sub>"
            parts.append(piece)
        return '<span class="oodocs-math">' + ("".join(parts) or "&nbsp;") + "</span>"

    def _resolve_fragment_text(
        self,
        fragment: Text,
        theme: Theme,
        render_index: RenderIndex,
    ) -> str:
        if isinstance(fragment, _BlockReference):
            if fragment.label is not None:
                return "".join(item.plain_text() for item in fragment.label)
            return self._resolve_block_reference(fragment.target, theme, render_index)
        if isinstance(fragment, Citation):
            citation_entry = render_index.citation_entry(fragment.target)
            return format_citation_label(
                citation_entry.source,
                citation_entry.number,
                theme.citations.citation_style,
            )
        if isinstance(fragment, Hyperlink):
            return fragment.plain_text()
        if isinstance(fragment, Comment):
            return fragment.value
        if isinstance(fragment, Footnote):
            return fragment.value
        if isinstance(fragment, Math):
            return fragment.plain_text()
        return fragment.value

    def _resolve_block_reference(
        self,
        target: object,
        theme: Theme,
        render_index: RenderIndex,
    ) -> str:
        if isinstance(target, (Table, SubTable, SubTableGroup)):
            number = render_index.table_number(target)
            if number is None:
                raise OODocsError(
                    "Table references require the target table to have a caption and be included in the document"
                )
            label = theme.resolve_caption_label("table", "reference")
            if isinstance(target, SubTable):
                subtable_label = render_index.subtable_reference_label(target)
                if subtable_label is None:
                    raise OODocsError(
                        "Subtable references require the target subtable to belong to a captioned SubTableGroup"
                    )
                return f"{label} {number}{subtable_label}"
            return f"{label} {number}"

        if isinstance(target, (Figure, SubFigure, SubFigureGroup)):
            number = render_index.figure_number(target)
            if number is None:
                raise OODocsError(
                    "Figure references require the target figure to have a caption and be included in the document"
                )
            if isinstance(target, SubFigure):
                label = render_index.subfigure_label(target)
                if label is None:
                    raise OODocsError(
                        "Subfigure references require the target subfigure to belong to a captioned SubFigureGroup"
                    )
                figure_label = theme.resolve_caption_label("figure", "reference")
                reference_label = render_index.subfigure_reference_label(target)
                return f"{figure_label} {number}{reference_label or f'({label})'}"
            label = theme.resolve_caption_label("figure", "reference")
            return f"{label} {number}"

        if isinstance(target, Part):
            number_label = render_index.heading_number(target)
            if number_label is None:
                raise OODocsError("Part references require the target part to be numbered and included in the document")
            return number_label

        if isinstance(target, Section):
            number_label = render_index.heading_number(target)
            if number_label is None:
                raise OODocsError("Section references require the target section to be numbered and included in the document")
            prefix = "Chapter" if target.level == 1 else "Section"
            return f"{prefix} {number_label}"

        if isinstance(target, Equation):
            number = render_index.equation_number(target)
            if number is None:
                raise OODocsError(
                    "Equation references require the target equation to be numbered and included in the document, "
                    "or the reference must provide a custom label"
                )
            return target.reference_text(number)

        if isinstance(target, Paragraph):
            number = render_index.paragraph_number(target)
            if number is None:
                raise OODocsError("Paragraph references require the target paragraph to be included in the document")
            return f"Paragraph {number}"

        if isinstance(target, CodeBlock):
            number = render_index.code_block_number(target)
            if number is None:
                raise OODocsError("Code block references require the target code block to be included in the document")
            return f"Code block {number}"

        if isinstance(target, Box):
            number = render_index.box_number(target)
            if number is None:
                raise OODocsError("Box references require the target box to be included in the document")
            return f"Box {number}"

        if isinstance(target, CountableBlock):
            number = render_index.countable_number(target)
            if number is None:
                raise OODocsError(
                    "CountableBlock references require the target to be numbered and included in the document, "
                    "or the reference must provide a custom label"
                )
            return target.reference_text(number)

        raise OODocsError(f"Unsupported reference target: {type(target)!r}")

    def _block_reference_anchor(
        self,
        target: object,
        render_index: RenderIndex,
    ) -> str | None:
        if isinstance(target, (Table, SubTable, SubTableGroup)):
            return render_index.table_anchor(target)
        if isinstance(target, (Figure, SubFigure, SubFigureGroup)):
            return render_index.figure_anchor(target)
        if isinstance(target, (Part, Section)):
            return render_index.heading_anchor(target)
        return render_index.block_anchor(target)

    def _figure_src(self, figure: Figure | SubFigure, default_unit: str = "in") -> str:
        source = figure.image_source
        if figure.crop is not None or figure.rotation:
            buffer = processed_image_source_to_buffer(
                source,
                image_format=figure.image_format,
                image_dpi=figure.image_dpi,
                crop=figure.crop,
                rotation=figure.rotation,
                default_unit=figure.unit or default_unit,
                usage="HTML rendering",
            )
            image_bytes = buffer.getvalue()
            mime_type = self._mime_type_for_format(figure.image_format)
        elif isinstance(source, Path):
            image_bytes = source.read_bytes()
            mime_type = guess_type(source.name)[0] or self._mime_type_for_format(
                source.suffix.lstrip(".") or figure.image_format
            )
        else:
            image_bytes = image_source_to_bytes(
                source,
                image_format=figure.image_format,
                image_dpi=figure.image_dpi,
                usage="HTML rendering",
            )
            mime_type = self._mime_type_for_format(figure.image_format)
        return f"data:{mime_type};base64,{b64encode(image_bytes).decode('ascii')}"

    def _figure_alt_text(self, figure: Figure | SubFigure, fallback: str) -> str:
        if figure.alt_text is not None:
            return figure.alt_text
        if figure.caption is not None:
            return figure.caption.plain_text()
        return fallback

    def _mime_type_for_format(self, image_format: str) -> str:
        normalized = image_format.strip().lower()
        if normalized in {"jpg", "jpeg"}:
            return "image/jpeg"
        if normalized == "svg":
            return "image/svg+xml"
        return f"image/{normalized or 'png'}"

    def _caption_fragments(
        self,
        label: str,
        number: int | None,
        caption: Paragraph,
    ) -> list[Text]:
        if number is None:
            return caption.content
        return [Text(f"{label} {number}. ")] + caption.content

    def _subfigure_caption_fragments(self, label: str, caption: Paragraph) -> list[Text]:
        return [Text(f"{label} ")] + caption.content

    def _heading_fragments(
        self,
        title: list[Text],
        number_label: str | None,
    ) -> list[Text]:
        if not number_label:
            return title
        return [Text(f"{number_label} ")] + title

    def _heading_tag(self, level: int) -> str:
        return f"h{min(level + 1, 6)}"

    def _heading_css(
        self,
        level: int,
        theme: Theme,
        override: HeadingStyle | None = None,
    ) -> str:
        heading_style = theme.resolve_heading_style(level, override)
        heading_text_style = heading_style.text_style
        bold = bool(heading_text_style.bold)
        italic = bool(heading_text_style.italic)
        font_size = heading_text_style.font_size or theme.resolve_heading_size(level)
        space_before = heading_style.space_before if heading_style.space_before is not None else 0
        space_after = heading_style.space_after if heading_style.space_after is not None else 0
        styles = [
            f"font-size: {font_size:.1f}pt",
            f"text-align: {heading_style.text_alignment or 'left'}",
            f"margin: {space_before:.1f}pt 0 {space_after:.1f}pt",
        ]
        if heading_style.leading is not None:
            styles.append(f"line-height: {heading_style.leading:.1f}pt")
        styles.append(f"font-weight: {'700' if bold else '400'}")
        if italic:
            styles.append("font-style: italic")
        if heading_text_style.font_name is not None:
            styles.append(f"font-family: {self._css_font_family(heading_text_style.font_name)}")
        if heading_text_style.text_color is not None:
            styles.append(f"color: #{heading_text_style.text_color}")
        if heading_text_style.highlight_color is not None:
            styles.append(f"background-color: #{heading_text_style.highlight_color}")
        decorations = []
        if heading_text_style.underline:
            decorations.append("underline")
        if heading_text_style.strikethrough:
            decorations.append("line-through")
        if decorations:
            styles.append(f"text-decoration: {' '.join(decorations)}")
        if heading_text_style.small_caps:
            styles.append("font-variant: small-caps")
        if heading_text_style.uppercase:
            styles.append("text-transform: uppercase")
        return "; ".join(styles)

    def _toc_level_style(self, block: TableOfContents, level: int) -> TocLevelStyle:
        if level == 0:
            defaults = TocLevelStyle(
                indent=0,
                space_before=16,
                space_after=8,
                font_size_delta=1.2,
                bold=True,
                italic=False,
            )
            override = block.style_for_level(level)
            return TocLevelStyle(
                indent=defaults.indent if override.indent is None else override.indent,
                space_before=defaults.space_before if override.space_before is None else override.space_before,
                space_after=defaults.space_after if override.space_after is None else override.space_after,
                font_size_delta=defaults.font_size_delta if override.font_size_delta is None else override.font_size_delta,
                bold=defaults.bold if override.bold is None else override.bold,
                italic=defaults.italic if override.italic is None else override.italic,
            )
        defaults = TocLevelStyle(
            indent=0.24 * max(level - 1, 0),
            space_before=12 if level == 1 else (3 if level == 2 else 0),
            space_after=7 if level == 1 else (3 if level == 2 else 2),
            font_size_delta=0.6 if level == 1 else 0,
            bold=True if level == 1 else False,
            italic=False,
        )
        override = block.style_for_level(level)
        return TocLevelStyle(
            indent=defaults.indent if override.indent is None else override.indent,
            space_before=defaults.space_before if override.space_before is None else override.space_before,
            space_after=defaults.space_after if override.space_after is None else override.space_after,
            font_size_delta=defaults.font_size_delta if override.font_size_delta is None else override.font_size_delta,
            bold=defaults.bold if override.bold is None else override.bold,
            italic=defaults.italic if override.italic is None else override.italic,
        )

    def _paragraph_style_css(
        self,
        style: ParagraphStyle,
        theme: Theme,
        *,
        default_space_after: float | None = None,
        default_unit: str = "in",
        alignment: str | None = None,
    ) -> str:
        space_before = style.space_before or 0
        space_after = style.space_after
        if space_after is None:
            space_after = default_space_after if default_space_after is not None else 0
        line_height = style.leading or theme.typography.body_font_size * 1.35
        left_indent_value = style.left_indent_in_inches(default_unit)
        right_indent_value = style.right_indent_in_inches(default_unit)
        first_line_indent_value = style.first_line_indent_in_inches(default_unit)
        left_indent = (
            f" margin-left: {left_indent_value:.2f}in;"
            if left_indent_value is not None
            else ""
        )
        right_indent = (
            f" margin-right: {right_indent_value:.2f}in;"
            if right_indent_value is not None
            else ""
        )
        first_line_indent = (
            f" text-indent: {first_line_indent_value:.2f}in;"
            if first_line_indent_value is not None
            else ""
        )
        resolved_alignment = alignment or theme.resolve_paragraph_text_alignment(style)
        pagination_styles: list[str] = []
        if style.keep_together:
            pagination_styles.extend([" break-inside: avoid;", " page-break-inside: avoid;"])
        if style.keep_with_next:
            pagination_styles.extend([" break-after: avoid;", " page-break-after: avoid;"])
        if style.page_break_before:
            pagination_styles.extend([" break-before: page;", " page-break-before: always;"])
        if style.widow_control is not None:
            widow_value = 2 if style.widow_control else 1
            pagination_styles.extend([f" widows: {widow_value};", f" orphans: {widow_value};"])
        return (
            f"text-align: {resolved_alignment};"
            f" margin: {space_before:.1f}pt 0 {space_after:.1f}pt;"
            f"{left_indent}"
            f"{right_indent}"
            f"{first_line_indent}"
            f" line-height: {line_height:.1f}pt;"
            f"{''.join(pagination_styles)}"
        )

    def _effective_box_style(self, box: Box, theme: Theme) -> BoxStyle:
        box_style = theme.stylesheet.resolve("box", box.style, None)
        if box.title_position is None and box.shadow is None:
            return box_style
        return replace(
            box_style,
            title_position=box.title_position or box_style.title_position,
            shadow=box_style.shadow if box.shadow is None else box.shadow,
        )

    def _box_css(self, style: BoxStyle, theme: Theme, unit: str) -> str:
        top_padding, right_padding, bottom_padding, left_padding = style.padding.to_points()
        width = (
            f" width: {length_to_inches(style.width, style.unit or unit):.4f}in;"
            if style.width is not None
            else ""
        )
        border_css = (
            f"{style.border.width_points():.2f}pt solid #{style.border.color}"
            if style.border.color is not None and style.border.width > 0
            else "none"
        )
        side_title_css = (
            " display: grid; grid-template-columns: max-content minmax(0, 1fr);"
            " column-gap: 10pt; align-items: stretch;"
            if style.title_position == "side"
            else ""
        )
        shadow_css = (
            " box-shadow: 0 10pt 22pt rgba(15, 23, 42, 0.14);"
            if style.shadow
            else ""
        )
        return (
            f"border: {border_css};"
            f" background: #{style.background_color};"
            f" padding: {top_padding:.1f}pt {right_padding:.1f}pt {bottom_padding:.1f}pt {left_padding:.1f}pt;"
            f" margin: 0 0 {style.space_after:.1f}pt;"
            f"{width}"
            f"{side_title_css}"
            f"{shadow_css}"
            f" {self._block_alignment_css(style.block_alignment or theme.blocks.box_block_alignment)}"
        )

    def _table_wrapper_css(self, theme: Theme, *, in_box: bool = False) -> str:
        padding = "0" if in_box else "14px 16px"
        margin = "4pt 0" if in_box else "0 0 12pt"
        return (
            "width: fit-content;"
            " max-width: 100%;"
            " overflow-x: auto;"
            f" padding: {padding};"
            f" margin: {margin};"
            f" {self._block_alignment_css(theme.blocks.table_block_alignment)}"
        )

    def _figure_css(self, theme: Theme, *, in_box: bool = False) -> str:
        padding = "0" if in_box else "16px"
        margin = "4pt 0" if in_box else "0 0 12pt"
        return (
            f"padding: {padding};"
            f" text-align: {theme.blocks.figure_block_alignment};"
            f" margin: {margin};"
            + (" background: transparent; box-shadow: none;" if in_box else "")
            + f" {self._block_alignment_css(theme.blocks.figure_block_alignment)}"
        )

    def _media_placement_css(self, placement: str, *, in_box: bool = False) -> str:
        if in_box:
            return ""
        if placement == "page":
            return "break-before: page; page-break-before: always; break-after: page; page-break-after: always;"
        if placement == "top":
            return "break-before: page; page-break-before: always;"
        if placement == "float":
            return "break-inside: avoid; page-break-inside: avoid;"
        if placement == "here":
            return "break-inside: auto; page-break-inside: auto;"
        return ""

    def _block_alignment_css(self, alignment: str) -> str:
        if alignment == "right":
            return "margin-left: auto; margin-right: 0;"
        if alignment == "center":
            return "margin-left: auto; margin-right: auto;"
        return "margin-left: 0; margin-right: auto;"

    def _box_title_css(self, style: BoxStyle, theme: Theme, *, side: bool = False) -> str:
        parts = [
            "font-weight: 700",
            "margin: 0 0 6pt" if not side else "margin: 0",
        ]
        if side:
            parts.extend(["align-self: stretch", "min-width: 0"])
        if style.title_background_color is not None:
            parts.append(f"background: #{style.title_background_color}")
            parts.append("padding: 4pt 6pt")
        if style.title_text_color is not None:
            parts.append(f"color: #{style.title_text_color}")
        parts.append(f"font-size: {theme.typography.body_font_size:.1f}pt")
        return "; ".join(parts)

    def _assert_box_children_supported(self, children: list[object]) -> None:
        unsupported = (
            CommentList,
            FootnoteList,
            ReferenceList,
            TableOfContents,
            ListOfTables,
            ListOfFigures,
            ListOfAlgorithms,
            Part,
        )
        for child in children:
            if isinstance(child, unsupported):
                raise OODocsError(f"{type(child).__name__} cannot be rendered inside a Box")

    def _link_html(
        self,
        target: str | None,
        inner_html: str,
        *,
        internal: bool = False,
    ) -> str:
        if not target:
            return inner_html
        href = f"#{target}" if internal else target
        return f'<a href="{escape(href)}">{inner_html}</a>'

    def _html_class_attr(self, *classes: str | None) -> str:
        normalized: list[str] = []
        for class_value in classes:
            if not class_value:
                continue
            normalized.extend(str(class_value).split())
        if not normalized:
            return ""
        escaped = " ".join(escape(class_name, quote=True) for class_name in normalized)
        return f' class="{escaped}"'

    def _css_font_family(self, font_name: str) -> str:
        fallback = "monospace" if "courier" in font_name.lower() else "serif" if "times" in font_name.lower() else "sans-serif"
        escaped_name = font_name.replace('"', '\\"')
        return f'"{escaped_name}", {fallback}'

    def _stylesheet(self, settings: object) -> str:
        theme = settings.theme
        margin_top, margin_right, margin_bottom, margin_left = settings.page_margin_inches()
        page_width = settings.page_width_in_inches()
        text_width = settings.text_width_in_inches()
        page_break_before = (
            "break-before: page; page-break-before: always;"
            if theme.generated_content.generated_content_page_breaks
            else ""
        )
        return f"""
:root {{
  color-scheme: light;
}}
@page {{
  size: {page_width:.2f}in {settings.page_height_in_inches():.2f}in;
  margin: {margin_top:.2f}in {margin_right:.2f}in {margin_bottom:.2f}in {margin_left:.2f}in;
}}
body {{
  margin: 0;
  background: #{theme.blocks.page_background_color};
  color: #1e2329;
  font-family: {self._css_font_family(theme.resolve_body_font())};
  font-size: {theme.typography.body_font_size:.1f}pt;
}}
.oodocs-page-frame {{
  position: relative;
  width: {page_width:.2f}in;
  max-width: 100vw;
  min-height: {settings.page_height_in_inches():.2f}in;
  margin: 0 auto;
}}
.oodocs-document {{
  width: {page_width:.2f}in;
  max-width: 100%;
  margin: 0;
  padding: {margin_top:.2f}in {margin_right:.2f}in {margin_bottom:.2f}in {margin_left:.2f}in;
  box-sizing: border-box;
}}
.oodocs-page-items {{
  position: absolute;
  inset: 0 auto auto 0;
  width: {page_width:.2f}in;
  height: {settings.page_height_in_inches():.2f}in;
  pointer-events: none;
}}
.oodocs-title-matter,
.oodocs-front-matter,
.oodocs-main-matter,
.oodocs-generated-page {{
  max-width: {text_width:.2f}in;
}}
.oodocs-title-matter,
.oodocs-front-matter,
.oodocs-main-matter,
.oodocs-part-page,
.oodocs-generated-page,
.oodocs-box,
.oodocs-table-wrapper,
.oodocs-figure {{
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 40px rgba(60, 48, 28, 0.08);
  border-radius: 16px;
}}
.oodocs-title-matter,
.oodocs-front-matter,
.oodocs-main-matter,
.oodocs-part-page,
.oodocs-generated-page {{
  padding: 24px 26px;
  margin-bottom: 18px;
}}
.oodocs-cover-page {{
  min-height: 40vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}}
.oodocs-part-page {{
  min-height: 52vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
}}
.oodocs-part-label {{
  margin: 0 0 18pt;
  font-size: {max(theme.typography.body_font_size + 3, 14):.1f}pt;
  font-weight: 700;
}}
.oodocs-part-title {{
  margin: 0;
  font-size: {max(theme.typography.title_font_size, theme.resolve_heading_size(1) + 2):.1f}pt;
  font-weight: 700;
}}
.oodocs-page-break-after {{
  break-after: page;
  page-break-after: always;
}}
.oodocs-page-break-before {{
  {page_break_before}
}}
.oodocs-page-break {{
  break-after: page;
  page-break-after: always;
  height: 0;
  margin: 0;
}}
.oodocs-title {{
  margin: 0 0 12pt;
}}
.oodocs-subtitle,
.oodocs-author,
.oodocs-affiliation,
.oodocs-author-detail {{
  margin-top: 0;
}}
.oodocs-paragraph {{
  font-family: {self._css_font_family(theme.resolve_body_font())};
}}
.oodocs-list {{
  margin: 0 0 10pt;
}}
.oodocs-list-item {{
  display: grid;
  grid-template-columns: max-content 1fr;
  align-items: start;
}}
.oodocs-list-marker {{
  text-align: right;
  padding-top: 1px;
  white-space: pre-wrap;
}}
.oodocs-list-content > .oodocs-paragraph {{
  margin-top: 0;
}}
.oodocs-code-block {{
  position: relative;
  margin: 0 0 12pt;
}}
.oodocs-code-language {{
  position: absolute;
  z-index: 1;
  font-family: {self._css_font_family(theme.resolve_monospace_font())};
  font-size: {max(theme.caption_size() - 1, 7):.1f}pt;
  font-weight: 600;
  color: #6f7d90;
  background: rgba(245, 247, 250, 0.9);
  border: 0.5pt solid #d8e0eb;
  border-radius: 4px;
  padding: 1pt 4pt;
  line-height: 1.2;
}}
.oodocs-code-language-top-left {{
  top: 6pt;
  left: 8pt;
}}
.oodocs-code-language-top-right {{
  top: 6pt;
  right: 8pt;
}}
.oodocs-code-language-bottom-left {{
  bottom: 18pt;
  left: 8pt;
}}
.oodocs-code-language-bottom-right {{
  bottom: 18pt;
  right: 8pt;
}}
.oodocs-code {{
  margin-top: 0;
  overflow-x: auto;
  padding: 10pt 12pt;
  border: 0.75pt solid #d8e0eb;
  background: #f5f7fa;
  border-radius: 12px;
  font-family: {self._css_font_family(theme.resolve_monospace_font())};
  font-size: {max(theme.typography.body_font_size - 1, 8):.1f}pt;
  line-height: {max(theme.typography.body_font_size - 1, 8) * 1.35:.1f}pt;
}}
.oodocs-code-has-label-top {{
  padding-top: 24pt;
}}
.oodocs-code-has-label-bottom {{
  padding-bottom: 24pt;
}}
.oodocs-equation {{
  font-size: {max(theme.typography.body_font_size + 1, 12):.1f}pt;
}}
.oodocs-equation-number {{
  margin-left: 0.5em;
  font-size: {theme.typography.body_font_size:.1f}pt;
}}
.oodocs-multi-column-layout {{
  display: block;
}}
.oodocs-multi-column-group {{
  margin: 0 0 10pt;
  column-fill: balance;
}}
.oodocs-multi-column-group > .oodocs-heading,
.oodocs-multi-column-group > .oodocs-table-wrapper,
.oodocs-multi-column-group > .oodocs-figure,
.oodocs-column-span {{
  break-inside: avoid;
  page-break-inside: avoid;
}}
.oodocs-column-span {{
  display: block;
  margin: 0 0 10pt;
}}
.oodocs-box {{
  overflow: hidden;
}}
.oodocs-countable-block {{
  margin: 0 0 10pt;
}}
.oodocs-countable-heading {{
  margin: 0 0 4pt;
  break-after: avoid;
  page-break-after: avoid;
}}
.oodocs-countable-label {{
  font-weight: 700;
}}
.oodocs-countable-title {{
  font-style: italic;
}}
.oodocs-table-wrapper {{
}}
.oodocs-table {{
  width: auto;
  max-width: 100%;
  border-collapse: collapse;
}}
.oodocs-table-split {{
  break-inside: auto;
  page-break-inside: auto;
}}
.oodocs-table-keep {{
  break-inside: avoid;
  page-break-inside: avoid;
}}
.oodocs-table-split thead {{
  display: table-header-group;
}}
.oodocs-table tr {{
  break-inside: avoid;
  page-break-inside: avoid;
}}
.oodocs-table .oodocs-paragraph {{
  margin-bottom: 0;
}}
.oodocs-caption {{
  margin: 6pt 0;
}}
.oodocs-figure {{
}}
.oodocs-figure-image {{
  display: inline-block;
  max-width: 100%;
  height: auto;
}}
.oodocs-generated-title {{
  margin-top: 0;
}}
.oodocs-generated-entry,
.oodocs-caption-list-entry,
.oodocs-toc-entry {{
  margin: 0 0 6pt;
}}
.oodocs-toc {{
  display: block;
}}
.oodocs-toc-entry {{
  display: grid;
  grid-template-columns: auto 1fr max-content;
  align-items: baseline;
  column-gap: 0.28em;
}}
.oodocs-toc-entry-no-page {{
  grid-template-columns: minmax(0, 1fr);
}}
.oodocs-toc-label {{
  min-width: 0;
}}
.oodocs-toc-entry-level-0,
.oodocs-toc-entry-level-1 {{
  margin-top: 10pt;
  padding-top: 6pt;
  border-top: 1px solid rgba(67, 89, 109, 0.18);
  font-size: 1.01em;
  font-weight: 700;
}}
.oodocs-toc-entry-level-2 {{
  margin-top: 2pt;
  font-weight: 600;
}}
.oodocs-toc-entry-level-3,
.oodocs-toc-entry-level-4 {{
  color: #4f667a;
  font-size: 0.97em;
}}
.oodocs-generated-marker {{
  font-weight: 700;
}}
.oodocs-math {{
  letter-spacing: 0.01em;
}}
a {{
  color: #0c5d78;
  text-decoration: underline;
  text-underline-offset: 0.08em;
}}
@media (max-width: 860px) {{
  .oodocs-document {{
    padding: 16px 12px 24px;
  }}
  .oodocs-title-matter,
  .oodocs-front-matter,
  .oodocs-main-matter,
  .oodocs-part-page,
  .oodocs-generated-page,
  .oodocs-table-wrapper,
  .oodocs-figure {{
    padding: 18px 16px;
    border-radius: 12px;
  }}
}}
""".strip()
