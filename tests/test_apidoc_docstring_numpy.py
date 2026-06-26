from __future__ import annotations

import inspect

import oodocs.apidoc.docstring as docstring_module
from oodocs.apidoc import parse_docstring
from tests.fixtures.apidoc_docstrings import numpy as fixture


def test_numpy_docstring_fixture_extracts_shared_fields() -> None:
    function = parse_docstring(inspect.getdoc(fixture.load_widget), style="numpy")
    class_doc = parse_docstring(inspect.getdoc(fixture.Widget), style="numpy")
    method = parse_docstring(inspect.getdoc(fixture.Widget.render), style="numpy")
    property_doc = parse_docstring(inspect.getdoc(fixture.Widget.title.fget), style="numpy")
    dataclass_doc = parse_docstring(inspect.getdoc(fixture.WidgetRecord), style="numpy")

    assert function.style == "numpy"
    assert function.parameters[0].annotation == "str"
    assert function.returns is not None
    assert function.exceptions[0].exception == "ValueError"
    assert function.examples
    assert function.notes
    assert function.renderer_notes[0].format == "html"
    assert function.deprecated
    assert function.deprecation_message == "Use load_widget_v2 instead."
    assert class_doc.parameters[0].name == "name"
    assert class_doc.attributes[0].name == "label"
    assert method.parameters[0].name == "path"
    assert property_doc.returns is not None
    assert dataclass_doc.attributes[0].name == "identifier"


def test_numpy_fallback_parser_extracts_raises_sections(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    parsed = parse_docstring(
        """
        Load data.

        Raises
        ------
        ValueError
            If the path is empty.
        RuntimeError : If loading fails.
        TypeError, OSError
            If input types or filesystem state are invalid.
        """,
        style="numpy",
    )

    assert [(item.exception, item.description) for item in parsed.exceptions] == [
        ("ValueError", "If the path is empty."),
        ("RuntimeError", "If loading fails."),
        ("TypeError, OSError", "If input types or filesystem state are invalid."),
    ]


def test_numpy_parser_merges_other_parameters() -> None:
    parsed = parse_docstring(
        """
        Load data.

        Parameters
        ----------
        path : str
            Input path.

        Other Parameters
        ----------------
        retries : int
            Retry count.
        timeout : float
            Timeout in seconds.
        """,
        style="numpy",
    )

    assert [(item.name, item.annotation, item.description) for item in parsed.parameters] == [
        ("path", "str", "Input path."),
        ("retries", "int", "Retry count."),
        ("timeout", "float", "Timeout in seconds."),
    ]


def test_numpy_fallback_parser_merges_other_parameters(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    parsed = parse_docstring(
        """
        Load data.

        Parameters
        ----------
        path : str
            Input path.

        Other Parameters
        ----------------
        retries : int
            Retry count.
        """,
        style="numpy",
    )

    assert [(item.name, item.annotation, item.description) for item in parsed.parameters] == [
        ("path", "str", "Input path."),
        ("retries", "int", "Retry count."),
    ]


def test_numpy_fallback_parser_preserves_return_values(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    single = parse_docstring(
        """
        Load data.

        Returns
        -------
        bool
            Whether loading succeeded.
        """,
        style="numpy",
    )
    multiple = parse_docstring(
        """
        Load data.

        Returns
        -------
        path : str
            Output path.
        count : int
            Number of rows.
        """,
        style="numpy",
    )

    assert single.returns is not None
    assert single.returns.annotation == "bool"
    assert single.returns.description == "Whether loading succeeded."
    assert multiple.returns is not None
    assert multiple.returns.annotation is None
    assert multiple.returns.description == "path (str): Output path.\ncount (int): Number of rows."
