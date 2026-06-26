from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from example_regression import (
    assert_docx_structure,
    assert_html_internal_links_resolve,
    assert_pdf_text_and_pages,
    assert_rendered_bundle,
)
from oodocs import Chapter, Document
from oodocs.apidoc import (
    ApiBuildConfig,
    ApiCollectConfig,
    ApiCoverageResult,
    ApiDiffResult,
    ApiPresentationProfile,
    ApiDocstringParser,
    ApiExample,
    ApiObject,
    ApiPackage,
    ApiPublicPolicy,
    ApiSnapshot,
    ParsedDocstring,
    check_api_docs,
    collect_module_api,
    collect_object_api,
    collect_api,
    detect_docstring_style,
    docstring_parser_names,
    diff_api,
    extract_code_blocks_from_docstring,
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
    assert google.exceptions[0].exception == "ValueError"
    assert google.examples[0].language == "python"
    assert google_doctest.examples[0].language == "pycon"
    assert google.notes == ["This loader is safe for generated reference documents."]
    assert google.warnings == ["Retries should stay low in examples."]
    assert google.renderer_notes[0].output_format == "pdf"
    mismatch = parse_docstring(GOOGLE_DOCSTRING, style="numpy", qualname="pkg.load", module="pkg")
    assert any(issue.code == "docstring-style-mismatch" for issue in mismatch.issues)
    assert ParsedDocstring.from_dict(google.to_dict()).to_dict() == google.to_dict()
    assert ParsedDocstring.from_dict(mismatch.to_dict()).to_dict() == mismatch.to_dict()

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


def test_docstring_parsers_normalize_yields_sections() -> None:
    google = parse_docstring(
        """Iterate values.

        Yields:
            str: Next value.
        """,
        style="google",
    )
    numpy = parse_docstring(
        """Iterate values.

        Yields
        ------
        str
            Next value.
        """,
        style="numpy",
    )
    sphinx = parse_docstring(
        """Iterate values.

        :yields: Next value.
        :ytype: str
        """,
        style="sphinx",
    )
    markdown = parse_docstring(
        """Iterate values.

        ## Yields

        str: Next value.
        """,
        style="markdown",
    )

    for parsed in (google, numpy, sphinx, markdown):
        assert parsed.returns is not None
        assert parsed.returns.annotation == "str"
        assert parsed.returns.description == "Next value."
        assert parsed.returns.documented

    assert detect_docstring_style(":yields: Next value.\n:ytype: str") == "sphinx"


def test_example_extraction_does_not_duplicate_fenced_doctest_blocks() -> None:
    fenced_pycon = extract_code_blocks_from_docstring(
        """Run an interactive example.

        ```pycon
        >>> echo("ok")
        'ok'
        ```
        """
    )
    mixed = extract_code_blocks_from_docstring(
        """Show both fenced and plain doctest examples.

        ```python
        echo("ok")
        ```

        >>> echo("again")
        'again'
        """
    )

    assert [example.language for example in fenced_pycon] == ["pycon"]
    assert [example.language for example in mixed] == ["python", "pycon"]


def test_example_extraction_preserves_multiple_case_captions() -> None:
    examples = extract_code_blocks_from_docstring(
        """Show common usage cases.

        Examples:
            Basic file:
                ```python
                load("basic.json")
                ```

            Retry session:
                >>> load("retry.json", retries=2)
                'ok'

            Alternate session:
                >>> load("alternate.json")
                'ok'
        """
    )

    assert [example.language for example in examples] == ["python", "pycon", "pycon"]
    assert [example.caption for example in examples] == [
        "Basic file",
        "Retry session",
        "Alternate session",
    ]
    assert examples[0].code == 'load("basic.json")'
    assert 'load("retry.json", retries=2)' in examples[1].code
    assert 'load("alternate.json")' in examples[2].code


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
    called = ApiDocstringParser.google()(
        "Run.\n\nArgs:\n    path: Input path.",
        qualname="pkg.run",
        module="pkg",
    )

    assert parsed.style == "google"
    assert called.style == "google"
    assert called.parameters[0].name == "path"
    assert parser.detect(GOOGLE_DOCSTRING) == "google"
    assert ApiDocstringParser.from_dict(parser.to_dict()) == parser

    def parse_brief(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
        return ParsedDocstring(summary=text.strip(), style="brief-test")

    if "brief-test" not in docstring_parser_names():
        register_docstring_parser("brief-test", parse_brief)
    config = ApiCollectConfig(docstring_style=ApiDocstringParser("brief-test"))
    assert config.to_dict()["docstring_style"] == "brief-test"
    custom_parser = ApiDocstringParser("brief-test")
    assert custom_parser.detect("Brief summary.") == "brief-test"
    assert custom_parser("Brief summary.").style == "brief-test"

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


def test_apidoc_cli_loads_custom_docstring_parser_modules_from_pyproject(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    package_dir = repo / "src" / "hookpkg"
    package_dir.mkdir(parents=True)
    (repo / "repo_apidoc_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_repo_style(text, qualname=None, module=None):",
                '    return ParsedDocstring(summary=f"custom:{text.strip()}", style="repo-brief-cli")',
                "",
                'if "repo-brief-cli" not in docstring_parser_names():',
                '    register_docstring_parser("repo-brief-cli", parse_repo_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "hookpkg"',
                "",
                "[tool.oodocs.apidoc]",
                'collector = "inspect"',
                'public-policy = "underscore"',
                'docstring-style = "repo-brief-cli"',
                'docstring-parser-modules = ["repo_apidoc_parsers"]',
                'profile = "compact"',
                'formats = ["html"]',
                'out = "artifacts/api"',
                "sidecars = true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Hook package."""',
                "",
                "def run() -> None:",
                '    """Run command."""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)
    monkeypatch.syspath_prepend(str(repo))

    assert main(["apidoc", "build", ".", "--config", "pyproject.toml"]) == 0
    config = ApiBuildConfig.from_pyproject(repo)
    built_api = ApiPackage.read_json(repo / "artifacts" / "api" / "hookpkg-api.json")
    run = built_api.find("hookpkg.run")

    assert config.collection.docstring_parser_modules == ("repo_apidoc_parsers",)
    assert run is not None
    assert run.summary == "custom:Run command."
    assert (repo / "artifacts" / "api" / "hookpkg-api-coverage.json").exists()


def test_apidoc_cli_loads_pyproject_parser_modules_from_target_repo_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "external-repo"
    package_dir = repo / "src" / "externalhookpkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""External hook package."""',
                "",
                "def run() -> None:",
                '    """Run external command."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "docs_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_external_style(text, qualname=None, module=None):",
                '    return ParsedDocstring(summary=f"external:{text.strip()}", style="external-brief-cli")',
                "",
                'if "external-brief-cli" not in docstring_parser_names():',
                '    register_docstring_parser("external-brief-cli", parse_external_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "externalhookpkg"',
                "",
                "[tool.oodocs.apidoc]",
                'collector = "inspect"',
                'public-policy = "underscore"',
                'docstring-style = "external-brief-cli"',
                'docstring-parser-modules = ["externalhookpkg.docs_parsers"]',
                'profile = "compact"',
                'formats = ["html"]',
                "sidecars = true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = repo / "artifacts" / "api"

    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "apidoc",
                "build",
                str(repo),
                "--config",
                str(repo / "pyproject.toml"),
                "--out",
                str(output_dir),
            ]
        )
        == 0
    )
    built_api = ApiPackage.read_json(output_dir / "externalhookpkg-api.json")
    run = built_api.find("externalhookpkg.run")

    assert run is not None
    assert run.summary == "external:Run external command."
    assert (output_dir / "externalhookpkg-api-coverage.json").exists()


def test_collect_api_builds_queryable_object_tree_and_blocks(tmp_path: Path) -> None:
    package_dir = tmp_path / "samplepkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Sample package.',
                "",
                "Notes:",
                "    Module notes survive API collection.",
                "",
                "Warnings:",
                "    Module warnings are rendered in module chapters.",
                "",
                "Renderer Notes:",
                "    HTML: Module renderer notes are visible in references.",
                '"""',
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
    module = api.modules_by_name()["samplepkg"]

    assert isinstance(api, ApiPackage)
    assert module.notes == ["Module notes survive API collection."]
    assert module.warnings == ["Module warnings are rendered in module chapters."]
    assert module.renderer_notes[0].output_format == "html"
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
    assert ApiPresentationProfile.from_dict(ApiPresentationProfile.review().to_dict()).include_review_notes
    parameter_table = functions[0].to_parameters_table()
    assert isinstance(parameter_table, Table)
    assert parameter_table.resolved_split(default_threshold=999_999)
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
    summary_table = api.to_summary_table(functions)
    assert isinstance(summary_table, Table)
    assert summary_table.resolved_split(default_threshold=999_999)
    website_table = api.to_summary_table(classes, profile="website")
    website_name = website_table.rows[0][2].content.content[0]
    assert isinstance(website_name, Hyperlink)
    assert website_name.internal
    assert website_name.target == classes[0].anchor_name()
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
    assert f'id="{classes[0].anchor_name()}"' in website_html
    assert f'href="#{classes[0].anchor_name()}"' in website_html

    sidecar = tmp_path / "api.json"
    api.write_json(sidecar)
    readback = ApiPackage.read_json(sidecar)
    assert readback.find("samplepkg.Widget") is not None
    assert readback.modules_by_name()["samplepkg"].warnings == module.warnings

    module_doc = Document("Module API", module.to_chapter(profile="reference"))
    module_html = tmp_path / "module-api.html"
    module_doc.save_html(module_html)
    module_html_text = module_html.read_text(encoding="utf-8")
    assert "Module notes survive API collection." in module_html_text
    assert "Module warnings are rendered in module chapters." in module_html_text
    assert "Module renderer notes are visible in references." in module_html_text

    module_blocks_doc = Document(
        "Module Blocks",
        Chapter("API", *module.to_blocks(profile="reference")),
    )
    module_blocks_html = tmp_path / "module-blocks.html"
    module_blocks_doc.save_html(module_blocks_html)
    module_blocks_html_text = module_blocks_html.read_text(encoding="utf-8")
    assert "Module notes survive API collection." in module_blocks_html_text
    assert "Module warnings are rendered in module chapters." in module_blocks_html_text
    assert "Module renderer notes are visible in references." in module_blocks_html_text

    limited_module_doc = Document("Limited Module API", module.to_chapter(max_level=2))
    limited_module_html = tmp_path / "limited-module-api.html"
    limited_module_doc.save_html(limited_module_html)
    limited_module_html_text = limited_module_html.read_text(encoding="utf-8")
    method_anchor = classes[0].select(kind="method")[0].anchor_name()
    assert f'id="{classes[0].anchor_name()}"' in limited_module_html_text
    assert f'id="{method_anchor}"' not in limited_module_html_text


def test_api_package_document_preserves_coverage_issue_details(tmp_path: Path) -> None:
    package_dir = tmp_path / "coveragepkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "def undocumented(path: str) -> str:\n"
        "    return path\n",
        encoding="utf-8",
    )

    api = collect_api(package_dir, public_policy="underscore", collector="inspect")
    document = api.to_document(include_coverage=True, include_modules=False)
    coverage_chapter = document.body.children[1]
    issue_tables = [
        child
        for child in coverage_chapter.children
        if isinstance(child, Table)
        and child.caption is not None
        and child.caption.plain_text() == "API documentation issues"
    ]

    assert coverage_chapter.plain_title() == "API Documentation Coverage"
    assert issue_tables
    issue_codes = [row[1].content.plain_text() for row in issue_tables[0].rows]
    assert "missing-docstring" in issue_codes

    html_path = tmp_path / "coverage-reference.html"
    document.save_html(html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "API documentation issues" in html
    assert "missing-docstring" in html


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

    reference = obj.to_signature_code_block(profile="reference")
    compact = obj.to_signature_code_block(profile=ApiPresentationProfile.compact())

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
    assert ApiPresentationProfile.from_dict(ApiPresentationProfile.compact().to_dict()).max_signature_width == 88
    assert ApiPresentationProfile.from_dict(ApiPresentationProfile.compact().to_dict()).max_signature_lines == 24

    long_signature = ApiObject(
        kind="function",
        name="many",
        qualname="pkg.many",
        module="pkg",
        signature="pkg.many(" + ", ".join(f"value_{index}: str" for index in range(40)) + ")",
    )
    truncated = long_signature.to_signature_code_block(profile=ApiPresentationProfile.compact())
    assert truncated is not None
    assert len(truncated.code.splitlines()) == 24
    assert truncated.code.splitlines()[-1] == "..."


def test_api_examples_escape_xml_incompatible_control_chars(tmp_path: Path) -> None:
    example = ApiExample('fragment = math(r"\x07lpha + \x08eta")')
    block = example.to_code_block()

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
    function = api.find("stylepkg.load")
    assert function is not None
    assert any(row[1] == "docstring-style-mismatch" for row in function.as_issue_rows())


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
    monkeypatch.syspath_prepend(str(repo / "src"))

    api = collect_api(repo, public_policy="__all__", collector="inspect")

    assert api.name == "widgetlib"
    assert {module.name for module in api.modules} == {"widgetlib", "widgetlib.core"}
    assert api.find("widgetlib.Widget") is not None
    assert api.find("widgetlib.core.Widget.render") is not None
    assert [obj.qualname for obj in api.select(kind="class", module="widgetlib")] == [
        "widgetlib.Widget"
    ]

    core_module = collect_module_api(
        "widgetlib.core",
        public_policy="underscore",
        collector="inspect",
    )
    assert core_module.name == "widgetlib.core"
    assert core_module.find("widgetlib.core.Widget.render") is not None
    assert Document("Core API", core_module.to_chapter(profile="manual")).validate().ok

    looked_up = collect_object_api(
        "widgetlib.core.Widget.render",
        public_policy="underscore",
        collector="inspect",
    )
    assert looked_up.kind == "method"
    assert looked_up.parameters[0].name == "path"

    core = importlib.import_module("widgetlib.core")
    live_class = collect_object_api(
        core.Widget,
        public_policy="underscore",
        collector="inspect",
    )
    live_method = collect_object_api(
        core.Widget.render,
        public_policy="underscore",
        collector="inspect",
    )
    live_function = collect_object_api(
        core.make_widget,
        public_policy="underscore",
        collector="inspect",
    )
    live_property = collect_object_api(
        core.Widget.title,
        public_policy="underscore",
        collector="inspect",
    )
    bound_method = collect_object_api(
        core.Widget("demo").render,
        public_policy="underscore",
        collector="inspect",
    )

    assert live_class.qualname == "widgetlib.core.Widget"
    assert live_method.kind == "method"
    assert live_method.parameters[0].name == "path"
    assert live_function.qualname == "widgetlib.core.make_widget"
    assert live_property.kind == "property"
    assert live_property.qualname == "widgetlib.core.Widget.title"
    assert bound_method.qualname == "widgetlib.core.Widget.render"


def test_collect_api_supports_src_layout_namespace_package_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    package_dir = repo / "src" / "ns_pkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "[project]\nname = \"namespace-lib\"\n",
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        "\n".join(
            [
                '"""Namespace core APIs."""',
                "",
                "def run(path: str) -> str:",
                '    """Run a namespace command.',
                "",
                "    Args:",
                "        path: Input path.",
                "    Returns:",
                "        str: Input path.",
                '    """',
                "    return path",
            ]
        ),
        encoding="utf-8",
    )

    api = collect_api(repo, public_policy="underscore", collector="inspect")

    assert api.name == "ns_pkg"
    assert [module.name for module in api.modules] == ["ns_pkg.core"]
    run = api.find("ns_pkg.core.run")
    assert run is not None
    assert run.parameters[0].description == "Input path."

    if importlib.util.find_spec("griffe") is not None:
        griffe_api = collect_api(repo, public_policy="underscore", collector="griffe")
        assert griffe_api.find("ns_pkg.core.run") is not None


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
        object_exclude_patterns=("filtermods.core.run",),
    )

    api = collect_api(package_dir, config=config, public_policy="underscore", collector="inspect")

    assert api.metadata["file_count"] == 1
    assert api.modules == []
    assert api.find("filtermods.core.run") is None
    assert api.find("filtermods.experimental.preview") is None
    assert api.find("filtermods.tests.helper") is None
    assert config.to_dict()["module_include_patterns"] == ["filtermods.*"]
    assert config.to_dict()["object_exclude_patterns"] == ["filtermods.core.run"]
    assert ApiCollectConfig.from_dict(config.to_dict()) == config
    config_path = tmp_path / "apidoc-config.json"
    config.write_json(config_path)
    assert ApiCollectConfig.read_json(config_path) == config
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "\n".join(
            [
                "[tool.oodocs.apidoc]",
                'collector = "inspect"',
                'public-policy = "underscore"',
                'docstring-style = "auto"',
                'module-include-patterns = ["filtermods.*"]',
                'module-exclude-patterns = ["filtermods.tests", "filtermods.experimental"]',
                'object-exclude-patterns = ["filtermods.core.run"]',
                'profile = "website"',
                'formats = ["html"]',
                "sidecars = true",
                'kind = ["function"]',
                'module-prefix = "filtermods.core"',
            ]
        ),
        encoding="utf-8",
    )
    pyproject_config = ApiCollectConfig.from_pyproject(tmp_path)
    assert pyproject_config.collector == "inspect"
    assert pyproject_config.public_policy == "underscore"
    assert pyproject_config.module_include_patterns == ("filtermods.*",)
    assert pyproject_config.module_exclude_patterns == (
        "filtermods.tests",
        "filtermods.experimental",
    )
    assert pyproject_config.object_exclude_patterns == ("filtermods.core.run",)
    assert ApiCollectConfig.read_file(pyproject_path) == pyproject_config
    pyproject_build_config = ApiBuildConfig.from_pyproject(tmp_path)
    assert pyproject_build_config.collection == pyproject_config
    assert pyproject_build_config.profile == "website"
    assert pyproject_build_config.output_formats == ("html",)
    assert pyproject_build_config.sidecars
    assert pyproject_build_config.kind == ("function",)
    assert pyproject_build_config.module_prefix == "filtermods.core"
    build_config_path = tmp_path / "apidoc-build-config.json"
    pyproject_build_config.write_json(build_config_path)
    assert ApiBuildConfig.read_json(build_config_path) == pyproject_build_config

    if importlib.util.find_spec("griffe") is not None:
        griffe_api = collect_api(
            package_dir,
            public_policy="underscore",
            collector="griffe",
            module_include_patterns=("filtermods.*",),
            module_exclude_patterns=("filtermods.tests", "filtermods.experimental"),
            object_exclude_patterns=("filtermods.core.run",),
        )
        assert griffe_api.metadata["file_count"] == 1
        assert griffe_api.modules == []

    include_api = collect_api(
        package_dir,
        public_policy="underscore",
        collector="inspect",
        object_include_patterns=("filtermods.core.run",),
    )
    assert [module.name for module in include_api.modules] == ["filtermods.core"]
    assert include_api.find("filtermods.core.run") is not None
    assert include_api.find("filtermods.experimental.preview") is None


