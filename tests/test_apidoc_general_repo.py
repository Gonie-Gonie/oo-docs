from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from apidoc_samples import (
    write_custom_docstring_parser_repo,
    write_flit_package_repo,
    write_flit_module_file_repo,
    write_hatch_multi_package_repo,
    write_hatch_only_include_repo,
    write_import_names_package_repo,
    write_import_names_module_file_repo,
    write_mixed_docstring_repo,
    write_pdm_package_dir_repo,
    write_pdm_module_file_repo,
    write_poetry_package_repo,
    write_setuptools_py_module_repo,
    write_single_file_module,
)
from example_regression import (
    assert_docx_structure,
    assert_html_internal_links_resolve,
    assert_pdf_text_and_pages,
    assert_rendered_bundle,
)
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import (
    ApiHelpBookConfig,
    ApiCollectConfig,
    ApiCoverageResult,
    ApiDocstringParser,
    ApiPackage,
    ApiSnapshot,
    api_coverage_to_chapter,
    api_objects_to_chapter,
    api_objects_to_summary_table,
    api_package_to_help_book,
    check_api_docs,
    collect_api,
    collect_module_api,
    collect_object_api,
    docstring_parser_import_paths,
)


def _load_api_objects_example():
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
    return example


def _save_api_reference(
    target: Path,
    output_dir: Path,
    *,
    output_formats: tuple[str, ...] = ("html",),
    collector: str = "inspect",
    public_policy: str = "__all__",
    docstring_style: object = "auto",
    sidecars: bool = True,
) -> None:
    ApiHelpBookConfig(
        collection=ApiCollectConfig(
            collector=collector,
            public_policy=public_policy,
            docstring_style=docstring_style,
        ),
        output_formats=output_formats,
        output_dir=str(output_dir),
        sidecars=sidecars,
    ).save_all(target)


def test_general_repo_auto_parser_objects_compose_into_document(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    parser = ApiDocstringParser.auto()

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=parser,
    )
    client = api.find_object("mixedpkg.Client")
    method = api.find_object("mixedpkg.Client.connect")
    function = api.find_object("mixedpkg.connect")
    stream = api.find_object("mixedpkg.stream")
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "mixedpkg"
    assert client is not None
    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"
    assert method.parameters[0].description == "Timeout in seconds."
    assert method.returns is not None
    assert method.returns.description == "Whether the connection succeeded."
    assert function is not None
    assert function.metadata["docstring_style"] == "google"
    assert stream is not None
    assert stream.metadata["docstring_style"] == "markdown"
    assert stream.returns is not None
    assert stream.returns.annotation == "str"
    assert stream.returns.description == "Endpoint update payload."
    assert coverage.object_coverage == 1.0

    document = Document(
        "Mixed Package API Notes",
        Chapter(
            "Selected API",
            Paragraph("These sections are composed from a normal Python repository."),
            client.to_section(level=2, presentation="manual"),
        ),
        Chapter(
            "Function Index",
            api.to_summary_table(api.select_functions(), presentation="compact"),
        ),
        Chapter("Coverage", coverage.to_table()),
    )

    outputs = document.save_all(
        tmp_path / "rendered",
        stem="mixed-api",
        formats=("docx", "pdf", "html"),
    )

    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert document.validate(formats=("docx", "pdf", "html")).ok
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "Mixed Package API Notes",
            "1 Selected API",
            "1.1 mixedpkg.Client",
            "2 Function Index",
            "3 Coverage",
        ),
        min_tables=4,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "Mixed Package API Notes",
            "mixedpkg.Client",
            "Timeout in seconds.",
            "Object coverage",
        ),
        min_pages=1,
    )
    assert_html_internal_links_resolve(outputs["html"])
    html = outputs["html"].read_text(encoding="utf-8")
    assert "mixedpkg.Client" in html
    assert "Timeout in seconds." in html
    assert "Object coverage" in html


