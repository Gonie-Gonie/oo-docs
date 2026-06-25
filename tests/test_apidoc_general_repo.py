from __future__ import annotations

import importlib.util
from pathlib import Path

from apidoc_samples import (
    write_custom_docstring_parser_repo,
    write_mixed_docstring_repo,
    write_single_file_module,
)
from example_regression import assert_html_internal_links_resolve
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import (
    ApiBuildConfig,
    ApiCoverageResult,
    ApiDocstringParser,
    ApiPackage,
    api_coverage_to_chapter,
    api_objects_to_chapter,
    api_objects_to_summary_table,
    api_package_to_document,
    check_api_docs,
    collect_api,
)
from oodocs.apidoc.cli import main


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


def test_general_repo_auto_parser_objects_compose_into_document(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    parser = ApiDocstringParser.auto()

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=parser,
    )
    client = api.find("mixedpkg.Client")
    method = api.find("mixedpkg.Client.connect")
    function = api.find("mixedpkg.connect")
    stream = api.find("mixedpkg.stream")
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
            client.to_section(level=2, profile="manual"),
        ),
        Chapter(
            "Function Index",
            api.to_summary_table(api.functions(), profile="compact"),
        ),
        Chapter("Coverage", coverage.to_table()),
    )

    outputs = document.save_all(
        tmp_path / "rendered",
        stem="mixed-api",
        formats=("html",),
    )

    html = outputs["html"].read_text(encoding="utf-8")
    assert "mixedpkg.Client" in html
    assert "Timeout in seconds." in html
    assert "Object coverage" in html


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
            api.select(kind="class", module_prefix="mixedpkg"),
            profile="manual",
            max_level=3,
        ),
        Chapter(
            "Function Summary",
            api_objects_to_summary_table(
                api.functions(),
                profile="compact",
                caption="Mixed package functions.",
            ),
        ),
        api_coverage_to_chapter(coverage),
    )

    outputs = document.save_all(
        tmp_path / "helper-rendered",
        stem="mixed-helper-api",
        formats=("html",),
    )
    html = outputs["html"].read_text(encoding="utf-8")

    assert document.validate(formats=("html",)).ok
    assert "Client Classes" in html
    assert "mixedpkg.Client" in html
    assert "Mixed package functions." in html
    assert "API Documentation Coverage" in html


def test_general_repo_package_render_helper_builds_complete_reference(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )

    document = api_package_to_document(api, profile="compact", max_level=3)
    outputs = document.save_all(
        tmp_path / "package-rendered",
        stem="mixedpkg-api",
        formats=("html",),
    )
    html = outputs["html"].read_text(encoding="utf-8")

    assert document.validate(formats=("html",)).ok
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
            "--to",
            "html",
            "--out",
            str(output_dir),
            "--quiet",
        ]
    )

    full_reference = output_dir / "oodocs-full-api-reference.html"
    composition = output_dir / "oodocs-api-objects.html"
    api_json = output_dir / "oodocs-api-objects.json"
    coverage_json = output_dir / "oodocs-api-coverage.json"

    assert full_reference.exists()
    assert composition.exists()
    assert api_json.exists()
    assert coverage_json.exists()
    rendered_api = ApiPackage.read_json(api_json)
    rendered_method = rendered_api.find("mixedpkg.Client.connect")
    assert rendered_api.name == "mixedpkg"
    assert rendered_method is not None
    assert rendered_method.metadata["docstring_style"] == "numpy"
    assert rendered_method.parameters[0].description == "Timeout in seconds."
    assert ApiCoverageResult.read_json(coverage_json).object_coverage == 1.0

    html = full_reference.read_text(encoding="utf-8")
    assert "mixedpkg API Reference" in html
    assert "mixedpkg.Client" in html
    assert "mixedpkg.connect" in html
    assert_html_internal_links_resolve(full_reference)


