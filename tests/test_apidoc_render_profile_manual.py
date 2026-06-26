from __future__ import annotations

from apidoc_samples import collect_sample_api
from oodocs import Chapter, Document


def test_manual_profile_embeds_selected_sections_in_document(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    classes = api.select_objects(kind="class")
    document = Document(
        "Manual API Notes",
        Chapter("Selected Classes", *[obj.to_section(profile="manual") for obj in classes]),
    )

    assert document.validate(formats=("html",)).ok


def test_hand_composed_api_document_saves_all_formats(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    classes = api.select_objects(kind="class")[:1]
    functions = api.select_objects(kind="function")[:1]
    parameter_table = functions[0].to_parameters_table(profile="reference")

    assert parameter_table is not None
    document = Document(
        "Demo",
        Chapter(
            "API",
            *[obj.to_section(level=2, profile="manual") for obj in classes],
            parameter_table,
        ),
    )

    assert document.validate(formats=("docx", "pdf", "html")).ok
    outputs = document.save_all(
        tmp_path / "rendered",
        stem="demo-api",
        formats=("docx", "pdf", "html"),
    )

    assert set(outputs) == {"docx", "pdf", "html"}
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs.values())
    assert "samplepkg.Widget" in outputs["html"].read_text(encoding="utf-8")
