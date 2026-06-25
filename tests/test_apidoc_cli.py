from __future__ import annotations

import json

from apidoc_samples import (
    write_custom_docstring_parser_repo,
    write_private_package,
    write_sample_package,
    write_setuptools_package_dir_repo,
)
from example_regression import (
    assert_docx_structure,
    assert_html_internal_links_resolve,
    assert_pdf_text_and_pages,
    assert_rendered_bundle,
)
import pytest

from oodocs.apidoc import (
    ApiBuildConfig,
    ApiCoverageResult,
    ApiPackage,
    docstring_parser_names,
)
from oodocs.cli import main


def test_apidoc_cli_builds_html_and_sidecars_for_general_repo(tmp_path) -> None:
    package_dir = write_sample_package(tmp_path)
    output_dir = tmp_path / "api"

    assert (
        main(
            [
                "apidoc",
                "build",
                str(package_dir),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--out",
                str(output_dir),
                "--to",
                "html",
                "--sidecars",
            ]
        )
        == 0
    )

    assert (output_dir / "samplepkg-api.html").exists()
    api = ApiPackage.read_json(output_dir / "samplepkg-api.json")
    render = api.find("samplepkg.Widget.render")

    assert api.name == "samplepkg"
    assert render is not None
    assert render.examples
    assert render.examples[0].syntax_ok is True
    assert render.examples[0].doctest_ok is True


def test_apidoc_cli_builds_full_reference_bundle_from_json_config(tmp_path) -> None:
    package_dir = write_sample_package(tmp_path)
    output_dir = tmp_path / "reference-api"
    config_path = tmp_path / "apidoc-build.json"
    ApiBuildConfig.from_dict(
        {
            "collector": "inspect",
            "public_policy": "__all__",
            "docstring_style": "google",
            "profile": "compact",
            "formats": ["docx", "pdf", "html"],
            "out": str(output_dir),
            "stem": "sample-reference",
            "sidecars": True,
        }
    ).write_json(config_path)

    assert (
        main(
            [
                "apidoc",
                "build",
                str(package_dir),
                "--config",
                str(config_path),
            ]
        )
        == 0
    )

    docx_path = output_dir / "sample-reference.docx"
    pdf_path = output_dir / "sample-reference.pdf"
    html_path = output_dir / "sample-reference.html"
    api_path = output_dir / "sample-reference.json"
    coverage_json_path = output_dir / "sample-reference-coverage.json"
    coverage_csv_path = output_dir / "sample-reference-coverage.csv"

    assert_rendered_bundle(docx_path, pdf_path, html_path)
    assert api_path.exists()
    assert coverage_json_path.exists()
    assert coverage_csv_path.exists()
    assert_docx_structure(
        docx_path,
        required_paragraphs=(
            "samplepkg API Reference",
            "1 API Documentation Coverage",
            "2 samplepkg",
            "2.1 samplepkg.CONSTANT",
            "2.2 samplepkg.Widget",
            "2.3 samplepkg.make_widget",
        ),
        min_tables=4,
    )
    assert_pdf_text_and_pages(
        pdf_path,
        required_text=(
            "samplepkg API Reference",
            "samplepkg.Widget",
            "samplepkg.make_widget",
        ),
        min_pages=1,
    )
    assert_html_internal_links_resolve(
        html_path,
        required_text=(
            "samplepkg API Reference",
            "samplepkg.Widget",
            "samplepkg.make_widget",
        ),
    )

    api = ApiPackage.read_json(api_path)
    coverage = ApiCoverageResult.read_json(coverage_json_path)
    render = api.find("samplepkg.Widget.render")

    assert api.name == "samplepkg"
    assert api.find("samplepkg.Widget") is not None
    assert render is not None
    assert render.examples[0].syntax_ok is True
    assert render.examples[0].doctest_ok is True
    assert coverage.package == "samplepkg"
    assert coverage.public_object_count == 7
    assert coverage.documented_object_count == 6
    assert any(
        issue.code == "missing-docstring" and issue.qualname == "samplepkg.CONSTANT"
        for issue in coverage.issues
    )
    assert coverage_csv_path.read_text(encoding="utf-8").startswith(
        "severity,code,qualname,module,path,line_number,message"
    )


