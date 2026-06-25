from __future__ import annotations

import inspect

from oodocs.apidoc import ApiDocstringParser, detect_docstring_style, parse_docstring
from tests.fixtures.apidoc_docstrings import google, markdown_style, numpy, plain, sphinx


def test_auto_docstring_parser_detects_fixture_styles() -> None:
    parser = ApiDocstringParser.auto()

    assert detect_docstring_style(inspect.getdoc(google.load_widget)) == "google"
    assert detect_docstring_style(inspect.getdoc(numpy.load_widget)) == "numpy"
    assert detect_docstring_style(inspect.getdoc(sphinx.load_widget)) == "sphinx"
    assert detect_docstring_style(inspect.getdoc(markdown_style.load_widget)) == "markdown"
    assert detect_docstring_style(inspect.getdoc(plain.load_widget)) == "plain"
    assert parser.detect(inspect.getdoc(google.load_widget)) == "google"
    assert parse_docstring(inspect.getdoc(google.load_widget), style=parser).style == "google"
