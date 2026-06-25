from __future__ import annotations

import inspect

import oodocs.apidoc.docstring as docstring_module
from oodocs.apidoc import parse_docstring
from tests.fixtures.apidoc_docstrings import sphinx as fixture


def test_sphinx_docstring_fixture_extracts_shared_fields() -> None:
    function = parse_docstring(inspect.getdoc(fixture.load_widget), style="sphinx")
    class_doc = parse_docstring(inspect.getdoc(fixture.Widget), style="sphinx")
    method = parse_docstring(inspect.getdoc(fixture.Widget.render), style="sphinx")
    property_doc = parse_docstring(inspect.getdoc(fixture.Widget.title.fget), style="sphinx")
    dataclass_doc = parse_docstring(inspect.getdoc(fixture.WidgetRecord), style="sphinx")

    assert function.style == "sphinx"
    assert function.parameters[0].annotation == "str"
    assert function.returns is not None
    assert function.raises[0].exception == "ValueError"
    assert function.examples
    assert function.notes
    assert function.warnings
    assert function.deprecated
    assert class_doc.parameters[0].name == "name"
    assert class_doc.attributes[0].name == "label"
    assert method.parameters[0].name == "path"
    assert property_doc.returns is not None
    assert dataclass_doc.attributes[0].name == "identifier"


def test_sphinx_fallback_parser_preserves_multiline_field_bodies(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    parsed = parse_docstring(
        """
        Load a widget.

        :param str path: Input path.
            Relative paths are resolved from the repository root.
        :returns: Loaded widget name.
            Empty paths return a default widget.
        :rtype: str
        :raises ValueError: If the path is invalid.
            The path is included in the exception message.

        .. note::

            Used by fallback parser regression tests.

        .. code-block:: python

            load_widget("widget.json")
        """,
        style="sphinx",
    )

    assert parsed.summary == "Load a widget."
    assert parsed.description is None
    assert parsed.parameters[0].name == "path"
    assert parsed.parameters[0].annotation == "str"
    assert parsed.parameters[0].description == (
        "Input path. Relative paths are resolved from the repository root."
    )
    assert parsed.returns is not None
    assert parsed.returns.annotation == "str"
    assert parsed.returns.description == (
        "Loaded widget name. Empty paths return a default widget."
    )
    assert parsed.raises[0].description == (
        "If the path is invalid. The path is included in the exception message."
    )
    assert parsed.notes == ["Used by fallback parser regression tests."]
    assert parsed.examples[0].code == 'load_widget("widget.json")'
