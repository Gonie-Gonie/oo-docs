from __future__ import annotations

import json
from pathlib import Path
import importlib.util

from oodocs import Chapter, Document
from oodocs.apidoc import (
    ApiCollectConfig,
    ApiCoverageResult,
    ApiDiffResult,
    ApiDocProfile,
    ApiDocstringParser,
    ApiExample,
    ApiObject,
    ApiPackage,
    ApiPublicPolicy,
    ApiSnapshot,
    ParsedDocstring,
    check_api_docs,
    collect_object_api,
    collect_api,
    detect_docstring_style,
    docstring_parser_names,
    diff_api,
    parse_docstring,
    register_docstring_parser,
)
from oodocs.cli import main
from oodocs.components.blocks import Paragraph, Section
from oodocs.components.inline import Hyperlink
from oodocs.components.media import Table


GOOGLE_DOCSTRING = """Load an object.

Longer details.

Args:
    path (str): Input path.
    retries: Retry count.

Returns:
    bool: Whether loading succeeded.

Raises:
    ValueError: If the path is invalid.

Examples:
    ```python
    load("input.txt")
    ```

See Also:
    open_file: Lower-level file opener.

Notes:
    This loader is safe for generated reference documents.

Warnings:
    Retries should stay low in examples.

Renderer Notes:
    PDF: Long signatures may wrap.

Attributes:
    cache_key (str): Stable cache key used in generated indexes.
"""


NUMPY_DOCSTRING = """Load an object.

Longer details.

Parameters
----------
path : str
    Input path.
retries : int
    Retry count.

Returns
-------
bool
    Whether loading succeeded.

Examples
--------
```python
load("input.txt")
```

Notes
-----
NumPy notes survive parsing.

Warnings
--------
NumPy warnings survive parsing.
"""


SPHINX_DOCSTRING = """Load an object.

:param path: Input path.
:type path: str
:returns: Whether loading succeeded.
:rtype: bool
:raises ValueError: If the path is invalid.

.. code-block:: python

   load("input.txt")
"""


MARKDOWN_DOCSTRING = """Load an object.

## Parameters

| Name | Type | Description |
| --- | --- | --- |
| path | str | Input path. |

## Returns

bool: Whether loading succeeded.

## Examples

```python
load("input.txt")
```

## Notes

Markdown notes survive parsing.

## Warnings

Markdown warnings survive parsing.
"""


def test_docstring_parsers_normalize_standard_styles() -> None:
    google = parse_docstring(GOOGLE_DOCSTRING, style="google")
    google_doctest = parse_docstring(
        """Echo a value.

        Examples:
            >>> echo("ok")
            'ok'
        """,
        style="google",
    )
    numpy = parse_docstring(NUMPY_DOCSTRING, style="numpy")
    sphinx = parse_docstring(SPHINX_DOCSTRING, style="sphinx")
    markdown = parse_docstring(MARKDOWN_DOCSTRING, style="markdown")
    plain = parse_docstring("Short summary.\n\nAdditional paragraph.", style="plain")

    assert google.summary == "Load an object."
    assert google.parameters[0].name == "path"
    assert google.parameters[0].annotation == "str"
    assert google.attributes[0].name == "cache_key"
    assert google.attributes[0].annotation == "str"
    assert google.returns and google.returns.annotation == "bool"
    assert google.raises[0].exception == "ValueError"
    assert google.examples[0].language == "python"
    assert google_doctest.examples[0].language == "pycon"
    assert google.notes == ["This loader is safe for generated reference documents."]
    assert google.warnings == ["Retries should stay low in examples."]
    assert google.renderer_notes[0].format == "pdf"
    mismatch = parse_docstring(GOOGLE_DOCSTRING, style="numpy", qualname="pkg.load", module="pkg")
    assert any(issue.code == "docstring-style-mismatch" for issue in mismatch.issues)

    assert numpy.parameters[1].name == "retries"
    assert numpy.returns and numpy.returns.documented
    assert numpy.notes == ["NumPy notes survive parsing."]
    assert numpy.warnings == ["NumPy warnings survive parsing."]
    assert sphinx.parameters[0].annotation == "str"
    assert markdown.parameters[0].description == "Input path."
    assert markdown.notes == ["Markdown notes survive parsing."]
    assert markdown.warnings == ["Markdown warnings survive parsing."]
    assert plain.description == "Additional paragraph."
    assert detect_docstring_style(GOOGLE_DOCSTRING) == "google"
    assert detect_docstring_style(NUMPY_DOCSTRING) == "numpy"
    assert detect_docstring_style(SPHINX_DOCSTRING) == "sphinx"
    assert detect_docstring_style(MARKDOWN_DOCSTRING) == "markdown"


