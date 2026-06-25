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


def test_sphinx_parser_degrades_inline_rest_markup_to_plain_text() -> None:
    parsed = parse_docstring(
        """
        Load a :class:`~widgets.Widget`.

        :param path: Input ``path`` for :func:`open_widget`.
        :type path: :class:`str`
        :returns: A `widget label <https://example.test/widget>`_ with *markup*.
        :rtype: :class:`str`
        :raises ValueError: If ``path`` is blank.

        .. note::

            See :mod:`widgets.registry` before calling.

        .. warning::

            Avoid **mutable** defaults.
        """,
        style="sphinx",
    )

    assert parsed.summary == "Load a Widget."
    assert parsed.parameters[0].annotation == "str"
    assert parsed.parameters[0].description == "Input path for open_widget."
    assert parsed.returns is not None
    assert parsed.returns.annotation == "str"
    assert parsed.returns.description == "A widget label with markup."
    assert parsed.raises[0].description == "If path is blank."
    assert parsed.notes == ["See widgets.registry before calling."]
    assert parsed.warnings == ["Avoid mutable defaults."]


def test_sphinx_parser_extracts_seealso_and_renderer_admonitions() -> None:
    parsed = parse_docstring(
        """
        Load a widget.

        :returns: Loaded widget.
        :rtype: :class:`widgets.Widget`

        .. seealso::

            :func:`load_widget`: Load one widget from disk.
            :class:`~widgets.Widget`
                Runtime widget object.

        .. admonition:: Renderer Notes

            PDF: Wide signatures may wrap.
            HTML: :func:`load_widget` receives a stable anchor.
        """,
        style="sphinx",
    )

    assert [item.label for item in parsed.see_also] == ["load_widget", "Widget"]
    assert [item.description for item in parsed.see_also] == [
        "Load one widget from disk.",
        "Runtime widget object.",
    ]
    assert parsed.renderer_notes[0].format == "pdf"
    assert parsed.renderer_notes[0].message == "Wide signatures may wrap."
    assert parsed.renderer_notes[1].format == "html"
    assert parsed.renderer_notes[1].message == "load_widget receives a stable anchor."


def test_sphinx_parser_extracts_keyword_parameters() -> None:
    parsed = parse_docstring(
        """
        Load data.

        :param path: Input path.
        :type path: str
        :keyword retries: Retry count.
        :kwtype retries: int
        :kwarg float timeout: Timeout in seconds.
        :returns: Loaded data.
        :rtype: str
        """,
        style="sphinx",
    )

    assert [(item.name, item.annotation, item.description, item.kind) for item in parsed.parameters] == [
        ("path", "str", "Input path.", None),
        ("retries", "int", "Retry count.", "keyword-only"),
        ("timeout", "float", "Timeout in seconds.", "keyword-only"),
    ]


def test_sphinx_fallback_parser_degrades_inline_rest_markup_to_plain_text(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    parsed = parse_docstring(
        """
        Load a :class:`~widgets.Widget`.

        :param path: Input ``path`` for :func:`open_widget`.
        :type path: :class:`str`
        :returns: A `widget label <https://example.test/widget>`_ with *markup*.
        :rtype: :class:`str`
        :raises ValueError: If ``path`` is blank.
        """,
        style="sphinx",
    )

    assert parsed.summary == "Load a Widget."
    assert parsed.parameters[0].annotation == "str"
    assert parsed.parameters[0].description == "Input path for open_widget."
    assert parsed.returns is not None
    assert parsed.returns.annotation == "str"
    assert parsed.returns.description == "A widget label with markup."
    assert parsed.raises[0].description == "If path is blank."


def test_sphinx_fallback_parser_extracts_seealso_and_renderer_admonitions(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    parsed = parse_docstring(
        """
        Load a widget.

        :returns: Loaded widget.
        :rtype: :class:`widgets.Widget`

        .. seealso::

            :func:`load_widget`: Load one widget from disk.
            :class:`~widgets.Widget`
                Runtime widget object.

        .. admonition:: Renderer Notes

            PDF: Wide signatures may wrap.
            HTML: :func:`load_widget` receives a stable anchor.
        """,
        style="sphinx",
    )

    assert [item.label for item in parsed.see_also] == ["load_widget", "Widget"]
    assert [item.description for item in parsed.see_also] == [
        "Load one widget from disk.",
        "Runtime widget object.",
    ]
    assert parsed.renderer_notes[0].format == "pdf"
    assert parsed.renderer_notes[0].message == "Wide signatures may wrap."
    assert parsed.renderer_notes[1].format == "html"
    assert parsed.renderer_notes[1].message == "load_widget receives a stable anchor."


def test_sphinx_fallback_parser_extracts_keyword_parameters(monkeypatch) -> None:
    monkeypatch.setattr(docstring_module.importlib.util, "find_spec", lambda name: None)

    parsed = parse_docstring(
        """
        Load data.

        :param path: Input path.
        :type path: str
        :keyword retries: Retry count.
        :kwtype retries: int
        :key float timeout: Timeout in seconds.
        :returns: Loaded data.
        :rtype: str
        """,
        style="sphinx",
    )

    assert [(item.name, item.annotation, item.description, item.kind) for item in parsed.parameters] == [
        ("path", "str", "Input path.", None),
        ("retries", "int", "Retry count.", "keyword-only"),
        ("timeout", "float", "Timeout in seconds.", "keyword-only"),
    ]
