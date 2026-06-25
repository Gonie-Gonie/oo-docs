from __future__ import annotations

from oodocs.apidoc import parse_docstring


def test_plain_docstring_parser_extracts_summary_and_description() -> None:
    parsed = parse_docstring("Short summary.\n\nLonger description.", style="plain")

    assert parsed.style == "plain"
    assert parsed.summary == "Short summary."
    assert parsed.description == "Longer description."
    assert not parsed.parameters
