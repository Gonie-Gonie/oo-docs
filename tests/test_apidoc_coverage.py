from __future__ import annotations

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