def test_collect_api_accepts_utf8_bom_pyproject_and_sources(tmp_path: Path) -> None:
    package_dir = tmp_path / "bompkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_bytes(
        b"\xef\xbb\xbf"
        + (
            '"""BOM package."""\n'
            "\n"
            "def run(path: str) -> str:\n"
            '    """Run a path.\n\n'
            "    Args:\n"
            "        path: Input path.\n"
            "    Returns:\n"
            "        str: Input path.\n"
            '    """\n'
            "    return path\n"
        ).encode("utf-8")
    )
    (tmp_path / "pyproject.toml").write_bytes(
        b"\xef\xbb\xbf"
        + (
            "[project]\n"
            'name = "bompkg"\n'
            "\n"
            "[tool.oodocs.apidoc]\n"
            'collector = "inspect"\n'
            'public-policy = "underscore"\n'
            'docstring-style = "auto"\n'
        ).encode("utf-8")
    )

    config = ApiCollectConfig.from_pyproject(tmp_path)
    api = collect_api(tmp_path, config=config)

    assert api.find("bompkg.run") is not None


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
                "from .core import ConstructorOnly, Widget, make_widget",
                "__all__ = ['ConstructorOnly', 'Widget', 'make_widget']",
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
                "class ConstructorOnly:",
                '    """A constructor-documented class."""',
                "",
                "    def __init__(self, path: str) -> None:",
                '        """Create from a path.',
                "",
                "        Args:",
                "            path: Input path.",
                '        """',
                "        self.path = path",
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
    constructor_only = griffe_api.find("pkg.core.ConstructorOnly")
    assert constructor_only is not None
    assert constructor_only.parameters[0].name == "path"
    assert constructor_only.parameters[0].description == "Input path."
    assert constructor_only.parameters[0].documented
    method = griffe_api.find("pkg.core.Widget.render")
    assert method is not None
    assert method.parameters[0].name == "path"
    assert method.returns and method.returns.annotation == "str"


