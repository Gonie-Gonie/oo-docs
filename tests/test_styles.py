from __future__ import annotations

import pytest

from oodocs import (
    BorderStyle,
    Padding,
    ParagraphStyle,
    RunInTitleStyle,
    StrokeStyle,
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