def test_general_repo_sphinx_seealso_directives_compose_into_reference(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "sphinxrepo"
    package_dir = repo / "sphinxpkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Sphinx-style package."""',
                "",
                "__all__ = ['load_widget', 'open_widget']",
                "",
                "def open_widget(path: str) -> str:",
                '    """Open a widget.',
                "",
                "    :param path: Input path.",
                "    :type path: str",
                "    :returns: Opened widget name.",
                "    :rtype: str",
                '    """',
                "    return path",
                "",
                "def load_widget(path: str) -> str:",
                '    """Load a widget.',
                "",
                "    :param path: Input path.",
                "    :type path: str",
                "    :returns: Loaded widget name.",
                "    :rtype: str",
                "",
                "    .. seealso::",
                "",
                "        :func:`open_widget`: Open a widget without loading metadata.",
                "",
                "    .. admonition:: Renderer Notes",
                "",
                "        HTML: :func:`open_widget` receives a stable related API entry.",
                '    """',
                "    return open_widget(path)",
            ]
        ),
        encoding="utf-8",
    )

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    obj = api.find_object("sphinxpkg.load_widget")
    assert obj is not None
    assert obj.metadata["docstring_style"] == "sphinx"
    assert obj.see_also[0].label == "open_widget"
    assert obj.see_also[0].description == "Open a widget without loading metadata."
    assert obj.renderer_notes[0].output_format == "html"
    assert obj.renderer_notes[0].message == "open_widget receives a stable related API entry."

    document = Document(
        "Sphinx API",
        Chapter("Selected API", obj.to_section(level=2, presentation="reference")),
    )
    html_path = tmp_path / "sphinx-api.html"
    document.save_html(html_path)

    assert_html_internal_links_resolve(html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "Open a widget without loading metadata." in html
    assert "open_widget receives a stable related API entry." in html


def test_general_repo_auto_parser_extended_parameter_sections_render(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "kwrepo"
    package_dir = repo / "kwpkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Keyword parameter package."""',
                "",
                "__all__ = ['load_google', 'load_numpy', 'load_sphinx', 'load_markdown']",
                "",
                "def load_google(path: str, *, retries: int = 0) -> str:",
                '    """Load via Google-style sections.',
                "",
                "    Args:",
                "        path (str): Input path.",
                "",
                "    Keyword Args:",
                "        retries (int): Retry count.",
                "",
                "    Returns:",
                "        str: Loaded path.",
                '    """',
                "    return path",
                "",
                "def load_numpy(path: str, *, timeout: float = 1.0) -> str:",
                '    """Load via NumPy-style sections.',
                "",
                "    Parameters",
                "    ----------",
                "    path : str",
                "        Input path.",
                "",
                "    Other Parameters",
                "    ----------------",
                "    timeout : float",
                "        Timeout in seconds.",
                "",
                "    Returns",
                "    -------",
                "    str",
                "        Loaded path.",
                '    """',
                "    return path",
                "",
                "def load_sphinx(path: str, *, cache: bool = False) -> str:",
                '    """Load via Sphinx-style keyword fields.',
                "",
                "    :param path: Input path.",
                "    :type path: str",
                "    :keyword cache: Whether to use cached data.",
                "    :kwtype cache: bool",
                "    :returns: Loaded path.",
                "    :rtype: str",
                '    """',
                "    return path",
                "",
                "def load_markdown(path: str, *, verbose: bool = False, dry_run: bool = False) -> str:",
                '    """Load via Markdown-style sections.',
                "",
                "    ## Parameters",
                "",
                "    path (str): Input path.",
                "",
                "    ## Keyword Arguments",
                "",
                "    verbose (bool): Whether to print progress.",
                "",
                "    ## Other Parameters",
                "",
                "    dry_run : bool",
                "        Whether to skip side effects.",
                "",
                "    ## Returns",
                "",
                "    str: Loaded path.",
                '    """',
                "    return path",
            ]
        ),
        encoding="utf-8",
    )

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    google = api.find_object("kwpkg.load_google")
    numpy = api.find_object("kwpkg.load_numpy")
    sphinx = api.find_object("kwpkg.load_sphinx")
    markdown = api.find_object("kwpkg.load_markdown")

    assert google is not None
    assert google.metadata["docstring_style"] == "google"
    assert [item.name for item in google.parameters] == ["path", "retries"]
    assert numpy is not None
    assert numpy.metadata["docstring_style"] == "numpy"
    assert [item.name for item in numpy.parameters] == ["path", "timeout"]
    assert sphinx is not None
    assert sphinx.metadata["docstring_style"] == "sphinx"
    assert [item.name for item in sphinx.parameters] == ["path", "cache"]
    assert markdown is not None
    assert markdown.metadata["docstring_style"] == "markdown"
    assert [item.name for item in markdown.parameters] == ["path", "verbose", "dry_run"]

    document = Document(
        "Keyword Parameter API",
        Chapter(
            "Selected API",
            google.to_section(level=2),
            numpy.to_section(level=2),
            sphinx.to_section(level=2),
            markdown.to_section(level=2),
        ),
    )
    html_path = tmp_path / "keyword-parameters.html"
    document.save_html(html_path)

    assert_html_internal_links_resolve(html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "Retry count." in html
    assert "Timeout in seconds." in html
    assert "Whether to use cached data." in html
    assert "Whether to print progress." in html
    assert "Whether to skip side effects." in html


def test_general_repo_sphinx_varargs_match_signature_and_render(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "varrepo"
    package_dir = repo / "varpkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Varargs package."""',
                "",
                "__all__ = ['call_hook']",
                "",
                "def call_hook(*args: object, **kwargs: object) -> object:",
                '    """Call a hook.',
                "",
                "    :param *args: Positional hook arguments.",
                "    :type *args: tuple[object, ...]",
                "    :param **kwargs: Keyword hook arguments.",
                "    :type **kwargs: dict[str, object]",
                "    :returns: Hook result.",
                "    :rtype: object",
                '    """',
                "    return kwargs.get('result', args[0] if args else None)",
            ]
        ),
        encoding="utf-8",
    )

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    obj = api.find_object("varpkg.call_hook")
    coverage = check_api_docs(api, fail_under=1.0)

    assert obj is not None
    assert obj.metadata["docstring_style"] == "sphinx"
    assert [(item.name, item.documented, item.description) for item in obj.parameters] == [
        ("*args", True, "Positional hook arguments."),
        ("**kwargs", True, "Keyword hook arguments."),
    ]
    assert not [issue for issue in coverage.issues if issue.code in {"missing-parameter-doc", "extra-parameter-doc"}]

    document = Document("Varargs API", Chapter("Selected API", obj.to_section(level=2)))
    html_path = tmp_path / "varargs-api.html"
    document.save_html(html_path)

    assert_html_internal_links_resolve(html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "Positional hook arguments." in html
    assert "Keyword hook arguments." in html


def test_general_repo_auto_parser_singular_sections_render(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "singularrepo"
    package_dir = repo / "singularpkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Singular section package."""',
                "",
                "__all__ = ['load_google', 'load_markdown']",
                "",
                "def load_google(path: str) -> str:",
                '    """Load data with singular Google sections.',
                "",
                "    Parameter:",
                "        path (str): Input path.",
                "",
                "    Return:",
                "        str: Loaded path.",
                "",
                "    Warning:",
                "        Avoid user-provided paths.",
                '    """',
                "    return path",
                "",
                "def load_markdown(path: str) -> str:",
                '    """Load data with singular Markdown headings.',
                "",
                "    ## Parameter",
                "",
                "    path (str): Input path.",
                "",
                "    ## Return",
                "",
                "    str: Loaded path.",
                "",
                "    ## Warning",
                "",
                "    Avoid user-provided paths.",
                '    """',
                "    return path",
            ]
        ),
        encoding="utf-8",
    )

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    google = api.find_object("singularpkg.load_google")
    markdown = api.find_object("singularpkg.load_markdown")

    assert google is not None
    assert google.metadata["docstring_style"] == "google"
    assert google.parameters[0].description == "Input path."
    assert google.returns is not None
    assert google.returns.description == "Loaded path."
    assert google.warnings == ["Avoid user-provided paths."]
    assert markdown is not None
    assert markdown.metadata["docstring_style"] == "markdown"
    assert markdown.parameters[0].description == "Input path."
    assert markdown.returns is not None
    assert markdown.returns.description == "Loaded path."
    assert markdown.warnings == ["Avoid user-provided paths."]

    document = Document(
        "Singular Sections API",
        Chapter(
            "Selected API",
            google.to_section(level=2),
            markdown.to_section(level=2),
        ),
    )
    html_path = tmp_path / "singular-sections.html"
    document.save_html(html_path)

    assert_html_internal_links_resolve(html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "Input path." in html
    assert "Loaded path." in html
    assert "Avoid user-provided paths." in html


def test_general_repo_auto_parser_object_survives_build_config_json_roundtrip(
    tmp_path: Path,
) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    config_path = tmp_path / "mixed-apidoc-build.json"
    output_dir = tmp_path / "roundtrip-rendered"
    build = ApiHelpBookConfig(
        collection=ApiCollectConfig(
            collector="inspect",
            public_policy="__all__",
            docstring_style=ApiDocstringParser.auto(),
        ),
        presentation="compact",
        output_formats=("docx", "pdf", "html"),
        output_dir=str(output_dir),
        stem="mixed-roundtrip",
        sidecars=True,
    )

    build.save_json(config_path)
    readback = ApiHelpBookConfig.load_json(config_path, target=repo)
    api = readback.collect(repo)
    method = api.find_object("mixedpkg.Client.connect")
    function = api.find_object("mixedpkg.connect")
    stream = api.find_object("mixedpkg.stream")
    outputs = readback.save_all(repo)

    assert readback.collection.docstring_style == "auto"
    assert readback.collection.docstring_parser() == ApiDocstringParser.auto()
    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"
    assert method.parameters[0].description == "Timeout in seconds."
    assert function is not None
    assert function.metadata["docstring_style"] == "google"
    assert stream is not None
    assert stream.metadata["docstring_style"] == "markdown"
    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert outputs["api-json"].exists()
    assert outputs["coverage-json"].exists()
    assert outputs["coverage-csv"].exists()
    assert ApiPackage.load_json(outputs["api-json"]).find_object("mixedpkg.Client.connect") is not None
    assert ApiCoverageResult.load_json(outputs["coverage-json"]).object_coverage == 1.0
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "mixedpkg API Reference",
            "1 API Contents",
            "2 Public API",
            "3 API Documentation Coverage",
        ),
        min_tables=6,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "mixedpkg API Reference",
            "mixedpkg.Client",
            "Base endpoint URL.",
        ),
        min_pages=1,
    )
    assert_html_internal_links_resolve(outputs["html"], required_text=("mixedpkg.Client",))


