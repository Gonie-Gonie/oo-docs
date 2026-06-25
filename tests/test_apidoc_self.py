from __future__ import annotations

from oodocs.apidoc import collect_api


def test_apidoc_collects_oodocs_public_api_for_self_reference() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")

    assert api.name == "oodocs"
    assert api.find("oodocs.Document") is not None
    assert api.public_objects()


def test_apidoc_renders_oodocs_public_api_reference_html(tmp_path) -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")
    document = api.to_document(
        profile="compact",
        include_coverage=True,
        include_modules=True,
    )

    outputs = document.save_all(tmp_path, stem="oodocs-api", formats=("html",))
    html = outputs["html"].read_text(encoding="utf-8")

    assert "oodocs API Reference" in html
    assert "oodocs.Document" in html
    assert "API Documentation Coverage" in html
