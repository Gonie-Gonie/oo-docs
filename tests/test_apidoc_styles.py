from __future__ import annotations

import pytest

from oodocs.apidoc import ApiDocProfile, profile_names, resolve_profile
from oodocs.apidoc.styles import normalize_parameter_columns


def test_apidoc_styles_resolve_all_standard_profiles() -> None:
    expected = {"reference", "compact", "manual", "evidence", "review", "website"}

    assert expected.issubset(set(profile_names()))
    assert resolve_profile("compact").max_examples == 1
    assert resolve_profile(ApiDocProfile.review()).include_review_notes
    assert ApiDocProfile.from_dict(ApiDocProfile.website().to_dict()).name == "website"


def test_apidoc_profile_validates_parameter_columns() -> None:
    profile = ApiDocProfile(
        name="compact",
        parameter_columns=(" Name ", "Required", "source"),
    )

    assert profile.parameter_columns == ("name", "required", "source")
    assert normalize_parameter_columns(("type", "description")) == (
        "type",
        "description",
    )
    with pytest.raises(ValueError, match="Unsupported API parameter columns"):
        ApiDocProfile.from_dict(
            {
                "name": "compact",
                "parameter_columns": ["name", "unknown"],
            }
        )
