from __future__ import annotations

from zipfile import ZipFile

import pytest

from oodocs import Document, InlineChip, Paragraph, inline_code, inline_math
from oodocs.components.inline import ObjectLink
from oodocs.engineering import Quantity
from oodocs.schema import (
    FieldSpec,
    SchemaCatalog,
    SchemaPresentation,
    SchemaSpec,
)


def _cell_text(table, row: int, column: int) -> str:
    return table.rows[row][column].content.plain_text()


def test_field_spec_preserves_full_raw_record_and_renders_generic_chips() -> None:
    constraints = (inline_math(r"x > 0"), Quantity(10, "m"))
    raw = {"vendor-keyword": {"retained": True}, "default": 3}
    field = FieldSpec(
        "threshold",
        "float",
        requirement="conditional-required",
        default=3,
        condition="Required when mode is automatic.",
        constraints=constraints,
        unit=inline_math(r"m\,s^{-1}"),
        description=Paragraph("Maximum accepted threshold."),
        metadata={"owner": "operations"},
        deprecated="Use limit after version 2.",
        links=(inline_code("policy.threshold"),),
        raw_record=raw,
    )
    schema = SchemaSpec("settings", "Settings", (field,))

    record = field.as_record()
    assert record["vendor-keyword"] == {"retained": True}
    assert record["constraints"] is constraints
    assert record["unit"] is field.unit
    assert record["default"] == 3
    assert record["deprecated"] == "Use limit after version 2."
    assert record["links"] == field.links

    table = schema.to_table(
        presentation=SchemaPresentation(metadata_columns={"owner": "Owner"}),
        requirement_labels={"conditional-required": "Required when active"},
    )
    type_chip = table.rows[0][1].content.content[0]
    requirement_chip = table.rows[0][2].content.content[0]
    assert isinstance(type_chip, InlineChip)
    assert type_chip.chip_style == "schema.type.float"
    assert isinstance(requirement_chip, InlineChip)
    assert requirement_chip.chip_style == "schema.requirement.conditional-required"
    assert requirement_chip.plain_text() == "Required when active"
    assert table.split is True
    assert table.style.repeat_header_rows is True
    assert _cell_text(table, 0, 5) == "x > 0; 10 m"


def test_custom_inline_type_is_not_replaced_with_a_generic_chip() -> None:
    value_type = inline_code("UUIDv7")
    table = SchemaSpec(
        "identifier",
        "Identifier",
        (FieldSpec("id", value_type),),
    ).to_table()

    assert table.rows[0][1].content.content == [value_type]
    assert _cell_text(table, 0, 1) == "UUIDv7"


def test_catalog_creates_each_section_once_and_resolves_circular_links(tmp_path) -> None:
    schema_a = SchemaSpec(
        "a",
        "Schema A",
        (FieldSpec("child", "object", target_schema="b"),),
    )
    schema_b = SchemaSpec(
        "b",
        "Schema B",
        (FieldSpec("parent", "object", target_schema="a"),),
    )
    catalog = SchemaCatalog((schema_a, schema_b))

    chapter = catalog.to_chapter()
    section_a, section_b = chapter.children
    a_link = section_a.children[-1].rows[0][8].content.content[0]
    b_link = section_b.children[-1].rows[0][8].content.content[0]
    assert isinstance(a_link, ObjectLink)
    assert isinstance(b_link, ObjectLink)
    assert a_link.target is section_b
    assert b_link.target is section_a
    assert len({id(section_a), id(section_b)}) == 2

    html_path = Document("Circular schemas", chapter).save_html(tmp_path / "schemas.html")
    html = html_path.read_text(encoding="utf-8")
    assert 'href="#schema-b"' in html
    assert 'href="#schema-a"' in html


def test_catalog_validation_uses_stable_duplicate_and_unknown_target_codes() -> None:
    catalog = SchemaCatalog(
        (
            SchemaSpec(
                "duplicate",
                "First",
                (FieldSpec("missing", "object", target_schema="not-present"),),
            ),
            SchemaSpec("duplicate", "Second", ()),
        )
    )

    result = catalog.validate()
    assert not result.ok
    assert {issue.code for issue in result.errors} == {
        "schema-duplicate-key",
        "schema-unknown-target",
    }
    with pytest.raises(ValueError):
        catalog.validate(raise_on_error=True)


def test_catalog_chapter_presentation_applies_to_schema_sections() -> None:
    chapter = SchemaCatalog((SchemaSpec("one", "One", ()),)).to_chapter(
        numbered=False,
        toc=False,
    )

    assert chapter.numbered is False
    assert chapter.toc is False
    assert chapter.children[0].numbered is False
    assert chapter.children[0].toc is False


def test_long_schema_table_splits_and_repeats_header_in_docx(tmp_path) -> None:
    schema = SchemaSpec(
        "long",
        "Long schema",
        tuple(
            FieldSpec(
                f"field_{index:03d}",
                "string",
                requirement="optional",
                description=f"Description for field {index}.",
            )
            for index in range(80)
        ),
    )
    table = schema.to_table()
    assert table.split is True
    assert table.style.repeat_header_rows is True

    docx_path = Document("Long schema", schema.to_section()).save_docx(
        tmp_path / "long-schema.docx"
    )
    with ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "<w:tblHeader" in document_xml
    assert "field_079" in document_xml
