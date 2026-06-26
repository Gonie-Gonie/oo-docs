from __future__ import annotations

from importlib.metadata import version as package_version
from html import unescape
from io import BytesIO
from pathlib import Path
import re
import struct
import zlib
import zipfile

import oodocs
from docx import Document as WordDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import RGBColor
from pypdf import PdfReader

import oodocs.components.generated as generated_components
import oodocs.components.inline as inline_components
from oodocs.components.equations import BASELINE, SUBSCRIPT, SUPERSCRIPT, parse_latex_segments
from oodocs.core import length_to_inches
from oodocs.layout.indexing import build_render_index
from oodocs import (
    Affiliation,
    Assumption,
    Author,
    AuthorLayout,
    Axiom,
    BlockDefaults,
    Box,
    BoxStyle,
    BulletList,
    CaptionDefaults,
    CitationDefaults,
    CitationLibrary,
    CitationSource,
    Chapter,
    Claim,
    Comment,
    CommentList,
    CodeBlock,
    ColumnSpan,
    Conjecture,
    CountableBlock,
    Corollary,
    Definition,
    Document,
    DocumentSettings,
    DocumentValidationError,
    Divider,
    Equation,
    Example,
    Figure,
    ListOfFigures,
    Footnote,
    GeneratedContentDefaults,
    HeadingNumbering,
    ImageBox,
    ImageData,
    InlineChip,
    InlineChipStyle,
    Lemma,
    ListStyle,
    Math,
    MultiColumn,
    NumberedList,
    PageNumberDefaults,
    PageMargins,
    PageSize,
    PageBreak,
    Paragraph,
    ParagraphStyle,
    RunInTitleStyle,
    Part,
    Proof,
    Proposition,
    ReferenceList,
    Remark,
    Section,
    Shape,
    SubFigure,
    SubFigureGroup,
    Subsection,
    SubSubsection,
    Table,
    TableCell,
    TableCellStyle,
    TableStyle,
    TableOfContents,
    ListOfTables,
    Text,
    TextStyle,
    TextBox,
    Theorem,
    Theme,
    TitleMatterDefaults,
    TocLevelStyle,
    TypographyDefaults,
    ValidationResult,
    VerticalSpace,
    badge,
    bold,
    inline_code,
    text_color,
    cite,
    comment,
    create_countable_block_type,
    footnote,
    highlight,
    italic,
    keyboard,
    link,
    line_break,
    math,
    markup,
    prescript,
    reference,
    status,
    strikethrough,
    styled,
    subscript,
    superscript,
    tag,
)
from oodocs.presets.components import CalloutBox, KeyValueTable, Nomenclature
from oodocs.presets.templates import JournalArticleTemplate, ManuscriptSection
from oodocs.styles import TextStyle

class HighlightedParagraph(Paragraph):
    pass


def _write_sample_image(path: Path) -> None:
    path.write_bytes(_build_sample_png())


def _build_sample_png(width: int = 360, height: int = 220) -> bytes:
    rows: list[bytes] = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            if y < 34:
                pixel = (34, 58, 94)
            elif x < 18 or x >= width - 18 or y < 52 or y >= height - 18:
                pixel = (214, 221, 233)
            elif 26 < x < width - 26 and 70 < y < 102:
                pixel = (205, 121, 62)
            elif (x - 36) // 54 % 2 == 0 and 122 < y < 182:
                pixel = (89, 132, 198)
            else:
                pixel = (247, 249, 252)
            row.extend(pixel)
        rows.append(bytes(row))

    raw_image = b"".join(rows)
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(raw_image, level=9)),
            _png_chunk(b"IEND", b""),
        )
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    payload = chunk_type + data
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", checksum)


class FakeAxis:
    def __init__(self, values: list[object], names: tuple[str | None, ...] = ("",)) -> None:
        self._values = values
        self.names = names
        self.name = names[0] if names else None
        self.nlevels = max((len(value) if isinstance(value, tuple) else 1) for value in values) if values else 1

    def tolist(self) -> list[object]:
        return list(self._values)

    def __iter__(self):
        return iter(self._values)


class FakeDataFrame:
    def __init__(
        self,
        *,
        columns: list[object],
        rows: list[list[object]],
        index: list[object] | None = None,
        index_names: tuple[str | None, ...] = ("",),
    ) -> None:
        self.columns = FakeAxis(columns)
        self._rows = rows
        self.index = FakeAxis(index or list(range(len(rows))), names=index_names)

    def itertuples(self, *, index: bool = False, name: str | None = None):
        for row_index, row in enumerate(self._rows):
            if index:
                yield (self.index.tolist()[row_index], *row)
            else:
                yield tuple(row)


class FakeFigure:
    def __init__(self, image_bytes: bytes) -> None:
        self.image_bytes = image_bytes
        self.calls: list[dict[str, object]] = []

    def savefig(self, target: object, **kwargs: object) -> None:
        self.calls.append(dict(kwargs))
        target.write(self.image_bytes)


def _pdf_font_names(pdf_path: Path) -> set[str]:
    font_names: set[str] = set()
    for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages:
        resources = page.get("/Resources")
        if resources is None or "/Font" not in resources:
            continue
        fonts = resources["/Font"].get_object()
        for font in fonts.values():
            font_object = font.get_object()
            base_font = font_object.get("/BaseFont")
            if base_font is not None:
                font_names.add(str(base_font))
    return font_names


def _pdf_image_draw_count(pdf_path: Path) -> int:
    count = 0
    for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages:
        resources = page.get("/Resources")
        if resources is None or "/XObject" not in resources:
            continue
        xobjects = resources["/XObject"].get_object()
        image_names = {
            name
            for name, xobject in xobjects.items()
            if xobject.get_object().get("/Subtype") == "/Image"
        }
        if not image_names:
            continue
        content = page.get_contents()
        if content is None:
            continue
        content_bytes = content.get_data()
        for name in image_names:
            token = f"{name} Do".encode()
            count += content_bytes.count(token)
    return count


def _pdf_content_bytes(pdf_path: Path) -> bytes:
    parts: list[bytes] = []
    for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages:
        contents = page.get_contents()
        if contents is None:
            continue
        if isinstance(contents, list):
            for item in contents:
                parts.append(item.get_data())
        else:
            parts.append(contents.get_data())
    return b"\n".join(parts)


def _pdf_text_context(pdf_path: Path, text: str, window: int = 160) -> bytes:
    content = _pdf_content_bytes(pdf_path)
    needle = f"({text})".encode()
    index = content.find(needle)
    assert index != -1, f"{text!r} not found in PDF content stream"
    start = max(index - window, 0)
    return content[start : index + len(needle) + window]


def _docx_document_xml(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def _docx_word_xml(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path) as archive:
        return "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.startswith("word/") and name.endswith(".xml")
        )


def _docx_settings_xml(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path) as archive:
        return archive.read("word/settings.xml").decode("utf-8")


def _normalized_html_text(html_path: Path) -> str:
    html_text = html_path.read_text(encoding="utf-8")
    html_text = re.sub(r"<style.*?>.*?</style>", " ", html_text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html_text)
    return " ".join(unescape(text).split())


def test_version_is_defined() -> None:
    from oodocs import __version__

    assert __version__ == package_version("oodocs")
    assert __version__


def test_markup_creates_styled_fragments() -> None:
    fragments = markup("plain **bold** *italic* `code`")

    assert [fragment.value for fragment in fragments] == ["plain ", "bold", " ", "italic", " ", "code"]
    assert fragments[1].style.bold is True
    assert fragments[3].style.italic is True
    assert fragments[5].style.font_name == "Courier New"


def test_list_classes_create_block_instances() -> None:
    bullet = BulletList("first", Paragraph("second"))
    ordered = NumberedList("step one", "step two")

    assert isinstance(bullet, BulletList)
    assert bullet.ordered is False
    assert [item.plain_text() for item in bullet.items] == ["first", "second"]
    assert isinstance(ordered, NumberedList)
    assert ordered.ordered is True
    assert [item.plain_text() for item in ordered.items] == ["step one", "step two"]


def test_comment_and_math_helpers_create_renderable_fragments() -> None:
    inline_comment = comment("term", "Expanded note", author="pytest", initials="PT")
    inline_footnote = footnote("term", "Portable footnote note")
    inline_math = math(r"\alpha^2 + \beta^2")
    equation = Equation(r"\frac{1}{2}")

    assert isinstance(inline_comment, oodocs.Comment)
    assert inline_comment.plain_text() == "term[?]"
    assert inline_comment.author == "pytest"
    assert inline_comment.initials == "PT"
    assert isinstance(inline_footnote, Footnote)
    assert inline_footnote.plain_text() == "term[?]"
    assert isinstance(inline_math, Math)
    assert inline_math.plain_text() == "alpha2 + beta2"
    assert equation.plain_text() == "(1)/(2)"


def test_math_prescript_renders_to_all_outputs(tmp_path: Path) -> None:
    segments = parse_latex_segments(r"\prescript{14}{6}{C} + {}^{3}_{1}H")
    assert [(segment.text, segment.vertical_align) for segment in segments] == [
        ("14", SUPERSCRIPT),
        ("6", SUBSCRIPT),
        ("C + ", BASELINE),
        ("3", SUPERSCRIPT),
        ("1", SUBSCRIPT),
        ("H", BASELINE),
    ]

    document = Document(
        "Prescript Math",
        Paragraph("Inline isotope ", Math(r"\prescript{14}{6}{C} + {}^{3}_{1}H"), "."),
        Equation(r"\prescript{14}{6}{C} + {}^{3}_{1}H"),
    )

    docx_path = tmp_path / "prescript.docx"
    pdf_path = tmp_path / "prescript.pdf"
    html_path = tmp_path / "prescript.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    inline_paragraph = next(paragraph for paragraph in word_document.paragraphs if "Inline isotope" in paragraph.text)
    equation_paragraph = next(paragraph for paragraph in word_document.paragraphs if paragraph.text.startswith("146C + 31H"))
    assert any(run.text == "14" and run.font.superscript for run in inline_paragraph.runs)
    assert any(run.text == "6" and run.font.subscript for run in inline_paragraph.runs)
    assert any(run.text == "3" and run.font.superscript for run in equation_paragraph.runs)
    assert any(run.text == "1" and run.font.subscript for run in equation_paragraph.runs)

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert "146C + 31H" in pdf_text

    html_text = html_path.read_text(encoding="utf-8")
    assert "<sup>14</sup><sub>6</sub>C" in html_text
    assert "<sup>3</sup><sub>1</sub>H" in html_text


def test_method_style_inline_actions_create_renderable_fragments() -> None:
    source = CitationSource("Usage Guide", key="guide", year="2026")
    library = CitationLibrary([source])

    assert Text.bold("important").style.bold is True
    assert Text.italic("note").style.italic is True
    assert Text.inline_code("x = 1").style.font_name == "Courier New"
    assert Text.text_color("accent", "#0066AA").style.text_color == "0066AA"
    assert Text.highlight("marked", "#FFF2CC").style.highlight_color == "FFF2CC"
    assert Text.strikethrough("old").style.strikethrough is True
    assert Text.superscript("2").style.superscript is True
    assert Text.subscript("0").style.subscript is True
    assert [fragment.value for fragment in Text.from_markup("plain **bold**")] == [
        "plain ",
        "bold",
    ]
    assert bold("important").style.bold is True
    assert italic("note").style.italic is True
    assert inline_code("x = 1").style.font_name == "Courier New"
    assert text_color("accent", "#0066AA").style.text_color == "0066AA"
    assert highlight("marked", "#FFF2CC").style.highlight_color == "FFF2CC"
    assert strikethrough("old").style.strikethrough is True
    assert superscript("2").style.superscript is True
    assert subscript("0").style.subscript is True
    assert [fragment.plain_text() for fragment in prescript("14", "6", "C")] == ["14", "6", "C"]
    assert line_break().plain_text() == "\n"
    external_link = link("https://example.com", "Example")
    assert isinstance(external_link, inline_components.Hyperlink)
    assert external_link.target == "https://example.com"
    assert external_link.plain_text() == "Example"
    assert source.cite().plain_text() == "[?]"
    assert library.cite("guide").plain_text() == "[?]"
    assert Comment.annotated("term", "Expanded note").plain_text() == "term[?]"
    assert Footnote.annotated("term", "Portable footnote note").plain_text() == "term[?]"
    assert Math.inline(r"\alpha^2").plain_text() == "alpha2"
    assert InlineChip("base").kind == "chip"
    assert tag("api", background_color="#EEF2FF").chip_style.background_color == "EEF2FF"
    assert badge(3).plain_text() == "3"
    assert status("ready", state="success").plain_text() == "READY"
    assert keyboard("Ctrl+Enter").kind == "keyboard"
    assert isinstance(tag("api"), InlineChip)
    assert isinstance(InlineChipStyle(text_color="#111827"), InlineChipStyle)

    try:
        status("ready", state="unknown")
    except ValueError as exc:
        assert "Unsupported status state" in str(exc)
    else:
        raise AssertionError("Expected invalid status state validation to fail")


def test_theme_validates_page_number_configuration() -> None:
    theme = Theme(
        page_numbers=PageNumberDefaults(
            show_page_numbers=True,
            page_number_template="Page {page}",
            page_number_alignment="right",
        )
    )

    assert theme.format_page_number(3) == "Page 3"
    assert theme.format_page_number(3, front_matter=True) == "Page iii"

    try:
        Theme(page_numbers=PageNumberDefaults(page_number_template="Page"))
    except ValueError as exc:
        assert "{page}" in str(exc)
    else:
        raise AssertionError("Expected page_number_template validation to fail")