def test_general_repo_facades_select_module_and_object_from_target_path(
    tmp_path: Path,
) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    kwargs = {
        "collector": "inspect",
        "public_policy": "__all__",
        "docstring_style": ApiDocstringParser.auto(),
    }

    module = collect_module_api("mixedpkg.core", target=repo, **kwargs)
    method = collect_object_api("mixedpkg.core.Client.connect", target=repo, **kwargs)
    reexported_class = collect_object_api("mixedpkg.Client", target=repo, **kwargs)

    assert module.name == "mixedpkg.core"
    assert module.find_object("mixedpkg.core.Client.connect") is not None
    assert method.kind == "method"
    assert method.parameters[0].name == "timeout"
    assert method.parameters[0].description == "Timeout in seconds."
    assert reexported_class.kind == "class"
    assert reexported_class.qualname == "mixedpkg.Client"

    module_document = Document(
        "Mixed Core Module API",
        module.to_chapter(presentation="manual", max_heading_level=3),
    )
    object_document = Document(
        "Mixed Connect API",
        Chapter(
            "Focused Method",
            Paragraph("This section is selected from the repository API tree."),
            method.to_section(level=2, presentation="manual"),
        ),
    )

    module_outputs = module_document.save_all(
        tmp_path / "module-facade",
        stem="mixed-core",
        formats=("docx", "pdf", "html"),
    )
    object_outputs = object_document.save_all(
        tmp_path / "object-facade",
        stem="mixed-connect",
        formats=("docx", "pdf", "html"),
    )

    assert_rendered_bundle(
        module_outputs["docx"],
        module_outputs["pdf"],
        module_outputs["html"],
    )
    assert_rendered_bundle(
        object_outputs["docx"],
        object_outputs["pdf"],
        object_outputs["html"],
    )
    assert_docx_structure(
        module_outputs["docx"],
        required_paragraphs=(
            "Mixed Core Module API",
            "1 mixedpkg.core",
            "1.1 mixedpkg.core.Client",
        ),
        min_tables=2,
    )
    assert_docx_structure(
        object_outputs["docx"],
        required_paragraphs=(
            "Mixed Connect API",
            "1 Focused Method",
            "1.1 mixedpkg.core.Client.connect",
        ),
        min_tables=1,
    )
    assert_pdf_text_and_pages(
        module_outputs["pdf"],
        required_text=("mixedpkg.core.Client", "Timeout in seconds."),
        min_pages=1,
    )
    assert_pdf_text_and_pages(
        object_outputs["pdf"],
        required_text=("mixedpkg.core.Client.connect", "Timeout in seconds."),
        min_pages=1,
    )
    assert_html_internal_links_resolve(
        module_outputs["html"],
        required_text=("mixedpkg.core.Client", "Timeout in seconds."),
    )
    assert_html_internal_links_resolve(
        object_outputs["html"],
        required_text=("mixedpkg.core.Client.connect", "Timeout in seconds."),
    )


