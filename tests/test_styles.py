from __future__ import annotations

from datetime import date

import pytest

from oodocs import (
    BlockDefaults,
    BorderStyle,
    BoxStyle,
    CaptionDefaults,
    CounterStyle,
    FootnoteDefaults,
    FootnoteStyle,
    GeneratedContentDefaults,
    HeaderFooterDefaults,
    HeadingStyle,
    HeadingNumbering,
    InlineChipStyle,
    ListStyle,
    LocaleDefaults,
    PageNumberDefaults,
    Padding,
    ParagraphStyle,
    RunInTitleStyle,
    StrokeStyle,
    StyleSheet,
    TableCellStyle,
    TableStyle,
    TextStyle,
    Theme,
    TypographyDefaults,
)


def test_text_style_normalizes_text_color() -> None:
    style = TextStyle(text_color="#ff0000")

    assert style.text_color == "FF0000"


def test_paragraph_style_normalizes_text_alignment() -> None:
    style = ParagraphStyle(text_alignment="Center")

    assert style.text_alignment == "center"


def test_run_in_title_style_validates_separator() -> None:
    with pytest.raises(TypeError, match="separator"):
        RunInTitleStyle(separator=object())  # type: ignore[arg-type]


def test_padding_factories_and_point_conversion() -> None:
    assert Padding.all(4).as_tuple() == (4, 4, 4, 4)
    assert Padding.symmetric(vertical=2, horizontal=5).as_tuple() == (2, 5, 2, 5)
    assert Padding.all(1, unit="in").to_points() == (72.0, 72.0, 72.0, 72.0)

    with pytest.raises(ValueError, match="em padding"):
        Padding.all(0.5, unit="em").to_points()


def test_border_style_factories_and_units() -> None:
    border = BorderStyle.solid("#cbd5e1", width=0.5, radius=0.4, radius_unit="em")

    assert border.color == "CBD5E1"
    assert border.width_points() == 0.5
    assert border.radius_em() == 0.4
    assert BorderStyle.none().color is None
    assert BorderStyle.none().width == 0.0


def test_table_style_booktabs_preset_uses_horizontal_rules() -> None:
    style = TableStyle.booktabs()

    assert style.border.color is None
    assert style.top_rule is not None
    assert style.top_rule.width_points() == 1.0
    assert style.header_rule is not None
    assert style.header_rule.width_points() == 0.6
    assert style.bottom_rule is not None
    assert style.bottom_rule.width_points() == 1.0
    header_edges = style._border_edges(row=0, rowspan=1, row_count=3, header_row_count=1)
    body_edges = style._border_edges(row=1, rowspan=1, row_count=3, header_row_count=1)
    bottom_edges = style._border_edges(row=2, rowspan=1, row_count=3, header_row_count=1)

    assert header_edges["top"].width_points() == 1.0
    assert header_edges["bottom"].width_points() == 0.6
    assert header_edges["left"].color is None
    assert body_edges["top"].color is None
    assert body_edges["bottom"].color is None
    assert bottom_edges["bottom"].width_points() == 1.0

    sheet = StyleSheet.default()
    resolved = sheet.resolve("table", "booktabs")
    round_tripped = StyleSheet.from_dict(sheet.to_dict()).resolve("table", "booktabs")

    assert isinstance(resolved, TableStyle)
    assert isinstance(round_tripped, TableStyle)
    assert round_tripped.top_rule is not None
    assert round_tripped.top_rule.width_points() == 1.0


def test_stroke_style_factories_and_point_conversion() -> None:
    stroke = StrokeStyle.solid("#334155", width=0.75)

    assert stroke.color == "334155".upper()
    assert stroke.width_points() == 0.75
    assert StrokeStyle.none().color is None
    assert StrokeStyle.none().width == 0.0


def test_counter_style_formats_values_and_sequences() -> None:
    marker = CounterStyle(counter_format="upper-roman", prefix="(", suffix=")")
    sequence = CounterStyle(counter_format="lower-alpha", separator="-")

    assert marker.format_value(3) == "(III)"
    assert sequence.format_sequence([1, 2, 3]) == "a-b-c"
    assert CounterStyle(counter_format="bullet", bullet="*").format_value(1) == "*"

    with pytest.raises(ValueError, match="start"):
        CounterStyle(start=0)


