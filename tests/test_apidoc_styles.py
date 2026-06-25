from __future__ import annotations

import pytest

from apidoc_samples import collect_sample_api
from example_regression import assert_rendered_bundle
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


@pytest.mark.parametrize(
    "profile_name",
    ("reference", "compact", "manual", "evidence", "review", "website"),
)
def test_standard_profiles_save_renderer_neutral_bundles(
    tmp_path,
    profile_name: str,
) -> None:
    api = collect_sample_api(tmp_path)
    document = api.to_document(profile=profile_name, max_level=2)

    assert document.validate(formats=("docx", "pdf", "html")).ok
    outputs = document.save_all(
        tmp_path / f"{profile_name}-rendered",
        stem=f"{profile_name}-api",
        formats=("docx", "pdf", "html"),
    )

    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert "samplepkg API Reference" in outputs["html"].read_text(encoding="utf-8")
