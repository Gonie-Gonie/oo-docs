from __future__ import annotations

from apidoc_samples import collect_sample_api
from oodocs import Chapter, Document


def test_manual_profile_embeds_selected_sections_in_document(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    classes = api.select(kind="class")
    document = Document(
        "Manual API Notes",
        Chapter("Selected Classes", *[obj.to_section(profile="manual") for obj in classes]),
    )

    assert document.validate(formats=("html",)).ok