def test_general_repo_render_helpers_compose_selected_api(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    document = Document(
        "Mixed Package API Helper Notes",
        api_objects_to_chapter(
            "Client Classes",
            api.select_objects(kind="class", module_prefix="mixedpkg"),
            presentation="manual",
            max_heading_level=3,
        ),
        Chapter(
            "Function Summary",
            api_objects_to_summary_table(
                api.select_functions(),
                presentation="compact",
                caption="Mixed package functions.",
            ),
        ),
        api_coverage_to_chapter(coverage),
    )

    outputs = document.save_all(
        tmp_path / "helper-rendered",
        stem="mixed-helper-api",
        formats=("docx", "pdf", "html"),
    )
    html = outputs["html"].read_text(encoding="utf-8")

    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert document.validate(formats=("docx", "pdf", "html")).ok
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "Mixed Package API Helper Notes",
            "1 Client Classes",
            "1.1 mixedpkg.Client",
            "2 Function Summary",
            "3 API Documentation Coverage",
        ),
        min_tables=5,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "Mixed Package API Helper Notes",
            "Client Classes",
            "mixedpkg.Client",
            "Mixed package functions.",
            "API Documentation Coverage",
        ),
        min_pages=1,
    )
    assert "Client Classes" in html
    assert "mixedpkg.Client" in html
    assert "Mixed package functions." in html
    assert "API Documentation Coverage" in html
    assert_html_internal_links_resolve(outputs["html"])


def test_general_repo_package_help_book_helper_builds_complete_reference(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )

    document = api_package_to_help_book(api, presentation="compact", max_heading_level=3)
    outputs = document.save_all(
        tmp_path / "package-rendered",
        stem="mixedpkg-api",
        formats=("docx", "pdf", "html"),
    )
    html = outputs["html"].read_text(encoding="utf-8")

    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert document.validate(formats=("docx", "pdf", "html")).ok
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "mixedpkg API Reference",
            "1 API Contents",
            "2 Public API",
            "2.1 mixedpkg.Client",
            "2.2 mixedpkg.connect",
            "3 API Documentation Coverage",
        ),
        min_tables=6,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "mixedpkg API Reference",
            "API Documentation Coverage",
            "mixedpkg.Client",
            "mixedpkg.connect",
        ),
        min_pages=1,
    )
    assert "mixedpkg API Reference" in html
    assert "API Contents" in html
    assert "API Documentation Coverage" in html
    assert "mixedpkg.Client" in html
    assert "mixedpkg.connect" in html
    assert_html_internal_links_resolve(outputs["html"])