def test_griffe_fallback_can_be_disabled_for_strict_collection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    griffe = pytest.importorskip("griffe")
    package_dir = tmp_path / "strictpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                "def run() -> None:",
                '    """Run the strict package."""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    def fail_load(*args, **kwargs):
        raise RuntimeError("forced griffe failure")

    monkeypatch.setattr(griffe, "load", fail_load)
    api = collect_api(
        package_dir,
        collector="griffe",
        fallback_collector="none",
        public_policy="underscore",
    )

    assert api.name == "strictpkg"
    assert not api.modules
    assert any(
        issue.severity == "error" and issue.code == "griffe-load-failed"
        for issue in api.issues
    )
    assert api.metadata["fallback_collector"] == "none"


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
    assert isinstance(diff_readback.to_coverage_delta_table(), Table)

    diff_document = diff_readback.to_document(title="API Change Report")
    diff_html_path = tmp_path / "api-diff.html"
    diff_document.save_html(diff_html_path)
    diff_html = diff_html_path.read_text(encoding="utf-8")
    assert "Coverage Delta" in diff_html
    assert "Base public objects" in diff_html
    assert "Object coverage delta" in diff_html


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
    coverage_json = tmp_path / "coverage.json"
    coverage_csv = tmp_path / "coverage.csv"
    snapshot_json = tmp_path / "snapshot.json"
    build_dir = tmp_path / "build"
    diff_dir = tmp_path / "diff"

    assert main(["apidoc", "collect", str(package_dir), "--out", str(api_json)]) == 0
    assert api_json.exists()
    assert (
        main(
            [
                "apidoc",
                "check",
                str(package_dir),
                "--out-json",
                str(coverage_json),
                "--out-csv",
                str(coverage_csv),
            ]
        )
        == 0
    )
    assert ApiCoverageResult.read_json(coverage_json).package == "clipkg"
    assert coverage_csv.read_text(encoding="utf-8").startswith(
        "severity,code,qualname,module,path,line_number,message"
    )
    assert (
        main(
            [
                "apidoc",
                "build",
                str(package_dir),
                "--out",
                str(build_dir),
                "--to",
                "docx,pdf,html",
                "--sidecars",
            ]
        )
        == 0
    )
    assert (build_dir / "clipkg-api.docx").exists()
    assert (build_dir / "clipkg-api.pdf").exists()
    assert (build_dir / "clipkg-api.html").exists()
    build_html = (build_dir / "clipkg-api.html").read_text(encoding="utf-8")
    assert "clipkg API Reference" in build_html
    assert "clipkg.run" in build_html
    assert (build_dir / "clipkg-api.json").exists()
    assert (build_dir / "clipkg-api-coverage.json").exists()
    assert (build_dir / "clipkg-api-coverage.csv").exists()
    built_api = json.loads((build_dir / "clipkg-api.json").read_text(encoding="utf-8"))
    assert built_api["modules"][0]["name"] == "clipkg"
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
    assert "Wrote coverage-json" in captured.out
    assert "Wrote coverage-csv" in captured.out


