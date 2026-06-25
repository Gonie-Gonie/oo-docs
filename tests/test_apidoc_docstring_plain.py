from __future__ import annotations

import inspect

from oodocs.apidoc import parse_docstring
from tests.fixtures.apidoc_docstrings import plain as fixture


def test_plain_docstring_fixture_extracts_only_summary_and_description() -> None:
    parsed = parse_docstring(inspect.getdoc(fixture.load_widget), style="plain")
    class_doc = parse_docstring(inspect.getdoc(fixture.Widget), style="plain")
    method = parse_docstring(inspect.getdoc(fixture.Widget.render), style="plain")
    property_doc = parse_docstring(inspect.getdoc(fixture.Widget.title.fget), style="plain")
    dataclass_doc = parse_docstring(inspect.getdoc(fixture.WidgetRecord), style="plain")

    assert parsed.style == "plain"
    assert parsed.summary == "Load a widget from disk."
    assert parsed.description is not None
    assert not parsed.parameters
    assert not parsed.returns
    assert class_doc.summary == "A plain-style widget."
    assert method.summary == "Render the widget."
    assert property_doc.summary == "Widget title."
    assert dataclass_doc.summary == "Stored widget record."