def test_theme_accepts_grouped_defaults_objects() -> None:
    theme = Theme(
        typography=TypographyDefaults(body_font_name="Calibri", body_font_size=10.0),
        captions=CaptionDefaults(figure_label="Fig.", table_caption_position="below"),
        citations=CitationDefaults(citation_style="apa", reference_style="apa"),
        generated_content=GeneratedContentDefaults(table_of_contents_title="Outline"),
        page_numbers=PageNumberDefaults(show_page_numbers=True, page_number_template="p. {page}"),
        title_matter=TitleMatterDefaults(title_text_alignment="left"),
        blocks=BlockDefaults(
            paragraph_text_alignment="left",
            table_block_alignment="right",
            run_in_title_style=RunInTitleStyle(TextStyle(italic=True), separator=": "),
        ),
    )

    assert theme.typography.body_font_name == "Calibri"
    assert theme.typography.body_font_size == 10.0
    assert theme.captions.figure_label == "Fig."
    assert theme.captions.table_caption_position == "below"
    assert theme.citations.citation_style == "apa"
    assert theme.citations.reference_style == "apa"
    assert theme.citations.citation_style == "apa"
    assert theme.generated_content.table_of_contents_title == "Outline"
    assert theme.page_numbers.show_page_numbers is True
    assert theme.format_page_number(4) == "p. 4"
    assert theme.title_matter.title_text_alignment == "left"
    assert theme.blocks.paragraph_text_alignment == "left"
    assert theme.blocks.run_in_title_style.text_style.italic is True
    assert theme.blocks.run_in_title_style.separator == ": "
    assert theme.blocks.table_block_alignment == "right"

    title_style_theme = Theme(
        blocks=BlockDefaults(
            run_in_title_style=RunInTitleStyle(TextStyle(bold=True), separator=". ")
        ),
    )
    assert title_style_theme.blocks.run_in_title_style.text_style.bold is True
    assert title_style_theme.blocks.run_in_title_style.separator == ". "

    keyword_group = Theme(typography=TypographyDefaults(body_font_name="Aptos"))
    assert keyword_group.typography.body_font_name == "Aptos"
    generated_keyword_group = Theme(
        generated_content=GeneratedContentDefaults(reference_list_title="Bibliography")
    )
    assert generated_keyword_group.generated_content.reference_list_title == "Bibliography"
    try:
        Theme(typography=object())  # type: ignore[arg-type]
    except TypeError as exc:
        assert "Theme.typography" in str(exc)
    else:
        raise AssertionError("Expected invalid Theme defaults group to fail")


def test_common_block_styles_accept_direct_kwargs() -> None:
    paragraph = Paragraph("Right aligned", text_alignment="right", space_after=4)
    code_block = CodeBlock("print('x')", language="python", left_indent=0.25)
    equation = Equation("x=1", space_after=2)
    bullet_list = BulletList("one", indent=0.4)
    numbered_list = NumberedList("one", start=3, suffix=")")
    box = Box(Paragraph("inside"), background_color="#FFFFFF", padding=8, width=3.0)
    table = Table(
        headers=["A"],
        rows=[["B"]],
        header_background_color="#AABBCC",
        cell_text_alignment="center",
    )
    contents = TableOfContents(level_styles={1: {"bold": False, "space_after": 1}})

    assert paragraph.style.text_alignment == "right"
    assert paragraph.style.space_after == 4
    assert code_block.style.left_indent == 0.25
    assert code_block.show_language is True
    assert code_block.language_position == "top-right"
    assert equation.style.space_after == 2
    assert bullet_list.style is not None
    assert bullet_list.style.marker_counter_format == "bullet"
    assert bullet_list.style.indent == 0.4
    assert numbered_list.style is not None
    assert numbered_list.style.start == 3
    assert numbered_list.style.suffix == ")"
    assert box.style.background_color == "FFFFFF"
    assert box.style.padding == 8
    assert box.style.width == 3.0
    assert table.style.header_background_color == "AABBCC"
    assert table.style.cell_text_alignment == "center"
    assert contents.style_for_level(1).bold is False
    assert contents.style_for_level(1).space_after == 1

    hidden_label_block = CodeBlock("plain text", language="text", show_language=False, language_position="bottom-left")
    assert hidden_label_block.show_language is False
    assert hidden_label_block.language_position == "bottom-left"

    try:
        CodeBlock("x", language="python", language_position="middle")  # type: ignore[arg-type]
    except ValueError as exc:
        assert "language_position" in str(exc)
    else:
        raise AssertionError("Expected invalid CodeBlock language_position to fail")


def test_paragraph_style_defaults_to_justify_alignment() -> None:
    paragraph = Paragraph("Default alignment paragraph.")

    assert paragraph.style.text_alignment is None
    assert Theme().resolve_paragraph_text_alignment(paragraph.style) == "justify"


def test_document_and_paragraph_text_alignment_options_render(tmp_path: Path) -> None:
    document = Document(
        "Alignment Test",
        Paragraph("Document-level centered paragraph."),
        Paragraph(
            "Paragraph-level right paragraph.",
            style=ParagraphStyle(text_alignment="right"),
        ),
        settings=DocumentSettings(
            theme=Theme(blocks=BlockDefaults(paragraph_text_alignment="center"))
        ),
    )

    docx_path = tmp_path / "alignment.docx"
    pdf_path = tmp_path / "alignment.pdf"
    html_path = tmp_path / "alignment.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    centered = next(
        paragraph
        for paragraph in word_document.paragraphs
        if paragraph.text == "Document-level centered paragraph."
    )
    right = next(
        paragraph
        for paragraph in word_document.paragraphs
        if paragraph.text == "Paragraph-level right paragraph."
    )
    assert centered.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert right.alignment == WD_ALIGN_PARAGRAPH.RIGHT

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")
    assert "Document-level centered paragraph." in pdf_text
    assert "Paragraph-level right paragraph." in pdf_text
    assert "text-align: center" in html_text
    assert "text-align: right" in html_text


def test_paragraph_titles_render_and_inherit_styles(tmp_path: Path) -> None:
    document = Document(
        "Paragraph Titles",
        Paragraph("Default body.", title="Default"),
        Section(
            "Scoped",
            Paragraph("Scoped body.", title="Scoped"),
            Paragraph(
                "Direct body.",
                title="Direct",
                title_style=RunInTitleStyle(
                    TextStyle(bold=True, text_color="991B1B"),
                    separator=" - ",
                ),
            ),
            run_in_title_style=RunInTitleStyle(
                TextStyle(bold=True, italic=True),
                separator=": ",
            ),
        ),
        Paragraph(
            "Individual body.",
            title="Individual",
            title_style=RunInTitleStyle(
                TextStyle(bold=True, text_color="166534"),
                separator=". ",
            ),
        ),
        settings=DocumentSettings(
            theme=Theme(
                blocks=BlockDefaults(
                    run_in_title_style=RunInTitleStyle(
                        TextStyle(bold=True),
                        separator=" ",
                    )
                )
            )
        ),
    )

    assert document.body.children[0].plain_text() == "Default Default body."

    docx_path = tmp_path / "paragraph-titles.docx"
    pdf_path = tmp_path / "paragraph-titles.pdf"
    html_path = tmp_path / "paragraph-titles.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    default = next(paragraph for paragraph in word_document.paragraphs if paragraph.text == "Default Default body.")
    scoped = next(paragraph for paragraph in word_document.paragraphs if paragraph.text == "Scoped: Scoped body.")
    direct = next(paragraph for paragraph in word_document.paragraphs if paragraph.text == "Direct - Direct body.")
    individual = next(paragraph for paragraph in word_document.paragraphs if paragraph.text == "Individual. Individual body.")
    assert default.runs[0].text == "Default"
    assert default.runs[0].bold is True
    assert scoped.runs[0].italic is True
    assert direct.runs[0].italic in (None, False)
    assert direct.runs[0].font.color.rgb == RGBColor(0x99, 0x1B, 0x1B)
    assert individual.runs[0].font.color.rgb == RGBColor(0x16, 0x65, 0x34)

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html = html_path.read_text(encoding="utf-8")
    assert "Default Default body." in pdf_text
    assert "Scoped: Scoped body." in pdf_text
    assert "Direct - Direct body." in pdf_text
    assert "Individual. Individual body." in pdf_text
    assert "Default Default body." in unescape(re.sub(r"<[^>]+>", "", html))
    assert "Scoped: Scoped body." in unescape(re.sub(r"<[^>]+>", "", html))
    assert "Direct - Direct body." in unescape(re.sub(r"<[^>]+>", "", html))
    assert "#991B1B" in html
    assert "#166534" in html


def test_paragraph_style_supports_word_like_indents() -> None:
    style = ParagraphStyle(
        left_indent=1.27,
        right_indent=0.508,
        first_line_indent=0.635,
        unit="cm",
    )
    hanging = ParagraphStyle.hanging(left=1.524, by=0.635, unit="cm")

    assert style.unit == "cm"
    assert round(style.left_indent_in_inches("in"), 2) == 0.5
    assert round(style.right_indent_in_inches("in"), 2) == 0.2
    assert round(style.first_line_indent_in_inches("in"), 2) == 0.25
    assert hanging.unit == "cm"
    assert round(hanging.left_indent_in_inches("in"), 2) == 0.6
    assert round(hanging.first_line_indent_in_inches("in"), 2) == -0.25

    try:
        ParagraphStyle(left_indent=-0.1)
    except ValueError as exc:
        assert "left_indent" in str(exc)
    else:
        raise AssertionError("Expected negative left_indent validation to fail")

    try:
        ParagraphStyle.hanging(by=-0.1)
    except ValueError as exc:
        assert "hanging by" in str(exc)
    else:
        raise AssertionError("Expected negative hanging indent validation to fail")


def test_theme_defaults_center_media_objects_and_captions() -> None:
    theme = Theme()

    assert theme.blocks.page_background_color == "FFFFFF"
    assert theme.captions.caption_text_alignment == "center"
    assert theme.blocks.table_block_alignment == "center"
    assert theme.blocks.figure_block_alignment == "center"
    assert theme.blocks.box_block_alignment == "center"


def test_page_background_color_renders_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Color Test",
        Paragraph("Tinted page."),
        settings=DocumentSettings(
            theme=Theme(blocks=BlockDefaults(page_background_color="#F4F8FC"))
        ),
    )
    docx_path = tmp_path / "color.docx"
    pdf_path = tmp_path / "color.pdf"
    html_path = tmp_path / "color.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    assert 'w:background w:color="F4F8FC"' in _docx_document_xml(docx_path)
    assert b".956863 .972549 .988235 rg" in _pdf_content_bytes(pdf_path)
    assert "background: #F4F8FC;" in html_path.read_text(encoding="utf-8")


def test_document_save_infers_renderer_from_extension(tmp_path: Path) -> None:
    document = Document("Save Test", Paragraph("Saved by extension."))

    docx_path = document.save(tmp_path / "extension.docx")
    pdf_path = document.save(tmp_path / "extension.pdf")
    html_path = document.save(tmp_path / "extension.html")
    htm_path = document.save(tmp_path / "extension.htm")

    assert docx_path.exists()
    assert pdf_path.exists()
    assert html_path.exists()
    assert htm_path.exists()

    try:
        document.save(tmp_path / "extension.txt")
    except ValueError as exc:
        assert ".docx" in str(exc)
        assert ".pdf" in str(exc)
        assert ".html" in str(exc)
    else:
        raise AssertionError("Expected unsupported save extension to fail")


def test_document_save_all_renders_multiple_formats(tmp_path: Path) -> None:
    document = Document("Quarterly Review Draft", Paragraph("Saved as a bundle."))

    outputs = document.save_all(tmp_path)

    assert sorted(outputs) == ["docx", "html", "pdf"]
    assert outputs["docx"] == tmp_path / "quarterly-review-draft.docx"
    assert outputs["pdf"] == tmp_path / "quarterly-review-draft.pdf"
    assert outputs["html"] == tmp_path / "quarterly-review-draft.html"
    assert all(path.exists() for path in outputs.values())

    selected_outputs = document.save_all(
        tmp_path / "selected",
        stem="review-pack",
        formats=(".docx", "htm"),
    )

    assert sorted(selected_outputs) == ["docx", "html"]
    assert selected_outputs["docx"] == tmp_path / "selected" / "review-pack.docx"
    assert selected_outputs["html"] == tmp_path / "selected" / "review-pack.html"
    assert all(path.exists() for path in selected_outputs.values())

    try:
        document.save_all(tmp_path, formats=("txt",))
    except ValueError as exc:
        assert "docx" in str(exc)
        assert "pdf" in str(exc)
        assert "html" in str(exc)
    else:
        raise AssertionError("Expected unsupported save_all format to fail")


def test_document_validate_returns_printable_result_with_format_scopes() -> None:
    document = Document(
        "Validation Report",
        TableOfContents(),
        Chapter("Findings", Paragraph("Body.")),
    )

    result = document.validate()

    assert isinstance(result, ValidationResult)
    assert result.ok
    assert [issue.code for issue in result.warnings] == ["html-toc-page-numbers"]
    assert result.warnings[0].formats == ("html",)
    assert result.warnings_for(("html",))
    assert result.warnings_for(("docx",)) == ()

    printable = str(result)
    assert "OODocs validation ok for All" in printable
    assert "Severity" in printable
    assert "Formats" in printable
    assert "HTML" in printable
    assert "html-toc-page-numbers" in printable


def test_document_validate_reports_authoring_errors_and_blocks_render(
    tmp_path: Path,
) -> None:
    missing_image = tmp_path / "missing.png"
    document = Document(
        "Broken Document",
        Figure(missing_image, caption="Missing figure."),
    )

    result = document.validate()
    assert not result.ok
    assert [issue.code for issue in result.errors] == ["missing-image-file"]
    assert result.errors[0].formats == ("docx", "pdf", "html")
    assert "All" in str(result)

    pdf_path = tmp_path / "broken.pdf"
    try:
        document.save_pdf(pdf_path)
    except DocumentValidationError as exc:
        message = str(exc)
        assert "OODocs validation failed for PDF" in message
        assert "missing-image-file" in message
        assert "PDF" in message
    else:
        raise AssertionError("Expected invalid document rendering to stop before PDF build")
    assert not pdf_path.exists()