def test_docstring_parser_backend_enriches_standard_style_metadata() -> None:
    if importlib.util.find_spec("docstring_parser") is None:
        return

    parsed = parse_docstring(
        """Load an object.

        Args:
            path (str, optional): Input path. Defaults to current directory.

        Returns:
            bool: Whether loading succeeded.
        """,
        style="google",
    )

    assert parsed.parameters[0].name == "path"
    assert parsed.parameters[0].annotation == "str"
    assert parsed.parameters[0].required is False
    assert parsed.parameters[0].source == "docstring"
    assert parsed.returns and parsed.returns.annotation == "bool"


def test_reusable_docstring_parser_object_and_custom_registry(tmp_path: Path) -> None:
    parser = ApiDocstringParser.auto()
    parsed = parser.parse(GOOGLE_DOCSTRING, qualname="pkg.load", module="pkg")

    assert parsed.style == "google"
    assert parser.detect(GOOGLE_DOCSTRING) == "google"
    assert ApiDocstringParser.from_dict(parser.to_dict()) == parser

    def parse_brief(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
        return ParsedDocstring(summary=text.strip(), style="brief-test")

    if "brief-test" not in docstring_parser_names():
        register_docstring_parser("brief-test", parse_brief)
    config = ApiCollectConfig(docstring_style=ApiDocstringParser("brief-test"))
    assert config.to_dict()["docstring_style"] == "brief-test"

    package_dir = tmp_path / "briefpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        '"""Brief package."""\n\ndef run() -> None:\n    """Brief function."""\n',
        encoding="utf-8",
    )

    api = collect_api(
        package_dir,
        collector="inspect",
        public_policy="underscore",
        docstring_style=ApiDocstringParser("brief-test"),
    )

    run = api.find("briefpkg.run")
    assert run is not None
    assert run.summary == "Brief function."


def test_collect_api_builds_queryable_object_tree_and_blocks(tmp_path: Path) -> None:
    package_dir = tmp_path / "samplepkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Sample package."""',
                "",
                "__all__ = ['Widget', 'make_widget']",
                "",
                "class Widget:",
                '    """A renderable widget.',
                "",
                "    Args:",
                "        name: Widget name.",
                "",
                "    Attributes:",
                "        label: User-facing label shown in summaries.",
                '    """',
                "    label: str",
                "",
                "    def __init__(self, name: str = 'demo') -> None:",
                "        self.name = name",
                "",
                "    def render(self, path: str) -> str:",
                '        """Render the widget.',
                "",
                "        Args:",
                "            path: Output path.",
                "",
                "        Returns:",
                "            str: Rendered path.",
                '        """',
                "        return path",
                "",
                "def make_widget(name: str) -> Widget:",
                '    """Create a widget.',
                "",
                "    Args:",
                "        name: Widget name.",
                "",
                "    Returns:",
                "        Widget: Created widget.",
                "",
                "    Examples:",
                "        ```python",
                "        make_widget('demo')",
                "        ```",
                "",
                "    Notes:",
                "        Use this helper when API docs need a factory example.",
                "",
                "    Warnings:",
                "        Do not pass user-facing secrets as names.",
                '    """',
                "    return Widget(name)",
            ]
        ),
        encoding="utf-8",
    )

    api = collect_api(package_dir, public_policy="__all__", collector="auto")
    classes = api.select(kind="class")
    functions = api.select(kind="function")

    assert isinstance(api, ApiPackage)
    assert [obj.qualname for obj in classes] == ["samplepkg.Widget"]
    assert [obj.qualname for obj in functions] == ["samplepkg.make_widget"]
    assert api.find("samplepkg.Widget") is classes[0]
    assert classes[0].select(kind="method")[0].name == "render"
    label = classes[0].find("label")
    assert label is not None
    assert label.summary == "User-facing label shown in summaries."
    assert isinstance(classes[0].to_section(level=2, profile="compact"), Section)
    review_blocks = classes[0].to_blocks(profile="review")
    review_notes = [
        block
        for block in review_blocks
        if isinstance(block, Paragraph) and "Review note[?]" in block.plain_text()
    ]
    assert review_notes
    assert "Review note[?]" in review_notes[0].plain_text()
    assert ApiDocProfile.from_dict(ApiDocProfile.review().to_dict()).include_review_notes
    assert isinstance(functions[0].to_parameter_table(), Table)
    assert functions[0].notes == ["Use this helper when API docs need a factory example."]
    assert functions[0].warnings == ["Do not pass user-facing secrets as names."]
    assert any("Use this helper" in block.plain_text() for block in functions[0].to_notes_blocks())
    warning_blocks = functions[0].to_warnings_blocks()
    assert warning_blocks
    warning_text = " ".join(
        child.plain_text()
        for block in warning_blocks
        for child in getattr(block, "children", [])
        if hasattr(child, "plain_text")
    )
    assert "Do not pass" in warning_text
    assert ApiObject.from_dict(functions[0].to_dict()).warnings == functions[0].warnings
    assert isinstance(api.to_summary_table(functions), Table)
    website_table = api.to_summary_table(classes, profile="website")
    website_name = website_table.rows[0][2].content.content[0]
    assert isinstance(website_name, Hyperlink)
    assert website_name.internal
    assert website_name.target == classes[0].anchor_id()
    website_section = classes[0].to_section(level=2, profile="website")
    assert website_section.anchor == website_name.target
    filtered = api.filtered(kind="class", module_prefix="samplepkg")
    assert [obj.qualname for obj in filtered.public_objects() if obj.kind == "class"] == ["samplepkg.Widget"]
    assert filtered.metadata["filters"]["kind"] == ["class"]

    document = Document(
        "Demo",
        Chapter("API", *[obj.to_section(level=2) for obj in classes]),
    )
    assert document.validate(formats=("html",)).ok
    html_path = tmp_path / "api.html"
    document.save_html(html_path)
    assert html_path.exists()
    website_doc = Document(
        "Website API",
        Chapter(
            "Index",
            api.to_summary_table(classes, profile="website"),
            website_section,
        ),
    )
    website_path = tmp_path / "website-api.html"
    website_doc.save_html(website_path)
    website_html = website_path.read_text(encoding="utf-8")
    assert f'id="{classes[0].anchor_id()}"' in website_html
    assert f'href="#{classes[0].anchor_id()}"' in website_html

    sidecar = tmp_path / "api.json"
    api.write_json(sidecar)
    assert ApiPackage.read_json(sidecar).find("samplepkg.Widget") is not None


