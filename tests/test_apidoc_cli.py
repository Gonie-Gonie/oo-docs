from __future__ import annotations

from apidoc_samples import (
    write_custom_docstring_parser_repo,
    write_private_package,
    write_sample_package,
    write_setuptools_package_dir_repo,
)
import pytest

from oodocs.apidoc import ApiPackage
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
