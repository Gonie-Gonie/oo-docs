from __future__ import annotations

import pytest

from oodocs import (
    BlockDefaults,
    BorderStyle,
    BoxStyle,
    CounterStyle,
    HeadingNumbering,
    InlineChipStyle,
    ListStyle,
    PageNumberDefaults,
    Padding,
    ParagraphStyle,
    RunInTitleStyle,
    StrokeStyle,
    StyleSheet,
    TableCellStyle,
    TableStyle,
    TextStyle,
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