def test_general_repo_api_objects_example_cli_targets_repo_path(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    output_dir = tmp_path / "example-bundle"
    example = _load_api_objects_example()

    example.main(
        [
            str(repo),
            "--collector",
            "inspect",
            "--public-policy",
            "__all__",
            "--docstring-style",
            "auto",
            "--outputs",
            "docx",
            "--outputs",
            "pdf",
            "--outputs",
            "html",
            "--out",
            str(output_dir),
            "--quiet",
        ]
    )

    help_book_docx = output_dir / "oodocs-api-reference.docx"
    help_book_pdf = output_dir / "oodocs-api-reference.pdf"
    help_book_html = output_dir / "oodocs-api-reference.html"
    object_composition_docx = output_dir / "oodocs-api-object-composition.docx"
    object_composition_pdf = output_dir / "oodocs-api-object-composition.pdf"
    object_composition_html_path = output_dir / "oodocs-api-object-composition.html"
    api_object_tree_json = output_dir / "oodocs-api-object-tree.json"
    api_coverage_json = output_dir / "oodocs-api-coverage.json"

    assert_rendered_bundle(help_book_docx, help_book_pdf, help_book_html)
    assert_rendered_bundle(object_composition_docx, object_composition_pdf, object_composition_html_path)
    assert api_object_tree_json.exists()
    assert api_coverage_json.exists()
    assert_docx_structure(
        help_book_docx,
        required_paragraphs=(
            "mixedpkg API Reference",
            "1 API Contents",
            "2 Public API",
            "2.1 mixedpkg.Client",
            "3 API Documentation Coverage",
        ),
        min_tables=6,
    )
    assert_docx_structure(
        object_composition_docx,
        required_paragraphs=(
            "OODocs API Object Composition",
            "1 Selected Classes",
            "2 Focused Module: mixedpkg.core",
            "3 Function Summary",
            "4 Coverage Summary",
        ),
        min_tables=4,
    )
    assert_pdf_text_and_pages(
        help_book_pdf,
        required_text=(
            "mixedpkg API Reference",
            "mixedpkg.Client",
            "mixedpkg.connect",
        ),
        min_pages=1,
    )
    assert_pdf_text_and_pages(
        object_composition_pdf,
        required_text=(
            "OODocs API Object Composition",
            "Focused Module: mixedpkg.core",
            "mixedpkg.core.Client.connect",
        ),
        min_pages=1,
    )
    rendered_api = ApiPackage.load_json(api_object_tree_json)
    rendered_method = rendered_api.find_object("mixedpkg.Client.connect")
    assert rendered_api.name == "mixedpkg"
    assert rendered_method is not None
    assert rendered_method.metadata["docstring_style"] == "numpy"
    assert rendered_method.parameters[0].description == "Timeout in seconds."
    assert ApiCoverageResult.load_json(api_coverage_json).object_coverage == 1.0

    html = help_book_html.read_text(encoding="utf-8")
    object_composition_html = object_composition_html_path.read_text(encoding="utf-8")
    assert "mixedpkg API Reference" in html
    assert "mixedpkg.Client" in html
    assert "mixedpkg.connect" in html
    assert "Focused Module: mixedpkg.core" in object_composition_html
    assert "mixedpkg.core.Client.connect" in object_composition_html
    assert_html_internal_links_resolve(help_book_html)
    assert_html_internal_links_resolve(object_composition_html_path)


def test_general_repo_pyproject_auto_parser_builds_cli_bundle(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    build_config = ApiHelpBookConfig.from_pyproject(repo)
    parser = build_config.collection.docstring_parser()
    output_dir = tmp_path / "bundle"
    example_output_dir = tmp_path / "example-config-bundle"
    example = _load_api_objects_example()

    assert parser == ApiDocstringParser.auto()
    assert parser.detect("Parameters\n----------\ntimeout : float\n    Timeout.") == "numpy"
    assert build_config.module_prefix == "mixedpkg"

    api = collect_api(repo, config=build_config.collection)
    method = api.find_object("mixedpkg.Client.connect")
    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"

    ApiHelpBookConfig.from_pyproject(repo).save_all(repo, output_dir=output_dir)

    html_path = output_dir / "mixedpkg-api.html"
    api_path = output_dir / "mixedpkg-api.json"
    coverage_path = output_dir / "mixedpkg-api-coverage.json"
    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    assert (output_dir / "mixedpkg-api-coverage.csv").exists()

    html = html_path.read_text(encoding="utf-8")
    assert "mixedpkg.Client" in html
    assert "Timeout in seconds." in html
    assert_html_internal_links_resolve(html_path)

    rendered_api = ApiPackage.load_json(api_path)
    rendered_method = rendered_api.find_object("mixedpkg.Client.connect")
    assert rendered_method is not None
    assert rendered_method.metadata["docstring_style"] == "numpy"
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0

    example.main(
        [
            str(repo),
            "--config",
            str(repo / "pyproject.toml"),
            "--out",
            str(example_output_dir),
            "--quiet",
        ]
    )

    example_html = example_output_dir / "oodocs-api-reference.html"
    example_api_path = example_output_dir / "oodocs-api-object-tree.json"
    example_coverage_path = example_output_dir / "oodocs-api-coverage.json"
    assert example_html.exists()
    assert example_api_path.exists()
    assert example_coverage_path.exists()
    assert not (example_output_dir / "oodocs-api-reference.docx").exists()
    assert not (example_output_dir / "oodocs-api-reference.pdf").exists()
    assert_html_internal_links_resolve(example_html)

    example_api = ApiPackage.load_json(example_api_path)
    example_method = example_api.find_object("mixedpkg.Client.connect")
    assert example_method is not None
    assert example_method.metadata["docstring_style"] == "numpy"
    assert ApiCoverageResult.load_json(example_coverage_path).object_coverage == 1.0


def test_general_python_file_module_targets_build_reference_and_example(
    tmp_path: Path,
) -> None:
    module_path = write_single_file_module(tmp_path)
    parser = ApiDocstringParser.auto()
    api = collect_api(
        module_path,
        collector="inspect",
        public_policy="__all__",
        docstring_style=parser,
    )
    client = api.find_object("singlemod.Client")
    method = api.find_object("singlemod.Client.connect")
    function = api.find_object("singlemod.connect")
    stream = api.find_object("singlemod.stream")
    coverage = check_api_docs(api, fail_under=1.0)
    composed_output = tmp_path / "single-file-composed"
    cli_output = tmp_path / "single-file-cli"
    example_output = tmp_path / "single-file-example"
    example = _load_api_objects_example()

    assert api.name == "singlemod"
    assert [module.name for module in api.modules] == ["singlemod"]
    assert client is not None
    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"
    assert method.parameters[0].description == "Timeout in seconds."
    assert function is not None
    assert function.metadata["docstring_style"] == "google"
    assert stream is not None
    assert stream.metadata["docstring_style"] == "markdown"
    assert coverage.object_coverage == 1.0

    document = Document(
        "Single File API Notes",
        Chapter(
            "Selected API",
            Paragraph("These sections are composed from one Python module file."),
            client.to_section(level=2, presentation="manual"),
        ),
        Chapter(
            "Function Index",
            api.to_summary_table(api.select_functions(), presentation="compact"),
        ),
    )
    outputs = document.save_all(
        composed_output,
        stem="single-file-api",
        formats=("docx", "pdf", "html"),
    )
    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert document.validate(formats=("docx", "pdf", "html")).ok
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "Single File API Notes",
            "1 Selected API",
            "1.1 singlemod.Client",
            "2 Function Index",
        ),
        min_tables=3,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "Single File API Notes",
            "singlemod.Client",
            "Timeout in seconds.",
            "Function Index",
        ),
        min_pages=1,
    )
    assert "singlemod.Client" in outputs["html"].read_text(encoding="utf-8")
    assert_html_internal_links_resolve(outputs["html"])

    _save_api_reference(
        module_path,
        cli_output,
        output_formats=("docx", "pdf", "html"),
    )
    cli_docx = cli_output / "singlemod-api.docx"
    cli_pdf = cli_output / "singlemod-api.pdf"
    cli_html = cli_output / "singlemod-api.html"
    cli_api_object_tree_json = cli_output / "singlemod-api.json"
    cli_api_coverage_json = cli_output / "singlemod-api-coverage.json"
    assert_rendered_bundle(cli_docx, cli_pdf, cli_html)
    assert_docx_structure(
        cli_docx,
        required_paragraphs=(
            "singlemod API Reference",
            "1 API Contents",
            "2 Public API",
            "2.1 singlemod.Client",
            "2.2 singlemod.connect",
            "3 API Documentation Coverage",
        ),
        min_tables=6,
    )
    assert_pdf_text_and_pages(
        cli_pdf,
        required_text=(
            "singlemod API Reference",
            "API Documentation Coverage",
            "singlemod.Client",
            "singlemod.connect",
        ),
        min_pages=1,
    )
    assert cli_html.exists()
    assert cli_api_object_tree_json.exists()
    assert cli_api_coverage_json.exists()
    assert_html_internal_links_resolve(cli_html)
    assert (
        ApiPackage.load_json(cli_api_object_tree_json).find_object("singlemod.Client.connect")
        is not None
    )
    assert ApiCoverageResult.load_json(cli_api_coverage_json).object_coverage == 1.0

    example.main(
        [
            str(module_path),
            "--collector",
            "inspect",
            "--public-policy",
            "__all__",
            "--docstring-style",
            "auto",
            "--outputs",
            "html",
            "--out",
            str(example_output),
            "--quiet",
        ]
    )
    example_html = example_output / "oodocs-api-reference.html"
    example_api_object_tree_json = example_output / "oodocs-api-object-tree.json"
    assert example_html.exists()
    assert example_api_object_tree_json.exists()
    assert "singlemod.Client" in example_html.read_text(encoding="utf-8")
    assert_html_internal_links_resolve(example_html)
    assert ApiPackage.load_json(example_api_object_tree_json).find_object("singlemod.stream") is not None