def test_apidoc_cli_json_config_loads_repo_local_parser_modules(tmp_path) -> None:
    repo = tmp_path / "json-config-repo"
    package_dir = repo / "src" / "jsonpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "jsonpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "json_config_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_json_config_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"json:{first}", style="json-config-brief")',
                "",
                'if "json-config-brief" not in docstring_parser_names():',
                '    register_docstring_parser("json-config-brief", parse_json_config_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""JSON config package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run from JSON config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "json-config-api"
    config_path = repo / "apidoc-build.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "json-config-brief",
                "docstring_parser_modules": ["json_config_parsers"],
                "profile": "compact",
                "formats": ["html"],
                "out": str(output_dir),
                "stem": "jsonpkg-api",
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "json-config-brief" not in docstring_parser_names()
    assert main(["apidoc", "build", str(repo), "--config", str(config_path)]) == 0

    html_path = output_dir / "jsonpkg-api.html"
    api_path = output_dir / "jsonpkg-api.json"
    coverage_path = output_dir / "jsonpkg-api-coverage.json"
    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    assert_html_internal_links_resolve(
        html_path,
        required_text=("json:Run from JSON config.",),
    )

    api = ApiPackage.read_json(api_path)
    run = api.find("jsonpkg.run")
    coverage = ApiCoverageResult.read_json(coverage_path)

    assert run is not None
    assert run.summary == "json:Run from JSON config."
    assert coverage.package == "jsonpkg"
    assert coverage.object_coverage == 1.0


def test_apidoc_cli_external_json_config_loads_target_parser_modules(tmp_path) -> None:
    repo = tmp_path / "external-json-repo"
    package_dir = repo / "src" / "externaljsonpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "externaljsonpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "external_json_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_external_json_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"target:{first}", style="external-json-brief")',
                "",
                'if "external-json-brief" not in docstring_parser_names():',
                '    register_docstring_parser("external-json-brief", parse_external_json_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""External JSON config package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run from external JSON config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "external-json-api"
    config_path = tmp_path / "generated-apidoc-build.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "external-json-brief",
                "docstring_parser_modules": ["external_json_parsers"],
                "profile": "compact",
                "formats": ["html"],
                "out": str(output_dir),
                "stem": "externaljsonpkg-api",
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "external-json-brief" not in docstring_parser_names()
    assert main(["apidoc", "build", str(repo), "--config", str(config_path)]) == 0

    html_path = output_dir / "externaljsonpkg-api.html"
    api = ApiPackage.read_json(output_dir / "externaljsonpkg-api.json")
    run = api.find("externaljsonpkg.run")

    assert_html_internal_links_resolve(
        html_path,
        required_text=("target:Run from external JSON config.",),
    )
    assert run is not None
    assert run.summary == "target:Run from external JSON config."
    assert (
        ApiCoverageResult.read_json(
            output_dir / "externaljsonpkg-api-coverage.json"
        ).object_coverage
        == 1.0
    )


def test_apidoc_cli_external_json_config_loads_griffe_target_parser_modules(
    tmp_path,
) -> None:
    pytest.importorskip("griffe")
    repo = tmp_path / "external-griffe-json-repo"
    package_dir = repo / "src" / "externalgriffepkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "externalgriffepkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "external_griffe_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_external_griffe_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"griffe-json:{first}", style="external-griffe-json-brief")',
                "",
                'if "external-griffe-json-brief" not in docstring_parser_names():',
                '    register_docstring_parser("external-griffe-json-brief", parse_external_griffe_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""External griffe JSON config package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run from external griffe JSON config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "external-griffe-json-api"
    config_path = tmp_path / "generated-griffe-apidoc-build.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "griffe",
                "public_policy": "__all__",
                "docstring_style": "external-griffe-json-brief",
                "docstring_parser_modules": ["external_griffe_parsers"],
                "profile": "compact",
                "formats": ["html"],
                "out": str(output_dir),
                "stem": "externalgriffepkg-api",
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "external-griffe-json-brief" not in docstring_parser_names()
    assert main(["apidoc", "build", str(repo), "--config", str(config_path)]) == 0

    html_path = output_dir / "externalgriffepkg-api.html"
    api = ApiPackage.read_json(output_dir / "externalgriffepkg-api.json")
    run = api.find("externalgriffepkg.run")

    assert api.metadata["collector"] == "griffe"
    assert_html_internal_links_resolve(
        html_path,
        required_text=("griffe-json:Run from external griffe JSON config.",),
    )
    assert run is not None
    assert run.summary == "griffe-json:Run from external griffe JSON config."
    assert (
        ApiCoverageResult.read_json(
            output_dir / "externalgriffepkg-api-coverage.json"
        ).object_coverage
        == 1.0
    )


