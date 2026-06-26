from __future__ import annotations

import importlib.util
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
    ApiCollectConfig,
    ApiCoverageResult,
    ApiDiffResult,
    ApiPackage,
    ApiSnapshot,
    docstring_parser_names,
)
from oodocs.cli import main


def test_apidoc_build_config_saves_html_and_sidecars_for_general_repo(tmp_path) -> None:
    package_dir = write_sample_package(tmp_path)
    output_dir = tmp_path / "api"

    ApiBuildConfig(
        collection=ApiCollectConfig(collector="inspect", public_policy="__all__"),
        output_formats=("html",),
        output_dir=str(output_dir),
        sidecars=True,
    ).save_all(package_dir)

    assert (output_dir / "samplepkg-api.html").exists()
    api = ApiPackage.load_json(output_dir / "samplepkg-api.json")
    render = api.find_object("samplepkg.Widget.render")

    assert api.name == "samplepkg"
    assert render is not None
    assert render.examples
    assert render.examples[0].syntax_ok is True
    assert render.examples[0].doctest_ok is True


def test_apidoc_build_config_auto_collector_saves_full_bundle_for_general_repo(
    tmp_path,
) -> None:
    package_dir = write_sample_package(tmp_path)
    output_dir = tmp_path / "auto-api"

    ApiBuildConfig(
        collection=ApiCollectConfig(collector="auto", public_policy="__all__"),
        profile="compact",
        output_formats=("docx", "pdf", "html"),
        output_dir=str(output_dir),
        sidecars=True,
    ).save_all(package_dir)

    docx_path = output_dir / "samplepkg-api.docx"
    pdf_path = output_dir / "samplepkg-api.pdf"
    html_path = output_dir / "samplepkg-api.html"
    api_path = output_dir / "samplepkg-api.json"
    coverage_path = output_dir / "samplepkg-api-coverage.json"

    assert_rendered_bundle(docx_path, pdf_path, html_path)
    assert api_path.exists()
    assert coverage_path.exists()
    assert_docx_structure(
        docx_path,
        required_paragraphs=(
            "samplepkg API Reference",
            "1 API Documentation Coverage",
            "2 samplepkg",
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

    api = ApiPackage.load_json(api_path)
    coverage = ApiCoverageResult.load_json(coverage_path)
    render = api.find_object("samplepkg.Widget.render")

    assert api.metadata["collector"] in {"griffe", "inspect"}
    if importlib.util.find_spec("griffe") is not None:
        assert api.metadata["collector"] == "griffe"
    assert api.find_object("samplepkg.Widget") is not None
    assert render is not None
    assert render.examples
    assert coverage.package == "samplepkg"
    assert coverage.public_object_count >= 1


def test_apidoc_build_config_saves_full_reference_bundle_from_json_config(tmp_path) -> None:
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
    ).save_json(config_path)

    ApiBuildConfig.load_json(config_path).save_all(package_dir)

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

    api = ApiPackage.load_json(api_path)
    coverage = ApiCoverageResult.load_json(coverage_json_path)
    render = api.find_object("samplepkg.Widget.render")

    assert api.name == "samplepkg"
    assert api.find_object("samplepkg.Widget") is not None
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
    ApiBuildConfig.load_file(config_path, target=repo).save_all(repo)

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

    api = ApiPackage.load_json(api_path)
    run = api.find_object("jsonpkg.run")
    coverage = ApiCoverageResult.load_json(coverage_path)

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
    ApiBuildConfig.load_file(config_path, target=repo).save_all(repo)

    html_path = output_dir / "externaljsonpkg-api.html"
    api = ApiPackage.load_json(output_dir / "externaljsonpkg-api.json")
    run = api.find_object("externaljsonpkg.run")

    assert_html_internal_links_resolve(
        html_path,
        required_text=("target:Run from external JSON config.",),
    )
    assert run is not None
    assert run.summary == "target:Run from external JSON config."
    assert (
        ApiCoverageResult.load_json(
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
    ApiBuildConfig.load_file(config_path, target=repo).save_all(repo)

    html_path = output_dir / "externalgriffepkg-api.html"
    api = ApiPackage.load_json(output_dir / "externalgriffepkg-api.json")
    run = api.find_object("externalgriffepkg.run")

    assert api.metadata["collector"] == "griffe"
    assert_html_internal_links_resolve(
        html_path,
        required_text=("griffe-json:Run from external griffe JSON config.",),
    )
    assert run is not None
    assert run.summary == "griffe-json:Run from external griffe JSON config."
    assert (
        ApiCoverageResult.load_json(
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
                "--save-json",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.load_json(output_path)
    run = api.find_object("collectjsonpkg.run")

    assert run is not None
    assert run.summary == "collect:Collect from external JSON config."


def test_apidoc_cli_check_and_snapshot_external_json_config_load_target_parsers(
    tmp_path,
) -> None:
    repo = tmp_path / "external-json-release-repo"
    package_dir = repo / "src" / "releasejsonpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "releasejsonpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "release_json_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_release_json_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"release:{first}", style="release-json-brief")',
                "",
                'if "release-json-brief" not in docstring_parser_names():',
                '    register_docstring_parser("release-json-brief", parse_release_json_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Release JSON config package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run through release commands."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "release-apidoc-config.json"
    coverage_json = tmp_path / "release-coverage.json"
    coverage_csv = tmp_path / "release-coverage.csv"
    snapshot_json = tmp_path / "release-snapshot.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "release-json-brief",
                "docstring_parser_modules": ["release_json_parsers"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "release-json-brief" not in docstring_parser_names()
    assert (
        main(
            [
                "apidoc",
                "check",
                str(repo),
                "--config",
                str(config_path),
                "--save-json",
                str(coverage_json),
                "--save-csv",
                str(coverage_csv),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "apidoc",
                "snapshot",
                str(repo),
                "--config",
                str(config_path),
                "--save-json",
                str(snapshot_json),
            ]
        )
        == 0
    )

    coverage = ApiCoverageResult.load_json(coverage_json)
    snapshot = ApiSnapshot.load_json(snapshot_json)

    assert coverage.package == "releasejsonpkg"
    assert coverage.object_coverage == 1.0
    assert coverage_csv.read_text(encoding="utf-8").startswith(
        "severity,code,qualname,module,path,line_number,message"
    )
    assert snapshot.name == "releasejsonpkg"
    assert snapshot.objects["releasejsonpkg.run"]["summary"] == (
        "release:Run through release commands."
    )


def test_apidoc_cli_diff_saves_json_report(tmp_path, capsys) -> None:
    base_package = tmp_path / "base" / "diffpkg"
    head_package = tmp_path / "head" / "diffpkg"
    base_package.mkdir(parents=True)
    head_package.mkdir(parents=True)
    base_snapshot = tmp_path / "api-base.json"
    head_snapshot = tmp_path / "api-head.json"
    diff_path = tmp_path / "api-diff.json"

    (base_package / "__init__.py").write_text(
        "\n".join(
            [
                "def run(path: str) -> str:",
                '    """Run task."""',
                "    return path",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (head_package / "__init__.py").write_text(
        "\n".join(
            [
                "def run(path: str, force: bool = False) -> str:",
                '    """Run task with force."""',
                "    return path",
                "",
                "def added() -> None:",
                '    """Added function."""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "apidoc",
                "snapshot",
                str(base_package),
                "--collector",
                "inspect",
                "--public-policy",
                "underscore",
                "--save-json",
                str(base_snapshot),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "apidoc",
                "snapshot",
                str(head_package),
                "--collector",
                "inspect",
                "--public-policy",
                "underscore",
                "--save-json",
                str(head_snapshot),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "apidoc",
                "diff",
                str(base_snapshot),
                str(head_snapshot),
                "--save-json",
                str(diff_path),
            ]
        )
        == 0
    )

    assert diff_path.exists()

    diff = ApiDiffResult.load_json(diff_path)
    assert [obj.qualname for obj in diff.added] == ["diffpkg.added"]
    assert diff.changed_signatures[0][0].qualname == "diffpkg.run"
    assert diff.changed_docstrings[0][1].summary == "Run task with force."
    assert f"Wrote api-diff: {diff_path}" in capsys.readouterr().out


def test_apidoc_build_config_saves_setuptools_package_dir_repo(tmp_path) -> None:
    repo = write_setuptools_package_dir_repo(tmp_path)
    output_dir = tmp_path / "api"

    ApiBuildConfig(
        collection=ApiCollectConfig(collector="inspect", public_policy="__all__"),
        output_formats=("html",),
        output_dir=str(output_dir),
        sidecars=True,
    ).save_all(repo)

    api = ApiPackage.load_json(output_dir / "samplepkg-api.json")

    assert (output_dir / "samplepkg-api.html").exists()
    assert api.find_object("samplepkg.run") is not None
    assert api.find_object("lib.samplepkg.run") is None


def test_apidoc_build_config_respects_explicit_public_policy(tmp_path) -> None:
    package_dir = write_sample_package(tmp_path)
    output_dir = tmp_path / "explicit-api"

    ApiBuildConfig(
        collection=ApiCollectConfig(
            collector="inspect",
            public_policy="explicit",
            explicit_names=("samplepkg.make_widget",),
        ),
        output_formats=("html",),
        output_dir=str(output_dir),
        sidecars=True,
    ).save_all(package_dir)

    api = ApiPackage.load_json(output_dir / "samplepkg-api.json")
    html = (output_dir / "samplepkg-api.html").read_text(encoding="utf-8")

    assert api.metadata["public_policy"] == "explicit"
    assert api.find_object("samplepkg.make_widget") is not None
    assert api.find_object("samplepkg.Widget") is None
    assert api.find_object("samplepkg.CONSTANT") is None
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
                "--save-json",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.load_json(output_path)
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
                "--save-json",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.load_json(output_path)
    assert api.find_object("samplepkg.Widget") is not None
    assert api.find_object("samplepkg.make_widget") is not None
    assert api.find_object("samplepkg.CONSTANT") is None
    assert api.find_object("samplepkg.Widget.label") is None
    assert api.find_object("samplepkg.Widget.title") is None
    assert api.find_object("samplepkg.Widget.render") is None


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
                "--save-json",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.load_json(output_path)
    widget = api.find_object("samplepkg.Widget")

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
                "--save-json",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.load_json(output_path)
    helper = api.find_object("privatepkg._helper")
    debug = api.find_object("privatepkg.PublicWidget._debug")
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
                "--save-json",
                str(output_path),
            ]
        )
        == 0
    )

    api = ApiPackage.load_json(output_path)
    runner = api.find_object("briefpkg.Runner")
    function = api.find_object("briefpkg.run")

    assert runner is not None
    assert runner.summary == "brief:Runner class."
    assert function is not None
    assert function.summary == "brief:Run custom command."


def test_apidoc_cli_init_loads_repo_local_docstring_parser_module(
    tmp_path,
) -> None:
    repo = tmp_path / "init-custom-parser-repo"
    package_dir = repo / "src" / "initbriefpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "initbriefpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "init_brief_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_init_brief(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"init:{first}", style="init-brief")',
                "",
                'if "init-brief" not in docstring_parser_names():',
                '    register_docstring_parser("init-brief", parse_init_brief)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Init brief package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run through initialized config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "init-config-api"

    assert "init-brief" not in docstring_parser_names()
    assert (
        main(
            [
                "apidoc",
                "init",
                str(repo),
                "--collector",
                "inspect",
                "--public-policy",
                "__all__",
                "--docstring-parser-module",
                "init_brief_parsers",
                "--docstring-style",
                "init-brief",
                "--presentation-profile",
                "compact",
                "--outputs",
                "html",
                "--out-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    build_config = ApiBuildConfig.from_pyproject(repo)

    assert build_config.collection.docstring_parser_modules == ("init_brief_parsers",)
    assert build_config.collection.docstring_parser().style == "init-brief"
    build_config.save_all(repo)

    api = ApiPackage.load_json(output_dir / "initbriefpkg-api.json")
    run = api.find_object("initbriefpkg.run")

    assert run is not None
    assert run.summary == "init:Run through initialized config."
    assert_html_internal_links_resolve(
        output_dir / "initbriefpkg-api.html",
        required_text=("init:Run through initialized config.",),
    )