def test_api_doc_profiles_wrap_long_signature_blocks() -> None:
    obj = ApiObject(
        kind="function",
        name="build_report",
        qualname="pkg.build_report",
        module="pkg",
        signature=(
            "pkg.build_report(path: str, *, retries: int = 3, "
            "metadata: dict[str, object] | None = None) -> dict[str, object]"
        ),
    )

    reference = obj.to_signature_block(profile="reference")
    compact = obj.to_signature_block(profile=ApiDocProfile.compact())

    assert reference is not None
    assert compact is not None
    assert "\n" not in reference.code
    assert compact.code.splitlines() == [
        "pkg.build_report(",
        "    path: str,",
        "    *,",
        "    retries: int = 3,",
        "    metadata: dict[str, object] | None = None",
        ") -> dict[str, object]",
    ]
    assert ApiDocProfile.from_dict(ApiDocProfile.compact().to_dict()).max_signature_width == 88
    assert ApiDocProfile.from_dict(ApiDocProfile.compact().to_dict()).max_signature_lines == 24

    long_signature = ApiObject(
        kind="function",
        name="many",
        qualname="pkg.many",
        module="pkg",
        signature="pkg.many(" + ", ".join(f"value_{index}: str" for index in range(40)) + ")",
    )
    truncated = long_signature.to_signature_block(profile=ApiDocProfile.compact())
    assert truncated is not None
    assert len(truncated.code.splitlines()) == 24
    assert truncated.code.splitlines()[-1] == "..."