def test_general_repo_pyproject_auto_parser_builds_cli_bundle(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    build_config = ApiBuildConfig.from_pyproject(repo)
    parser = build_config.collection.docstring_parser()
    output_dir = tmp_path / "bundle"
    example_output_dir = tmp_path / "example-config-bundle"
    example = _load_api_objects_example()

    assert parser == ApiDocstringParser.auto()
    assert parser.detect("Parameters\n----------\ntimeout : float\n    Timeout.") == "numpy"
    assert build_config.module_prefix == "mixedpkg"

    api = collect_api(repo, config=build_config.collection)
    method = api.find("mixedpkg.Client.connect")
    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"

    assert (
        main(
            [
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

    rendered_api = ApiPackage.read_json(api_path)
    rendered_method = rendered_api.find("mixedpkg.Client.connect")
    assert rendered_method is not None
    assert rendered_method.metadata["docstring_style"] == "numpy"
    assert ApiCoverageResult.read_json(coverage_path).object_coverage == 1.0

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

    example_html = example_output_dir / "oodocs-full-api-reference.html"
    example_api_path = example_output_dir / "oodocs-api-objects.json"
    example_coverage_path = example_output_dir / "oodocs-api-coverage.json"
    assert example_html.exists()
    assert example_api_path.exists()
    assert example_coverage_path.exists()
    assert not (example_output_dir / "oodocs-full-api-reference.docx").exists()
    assert not (example_output_dir / "oodocs-full-api-reference.pdf").exists()
    assert_html_internal_links_resolve(example_html)

    example_api = ApiPackage.read_json(example_api_path)
    example_method = example_api.find("mixedpkg.Client.connect")
    assert example_method is not None
    assert example_method.metadata["docstring_style"] == "numpy"
    assert ApiCoverageResult.read_json(example_coverage_path).object_coverage == 1.0


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
    client = api.find("singlemod.Client")
    method = api.find("singlemod.Client.connect")
    function = api.find("singlemod.connect")
    stream = api.find("singlemod.stream")
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
            client.to_section(level=2, profile="manual"),
        ),
        Chapter(
            "Function Index",
            api.to_summary_table(api.functions(), profile="compact"),
        ),
    )
    outputs = document.save_all(
        composed_output,
        stem="single-file-api",
        formats=("html",),
    )
    assert "singlemod.Client" in outputs["html"].read_text(encoding="utf-8")
    assert_html_internal_links_resolve(outputs["html"])

    assert (
        main(
            [
                "build",
                str(module_path),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--docstring-style",
                "auto",
                "--out",
                str(cli_output),
                "--to",
                "html",
                "--sidecars",
            ]
        )
        == 0
    )
    cli_html = cli_output / "singlemod-api.html"
    cli_api_json = cli_output / "singlemod-api.json"
    cli_coverage_json = cli_output / "singlemod-api-coverage.json"
    assert cli_html.exists()
    assert cli_api_json.exists()
    assert cli_coverage_json.exists()
    assert_html_internal_links_resolve(cli_html)
    assert (
        ApiPackage.read_json(cli_api_json).find("singlemod.Client.connect")
        is not None
    )
    assert ApiCoverageResult.read_json(cli_coverage_json).object_coverage == 1.0

    example.main(
        [
            str(module_path),
            "--collector",
            "inspect",
            "--public-policy",
            "__all__",
            "--docstring-style",
            "auto",
            "--to",
            "html",
            "--out",
            str(example_output),
            "--quiet",
        ]
    )
    example_html = example_output / "oodocs-full-api-reference.html"
    example_api_json = example_output / "oodocs-api-objects.json"
    assert example_html.exists()
    assert example_api_json.exists()
    assert "singlemod.Client" in example_html.read_text(encoding="utf-8")
    assert_html_internal_links_resolve(example_html)
    assert ApiPackage.read_json(example_api_json).find("singlemod.stream") is not None


def test_api_objects_example_config_loads_repo_docstring_parser_modules(
    tmp_path: Path,
) -> None:
    repo = write_custom_docstring_parser_repo(tmp_path)
    build_config = ApiBuildConfig.from_pyproject(repo)
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

    full_reference = output_dir / "oodocs-full-api-reference.html"
    api_json = output_dir / "oodocs-api-objects.json"
    coverage_json = output_dir / "oodocs-api-coverage.json"
    assert full_reference.exists()
    assert api_json.exists()
    assert coverage_json.exists()
    assert not (output_dir / "oodocs-full-api-reference.docx").exists()

    api = ApiPackage.read_json(api_json)
    runner = api.find("briefpkg.Runner")
    run = api.find("briefpkg.run")
    assert runner is not None
    assert runner.summary == "brief:Runner class."
    assert run is not None
    assert run.summary == "brief:Run custom command."
    assert ApiCoverageResult.read_json(coverage_json).object_coverage == 1.0

    html = full_reference.read_text(encoding="utf-8")
    assert "brief:Runner class." in html
    assert "brief:Run custom command." in html
    assert_html_internal_links_resolve(full_reference)
