from __future__ import annotations

from oodocs.apidoc import parse_docstring


def test_sphinx_docstring_parser_extracts_field_lists() -> None:
    parsed = parse_docstring(
        "Load data.\n\n:param path: Input path.\n:type path: str\n:returns: Loaded data.",
        style="sphinx",
    )

    assert parsed.style == "sphinx"
    assert parsed.parameters[0].name == "path"
    assert parsed.parameters[0].annotation == "str"
    assert parsed.returns is not None
