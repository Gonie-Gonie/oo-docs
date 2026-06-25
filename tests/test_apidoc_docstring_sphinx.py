from __future__ import annotations

import inspect

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