def test_general_py_modules_repo_targets_build_reference_and_example(
    tmp_path: Path,
) -> None:
    repo = write_setuptools_py_module_repo(tmp_path)
    output_dir = tmp_path / "single-module-repo-cli"
    example_output = tmp_path / "single-module-repo-example"
    example = _load_api_objects_example()

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "singlemod"
    assert [module.name for module in api.modules] == ["singlemod"]
    assert api.find_object("singlemod.Client.connect") is not None
    assert api.find_object("singlemod.connect") is not None
    assert api.find_object("singlemod.stream") is not None
    assert api.find_object("src.singlemod.Client") is None
    assert coverage.object_coverage == 1.0

    _save_api_reference(repo, output_dir)
    html_path = output_dir / "singlemod-api.html"
    api_path = output_dir / "singlemod-api.json"
    coverage_path = output_dir / "singlemod-api-coverage.json"

    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "singlemod.Client" in html
    assert "src.singlemod" not in html
    assert_html_internal_links_resolve(html_path)
    assert ApiPackage.load_json(api_path).find_object("singlemod.Client.connect") is not None
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0

    example.main(
        [
            str(repo),
            "--collector",
            "inspect",
            "--public-policy",
            "__all__",
            "--docstring-style",
            "auto",
            "--outputs",
            "html",
            "--out",
            str(example_output),
            "--quiet",
        ]
    )
    example_html = example_output / "oodocs-api-reference.html"
    example_api_object_tree_json = example_output / "oodocs-api-object-tree.json"

    assert example_html.exists()
    assert example_api_object_tree_json.exists()
    rendered_example = example_html.read_text(encoding="utf-8")
    assert "singlemod.Client" in rendered_example
    assert "src.singlemod" not in rendered_example
    assert_html_internal_links_resolve(example_html)
    assert ApiPackage.load_json(example_api_object_tree_json).find_object("singlemod.stream") is not None


def test_general_hatch_multi_package_repo_builds_complete_reference(
    tmp_path: Path,
) -> None:
    repo = write_hatch_multi_package_repo(tmp_path)
    output_dir = tmp_path / "multi-hatch-output"

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "multi_hatch_project"
    assert api.find_object("alpha.run") is not None
    assert api.find_object("beta.run") is not None
    assert api.find_object("lib.alpha.run") is None
    assert coverage.object_coverage == 1.0

    _save_api_reference(repo, output_dir)
    html_path = output_dir / "multi_hatch_project-api.html"
    api_path = output_dir / "multi_hatch_project-api.json"
    coverage_path = output_dir / "multi_hatch_project-api-coverage.json"

    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "alpha.run" in html
    assert "beta.run" in html
    assert "lib.alpha" not in html
    assert_html_internal_links_resolve(html_path)
    rendered_api = ApiPackage.load_json(api_path)
    assert rendered_api.find_object("alpha.run") is not None
    assert rendered_api.find_object("beta.run") is not None
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0


def test_general_hatch_only_include_repo_builds_complete_reference(
    tmp_path: Path,
) -> None:
    repo = write_hatch_only_include_repo(tmp_path)
    output_dir = tmp_path / "hatch-only-include-output"

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "onlypkg"
    assert api.find_object("onlypkg.run") is not None
    assert api.find_object("onlypkg.core.run") is not None
    assert api.find_object("lib.onlypkg.run") is None
    assert api.find_object("straypkg.leak") is None
    assert coverage.object_coverage == 1.0

    _save_api_reference(repo, output_dir)
    html_path = output_dir / "onlypkg-api.html"
    api_path = output_dir / "onlypkg-api.json"
    coverage_path = output_dir / "onlypkg-api-coverage.json"

    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "onlypkg.run" in html
    assert "lib.onlypkg" not in html
    assert "straypkg" not in html
    assert_html_internal_links_resolve(html_path)
    rendered_api = ApiPackage.load_json(api_path)
    assert rendered_api.find_object("onlypkg.run") is not None
    assert rendered_api.find_object("onlypkg.core.run") is not None
    assert rendered_api.find_object("lib.onlypkg.run") is None
    assert rendered_api.find_object("straypkg.leak") is None
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0


def test_general_pdm_package_dir_repo_builds_complete_reference(
    tmp_path: Path,
) -> None:
    repo = write_pdm_package_dir_repo(tmp_path)
    output_dir = tmp_path / "pdm-output"

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "pdmpkg"
    assert api.find_object("pdmpkg.run") is not None
    assert api.find_object("pdmpkg.core.run") is not None
    assert api.find_object("lib.pdmpkg.run") is None
    assert coverage.object_coverage == 1.0

    _save_api_reference(repo, output_dir)
    html_path = output_dir / "pdmpkg-api.html"
    api_path = output_dir / "pdmpkg-api.json"
    coverage_path = output_dir / "pdmpkg-api-coverage.json"

    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "pdmpkg.run" in html
    assert "lib.pdmpkg" not in html
    assert_html_internal_links_resolve(html_path)
    rendered_api = ApiPackage.load_json(api_path)
    assert rendered_api.find_object("pdmpkg.run") is not None
    assert rendered_api.find_object("pdmpkg.core.run") is not None
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0


