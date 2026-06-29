"""PDF renderer.

Attributes:
    ALIGNMENTS: Mapping from OODocs paragraph alignment names to ReportLab
        paragraph alignment values.
    TABLE_CELL_ALIGNMENTS: Mapping from OODocs cell alignment names to
        ReportLab table style values.
    TABLE_CELL_VERTICAL_ALIGNMENTS: Mapping from OODocs vertical alignment names
        to ReportLab table style values.
    FLOWABLE_ALIGNMENTS: Mapping from OODocs alignment names to ReportLab
        flowable alignment values.
    PDF_FONT_VARIANTS: Built-in ReportLab font variants keyed by bold/italic
        flags.
    FONT_FAMILY_ALIASES: Normalized font family aliases used by PDF font
        resolution.
    SYSTEM_FONT_VARIANTS: Optional Windows system font files used when
        registering PDF fonts.
"""

from __future__ import annotations

from dataclasses import replace
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle as RLParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage
from reportlab.platypus import (
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak as RLPageBreak,
    PageTemplate,
    Paragraph as RLParagraph,
    SimpleDocTemplate,
    Spacer,
    Table as RLTable,
    TableStyle,
)
from reportlab.platypus.doctemplate import _doNothing
from reportlab.platypus.flowables import BalancedColumns
from reportlab.platypus.tableofcontents import TableOfContents as RLTableOfContents

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
    PageBreak as OODocsPageBreak,
    Paragraph,
    Part,
    Section,
    VerticalSpace,
)
from oodocs.components.generated import (
    CommentList,
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
    SubFigure,
    SubFigureGroup,
    Table,
    build_table_layout,
    image_source_to_buffer,
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
from oodocs.document import Document
from oodocs.components.equations import SUBSCRIPT, SUPERSCRIPT, parse_latex_segments
from oodocs.core import OODocsError, PathLike, length_to_inches
from oodocs.layout.indexing import RenderIndex, build_render_index
from oodocs.styles import ParagraphStyle, TableStyle as OODocsTableStyle, Theme
from oodocs.renderers.context import PdfRenderContext
from oodocs.renderers.syntax import SyntaxToken, syntax_tokens


ALIGNMENTS = {
    "left": TA_LEFT,
    "center": TA_CENTER,
    "right": TA_RIGHT,
    "justify": TA_JUSTIFY,
}

TABLE_CELL_ALIGNMENTS = {
    "left": "LEFT",
    "center": "CENTER",
    "right": "RIGHT",
    "justify": "LEFT",
}

TABLE_CELL_VERTICAL_ALIGNMENTS = {
    "top": "TOP",
    "middle": "MIDDLE",
    "bottom": "BOTTOM",
}

FLOWABLE_ALIGNMENTS = {
    "left": "LEFT",
    "center": "CENTER",
    "right": "RIGHT",
}

PDF_FONT_VARIANTS = {
    "Courier": {
        (False, False): "Courier",
        (True, False): "Courier-Bold",
        (False, True): "Courier-Oblique",
        (True, True): "Courier-BoldOblique",
    },
    "Helvetica": {
        (False, False): "Helvetica",
        (True, False): "Helvetica-Bold",
        (False, True): "Helvetica-Oblique",
        (True, True): "Helvetica-BoldOblique",
    },
    "Times-Roman": {
        (False, False): "Times-Roman",
        (True, False): "Times-Bold",
        (False, True): "Times-Italic",
        (True, True): "Times-BoldItalic",
    },
}

FONT_FAMILY_ALIASES = {
    "times new roman": "Times-Roman",
    "times": "Times-Roman",
    "times-roman": "Times-Roman",
    "courier new": "Courier",
    "courier": "Courier",
    "cambria math": "Times-Roman",
    "helvetica": "Helvetica",
    "arial": "Helvetica",
}

SYSTEM_FONT_VARIANTS = {
    "Times New Roman": {
        (False, False): ["C:/Windows/Fonts/times.ttf"],
        (True, False): ["C:/Windows/Fonts/timesbd.ttf"],
        (False, True): ["C:/Windows/Fonts/timesi.ttf"],
        (True, True): ["C:/Windows/Fonts/timesbi.ttf"],
    },
    "Courier New": {
        (False, False): ["C:/Windows/Fonts/cour.ttf"],
        (True, False): ["C:/Windows/Fonts/courbd.ttf"],
        (False, True): ["C:/Windows/Fonts/couri.ttf"],
        (True, True): ["C:/Windows/Fonts/courbi.ttf"],
    },
    "Arial": {
        (False, False): ["C:/Windows/Fonts/arial.ttf"],
        (True, False): ["C:/Windows/Fonts/arialbd.ttf"],
        (False, True): ["C:/Windows/Fonts/ariali.ttf"],
        (True, True): ["C:/Windows/Fonts/arialbi.ttf"],
    },
}


class PageNumberTransition(Flowable):
    """Invisible flowable that marks the beginning of a page-numbering mode.

    Attributes:
        mode: Page-numbering mode to activate after this flowable.
    """

    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        """Return the zero-size flowable footprint.

        Args:
            available_width: Width available from ReportLab.
            available_height: Height available from ReportLab.

        Returns:
            ``(0, 0)`` because the transition has no visible size.
        """

        return (0, 0)

    def draw(self) -> None:
        """Draw nothing for the invisible transition marker.

        Returns:
            ``None``.
        """

        return None


class FilteredTableOfContents(RLTableOfContents):
    """ReportLab TOC flowable with optional heading-level filtering.

    Args:
        max_level: Maximum heading level included in the generated TOC.
        allowed_keys: Optional anchor keys allowed in this generated list.
        **kwargs: Additional ReportLab table-of-contents options forwarded to
            ``RLTableOfContents``.

    Attributes:
        max_level: Maximum heading level included in the generated TOC.
        allowed_keys: Optional anchor keys allowed in this generated list.
    """

    def __init__(
        self,
        *,
        max_level: int | None = None,
        allowed_keys: set[str] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.max_level = max_level
        self.allowed_keys = allowed_keys

    def notify(self, kind: str, stuff: object) -> None:
        """Receive ReportLab TOC notifications and filter by heading level.

        Args:
            kind: ReportLab notification kind.
            stuff: Notification payload supplied by ReportLab.
        """

        if kind == self._notifyKind and self.max_level is not None:
            level = stuff[0]  # type: ignore[index]
            if level > self.max_level:
                return
        if kind == self._notifyKind and self.allowed_keys is not None:
            key = stuff[3] if len(stuff) > 3 else None  # type: ignore[arg-type]
            if key not in self.allowed_keys:
                return
        super().notify(kind, stuff)


class CodeBlockFlowable(Flowable):
    """Syntax-highlighted code that wraps to the available PDF width.

    Attributes:
        tokens: Syntax-highlighted source tokens.
        font_names: Font names keyed by ``(bold, italic)``.
        font_size: Code font size in points.
        leading: Line height in points.
        anchor: Optional PDF bookmark anchor.
        width: Wrapped code block width in points after measurement.
        height: Wrapped code block height in points after measurement.
    """

    def __init__(
        self,
        tokens: list[SyntaxToken],
        *,
        font_names: dict[tuple[bool, bool], str],
        font_size: float,
        leading: float,
        anchor: str | None = None,
    ) -> None:
        super().__init__()
        self.tokens = tokens
        self.font_names = font_names
        self.font_size = font_size
        self.leading = leading
        self.anchor = anchor
        self.width = 0.0
        self.height = leading
        self._lines: list[list[SyntaxToken]] = []

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        """Measure wrapped code against the available width.

        Args:
            available_width: Width available from ReportLab.
            available_height: Height available from ReportLab.

        Returns:
            Required ``(width, height)`` for the wrapped code block.
        """

        self.width = max(available_width, self.font_size)
        self._lines = self._wrap_tokens(self.width)
        self.height = max(len(self._lines), 1) * self.leading
        return (self.width, self.height)

    def draw(self) -> None:
        """Draw the wrapped highlighted code onto the ReportLab canvas.

        Returns:
            ``None``.
        """

        if self.anchor:
            self.canv.bookmarkPage(self.anchor)
        y = self.height - self.font_size
        for line in self._lines or [[]]:
            text_object = self.canv.beginText(0, y)
            for segment in line:
                if not segment.text:
                    continue
                font_name = self.font_names[(segment.bold, segment.italic)]
                text_object.setFont(font_name, self.font_size)
                text_object.setFillColor(colors.HexColor(f"#{segment.color}") if segment.color else colors.black)
                text_object.textOut(segment.text)
            self.canv.drawText(text_object)
            y -= self.leading
        self.canv.setFillColor(colors.black)

    def _wrap_tokens(self, max_width: float) -> list[list[SyntaxToken]]:
        lines: list[list[SyntaxToken]] = []
        current_line: list[SyntaxToken] = []
        current_width = 0.0

        for token in self.tokens:
            text = token.text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
            for character in text:
                if character == "\n":
                    lines.append(current_line)
                    current_line = []
                    current_width = 0.0
                    continue

                font_name = self.font_names[(token.bold, token.italic)]
                character_width = pdfmetrics.stringWidth(character, font_name, self.font_size)
                if current_line and current_width + character_width > max_width:
                    lines.append(current_line)
                    current_line = []
                    current_width = 0.0

                current_line = self._append_segment(current_line, character, token)
                current_width += character_width

        lines.append(current_line)
        return lines

    def _append_segment(
        self,
        line: list[SyntaxToken],
        text: str,
        token: SyntaxToken,
    ) -> list[SyntaxToken]:
        if (
            line
            and line[-1].color == token.color
            and line[-1].bold == token.bold
            and line[-1].italic == token.italic
        ):
            previous = line[-1]
            line[-1] = SyntaxToken(
                previous.text + text,
                color=previous.color,
                bold=previous.bold,
                italic=previous.italic,
            )
        else:
            line.append(SyntaxToken(text, color=token.color, bold=token.bold, italic=token.italic))
        return line


class PositionedItemFlowable(Flowable):
    """ReportLab flowable for inline drawing items.

    Attributes:
        item: Positioned item to draw inline.
        renderer: PDF renderer responsible for drawing the item.
        context: Current PDF render context.
        width: Inline item width in ReportLab points.
        height: Inline item height in ReportLab points.
    """

    def __init__(
        self,
        item: PositionedItem,
        renderer: "PdfRenderer",
        context: PdfRenderContext,
    ) -> None:
        super().__init__()
        self.item = item
        self.renderer = renderer
        self.context = context
        self.width = length_to_inches(item.width, item.unit or context.unit) * inch
        self.height = length_to_inches(item.height, item.unit or context.unit) * inch

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        """Return the fixed inline item size.

        Args:
            available_width: Width available from ReportLab.
            available_height: Height available from ReportLab.

        Returns:
            Required ``(width, height)`` for the item.
        """

        return (self.width, self.height)

    def draw(self) -> None:
        """Draw the inline positioned item onto the ReportLab canvas.

        Returns:
            ``None``.
        """

        self.renderer._draw_positioned_item(
            self.canv,
            self.item,
            x=0,
            y_top=0,
            width=self.width,
            height=self.height,
            page_height=self.height,
            context=self.context,
        )


class PagePositionedItemFlowable(Flowable):
    """Zero-size flowable that draws a page-positioned item on the current page.

    Attributes:
        box: Resolved page-positioned box to draw.
        renderer: PDF renderer responsible for drawing the item.
        context: Current PDF render context.
    """

    def __init__(
        self,
        box: PositionedBox,
        renderer: "PdfRenderer",
        context: PdfRenderContext,
    ) -> None:
        super().__init__()
        self.box = box
        self.renderer = renderer
        self.context = context

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        """Return the zero-size page-positioned footprint.

        Args:
            available_width: Width available from ReportLab.
            available_height: Height available from ReportLab.

        Returns:
            ``(0, 0)`` because the item is positioned against the page.
        """

        return (0, 0)

    def draw(self) -> None:
        """Draw the page-positioned item onto the current ReportLab page.

        Returns:
            ``None``.
        """

        settings = self.context.settings
        self.renderer._draw_positioned_item(
            self.canv,
            self.box.item,
            x=self.box.x * inch,
            y_top=self.box.y * inch,
            width=self.box.width * inch,
            height=self.box.height * inch,
            page_height=settings.page_height_in_inches() * inch,
            context=self.context,
        )


class OODocsPdfTemplate(SimpleDocTemplate):
    """SimpleDocTemplate with page-number mode transitions.

    Args:
        *args: Positional arguments forwarded to ``SimpleDocTemplate``.
        **kwargs: Keyword arguments forwarded to ``SimpleDocTemplate``.

    Attributes:
        main_matter_start_page: Physical page where main-matter numbering
            starts, or ``None`` before main matter begins.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.main_matter_start_page: int | None = None

    def beforeDocument(self) -> None:
        """Reset per-build page-number state before ReportLab starts.

        Returns:
            ``None``.
        """

        self.main_matter_start_page = None

    def build(
        self,
        flowables: list[object],
        onFirstPage: object = _doNothing,
        onLaterPages: object = _doNothing,
        canvasmaker: object = None,
    ) -> None:
        """Build a PDF using OODocs page templates.

        Args:
            flowables: Story flowables to render.
            onFirstPage: Optional callback for the first page.
            onLaterPages: Optional callback for later pages.
            canvasmaker: Optional ReportLab canvas factory.
        """

        self._calc()
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        self.addPageTemplates(
            [
                PageTemplate(id="First", frames=frame, onPage=onFirstPage, pagesize=self.pagesize),
                PageTemplate(id="Later", frames=frame, onPage=onLaterPages, pagesize=self.pagesize),
            ]
        )
        if onFirstPage is _doNothing and hasattr(self, "onFirstPage"):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self, "onLaterPages"):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        from reportlab.platypus.doctemplate import BaseDocTemplate

        if canvasmaker is None:
            BaseDocTemplate.build(self, flowables)
        else:
            BaseDocTemplate.build(self, flowables, canvasmaker=canvasmaker)

    def afterFlowable(self, flowable: Flowable) -> None:
        """Track page-number transitions and TOC entries after each flowable.

        Args:
            flowable: Flowable that ReportLab just rendered.
        """

        if isinstance(flowable, PageNumberTransition) and flowable.mode == "main":
            self.main_matter_start_page = self.page + 1
            return
        toc_entry = getattr(flowable, "_oodocs_toc_entry", None)
        if toc_entry is not None:
            level, text, key = toc_entry
            self.notify("TOCEntry", (level, text, self._logical_page(self.page), key))
        caption_list_entry = getattr(flowable, "_oodocs_caption_list_entry", None)
        if caption_list_entry is not None:
            kind, text, key = caption_list_entry
            self.notify(kind, (0, text, self._logical_page(self.page), key))

    def _logical_page(self, physical_page: int) -> int:
        if self.main_matter_start_page is None:
            return physical_page
        if physical_page < self.main_matter_start_page:
            return physical_page
        return physical_page - self.main_matter_start_page + 1


class PdfRenderer:
    """Render OODocs documents into PDF files.

    The renderer exposes ``render_*`` methods so block classes and custom
    extensions can dispatch ReportLab flowable generation through a shared
    context.

    Attributes:
        _registered_system_fonts: Cache of registered system font variants.
        _pending_float_flowables: Float flowables deferred until a safe flush
            point in the story.
    """

    def __init__(self) -> None:
        self._registered_system_fonts: dict[tuple[str, bool, bool], str] = {}
        self._pending_float_flowables: list[object] = []

    def render(self, document: Document, output_path: PathLike) -> Path:
        """Render an OODocs document to a PDF file.

        Args:
            document: Document to render.
            output_path: Destination ``.pdf`` path.

        Returns:
            Output path that was written.
        """

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._pending_float_flowables = []
        settings = document.settings

        pdf = OODocsPdfTemplate(
            str(path),
            pagesize=(
                settings.page_width_in_inches() * inch,
                settings.page_height_in_inches() * inch,
            ),
            title=document.title,
            author=settings.resolved_author(),
            leftMargin=settings.page_margins.left_in_inches(settings.unit) * inch,
            rightMargin=settings.page_margins.right_in_inches(settings.unit) * inch,
            topMargin=settings.page_margins.top_in_inches(settings.unit) * inch,
            bottomMargin=settings.page_margins.bottom_in_inches(settings.unit) * inch,
        )
        story: list[object] = []
        styles = getSampleStyleSheet()
        render_index = build_render_index(document)
        context = PdfRenderContext(
            theme=settings.theme,
            render_index=render_index,
            settings=settings,
            unit=settings.unit,
            styles=styles,
        )

        front_children, main_children = document.split_top_level_children()
        has_front_matter = settings.cover_page or bool(front_children)

        story.extend(self._render_title_matter(document, context))
        if settings.cover_page and front_children:
            story.append(RLPageBreak())

        story.extend(
            self._render_top_level_children(
                front_children,
                context,
                follows_existing_content=not settings.cover_page,
            )
        )
        if has_front_matter and main_children:
            story.append(PageNumberTransition("main"))
            if story and not isinstance(story[-2] if len(story) > 1 else None, RLPageBreak):
                story.append(RLPageBreak())
            story.extend(
                self._render_top_level_children(
                    main_children,
                    context,
                    follows_existing_content=False,
                )
            )
        elif not has_front_matter:
            story.extend(
                self._render_top_level_children(
                    main_children,
                    context,
                    follows_existing_content=True,
                )
            )

        if self._should_auto_render_footnote_list(document, render_index):
            story.extend(self.render_footnote_list(FootnoteList(), context))

        page_callback = self._page_callback(
            document,
            context,
            has_front_matter=has_front_matter,
        )
        if self._story_has_indexing_flowable(story):
            pdf.multiBuild(story, onFirstPage=page_callback, onLaterPages=page_callback)
        elif settings.theme.page_numbers.show_page_numbers or settings.theme.blocks.page_background_color != "FFFFFF":
            pdf.build(story, onFirstPage=page_callback, onLaterPages=page_callback)
        else:
            pdf.build(story)
        return path

    def make_section_heading(
        self,
        block: Section,
        context: PdfRenderContext,
    ) -> RLParagraph:
        """Build the PDF flowable used for a section heading.

        Args:
            block: Section whose heading should be rendered.
            context: Current PDF render context.

        Returns:
            ReportLab paragraph containing heading markup and optional TOC
            metadata.
        """

        theme = context.theme
        styles = context.styles
        render_index = context.render_index
        heading_style = theme.resolve_heading_style(block.level, block.heading_style)
        heading_text_style = heading_style.text_style
        bold = bool(heading_text_style.bold)
        italic = bool(heading_text_style.italic)
        font_size = heading_text_style.font_size or theme.resolve_heading_size(block.level)
        title_style = RLParagraphStyle(
            f"Heading{block.level}",
            parent=styles["Heading1"],
            fontName=self._resolve_font(
                heading_text_style.font_name or theme.resolve_body_font(),
                bold,
                italic,
            ),
            fontSize=font_size,
            leading=heading_style.leading if heading_style.leading is not None else font_size * 1.2,
            spaceBefore=heading_style.space_before if heading_style.space_before is not None else 0,
            spaceAfter=heading_style.space_after if heading_style.space_after is not None else 0,
            alignment=ALIGNMENTS[heading_style.text_alignment or "left"],
            textColor=(
                colors.HexColor(f"#{heading_text_style.text_color}")
                if heading_text_style.text_color is not None
                else colors.black
            ),
        )
        anchor = render_index.heading_anchor(block)
        paragraph = RLParagraph(
            self._anchor_markup(anchor)
            + self._inline_markup(
                self._heading_fragments(
                    block.title,
                    render_index.heading_number(block),
                ),
                theme,
                render_index,
                base_font_name=title_style.fontName,
                base_size=title_style.fontSize,
                base_bold=bold,
                base_italic=italic,
            ),
            title_style,
        )
        if block.toc and anchor is not None:
            paragraph._oodocs_toc_entry = (
                block.level,
                self._flatten_fragments(
                    self._heading_fragments(block.title, render_index.heading_number(block)),
                    theme,
                    render_index,
                ),
                anchor,
            )
        return paragraph

    def render_paragraph(
        self,
        block: Paragraph,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a paragraph block into PDF flowables.

        Args:
            block: Paragraph block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the paragraph.
        """

        block_style = context.stylesheet.resolve("paragraph", block.style, ParagraphStyle())
        paragraph_style = self._paragraph_style(
            block_style,
            context.theme,
            context.styles["BodyText"],
            default_unit=context.unit,
        )
        title_style = context.theme.resolve_run_in_title_style(
            block.title_style,
            context.run_in_title_style,
        )
        paragraph = RLParagraph(
            self._anchor_markup(context.render_index.block_anchor(block))
            +
            self._inline_markup(
                block.render_content(title_style),
                context.theme,
                context.render_index,
                base_font_name=paragraph_style.fontName,
                base_size=paragraph_style.fontSize,
            ),
            paragraph_style,
        )
        flowables: list[object] = [paragraph]
        if block_style.keep_together:
            flowables = [KeepTogether(flowables)]
        if block_style.page_break_before:
            flowables.insert(0, RLPageBreak())
        return flowables

    def render_part(
        self,
        block: Part,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a part separator page and its child blocks into PDF flowables.

        Args:
            block: Part block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the part separator and children.
        """

        theme = context.theme
        render_index = context.render_index
        number_label = render_index.heading_number(block) if block.numbered else None
        anchor = render_index.heading_anchor(block)
        story: list[object] = []

        toc_flowable: object | None = None
        if number_label:
            label = self._part_paragraph(
                [Text(number_label)],
                context,
                style_name="OODocsPartLabel",
                font_size=max(theme.typography.body_font_size + 3, 14),
                bold=True,
                space_after=18,
                anchor=anchor,
            )
            story.append(label)
            toc_flowable = label
            anchor = None
        title = self._part_paragraph(
            block.title,
            context,
            style_name="OODocsPartTitle",
            font_size=max(theme.typography.title_font_size, theme.resolve_heading_size(1) + 2),
            bold=True,
            space_after=0,
            anchor=anchor,
        )
        story.append(title)
        if toc_flowable is None:
            toc_flowable = title
        if block.toc and render_index.heading_anchor(block) is not None:
            toc_flowable._oodocs_toc_entry = (
                block.level,
                self._flatten_fragments(
                    self._heading_fragments(block.title, render_index.heading_number(block)),
                    theme,
                    render_index,
                ),
                render_index.heading_anchor(block),
            )

        if block.children:
            story.append(RLPageBreak())
            story.extend(
                self._render_top_level_children(
                    block.children,
                    context,
                    follows_existing_content=False,
                )
            )
        return story

    def render_section(
        self,
        block: Section,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a section heading and body, allowing float blocks to move later.

        Args:
            block: Section block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the heading and section body.
        """

        child_context = (
            replace(context, run_in_title_style=block.run_in_title_style)
            if block.run_in_title_style is not None
            else context
        )
        return [self.make_section_heading(block, context)] + self._render_flow_children(
            block.children,
            child_context,
            flush_trailing_floats=False,
        )

    def render_list(
        self,
        block: BulletList | NumberedList,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a list block into PDF flowables.

        Args:
            block: Bullet or numbered list block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the list.
        """

        return self._render_list(
            block,
            context.theme,
            context.styles,
            context.render_index,
            context.unit,
        )

    def render_code_block(
        self,
        block: CodeBlock,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a code block into PDF flowables.

        Args:
            block: Code block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the code block.
        """

        return self._render_code_block(
            block,
            context.theme,
            context.styles,
            context.render_index,
            context.settings,
            context.in_box,
        )

    def render_equation(
        self,
        block: Equation,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a block equation into PDF flowables.

        Args:
            block: Equation block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the equation.
        """

        return self._render_equation(
            block,
            context.theme,
            context.styles,
            context.render_index,
        )

    def render_page_break(
        self,
        block: OODocsPageBreak,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render an explicit page break into PDF flowables.

        Args:
            block: Page break block to render.
            context: Current PDF render context.

        Returns:
            Flowables containing a ReportLab page break.
        """

        return [RLPageBreak()]

    def render_vertical_space(
        self,
        block: VerticalSpace,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a LaTeX-like vertical spacer into PDF flowables.

        Args:
            block: Vertical space block to render.
            context: Current PDF render context.

        Returns:
            Flowables containing a spacer.
        """

        return [Spacer(1, block.height_in_points())]

    def render_divider(
        self,
        block: Divider,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a horizontal divider into PDF flowables.

        Args:
            block: Divider block to render.
            context: Current PDF render context.

        Returns:
            Flowables containing a horizontal rule.
        """

        width = block.width_in_inches(context.unit)
        flowable = HRFlowable(
            width="100%" if width is None else width * inch,
            thickness=block.thickness,
            color=colors.HexColor(f"#{block.color}"),
            spaceBefore=block.space_before,
            spaceAfter=block.space_after,
            hAlign=FLOWABLE_ALIGNMENTS[block.alignment],
        )
        return [flowable]

    def render_box(
        self,
        block: Box,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a box and its child blocks into PDF flowables.

        Args:
            block: Box block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the box and child content.
        """

        return self._render_box(
            block,
            context.theme,
            context.styles,
            context.render_index,
            context.settings,
            context.unit,
        )

    def render_countable_block(
        self,
        block: CountableBlock,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a theorem-like countable block into PDF flowables.

        Args:
            block: Countable block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the countable heading and children.
        """

        heading_style = self._paragraph_style(
            ParagraphStyle(space_after=4, keep_with_next=True),
            context.theme,
            context.styles["BodyText"],
            default_unit=context.unit,
        )
        heading_markup = (
            self._anchor_markup(context.render_index.block_anchor(block))
            + f"<b>{escape(block.heading_label(context.render_index.countable_number(block)))}</b>"
        )
        if block.title is not None:
            heading_markup += " " + self._inline_markup(
                block.title,
                context.theme,
                context.render_index,
                base_font_name=heading_style.fontName,
                base_size=heading_style.fontSize,
                base_italic=True,
            )
        return [RLParagraph(heading_markup, heading_style)] + self._render_flow_children(
            block.children,
            context,
            flush_trailing_floats=False,
        )

    def render_column_span(
        self,
        block: ColumnSpan,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render full-width content from a multicolumn flow.

        Args:
            block: Column-span block to render.
            context: Current PDF render context.

        Returns:
            Flowables that should span all columns.
        """

        return self._render_flow_children(
            block.children,
            context,
            flush_trailing_floats=True,
        )

    def render_multi_column(
        self,
        block: MultiColumn,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a multicolumn flow into PDF flowables.

        Args:
            block: Multi-column block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing grouped column content and full-width spans.
        """

        if block.columns == 1:
            return self._render_flow_children(
                block.children,
                context,
                flush_trailing_floats=True,
            )

        story: list[object] = []
        current_group: list[object] = []
        available_width = context.settings.text_width_in_inches()

        def flush_group() -> None:
            if not current_group:
                return
            story.extend(self._render_multi_column_group(block, current_group, context))
            current_group.clear()

        for child in block.children:
            # Full-width children split the current column group so they can be
            # emitted between normal multi-column runs without being squeezed.
            if block._child_spans_columns(
                child,
                available_width=available_width,
                default_unit=context.unit,
            ):
                flush_group()
                story.extend(self._unmark_float_story(child.render_to_pdf(self, context)))
                continue
            current_group.append(child)
        flush_group()
        return story

    def render_shape(
        self,
        block: Shape,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a shape into PDF flowables.

        Args:
            block: Shape to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the positioned or inline shape.
        """

        return self._render_positioned_item(block, context)

    def render_text_box(
        self,
        block: TextBox,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a textbox into PDF flowables.

        Args:
            block: Text box to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the positioned or inline text box.
        """

        return self._render_positioned_item(block, context)

    def render_image_box(
        self,
        block: ImageBox,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render an image box into PDF flowables.

        Args:
            block: Image box to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the positioned or inline image.
        """

        return self._render_positioned_item(block, context)

    def render_table(
        self,
        block: Table,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a table block into PDF flowables.

        Args:
            block: Table block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the table and optional caption.
        """

        return self._render_table(
            block,
            context.theme,
            context.styles,
            context.render_index,
            context.unit,
            text_width=context.settings.text_width_in_inches(),
            in_box=context.in_box,
        )

    def render_figure(
        self,
        block: Figure,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a figure block into PDF flowables.

        Args:
            block: Figure block to render.
            context: Current PDF render context.

        Returns:
            Flowables representing the image and optional caption.
        """

        return self._render_figure(
            block,
            context.theme,
            context.styles,
            context.render_index,
            context.unit,
            in_box=context.in_box,
        )

    def render_subfigure_group(
        self,
        block: SubFigureGroup,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render a subfigure group into PDF flowables.

        Args:
            block: Subfigure group to render.
            context: Current PDF render context.

        Returns:
            Flowables representing grouped subfigures and optional caption.
        """

        return self._render_subfigure_group(
            block,
            context.theme,
            context.styles,
            context.render_index,
            context.unit,
            in_box=context.in_box,
        )

    def render_list_of_tables(
        self,
        block: ListOfTables,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render the generated list of tables into PDF flowables.

        Args:
            block: Generated table-list block.
            context: Current PDF render context.

        Returns:
            Flowables representing the generated list of tables.
        """

        return self._render_caption_list(
            block,
            block.title,
            context.render_index.scoped_tables(block),
            context.theme,
            context.styles,
            context.render_index,
            context.theme.resolve_generated_page_title("list_of_tables"),
            context.theme.resolve_caption_label("table", "caption"),
            notify_kind="TableListEntry",
        )

    def render_list_of_figures(
        self,
        block: ListOfFigures,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render the generated list of figures into PDF flowables.

        Args:
            block: Generated figure-list block.
            context: Current PDF render context.

        Returns:
            Flowables representing the generated list of figures.
        """

        return self._render_caption_list(
            block,
            block.title,
            context.render_index.scoped_figures(block),
            context.theme,
            context.styles,
            context.render_index,
            context.theme.resolve_generated_page_title("list_of_figures"),
            context.theme.resolve_caption_label("figure", "caption"),
            notify_kind="FigureListEntry",
        )

    def render_comment_list(
        self,
        block: CommentList,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render the generated comments page into PDF flowables.

        Args:
            block: Generated comments page block.
            context: Current PDF render context.

        Returns:
            Flowables representing the generated comments page.
        """

        return self._render_comment_list(
            block.title,
            context.theme,
            context.styles,
            context.render_index,
        )

    def render_footnote_list(
        self,
        block: FootnoteList,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render the generated footnotes page into PDF flowables.

        Args:
            block: Generated footnotes page block.
            context: Current PDF render context.

        Returns:
            Flowables representing the generated footnotes page.
        """

        return self._render_footnote_list(
            block.title,
            context.theme,
            context.styles,
            context.render_index,
        )

    def render_reference_list(
        self,
        block: ReferenceList,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render the generated references page into PDF flowables.

        Args:
            block: Generated references page block.
            context: Current PDF render context.

        Returns:
            Flowables representing the generated references page.
        """

        return self._render_reference_list(
            block.title,
            context.theme,
            context.styles,
            context.render_index,
        )

    def render_table_of_contents(
        self,
        block: TableOfContents,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render the generated table of contents into PDF flowables.

        Args:
            block: Generated table-of-contents block.
            context: Current PDF render context.

        Returns:
            Flowables representing the generated table of contents.
        """

        return self._render_table_of_contents(
            block,
            context,
        )

    def _render_block(
        self,
        block: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Delegate block rendering back to the block instance itself."""

        return block.render_to_pdf(self, context)

    def _render_top_level_children(
        self,
        children: list[object],
        context: PdfRenderContext,
        *,
        follows_existing_content: bool = False,
    ) -> list[object]:
        story: list[object] = []
        for index, child in enumerate(children):
            if isinstance(child, Part):
                story.extend(self._pop_pending_float_flowables())
                if story and not isinstance(story[-1], RLPageBreak):
                    story.append(RLPageBreak())
                elif not story and follows_existing_content:
                    story.append(RLPageBreak())
                story.extend(child.render_to_pdf(self, context))
                if not child.children and index < len(children) - 1:
                    story.append(RLPageBreak())
                continue
            if self._is_paginated_generated_page(child) and context.theme.generated_content.generated_content_page_breaks:
                story.extend(self._pop_pending_float_flowables())
                if story and not isinstance(story[-1], RLPageBreak):
                    story.append(RLPageBreak())
                story.extend(child.render_to_pdf(self, context))
                if index < len(children) - 1:
                    story.append(RLPageBreak())
                continue
            pending_before_child = bool(self._pending_float_flowables)
            child_story = child.render_to_pdf(self, context)
            if self._is_float_story(child_story):
                self._pending_float_flowables.extend(child_story)
                continue
            story.extend(child_story)
            if pending_before_child:
                story.extend(self._pop_pending_float_flowables())
        story.extend(self._pop_pending_float_flowables())
        return story

    def _render_flow_children(
        self,
        children: list[object],
        context: PdfRenderContext,
        *,
        flush_trailing_floats: bool,
    ) -> list[object]:
        story: list[object] = []
        for child in children:
            pending_before_child = bool(self._pending_float_flowables)
            child_story = child.render_to_pdf(self, context)
            if self._is_float_story(child_story):
                self._pending_float_flowables.extend(child_story)
                continue
            story.extend(child_story)
            if pending_before_child:
                story.extend(self._pop_pending_float_flowables())
        if flush_trailing_floats:
            story.extend(self._pop_pending_float_flowables())
        return story

    def _render_multi_column_group(
        self,
        block: MultiColumn,
        children: list[object],
        context: PdfRenderContext,
    ) -> list[object]:
        story = self._render_flow_children(
            children,
            context,
            flush_trailing_floats=True,
        )
        if not story:
            return []
        if block.columns == 1:
            return story
        story = self._flatten_keep_together_for_columns(story)
        gap_points = block.column_gap_in_inches(context.unit) * inch
        return [
            BalancedColumns(
                story,
                nCols=block.columns,
                innerPadding=gap_points,
                spaceAfter=6,
            )
        ]

    def _flatten_keep_together_for_columns(self, story: list[object]) -> list[object]:
        flattened: list[object] = []
        for flowable in story:
            if isinstance(flowable, KeepTogether):
                flattened.extend(flowable._content)
                continue
            flattened.append(flowable)
        return flattened

    def _mark_float_story(self, story: list[object]) -> list[object]:
        for flowable in story:
            setattr(flowable, "_oodocs_float", True)
        return story

    def _unmark_float_story(self, story: list[object]) -> list[object]:
        for flowable in story:
            if hasattr(flowable, "_oodocs_float"):
                setattr(flowable, "_oodocs_float", False)
        return story

    def _is_float_story(self, story: list[object]) -> bool:
        return bool(story) and all(
            bool(getattr(flowable, "_oodocs_float", False))
            for flowable in story
        )

    def _pop_pending_float_flowables(self) -> list[object]:
        pending = self._pending_float_flowables
        self._pending_float_flowables = []
        return pending

    def _render_title_matter(
        self,
        document: Document,
        context: PdfRenderContext,
    ) -> list[object]:
        theme = context.theme
        styles = context.styles
        story: list[object] = [
            self._title_paragraph(
                [Text(document.title)],
                theme,
                styles,
                style_name="OODocsTitle",
                font_size=theme.typography.title_font_size,
                alignment=theme.title_matter.title_text_alignment,
                bold=True,
                space_after=18,
            )
        ]
        if document.settings.subtitle is not None:
            story.append(
                self._title_paragraph(
                    document.settings.subtitle,
                    theme,
                    styles,
                    style_name="OODocsSubtitle",
                    font_size=max(theme.typography.body_font_size + 1, 12),
                    alignment=theme.title_matter.subtitle_text_alignment,
                    italic=True,
                    space_after=12,
                )
            )
        author_lines = list(document.settings.iter_author_title_lines())
        for index, (line, _is_last_for_author) in enumerate(author_lines):
            story.append(
                self._title_paragraph(
                    list(line.fragments),
                    theme,
                    styles,
                    style_name=f"OODocsAuthor{line.kind.title()}",
                    font_size=self._title_line_font_size(line, theme),
                    alignment=self._title_line_alignment(line, theme),
                    italic=line.kind == "affiliation",
                    space_after=self._author_title_line_space_after(author_lines, index, last_space=12),
                )
            )
        return story

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

    def _title_paragraph(
        self,
        fragments: list[Text],
        theme: Theme,
        styles: object,
        *,
        style_name: str,
        font_size: float,
        alignment: str,
        bold: bool = False,
        italic: bool = False,
        space_after: float = 0,
    ) -> RLParagraph:
        paragraph_style = RLParagraphStyle(
            style_name,
            parent=styles["BodyText"],
            fontName=self._resolve_font(theme.resolve_body_font(), bold, italic),
            fontSize=font_size,
            leading=font_size * 1.2,
            alignment=ALIGNMENTS[alignment],
            spaceAfter=space_after,
            textColor=colors.black,
        )
        return RLParagraph(
            self._inline_markup(
                fragments,
                theme,
                RenderIndex(),
                base_font_name=paragraph_style.fontName,
                base_size=paragraph_style.fontSize,
                base_bold=bold,
                base_italic=italic,
            ),
            paragraph_style,
        )

    def _part_paragraph(
        self,
        fragments: list[Text],
        context: PdfRenderContext,
        *,
        style_name: str,
        font_size: float,
        bold: bool,
        space_after: float,
        anchor: str | None = None,
    ) -> RLParagraph:
        theme = context.theme
        paragraph_style = RLParagraphStyle(
            style_name,
            parent=context.styles["BodyText"],
            fontName=self._resolve_font(theme.resolve_body_font(), bold, False),
            fontSize=font_size,
            leading=font_size * 1.2,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=space_after,
            textColor=colors.black,
        )
        return RLParagraph(
            self._anchor_markup(anchor)
            + self._inline_markup(
                fragments,
                theme,
                context.render_index,
                base_font_name=paragraph_style.fontName,
                base_size=paragraph_style.fontSize,
                base_bold=bold,
            ),
            paragraph_style,
        )

    def _is_paginated_generated_page(self, block: object) -> bool:
        return isinstance(block, (ListOfTables, ListOfFigures, TableOfContents))

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

    def _story_has_indexing_flowable(self, story: list[object]) -> bool:
        return any(getattr(flowable, "isIndexing", lambda: False)() for flowable in story)

    def _render_positioned_item(
        self,
        item: PositionedItem,
        context: PdfRenderContext,
    ) -> list[object]:
        if item.placement == "inline":
            return [PositionedItemFlowable(item, self, context)]
        box = resolve_positioned_boxes([item], context.settings, context.unit)[0]
        return [PagePositionedItemFlowable(box, self, context)]

    def _draw_page_items(
        self,
        canvas: object,
        document: Document,
        context: PdfRenderContext,
    ) -> None:
        if not document.settings.page_items:
            return
        page_height = document.settings.page_height_in_inches() * inch
        for box in resolve_positioned_boxes(
            document.settings.page_items,
            document.settings,
            context.unit,
        ):
            self._draw_positioned_item(
                canvas,
                box.item,
                x=box.x * inch,
                y_top=box.y * inch,
                width=box.width * inch,
                height=box.height * inch,
                page_height=page_height,
                context=context,
            )

    def _draw_positioned_item(
        self,
        canvas: object,
        item: PositionedItem,
        *,
        x: float,
        y_top: float,
        width: float,
        height: float,
        page_height: float,
        context: PdfRenderContext,
    ) -> None:
        canvas.saveState()
        if isinstance(item, TextBox):
            self._draw_text_box(canvas, item, x, y_top, width, height, page_height, context)
        elif isinstance(item, ImageBox):
            self._draw_image_box(canvas, item, x, y_top, width, height, page_height)
        else:
            self._draw_shape(canvas, item, x, y_top, width, height, page_height)
        canvas.restoreState()

    def _draw_text_box(
        self,
        canvas: object,
        item: TextBox,
        x: float,
        y_top: float,
        width: float,
        height: float,
        page_height: float,
        context: PdfRenderContext,
    ) -> None:
        font_size = item.font_size or context.theme.typography.body_font_size
        style = RLParagraphStyle(
            "PositionedTextBox",
            fontName=self._resolve_font(context.theme.resolve_body_font(), False, False),
            fontSize=font_size,
            leading=font_size * 1.22,
            alignment=ALIGNMENTS[item.text_alignment],
            textColor=colors.black,
        )
        paragraph = RLParagraph(
            self._inline_markup(
                item.content,
                context.theme,
                context.render_index,
                base_font_name=style.fontName,
                base_size=font_size,
            ),
            style,
        )
        _, paragraph_height = paragraph.wrap(width, height)
        if item.vertical_alignment == "middle":
            y = page_height - y_top - ((height + paragraph_height) / 2)
        elif item.vertical_alignment == "bottom":
            y = page_height - y_top - height
        else:
            y = page_height - y_top - paragraph_height
        paragraph.drawOn(canvas, x, y)

    def _draw_shape(
        self,
        canvas: object,
        item: Shape,
        x: float,
        y_top: float,
        width: float,
        height: float,
        page_height: float,
    ) -> None:
        y = page_height - y_top - height
        if item.stroke.color is not None and item.stroke.width > 0:
            canvas.setStrokeColor(colors.HexColor(f"#{item.stroke.color}"))
            canvas.setLineWidth(item.stroke.width_points())
        if item.fill_color is not None:
            canvas.setFillColor(colors.HexColor(f"#{item.fill_color}"))
        fill = 1 if item.fill_color is not None else 0
        stroke = 1 if item.stroke.color is not None and item.stroke.width > 0 else 0
        if item.kind == "rect":
            canvas.rect(x, y, width, height, fill=fill, stroke=stroke)
        elif item.kind == "ellipse":
            canvas.ellipse(x, y, x + width, y + height, fill=fill, stroke=stroke)
        else:
            canvas.line(x, page_height - y_top, x + width, page_height - y_top - height)

    def _draw_image_box(
        self,
        canvas: object,
        item: ImageBox,
        x: float,
        y_top: float,
        width: float,
        height: float,
        page_height: float,
    ) -> None:
        y = page_height - y_top - height
        canvas.drawImage(
            self._image_box_source(item),
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=item.fit == "contain",
            anchor="c",
            mask="auto",
        )

    def _paragraph_style(
        self,
        style: ParagraphStyle,
        theme: Theme,
        base_style: RLParagraphStyle,
        *,
        default_unit: str = "in",
    ) -> RLParagraphStyle:
        alignment = theme.resolve_paragraph_text_alignment(style)
        left_indent = style.left_indent_in_inches(default_unit) or 0
        right_indent = style.right_indent_in_inches(default_unit) or 0
        first_line_indent = style.first_line_indent_in_inches(default_unit) or 0
        return RLParagraphStyle(
            (
                f"Paragraph{alignment}{style.space_before}{style.space_after}{style.leading}"
                f"{left_indent}{right_indent}{first_line_indent}"
            ),
            parent=base_style,
            fontName=self._resolve_font(theme.resolve_body_font(), False, False),
            fontSize=theme.typography.body_font_size,
            leading=style.leading or theme.typography.body_font_size * 1.35,
            spaceBefore=style.space_before or 0,
            spaceAfter=style.space_after or 0,
            alignment=ALIGNMENTS[alignment],
            leftIndent=left_indent * inch,
            rightIndent=right_indent * inch,
            firstLineIndent=first_line_indent * inch,
            keepWithNext=bool(style.keep_with_next),
            textColor=colors.black,
        )

    def _assert_box_child_supported(self, child: object) -> None:
        if isinstance(
            child,
            (
                CommentList,
                FootnoteList,
                ReferenceList,
                TableOfContents,
                ListOfTables,
                ListOfFigures,
                Part,
            ),
        ):
            raise OODocsError(
                f"{type(child).__name__} cannot be rendered inside a Box"
            )

    def _render_table(
        self,
        block: Table,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
        unit: str,
        *,
        text_width: float,
        in_box: bool = False,
    ) -> list[object]:
        table_style = theme.stylesheet.resolve("table", block.style, OODocsTableStyle())
        split_table = block._resolve_split()
        media_placement = block._resolve_placement()
        body_style = self._paragraph_style(ParagraphStyle(space_after=0), theme, styles["BodyText"])
        layout = build_table_layout(block.header_rows, block.rows)
        table_rows: list[list[object]] = [["" for _ in range(layout.column_count)] for _ in range(layout.row_count)]
        top_padding, right_padding, bottom_padding, left_padding = table_style.cell_padding.to_points()
        style_commands: list[tuple[str, tuple[int, int], tuple[int, int], object]] = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), left_padding),
            ("RIGHTPADDING", (0, 0), (-1, -1), right_padding),
            ("TOPPADDING", (0, 0), (-1, -1), top_padding),
            ("BOTTOMPADDING", (0, 0), (-1, -1), bottom_padding),
        ]
        style_commands[0:0] = self._table_border_style_commands(table_style, layout)
        for placement in layout.placements:
            effective_style = block._effective_cell_style(
                placement,
                stylesheet=theme.stylesheet,
                table_style=table_style,
            )
            cell_bold = bool(effective_style.bold)
            cell_italic = bool(effective_style.italic)
            cell_text_color = (
                colors.HexColor(f"#{effective_style.text_color}")
                if effective_style.text_color is not None
                else colors.black
            )
            paragraph_style = RLParagraphStyle(
                f"TableCell{placement.row}_{placement.column}_{int(cell_bold)}_{int(cell_italic)}",
                parent=body_style,
                fontName=self._resolve_font(theme.resolve_body_font(), cell_bold, cell_italic),
                textColor=cell_text_color,
            )
            cell_text_alignment = self._table_cell_text_alignment(
                placement,
                block,
                theme.stylesheet,
                table_style,
            ) or "left"
            paragraph_style = RLParagraphStyle(
                f"{paragraph_style.name}Cell{cell_text_alignment}",
                parent=paragraph_style,
                alignment=ALIGNMENTS[cell_text_alignment],
            )
            table_rows[placement.row][placement.column] = RLParagraph(
                self._inline_markup(
                    placement.cell.content.content,
                    theme,
                    render_index,
                    base_font_name=paragraph_style.fontName,
                    base_size=paragraph_style.fontSize,
                    base_bold=cell_bold,
                    base_italic=cell_italic,
                ),
                paragraph_style,
            )
            if placement.cell.colspan > 1 or placement.cell.rowspan > 1:
                style_commands.append(
                    (
                        "SPAN",
                        (placement.column, placement.row),
                        (
                            placement.column + placement.cell.colspan - 1,
                            placement.row + placement.cell.rowspan - 1,
                        ),
                    )
                )
            cell_vertical_alignment = self._table_cell_vertical_alignment(
                placement,
                block,
                theme.stylesheet,
                table_style,
            )
            if cell_vertical_alignment is not None:
                style_commands.append(
                    (
                        "VALIGN",
                        (placement.column, placement.row),
                        (
                            placement.column + placement.cell.colspan - 1,
                            placement.row + placement.cell.rowspan - 1,
                        ),
                        TABLE_CELL_VERTICAL_ALIGNMENTS[cell_vertical_alignment],
                    )
                )
            style_commands.append(
                (
                    "ALIGN",
                    (placement.column, placement.row),
                    (
                        placement.column + placement.cell.colspan - 1,
                        placement.row + placement.cell.rowspan - 1,
                    ),
                    TABLE_CELL_ALIGNMENTS[cell_text_alignment],
                )
            )
            if effective_style.background_color is not None:
                style_commands.append(
                    (
                        "BACKGROUND",
                        (placement.column, placement.row),
                        (
                            placement.column + placement.cell.colspan - 1,
                            placement.row + placement.cell.rowspan - 1,
                        ),
                        colors.HexColor(f"#{effective_style.background_color}"),
                    )
                )

        resolved_widths = block._column_widths_in_inches(
            unit,
            available_width=text_width,
        )
        column_widths = [width * inch for width in resolved_widths] if resolved_widths is not None else None
        table = RLTable(
            table_rows,
            colWidths=column_widths,
            hAlign=FLOWABLE_ALIGNMENTS[theme.blocks.table_block_alignment],
            repeatRows=layout.header_row_count if split_table or table_style.repeat_header_rows else 0,
        )
        table.splitByRow = 1
        table.setStyle(TableStyle(style_commands))

        story: list[object] = []
        if block.caption is not None and theme.captions.table_caption_position == "above":
            caption_style = RLParagraphStyle(
                "TableCaption",
                parent=body_style,
                fontSize=theme.caption_size(),
                alignment=ALIGNMENTS[theme.captions.caption_text_alignment],
                spaceBefore=0,
                spaceAfter=6,
            )
            caption_fragments = self._caption_fragments(
                theme.resolve_caption_label("table", "caption"),
                render_index.table_number(block),
                block.caption,
            )
            story.append(
                self._caption_paragraph(
                    render_index.table_anchor(block),
                    caption_fragments,
                    caption_style,
                    theme,
                    render_index,
                    notify_kind="TableListEntry",
                )
            )
        story.append(table)
        if block.caption is not None and theme.captions.table_caption_position == "below":
            caption_style = RLParagraphStyle(
                "TableCaption",
                parent=body_style,
                fontSize=theme.caption_size(),
                alignment=ALIGNMENTS[theme.captions.caption_text_alignment],
                spaceBefore=6,
                spaceAfter=12,
            )
            caption_fragments = self._caption_fragments(
                theme.resolve_caption_label("table", "caption"),
                render_index.table_number(block),
                block.caption,
            )
            story.append(
                self._caption_paragraph(
                    render_index.table_anchor(block),
                    caption_fragments,
                    caption_style,
                    theme,
                    render_index,
                    notify_kind="TableListEntry",
                )
            )
        elif not in_box:
            story.append(Spacer(1, 12))
        if not split_table:
            story = [KeepTogether(story)]
        return self._apply_pdf_media_placement(story, media_placement, in_box=in_box)

    def _table_border_style_commands(
        self,
        table_style: OODocsTableStyle,
        layout: object,
    ) -> list[tuple[object, ...]]:
        commands: list[tuple[object, ...]] = []
        if table_style.border.color is not None and table_style.border.width > 0:
            commands.append(
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    table_style.border.width_points(),
                    colors.HexColor(f"#{table_style.border.color}"),
                )
            )
        if layout.row_count == 0:
            return commands
        if (
            table_style.top_rule is not None
            and table_style.top_rule.color is not None
            and table_style.top_rule.width > 0
        ):
            commands.append(
                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    table_style.top_rule.width_points(),
                    colors.HexColor(f"#{table_style.top_rule.color}"),
                )
            )
        if (
            layout.header_row_count > 0
            and table_style.header_rule is not None
            and table_style.header_rule.color is not None
            and table_style.header_rule.width > 0
        ):
            header_row = layout.header_row_count - 1
            commands.append(
                (
                    "LINEBELOW",
                    (0, header_row),
                    (-1, header_row),
                    table_style.header_rule.width_points(),
                    colors.HexColor(f"#{table_style.header_rule.color}"),
                )
            )
        if (
            table_style.bottom_rule is not None
            and table_style.bottom_rule.color is not None
            and table_style.bottom_rule.width > 0
        ):
            bottom_row = layout.row_count - 1
            commands.append(
                (
                    "LINEBELOW",
                    (0, bottom_row),
                    (-1, bottom_row),
                    table_style.bottom_rule.width_points(),
                    colors.HexColor(f"#{table_style.bottom_rule.color}"),
                )
            )
        return commands

    def _apply_pdf_media_placement(
        self,
        story: list[object],
        placement: str,
        *,
        in_box: bool = False,
    ) -> list[object]:
        if in_box:
            return story
        if placement == "page":
            return [RLPageBreak(), *story, RLPageBreak()]
        if placement == "top":
            return [RLPageBreak(), *story]
        if placement == "float":
            return self._mark_float_story(story)
        return story

    def _table_cell_text_alignment(
        self,
        placement: object,
        block: Table,
        stylesheet: object | None = None,
        table_style: OODocsTableStyle | None = None,
    ) -> str | None:
        return block._effective_cell_style(
            placement,
            stylesheet=stylesheet,
            table_style=table_style,
        ).text_alignment

    def _table_cell_vertical_alignment(
        self,
        placement: object,
        block: Table,
        stylesheet: object | None = None,
        table_style: OODocsTableStyle | None = None,
    ) -> str | None:
        return block._effective_cell_style(
            placement,
            stylesheet=stylesheet,
            table_style=table_style,
        ).vertical_alignment

    def _render_list(
        self,
        block: BulletList | NumberedList,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
        unit: str,
        *,
        depth: int = 0,
        add_trailing_spacer: bool = True,
    ) -> list[object]:
        item_block_style = theme.stylesheet.resolve(
            "paragraph",
            ParagraphStyle(space_after=3),
            ParagraphStyle(space_after=3),
        )
        item_style = self._paragraph_style(
            item_block_style,
            theme,
            styles["BodyText"],
            default_unit=unit,
        )
        marker_style = RLParagraphStyle(
            "ListMarker",
            parent=item_style,
            alignment=TA_RIGHT,
            spaceAfter=3,
        )
        list_style = theme.stylesheet.resolve(
            "list",
            block.style,
            theme.list_style(ordered=isinstance(block, NumberedList)),
        )
        if depth:
            list_style = replace(list_style, indent=list_style.indent + depth * 0.22)
        marker_width = max(list_style.indent * inch, 0.35 * inch)
        rows: list[list[object]] = []
        for index, item in enumerate(block.items):
            marker = list_style.marker_for(index)
            marker_markup = escape(marker) if marker else "&nbsp;"
            marker_paragraph = RLParagraph(marker_markup, marker_style)
            content_paragraph = RLParagraph(
                self._anchor_markup(render_index.block_anchor(item))
                + self._inline_markup(
                    item.content,
                    theme,
                    render_index,
                    base_font_name=item_style.fontName,
                    base_size=item_style.fontSize,
                ),
                item_style,
            )
            child_flowables: list[object] = [content_paragraph]
            for child_list in block.item_children[index]:
                child_flowables.extend(
                    self._render_list(
                        child_list,
                        theme,
                        styles,
                        render_index,
                        unit,
                        depth=depth + 1,
                        add_trailing_spacer=False,
                    )
                )
            rows.append(
                [
                    marker_paragraph,
                    child_flowables if len(child_flowables) > 1 else content_paragraph,
                ]
            )
        table = RLTable(rows, colWidths=[marker_width, None], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (1, 0), (1, -1), max(list_style.marker_gap * inch, 4)),
                ]
            )
        )
        flowables: list[object] = [table]
        if add_trailing_spacer:
            flowables.append(Spacer(1, 8))
        return flowables

    def _render_box(self, block: Box, theme: Theme, styles: object, render_index: RenderIndex, settings: object, unit: str) -> list[object]:
        box_style = theme.stylesheet.resolve("box", block.style, None)
        body_style = self._paragraph_style(ParagraphStyle(space_after=0), theme, styles["BodyText"])
        rows: list[list[object]] = []
        row_styles: list[tuple[str, tuple[int, int], tuple[int, int], object]] = []
        if block.title is not None:
            title_style = RLParagraphStyle(
                "BoxTitle",
                parent=body_style,
                fontName=self._resolve_font(theme.resolve_body_font(), True, False),
                spaceAfter=6,
                textColor=colors.HexColor(f"#{box_style.title_text_color or '000000'}"),
            )
            rows.append(
                [
                    RLParagraph(
                        self._inline_markup(
                            block.title,
                            theme,
                            render_index,
                            base_font_name=title_style.fontName,
                            base_size=title_style.fontSize,
                            base_bold=True,
                            base_italic=False,
                        ),
                        title_style,
                    )
                ]
            )
            if box_style.title_background_color is not None:
                row_styles.append(
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, 0),
                        colors.HexColor(f"#{box_style.title_background_color}"),
                    )
                )
        for child in block.children:
            self._assert_box_child_supported(child)
            context = PdfRenderContext(
                theme=theme,
                render_index=render_index,
                settings=settings,
                unit=unit,
                styles=styles,
                in_box=True,
            )
            for flowable in self._render_block(child, context):
                if isinstance(flowable, KeepTogether):
                    rows.extend([[nested]] for nested in flowable._content)
                    continue
                rows.append([flowable])
        if not rows:
            rows.append([Spacer(1, 1)])

        column_widths = None
        if box_style.width is not None:
            column_widths = [length_to_inches(box_style.width, box_style.unit or unit) * inch]
        table = RLTable(
            rows,
            colWidths=column_widths,
            hAlign=FLOWABLE_ALIGNMENTS[box_style.block_alignment or theme.blocks.box_block_alignment],
            repeatRows=0,
        )
        top_padding, right_padding, bottom_padding, left_padding = box_style.padding.to_points()
        style_commands: list[tuple[str, tuple[int, int], tuple[int, int], object]] = [
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(f"#{box_style.background_color}")),
            ("LEFTPADDING", (0, 0), (-1, -1), left_padding),
            ("RIGHTPADDING", (0, 0), (-1, -1), right_padding),
            ("TOPPADDING", (0, 0), (-1, -1), top_padding),
            ("BOTTOMPADDING", (0, 0), (-1, -1), bottom_padding),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        if box_style.border.color is not None and box_style.border.width > 0:
            style_commands.insert(
                1,
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    box_style.border.width_points(),
                    colors.HexColor(f"#{box_style.border.color}"),
                ),
            )
        style_commands.extend(row_styles)
        table.setStyle(TableStyle(style_commands))
        elements: list[object] = []
        anchor = render_index.block_anchor(block)
        if anchor is not None:
            elements.append(RLParagraph(self._anchor_markup(anchor), body_style))
        elements.extend([table, Spacer(1, box_style.space_after)])
        return elements

    def _render_code_block(
        self,
        block: CodeBlock,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
        settings: DocumentSettings,
        in_box: bool,
    ) -> list[object]:
        font_size = max(theme.typography.body_font_size - 1, 8)
        code_style = RLParagraphStyle(
            "CodeBlock",
            parent=styles["Code"],
            fontName=self._resolve_font(theme.resolve_monospace_font(), False, False),
            fontSize=font_size,
            leading=font_size * 1.35,
            leftIndent=0,
            rightIndent=0,
            spaceBefore=0,
            spaceAfter=0,
        )

        anchor = render_index.block_anchor(block)
        show_label = bool(block.language and block.show_language)
        cell_flowables: list[object] = []
        if show_label:
            label_style = RLParagraphStyle(
                "CodeBlockLabel",
                parent=styles["BodyText"],
                fontName=self._resolve_font(theme.resolve_monospace_font(), False, False),
                fontSize=max(theme.caption_size() - 1, 7),
                leading=max(theme.caption_size() - 1, 7) * 1.2,
                textColor=colors.HexColor("#6F7D90"),
                alignment=TA_LEFT if block.language_position.endswith("left") else TA_RIGHT,
                spaceBefore=0,
                spaceAfter=4 if block.language_position.startswith("top") else 0,
            )
            label_markup = escape(block.language.upper())
            if block.language_position.startswith("top"):
                label_markup = self._anchor_markup(anchor) + label_markup
                anchor = None
                cell_flowables.append(RLParagraph(label_markup, label_style))

        cell_flowables.append(
            CodeBlockFlowable(
                syntax_tokens(block.code, block.language),
                font_names={
                    (False, False): self._resolve_font(theme.resolve_monospace_font(), False, False),
                    (True, False): self._resolve_font(theme.resolve_monospace_font(), True, False),
                    (False, True): self._resolve_font(theme.resolve_monospace_font(), False, True),
                    (True, True): self._resolve_font(theme.resolve_monospace_font(), True, True),
                },
                font_size=code_style.fontSize,
                leading=code_style.leading,
                anchor=anchor,
            )
        )
        if show_label and block.language_position.startswith("bottom"):
            label_style.spaceBefore = 4
            cell_flowables.append(RLParagraph(escape(block.language.upper()), label_style))

        block_style = theme.stylesheet.resolve("paragraph", block.style, ParagraphStyle())
        block_alignment = theme.resolve_paragraph_text_alignment(block_style)
        column_widths = None if in_box else [settings.text_width_in_inches() * inch]
        table = RLTable(
            [[cell_flowables]],
            colWidths=column_widths,
            hAlign=FLOWABLE_ALIGNMENTS[block_alignment if block_alignment in FLOWABLE_ALIGNMENTS else "left"],
            repeatRows=0,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FA")),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#D8E0EB")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return [KeepTogether([table, Spacer(1, block_style.space_after or 0)])]

    def _render_equation(
        self,
        block: Equation,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
    ) -> list[object]:
        block_style = theme.stylesheet.resolve("paragraph", block.style, ParagraphStyle())
        equation_style = RLParagraphStyle(
            "EquationBlock",
            parent=styles["BodyText"],
            fontName=self._resolve_font(theme.resolve_body_font(), False, False),
            fontSize=max(theme.typography.body_font_size + 1, 12),
            leading=max(theme.typography.body_font_size + 1, 12) * 1.3,
            alignment=ALIGNMENTS[theme.resolve_paragraph_text_alignment(block_style)],
            spaceAfter=block_style.space_after or 0,
            textColor=colors.black,
        )
        equation_markup = self._anchor_markup(render_index.block_anchor(block)) + self._math_markup(
            Math(block.expression),
            theme,
            base_font_name=equation_style.fontName,
            base_size=equation_style.fontSize,
        )
        number = render_index.equation_number(block)
        if number is not None:
            equation_markup += f" ({number})"
        return [RLParagraph(equation_markup, equation_style)]

    def _render_figure(
        self,
        block: Figure,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
        unit: str,
        *,
        in_box: bool = False,
    ) -> list[object]:
        placement = block.resolved_placement()
        image = self._figure_image(block, theme, unit)

        body_style = self._paragraph_style(ParagraphStyle(space_after=0), theme, styles["BodyText"])
        elements: list[object] = [image]
        if block.caption is not None and theme.captions.figure_caption_position == "above":
            caption_style = RLParagraphStyle(
                "FigureCaption",
                parent=body_style,
                fontSize=theme.caption_size(),
                alignment=ALIGNMENTS[theme.captions.caption_text_alignment],
                spaceBefore=0,
                spaceAfter=2 if in_box else 6,
            )
            elements = [
                self._caption_paragraph(
                    render_index.figure_anchor(block),
                    self._caption_fragments(
                        theme.resolve_caption_label("figure", "caption"),
                        render_index.figure_number(block),
                        block.caption,
                    ),
                    caption_style,
                    theme,
                    render_index,
                    notify_kind="FigureListEntry",
                )
            ] + elements
        if block.caption is not None and theme.captions.figure_caption_position == "below":
            caption_style = RLParagraphStyle(
                "FigureCaption",
                parent=body_style,
                fontSize=theme.caption_size(),
                alignment=ALIGNMENTS[theme.captions.caption_text_alignment],
                spaceBefore=2 if in_box else 6,
                spaceAfter=0 if in_box else 12,
            )
            elements.append(
                self._caption_paragraph(
                    render_index.figure_anchor(block),
                    self._caption_fragments(
                        theme.resolve_caption_label("figure", "caption"),
                        render_index.figure_number(block),
                        block.caption,
                    ),
                    caption_style,
                    theme,
                    render_index,
                    notify_kind="FigureListEntry",
                )
            )
        elif not in_box:
            elements.append(Spacer(1, 12))
        return self._apply_pdf_media_placement([KeepTogether(elements)], placement, in_box=in_box)

    def _render_subfigure_group(
        self,
        block: SubFigureGroup,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
        unit: str,
        *,
        in_box: bool = False,
    ) -> list[object]:
        placement = block.resolved_placement()
        body_style = self._paragraph_style(ParagraphStyle(space_after=0), theme, styles["BodyText"])
        caption_style = RLParagraphStyle(
            "FigureCaption",
            parent=body_style,
            fontSize=theme.caption_size(),
            alignment=ALIGNMENTS[theme.captions.caption_text_alignment],
            spaceBefore=0,
            spaceAfter=6,
        )
        subcaption_style = RLParagraphStyle(
            "SubFigureCaption",
            parent=body_style,
            fontSize=theme.caption_size(),
            alignment=ALIGNMENTS[theme.captions.caption_text_alignment],
            spaceBefore=2,
            spaceAfter=0,
        )

        table_rows: list[list[object]] = []
        for row_start in range(0, len(block.subfigures), block.columns):
            row: list[object] = []
            for column_index in range(block.columns):
                index = row_start + column_index
                if index >= len(block.subfigures):
                    row.append(Spacer(1, 1))
                    continue
                subfigure = block.subfigures[index]
                cell_elements: list[object] = [self._figure_image(subfigure, theme, unit)]
                if subfigure.caption is not None:
                    cell_elements.append(
                        RLParagraph(
                            self._anchor_markup(render_index.figure_anchor(subfigure))
                            + self._inline_markup(
                                self._subfigure_caption_fragments(
                                    block.formatted_label_for_index(index),
                                    subfigure.caption,
                                ),
                                theme,
                                render_index,
                                base_font_name=subcaption_style.fontName,
                                base_size=subcaption_style.fontSize,
                            ),
                            subcaption_style,
                        )
                    )
                else:
                    anchor = render_index.figure_anchor(subfigure)
                    if anchor is not None:
                        cell_elements.insert(0, RLParagraph(self._anchor_markup(anchor), subcaption_style))
                row.append(cell_elements)
            table_rows.append(row)

        gap_points = length_to_inches(block.column_gap, block.unit or unit) * inch
        subfigure_table = RLTable(
            table_rows,
            hAlign=FLOWABLE_ALIGNMENTS[theme.blocks.figure_block_alignment],
            repeatRows=0,
        )
        subfigure_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), gap_points / 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), gap_points / 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        elements: list[object] = []
        if block.caption is not None and theme.captions.figure_caption_position == "above":
            elements.append(
                self._caption_paragraph(
                    render_index.figure_anchor(block),
                    self._caption_fragments(
                        theme.resolve_caption_label("figure", "caption"),
                        render_index.figure_number(block),
                        block.caption,
                    ),
                    caption_style,
                    theme,
                    render_index,
                    notify_kind="FigureListEntry",
                )
            )
        elements.append(subfigure_table)
        if block.caption is not None and theme.captions.figure_caption_position == "below":
            below_caption_style = RLParagraphStyle(
                "FigureCaptionBelow",
                parent=caption_style,
                spaceBefore=6,
                spaceAfter=0 if in_box else 12,
            )
            elements.append(
                self._caption_paragraph(
                    render_index.figure_anchor(block),
                    self._caption_fragments(
                        theme.resolve_caption_label("figure", "caption"),
                        render_index.figure_number(block),
                        block.caption,
                    ),
                    below_caption_style,
                    theme,
                    render_index,
                    notify_kind="FigureListEntry",
                )
            )
        elif not in_box:
            elements.append(Spacer(1, 12))
        return self._apply_pdf_media_placement([KeepTogether(elements)], placement, in_box=in_box)

    def _figure_image(self, block: Figure | SubFigure, theme: Theme, unit: str) -> RLImage:
        image = RLImage(self._figure_image_source(block, unit))
        image.hAlign = FLOWABLE_ALIGNMENTS[theme.blocks.figure_block_alignment]
        resolved_width = block.width_in_inches(unit)
        resolved_height = block.height_in_inches(unit)
        if resolved_width is not None and resolved_height is not None:
            image.drawWidth = resolved_width * inch
            image.drawHeight = resolved_height * inch
        elif resolved_width is not None:
            target_width = resolved_width * inch
            scale = target_width / image.drawWidth
            image.drawWidth = target_width
            image.drawHeight = image.drawHeight * scale
        elif resolved_height is not None:
            target_height = resolved_height * inch
            scale = target_height / image.drawHeight
            image.drawHeight = target_height
            image.drawWidth = image.drawWidth * scale
        return image

    def _figure_image_source(self, block: Figure | SubFigure, unit: str) -> str | BytesIO:
        source = block.image_source
        if block.crop is not None or block.rotation:
            return processed_image_source_to_buffer(
                source,
                image_format=block.image_format,
                image_dpi=block.image_dpi,
                crop=block.crop,
                rotation=block.rotation,
                default_unit=block.unit or unit,
                usage="PDF rendering",
            )
        if isinstance(source, Path):
            return str(source)
        return image_source_to_buffer(
            source,
            image_format=block.image_format,
            image_dpi=block.image_dpi,
            usage="PDF rendering",
        )

    def _image_box_source(self, image_box: ImageBox) -> str | ImageReader:
        source = image_box.image_source
        if isinstance(source, Path):
            return str(source)
        return ImageReader(
            image_source_to_buffer(
                source,
                image_format=image_box.image_format,
                image_dpi=image_box.image_dpi,
                usage="PDF positioned image rendering",
            )
        )

    def _inline_markup(
        self,
        fragments: list[Text],
        theme: Theme,
        render_index: RenderIndex,
        *,
        base_font_name: str | None = None,
        base_size: float | None = None,
        base_bold: bool = False,
        base_italic: bool = False,
    ) -> str:
        parts = [
            self._fragment_markup(
                fragment,
                theme,
                render_index,
                base_font_name=base_font_name,
                base_size=base_size,
                base_bold=base_bold,
                base_italic=base_italic,
            )
            for fragment in fragments
        ]
        return "".join(parts) or "&nbsp;"

    def _heading_fragments(self, title: list[Text], number_label: str | None) -> list[Text]:
        if not number_label:
            return title
        return [Text(f"{number_label} ")] + title

    def _fragment_markup(
        self,
        fragment: Text,
        theme: Theme,
        render_index: RenderIndex,
        *,
        base_font_name: str | None,
        base_size: float | None,
        base_bold: bool,
        base_italic: bool,
    ) -> str:
        if isinstance(fragment, ImageBox):
            source = fragment.image_source
            if not isinstance(source, Path):
                return ""
            width = length_to_inches(fragment.width, fragment.unit or "in") * inch
            height = length_to_inches(fragment.height, fragment.unit or "in") * inch
            return (
                f'<img src="{escape(str(source))}" '
                f'width="{width:.2f}" height="{height:.2f}" valign="middle"/>'
            )
        if isinstance(fragment, TextBox):
            return self._inline_markup(
                fragment.content,
                theme,
                render_index,
                base_font_name=base_font_name,
                base_size=fragment.font_size or base_size,
                base_bold=base_bold,
                base_italic=base_italic,
            )
        if isinstance(fragment, Shape):
            return ""
        if isinstance(fragment, InlineChip):
            return self._inline_chip_markup(
                fragment,
                theme,
                base_font_name=base_font_name,
                base_size=base_size,
            )
        if isinstance(fragment, Hyperlink):
            return self._link_markup(
                fragment.target,
                self._inline_markup(
                    fragment.label,
                    theme,
                    render_index,
                    base_font_name=base_font_name,
                    base_size=base_size,
                    base_bold=base_bold,
                    base_italic=base_italic,
                ),
                internal=fragment.internal,
            )
        if isinstance(fragment, _BlockReference):
            label_markup = (
                self._inline_markup(
                    fragment.label,
                    theme,
                    render_index,
                    base_font_name=base_font_name,
                    base_size=base_size,
                    base_bold=base_bold,
                    base_italic=base_italic,
                )
                if fragment.label is not None
                else self._styled_text_markup(
                    self._resolve_block_reference(fragment.target, theme, render_index),
                    fragment,
                    theme,
                    base_font_name=base_font_name,
                    base_size=base_size,
                    base_bold=base_bold,
                    base_italic=base_italic,
                )
            )
            return self._link_markup(
                self._block_reference_anchor(fragment.target, render_index),
                label_markup,
                internal=True,
            )
        if isinstance(fragment, Citation):
            citation_entry = render_index.citation_entry(fragment.target)
            citation_label = format_citation_label(
                citation_entry.source,
                citation_entry.number,
                theme.citations.citation_style,
            )
            return self._link_markup(
                citation_entry.anchor,
                self._styled_text_markup(
                    citation_label,
                    fragment,
                    theme,
                    base_font_name=base_font_name,
                    base_size=base_size,
                    base_bold=base_bold,
                    base_italic=base_italic,
                ),
                internal=True,
            )
        if isinstance(fragment, Comment):
            visible = self._styled_text_markup(
                fragment.value,
                fragment,
                theme,
                base_font_name=base_font_name,
                base_size=base_size,
                base_bold=base_bold,
                base_italic=base_italic,
            )
            return f"{visible}<super>{escape(self._comment_marker(fragment, render_index))}</super>"
        if isinstance(fragment, Footnote):
            visible = self._styled_text_markup(
                fragment.value,
                fragment,
                theme,
                base_font_name=base_font_name,
                base_size=base_size,
                base_bold=base_bold,
                base_italic=base_italic,
            )
            return f"{visible}<super>{escape(self._footnote_marker(fragment, render_index))}</super>"
        if isinstance(fragment, Math):
            return self._math_markup(
                fragment,
                theme,
                base_font_name=base_font_name,
                base_size=base_size,
                base_bold=base_bold,
                base_italic=base_italic,
            )
        return self._styled_text_markup(
            self._resolve_fragment_text(fragment, theme, render_index),
            fragment,
            theme,
            base_font_name=base_font_name,
            base_size=base_size,
            base_bold=base_bold,
            base_italic=base_italic,
        )

    def _inline_chip_markup(
        self,
        fragment: InlineChip,
        theme: Theme,
        *,
        base_font_name: str | None,
        base_size: float | None,
    ) -> str:
        chip_style = theme.stylesheet.resolve("chip", fragment.chip_style, None)
        base_size = fragment.style.font_size or base_size or theme.typography.body_font_size
        size = max(base_size + chip_style.font_size_delta, 6.0)
        font_name = self._resolve_font(
            chip_style.font_name or fragment.style.font_name or theme.resolve_body_font(),
            chip_style.bold,
            chip_style.italic,
        )
        text = escape(fragment.display_text(chip_style)).replace("\n", " ")
        font_attrs = [
            f'face="{font_name}"',
            f'size="{size}"',
            f'color="#{chip_style.text_color}"',
            f'backColor="#{chip_style.background_color}"',
        ]
        if base_font_name is not None and font_name == base_font_name:
            font_attrs.pop(0)
        return f"<font {' '.join(font_attrs)}>&#160;{text}&#160;</font>"

    def _styled_text_markup(
        self,
        text_value: str,
        fragment: Text,
        theme: Theme,
        *,
        base_font_name: str | None,
        base_size: float | None,
        base_bold: bool,
        base_italic: bool,
    ) -> str:
        rendered_text = text_value.upper() if fragment.style.uppercase else text_value
        text = escape(rendered_text).replace("\n", "<br/>")
        bold = base_bold if fragment.style.bold is None else fragment.style.bold
        italic = base_italic if fragment.style.italic is None else fragment.style.italic
        font_name = (
            base_font_name
            if (
                fragment.style.font_name is None
                and fragment.style.bold is None
                and fragment.style.italic is None
                and base_font_name is not None
            )
            else self._resolve_font(fragment.style.font_name or theme.resolve_body_font(), bold, italic)
        )
        size = fragment.style.font_size or base_size or theme.typography.body_font_size

        font_attrs: list[str] = []
        if base_font_name is None or font_name != base_font_name:
            font_attrs.append(f'face="{font_name}"')
        if base_size is None or size != base_size:
            font_attrs.append(f'size="{size}"')
        if fragment.style.text_color is not None:
            font_attrs.append(f'color="#{fragment.style.text_color}"')
        if fragment.style.highlight_color is not None:
            font_attrs.append(f'backColor="#{fragment.style.highlight_color}"')
        wrapped = text if not font_attrs else f"<font {' '.join(font_attrs)}>{text}</font>"
        if fragment.style.underline:
            wrapped = f"<u>{wrapped}</u>"
        if fragment.style.strikethrough:
            wrapped = f"<strike>{wrapped}</strike>"
        if fragment.style.superscript:
            wrapped = f"<super>{wrapped}</super>"
        if fragment.style.subscript:
            wrapped = f"<sub>{wrapped}</sub>"
        return wrapped

    def _math_markup(
        self,
        fragment: Math,
        theme: Theme,
        *,
        base_font_name: str | None,
        base_size: float | None,
        base_bold: bool = False,
        base_italic: bool = False,
    ) -> str:
        parts: list[str] = []
        for segment in parse_latex_segments(fragment.value):
            piece = self._styled_text_markup(
                segment.text,
                fragment,
                theme,
                base_font_name=base_font_name,
                base_size=base_size,
                base_bold=base_bold,
                base_italic=base_italic,
            )
            if segment.vertical_align == SUPERSCRIPT:
                piece = f"<super>{piece}</super>"
            elif segment.vertical_align == SUBSCRIPT:
                piece = f"<sub>{piece}</sub>"
            parts.append(piece)
        return "".join(parts) or "&nbsp;"

    def _resolve_font(self, font_name: str, bold: bool, italic: bool) -> str:
        system_font = self._register_system_font(font_name, bold, italic)
        if system_font is not None:
            return system_font
        aliased_font_name = FONT_FAMILY_ALIASES.get(font_name.lower(), font_name)
        font_name = aliased_font_name
        if font_name in PDF_FONT_VARIANTS:
            return PDF_FONT_VARIANTS[font_name][(bold, italic)]
        if font_name in pdfmetrics.getRegisteredFontNames():
            return font_name
        fallback = "Courier" if "Courier" in font_name else "Times-Roman" if "Times" in font_name else "Helvetica"
        return PDF_FONT_VARIANTS[fallback][(bold, italic)]

    def _register_system_font(self, font_name: str, bold: bool, italic: bool) -> str | None:
        key = (font_name, bold, italic)
        if key in self._registered_system_fonts:
            return self._registered_system_fonts[key]

        for candidate_name, variants in SYSTEM_FONT_VARIANTS.items():
            if candidate_name.lower() != font_name.lower():
                continue
            for font_path in variants[(bold, italic)]:
                if not Path(font_path).exists():
                    continue
                registered_name = f"{candidate_name}-{int(bold)}-{int(italic)}"
                if registered_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(registered_name, font_path))
                self._registered_system_fonts[key] = registered_name
                return registered_name
        return None

    def _resolve_fragment_text(self, fragment: Text, theme: Theme, render_index: RenderIndex) -> str:
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

    def _flatten_fragments(
        self,
        fragments: list[Text],
        theme: Theme,
        render_index: RenderIndex,
    ) -> str:
        return "".join(
            self._resolve_fragment_text(fragment, theme, render_index)
            for fragment in fragments
        )

    def _anchor_markup(self, anchor: str | None) -> str:
        if not anchor:
            return ""
        return f'<a name="{escape(anchor)}"/>'

    def _link_markup(
        self,
        target: str | None,
        inner_markup: str,
        *,
        internal: bool,
    ) -> str:
        if not target:
            return inner_markup
        href = f"#{target}" if internal else target
        return f'<a href="{escape(href)}">{inner_markup}</a>'

    def _block_reference_anchor(
        self,
        target: object,
        render_index: RenderIndex,
    ) -> str | None:
        if isinstance(target, Table):
            return render_index.table_anchor(target)
        if isinstance(target, (Figure, SubFigure, SubFigureGroup)):
            return render_index.figure_anchor(target)
        if isinstance(target, (Part, Section)):
            return render_index.heading_anchor(target)
        return render_index.block_anchor(target)

    def _resolve_block_reference(
        self,
        target: object,
        theme: Theme,
        render_index: RenderIndex,
    ) -> str:
        if isinstance(target, Table):
            number = render_index.table_number(target)
            if number is None:
                raise OODocsError("Table references require the target table to have a caption and be included in the document")
            label = theme.resolve_caption_label("table", "reference")
            return f"{label} {number}"

        if isinstance(target, (Figure, SubFigure, SubFigureGroup)):
            number = render_index.figure_number(target)
            if number is None:
                raise OODocsError("Figure references require the target figure to have a caption and be included in the document")
            if isinstance(target, SubFigure):
                label = render_index.subfigure_label(target)
                if label is None:
                    raise OODocsError("Subfigure references require the target subfigure to belong to a captioned SubFigureGroup")
                figure_label = theme.resolve_caption_label("figure", "reference")
                return f"{figure_label} {number}({label})"
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
                raise OODocsError("Equation references require the target equation to be included in the document")
            return f"Equation {number}"

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

    def _caption_fragments(self, label: str, number: int | None, caption: Paragraph) -> list[Text]:
        if number is None:
            return caption.content
        return [Text(f"{label} {number}. ")] + caption.content

    def _subfigure_caption_fragments(self, label: str, caption: Paragraph) -> list[Text]:
        return [Text(f"{label} ")] + caption.content

    def _caption_paragraph(
        self,
        anchor: str | None,
        fragments: list[Text],
        style: RLParagraphStyle,
        theme: Theme,
        render_index: RenderIndex,
        *,
        notify_kind: str,
    ) -> RLParagraph:
        paragraph = RLParagraph(
            self._anchor_markup(anchor)
            + self._inline_markup(
                fragments,
                theme,
                render_index,
                base_font_name=style.fontName,
                base_size=style.fontSize,
            ),
            style,
        )
        paragraph._oodocs_caption_list_entry = (  # type: ignore[attr-defined]
            notify_kind,
            self._flatten_fragments(fragments, theme, render_index),
            anchor,
        )
        return paragraph

    def _render_caption_list(
        self,
        block: ListOfTables | ListOfFigures,
        title: list[Text] | None,
        entries: list[object],
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
        default_title: str,
        label: str,
        *,
        notify_kind: str,
    ) -> list[object]:
        level = theme.generated_content.generated_heading_level
        bold, italic = theme.resolve_heading_emphasis(level)
        title_style = RLParagraphStyle(
            "GeneratedCaptionListTitle",
            parent=styles["Heading1"],
            fontName=self._resolve_font(theme.resolve_body_font(), bold, italic),
            fontSize=theme.resolve_heading_size(level),
            leading=theme.resolve_heading_size(level) * 1.2,
            spaceBefore=12,
            spaceAfter=6,
            alignment=ALIGNMENTS[theme.resolve_heading_text_alignment(level)],
            textColor=colors.black,
        )
        entry_style = self._paragraph_style(ParagraphStyle(space_after=3), theme, styles["BodyText"])
        story: list[object] = [
            RLParagraph(
                self._inline_markup(
                    title or [Text(default_title)],
                    theme,
                    render_index,
                    base_font_name=title_style.fontName,
                    base_size=title_style.fontSize,
                    base_bold=bold,
                    base_italic=italic,
                ),
                title_style,
            )
        ]
        if block.show_page_numbers:
            caption_list = FilteredTableOfContents(
                notifyKind=notify_kind,
                dotsMinLevel=0 if block.leader else -1,
                allowed_keys={entry.anchor for entry in entries},
            )
            caption_list.levelStyles = [entry_style]
            story.append(caption_list)
        else:
            for entry in entries:
                story.append(
                    RLParagraph(
                        self._link_markup(
                            entry.anchor,
                            self._inline_markup(
                                self._caption_fragments(
                                    label,
                                    entry.number,
                                    entry.block.caption,
                                ),
                                theme,
                                render_index,
                                base_font_name=entry_style.fontName,
                                base_size=entry_style.fontSize,
                            ),
                            internal=True,
                        ),
                        entry_style,
                    )
                )
        if entries:
            story.append(Spacer(1, 6))
        return story

    def _render_comment_list(
        self,
        title: list[Text] | None,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
    ) -> list[object]:
        level = theme.generated_content.generated_heading_level
        bold, italic = theme.resolve_heading_emphasis(level)
        title_style = RLParagraphStyle(
            "CommentListTitle",
            parent=styles["Heading1"],
            fontName=self._resolve_font(theme.resolve_body_font(), bold, italic),
            fontSize=theme.resolve_heading_size(level),
            leading=theme.resolve_heading_size(level) * 1.2,
            spaceBefore=0,
            spaceAfter=10,
            alignment=ALIGNMENTS[theme.resolve_heading_text_alignment(level)],
            textColor=colors.black,
        )
        entry_style = RLParagraphStyle(
            "CommentEntry",
            parent=styles["BodyText"],
            fontName=self._resolve_font(theme.resolve_body_font(), False, False),
            fontSize=theme.typography.body_font_size,
            leading=theme.typography.body_font_size * 1.35,
            leftIndent=18,
            firstLineIndent=-18,
            spaceAfter=6,
            textColor=colors.black,
        )
        story: list[object] = [
            RLPageBreak(),
            RLParagraph(
                self._inline_markup(
                    title or [Text(theme.resolve_generated_page_title("comment_list"))],
                    theme,
                    render_index,
                    base_font_name=title_style.fontName,
                    base_size=title_style.fontSize,
                    base_bold=bold,
                    base_italic=italic,
                ),
                title_style,
            ),
        ]
        for entry in render_index.comments:
            story.append(
                RLParagraph(
                    self._inline_markup(
                        [Text(f"[{entry.number}] ")] + entry.comment.comment,
                        theme,
                        render_index,
                        base_font_name=entry_style.fontName,
                        base_size=entry_style.fontSize,
                    ),
                    entry_style,
                )
            )
        return story

    def _render_footnote_list(
        self,
        title: list[Text] | None,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
    ) -> list[object]:
        level = theme.generated_content.generated_heading_level
        bold, italic = theme.resolve_heading_emphasis(level)
        title_style = RLParagraphStyle(
            "FootnoteListTitle",
            parent=styles["Heading1"],
            fontName=self._resolve_font(theme.resolve_body_font(), bold, italic),
            fontSize=theme.resolve_heading_size(level),
            leading=theme.resolve_heading_size(level) * 1.2,
            spaceBefore=0,
            spaceAfter=10,
            alignment=ALIGNMENTS[theme.resolve_heading_text_alignment(level)],
            textColor=colors.black,
        )
        entry_style = RLParagraphStyle(
            "FootnoteEntry",
            parent=styles["BodyText"],
            fontName=self._resolve_font(theme.resolve_body_font(), False, False),
            fontSize=theme.typography.body_font_size,
            leading=theme.typography.body_font_size * 1.35,
            leftIndent=18,
            firstLineIndent=-18,
            spaceAfter=6,
            textColor=colors.black,
        )
        story: list[object] = [
            RLPageBreak(),
            RLParagraph(
                self._inline_markup(
                    title or [Text(theme.resolve_generated_page_title("footnote_list"))],
                    theme,
                    render_index,
                    base_font_name=title_style.fontName,
                    base_size=title_style.fontSize,
                    base_bold=bold,
                    base_italic=italic,
                ),
                title_style,
            ),
        ]
        for entry in render_index.footnotes:
            story.append(
                RLParagraph(
                    self._inline_markup(
                        [Text(f"[{entry.number}] ")] + entry.footnote.note,
                        theme,
                        render_index,
                        base_font_name=entry_style.fontName,
                        base_size=entry_style.fontSize,
                    ),
                    entry_style,
                )
            )
        return story

    def _render_reference_list(
        self,
        title: list[Text] | None,
        theme: Theme,
        styles: object,
        render_index: RenderIndex,
    ) -> list[object]:
        level = theme.generated_content.generated_heading_level
        bold, italic = theme.resolve_heading_emphasis(level)
        title_style = RLParagraphStyle(
            "ReferenceListTitle",
            parent=styles["Heading1"],
            fontName=self._resolve_font(theme.resolve_body_font(), bold, italic),
            fontSize=theme.resolve_heading_size(level),
            leading=theme.resolve_heading_size(level) * 1.2,
            spaceBefore=0,
            spaceAfter=10,
            alignment=ALIGNMENTS[theme.resolve_heading_text_alignment(level)],
            textColor=colors.black,
        )
        entry_style = RLParagraphStyle(
            "ReferenceEntry",
            parent=styles["BodyText"],
            fontName=self._resolve_font(theme.resolve_body_font(), False, False),
            fontSize=theme.typography.body_font_size,
            leading=theme.typography.body_font_size * 1.35,
            leftIndent=18,
            firstLineIndent=-18,
            spaceAfter=6,
            textColor=colors.black,
        )
        story: list[object] = [
            RLPageBreak(),
            RLParagraph(
                self._inline_markup(
                    title or [Text(theme.resolve_generated_page_title("reference_list"))],
                    theme,
                    render_index,
                    base_font_name=title_style.fontName,
                    base_size=title_style.fontSize,
                    base_bold=bold,
                    base_italic=italic,
                ),
                title_style,
            ),
        ]
        for entry in render_index.citations:
            marker = reference_entry_marker(
                entry.number,
                citation_style=theme.citations.citation_style,
                reference_style=theme.citations.reference_style,
            )
            fragments = entry.source.reference_fragments(theme.citations.reference_style)
            if marker:
                fragments = [Text(f"{marker} ")] + fragments
            story.append(
                RLParagraph(
                    self._anchor_markup(entry.anchor)
                    + self._inline_markup(
                        fragments,
                        theme,
                        render_index,
                        base_font_name=entry_style.fontName,
                        base_size=entry_style.fontSize,
                    ),
                    entry_style,
                )
            )
        return story

    def _render_table_of_contents(
        self,
        block: TableOfContents,
        context: PdfRenderContext,
    ) -> list[object]:
        theme = context.theme
        styles = context.styles
        render_index = context.render_index
        level = theme.generated_content.generated_heading_level
        bold, italic = theme.resolve_heading_emphasis(level)
        title_style = RLParagraphStyle(
            "TableOfContentsTitle",
            parent=styles["Heading1"],
            fontName=self._resolve_font(theme.resolve_body_font(), bold, italic),
            fontSize=theme.resolve_heading_size(level),
            leading=theme.resolve_heading_size(level) * 1.2,
            spaceBefore=12,
            spaceAfter=6,
            alignment=ALIGNMENTS[theme.resolve_heading_text_alignment(level)],
            textColor=colors.black,
        )
        story: list[object] = [
            RLParagraph(
                self._inline_markup(
                    block.title or [Text(theme.resolve_generated_page_title("table_of_contents"))],
                    theme,
                    render_index,
                    base_font_name=title_style.fontName,
                    base_size=title_style.fontSize,
                    base_bold=bold,
                    base_italic=italic,
                ),
                title_style,
            )
        ]
        entries = render_index.scoped_headings(block)
        if block.show_page_numbers:
            toc = FilteredTableOfContents(
                max_level=block.max_level,
                dotsMinLevel=0 if block.leader else -1,
                allowed_keys={entry.anchor for entry in entries if entry.anchor is not None},
            )
            toc.levelStyles = [
                self._pdf_toc_level_style(block, toc_level, theme, styles)
                for toc_level in range(max((entry.level for entry in entries), default=1) + 1)
            ]
            story.append(toc)
        else:
            for entry in entries:
                entry_style = self._pdf_toc_level_style(block, entry.level, theme, styles)
                story.append(
                    RLParagraph(
                        self._link_markup(
                            entry.anchor,
                            self._inline_markup(
                                self._heading_fragments(entry.title, entry.number),
                                theme,
                                render_index,
                                base_font_name=entry_style.fontName,
                                base_size=entry_style.fontSize,
                            ),
                            internal=True,
                        ),
                        entry_style,
                    )
                )
        story.append(Spacer(1, 6))
        return story

    def _pdf_toc_level_style(
        self,
        block: TableOfContents,
        toc_level: int,
        theme: Theme,
        styles: object,
    ) -> RLParagraphStyle:
        level = toc_level
        toc_style = self._toc_level_style(block, level)
        font_size = theme.typography.body_font_size + toc_style.font_size_delta
        return RLParagraphStyle(
            f"TableOfContentsEntry{level}",
            parent=styles["BodyText"],
            fontName=self._resolve_font(
                theme.resolve_body_font(),
                bool(toc_style.bold),
                bool(toc_style.italic),
            ),
            fontSize=font_size,
            leading=font_size * 1.32,
            leftIndent=20 * toc_style.indent / 0.24 if toc_style.indent else 0,
            spaceBefore=toc_style.space_before,
            spaceAfter=toc_style.space_after,
            textColor=colors.black,
        )

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

    def _page_callback(
        self,
        document: Document,
        context: PdfRenderContext,
        *,
        has_front_matter: bool,
    ):
        theme = document.settings.theme
        font_name = self._resolve_font(theme.resolve_body_font(), False, False)

        def draw_page(canvas: object, doc: object) -> None:
            canvas.saveState()
            if theme.blocks.page_background_color != "FFFFFF":
                canvas.setFillColor(colors.HexColor(f"#{theme.blocks.page_background_color}"))
                canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
            self._draw_page_items(canvas, document, context)
            if not theme.page_numbers.show_page_numbers:
                canvas.restoreState()
                return
            canvas.setFont(font_name, theme.page_numbers.page_number_font_size)
            current_page = canvas.getPageNumber()
            main_start_page = getattr(doc, "main_matter_start_page", None)
            is_front_matter = has_front_matter and (
                main_start_page is None or current_page < main_start_page
            )
            logical_page = (
                current_page
                if is_front_matter or main_start_page is None
                else current_page - main_start_page + 1
            )
            text = theme.format_page_number(
                logical_page,
                front_matter=is_front_matter,
            )
            y = 0.45 * inch
            if theme.page_numbers.page_number_alignment == "left":
                canvas.drawString(doc.leftMargin, y, text)
            elif theme.page_numbers.page_number_alignment == "right":
                canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, text)
            else:
                canvas.drawCentredString(doc.pagesize[0] / 2, y, text)
            canvas.restoreState()

        return draw_page

    def _comment_marker(self, fragment: Comment, render_index: RenderIndex) -> str:
        return f"[{render_index.comment_number(fragment)}]"

    def _footnote_marker(self, fragment: Footnote, render_index: RenderIndex) -> str:
        return str(render_index.footnote_number(fragment))
