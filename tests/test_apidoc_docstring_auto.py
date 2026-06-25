from __future__ import annotations

import inspect

import pytest

from oodocs.apidoc import (
    ApiCollectConfig,
    ApiDocstringParser,
    ParsedDocstring,
    detect_docstring_style,
    docstring_parser_names,
    is_docstring_style_supported,
    parse_docstring,
    register_docstring_parser,
)
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


def test_auto_docstring_parser_detects_markdown_yields_section() -> None:
    parser = ApiDocstringParser.auto()
    docstring = """Iterate values.

    ## Yields

    str: Next value.
    """

    parsed = parse_docstring(docstring, style=parser)

    assert parser.detect(docstring) == "markdown"
    assert parsed.style == "markdown"
    assert parsed.returns is not None
    assert parsed.returns.annotation == "str"
    assert parsed.returns.description == "Next value."
    assert parsed.returns.documented


def test_custom_docstring_parser_registry_supports_reusable_parser_objects() -> None:
    style = "auto-fixture-brief"

    def parse_brief(
        text: str | None,
        qualname: str | None = None,
        module: str | None = None,
    ) -> ParsedDocstring:
        scope = ".".join(part for part in (module, qualname) if part)
        summary = f"{scope}: {(text or '').strip()}" if scope else (text or "").strip()
        return ParsedDocstring(summary=summary, style=style)

    if style not in docstring_parser_names():
        register_docstring_parser(style, parse_brief)

    parser = ApiDocstringParser.from_value({"style": style})
    config = ApiCollectConfig(docstring_style=parser)
    parsed = parse_docstring("Brief summary.", style=config.docstring_parser(), qualname="load", module="pkg")

    assert ApiDocstringParser.from_value(parser) is parser
    assert ApiDocstringParser.from_dict(parser.to_dict()) == parser
    assert config.to_dict()["docstring_style"] == style
    assert config.docstring_parser() == parser
    assert parsed.style == style
    assert parsed.summary == "pkg.load: Brief summary."
    assert parser.detect("Brief summary.") == style
    assert is_docstring_style_supported(style)
    assert is_docstring_style_supported(parser)
    assert style in docstring_parser_names()

    with pytest.raises(ValueError, match="already registered"):
        register_docstring_parser(style, parse_brief)