def test_api_examples_escape_xml_incompatible_control_chars(tmp_path: Path) -> None:
    example = ApiExample('fragment = math(r"\x07lpha + \x08eta")')
    block = example.to_block()

    assert "\\x07" in block.code
    assert "\\x08" in block.code
    assert "\x07" not in block.code
    assert "\x08" not in block.code
    Document("Example", Chapter("Snippet", block)).save_docx(tmp_path / "example.docx")


def test_collect_api_exposes_docstring_parser_issues_in_issue_table(tmp_path: Path) -> None:
    package_dir = tmp_path / "stylepkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "def load(path: str) -> str:\n"
        '    """Load a path.\n\n'
        "    Args:\n"
        "        path: Input path.\n"
        "    Returns:\n"
        "        str: Loaded path.\n"
        '    """\n'
        "    return path\n",
        encoding="utf-8",
    )

    api = collect_api(package_dir, public_policy="underscore", docstring_style="numpy")
    issues = list(api.iter_issues())

    assert any(issue.code == "docstring-style-mismatch" for issue in issues)
    issue_table = api.to_issue_table()
    assert any(
        row[1].content.plain_text() == "docstring-style-mismatch"
        for row in issue_table.rows
    )


def test_collect_api_supports_src_layout_repo_reexports_and_deep_object_lookup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    package_dir = repo / "src" / "widgetlib"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "[project]\nname = \"widget-lib\"\n",
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Widget library."""',
                "from .core import Widget, make_widget",
                "",
                "__all__ = ['Widget', 'make_widget']",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        "\n".join(
            [
                '"""Core widget APIs."""',
                "",
                "class Widget:",
                '    """A widget.',
                "",
                "    Args:",
                "        name: Widget name.",
                '    """',
                "    def __init__(self, name: str) -> None:",
                "        self.name = name",
                "",
                "    def render(self, path: str) -> str:",
                '        """Render the widget.',
                "",
                "        Args:",
                "            path: Output path.",
                "        Returns:",
                "            str: Rendered path.",
                '        """',
                "        return path",
                "",
                "def make_widget(name: str) -> Widget:",
                '    """Create a widget.',
                "",
                "    Args:",
                "        name: Widget name.",
                "    Returns:",
                "        Widget: Created widget.",
                '    """',
                "    return Widget(name)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(repo / "src"))

    api = collect_api(repo, public_policy="__all__", collector="inspect")

    assert api.name == "widgetlib"
    assert {module.name for module in api.modules} == {"widgetlib", "widgetlib.core"}
    assert api.find("widgetlib.Widget") is not None
    assert api.find("widgetlib.core.Widget.render") is not None
    assert [obj.qualname for obj in api.select(kind="class", module="widgetlib")] == [
        "widgetlib.Widget"
    ]

    looked_up = collect_object_api(
        "widgetlib.core.Widget.render",
        public_policy="underscore",
        collector="inspect",
    )
    assert looked_up.kind == "method"
    assert looked_up.parameters[0].name == "path"


def test_collect_api_accepts_reusable_public_policy_object(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Policy package."""',
                "",
                "class Widget:",
                '    """A widget."""',
                "",
                "    def _secret(self) -> str:",
                '        """Return internal detail for curated docs."""',
                "        return 'ok'",
                "",
                "def helper() -> None:",
                '    """Not part of the curated API."""',
                "",
                "from .core import Extra",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        "\n".join(
            [
                "class Extra:",
                '    """A target object included without its package alias."""',
            ]
        ),
        encoding="utf-8",
    )
    policy = ApiPublicPolicy.explicit("pkg.Widget", "pkg.Widget._secret", "pkg.core.Extra")

    api = collect_api(package_dir, public_policy=policy, collector="inspect")

    assert api.metadata["public_policy"] == "explicit"
    assert api.find("pkg.Widget") is not None
    secret = api.find("pkg.Widget._secret")
    assert secret is not None
    assert secret.kind == "method"
    assert api.find("pkg.core.Extra") is not None
    assert api.find("pkg.Extra") is None
    assert api.find("pkg.helper") is None
    assert ApiPublicPolicy.from_dict(policy.to_dict()) == policy


def test_source_collector_can_include_external_import_aliases(tmp_path: Path) -> None:
    package_dir = tmp_path / "importpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Import boundary package."""',
                "from pathlib import Path",
                "import json as json_module",
                "from .core import Widget",
                "",
                "__all__ = ['Path', 'json_module', 'Widget']",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        "\n".join(
            [
                "class Widget:",
                '    """A documented widget."""',
            ]
        ),
        encoding="utf-8",
    )

    default_api = collect_api(package_dir, public_policy="__all__", collector="inspect")
    imported_api = collect_api(
        package_dir,
        public_policy="__all__",
        collector="inspect",
        include_imported=True,
    )

    assert default_api.find("importpkg.Widget") is not None
    assert default_api.find("importpkg.Path") is None
    assert default_api.find("importpkg.json_module") is None

    widget = imported_api.find("importpkg.Widget")
    path_alias = imported_api.find("importpkg.Path")
    json_alias = imported_api.find("importpkg.json_module")

    assert widget is not None
    assert widget.kind == "class"
    assert widget.metadata["reexported_from"] == "importpkg.core.Widget"
    assert path_alias is not None
    assert path_alias.kind == "data"
    assert path_alias.metadata["imported"] is True
    assert path_alias.metadata["imported_from"] == "pathlib.Path"
    assert json_alias is not None
    assert json_alias.metadata["imported_from"] == "json"

    cli_json = tmp_path / "imported-api.json"
    assert main(
        [
            "apidoc",
            "collect",
            str(package_dir),
            "--collector",
            "inspect",
            "--include-imported",
            "--out",
            str(cli_json),
        ]
    ) == 0
    cli_api = ApiPackage.read_json(cli_json)
    assert cli_api.find("importpkg.Path") is not None


