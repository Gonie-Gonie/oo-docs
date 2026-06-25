from __future__ import annotations

from oodocs.apidoc import parse_docstring


def test_markdown_docstring_parser_extracts_parameter_tables() -> None:
    parsed = parse_docstring(
        """Load data.

        ## Parameters

        | Name | Type | Description |
        | --- | --- | --- |
        | path | str | Input path. |

        ## Returns

        Loaded data.
        """,
        style="markdown",
    )

    assert parsed.style == "markdown"
    assert parsed.parameters[0].name == "path"
    assert parsed.returns is not None
