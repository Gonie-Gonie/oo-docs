from __future__ import annotations

from textwrap import dedent

import pytest

from apidoc_samples import write_undocumented_package
from oodocs.apidoc import collect_api
from oodocs.apidoc.coverage import ApiCoverageResult, check_api_docs
from oodocs.components.media import Table


def test_apidoc_coverage_detects_missing_docs_and_serializes(tmp_path) -> None:
    package_dir = write_undocumented_package(tmp_path)
    api = collect_api(package_dir, collector="inspect", public_policy="underscore")
    coverage = check_api_docs(api)

    assert coverage.undocumented_object_count >= 1
    assert any(issue.code == "missing-docstring" for issue in coverage.issues)
    assert ApiCoverageResult.from_dict(coverage.to_dict()).package == "undocpkg"
    assert isinstance(coverage.to_table(), Table)


def test_apidoc_coverage_uses_dataclass_attribute_docs_for_constructor_parameters(
    tmp_path,
) -> None:
    pytest.importorskip("griffe")
    package_dir = tmp_path / "datapkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            from dataclasses import dataclass

            __all__ = ["Settings"]

            @dataclass(slots=True)
            class Settings:
                """Runtime settings.

                Attributes:
                    path: Output path.
                    retries: Retry count.
                """

                path: str
                retries: int = 3
            '''
        ),
        encoding="utf-8",
    )

    api = collect_api(package_dir, collector="griffe", public_policy="__all__")
    settings = api.find("datapkg.Settings")
    coverage = check_api_docs(api)

    assert settings is not None
    assert {parameter.name for parameter in settings.parameters} >= {"path", "retries"}
    assert all(parameter.documented for parameter in settings.parameters)
    assert not [
        issue
        for issue in coverage.issues
        if issue.qualname == "datapkg.Settings"
        and issue.code == "missing-parameter-doc"
    ]
