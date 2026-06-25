from __future__ import annotations

from apidoc_samples import write_sample_package
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
    assert ApiPackage.read_json(output_dir / "samplepkg-api.json").name == "samplepkg"


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
