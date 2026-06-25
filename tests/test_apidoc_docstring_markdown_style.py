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
    assert function.returns is not None
    assert function.examples
    assert function.notes
    assert function.renderer_notes[0].format == "html"
    assert class_doc.parameters[0].name == "name"
    assert class_doc.attributes[0].name == "label"
    assert method.parameters[0].name == "path"
    assert property_doc.returns is not None
    assert dataclass_doc.attributes[0].name == "identifier"