def test_collect_api_filters_modules_before_collection(tmp_path: Path) -> None:
    package_dir = tmp_path / "filtermods"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text('"""Filter mods."""\n', encoding="utf-8")
    (package_dir / "core.py").write_text(
        '"""Core module."""\n'
        "\n"
        "def run() -> None:\n"
        '    """Run the core workflow."""\n',
        encoding="utf-8",
    )
    (package_dir / "experimental.py").write_text(
        '"""Experimental module."""\n'
        "\n"
        "def preview() -> None:\n"
        '    """Preview an experimental workflow."""\n',
        encoding="utf-8",
    )
    (package_dir / "tests.py").write_text(
        '"""Test helper module."""\n'
        "\n"
        "def helper() -> None:\n"
        '    """Help tests."""\n',
        encoding="utf-8",
    )
    config = ApiCollectConfig.from_kwargs(
        module_include_patterns=("filtermods.*",),
        module_exclude_patterns=("filtermods.tests", "filtermods.experimental"),
    )

    api = collect_api(package_dir, config=config, public_policy="underscore", collector="inspect")

    assert api.metadata["file_count"] == 1
    assert [module.name for module in api.modules] == ["filtermods.core"]
    assert api.find("filtermods.core.run") is not None
    assert api.find("filtermods.experimental.preview") is None
    assert api.find("filtermods.tests.helper") is None
    assert config.to_dict()["module_include_patterns"] == ["filtermods.*"]

    if importlib.util.find_spec("griffe") is not None:
        griffe_api = collect_api(
            package_dir,
            public_policy="underscore",
            collector="griffe",
            module_include_patterns=("filtermods.*",),
            module_exclude_patterns=("filtermods.tests", "filtermods.experimental"),
        )
        assert griffe_api.metadata["file_count"] == 1
        assert [module.name for module in griffe_api.modules] == ["filtermods.core"]


