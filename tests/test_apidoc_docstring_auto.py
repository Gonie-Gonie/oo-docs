from __future__ import annotations

from oodocs.apidoc import ApiDocstringParser, detect_docstring_style, parse_docstring


def test_auto_docstring_parser_detects_google_style() -> None:
    text = "Load data.\n\nArgs:\n    path: Input path."
    parser = ApiDocstringParser.auto()

    assert detect_docstring_style(text) == "google"
    assert parser.detect(text) == "google"
    assert parse_docstring(text, style=parser).style == "google"
