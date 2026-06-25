from __future__ import annotations

from oodocs.apidoc import parse_docstring


def test_numpy_docstring_parser_extracts_parameters_and_returns() -> None:
    parsed = parse_docstring(
        """Load data.

        Parameters
        ----------
        path : str
            Input path.

        Returns
        -------
        bool
            Whether loading succeeded.
        """,
        style="numpy",
    )

    assert parsed.style == "numpy"
    assert parsed.parameters[0].annotation == "str"
    assert parsed.returns is not None