def test_griffe_collector_matches_inspect_schema_on_src_layout_repo(
    tmp_path: Path,
) -> None:
    if importlib.util.find_spec("griffe") is None:
        return
    repo = tmp_path / "repo"
    package_dir = repo / "src" / "pkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = \"pkg\"\n", encoding="utf-8")
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Package docs."""',
                "from .core import Widget, make_widget",
                "__all__ = ['Widget', 'make_widget']",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        "\n".join(
            [
                '"""Core docs."""',
                "",
                "class Widget:",
                '    """A widget.',
                "",
                "    Args:",
                "        name: Widget name.",
                "    Attributes:",
                "        label: User-facing label.",
                '    """',
                "    label: str",
                "    def __init__(self, name: str = 'demo') -> None:",
                "        self.name = name",
                "",
                "    @property",
                "    def title(self) -> str:",
                '        """Widget title."""',
                "        return self.name",
                "",
                "    def render(self, path: str) -> str:",
                '        """Render the widget.',
                "",
                "        Args:",
                "            path: Output path.",
                "        Returns:",
                "            str: Rendered path.",
                '        """',
                "        return path",
                "",
                "def make_widget(name: str) -> Widget:",
                '    """Create a widget.',
                "",
                "    Args:",
                "        name: Widget name.",
                "    Returns:",
                "        Widget: Created widget.",
                '    """',
                "    return Widget(name)",
            ]
        ),
        encoding="utf-8",
    )

    inspect_api = collect_api(repo, public_policy="__all__", collector="inspect")
    griffe_api = collect_api(repo, public_policy="__all__", collector="griffe")

    assert griffe_api.metadata["collector"] == "griffe"
    assert len(griffe_api.public_objects()) >= len(inspect_api.public_objects())
    assert griffe_api.find("pkg.Widget") is not None
    assert griffe_api.find("pkg.core.Widget.render") is not None
    property_obj = griffe_api.find("pkg.core.Widget.title")
    assert property_obj is not None
    assert getattr(property_obj, "kind") == "property"
    label_obj = griffe_api.find("pkg.core.Widget.label")
    assert label_obj is not None
    assert label_obj.summary == "User-facing label."
    method = griffe_api.find("pkg.core.Widget.render")
    assert method is not None
    assert method.parameters[0].name == "path"
    assert method.returns and method.returns.annotation == "str"


def test_collectors_detect_deprecated_decorators_and_warning_bodies(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "deppkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                "import warnings",
                "",
                "def deprecated(value):",
                "    return value",
                "",
                "@deprecated",
                "class OldWidget:",
                '    """Old widget."""',
                "",
                "def old_run() -> None:",
                '    """Run the old workflow."""',
                "    warnings.warn(",
                "        'Use new_run instead.',",
                "        DeprecationWarning,",
                "        stacklevel=2,",
                "    )",
                "",
                "def keyword_old() -> None:",
                '    """Run the keyword old workflow."""',
                "    warnings.warn(",
                "        'Use keyword_new instead.',",
                "        category=DeprecationWarning,",
                "    )",
            ]
        ),
        encoding="utf-8",
    )

    inspect_api = collect_api(package_dir, public_policy="underscore", collector="inspect")
    old_class = inspect_api.find("deppkg.OldWidget")
    old_run = inspect_api.find("deppkg.old_run")
    keyword_old = inspect_api.find("deppkg.keyword_old")

    assert old_class is not None and old_class.deprecated
    assert old_run is not None and old_run.deprecated
    assert old_run.deprecation_message == "Use new_run instead."
    assert keyword_old is not None and keyword_old.deprecated
    assert keyword_old.deprecation_message == "Use keyword_new instead."

    if importlib.util.find_spec("griffe") is not None:
        griffe_api = collect_api(package_dir, public_policy="underscore", collector="griffe")
        assert griffe_api.find("deppkg.OldWidget").deprecated
        assert griffe_api.find("deppkg.old_run").deprecated
        assert griffe_api.find("deppkg.old_run").deprecation_message == "Use new_run instead."


