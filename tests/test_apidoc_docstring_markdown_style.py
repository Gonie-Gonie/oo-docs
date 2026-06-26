from __future__ import annotations

import inspect

from oodocs.apidoc import parse_docstring
from tests.fixtures.apidoc_docstrings import markdown_style as fixture


def test_markdown_docstring_fixture_extracts_shared_fields() -> None:
    function = parse_docstring(inspect.getdoc(fixture.load_widget), style="markdown")
    class_doc = parse_docstring(inspect.getdoc(fixture.Widget), style="markdown")
    method = parse_docstring(inspect.getdoc(fixture.Widget.render), style="markdown")
    property_doc = parse_docstring(inspect.getdoc(fixture.Widget.title.fget), style="markdown")
    dataclass_doc = parse_docstring(inspect.getdoc(fixture.WidgetRecord), style="markdown")

    assert function.style == "markdown"
    assert function.parameters[0].name == "path"
    assert function.parameters[0].annotation == "str"
    assert function.parameters[0].description == "Input path."
    assert function.returns is not None
    assert function.exceptions[0].exception == "ValueError"
    assert function.exceptions[0].description == "If the path is empty."
    assert function.examples
    assert function.notes
    assert function.renderer_notes[0].output_format == "html"
    assert class_doc.parameters[0].name == "name"
    assert class_doc.parameters[0].annotation == "str"
    assert class_doc.parameters[0].description == "Widget name value."
    assert class_doc.attributes[0].name == "label"
    assert method.parameters[0].name == "path"
    assert method.parameters[0].annotation == "str"
    assert method.parameters[0].description == "Output path."
    assert property_doc.returns is not None
    assert dataclass_doc.attributes[0].name == "identifier"
    assert dataclass_doc.attributes[0].annotation == "str"
    assert dataclass_doc.attributes[0].description == "Stable record id."


def test_markdown_docstring_parses_raises_table() -> None:
    parsed = parse_docstring(
        """
        Load a widget.

        ## Raises

        | Exception | Description |
        | --- | --- |
        | `ValueError` | If the path is empty. |
        | RuntimeError | If loading fails. |
        """,
        style="markdown",
    )

    assert [(item.exception, item.description) for item in parsed.exceptions] == [
        ("ValueError", "If the path is empty."),
        ("RuntimeError", "If loading fails."),
    ]


def test_markdown_docstring_parses_keyword_argument_sections() -> None:
    parsed = parse_docstring(
        """
        Load a widget.

        ## Parameters

        | Name | Type | Description |
        | --- | --- | --- |
        | path | str | Input path. |

        ## Keyword Arguments

        - `retries` (int): Retry count.
        - `timeout` (float): Timeout in seconds.
        """,
        style="markdown",
    )

    assert [(item.name, item.annotation, item.description) for item in parsed.parameters] == [
        ("path", "str", "Input path."),
        ("retries", "int", "Retry count."),
        ("timeout", "float", "Timeout in seconds."),
    ]


def test_markdown_docstring_parses_plain_parameter_sections() -> None:
    parsed = parse_docstring(
        """
        Load a widget.

        ## Parameters

        path (str): Input path.
            Relative paths are resolved from the repository root.
        retries (int): Retry count.

        ## Other Parameters

        timeout : float
            Timeout in seconds.

        ## Keyword Arguments

        - `verbose` (bool): Whether to print progress.
          The value is only used by CLI callers.
        """,
        style="markdown",
    )

    assert [(item.name, item.annotation, item.description) for item in parsed.parameters] == [
        (
            "path",
            "str",
            "Input path. Relative paths are resolved from the repository root.",
        ),
        ("retries", "int", "Retry count."),
        ("timeout", "float", "Timeout in seconds."),
        ("verbose", "bool", "Whether to print progress. The value is only used by CLI callers."),
    ]