def test_image_data_sources_render_without_temp_files(tmp_path: Path) -> None:
    figure = Figure(ImageData(_build_sample_png()), caption="In-memory image.", width=1.0)
    document = Document("Image Data", figure)

    outputs = document.save_all(tmp_path, stem="image-data")

    assert set(outputs) == {"docx", "pdf", "html"}
    assert all(path.exists() for path in outputs.values())
    assert "data:image/png;base64," in outputs["html"].read_text(encoding="utf-8")


def test_document_validate_catches_reference_mistakes() -> None:
    orphan = Paragraph("Outside the document.")
    uncaptioned_table = Table(headers=["Area"], rows=[["Validation"]])
    document = Document(
        "Reference Mistakes",
        Paragraph("See ", orphan.reference(), " and ", uncaptioned_table.reference(), "."),
        uncaptioned_table,
    )

    result = document.validate()
    assert [issue.code for issue in result.errors] == [
        "missing-reference-target",
        "uncaptioned-reference-target",
    ]

    try:
        document.validate(raise_on_error=True)
    except DocumentValidationError as exc:
        assert exc.errors == result.errors
        assert "missing-reference-target" in str(exc)
    else:
        raise AssertionError("Expected validate(raise_on_error=True) to fail")


def test_document_validate_reports_preflight_warnings(tmp_path: Path) -> None:
    image_path = tmp_path / "plot.png"
    _write_sample_image(image_path)
    missing_inline_image = tmp_path / "missing-inline.png"
    settings = DocumentSettings(
        unit="in",
        page_size=PageSize.letter(),
        page_margins=PageMargins.all(1.0, unit="in"),
    )
    wide_table = Table(
        headers=["A", "B"],
        rows=[["wide", "table"]],
        column_widths=[4.0, 4.0],
        unit="in",
    )
    captionless_figure = Figure(image_path)
    document = Document(
        "Preflight",
        wide_table,
        captionless_figure,
        Paragraph(
            "Inline asset ",
            ImageBox(
                missing_inline_image,
                placement="inline",
                width=0.2,
                height=0.2,
            ),
        ),
        settings=settings,
    )

    result = document.validate()
    warning_codes = {issue.code for issue in result.warnings}
    error_codes = {issue.code for issue in result.errors}

    assert warning_codes >= {
        "missing-table-caption",
        "missing-figure-caption",
        "wide-table",
    }
    assert "missing-image-file" in error_codes
    assert any(issue.formats == ("docx", "pdf") for issue in result.warnings if issue.code == "wide-table")


def test_document_validate_treats_subfigure_group_caption_as_reference_target(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "plot.png"
    _write_sample_image(image_path)
    grouped = SubFigureGroup(
        SubFigure(image_path, width=1.0),
        SubFigure(image_path, width=1.0),
        caption="Grouped result.",
    )
    captionless_group = SubFigureGroup(
        SubFigure(image_path, width=1.0),
    )

    valid_result = Document(
        "Grouped",
        Paragraph("See ", grouped.reference(), "."),
        grouped,
    ).validate()
    warning_codes = {issue.code for issue in valid_result.warnings}
    assert "missing-figure-caption" not in warning_codes
    assert valid_result.ok

    invalid_result = Document(
        "Captionless Group",
        Paragraph("See ", captionless_group.reference(), "."),
        captionless_group,
    ).validate()
    assert "missing-figure-caption" in {issue.code for issue in invalid_result.warnings}
    assert "uncaptioned-reference-target" in {issue.code for issue in invalid_result.errors}


def test_numbering_and_list_styles_are_customizable() -> None:
    heading_numbering = HeadingNumbering(
        level_counter_formats=("upper-roman", "lower-alpha"),
        prefix="[",
        suffix="]",
    )
    ordered_style = ListStyle(marker_counter_format="upper-roman", prefix="(", suffix=")")
    bullet_style = ListStyle(marker_counter_format="bullet", bullet="\u2022", suffix="")

    assert heading_numbering.format_label([2, 3]) == "[II.c]"
    assert ordered_style.marker_for(0) == "(I)"
    assert ordered_style.marker_for(2) == "(III)"
    assert bullet_style.marker_for(1) == "\u2022"


def test_table_accepts_dataframe_like_inputs_and_spans() -> None:
    dataframe = FakeDataFrame(
        columns=[("Metrics", "Latency"), ("Metrics", "Quality"), ("Summary", "")],
        rows=[["14 ms", "stable", "ready"]],
    )
    table = Table(
        dataframe,
        caption="Span test.",
        column_widths=[1.5, 1.5, 1.5],
        style=TableStyle(alternate_row_background_color="#F4F8FC"),
    )
    merged_header = Table(
        headers=[
            [TableCell("Metrics", colspan=2), TableCell("Summary", rowspan=2)],
            ["Latency", "Quality"],
        ],
        rows=[["14 ms", "stable", "ready"]],
        column_widths=[1.5, 1.5, 1.5],
    )

    assert len(table.header_rows) == 2
    assert table.header_rows[0][0].colspan == 2
    assert table.header_rows[0][1].rowspan == 2
    assert table._layout().column_count == 3
    assert merged_header._layout().row_count == 3


def test_table_cell_alignment_options_are_validated() -> None:
    cell = TableCell(
        "42",
        text_alignment="right",
        vertical_alignment="center",
    )
    style = TableStyle(
        cell_text_alignment="center",
        cell_vertical_alignment="bottom",
        header_text_alignment="right",
        header_vertical_alignment="middle",
    )

    assert cell.text_alignment == "right"
    assert cell.vertical_alignment == "middle"
    assert style.cell_text_alignment == "center"
    assert style.cell_vertical_alignment == "bottom"
    assert style.header_text_alignment == "right"
    assert style.header_vertical_alignment == "middle"

    try:
        TableCell("bad", text_alignment="diagonal")
    except ValueError as exc:
        assert "alignment" in str(exc)
    else:
        raise AssertionError("Expected invalid horizontal alignment to fail")

    try:
        TableStyle(cell_vertical_alignment="baseline")
    except ValueError as exc:
        assert "vertical" in str(exc)
    else:
        raise AssertionError("Expected invalid vertical alignment to fail")


def test_table_split_and_media_placement_options_render(tmp_path: Path) -> None:
    image_path = tmp_path / "placement.png"
    _write_sample_image(image_path)
    long_rows = [[f"Item {index}", f"Value {index}"] for index in range(34)]
    long_table = Table(
        headers=["Item", "Value"],
        rows=long_rows,
        caption="Long table with repeated headers.",
        column_widths=[2.0, 2.0],
        split=False,
    )
    here_table = Table(
        headers=["Mode", "Behavior"],
        rows=[["split=True", "render here and allow page breaks"]],
        caption="Explicit split table.",
        split=True,
    )
    top_figure = Figure(
        image_path,
        caption=Paragraph("Figure with top placement."),
        width=1.0,
        placement="top",
    )
    document = Document(
        "Placement Test",
        Paragraph("Before media."),
        long_table,
        here_table,
        top_figure,
        settings=DocumentSettings(
            page_size=PageSize.letter(),
            page_margins=PageMargins.all(0.5, unit="in"),
        ),
    )

    assert long_table._resolve_split() is True
    assert long_table._resolve_placement() == "here"
    assert here_table._resolve_split() is True
    assert here_table._resolve_placement() == "here"
    assert top_figure.resolved_placement() == "top"

    docx_path = tmp_path / "placement.docx"
    pdf_path = tmp_path / "placement.pdf"
    html_path = tmp_path / "placement.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_reader = PdfReader(BytesIO(pdf_path.read_bytes()))
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert long_table.total_row_count == 35
    assert 'w:tblHeader' in docx_xml
    assert '<w:br w:type="page"/>' in docx_xml
    assert "Long table with repeated headers." in pdf_text
    assert pdf_text.count("Item") >= 2
    assert len(pdf_reader.pages) >= 2
    assert 'oodocs-table-split' in html_text
    assert 'oodocs-placement-here' in html_text
    assert 'oodocs-placement-top' in html_text
    assert 'break-before: page' in html_text


def test_pdf_float_tables_can_move_after_following_prose(tmp_path: Path) -> None:
    floating_table = Table(
        headers=["Metric", "Value"],
        rows=[["Latency", "14 ms"], ["Quality", "stable"]],
        caption="Deferred table.",
        column_widths=[1.4, 1.4],
    )
    here_table = Table(
        headers=["Metric", "Value"],
        rows=[["Throughput", "ready"]],
        caption="Here table.",
        placement="here",
        column_widths=[1.4, 1.4],
    )
    document = Document(
        "Float Test",
        Chapter(
            "Main",
            Section(
                "Flow",
                Paragraph("Before floating table."),
                floating_table,
                Paragraph("Following prose fills the available page before the float."),
                Paragraph("Before here table."),
                here_table,
                Paragraph("After here table."),
            ),
        ),
    )

    pdf_path = tmp_path / "float.pdf"
    document.save_pdf(pdf_path)

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert pdf_text.index("Following prose fills the available page before the float.") < pdf_text.index("Table 1. Deferred table.")
    assert pdf_text.index("Table 2. Here table.") < pdf_text.index("After here table.")


def test_heading_hierarchy_uses_latex_like_levels() -> None:
    chapter = Chapter(
        "Part I",
        Section(
            "Overview",
            Subsection(
                "Details",
                SubSubsection("Examples"),
            ),
        ),
    )

    assert chapter.level == 1
    assert chapter.children[0].level == 2
    assert chapter.children[0].children[0].level == 3
    assert chapter.children[0].children[0].children[0].level == 4


def test_sections_can_be_rendered_without_numbering() -> None:
    unnumbered = Section("Abstract", Paragraph("Summary."), level=2, numbered=False)
    numbered = Section("Introduction", Paragraph("Body."), level=1)
    document = Document("Article", unnumbered, numbered)

    render_index = build_render_index(document)

    assert render_index.heading_number(unnumbered) is None
    assert render_index.heading_number(numbered) == "1"


def test_parts_use_dedicated_pages_without_resetting_chapters(tmp_path: Path) -> None:
    first_part = Part(
        "Foundations",
        Chapter("Start", Section("Scope", Paragraph("Body one."))),
    )
    second_part = Part(
        "Reference",
        Chapter("Continue", Section("API", Paragraph("Body two."))),
    )
    document = Document("Part Test", TableOfContents(), first_part, second_part)

    render_index = build_render_index(document)

    assert render_index.heading_number(first_part) == "Part I"
    assert render_index.heading_number(first_part.children[0]) == "1"
    assert render_index.heading_number(second_part) == "Part II"
    assert render_index.heading_number(second_part.children[0]) == "2"
    assert [entry.level for entry in render_index.headings[:4]] == [0, 1, 2, 0]

    docx_path = tmp_path / "parts.docx"
    pdf_path = tmp_path / "parts.pdf"
    html_path = tmp_path / "parts.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    paragraph_texts = [paragraph.text for paragraph in word_document.paragraphs]
    assert "Part I" in paragraph_texts
    assert "Foundations" in paragraph_texts
    assert "1 Start" in paragraph_texts
    assert "Part II" in paragraph_texts
    assert "2 Continue" in paragraph_texts
    assert _docx_document_xml(docx_path).count('<w:br w:type="page"/>') >= 2

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert "Part I" in pdf_text
    assert "1 Start" in pdf_text
    assert "Part II" in pdf_text
    assert "2 Continue" in pdf_text

    html_text = html_path.read_text(encoding="utf-8")
    normalized_html_text = _normalized_html_text(html_path)
    assert "Part I Foundations" in normalized_html_text
    assert "2 Continue" in normalized_html_text
    assert 'class="oodocs-part-page oodocs-page-break-before oodocs-page-break-after"' in html_text
    assert 'oodocs-toc-entry-level-0' in html_text


def test_public_api_prefers_classes_for_structural_nodes() -> None:
    assert hasattr(oodocs, "Document")
    assert hasattr(oodocs, "DocumentSettings")
    assert hasattr(oodocs, "Chapter")
    assert hasattr(oodocs, "AuthorLayout")
    assert hasattr(oodocs, "Section")
    assert hasattr(oodocs, "Shape")
    assert hasattr(oodocs, "Paragraph")
    assert hasattr(oodocs, "Part")
    assert hasattr(oodocs, "BulletList")
    assert hasattr(oodocs, "ColumnSpan")
    assert hasattr(oodocs, "CountableBlock")
    assert hasattr(oodocs, "Definition")
    assert hasattr(oodocs, "Lemma")
    assert hasattr(oodocs, "Proposition")
    assert hasattr(oodocs, "Theorem")
    assert hasattr(oodocs, "Corollary")
    assert hasattr(oodocs, "Proof")
    assert hasattr(oodocs, "Example")
    assert hasattr(oodocs, "Remark")
    assert hasattr(oodocs, "Assumption")
    assert hasattr(oodocs, "Axiom")
    assert hasattr(oodocs, "Claim")
    assert hasattr(oodocs, "Conjecture")
    assert hasattr(oodocs, "create_countable_block_type")
    assert hasattr(oodocs, "MultiColumn")
    assert hasattr(oodocs, "NumberedList")
    assert hasattr(oodocs, "PageBreak")
    assert hasattr(oodocs, "PageMargins")
    assert hasattr(oodocs, "PageSize")
    assert hasattr(oodocs, "ListOfTables")
    assert hasattr(oodocs, "ListOfFigures")
    assert hasattr(oodocs, "cite")
    assert hasattr(oodocs, "Box")
    assert hasattr(oodocs, "BoxStyle")
    assert hasattr(oodocs, "CitationDefaults")
    assert hasattr(oodocs, "HeadingNumbering")
    assert hasattr(oodocs, "ImageBox")
    assert hasattr(oodocs, "ImageData")
    assert hasattr(oodocs, "ListStyle")
    assert hasattr(oodocs, "Table")
    assert hasattr(oodocs, "TableCell")
    assert hasattr(oodocs, "TableStyle")
    assert hasattr(oodocs, "Figure")
    assert hasattr(oodocs, "TableOfContents")
    assert hasattr(oodocs, "TocLevelStyle")
    assert hasattr(oodocs, "Comment")
    assert hasattr(oodocs, "CommentList")
    assert hasattr(oodocs, "Footnote")
    assert hasattr(oodocs, "FootnoteList")
    assert hasattr(oodocs, "Equation")
    assert hasattr(oodocs, "Math")
    assert hasattr(oodocs, "InlineChip")
    assert hasattr(oodocs, "InlineChipStyle")
    assert hasattr(oodocs, "TextStyle")
    assert hasattr(oodocs, "TextBox")
    assert hasattr(oodocs, "LineBreak")
    assert hasattr(oodocs, "VerticalSpace")
    assert hasattr(oodocs, "Divider")
    assert not hasattr(oodocs, "Sheet")
    assert not hasattr(oodocs, "Body")
    assert not hasattr(oodocs, "Bold")
    assert not hasattr(oodocs, "Hyperlink")
    assert not hasattr(oodocs, "Italic")
    assert not hasattr(oodocs, "InlineCode")
    assert hasattr(inline_components, "Bold")
    assert hasattr(inline_components, "Hyperlink")
    assert hasattr(inline_components, "Italic")
    assert hasattr(inline_components, "InlineCode")
    assert hasattr(generated_components, "FootnoteList")
    assert not hasattr(oodocs, "ListBlock")
    assert not hasattr(oodocs, "Citation")
    assert not hasattr(oodocs, "TableReference")
    assert not hasattr(oodocs, "FigureReference")
    assert not hasattr(oodocs, "Strong")
    assert not hasattr(oodocs, "Emphasis")
    assert not hasattr(oodocs, "Code")
    assert not hasattr(oodocs, "PageBreaker")
    assert not hasattr(oodocs, "VSpace")
    assert not hasattr(oodocs, "HorizontalRule")
    assert hasattr(oodocs, "comment")
    assert hasattr(oodocs, "footnote")
    assert hasattr(oodocs, "from_notebook")
    assert hasattr(oodocs, "from_markdown")
    assert hasattr(oodocs, "from_markdown_file")
    assert not hasattr(oodocs, "from_ipynb")
    assert hasattr(oodocs, "math")
    assert hasattr(oodocs, "prescript")
    assert hasattr(oodocs, "reference")
    assert hasattr(oodocs, "bold")
    assert hasattr(oodocs, "italic")
    assert hasattr(oodocs, "inline_code")
    assert hasattr(oodocs, "text_color")
    assert not hasattr(oodocs, "code")
    assert not hasattr(oodocs, "color")
    assert hasattr(oodocs, "highlight")
    assert hasattr(oodocs, "link")
    assert hasattr(oodocs, "line_break")
    assert not hasattr(oodocs, "vspace")
    assert not hasattr(oodocs, "hrule")
    assert not hasattr(oodocs, "strike")
    assert hasattr(oodocs, "strikethrough")
    assert hasattr(oodocs, "tag")
    assert hasattr(oodocs, "badge")
    assert hasattr(oodocs, "status")
    assert hasattr(oodocs, "keyboard")
    assert hasattr(oodocs, "subscript")
    assert hasattr(oodocs, "superscript")
    assert hasattr(oodocs, "parse_notebook")
    assert hasattr(oodocs, "parse_markdown")
    assert hasattr(oodocs, "parse_markdown_file")
    assert not hasattr(oodocs, "parse_ipynb")
    assert hasattr(inline_components, "InlineChip")
    assert hasattr(inline_components, "InlineChipStyle")
    assert not hasattr(inline_components, "Strong")
    assert not hasattr(inline_components, "Emphasis")
    assert not hasattr(inline_components, "Code")
    assert hasattr(inline_components, "tag")
    assert hasattr(inline_components, "badge")
    assert hasattr(inline_components, "status")
    assert hasattr(inline_components, "keyboard")
    assert hasattr(inline_components, "reference")
    assert ImageData(_build_sample_png()).data

    for removed_name in (
        "document",
        "body",
        "chapter",
        "section",
        "subsection",
        "subsubsection",
        "paragraph",
        "code_block",
        "bullet_list",
        "numbered_list",
        "table",
        "figure",
    ):
        assert not hasattr(oodocs, removed_name)


def test_multicolumn_layout_renders_across_outputs(tmp_path: Path) -> None:
    image_path = tmp_path / "multicolumn.png"
    _write_sample_image(image_path)

    wide_table = Table(
        headers=["Metric", "Value"],
        rows=[
            ["Traceability checks", "passed"],
            ["Late revision cost", "reduced"],
        ],
        caption="Wide result table.",
        column_widths=[2.4, 2.4],
        placement="here",
    )
    wide_figure = Figure(
        image_path,
        caption="Wide result figure.",
        width=5.6,
        placement="here",
    )
    document = Document(
        "Multicolumn Report",
        Section(
            "Findings",
            MultiColumn(
                Paragraph("Column paragraph alpha."),
                Paragraph("Column paragraph beta."),
                wide_table,
                Paragraph("Column paragraph gamma."),
                ColumnSpan(wide_figure),
                Paragraph("Column paragraph delta."),
                columns=2,
                column_gap=0.18,
            ),
        ),
    )

    docx_path = tmp_path / "multicolumn.docx"
    pdf_path = tmp_path / "multicolumn.pdf"
    html_path = tmp_path / "multicolumn.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    word_text = "\n".join(
        [paragraph.text for paragraph in word_document.paragraphs]
        + [
            cell.text
            for table in word_document.tables
            for row in table.rows
            for cell in row.cells
        ]
    )
    assert "Column paragraph alpha." in word_text
    assert "Column paragraph delta." in word_text
    assert "Table 1. Wide result table." in word_text
    assert "Figure 1. Wide result figure." in word_text
    docx_xml = _docx_document_xml(docx_path)
    assert "<w:cols" in docx_xml
    assert 'w:num="2"' in docx_xml

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert "Column paragraph alpha." in pdf_text
    assert "Column paragraph delta." in pdf_text
    assert "Table 1. Wide result table." in pdf_text
    assert "Figure 1. Wide result figure." in pdf_text

    html_text = html_path.read_text(encoding="utf-8")
    normalized_html_text = _normalized_html_text(html_path)
    assert 'class="oodocs-multi-column-layout"' in html_text
    assert "column-count: 2" in html_text
    assert html_text.count('class="oodocs-column-span"') >= 2
    assert "Column paragraph alpha." in normalized_html_text
    assert "Column paragraph delta." in normalized_html_text
    assert "Table 1. Wide result table." in normalized_html_text
    assert "Figure 1. Wide result figure." in normalized_html_text


