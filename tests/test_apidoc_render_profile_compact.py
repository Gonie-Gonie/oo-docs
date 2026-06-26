from __future__ import annotations

from apidoc_samples import collect_sample_api


def test_compact_profile_builds_valid_document(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    document = api.to_document(presentation="compact", max_level=2)

    assert document.validate(formats=("html",)).ok
    assert api.find_object("samplepkg.Widget").to_section(presentation="compact") is not None