def test_general_flit_package_repo_builds_complete_reference(
    tmp_path: Path,
) -> None:
    repo = write_flit_package_repo(tmp_path)
    output_dir = tmp_path / "flit-output"

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "flitpkg"
    assert api.find_object("flitpkg.run") is not None
    assert api.find_object("flitpkg.core.Runner.run") is not None
    assert api.find_object("straypkg.leak") is None
    assert coverage.object_coverage == 1.0

    _save_api_reference(repo, output_dir)
    html_path = output_dir / "flitpkg-api.html"
    api_path = output_dir / "flitpkg-api.json"
    coverage_path = output_dir / "flitpkg-api-coverage.json"

    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "flitpkg.run" in html
    assert "straypkg" not in html
    assert_html_internal_links_resolve(html_path)
    rendered_api = ApiPackage.load_json(api_path)
    assert rendered_api.find_object("flitpkg.run") is not None
    assert rendered_api.find_object("flitpkg.core.Runner.run") is not None
    assert rendered_api.find_object("straypkg.leak") is None
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0


def test_general_import_names_package_repo_builds_complete_reference(
    tmp_path: Path,
) -> None:
    repo = write_import_names_package_repo(tmp_path, source_root="lib")
    output_dir = tmp_path / "import-names-output"

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "importnamedpkg"
    assert api.find_object("importnamedpkg.run") is not None
    assert api.find_object("lib.importnamedpkg.run") is None
    assert api.find_object("straypkg.leak") is None
    assert coverage.object_coverage == 1.0

    _save_api_reference(repo, output_dir)
    html_path = output_dir / "importnamedpkg-api.html"
    api_path = output_dir / "importnamedpkg-api.json"
    coverage_path = output_dir / "importnamedpkg-api-coverage.json"

    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "importnamedpkg.run" in html
    assert "straypkg" not in html
    assert_html_internal_links_resolve(html_path)
    rendered_api = ApiPackage.load_json(api_path)
    assert rendered_api.find_object("importnamedpkg.run") is not None
    assert rendered_api.find_object("lib.importnamedpkg.run") is None
    assert rendered_api.find_object("straypkg.leak") is None
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0


@pytest.mark.parametrize(
    (
        "writer",
        "expected_package",
        "expected_qualnames",
        "forbidden_qualnames",
        "forbidden_html",
    ),
    [
        (
            write_poetry_package_repo,
            "poetrypkg",
            ("poetrypkg.run", "poetrypkg.core.run"),
            ("lib.poetrypkg.run",),
            ("lib.poetrypkg",),
        ),
        (
            write_pdm_module_file_repo,
            "pdmrunner",
            ("pdmrunner.Client.connect", "pdmrunner.stream"),
            ("pdm_module_repo.pdmrunner.Client",),
            ("pdm_module_repo.pdmrunner",),
        ),
        (
            write_flit_module_file_repo,
            "flitrunner",
            ("flitrunner.Client.connect", "flitrunner.connect"),
            ("helper.leak",),
            ("helper.leak",),
        ),
        (
            write_import_names_module_file_repo,
            "importnamedrunner",
            ("importnamedrunner.run",),
            ("helper.leak",),
            ("helper.leak",),
        ),
    ],
)
def test_general_packaging_variants_build_complete_cli_reference(
    tmp_path: Path,
    writer,
    expected_package: str,
    expected_qualnames: tuple[str, ...],
    forbidden_qualnames: tuple[str, ...],
    forbidden_html: tuple[str, ...],
) -> None:
    repo = writer(tmp_path)
    output_dir = tmp_path / f"{expected_package}-output"

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == expected_package
    for qualname in expected_qualnames:
        assert api.find_object(qualname) is not None
    for qualname in forbidden_qualnames:
        assert api.find_object(qualname) is None
    assert coverage.object_coverage == 1.0

    _save_api_reference(
        repo,
        output_dir,
        output_formats=("docx", "pdf", "html"),
    )
    docx_path = output_dir / f"{expected_package}-api.docx"
    pdf_path = output_dir / f"{expected_package}-api.pdf"
    html_path = output_dir / f"{expected_package}-api.html"
    api_path = output_dir / f"{expected_package}-api.json"
    coverage_path = output_dir / f"{expected_package}-api-coverage.json"

    assert_rendered_bundle(docx_path, pdf_path, html_path)
    assert api_path.exists()
    assert coverage_path.exists()
    assert_docx_structure(
        docx_path,
        required_paragraphs=(
            f"{expected_package} API Reference",
            "1 API Contents",
            "2 Public API",
            "3 API Documentation Coverage",
        ),
        min_tables=2,
    )
    assert_pdf_text_and_pages(
        pdf_path,
        required_text=(
            f"{expected_package} API Reference",
            "API Documentation Coverage",
            *expected_qualnames,
        ),
        min_pages=1,
    )
    html = html_path.read_text(encoding="utf-8")
    for qualname in expected_qualnames:
        assert qualname in html
    for text in forbidden_html:
        assert text not in html
    assert_html_internal_links_resolve(html_path)
    rendered_api = ApiPackage.load_json(api_path)
    for qualname in expected_qualnames:
        assert rendered_api.find_object(qualname) is not None
    for qualname in forbidden_qualnames:
        assert rendered_api.find_object(qualname) is None
    assert ApiCoverageResult.load_json(coverage_path).object_coverage == 1.0


def test_api_objects_example_config_loads_repo_docstring_parser_modules(
    tmp_path: Path,
) -> None:
    repo = write_custom_docstring_parser_repo(tmp_path)
    build_config = ApiHelpBookConfig.from_pyproject(repo)
    output_dir = tmp_path / "custom-parser-example"
    example = _load_api_objects_example()

    assert build_config.collection.docstring_parser_modules == (
        "example_brief_parsers",
    )
    assert build_config.collection.docstring_parser().style == "example-brief"

    example.main(
        [
            str(repo),
            "--config",
            str(repo / "pyproject.toml"),
            "--out",
            str(output_dir),
            "--quiet",
        ]
    )

    help_book = output_dir / "oodocs-api-reference.html"
    api_object_tree_json = output_dir / "oodocs-api-object-tree.json"
    api_coverage_json = output_dir / "oodocs-api-coverage.json"
    assert help_book.exists()
    assert api_object_tree_json.exists()
    assert api_coverage_json.exists()
    assert not (output_dir / "oodocs-api-reference.docx").exists()

    api = ApiPackage.load_json(api_object_tree_json)
    runner = api.find_object("briefpkg.Runner")
    run = api.find_object("briefpkg.run")
    assert runner is not None
    assert runner.summary == "brief:Runner class."
    assert run is not None
    assert run.summary == "brief:Run custom command."
    assert ApiCoverageResult.load_json(api_coverage_json).object_coverage == 1.0

    html = help_book.read_text(encoding="utf-8")
    assert "brief:Runner class." in html
    assert "brief:Run custom command." in html
    assert_html_internal_links_resolve(help_book)