def test_page_items_render_without_affecting_document_flow(tmp_path: Path) -> None:
    image_path = tmp_path / "page-logo.png"
    _write_sample_image(image_path)
    page_items = [
        Shape.rect(
            name="frame",
            x=0.25,
            y=0.25,
            width=7.0,
            height=10.0,
            stroke_color="#476172",
            stroke_width=1.4,
        ),
        Shape.ellipse(
            anchor="frame",
            x=5.7,
            y=0.25,
            width=0.7,
            height=0.7,
            stroke_color="#B2783D",
            fill_color="#FFF1D8",
        ),
        ImageBox(
            image_path,
            anchor="frame",
            x=0.4,
            y=0.35,
            width=0.7,
            height=0.42,
            z_index=1,
        ),
        TextBox(
            "Positioned Page Overlay",
            anchor="margin",
            x=0.0,
            y=0.0,
            width=3.0,
            height=0.45,
            font_size=12,
        ),
        TextBox(
            "Anchored to the named frame shape.",
            anchor="frame",
            x=0.7,
            y=0.95,
            width=5.4,
            height=0.5,
            text_alignment="center",
            vertical_alignment="middle",
            font_size=11,
            z_index=2,
        ),
    ]
    document = Document(
        "Page Item Test",
        Paragraph("Body text keeps its normal position."),
        settings=DocumentSettings(
            page_size=PageSize.letter(),
            page_items=page_items,
            theme=Theme(page_numbers=PageNumberDefaults(show_page_numbers=True)),
        ),
    )

    docx_path = tmp_path / "page-items.docx"
    pdf_path = tmp_path / "page-items.pdf"
    html_path = tmp_path / "page-items.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    word_text = "\n".join(paragraph.text for paragraph in word_document.paragraphs)
    pdf_reader = PdfReader(BytesIO(pdf_path.read_bytes()))
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    html_text = html_path.read_text(encoding="utf-8")
    word_xml = _docx_word_xml(docx_path)

    assert "Body text keeps its normal position." in word_text
    assert "Positioned Page Overlay" in word_xml
    assert "Anchored to the named frame shape." in word_xml
    assert "<v:rect" in word_xml
    assert "<v:oval" in word_xml
    assert "<v:imagedata" in word_xml
    assert "Positioned Page Overlay" in pdf_text
    assert "Anchored to the named frame shape." in pdf_text
    assert _pdf_image_draw_count(pdf_path) == 1
    assert 'class="oodocs-page-items"' in html_text
    assert 'class="oodocs-page-item oodocs-imagebox"' in html_text
    assert "Positioned Page Overlay" in html_text
    assert "Anchored to the named frame shape." in html_text
    assert html_text.count("data:image/png;base64,") == 1
    assert "oodocs-sheet" not in html_text


def test_positioned_items_can_render_inline_like_text(tmp_path: Path) -> None:
    image_path = tmp_path / "inline-logo.png"
    _write_sample_image(image_path)
    document = Document(
        "Inline Drawing Test",
        Paragraph("Before inline drawing."),
        Shape.rect(
            width=1.2,
            height=0.35,
            placement="inline",
            stroke_color="#476172",
            fill_color="#EEF6FF",
        ),
        ImageBox(
            image_path,
            width=0.7,
            height=0.42,
            placement="inline",
        ),
        TextBox(
            "Inline textbox",
            width=1.8,
            height=0.35,
            placement="inline",
            text_alignment="center",
        ),
        Paragraph(
            "Image can sit ",
            ImageBox(
                image_path,
                width=0.45,
                height=0.27,
                placement="inline",
            ),
            " inside text.",
        ),
        Paragraph("After inline drawing."),
        settings=DocumentSettings(page_size=PageSize.letter()),
    )

    docx_path = tmp_path / "inline-drawing.docx"
    pdf_path = tmp_path / "inline-drawing.pdf"
    html_path = tmp_path / "inline-drawing.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    word_text = "\n".join(paragraph.text for paragraph in word_document.paragraphs)
    word_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert "Before inline drawing." in word_text
    assert "After inline drawing." in word_text
    assert "<v:rect" in word_xml
    assert "Inline textbox" in word_xml
    assert len(word_document.inline_shapes) == 2
    assert "Inline textbox" in pdf_text
    assert _pdf_image_draw_count(pdf_path) == 2
    assert "display: inline-block" in html_text
    assert "Inline textbox" in html_text
    assert html_text.count("data:image/png;base64,") == 2


def test_box_style_supports_tcolorbox_like_layout_controls(tmp_path: Path) -> None:
    image_path = tmp_path / "panel-logo.png"
    _write_sample_image(image_path)
    document = Document(
        "Box Layout Test",
        Box(
            Paragraph("Editable content inside a styled report panel."),
            Table(
                headers=["Surface", "Behavior"],
                rows=[["Box", "compact nested table"]],
                column_widths=[1.2, 2.0],
            ),
            Figure(image_path, width=0.7),
            title="Panel",
            style=BoxStyle(
                border_color="#1058A3",
                background_color="#FFFFFF",
                title_background_color="#1058A3",
                title_text_color="#FFFFFF",
                border_width=0.5,
                padding_top=2,
                padding_right=5,
                padding_bottom=3,
                padding_left=7,
                width=10,
                unit="cm",
                block_alignment="left",
            ),
        ),
    )

    docx_path = tmp_path / "box-layout.docx"
    pdf_path = tmp_path / "box-layout.pdf"
    html_path = tmp_path / "box-layout.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    html_text = html_path.read_text(encoding="utf-8")
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)

    assert "Editable content inside a styled report panel." in docx_xml
    assert 'w:fill="1058A3"' in docx_xml
    assert 'w:color="FFFFFF"' in docx_xml
    assert '<w:tblW w:w="5669" w:type="dxa"/>' in docx_xml
    assert '<w:top w:w="40" w:type="dxa"/>' in docx_xml
    assert '<w:left w:w="140" w:type="dxa"/>' in docx_xml
    assert "width: 3.9370in" in html_text
    assert "padding: 2.0pt 5.0pt 3.0pt 7.0pt" in html_text
    assert "padding: 0;" in html_text
    assert "box-shadow: none" in html_text
    assert "color: #FFFFFF" in html_text
    assert "Editable content inside a styled report panel." in pdf_text
    assert "compact nested table" in pdf_text


def test_explicit_page_break_renders_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Break Test",
        Paragraph("Before break."),
        PageBreak(),
        Paragraph("After break."),
    )

    docx_path = tmp_path / "break.docx"
    pdf_path = tmp_path / "break.pdf"
    html_path = tmp_path / "break.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    assert '<w:br w:type="page"/>' in _docx_document_xml(docx_path)
    assert len(PdfReader(BytesIO(pdf_path.read_bytes())).pages) >= 2
    assert 'class="oodocs-page-break"' in html_path.read_text(encoding="utf-8")


def test_inline_highlight_strike_and_line_break_render_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Inline Word Features",
        Paragraph(
            "Keep ",
            highlight("review focus", "#FFF2CC"),
            ", remove ",
            strikethrough("old value"),
            line_break(),
            "Continue same paragraph.",
        ),
    )

    docx_path = tmp_path / "inline-word-features.docx"
    pdf_path = tmp_path / "inline-word-features.pdf"
    html_path = tmp_path / "inline-word-features.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert 'w:fill="FFF2CC"' in docx_xml
    assert "<w:strike" in docx_xml
    assert "<w:br" in docx_xml
    assert "review focus" in pdf_text
    assert "old value" in pdf_text
    assert "Continue same paragraph." in pdf_text
    assert "background-color: #FFF2CC" in html_text
    assert "line-through" in html_text
    assert "<br/>" in html_text


