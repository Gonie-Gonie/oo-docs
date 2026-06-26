from __future__ import annotations

from apidoc_samples import collect_sample_api
from example_regression import assert_docx_structure


def test_review_profile_builds_editable_docx_review_copy(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    docx_path = tmp_path / "review-api.docx"

    document = api.to_document(presentation="review", max_level=2)

    assert document.validate(formats=("docx",)).ok
    document.save_docx(docx_path)
    assert_docx_structure(
        docx_path,
        required_paragraphs=(
            "samplepkg API Reference",
            "1 API Documentation Coverage",
            "2 samplepkg",
            "2.1 samplepkg.CONSTANT",
            "2.2 samplepkg.Widget",
            "2.3 samplepkg.make_widget",
        ),
        min_tables=4,
        comment_count=3,
    )