def test_footnote_defaults_format_stream_markers() -> None:
    defaults = FootnoteDefaults(
        stream_styles={
            "symbols": FootnoteStyle.symbol(("*", "#")),
            "review": FootnoteStyle(CounterStyle(prefix="R")),
        }
    )

    assert defaults.format_marker("default", 2) == "2"
    assert defaults.format_marker("symbols", 1) == "*"
    assert defaults.format_marker("symbols", 3) == "**"
    assert defaults.format_marker("review", 2) == "R2"
    assert defaults.is_native_docx_compatible("default")
    assert not defaults.is_native_docx_compatible("symbols")
    assert not FootnoteDefaults(
        stream_styles={"default": FootnoteStyle.symbol()}
    ).is_native_docx_compatible("default")

    with pytest.raises(ValueError, match="stream"):
        FootnoteDefaults(stream_styles={"": FootnoteStyle()})
    with pytest.raises(ValueError, match="symbols"):
        FootnoteStyle.symbol(())


def test_counter_style_drives_list_heading_page_and_part_defaults() -> None:
    list_style = ListStyle(marker=CounterStyle(counter_format="upper-alpha", suffix=")"))
    heading_numbering = HeadingNumbering(
        level_styles=(
            CounterStyle(counter_format="upper-roman"),
            CounterStyle(counter_format="lower-alpha"),
        ),
        prefix="[",
        suffix="]",
    )
    page_numbers = PageNumberDefaults(
        front_matter_counter=CounterStyle(counter_format="lower-roman")
    )
    blocks = BlockDefaults(part_counter=CounterStyle(counter_format="upper-roman"))

    assert list_style.marker_for(1) == "B)"
    assert heading_numbering.format_label([2, 3]) == "[II.c]"
    assert page_numbers.front_matter_counter.format_value(4) == "iv"
    assert blocks.part_counter.format_value(2) == "II"


def test_theme_resolves_heading_and_caption_defaults() -> None:
    theme = Theme(
        typography=TypographyDefaults(
            body_font_name="Arial",
            monospace_font_name="Consolas",
            heading_sizes=(20.0, 16.0),
        ),
        captions=CaptionDefaults(
            table_caption_label="Tbl.",
            figure_reference_label="Fig.",
        ),
    )

    assert theme.resolve_body_font() == "Arial"
    assert theme.resolve_monospace_font() == "Consolas"
    assert theme.resolve_heading_size(3) == 16.0
    assert theme.resolve_heading_emphasis(1) == (True, False)
    assert theme.resolve_heading_text_alignment(2) == "left"
    assert theme.format_appendix_heading_label([1, 2]) == "A.2"
    assert theme.resolve_caption_label("table", "caption") == "Tbl."
    assert theme.resolve_caption_label("figure", "reference") == "Fig."

    with pytest.raises(ValueError, match="caption label kind"):
        theme.resolve_caption_label("equation", "caption")

    with pytest.raises(ValueError, match="caption label context"):
        theme.resolve_caption_label("table", "inline")


def test_heading_style_merges_level_defaults_and_overrides() -> None:
    level_style = HeadingStyle(
        text_style=TextStyle(font_size=14, bold=False, text_color="#123456"),
        space_before=4,
        space_after=5,
        text_alignment="center",
        numbering=CounterStyle(counter_format="upper-alpha"),
    )
    theme = Theme(blocks=BlockDefaults(heading_styles={2: level_style}))

    resolved = theme.resolve_heading_style(2)

    assert resolved.text_style.font_size == 14
    assert resolved.text_style.bold is False
    assert resolved.text_style.italic is False
    assert resolved.text_style.text_color == "123456"
    assert resolved.space_before == 4
    assert resolved.space_after == 5
    assert resolved.text_alignment == "center"
    assert theme.resolve_heading_size(2) == 14
    assert theme.resolve_heading_emphasis(2) == (False, False)
    assert theme.resolve_heading_text_alignment(2) == "center"
    assert theme.format_heading_label([1, 2]) == "1.B"

    override = HeadingStyle(text_style=TextStyle(italic=True), space_after=2)
    overridden = theme.resolve_heading_style(2, override)

    assert overridden.text_style.font_size == 14
    assert overridden.text_style.bold is False
    assert overridden.text_style.italic is True
    assert overridden.space_before == 4
    assert overridden.space_after == 2


def test_heading_style_validates_values() -> None:
    with pytest.raises(ValueError, match="space_before"):
        HeadingStyle(space_before=-1)

    with pytest.raises(ValueError, match="heading_styles keys"):
        BlockDefaults(heading_styles={0: HeadingStyle()})

    with pytest.raises(TypeError, match="HeadingStyle"):
        BlockDefaults(heading_styles={1: object()})  # type: ignore[dict-item]