def test_apidoc_cli_collect_external_json_config_loads_target_parser_modules(
    tmp_path,
) -> None:
    repo = tmp_path / "external-json-collect-repo"
    package_dir = repo / "src" / "collectjsonpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "collectjsonpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "collect_json_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_collect_json_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"collect:{first}", style="external-json-collect-brief")',
                "",
                'if "external-json-collect-brief" not in docstring_parser_names():',
                '    register_docstring_parser("external-json-collect-brief", parse_collect_json_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Collect JSON config package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Collect from external JSON config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "collect-apidoc-config.json"
    output_path = tmp_path / "collectjsonpkg-api.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "external-json-collect-brief",
                "docstring_parser_modules": ["collect_json_parsers"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "external-json-collect-brief" not in docstring_parser_names()
    assert (
        main(
            [
                "apidoc",
                "collect",
                str(repo),
                "--config",
                str(config_path),
                "--out",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_path)
    run = api.find("collectjsonpkg.run")

    assert run is not None
    assert run.summary == "collect:Collect from external JSON config."


def test_apidoc_cli_builds_setuptools_package_dir_repo(tmp_path) -> None:
    repo = write_setuptools_package_dir_repo(tmp_path)
    output_dir = tmp_path / "api"

    assert (
        main(
            [
                "apidoc",
                "build",
                str(repo),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--out",
                str(output_dir),
                "--to",
                "html",
                "--sidecars",
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_dir / "samplepkg-api.json")

    assert (output_dir / "samplepkg-api.html").exists()
    assert api.find("samplepkg.run") is not None
    assert api.find("lib.samplepkg.run") is None


def test_apidoc_cli_build_respects_explicit_public_policy(tmp_path) -> None:
    package_dir = write_sample_package(tmp_path)
    output_dir = tmp_path / "explicit-api"

    assert (
        main(
            [
                "apidoc",
                "build",
                str(package_dir),
                "--collector",
                "inspect",
                "--public-policy",
                "explicit",
                "--explicit-name",
                "samplepkg.make_widget",
                "--out",
                str(output_dir),
                "--to",
                "html",
                "--sidecars",
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_dir / "samplepkg-api.json")
    html = (output_dir / "samplepkg-api.html").read_text(encoding="utf-8")

    assert api.metadata["public_policy"] == "explicit"
    assert api.find("samplepkg.make_widget") is not None
    assert api.find("samplepkg.Widget") is None
    assert api.find("samplepkg.CONSTANT") is None
    assert 'id="samplepkg-make_widget"' in html
    assert 'id="samplepkg-widget"' not in html


def test_apidoc_cli_passes_fallback_collector_to_collection(
    tmp_path,
    monkeypatch,
) -> None:
    griffe = pytest.importorskip("griffe")
    package_dir = write_sample_package(tmp_path, name="strictcli")
    output_path = tmp_path / "strictcli-api.json"

    def fail_load(*args, **kwargs):
        raise RuntimeError("forced griffe failure")

    monkeypatch.setattr(griffe, "load", fail_load)

    assert (
        main(
            [
                "apidoc",
                "collect",
                str(package_dir),
                "--collector",
                "griffe",
                "--fallback-collector",
                "none",
                "--public-policy",
                "underscore",
                "--out",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_path)
    assert api.name == "strictcli"
    assert not api.modules
    assert api.metadata["fallback_collector"] == "none"
    assert any(
        issue.severity == "error" and issue.code == "griffe-load-failed"
        for issue in api.issues
    )


def test_apidoc_cli_can_exclude_member_kinds(tmp_path) -> None:
    package_dir = write_sample_package(tmp_path)
    output_path = tmp_path / "samplepkg-api.json"

    assert (
        main(
            [
                "apidoc",
                "collect",
                str(package_dir),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--no-attributes",
                "--no-properties",
                "--no-methods",
                "--out",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_path)
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.make_widget") is not None
    assert api.find("samplepkg.CONSTANT") is None
    assert api.find("samplepkg.Widget.label") is None
    assert api.find("samplepkg.Widget.title") is None
    assert api.find("samplepkg.Widget.render") is None


def test_apidoc_cli_can_strip_source_locations(tmp_path) -> None:
    package_dir = write_sample_package(tmp_path)
    output_path = tmp_path / "samplepkg-api.json"

    assert (
        main(
            [
                "apidoc",
                "collect",
                str(package_dir),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--no-source-locations",
                "--out",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_path)
    widget = api.find("samplepkg.Widget")

    assert api.metadata.get("source_root") is None
    assert api.modules[0].source_path is None
    assert widget is not None
    assert widget.source_path is None
    assert widget.line_number is None


def test_apidoc_cli_can_include_private_objects(tmp_path) -> None:
    package_dir = write_private_package(tmp_path)
    output_path = tmp_path / "privatepkg-api.json"

    assert (
        main(
            [
                "apidoc",
                "collect",
                str(package_dir),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--include-private",
                "--out",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_path)
    helper = api.find("privatepkg._helper")
    debug = api.find("privatepkg.PublicWidget._debug")
    assert helper is not None
    assert helper.visibility == "protected"
    assert debug is not None
    assert debug.visibility == "protected"


def test_apidoc_cli_loads_repo_local_docstring_parser_module_option(
    tmp_path,
) -> None:
    repo = write_custom_docstring_parser_repo(tmp_path)
    output_path = tmp_path / "briefpkg-api.json"

    assert (
        main(
            [
                "apidoc",
                "collect",
                str(repo),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--docstring-parser-module",
                "example_brief_parsers",
                "--docstring-style",
                "example-brief",
                "--out",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.read_json(output_path)
    runner = api.find("briefpkg.Runner")
    function = api.find("briefpkg.run")

    assert runner is not None
    assert runner.summary == "brief:Runner class."
    assert function is not None
    assert function.summary == "brief:Run custom command."
