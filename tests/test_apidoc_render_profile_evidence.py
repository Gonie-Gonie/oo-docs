from __future__ import annotations

from apidoc_samples import collect_sample_api


def test_evidence_profile_builds_valid_coverage_document(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    document = api.to_document(presentation="evidence", include_coverage=True, max_level=2)

    assert document.validate(formats=("html",)).ok