def test_theme_resolves_generated_page_titles() -> None:
    theme = Theme(
        generated_content=GeneratedContentDefaults(
            list_of_tables_title="Tables",
            list_of_references_title="Bibliography",
        )
    )

    assert theme.resolve_generated_page_title("list_of_tables") == "Tables"
    assert theme.resolve_generated_page_title("list_of_references") == "Bibliography"

    with pytest.raises(ValueError, match="unsupported generated content kind"):
        theme.resolve_generated_page_title("appendix")


def test_theme_from_locale_resolves_korean_labels_dates_and_font_guidance() -> None:
    theme = Theme.from_locale("ko-KR")

    assert theme.resolve_language_tag() == "ko-KR"
    assert theme.resolve_body_font() == "Malgun Gothic"
    assert theme.resolve_monospace_font() == "D2Coding"
    assert theme.resolve_caption_label("table", "caption") == "표"
    assert theme.resolve_caption_label("figure", "reference") == "그림"
    assert theme.resolve_generated_page_title("table_of_contents") == "목차"
    assert theme.resolve_generated_page_title("list_of_references") == "참고문헌"
    assert theme.resolve_generated_page_title("list_of_glossary_terms") == "용어집"
    assert theme.resolve_glossary_headers() == ("용어", "정의")
    assert theme.format_date(date(2026, 6, 29)) == "2026. 6. 29."
    assert theme.format_date("2026-06-29") == "2026. 6. 29."
    assert "Malgun Gothic" in theme.pdf_font_fallback_guide()

    with pytest.raises(ValueError, match="unsupported built-in locale"):
        LocaleDefaults.from_locale("fr-FR")
    with pytest.raises(TypeError, match="Theme.locale"):
        Theme(locale=object())  # type: ignore[arg-type]


def test_header_footer_defaults_resolve_templates_and_legacy_page_numbers() -> None:
    header_footer = HeaderFooterDefaults(
        header_left="{chapter}",
        footer_center="{page}",
        first_footer_center="cover {page}",
        different_first_page=True,
    )
    assert header_footer.content_for("header", "left") == "{chapter}"
    assert header_footer.content_for("footer", "center", page_kind="first") == "cover {page}"

    theme = Theme(header_footer=header_footer)
    assert theme.uses_header_footer()
    assert theme.format_header_footer_text(
        theme.resolve_header_footer_template("footer", "center"),
        page_number=3,
        title="Report",
        chapter="Methods",
        section="Scope",
    ) == "3"

    legacy = Theme(page_numbers=PageNumberDefaults(show_page_numbers=True))
    assert legacy.uses_header_footer()
    assert legacy.resolve_header_footer_template("footer", "center") == "{page}"


def test_stylesheet_resolves_prefixed_names_and_roundtrips() -> None:
    styles = StyleSheet.default()
    styles.register("paragraph", "lead", ParagraphStyle(space_after=10))
    styles.register("box", "callout", BoxStyle(padding=Padding.all(8)))
    styles.register("chip", "state.ok", InlineChipStyle(uppercase=True))

    assert isinstance(styles.resolve("table", "table.compact"), TableStyle)
    assert isinstance(styles.resolve("table", "nomenclature.inner"), TableStyle)
    assert isinstance(styles.resolve("table_cell", "table_cell.numeric"), TableCellStyle)
    assert styles.resolve("paragraph", "lead").space_after == 10
    assert styles.resolve("chip", "chip.state.ok").uppercase is True

    restored = StyleSheet.from_dict(styles.to_dict())

    assert isinstance(restored.resolve("box", "callout"), BoxStyle)
    assert restored.resolve("chip", "status.success").uppercase is True


def test_stylesheet_rejects_unknown_or_wrong_category_styles() -> None:
    styles = StyleSheet.default()

    with pytest.raises(KeyError, match="Unknown table style"):
        styles.resolve("table", "missing")

    with pytest.raises(TypeError, match="BoxStyle"):
        styles.register("box", "not-a-box", TableStyle())


def test_style_css_class_normalization() -> None:
    assert ParagraphStyle(css_class=" lead   dense ").css_class == "lead dense"
    assert BoxStyle(css_class="callout").css_class == "callout"
    assert TableStyle(css_class="data-table").css_class == "data-table"
    assert InlineChipStyle(css_class="state ok").css_class == "state ok"

    with pytest.raises(TypeError, match="css_class"):
        ParagraphStyle(css_class=object())  # type: ignore[arg-type]
