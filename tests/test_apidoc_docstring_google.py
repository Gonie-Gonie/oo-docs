from __future__ import annotations

from oodocs.apidoc import parse_docstring


def test_google_docstring_parser_extracts_sections() -> None:
    parsed = parse_docstring(
        """Load data.

        Args:
            path (str): Input path.

        Returns:
            bool: Whether loading succeeded.

        Examples:
            >>> load("data.csv")
            True
        """,
        style="google",
    )

    assert parsed.style == "google"
    assert parsed.parameters[0].name == "path"
    assert parsed.returns is not None
    assert parsed.examples
