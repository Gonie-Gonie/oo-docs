from __future__ import annotations

from oodocs.apidoc import ApiDocProfile, profile_names, resolve_profile


def test_apidoc_styles_resolve_all_standard_profiles() -> None:
    expected = {"reference", "compact", "manual", "evidence", "review", "website"}

    assert expected.issubset(set(profile_names()))
    assert resolve_profile("compact").max_examples == 1
    assert resolve_profile(ApiDocProfile.review()).include_review_notes
    assert ApiDocProfile.from_dict(ApiDocProfile.website().to_dict()).name == "website"