def test_apidoc_cli_init_writes_config_for_general_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    package_dir = repo / "src" / "initpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "[project]\nname = \"initpkg\"\n",
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Init package."""\nfrom .core import Widget, run\n__all__ = ["Widget", "run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        "class Widget:\n"
        '    """A configured widget."""\n'
        "\n"
        "    def __init__(self, name: str) -> None:\n"
        '        """Create a widget.\n\n'
        "        Args:\n"
        "            name: Widget name.\n"
        '        """\n'
        "        self.name = name\n"
        "\n"
        "def run(path: str) -> str:\n"
        '    """Run a configured build.\n\n'
        "    Args:\n"
        "        path: Input path.\n"
        "    Returns:\n"
        "        str: Input path.\n"
        '    """\n'
        "    return path\n",
        encoding="utf-8",
    )
    build_dir = tmp_path / "init-build"

    assert main(
        [
            "apidoc",
            "init",
            str(repo),
            "--collector",
            "inspect",
            "--public-policy",
            "__all__",
            "--profile",
            "website",
            "--to",
            "html",
            "--out-dir",
            str(build_dir),
            "--no-class-signature-from-init",
            "--kind",
            "function",
            "--module-prefix",
            "initpkg.core",
        ]
    ) == 0

    config = ApiBuildConfig.from_pyproject(repo)
    assert config.collection.collector == "inspect"
    assert config.profile == "website"
    assert config.output_formats == ("html",)
    assert config.output_dir == str(build_dir)
    assert config.sidecars
    assert config.kind == ("function",)
    assert not config.collection.class_signature_from_init

    signature_json = tmp_path / "initpkg-signatures.json"
    assert main(
        [
            "apidoc",
            "collect",
            str(repo),
            "--collector",
            "inspect",
            "--public-policy",
            "__all__",
            "--no-class-signature-from-init",
            "--out",
            str(signature_json),
        ]
    ) == 0
    signature_api = ApiPackage.read_json(signature_json)
    widget = signature_api.find("initpkg.core.Widget")
    assert widget is not None
    assert widget.signature == "initpkg.core.Widget"

    assert main(["apidoc", "build", str(repo), "--config", str(repo / "pyproject.toml")]) == 0
    assert (build_dir / "initpkg-api.html").exists()
    assert (build_dir / "initpkg-api.json").exists()
    built_api = json.loads((build_dir / "initpkg-api.json").read_text(encoding="utf-8"))
    assert built_api["modules"][0]["members"][0]["qualname"] == "initpkg.core.run"

    json_config = tmp_path / "apidoc-build.json"
    assert main(["apidoc", "init", str(json_config), "--format", "json", "--to", "html"]) == 0
    assert ApiBuildConfig.read_json(json_config).output_formats == ("html",)


