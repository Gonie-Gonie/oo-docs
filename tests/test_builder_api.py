from __future__ import annotations

from pathlib import Path

from oodocs import Chapter, Document, ListOfTables, Paragraph, Section, Table
from oodocs.components.base import Body, Component
from oodocs.layout.indexing import build_render_index


def test_add_and_extend_match_constructor_structure() -> None:
    constructor_table = Table(["Metric", "Value"], [["status", "ok"]], caption="Summary.")
    builder_table = Table(["Metric", "Value"], [["status", "ok"]], caption="Summary.")

    constructor_doc = Document(
        "Builder Comparison",
        Chapter(
            "Run",
            Section("Configuration", Paragraph("Solver: fast."), constructor_table),
        ),
    )
    builder_doc = Document("Builder Comparison")
    chapter = Chapter("Run")
    section = Section("Configuration")

    assert section.add(Paragraph("Solver: fast."), [builder_table]) is section
    assert chapter.add(section) is chapter
    assert builder_doc.add(chapter) is builder_doc

    constructor_index = build_render_index(constructor_doc)
    builder_index = build_render_index(builder_doc)

    assert [entry.level for entry in constructor_index.headings] == [
        entry.level for entry in builder_index.headings
    ]
    assert len(constructor_index.tables) == len(builder_index.tables) == 1
    assert constructor_doc.validate().ok
    assert builder_doc.validate().ok


def test_body_extend_uses_constructor_coercion() -> None:
    body = Body()

    assert body.add(None, "Lead paragraph.") is body
    assert body.extend([Paragraph("Second paragraph.")]) is body

    assert [child.plain_text() for child in body.children] == [
        "Lead paragraph.",
        "Second paragraph.",
    ]


def test_builder_api_preserves_validation_paths() -> None:
    document = Document("Validation Paths")
    document.add(Chapter("Tables").add(Table(["A"], [["B"]])))

    result = document.validate()

    assert any(
        issue.code == "missing-table-caption"
        and issue.path == "document.body.children[0].children[0].caption"
        for issue in result.warnings
    )


def test_component_compose_drives_validation_indexing_and_rendering(tmp_path: Path) -> None:
    class EvidenceSummary(Component):
        def __init__(self) -> None:
            self.compose_calls = 0
            self.table = Table(
                ["Metric", "Value"],
                [["status", "pass"]],
                caption="Composed evidence table.",
            )

        def compose(self):
            self.compose_calls += 1
            return [
                Paragraph("Composed summary."),
                self.table,
                Paragraph("See ", self.table.ref(), "."),
            ]

    summary = EvidenceSummary()
    document = Document("Component Extension", summary, ListOfTables())

    assert document.validate(formats=("docx", "pdf", "html")).ok
    index = build_render_index(document)
    assert index.table_number(summary.table) == 1
    assert summary.compose_calls == 1

    outputs = document.save_all(
        tmp_path,
        stem="component-extension",
        formats=("docx", "pdf", "html"),
    )

    assert set(outputs.keys()) == {"docx", "pdf", "html"}
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs.values())
    html = outputs["html"].read_text(encoding="utf-8")
    assert "Composed summary." in html
    assert "Composed evidence table." in html
    assert summary.compose_calls == 1