def test_api_objects_example_external_json_config_loads_target_parser_modules(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "external-example-config-repo"
    package_dir = repo / "src" / "examplejsonpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "examplejsonpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "example_json_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_example_json_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"example-json:{first}", style="example-json-brief")',
                "",
                'if "example-json-brief" not in docstring_parser_names():',
                '    register_docstring_parser("example-json-brief", parse_example_json_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Example JSON package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run from the example external config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "generated-example-apidoc.json"
    output_dir = tmp_path / "external-example-config-output"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "example-json-brief",
                "docstring_parser_modules": ["example_json_parsers"],
                "presentation": "compact",
                "output_formats": ["html"],
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    example = _load_api_objects_example()

    example.main(
        [
            str(repo),
            "--config",
            str(config_path),
            "--out",
            str(output_dir),
            "--quiet",
        ]
    )

    help_book = output_dir / "oodocs-api-reference.html"
    api_object_tree_json = output_dir / "oodocs-api-object-tree.json"
    api_coverage_json = output_dir / "oodocs-api-coverage.json"
    assert help_book.exists()
    assert api_object_tree_json.exists()
    assert api_coverage_json.exists()

    api = ApiPackage.load_json(api_object_tree_json)
    run = api.find_object("examplejsonpkg.run")

    assert run is not None
    assert run.summary == "example-json:Run from the example external config."
    assert ApiCoverageResult.load_json(api_coverage_json).object_coverage == 1.0
    assert_html_internal_links_resolve(
        help_book,
        required_text=("example-json:Run from the example external config.",),
    )


def test_build_config_save_all_targets_repo_with_parser_modules(
    tmp_path: Path,
) -> None:
    repo = write_custom_docstring_parser_repo(tmp_path)
    config_path = tmp_path / "external-brief-build.json"
    output_dir = tmp_path / "brief-build-output"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "example-brief",
                "docstring_parser_modules": ["example_brief_parsers"],
                "presentation": "compact",
                "output_formats": ["docx", "pdf", "html"],
                "output_dir": str(output_dir),
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    build = ApiHelpBookConfig.load_file(config_path, target=repo)
    api = build.collect(repo)
    coverage = build.check_docs(repo, fail_under=1.0)
    snapshot = build.snapshot(repo)
    snapshot_path = build.save_snapshot(repo, tmp_path / "brief-snapshot.json")
    document = build.to_help_book(repo)
    outputs = build.save_all(repo)
    run = api.find_object("briefpkg.run")

    assert build.collection.docstring_parser().style == "example-brief"
    assert run is not None
    assert run.summary == "brief:Run custom command."
    assert coverage.object_coverage == 1.0
    assert snapshot.objects["briefpkg.run"]["summary"] == "brief:Run custom command."
    assert ApiSnapshot.load_json(snapshot_path).objects["briefpkg.run"]["summary"] == (
        "brief:Run custom command."
    )
    assert document.validate(formats=("docx", "pdf", "html")).ok
    assert outputs["docx"] == output_dir / "briefpkg-api.docx"
    assert outputs["pdf"] == output_dir / "briefpkg-api.pdf"
    assert outputs["html"] == output_dir / "briefpkg-api.html"
    assert outputs["api-json"] == output_dir / "briefpkg-api.json"
    assert outputs["coverage-json"] == output_dir / "briefpkg-api-coverage.json"
    assert outputs["coverage-csv"] == output_dir / "briefpkg-api-coverage.csv"
    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "briefpkg API Reference",
            "1 API Contents",
            "2 Public API",
            "2.1 briefpkg.Runner",
            "2.2 briefpkg.run",
            "3 API Documentation Coverage",
        ),
        min_tables=2,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "briefpkg API Reference",
            "API Documentation Coverage",
            "brief:Runner class.",
            "brief:Run custom command.",
        ),
        min_pages=1,
    )
    assert_html_internal_links_resolve(
        outputs["html"],
        required_text=("brief:Run custom command.",),
    )
    saved_api = ApiPackage.load_json(outputs["api-json"])
    saved_run = saved_api.find_object("briefpkg.run")
    assert saved_run is not None
    assert saved_run.summary == "brief:Run custom command."
    assert ApiCoverageResult.load_json(outputs["coverage-json"]).object_coverage == coverage.object_coverage


def test_collect_api_loads_repo_local_docstring_parser_modules(
    tmp_path: Path,
) -> None:
    repo = write_custom_docstring_parser_repo(tmp_path)

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_parser_modules=("example_brief_parsers",),
        docstring_style="example-brief",
    )
    runner = api.find_object("briefpkg.Runner")
    run = api.find_object("briefpkg.run")

    assert runner is not None
    assert runner.summary == "brief:Runner class."
    assert run is not None
    assert run.summary == "brief:Run custom command."


def test_collect_api_accepts_config_with_repo_local_parser_modules(
    tmp_path: Path,
) -> None:
    repo = write_custom_docstring_parser_repo(tmp_path)

    with docstring_parser_import_paths(repo):
        config = ApiCollectConfig(
            collector="inspect",
            public_policy="__all__",
            docstring_parser_modules=("example_brief_parsers",),
            docstring_style="example-brief",
        )

    api = collect_api(repo, config=config)
    run = api.find_object("briefpkg.run")

    assert run is not None
    assert run.summary == "brief:Run custom command."