def test_apidoc_cli_filters_check_and_snapshot(tmp_path: Path) -> None:
    package_dir = tmp_path / "filterpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text('"""Filtered package."""\n', encoding="utf-8")
    (package_dir / "core.py").write_text(
        "class Worker:\n"
        '    """Run API work."""\n'
        "\n"
        "    def process(self, path: str) -> str:\n"
        '        """Process a path.\n\n'
        "        Args:\n"
        "            path: Input path.\n"
        "        Returns:\n"
        "            str: Input path.\n"
        '        """\n'
        "        return path\n"
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
    (package_dir / "legacy.py").write_text(
        "class Legacy:\n"
        "    pass\n",
        encoding="utf-8",
    )
    snapshot_json = tmp_path / "filtered-snapshot.json"
    build_dir = tmp_path / "filtered-build"
    configured_build_dir = tmp_path / "configured-filtered-build"
    max_level_build_dir = tmp_path / "max-level-build"
    config_path = tmp_path / "apidoc-config.json"
    config_json = tmp_path / "configured-api.json"
    pyproject_config_path = tmp_path / "pyproject.toml"
    pyproject_config_json = tmp_path / "pyproject-configured-api.json"
    pyproject_coverage_json = tmp_path / "pyproject-filtered-coverage.json"
    pyproject_snapshot_json = tmp_path / "pyproject-filtered-snapshot.json"
    ApiCollectConfig(
        collector="inspect",
        public_policy="underscore",
        module_include_patterns=("filterpkg.core",),
        module_exclude_patterns=("filterpkg.legacy",),
        object_exclude_patterns=("*.Worker.process",),
    ).write_json(config_path)
    pyproject_config_path.write_text(
        "\n".join(
            [
                "[tool.oodocs.apidoc]",
                'collector = "inspect"',
                'public-policy = "underscore"',
                'module-include-patterns = ["filterpkg.core"]',
                'module-exclude-patterns = ["filterpkg.legacy"]',
                'object-exclude-patterns = ["*.Worker.process"]',
                'profile = "website"',
                'formats = ["html"]',
                f'out = "{configured_build_dir.as_posix()}"',
                "sidecars = true",
                'kind = ["function"]',
                'module-prefix = "filterpkg.core"',
            ]
        ),
        encoding="utf-8",
    )

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
            "--object-exclude",
            "*.Worker.process",
            "--out",
            str(collected_json),
        ]
    ) == 0
    collected = json.loads(collected_json.read_text(encoding="utf-8"))
    assert [module["name"] for module in collected["modules"]] == ["filterpkg.core"]
    assert collected["modules"][0]["members"][0]["members"] == []

    assert main(
        [
            "apidoc",
            "collect",
            str(package_dir),
            "--config",
            str(config_path),
            "--out",
            str(config_json),
        ]
    ) == 0
    configured = json.loads(config_json.read_text(encoding="utf-8"))
    assert [module["name"] for module in configured["modules"]] == ["filterpkg.core"]
    assert configured["metadata"]["collector"] == "inspect"
    assert configured["modules"][0]["members"][0]["members"] == []

    assert main(
        [
            "apidoc",
            "collect",
            str(package_dir),
            "--config",
            str(pyproject_config_path),
            "--out",
            str(pyproject_config_json),
        ]
    ) == 0
    pyproject_configured = json.loads(pyproject_config_json.read_text(encoding="utf-8"))
    assert [module["name"] for module in pyproject_configured["modules"]] == ["filterpkg.core"]
    assert pyproject_configured["metadata"]["collector"] == "inspect"
    assert pyproject_configured["modules"][0]["members"][0]["members"] == []

    assert main(
        [
            "apidoc",
            "check",
            str(package_dir),
            "--config",
            str(pyproject_config_path),
            "--fail-under",
            "1.0",
            "--out-json",
            str(pyproject_coverage_json),
        ]
    ) == 0
    assert ApiCoverageResult.read_json(pyproject_coverage_json).public_object_count == 1

    assert main(
        [
            "apidoc",
            "snapshot",
            str(package_dir),
            "--config",
            str(pyproject_config_path),
            "--out",
            str(pyproject_snapshot_json),
        ]
    ) == 0
    pyproject_snapshot = json.loads(pyproject_snapshot_json.read_text(encoding="utf-8"))
    assert list(pyproject_snapshot["objects"]) == ["filterpkg.core.run"]

    assert main(
        [
            "apidoc",
            "build",
            str(package_dir),
            "--config",
            str(pyproject_config_path),
        ]
    ) == 0
    configured_html = (configured_build_dir / "filterpkg-api.html").read_text(encoding="utf-8")
    assert 'id="filterpkg-core-run"' in configured_html
    assert 'id="filterpkg-core-worker"' not in configured_html
    configured_build_api = json.loads(
        (configured_build_dir / "filterpkg-api.json").read_text(encoding="utf-8")
    )
    assert configured_build_api["modules"][0]["members"][0]["qualname"] == "filterpkg.core.run"
    assert (configured_build_dir / "filterpkg-api-coverage.csv").exists()

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
            "--sidecars",
        ]
    ) == 0
    html = (build_dir / "filterpkg-api.html").read_text(encoding="utf-8")
    assert 'href="#filterpkg-core-run"' in html
    assert 'id="filterpkg-core-run"' in html
    filtered_build_api = json.loads(
        (build_dir / "filterpkg-api.json").read_text(encoding="utf-8")
    )
    assert [module["name"] for module in filtered_build_api["modules"]] == ["filterpkg.core"]
    assert filtered_build_api["modules"][0]["members"][0]["qualname"] == "filterpkg.core.run"
    assert (build_dir / "filterpkg-api-coverage.csv").exists()

    assert main(
        [
            "apidoc",
            "build",
            str(package_dir),
            "--profile",
            "website",
            "--max-level",
            "2",
            "--out",
            str(max_level_build_dir),
            "--to",
            "html",
        ]
    ) == 0
    max_level_html = (max_level_build_dir / "filterpkg-api.html").read_text(encoding="utf-8")
    assert 'id="filterpkg-core-worker"' in max_level_html
    assert 'id="filterpkg-core-worker-process"' not in max_level_html


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
    target_api = example.collect_target_api(
        package_dir,
        public_policy="underscore",
        collector="inspect",
        docstring_style=ApiDocstringParser.auto(),
    )
    full_reference = example.build_full_package_document(api)
    composition = example.build_document(api, coverage)
    bundle_outputs = example.render_api_objects_example(
        api,
        coverage,
        tmp_path / "bundle",
    )

    outputs = {
        "docx": bundle_outputs["full_reference_docx"],
        "pdf": bundle_outputs["full_reference_pdf"],
        "html": bundle_outputs["full_reference_html"],
    }
    composition_outputs = {
        "docx": bundle_outputs["composition_docx"],
        "pdf": bundle_outputs["composition_pdf"],
        "html": bundle_outputs["composition_html"],
    }

    assert set(outputs) == {"docx", "pdf", "html"}
    assert set(composition_outputs) == {"docx", "pdf", "html"}
    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert_rendered_bundle(
        composition_outputs["docx"],
        composition_outputs["pdf"],
        composition_outputs["html"],
    )
    assert full_reference.validate(formats=("docx", "pdf", "html")).ok
    assert composition.validate(formats=("docx", "pdf", "html")).ok
    assert_docx_structure(
        composition_outputs["docx"],
        required_paragraphs=(
            "OODocs API Object Composition",
            "1 Selected Classes",
            "2 Focused Module: examplepkg",
            "3 Function Summary",
            "4 Coverage Summary",
        ),
        min_tables=3,
    )
    assert_pdf_text_and_pages(
        composition_outputs["pdf"],
        required_text=(
            "OODocs API Object Composition",
            "Selected Classes",
            "Focused Module: examplepkg",
            "Function Summary",
            "Coverage Summary",
        ),
        min_pages=1,
    )
    assert target_api.name == "examplepkg"
    assert target_api.find("examplepkg.Widget") is not None
    assert ApiPackage.read_json(bundle_outputs["api_json"]).name == "examplepkg"
    assert (
        ApiCoverageResult.read_json(bundle_outputs["coverage_json"]).package
        == "examplepkg"
    )
    assert bundle_outputs["coverage_csv"].read_text(encoding="utf-8").startswith(
        "severity,code,qualname,module,path,line_number,message"
    )
    html = outputs["html"].read_text(encoding="utf-8")
    assert "examplepkg.Widget" in html
    assert "examplepkg.run" in html
    assert_html_internal_links_resolve(outputs["html"])
    assert any(
        getattr(child.title[0], "value", "") == "Selected Classes"
        for child in composition.body.children
        if hasattr(child, "title")
    )
    assert any(
        getattr(child.title[0], "value", "") == "Focused Module: examplepkg"
        for child in composition.body.children
        if hasattr(child, "title")
    )

    cli_output = tmp_path / "cli-bundle"
    example.main(
        [
            str(package_dir),
            "--public-policy",
            "underscore",
            "--collector",
            "inspect",
            "--docstring-style",
            "auto",
            "--to",
            "html",
            "--out",
            str(cli_output),
            "--quiet",
        ]
    )

    assert (cli_output / "oodocs-full-api-reference.html").exists()
    assert (cli_output / "oodocs-api-objects.html").exists()
    cli_html = (cli_output / "oodocs-full-api-reference.html").read_text(
        encoding="utf-8"
    )
    composition_html = (cli_output / "oodocs-api-objects.html").read_text(
        encoding="utf-8"
    )
    assert "examplepkg API Reference" in cli_html
    assert "Focused Module: examplepkg" in composition_html
    assert "examplepkg.run" in composition_html
    assert "examplepkg.Widget" in cli_html
    assert_html_internal_links_resolve(cli_output / "oodocs-full-api-reference.html")