def test_api_coverage_and_diff_detect_doc_changes(tmp_path: Path) -> None:
    base_dir = tmp_path / "base" / "pkg"
    head_dir = tmp_path / "head" / "pkg"
    base_dir.mkdir(parents=True)
    head_dir.mkdir(parents=True)
    (base_dir / "__init__.py").write_text(
        "def add(left: int, right: int) -> int:\n"
        '    """Add values.\n\n'
        "    Args:\n"
        "        left: Left value.\n"
        '    """\n'
        "    return left + right\n"
        "\n"
        "def cast(value: int) -> str:\n"
        '    """Cast a value.\n\n'
        "    Args:\n"
        "        value: Value to cast.\n"
        "    Returns:\n"
        "        str: Cast value.\n"
        '    """\n'
        "    return str(value)\n",
        encoding="utf-8",
    )
    (head_dir / "__init__.py").write_text(
        "def add(left: int, right: int = 0) -> int:\n"
        '    """Add two values.\n\n'
        "    Args:\n"
        "        left: Left value.\n"
        "        right: Right value.\n"
        "    Returns:\n"
        "        int: Sum.\n"
        '    """\n'
        "    return left + right\n"
        "\n"
        "def cast(value: str) -> bytes:\n"
        '    """Cast a value.\n\n'
        "    Args:\n"
        "        value: Value to cast.\n"
        "    Returns:\n"
        "        bytes: Cast value.\n"
        '    """\n'
        "    return value.encode()\n"
        "\n"
        'def subtract(left: int, right: int) -> int:\n    """Subtract values."""\n    return left - right\n',
        encoding="utf-8",
    )

    base = collect_api(base_dir, public_policy="underscore")
    head = collect_api(head_dir, public_policy="underscore")
    coverage = check_api_docs(base)
    diff = diff_api(base, head)

    assert any(issue.code == "missing-parameter-doc" for issue in coverage.issues)
    assert diff.added
    assert diff.changed_signatures
    assert diff.changed_defaults
    assert diff.changed_parameter_annotations
    assert diff.changed_return_annotations
    assert diff.changed_docstrings
    assert diff.coverage_delta["base_public_object_count"] > 0
    assert diff.coverage_delta["head_public_object_count"] > 0
    assert "object_coverage_delta" in diff.coverage_delta

    snapshot_path = tmp_path / "snapshot.json"
    ApiSnapshot.from_package(head).write_json(snapshot_path)
    assert json.loads(snapshot_path.read_text(encoding="utf-8"))["name"] == "pkg"
    snapshot_diff = diff_api(ApiSnapshot.from_package(base), ApiSnapshot.from_package(head))
    assert snapshot_diff.coverage_delta == diff.coverage_delta

    coverage_path = tmp_path / "coverage.json"
    coverage.write_json(coverage_path)
    coverage_readback = ApiCoverageResult.read_json(coverage_path)
    assert coverage_readback.to_dict() == coverage.to_dict()
    assert isinstance(coverage_readback.to_table(), Table)

    diff_path = tmp_path / "diff.json"
    diff.write_json(diff_path)
    diff_readback = ApiDiffResult.read_json(diff_path)
    assert diff_readback.to_dict() == diff.to_dict()
    assert diff_readback.changed_parameter_annotations
    assert diff_readback.changed_return_annotations
    assert isinstance(diff_readback.to_summary_table(), Table)


def test_api_coverage_counts_doctest_examples(tmp_path: Path) -> None:
    package_dir = tmp_path / "doctestpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "def echo(value: str) -> str:\n"
        '    """Echo a value.\n\n'
        "    Args:\n"
        "        value: Value to echo.\n"
        "    Returns:\n"
        "        str: Echoed value.\n\n"
        "    Examples:\n"
        "        >>> echo('ok')\n"
        "        'ok'\n"
        '    """\n'
        "    return value\n",
        encoding="utf-8",
    )

    api = collect_api(package_dir, public_policy="underscore")
    coverage = check_api_docs(api)

    assert coverage.example_count == 1
    assert coverage.syntax_checked_example_count == 1
    assert coverage.syntax_ok_example_count == 1
    assert coverage.doctest_checked_example_count == 1
    assert coverage.doctest_ok_example_count == 1
    assert coverage.to_dict()["doctest_ok_example_count"] == 1
    assert any(
        row[0].content.plain_text() == "Doctest-valid examples"
        for row in coverage.to_table().rows
    )


def test_apidoc_cli_collect_check_build_snapshot_and_diff(tmp_path: Path, capsys) -> None:
    package_dir = tmp_path / "clipkg"
    package_dir.mkdir()
    source = (
        '"""CLI package."""\n'
        "def run(path: str) -> str:\n"
        '    """Run a task.\n\n'
        "    Args:\n"
        "        path: Input path.\n"
        "    Returns:\n"
        "        str: Input path.\n"
        '    """\n'
        "    return path\n"
    )
    (package_dir / "__init__.py").write_text(source, encoding="utf-8")
    api_json = tmp_path / "api.json"
    snapshot_json = tmp_path / "snapshot.json"
    build_dir = tmp_path / "build"
    diff_dir = tmp_path / "diff"

    assert main(["apidoc", "collect", str(package_dir), "--out", str(api_json)]) == 0
    assert api_json.exists()
    assert main(["apidoc", "check", str(package_dir)]) == 0
    assert main(["apidoc", "build", str(package_dir), "--out", str(build_dir), "--to", "html"]) == 0
    assert any(path.suffix == ".html" for path in build_dir.iterdir())
    assert main(["apidoc", "snapshot", str(package_dir), "--out", str(snapshot_json)]) == 0
    assert snapshot_json.exists()
    assert main(
        [
            "apidoc",
            "diff",
            "--base",
            str(snapshot_json),
            "--head",
            str(snapshot_json),
            "--out",
            str(diff_dir),
            "--to",
            "html",
        ]
    ) == 0
    assert (diff_dir / "api-diff.html").exists()

    captured = capsys.readouterr()
    assert "Wrote api-json" in captured.out