def test_inline_caps_and_vertical_align_render_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Inline Detail Features",
        Paragraph(
            Text.styled("small caps", small_caps=True),
            " ",
            Text.styled("upper", uppercase=True),
            " H",
            Text.styled("2", subscript=True),
            " x",
            Text.styled("2", superscript=True),
            " isotope ",
            prescript("14", "6", "C"),
            " index ",
            subscript("i"),
            superscript("j"),
        ),
    )

    docx_path = tmp_path / "inline-detail-features.docx"
    pdf_path = tmp_path / "inline-detail-features.pdf"
    html_path = tmp_path / "inline-detail-features.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert "<w:smallCaps" in docx_xml
    assert "<w:caps" in docx_xml
    assert 'w:val="subscript"' in docx_xml
    assert 'w:val="superscript"' in docx_xml
    word_paragraph = next(paragraph for paragraph in WordDocument(docx_path).paragraphs if "isotope 146C" in paragraph.text)
    assert any(run.text == "14" and run.font.superscript for run in word_paragraph.runs)
    assert any(run.text == "6" and run.font.subscript for run in word_paragraph.runs)
    assert any(run.text == "i" and run.font.subscript for run in word_paragraph.runs)
    assert any(run.text == "j" and run.font.superscript for run in word_paragraph.runs)
    assert "UPPER" in pdf_text
    assert "146C" in pdf_text
    assert "font-variant: small-caps" in html_text
    assert "text-transform: uppercase" in html_text
    assert "vertical-align: sub" in html_text
    assert "vertical-align: super" in html_text


def test_inline_chips_render_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Inline Chips",
        Paragraph(
            "Route ",
            tag("api"),
            " with ",
            status("ready", state="success"),
            ", show ",
            badge(3),
            ", and press ",
            keyboard("Ctrl+Enter"),
            ".",
        ),
    )

    docx_path = tmp_path / "inline-chips.docx"
    pdf_path = tmp_path / "inline-chips.pdf"
    html_path = tmp_path / "inline-chips.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")
    normalized_html = _normalized_html_text(html_path)

    assert len(word_document.inline_shapes) == 4
    assert "Route  with , show , and press ." in [paragraph.text for paragraph in word_document.paragraphs]
    assert "api" in pdf_text
    assert "READY" in pdf_text
    assert "3" in pdf_text
    assert "Ctrl+Enter" in pdf_text
    assert "oodocs-inline-chip-tag" in html_text
    assert "oodocs-inline-chip-badge" in html_text
    assert "oodocs-inline-chip-status" in html_text
    assert "oodocs-inline-chip-keyboard" in html_text
    assert "api" in normalized_html
    assert "READY" in normalized_html
    assert "Ctrl+Enter" in normalized_html


def test_paragraph_indents_render_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Indent Test",
        Paragraph(
            "Indented paragraph.",
            style=ParagraphStyle(
                left_indent=1.27,
                right_indent=0.508,
                first_line_indent=0.635,
            ),
        ),
        Paragraph(
            "Hanging indent paragraph.",
            style=ParagraphStyle.hanging(left=1.524, by=0.635),
        ),
        settings=DocumentSettings(unit="cm"),
    )

    docx_path = tmp_path / "indent.docx"
    pdf_path = tmp_path / "indent.pdf"
    html_path = tmp_path / "indent.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert 'w:left="720"' in docx_xml
    assert 'w:right="288"' in docx_xml
    assert 'w:firstLine="360"' in docx_xml
    assert 'w:hanging="360"' in docx_xml
    assert "Indented paragraph." in pdf_text
    assert "Hanging indent paragraph." in pdf_text
    assert "margin-left: 0.50in" in html_text
    assert "margin-right: 0.20in" in html_text
    assert "text-indent: 0.25in" in html_text
    assert "text-indent: -0.25in" in html_text


def test_paragraph_spacing_and_pagination_options_render_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Paragraph Detail Options",
        Paragraph(
            "Keep this with the next block.",
            space_before=6,
            space_after=3,
            keep_together=True,
            keep_with_next=True,
            page_break_before=True,
            widow_control=False,
        ),
        Paragraph("Next block."),
    )

    docx_path = tmp_path / "paragraph-details.docx"
    pdf_path = tmp_path / "paragraph-details.pdf"
    html_path = tmp_path / "paragraph-details.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert 'w:before="120"' in docx_xml
    assert 'w:after="60"' in docx_xml
    assert "<w:keepLines" in docx_xml
    assert "<w:keepNext" in docx_xml
    assert "<w:pageBreakBefore" in docx_xml
    assert 'w:widowControl w:val="0"' in docx_xml
    assert "Keep this with the next block." in pdf_text
    assert "margin: 6.0pt 0 3.0pt" in html_text
    assert "break-inside: avoid" in html_text
    assert "page-break-before: always" in html_text
    assert "widows: 1" in html_text


def test_vertical_space_and_divider_render_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Spacing Blocks",
        Paragraph("Before spacer."),
        VerticalSpace(18),
        Divider(
            color="C8CDD6",
            thickness=1.5,
            space_before=4,
            space_after=5,
            width=2.0,
            alignment="center",
            unit="in",
        ),
        Paragraph("After divider."),
    )

    docx_path = tmp_path / "spacing-blocks.docx"
    pdf_path = tmp_path / "spacing-blocks.pdf"
    html_path = tmp_path / "spacing-blocks.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert 'w:after="360"' in docx_xml
    assert 'w:before="80"' in docx_xml
    assert 'w:after="100"' in docx_xml
    assert '<w:bottom w:val="single" w:sz="12" w:space="1" w:color="C8CDD6"/>' in docx_xml
    assert "Before spacer." in pdf_text
    assert "After divider." in pdf_text
    assert 'class="oodocs-vertical-space"' in html_text
    assert "height: 18.0pt" in html_text
    assert 'class="oodocs-divider"' in html_text
    assert "border-top: 1.50pt solid #C8CDD6" in html_text
    assert "width: 2.0000in" in html_text


def test_table_cell_alignment_renders_to_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Table Alignment Test",
        Table(
            headers=[
                [
                    TableCell(
                        "Metric",
                        text_alignment="center",
                        vertical_alignment="middle",
                    ),
                    "Value",
                ]
            ],
            rows=[
                [
                    "Latency",
                    TableCell(
                        "14 ms",
                        text_alignment="right",
                        vertical_alignment="bottom",
                    ),
                ],
            ],
            style=TableStyle(
                header_text_alignment="center",
                header_vertical_alignment="middle",
                cell_text_alignment="left",
                cell_vertical_alignment="top",
            ),
        ),
    )

    docx_path = tmp_path / "table-alignment.docx"
    pdf_path = tmp_path / "table-alignment.pdf"
    html_path = tmp_path / "table-alignment.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert '<w:jc w:val="center"' in docx_xml
    assert '<w:jc w:val="right"' in docx_xml
    assert '<w:vAlign w:val="center"' in docx_xml
    assert '<w:vAlign w:val="bottom"' in docx_xml
    assert "Metric" in pdf_text
    assert "14 ms" in pdf_text
    assert "text-align: center" in html_text
    assert "text-align: right" in html_text


def test_default_table_cell_alignment_is_left_in_all_outputs(tmp_path: Path) -> None:
    document = Document(
        "Default Table Alignment Test",
        Table(
            headers=["Area", "Status"],
            rows=[["Release notes", "Compatibility notes wrap cleanly in narrow cells."]],
        ),
        settings=DocumentSettings(
            theme=Theme(blocks=BlockDefaults(paragraph_text_alignment="justify"))
        ),
    )

    docx_path = tmp_path / "default-table-alignment.docx"
    pdf_path = tmp_path / "default-table-alignment.pdf"
    html_path = tmp_path / "default-table-alignment.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert '<w:jc w:val="left"' in docx_xml
    assert "Compatibility notes wrap cleanly" in pdf_text
    assert "text-align: left" in html_text


def test_table_cell_row_and_column_styles_render_to_all_outputs(tmp_path: Path) -> None:
    table = Table(
        headers=["Metric", "Value"],
        rows=[
            [
                "Latency",
                TableCell(
                    "14 ms",
                    style=TableCellStyle(
                        background_color="#FFE699",
                        text_color="#7F1D1D",
                        bold=True,
                    ),
                ),
            ],
            ["Quality", "Stable"],
        ],
        caption="Styled table.",
        row_styles={
            1: TableCellStyle(background_color="#E2F0D9", italic=True),
        },
        column_styles={
            0: TableCellStyle(text_color="#1F4E79", bold=True),
        },
        header_row_styles={
            0: TableCellStyle(background_color="#1F4E79", text_color="#FFFFFF"),
        },
    )
    document = Document("Table Style Test", table)

    docx_path = tmp_path / "table-style.docx"
    pdf_path = tmp_path / "table-style.pdf"
    html_path = tmp_path / "table-style.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert "1F4E79" in docx_xml
    assert "FFE699" in docx_xml
    assert "E2F0D9" in docx_xml
    assert '<w:b' in docx_xml
    assert '<w:i' in docx_xml
    assert "Styled table." in pdf_text
    assert "Latency" in pdf_text
    assert "Stable" in pdf_text
    assert "background: #1F4E79" in html_text
    assert "background: #FFE699" in html_text
    assert "background: #E2F0D9" in html_text
    assert "color: #7F1D1D" in html_text
    assert "font-weight: 700" in html_text
    assert "font-style: italic" in html_text


def test_table_detail_style_options_render_to_all_outputs(tmp_path: Path) -> None:
    table = Table(
        headers=["Metric", "Value"],
        rows=[["Latency", "14 ms"], ["Quality", "Stable"]],
        caption="Detailed table.",
        border_color="#334155",
        border_width=1.25,
        cell_padding_top=2,
        cell_padding_right=3,
        cell_padding_bottom=4,
        cell_padding_left=5,
        repeat_header_rows=True,
    )
    document = Document("Table Detail Test", table)

    docx_path = tmp_path / "table-detail-style.docx"
    pdf_path = tmp_path / "table-detail-style.pdf"
    html_path = tmp_path / "table-detail-style.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert 'w:sz="10"' in docx_xml
    assert 'w:color="334155"' in docx_xml
    assert '<w:top w:w="40" w:type="dxa"/>' in docx_xml
    assert '<w:right w:w="60" w:type="dxa"/>' in docx_xml
    assert '<w:bottom w:w="80" w:type="dxa"/>' in docx_xml
    assert '<w:left w:w="100" w:type="dxa"/>' in docx_xml
    assert "<w:tblHeader" in docx_xml
    assert "Detailed table." in pdf_text
    assert "border: 1.25pt solid #334155" in html_text
    assert "padding: 2.0pt 3.0pt 4.0pt 5.0pt" in html_text


