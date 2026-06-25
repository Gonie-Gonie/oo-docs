from __future__ import annotations

import json
from pathlib import Path
import importlib.util

from oodocs import Chapter, Document
from oodocs.apidoc import (
    ApiCollectConfig,
    ApiDocstringParser,
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
from oodocs.components.blocks import Section
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
"""


def test_docstring_parsers_normalize_standard_styles() -> None:
    google = parse_docstring(GOOGLE_DOCSTRING, style="google")
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
    assert google.renderer_notes[0].format == "pdf"

    assert numpy.parameters[1].name == "retries"
    assert numpy.returns and numpy.returns.documented
    assert sphinx.parameters[0].annotation == "str"
    assert markdown.parameters[0].description == "Input path."
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
    assert isinstance(functions[0].to_parameter_table(), Table)
    assert isinstance(api.to_summary_table(functions), Table)
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

    sidecar = tmp_path / "api.json"
    api.write_json(sidecar)
    assert ApiPackage.read_json(sidecar).find("samplepkg.Widget") is not None


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
            ]
        ),
        encoding="utf-8",
    )
    policy = ApiPublicPolicy.explicit("pkg.Widget", "pkg.Widget._secret")

    api = collect_api(package_dir, public_policy=policy, collector="inspect")

    assert api.metadata["public_policy"] == "explicit"
    assert api.find("pkg.Widget") is not None
    secret = api.find("pkg.Widget._secret")
    assert secret is not None
    assert secret.kind == "method"
    assert api.find("pkg.helper") is None
    assert ApiPublicPolicy.from_dict(policy.to_dict()) == policy


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
        "    return left + right\n",
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
    assert diff.changed_docstrings

    snapshot_path = tmp_path / "snapshot.json"
    ApiSnapshot.from_package(head).write_json(snapshot_path)
    assert json.loads(snapshot_path.read_text(encoding="utf-8"))["name"] == "pkg"


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