def test_apidoc_cli_filters_check_and_snapshot(tmp_path: Path) -> None:
    package_dir = tmp_path / "filterpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text('"""Filtered package."""\n', encoding="utf-8")
    (package_dir / "core.py").write_text(
        "def run(path: str) -> str:\n"
        '    """Run a task.\n\n'
        "    Args:\n"
        "        path: Input path.\n"
        "    Returns:\n"
        "        str: Input path.\n"
        '    """\n'
        "    return path\n",
        encoding="utf-8",
    )
    (package_dir / "legacy.py").write_text(
        "class Legacy:\n"
        "    pass\n",
        encoding="utf-8",
    )
    snapshot_json = tmp_path / "filtered-snapshot.json"
    build_dir = tmp_path / "filtered-build"

    assert main(
        [
            "apidoc",
            "check",
            str(package_dir),
            "--kind",
            "function",
            "--module-prefix",
            "filterpkg.core",
            "--fail-under",
            "1.0",
        ]
    ) == 0
    assert main(
        [
            "apidoc",
            "snapshot",
            str(package_dir),
            "--kind",
            "function",
            "--module-prefix",
            "filterpkg.core",
            "--out",
            str(snapshot_json),
        ]
    ) == 0

    snapshot = json.loads(snapshot_json.read_text(encoding="utf-8"))
    assert list(snapshot["objects"]) == ["filterpkg.core.run"]

    collected_json = tmp_path / "module-filtered-api.json"
    assert main(
        [
            "apidoc",
            "collect",
            str(package_dir),
            "--module-include",
            "filterpkg.core",
            "--module-exclude",
            "filterpkg.legacy",
            "--out",
            str(collected_json),
        ]
    ) == 0
    collected = json.loads(collected_json.read_text(encoding="utf-8"))
    assert [module["name"] for module in collected["modules"]] == ["filterpkg.core"]

    assert main(
        [
            "apidoc",
            "build",
            str(package_dir),
            "--kind",
            "function",
            "--module-prefix",
            "filterpkg.core",
            "--profile",
            "website",
            "--out",
            str(build_dir),
            "--to",
            "html",
        ]
    ) == 0
    html = (build_dir / "filterpkg-api.html").read_text(encoding="utf-8")
    assert 'href="#filterpkg-core-run"' in html
    assert 'id="filterpkg-core-run"' in html


def test_api_objects_example_builds_full_reference_and_composable_document(
    tmp_path: Path,
) -> None:
    module_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "api_objects_example"
        / "main.py"
    )
    spec = importlib.util.spec_from_file_location("api_objects_example_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)

    package_dir = tmp_path / "examplepkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "class Widget:\n"
        '    """A documented widget."""\n'
        "\n"
        "def run(path: str) -> str:\n"
        '    """Run a task.\n\n'
        "    Args:\n"
        "        path: Input path.\n"
        "    Returns:\n"
        "        str: Input path.\n"
        '    """\n'
        "    return path\n",
        encoding="utf-8",
    )

    api = collect_api(package_dir, public_policy="underscore")
    coverage = check_api_docs(api)
    full_reference = example.build_full_package_document(api)
    composition = example.build_document(api, coverage)

    outputs = full_reference.save_all(tmp_path, stem="full-reference")

    assert set(outputs) == {"docx", "pdf", "html"}
    assert all(path.exists() for path in outputs.values())
    assert full_reference.validate(formats=("docx", "pdf", "html")).ok
    assert composition.validate(formats=("html",)).ok
    html = outputs["html"].read_text(encoding="utf-8")
    assert "examplepkg.Widget" in html
    assert "examplepkg.run" in html
    assert any(
        getattr(child.title[0], "value", "") == "Selected Classes"
        for child in composition.body.children
        if hasattr(child, "title")
    )