def test_component_and_template_presets_build_renderable_documents(tmp_path: Path) -> None:
    callout = CalloutBox(
        Paragraph("Check terminology before review."),
        title="Review focus",
        variant="warning",
    )
    metadata = KeyValueTable(
        {"Preset namespace": "oodocs.presets.components", "Output": "DOCX/PDF/HTML"},
        caption="Preset metadata.",
    )
    nomenclature = Nomenclature(
        [
            ("A", "area", "m2"),
            ("E", "energy", "kWh"),
            ("q", "heat flux", "W/m2"),
            ("T", "temperature", "degC"),
        ],
        double_column=True,
        title="Nomenclature",
    )
    document = Document("Preset Components", callout, metadata, nomenclature)

    docx_path = tmp_path / "preset-components.docx"
    html_path = tmp_path / "preset-components.html"
    document.save_docx(docx_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    html_text = html_path.read_text(encoding="utf-8")

    assert "Review focus" in docx_xml
    assert "Preset namespace" in docx_xml
    assert "Nomenclature" in docx_xml
    assert "heat flux" in docx_xml
    assert "FFFBEB" in docx_xml
    assert "Review focus" in html_text
    assert "Preset metadata." in _normalized_html_text(html_path)

    article_document = JournalArticleTemplate(include_contents=True, include_references=False).build(
        "Readable manuscript generation",
        authors=[Author("Research Lead", affiliations=["Example Lab"], corresponding=True)],
        abstract="A concise abstract paragraph.",
        keywords=["document generation", "python"],
        sections=[
            ManuscriptSection("Introduction", [Paragraph("Problem and contribution.")]),
            ("Methods", [Paragraph("Data, model, and validation.")]),
        ],
        acknowledgements="The authors thank the review team.",
        data_availability=None,
    )

    assert isinstance(article_document, Document)
    assert any(isinstance(child, TableOfContents) for child in article_document.body.children)
    article_headings = [
        child.plain_title()
        for child in article_document.body.children
        if isinstance(child, Section)
    ]
    assert "Acknowledgements" in article_headings
    assert "Data Availability" not in article_headings

    unitless = Nomenclature([("x", "value"), ("y", "other value")], double_column=True)
    assert unitless.children[0].header_rows[0][0].content.content[0].value == "Symbol"
    assert len(unitless.children[0].header_rows[0]) == 4

    try:
        Nomenclature([("x", "value", "-", "extra")])  # type: ignore[list-item]
    except ValueError as exc:
        assert "entries" in str(exc)
    else:
        raise AssertionError("Expected invalid Nomenclature entry shape to fail")


def test_subfigure_group_renders_labels_and_references(tmp_path: Path) -> None:
    image_path = tmp_path / "subfigure.png"
    _write_sample_image(image_path)
    baseline = SubFigure(image_path, caption="Baseline output.", width=1.0)
    treatment = SubFigure(image_path, caption="Treatment output.", width=1.0)
    group = SubFigureGroup(
        baseline,
        treatment,
        caption="Paired outputs.",
        columns=2,
        column_gap=0.2,
    )
    document = Document(
        "Subfigure Test",
        Paragraph("Compare ", baseline.reference(), " with ", treatment.reference(), " in ", group.reference(), "."),
        group,
    )

    docx_path = tmp_path / "subfigure.docx"
    pdf_path = tmp_path / "subfigure.pdf"
    html_path = tmp_path / "subfigure.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    paragraph_text = "\n".join(paragraph.text for paragraph in word_document.paragraphs)
    table_text = "\n".join(
        paragraph.text
        for table in word_document.tables
        for row in table.rows
        for cell in row.cells
        for paragraph in cell.paragraphs
    )
    assert "Compare Figure 1(a) with Figure 1(b) in Figure 1." in paragraph_text
    assert "(a) Baseline output." in table_text
    assert "(b) Treatment output." in table_text
    assert "Figure 1. Paired outputs." in paragraph_text
    assert len(word_document.inline_shapes) == 2

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert "Compare Figure 1(a) with Figure 1(b) in Figure 1." in pdf_text
    assert "(a) Baseline output." in pdf_text
    assert "(b) Treatment output." in pdf_text
    assert "Figure 1. Paired outputs." in pdf_text

    html_text = html_path.read_text(encoding="utf-8")
    normalized_html_text = _normalized_html_text(html_path)
    assert "Compare Figure 1(a) with Figure 1(b) in Figure 1" in normalized_html_text
    assert "(a) Baseline output." in normalized_html_text
    assert "(b) Treatment output." in normalized_html_text
    assert "Figure 1. Paired outputs." in normalized_html_text
    assert 'href="#figure_1_a"' in html_text
    assert 'href="#figure_1_b"' in html_text
    assert 'id="figure_1_a"' in html_text
    assert 'id="figure_1_b"' in html_text
    assert html_text.count("data:image/png;base64,") == 2


def test_caption_and_reference_labels_can_differ_by_theme(tmp_path: Path) -> None:
    image_path = tmp_path / "labels.png"
    _write_sample_image(image_path)
    table = Table(
        headers=["Metric", "Value"],
        rows=[["Latency", "14 ms"]],
        caption="Localized table caption.",
    )
    figure = Figure(image_path, caption="Localized figure caption.", width=1.0)
    document = Document(
        "Caption Labels Test",
        Paragraph("See ", table.reference(), " and ", figure.reference(), "."),
        table,
        figure,
        ListOfTables(),
        ListOfFigures(),
        settings=DocumentSettings(
            theme=Theme(
                captions=CaptionDefaults(
                    table_caption_label="Table",
                    table_reference_label="Tbl.",
                    figure_caption_label="Figure",
                    figure_reference_label="Fig.",
                )
            )
        ),
    )

    docx_path = tmp_path / "caption-labels.docx"
    pdf_path = tmp_path / "caption-labels.pdf"
    html_path = tmp_path / "caption-labels.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_text = "\n".join(paragraph.text for paragraph in WordDocument(docx_path).paragraphs)
    assert "See Tbl. 1 and Fig. 1." in word_text
    assert "Table 1. Localized table caption." in word_text
    assert "Figure 1. Localized figure caption." in word_text

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert "See Tbl. 1 and Fig. 1." in pdf_text
    assert "Table 1. Localized table caption." in pdf_text
    assert "Figure 1. Localized figure caption." in pdf_text

    normalized_html_text = _normalized_html_text(html_path)
    assert "See Tbl. 1 and Fig. 1" in normalized_html_text
    assert "Table 1. Localized table caption." in normalized_html_text
    assert "Figure 1. Localized figure caption." in normalized_html_text


def test_explicit_reference_api_covers_numbered_blocks(tmp_path: Path) -> None:
    intro = Paragraph("Reusable paragraph target.")
    equation = Equation(r"\alpha^2 + \beta^2 = \gamma^2")
    snippet = CodeBlock("const ready = true;\nconsole.log(ready);", language="javascript")
    detail_box = Box(Paragraph("Box body."), title="Referenceable Box")
    section = Section("Reference Targets", intro)
    section.children.append(Paragraph(
        "Targets: ",
        intro.reference(),
        ", ",
        reference(equation),
        ", ",
        snippet.reference(),
        ", ",
        detail_box.reference("the boxed note"),
        ", and ",
        section.reference(),
        ".",
    ))
    document = Document(
        "Explicit References",
        section,
        equation,
        snippet,
        detail_box,
    )

    docx_path = tmp_path / "explicit-references.docx"
    pdf_path = tmp_path / "explicit-references.pdf"
    html_path = tmp_path / "explicit-references.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_text = "\n".join(paragraph.text for paragraph in WordDocument(docx_path).paragraphs)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")
    normalized_html_text = _normalized_html_text(html_path)

    assert "Targets: Paragraph 1, Equation 1, Code block 1, the boxed note, and Section 1.1." in word_text
    assert "alpha2 + beta2 = gamma2 (1)" in word_text
    assert "const ready = true;" in word_text
    assert "Targets: Paragraph 1, Equation 1, Code block 1, the boxed note, and Section 1.1." in pdf_text
    assert "alpha2 + beta2 = gamma2 (1)" in pdf_text
    assert "Targets:" in normalized_html_text
    assert "Paragraph 1" in normalized_html_text
    assert "Equation 1" in normalized_html_text
    assert "Code block 1" in normalized_html_text
    assert "the boxed note" in normalized_html_text
    assert "Section 1.1" in normalized_html_text
    assert 'href="#paragraph_' in html_text
    assert 'href="#equation_' in html_text
    assert 'href="#code_' in html_text
    assert 'href="#box_' in html_text
    assert 'href="#heading_' in html_text
    assert "color: #" in html_text

    try:
        Paragraph("Ambiguous ", equation, ".")
    except TypeError as exc:
        assert "reference(obj)" in str(exc)
    else:
        raise AssertionError("Expected raw document object references in Paragraph to fail")


def test_countable_blocks_share_document_counter_and_render_references(tmp_path: Path) -> None:
    CustomClaim = create_countable_block_type("Claim", counter="theorem")
    definition = Definition("A countable block participates in the document-wide theorem counter.")
    lemma = Lemma("A later theorem-like block advances the same counter.")
    theorem = Theorem("The shared counter is stable across output formats.", title="Main result")
    proof = Proof("The proof is intentionally unnumbered.")
    example = Example("Examples keep counting after the proof.")
    remark = Remark("Remarks share the same theorem-like sequence.")
    assumption = Assumption("Assumptions can be referenced and numbered.")
    claim = CustomClaim("Custom countable kinds can join the same counter.")
    document = Document(
        "Countable Blocks",
        Paragraph("See ", theorem.reference(), ", ", proof.reference("the proof"), ", and ", claim.reference(), "."),
        definition,
        lemma,
        theorem,
        proof,
        example,
        remark,
        assumption,
        claim,
    )

    render_index = build_render_index(document)
    assert isinstance(claim, CountableBlock)
    assert render_index.countable_number(definition) == 1
    assert render_index.countable_number(lemma) == 2
    assert render_index.countable_number(theorem) == 3
    assert render_index.countable_number(proof) is None
    assert render_index.countable_number(example) == 4
    assert render_index.countable_number(remark) == 5
    assert render_index.countable_number(assumption) == 6
    assert render_index.countable_number(claim) == 7

    docx_path = tmp_path / "countable-blocks.docx"
    pdf_path = tmp_path / "countable-blocks.pdf"
    html_path = tmp_path / "countable-blocks.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_text = "\n".join(paragraph.text for paragraph in WordDocument(docx_path).paragraphs)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")
    normalized_html_text = _normalized_html_text(html_path)

    expected_texts = (
        "See Theorem 3, the proof, and Claim 7.",
        "Definition 1.",
        "Lemma 2.",
        "Theorem 3. Main result",
        "Proof.",
        "Example 4.",
        "Remark 5.",
        "Assumption 6.",
        "Claim 7.",
    )
    for text in expected_texts:
        assert text in word_text
        assert text in pdf_text
    for text in expected_texts[1:]:
        assert text in normalized_html_text
    assert "See Theorem 3 , the proof , and Claim 7 ." in normalized_html_text
    assert 'class="oodocs-countable-block' in html_text
    assert 'href="#countable_' in html_text


def test_unnumbered_countable_reference_requires_custom_label() -> None:
    proof = Proof("No counter is assigned to proofs by default.")
    document = Document("Proof Reference", Paragraph("See ", proof.reference(), "."), proof)

    result = document.validate()

    assert [issue.code for issue in result.errors] == ["unnumbered-countable-reference"]


def test_code_block_language_label_can_move_or_hide(tmp_path: Path) -> None:
    visible = CodeBlock("print('visible')", language="python", language_position="bottom-left")
    hidden = CodeBlock("README.md\nsrc/oodocs", language="text", show_language=False)
    document = Document("Code Labels", visible, hidden)

    docx_path = tmp_path / "code-labels.docx"
    pdf_path = tmp_path / "code-labels.pdf"
    html_path = tmp_path / "code-labels.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_text = "\n".join(paragraph.text for paragraph in WordDocument(docx_path).paragraphs)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert "PYTHON" in word_text
    assert "PYTHON" in pdf_text
    assert "oodocs-code-language-bottom-left" in html_text
    assert "oodocs-code-has-label-bottom" in html_text
    assert "TEXT" not in word_text
    assert "TEXT" not in pdf_text
    assert ">TEXT<" not in html_text
    assert "README.md" in word_text
    assert "README.md" in pdf_text
    assert "README.md" in html_text


def test_pdf_code_block_flowable_wraps_long_unbroken_lines() -> None:
    from oodocs.renderers.pdf import CodeBlockFlowable
    from oodocs.renderers.syntax import SyntaxToken

    flowable = CodeBlockFlowable(
        [SyntaxToken("x" * 120)],
        font_names={
            (False, False): "Courier",
            (True, False): "Courier-Bold",
            (False, True): "Courier-Oblique",
            (True, True): "Courier-BoldOblique",
        },
        font_size=9,
        leading=12,
    )

    width, height = flowable.wrap(90, 400)

    assert width == 90
    assert height > 12
    assert len(flowable._lines) > 1


def test_table_of_contents_uses_page_numbers_and_leaders_by_default(tmp_path: Path) -> None:
    document = Document(
        "TOC Test",
        TableOfContents(),
        Chapter("One", Section("Two", Paragraph("Body"))),
    )

    docx_path = tmp_path / "toc.docx"
    pdf_path = tmp_path / "toc.pdf"
    html_path = tmp_path / "toc.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    docx_settings_xml = _docx_settings_xml(docx_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    html_text = html_path.read_text(encoding="utf-8")

    assert " TOC \\f \\l \"1-9\" \\h \\z " in docx_xml
    assert ' TC "1 One" \\l 1 ' in docx_xml
    assert ' TC "1.1 Two" \\l 2 ' in docx_xml
    assert "PAGEREF heading_" not in docx_xml
    assert 'w:updateFields w:val="true"' in docx_settings_xml
    assert 'w:dirty="true"' in docx_xml
    assert "<w:fldSimple" not in docx_xml
    assert ".  .  ." in pdf_text
    assert "1 One" in pdf_text
    assert 'class="oodocs-toc-page-number"' not in html_text
    assert "oodocs-toc-leader" not in html_text
    assert "target-counter(attr(data-target), page)" not in html_text
    assert "oodocs-toc-entry-no-page" in html_text


