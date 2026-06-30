from __future__ import annotations

import inspect

import oodocs.apidoc.docstring as docstring_module
from oodocs.apidoc import parse_docstring
from tests.fixtures.apidoc_docstrings import google as fixture


def test_google_docstring_fixture_extracts_shared_fields() -> None:
    function = parse_docstring(inspect.getdoc(fixture.load_widget), style="google")
    class_doc = parse_docstring(inspect.getdoc(fixture.Widget), style="google")
    method = parse_docstring(inspect.getdoc(fixture.Widget.render), style="google")
    property_doc = parse_docstring(inspect.getdoc(fixture.Widget.title.fget), style="google")
    dataclass_doc = parse_docstring(inspect.getdoc(fixture.WidgetRecord), style="google")

    assert function.style == "google"
    assert function.parameters[0].name == "path"
    assert function.returns is not None
    assert function.exceptions[0].exception == "ValueError"
    assert function.examples
    assert [item.label for item in function.see_also] == [
        "Widget.render",
        "WidgetRecord",
        "Widget.title",
    ]
    assert function.see_also_notes == [
        "DocumentSettings for metadata and layout configuration."
    ]
    assert function.notes
    assert function.renderer_notes[0].output_format == "html"
    assert class_doc.parameters[0].name == "name"
    assert class_doc.attributes[0].name == "label"
    assert method.parameters[0].name == "path"
    assert property_doc.returns is not None
    assert dataclass_doc.attributes[0].name == "identifier"


def test_google_docstring_parses_keyword_args() -> None:
    parsed = parse_docstring(
        """
        Load data.

        Args:
            path (str): Input path.

        Keyword Args:
            retries (int): Retry count.
            timeout (float): Timeout in seconds.
        """,
        style="google",
    )

    assert [(item.name, item.annotation, item.description) for item in parsed.parameters] == [
        ("path", "str", "Input path."),
        ("retries", "int", "Retry count."),
        ("timeout", "float", "Timeout in seconds."),
    ]


def test_google_fallback_docstring_parses_keyword_args(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    parsed = parse_docstring(
        """
        Load data.

        Args:
            path (str): Input path.

        Keyword Arguments:
            retries (int): Retry count.
        """,
        style="google",
    )

    assert [(item.name, item.annotation, item.description) for item in parsed.parameters] == [
        ("path", "str", "Input path."),
        ("retries", "int", "Retry count."),
    ]
