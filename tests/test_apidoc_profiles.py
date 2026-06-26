from __future__ import annotations

import ast
from pathlib import Path

import pytest

from apidoc_samples import collect_sample_api
from example_regression import assert_rendered_bundle
from oodocs.apidoc import (
    ApiPresentationProfile,
    presentation_profile_names,
    resolve_presentation_profile,
)
from oodocs.apidoc.profiles import normalize_parameter_columns


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_apidoc_profiles_resolve_all_standard_profiles() -> None:
    expected = {"reference", "compact", "manual", "evidence", "review", "website"}

    assert expected.issubset(set(presentation_profile_names()))
    assert resolve_presentation_profile("compact").max_examples == 1
    assert resolve_presentation_profile(ApiPresentationProfile.review()).include_review_notes
    assert ApiPresentationProfile.from_dict(ApiPresentationProfile.website().to_dict()).name == "website"


def test_apidoc_profile_validates_parameter_columns() -> None:
    profile = ApiPresentationProfile(
        name="compact",
        parameter_columns=(" Name ", "Required", "source"),
    )

    assert profile.parameter_columns == ("name", "required", "source")
    assert normalize_parameter_columns(("type", "description")) == (
        "type",
        "description",
    )
    with pytest.raises(ValueError, match="Unsupported API parameter columns"):
        ApiPresentationProfile.from_dict(
            {
                "name": "compact",
                "parameter_columns": ["name", "unknown"],
            }
        )


def test_apidoc_profiles_are_separate_from_visual_stylesheet() -> None:
    profile_imports = _imported_modules(Path("src/oodocs/apidoc/profiles.py"))
    stylesheet_imports = _imported_modules(Path("src/oodocs/styles/sheet.py"))

    assert not any(module.startswith("oodocs.styles") for module in profile_imports)
    assert "StyleSheet" not in Path("src/oodocs/apidoc/profiles.py").read_text(encoding="utf-8")
    assert not any(module.startswith("oodocs.apidoc") for module in stylesheet_imports)


@pytest.mark.parametrize(
    "profile_name",
    ("reference", "compact", "manual", "evidence", "review", "website"),
)
def test_standard_profiles_save_renderer_neutral_bundles(
    tmp_path,
    profile_name: str,
) -> None:
    api = collect_sample_api(tmp_path)
    document = api.to_document(presentation=profile_name, max_level=2)

    assert document.validate(formats=("docx", "pdf", "html")).ok
    outputs = document.save_all(
        tmp_path / f"{profile_name}-rendered",
        stem=f"{profile_name}-api",
        formats=("docx", "pdf", "html"),
    )

    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert "samplepkg API Reference" in outputs["html"].read_text(encoding="utf-8")
