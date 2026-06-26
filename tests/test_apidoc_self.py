from __future__ import annotations

from example_regression import (
    assert_docx_structure,
    assert_html_internal_links_resolve,
    assert_pdf_text_and_pages,
    assert_rendered_bundle,
)
from oodocs.apidoc import ApiCoverageResult, ApiPackage, check_api_docs, collect_api


def test_apidoc_collects_oodocs_public_api_for_self_reference() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")

    assert api.name == "oodocs"
    assert api.find_object("oodocs.Document") is not None
    assert api.select_public_objects()


def test_apidoc_renders_oodocs_public_api_reference_bundle(tmp_path) -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")
    coverage = check_api_docs(api)
    document = api.to_help_book(
        presentation="compact",
        include_coverage=True,
        max_level=3,
    )

    outputs = document.save_all(
        tmp_path,
        stem="oodocs-api",
        formats=("docx", "pdf", "html"),
    )
    api_path = api.save_json(tmp_path / "oodocs-api.json")
    coverage_json_path = coverage.save_json(tmp_path / "oodocs-api-coverage.json")
    coverage_csv_path = coverage.save_csv(tmp_path / "oodocs-api-coverage.csv")

    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert api_path.exists()
    assert coverage_json_path.exists()
    assert coverage_csv_path.exists()
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=("oodocs API Reference",),
        min_tables=3,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "oodocs API Reference",
            "API Documentation Coverage",
            "oodocs.Document",
        ),
        min_pages=1,
    )
    assert_html_internal_links_resolve(
        outputs["html"],
        required_text=(
            "oodocs API Reference",
            "API Documentation Coverage",
            "oodocs.Document",
        ),
    )
    html = outputs["html"].read_text(encoding="utf-8")
    assert "Uncategorized API" not in html
    assert "Renderer Extension API" not in html
    assert "C:\\Users" not in html
    assert not ("<th>Label</th>" in html and "See Also" in html)
    assert html.find("API Contents") < html.find("API Documentation Coverage")
    assert ApiPackage.load_json(api_path).find_object("oodocs.Document") is not None
    assert ApiCoverageResult.load_json(coverage_json_path).public_object_count > 0