def test_table_of_contents_options_can_hide_pages_and_limit_depth(tmp_path: Path) -> None:
    document = Document(
        "TOC Options",
        TableOfContents(
            show_page_numbers=False,
            max_level=1,
            level_styles={1: TocLevelStyle(bold=False, space_after=1)},
        ),
        Chapter("One", Section("Two", Paragraph("Body"))),
    )

    docx_path = tmp_path / "toc-options.docx"
    html_path = tmp_path / "toc-options.html"
    document.save_docx(docx_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    html_text = html_path.read_text(encoding="utf-8")

    assert "PAGEREF heading_" not in docx_xml
    assert 'class="oodocs-toc-page-number"' not in html_text
    assert 'class="oodocs-toc-entry oodocs-toc-entry-no-page oodocs-toc-entry-level-1"' in html_text
    assert 'class="oodocs-toc-entry oodocs-toc-entry-level-2"' not in html_text


def test_table_of_contents_default_styles_emphasize_only_top_level(tmp_path: Path) -> None:
    document = Document(
        "TOC Style",
        TableOfContents(),
        Chapter("Top", Section("Second", Subsection("Third", Paragraph("Body")))),
    )
    docx_path = tmp_path / "toc-style.docx"
    html_path = tmp_path / "toc-style.html"
    document.save_docx(docx_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    assert ' TC "1 Top" \\l 1 ' in docx_xml
    assert ' TC "1.1 Second" \\l 2 ' in docx_xml
    assert ' TC "1.1.1 Third" \\l 3 ' in docx_xml
    assert " TOC \\f \\l \"1-9\" \\h \\z " in docx_xml
    html_text = html_path.read_text(encoding="utf-8")
    assert 'oodocs-toc-entry-level-1" style="margin-left: 0.00in; margin-top: 12.0pt; margin-bottom: 7.0pt' in html_text
    assert 'oodocs-toc-entry-level-2" style="margin-left: 0.24in; margin-top: 3.0pt; margin-bottom: 3.0pt' in html_text
    assert 'oodocs-toc-entry-level-2" style=' in html_text and "font-weight: 400" in html_text


def test_bibtex_string_creates_citation_library() -> None:
    document = Document(
        "Bibliography Test",
        Paragraph("Example"),
        citations="""@misc{oodocs-repository,
  title = {oodocs},
  organization = {Gonie-Gonie},
  year = {2026},
  url = {https://github.com/Gonie-Gonie/oo-docs},
  note = {GitHub repository}
}""",
    )

    entry = document.citations.resolve("oodocs-repository")
    assert entry.title == "oodocs"
    assert entry.organization == "Gonie-Gonie"
    assert entry.url == "https://github.com/Gonie-Gonie/oo-docs"
    assert "GitHub repository" in entry.format_reference()


def test_citation_and_reference_styles_can_be_configured(tmp_path: Path) -> None:
    source = CitationSource(
        "Literate Programming",
        key="knuth",
        authors=("Donald E. Knuth",),
        publisher="The Computer Journal",
        year="1984",
        url="https://doi.org/10.1093/comjnl/27.2.97",
    )
    document = Document(
        "Citation Style Test",
        Paragraph("Prior work ", cite("knuth"), " remains relevant."),
        ReferenceList(),
        settings=DocumentSettings(
            theme=Theme(citations=CitationDefaults(citation_style="apa", reference_style="apa")),
        ),
        citations=[source],
    )

    assert source.format_reference("apa").startswith(
        "Knuth, D. E. (1984). Literate Programming."
    )

    docx_path = tmp_path / "citation-style.docx"
    pdf_path = tmp_path / "citation-style.pdf"
    html_path = tmp_path / "citation-style.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    paragraph_texts = [paragraph.text for paragraph in WordDocument(docx_path).paragraphs]
    assert any("Prior work (Knuth, 1984) remains relevant." in text for text in paragraph_texts)
    assert any(
        text.startswith("Knuth, D. E. (1984). Literate Programming.")
        for text in paragraph_texts
    )
    assert not any(text.startswith("[1] Knuth") for text in paragraph_texts)

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert "Prior work (Knuth, 1984) remains relevant." in pdf_text
    assert "Knuth, D. E. (1984). Literate Programming." in pdf_text

    html_text = html_path.read_text(encoding="utf-8")
    normalized_html_text = _normalized_html_text(html_path)
    assert "Prior work (Knuth, 1984) remains relevant." in normalized_html_text
    assert "Knuth, D. E. (1984). Literate Programming." in normalized_html_text
    assert 'href="#citation_1"' in html_text
    assert 'id="citation_1"' in html_text
    assert '<span class="oodocs-generated-marker">' not in html_text


def test_document_accepts_document_settings() -> None:
    settings = DocumentSettings(
        metadata_author="OODocs",
        summary="Settings test",
        subtitle="Grouped metadata",
        authors=[
            Author(
                "Example Author",
                affiliations=[Affiliation(organization="Example Lab")],
            )
        ],
        author_layout=AuthorLayout(mode="stacked"),
        cover_page=True,
        unit="cm",
        theme=Theme(page_numbers=PageNumberDefaults(show_page_numbers=True)),
    )

    document = Document("Configured", Paragraph("Body"), settings=settings)

    assert document.settings.resolved_author() == "OODocs"
    assert document.settings.summary == "Settings test"
    assert document.settings.subtitle is not None
    assert document.settings.subtitle[0].plain_text() == "Grouped metadata"
    assert document.settings.authors[0].name == "Example Author"
    assert document.settings.authors[0].affiliations[0].formatted() == "Example Lab"
    assert document.settings.author_layout.mode == "stacked"
    assert document.settings.cover_page is True
    assert document.settings.unit == "cm"
    assert round(document.settings.get_text_width(), 2) == 15.92
    assert document.settings.theme.page_numbers.show_page_numbers is True


def test_print_units_include_common_document_units() -> None:
    assert round(length_to_inches(25.4, "mm"), 8) == 1.0
    assert length_to_inches(6, "pc") == 1.0
    assert length_to_inches(1440, "twip") == 1.0
    assert length_to_inches(72, "pt") == 1.0


def test_document_unit_applies_to_media_dimensions(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    _write_sample_image(image_path)
    table = Table(
        headers=["A", "B"],
        rows=[["one", "two"]],
        column_widths=[2.54, 5.08],
    )
    figure = Figure(image_path, width=2.54)
    document = Document(
        "Metric Dimensions",
        table,
        figure,
        settings=DocumentSettings(unit="cm"),
    )

    docx_path = tmp_path / "metric.docx"
    pdf_path = tmp_path / "metric.pdf"
    html_path = tmp_path / "metric.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_document = WordDocument(docx_path)
    assert abs(int(word_document.inline_shapes[0].width) - 914400) <= 1
    assert len(PdfReader(BytesIO(pdf_path.read_bytes())).pages) == 1
    html_text = html_path.read_text(encoding="utf-8")
    assert 'style="width: 1.00in;"' in html_text
    assert 'style="width: 2.00in;"' in html_text
    assert 'width: 1.00in; max-width: 100%; height: auto' in html_text


def test_page_size_and_margins_render_to_all_outputs(tmp_path: Path) -> None:
    settings = DocumentSettings(
        unit="cm",
        page_size=PageSize(20, 10, unit="cm"),
        page_margins=PageMargins.symmetric(vertical=1.5, horizontal=2.0, unit="cm"),
    )
    document = Document("Margins", Paragraph("Body"), settings=settings)

    docx_path = tmp_path / "margins.docx"
    pdf_path = tmp_path / "margins.pdf"
    html_path = tmp_path / "margins.html"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    word_section = WordDocument(docx_path).sections[0]
    assert abs(int(word_section.page_width) - int(20 / 2.54 * 914400)) <= 300
    assert abs(int(word_section.left_margin) - int(2 / 2.54 * 914400)) <= 300
    pdf_page = PdfReader(BytesIO(pdf_path.read_bytes())).pages[0]
    assert round(float(pdf_page.mediabox.width), 1) == round(20 / 2.54 * 72, 1)
    html_text = html_path.read_text(encoding="utf-8")
    assert "size: 7.87in 3.94in;" in html_text
    assert "margin: 0.59in 0.79in 0.59in 0.79in;" in html_text
    assert "max-width: 6.30in;" in html_text


def test_object_unit_overrides_document_unit(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    _write_sample_image(image_path)
    figure = Figure(image_path, width=1.0, unit="in")
    table = Table(
        headers=["A"],
        rows=[["one"]],
        column_widths=[1.0],
        unit="in",
    )
    document = Document(
        "Local Dimensions",
        table,
        figure,
        settings=DocumentSettings(unit="cm"),
    )

    html_path = tmp_path / "local.html"
    document.save_html(html_path)

    html_text = html_path.read_text(encoding="utf-8")
    assert 'style="width: 1.00in;"' in html_text
    assert 'width: 1.00in; max-width: 100%; height: auto' in html_text


def test_figure_height_and_text_width_helpers_render(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    _write_sample_image(image_path)
    settings = DocumentSettings(
        unit="cm",
        page_size=PageSize.a4(),
        page_margins=PageMargins.all(2.0, unit="cm"),
    )
    figure = Figure(
        image_path,
        width=settings.get_text_width(0.5),
        height=3.0,
    )
    document = Document("Figure Size", figure, settings=settings)

    docx_path = tmp_path / "figure-size.docx"
    html_path = tmp_path / "figure-size.html"
    document.save_docx(docx_path)
    document.save_html(html_path)

    shape = WordDocument(docx_path).inline_shapes[0]
    assert abs(int(shape.width) - int((settings.text_width_in_inches() * 0.5) * 914400)) <= 1
    assert abs(int(shape.height) - int((3.0 / 2.54) * 914400)) <= 1
    html_text = html_path.read_text(encoding="utf-8")
    assert "width: 3.35in" in html_text
    assert "height: 1.18in" in html_text


def test_auto_footnotes_page_can_be_disabled(tmp_path: Path) -> None:
    document = Document(
        "Inline Notes",
        Paragraph(
            "Portable ",
            footnote("term", "Suppressed footnote note."),
            " stays inline.",
        ),
        settings=DocumentSettings(
            theme=Theme(
                blocks=BlockDefaults(
                    auto_footnotes_page=False,
                    footnote_placement="document",
                )
            )
        ),
    )

    docx_path = tmp_path / "inline-notes.docx"
    pdf_path = tmp_path / "inline-notes.pdf"
    html_path = tmp_path / "inline-notes.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    paragraph_texts = [paragraph.text for paragraph in WordDocument(docx_path).paragraphs]
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    normalized_html_text = _normalized_html_text(html_path)

    assert "Footnotes" not in paragraph_texts
    assert all("Suppressed footnote note." not in text for text in paragraph_texts)
    assert "Footnotes" not in pdf_text
    assert "Suppressed footnote note." not in pdf_text
    assert "Footnotes" not in normalized_html_text
    assert "Suppressed footnote note." not in normalized_html_text


def test_docx_native_page_footnotes_are_default(tmp_path: Path) -> None:
    document = Document(
        "Inline Notes",
        Paragraph(
            "Portable ",
            footnote("term", "Default native footnote note."),
            " stays inline.",
        ),
    )

    docx_path = tmp_path / "inline-notes.docx"
    document.save_docx(docx_path)

    paragraph_texts = [paragraph.text for paragraph in WordDocument(docx_path).paragraphs]
    assert "Footnotes" not in paragraph_texts
    assert all("Default native footnote note." not in text for text in paragraph_texts)

    with zipfile.ZipFile(docx_path) as archive:
        footnotes_xml = archive.read("word/footnotes.xml").decode("utf-8")
    assert "Default native footnote note." in footnotes_xml
    assert "w:footnoteReference" in _docx_document_xml(docx_path)


def test_document_renders_to_docx_and_pdf(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    _write_sample_image(image_path)
    repository_source = CitationSource(
        "oodocs",
        organization="Gonie-Gonie",
        publisher="GitHub repository",
        year="2026",
        url="https://github.com/Gonie-Gonie/oo-docs",
    )
    registered_source = CitationSource(
        "Release Notes",
        key="release-notes",
        organization="Gonie-Gonie",
        publisher="Documentation index",
        year="2026",
        url="https://github.com/Gonie-Gonie/oo-docs/releases",
    )
    unused_source = CitationSource(
        "Internal Draft",
        key="internal-draft",
        organization="Gonie-Gonie",
        year="2026",
        url="https://example.invalid/internal-draft",
    )
    artifacts_table = Table(
        headers=["Type", "Status"],
        rows=[
            ["DOCX", Paragraph("generated ", footnote("state", "Table cell footnote note."))],
            ["PDF", "generated"],
        ],
        caption="Generated artifacts.",
        column_widths=[2.5, 2.5],
        style=TableStyle(
            header_background_color="#DCE8F4",
            alternate_row_background_color="#F7FAFD",
        ),
    )
    workflow_frame = FakeDataFrame(
        columns=[("Workflow", "Step"), ("Workflow", "Target"), ("Result", "")],
        rows=[
            ["Draft review", "DOCX", "ready"],
            ["Release", "PDF", "published"],
        ],
    )
    workflow_table = Table(
        workflow_frame,
        caption="Output workflow.",
        column_widths=[2.2, 1.6, 1.6],
        style=TableStyle(alternate_row_background_color="#EEF4FA"),
    )
    merged_header_table = Table(
        headers=[
            [TableCell("Metrics", colspan=2), TableCell("Summary", rowspan=2)],
            ["Latency", "Quality"],
        ],
        rows=[
            [
                TableCell("14 ms"),
                TableCell("stable", background_color="#EEF6FF"),
                TableCell("ready"),
            ]
        ],
        caption="Merged header table.",
        column_widths=[1.6, 1.6, 1.6],
        style=TableStyle(header_background_color="#D9E6F2"),
    )
    preview_figure = Figure(
        image_path,
        caption=Paragraph("Tiny sample image."),
        width=1.0,
    )
    figure_object = FakeFigure(_build_sample_png(width=320, height=180))
    preview_figure_second = Figure(
        figure_object,
        caption=Paragraph("Second tiny sample image."),
        width=1.2,
    )
    boxed_detail = Box(
        Paragraph("A boxed paragraph can live alongside nested objects."),
        Table(
            headers=["Scope", "State"],
            rows=[["Box", "stable"]],
            column_widths=[1.4, 1.4],
        ),
        Figure(
            image_path,
            width=0.7,
        ),
        title="Review Box",
        style=BoxStyle(
            border_color="#7A8CA5",
            background_color="#F4F8FC",
            title_background_color="#DDE8F4",
        ),
    )

    document = Document(
        "Pipeline Report",
        TableOfContents(),
        Chapter(
            "Summary",
            Section(
                "Highlights",
                Paragraph(
                    "The review ",
                    comment("note", "Check the generated outputs before release.", author="pytest", initials="PT"),
                    " appears inline and is also exported to the comments page.",
                ),
                HighlightedParagraph(
                    "The ",
                    bold("oodocs"),
                    " pipeline supports ",
                    italic("styled"),
                    " text, ",
                    inline_code("code"),
                    ", and ",
                    text_color("custom color", "#0066AA", style=TextStyle(bold=True)),
                    ".",
                    style=ParagraphStyle(space_after=14),
                ),
                Paragraph(
                    markup("Inline helpers also support **bold** and *italic* markup."),
                    " Inline math such as ",
                    math(r"\alpha^2 + \beta^2 = \gamma^2"),
                    " is supported as well.",
                ),
                Paragraph(
                    "See ",
                    reference(artifacts_table),
                    " and ",
                    preview_figure.reference(),
                    " for the generated outputs.",
                ),
                Paragraph(
                    "Repository status is tracked in ",
                    cite(repository_source),
                    ".",
                ),
                Paragraph(
                    "Registered bibliography entries can still be cited as ",
                    cite("release-notes"),
                    ".",
                ),
                Paragraph(
                    "Portable footnotes such as ",
                    footnote("term", "Paragraph footnote note."),
                    " are collected automatically on the footnotes page.",
                ),
                boxed_detail,
                Subsection(
                    "Artifacts",
                    BulletList(
                        "Lists render into both DOCX and PDF.",
                        Paragraph("Paragraph instances can also be list items."),
                    ),
                    SubSubsection(
                        "Export Steps",
                        CodeBlock(
                            "from oodocs import Document\n\ndocument.save_docx('report.docx')\ndocument.save_pdf('report.pdf')",
                            language="python",
                        ),
                    ),
                    Equation(r"\int_0^1 \alpha x^2 \, dx = \frac{\alpha}{3}"),
                    NumberedList("Create the model", "Render the files"),
                    artifacts_table,
                    workflow_table,
                    merged_header_table,
                    preview_figure,
                    preview_figure_second,
                ),
            ),
        ),
        ListOfTables(),
        ListOfFigures(),
        CommentList(),
        ReferenceList(),
        settings=DocumentSettings(
            metadata_author="pytest",
            summary="Renderer integration test",
            theme=Theme(
                page_numbers=PageNumberDefaults(
                    show_page_numbers=True,
                    page_number_template="Page {page}",
                    page_number_alignment="center",
                ),
                blocks=BlockDefaults(
                    footnote_placement="document",
                    heading_numbering=HeadingNumbering(),
                    bullet_list_style=ListStyle(
                        marker_counter_format="bullet",
                        bullet="\u2022",
                        suffix="",
                    ),
                    numbered_list_style=ListStyle(
                        marker_counter_format="decimal",
                        suffix=".",
                    ),
                ),
            ),
        ),
        citations=[registered_source, unused_source],
    )

    docx_path = tmp_path / "report.docx"
    pdf_path = tmp_path / "report.pdf"
    html_path = tmp_path / "report.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    assert docx_path.exists()
    assert pdf_path.exists()
    assert html_path.exists()
    assert docx_path.stat().st_size > 0
    assert pdf_path.stat().st_size > 0
    assert html_path.stat().st_size > 0

    word_document = WordDocument(docx_path)
    paragraph_texts = [paragraph.text for paragraph in word_document.paragraphs]
    assert "Pipeline Report" in paragraph_texts
    assert "1 Summary" in paragraph_texts
    assert "1.1 Highlights" in paragraph_texts
    assert "1.1.1 Artifacts" in paragraph_texts
    assert "1.1.1.1 Export Steps" in paragraph_texts
    assert "Contents" in paragraph_texts
    assert "Comments" in paragraph_texts
    assert "Footnotes" in paragraph_texts
    assert "List of Tables" in paragraph_texts
    assert "List of Figures" in paragraph_texts
    assert "References" in paragraph_texts
    assert any("The review note[1] appears inline" in text for text in paragraph_texts)
    assert any("oodocs" in text for text in paragraph_texts)
    assert any(text == "1 Summary" for text in paragraph_texts)
    assert any(text == "1.1 Highlights" for text in paragraph_texts)
    assert any("See Table 1 and Figure 1 for the generated outputs." in text for text in paragraph_texts)
    assert any("Repository status is tracked in [1]." in text for text in paragraph_texts)
    assert any("Registered bibliography entries can still be cited as [2]." in text for text in paragraph_texts)
    assert any("Portable footnotes such as term" in text and "collected automatically on the footnotes page." in text for text in paragraph_texts)
    assert any("Inline math such as" in text and "2 + " in text and " = " in text for text in paragraph_texts)
    assert any("dx = (" in text and ")/(3)" in text for text in paragraph_texts)
    assert any("Table cell footnote note." in text for text in paragraph_texts)
    assert any("Paragraph footnote note." in text for text in paragraph_texts)
    assert any("[1] Check the generated outputs before release." in text for text in paragraph_texts)
    assert any(text == "\u2022 Lists render into both DOCX and PDF." for text in paragraph_texts)
    assert any(text == "1. Create the model" for text in paragraph_texts)
    assert paragraph_texts.count("Table 1. Generated artifacts.") >= 2
    assert paragraph_texts.count("Table 2. Output workflow.") >= 2
    assert paragraph_texts.count("Table 3. Merged header table.") >= 2
    assert paragraph_texts.count("Figure 1. Tiny sample image.") >= 2
    assert paragraph_texts.count("Figure 2. Second tiny sample image.") >= 2
    assert any("https://github.com/Gonie-Gonie/oo-docs" in text for text in paragraph_texts)
    assert any("https://github.com/Gonie-Gonie/oo-docs/releases" in text for text in paragraph_texts)
    assert all("internal-draft" not in text.lower() for text in paragraph_texts)
    assert any("from oodocs import Document" in text for text in paragraph_texts)
    assert len(word_document.inline_shapes) == 3
    summary_paragraph = next(
        paragraph
        for paragraph in word_document.paragraphs
        if "The review note[1] appears inline" in paragraph.text
    )
    assert summary_paragraph.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY

    assert len(word_document.tables) == 4
    assert "Review Box" in word_document.tables[0].cell(0, 0).text
    assert word_document.tables[1].cell(1, 0).text == "DOCX"
    assert word_document.tables[1].cell(1, 1).text.startswith("generated")
    assert word_document.tables[1].cell(2, 1).text == "generated"
    assert word_document.tables[2].cell(2, 0).text == "Draft review"
    assert word_document.tables[2].cell(3, 1).text == "PDF"
    assert word_document.tables[3].cell(2, 0).text == "14 ms"
    assert word_document.tables[3].cell(2, 2).text == "ready"
    assert word_document.styles["Normal"].font.name == "Times New Roman"
    assert word_document.styles["Title"].font.name == "Times New Roman"
    assert word_document.styles["Heading 1"].font.name == "Times New Roman"
    assert word_document.styles["Heading 2"].font.name == "Times New Roman"
    assert word_document.styles["Heading 3"].font.name == "Times New Roman"
    assert word_document.styles["Heading 4"].font.name == "Times New Roman"
    assert word_document.styles["Title"].font.color.rgb == RGBColor(0, 0, 0)
    assert word_document.styles["Heading 1"].font.color.rgb == RGBColor(0, 0, 0)
    assert word_document.styles["Heading 2"].font.color.rgb == RGBColor(0, 0, 0)
    assert word_document.styles["Heading 3"].font.color.rgb == RGBColor(0, 0, 0)
    assert word_document.styles["Heading 4"].font.color.rgb == RGBColor(0, 0, 0)
    heading_styles = {paragraph.text: paragraph.style.name for paragraph in word_document.paragraphs if paragraph.text in {"Comments", "List of Tables", "List of Figures", "References"}}
    assert heading_styles["Comments"] == "Heading 2"
    assert heading_styles["List of Tables"] == "Heading 2"
    assert heading_styles["List of Figures"] == "Heading 2"
    assert heading_styles["References"] == "Heading 2"
    assert next(paragraph.style.name for paragraph in word_document.paragraphs if paragraph.text == "Footnotes") == "Heading 2"
    assert len(word_document.comments) == 1
    assert "Check the generated outputs before release." in "\n".join(
        paragraph.text
        for comment_item in word_document.comments
        for paragraph in comment_item.paragraphs
    )
    footer_xml = word_document.sections[0].footer.paragraphs[0]._p.xml
    assert "<w:instrText" in footer_xml
    assert " PAGE " in footer_xml
    assert word_document.sections[0].footer.paragraphs[0].text.startswith("Page ")
    inline_math_paragraph = next(paragraph for paragraph in word_document.paragraphs if "Inline math such as" in paragraph.text)
    assert any(run.text == "2" and run.font.superscript for run in inline_math_paragraph.runs)
    equation_paragraph = next(paragraph for paragraph in word_document.paragraphs if "dx = (" in paragraph.text and ")/(3)" in paragraph.text)
    assert any(run.text == "2" and run.font.superscript for run in equation_paragraph.runs)
    assert any(run.text == "0" and run.font.subscript for run in equation_paragraph.runs)
    assert any(run.text == "1" and run.font.superscript for run in equation_paragraph.runs)
    docx_xml = _docx_document_xml(docx_path)
    assert "Review Box" in docx_xml
    assert "A boxed paragraph can live alongside nested objects." in docx_xml
    assert "stable" in docx_xml
    assert "D9E6F2" in docx_xml
    assert "DCE8F4" in docx_xml
    assert len(figure_object.calls) >= 2
    assert all(call.get("format") == "png" for call in figure_object.calls)

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages)
    assert "Pipeline Report" in pdf_text
    assert "1 Summary" in pdf_text
    assert "1.1 Highlights" in pdf_text
    assert "1.1.1 Artifacts" in pdf_text
    assert "1.1.1.1 Export Steps" in pdf_text
    assert "Contents" in pdf_text
    assert "Comments" in pdf_text
    assert "Footnotes" in pdf_text
    assert "The review note[1] appears inline and is also exported to the comments page." in pdf_text
    assert "See Table 1 and Figure 1 for the generated outputs." in pdf_text
    assert "Repository status is tracked in [1]." in pdf_text
    assert "Registered bibliography entries can still be cited as [2]." in pdf_text
    assert "Portable footnotes such as term" in pdf_text and "collected automatically on the footnotes page." in pdf_text
    assert "Inline math such as" in pdf_text
    assert "dx = (" in pdf_text
    assert "Table cell footnote note." in pdf_text
    assert "Paragraph footnote note." in pdf_text
    assert "[1] Check the generated outputs before release." in pdf_text
    assert "Review Box" in pdf_text
    assert "A boxed paragraph can live alongside nested objects." in pdf_text
    assert "stable" in pdf_text
    assert pdf_text.count("Table 1. Generated artifacts.") >= 2
    assert pdf_text.count("Table 2. Output workflow.") >= 2
    assert pdf_text.count("Table 3. Merged header table.") >= 2
    assert pdf_text.count("Figure 1. Tiny sample image.") >= 2
    assert pdf_text.count("Figure 2. Second tiny sample image.") >= 2
    assert "List of Tables" in pdf_text
    assert "List of Figures" in pdf_text
    assert "References" in pdf_text
    assert "https://github.com/Gonie-Gonie/oo-docs" in pdf_text
    assert "https://github.com/Gonie-Gonie/oo-docs/releases" in pdf_text
    assert "Internal Draft" not in pdf_text
    assert "Lists render into both DOCX and PDF." in pdf_text
    assert "from oodocs import Document" in pdf_text
    assert "1\nLists render into both DOCX and PDF." not in pdf_text
    assert "1.\nCreate the model" in pdf_text
    assert _pdf_image_draw_count(pdf_path) == 3
    pdf_fonts = _pdf_font_names(pdf_path)
    assert any(font == "/Times-Roman" or "TimesNewRomanPSMT" in font for font in pdf_fonts)
    assert any(font == "/Times-Bold" or "TimesNewRomanPS-Bold" in font for font in pdf_fonts)
    assert any(
        font in {"/Times-BoldItalic", "/Times-Italic"}
        or "TimesNewRomanPS-BoldItalic" in font
        or "TimesNewRomanPS-Italic" in font
        for font in pdf_fonts
    )
    assert any(font.startswith("/Courier") or "CourierNewPS" in font for font in pdf_fonts)
    pdf_content = _pdf_content_bytes(pdf_path)
    assert b"Page 1" in pdf_content
    assert b"18 Tf" in pdf_content
    assert b"15 Tf" in pdf_content
    assert b"13 Tf" in pdf_content
    assert b"11.5 Tf" in pdf_content
    assert b"Comments" in pdf_content
    assert b"15 Tf" in _pdf_text_context(pdf_path, "List of Tables")
    assert b"15 Tf" in _pdf_text_context(pdf_path, "List of Figures")
    assert b"15 Tf" in _pdf_text_context(pdf_path, "Comments")
    assert b"15 Tf" in _pdf_text_context(pdf_path, "References")
    assert b"15 Tf" in _pdf_text_context(pdf_path, "Contents")

    html_text = html_path.read_text(encoding="utf-8")
    normalized_html_text = _normalized_html_text(html_path)
    assert "Pipeline Report" in normalized_html_text
    assert "1 Summary" in normalized_html_text
    assert "1.1 Highlights" in normalized_html_text
    assert "1.1.1 Artifacts" in normalized_html_text
    assert "1.1.1.1 Export Steps" in normalized_html_text
    assert "Contents" in normalized_html_text
    assert "Comments" in normalized_html_text
    assert "Footnotes" in normalized_html_text
    assert "List of Tables" in normalized_html_text
    assert "List of Figures" in normalized_html_text
    assert "References" in normalized_html_text
    assert "The review note [1] appears inline and is also exported to the comments page." in normalized_html_text
    assert "See Table 1 and Figure 1 for the generated outputs." in normalized_html_text
    assert "Repository status is tracked in [1]" in normalized_html_text
    assert "Registered bibliography entries can still be cited as [2]" in normalized_html_text
    assert "Portable footnotes such as term" in normalized_html_text
    assert "Table cell footnote note." in normalized_html_text
    assert "Paragraph footnote note." in normalized_html_text
    assert "[1] Check the generated outputs before release." in normalized_html_text
    assert "Review Box" in normalized_html_text
    assert "A boxed paragraph can live alongside nested objects." in normalized_html_text
    assert "stable" in normalized_html_text
    assert normalized_html_text.count("Table 1. Generated artifacts.") >= 2
    assert normalized_html_text.count("Table 2. Output workflow.") >= 2
    assert normalized_html_text.count("Table 3. Merged header table.") >= 2
    assert normalized_html_text.count("Figure 1. Tiny sample image.") >= 2
    assert normalized_html_text.count("Figure 2. Second tiny sample image.") >= 2
    assert "https://github.com/Gonie-Gonie/oo-docs" in normalized_html_text
    assert "https://github.com/Gonie-Gonie/oo-docs/releases" in normalized_html_text
    assert "Internal Draft" not in normalized_html_text
    assert "Lists render into both DOCX and PDF." in normalized_html_text
    assert "from oodocs import Document" in normalized_html_text
    assert html_text.count("data:image/png;base64,") == 3
    assert 'href="#table_1"' in html_text
    assert 'href="#figure_1"' in html_text
    assert 'id="table_1"' in html_text
    assert 'id="figure_1"' in html_text
    assert 'id="citation_1"' in html_text
    assert 'id="comment_1"' in html_text
    assert 'id="footnote_1"' in html_text
