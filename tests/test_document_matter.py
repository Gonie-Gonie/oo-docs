from __future__ import annotations

from pathlib import Path

import pytest

from oodocs.components.blocks import Chapter, Paragraph
from oodocs.components.generated import (
    ListOfFigures,
    ListOfReferences,
    ListOfTables,
    TableOfContents,
)
from oodocs.components.matter import BackMatter, FrontMatter, MainMatter
from oodocs.document import Document
from oodocs.styles.theme import PageNumberDefaults, Theme


def test_explicit_matter_partitions_generated_and_authored_content() -> None:
    contents = TableOfContents()
    figures = ListOfFigures()
    tables = ListOfTables()
    references = ListOfReferences()
    chapter = Chapter("Findings", Paragraph("Main content."))

    front = FrontMatter(contents, page_break_before=True)
    assert front.add(figures) is front
    assert front.extend([tables]) is front
    main = MainMatter(chapter, start_on_new_page=True)
    back = BackMatter(references)
    document = Document("Explicit matter", front, main, back)

    layout = document.matter_layout()
    assert layout.explicit is True
    assert layout.front.children == (contents, figures, tables)
    assert layout.main.children == (chapter,)
    assert layout.back.children == (references,)
    assert layout.front.page_break_before is True
    assert layout.main.page_break_before is True
    assert layout.back.page_break_before is False
    assert document.split_top_level_children() == (
        [contents, figures, tables],
        [chapter, references],
    )


def test_explicit_matter_disables_the_legacy_numbered_chapter_heuristic() -> None:
    inferred_preface = Paragraph("Inferred preface.")
    inferred_chapter = Chapter("Body", Paragraph("Body text."))
    inferred = Document("Legacy inference", inferred_preface, inferred_chapter)

    inferred_layout = inferred.matter_layout()
    assert inferred_layout.explicit is False
    assert inferred_layout.front.children == (inferred_preface,)
    assert inferred_layout.main.children == (inferred_chapter,)

    simple_paragraph = Paragraph("A simple document stays in one flow.")
    simple_layout = Document("Simple", simple_paragraph).matter_layout()
    assert simple_layout.explicit is False
    assert simple_layout.front.children == ()
    assert simple_layout.main.children == (simple_paragraph,)

    declared_preface = Paragraph("Declared front matter.")
    ordinary_block = Paragraph("Unwrapped content remains main matter.")
    declared_chapter = Chapter("Body", Paragraph("Body text."))
    explicit = Document(
        "Explicit layout",
        FrontMatter(declared_preface),
        ordinary_block,
        declared_chapter,
    )

    explicit_layout = explicit.matter_layout()
    assert explicit_layout.explicit is True
    assert explicit_layout.front.children == (declared_preface,)
    assert explicit_layout.main.children == (ordinary_block, declared_chapter)
    assert explicit_layout.back.children == ()


def test_valid_explicit_matter_has_no_structural_validation_errors() -> None:
    document = Document(
        "Valid matter",
        FrontMatter(Paragraph("Preface.")),
        MainMatter(Chapter("Body", Paragraph("Main text."))),
        BackMatter(Paragraph("Afterword.")),
    )

    result = document.validate()
    structural_codes = {"matter-order", "nested-matter", "duplicate-matter"}
    assert result.ok
    assert structural_codes.isdisjoint(issue.code for issue in result.issues)


@pytest.mark.parametrize(
    ("document", "expected_code"),
    [
        (
            Document(
                "Nested matter",
                FrontMatter(MainMatter(Paragraph("Nested main matter."))),
            ),
            "nested-matter",
        ),
        (
            Document(
                "Duplicate matter",
                FrontMatter(Paragraph("First.")),
                FrontMatter(Paragraph("Second.")),
                MainMatter(Paragraph("Body.")),
            ),
            "duplicate-matter",
        ),
        (
            Document(
                "Out-of-order matter",
                MainMatter(Paragraph("Body.")),
                FrontMatter(Paragraph("Preface.")),
                BackMatter(Paragraph("Afterword.")),
            ),
            "matter-order",
        ),
    ],
)
def test_invalid_matter_structure_reports_stable_error_codes(
    document: Document,
    expected_code: str,
) -> None:
    matching = [
        issue for issue in document.validate().issues if issue.code == expected_code
    ]
    assert matching
    assert all(issue.severity == "error" for issue in matching)


def test_html_marks_matter_regions_and_requested_print_page_breaks(
    tmp_path: Path,
) -> None:
    document = Document(
        "HTML matter",
        FrontMatter(Paragraph("FRONT REGION"), page_break_before=True),
        MainMatter(Paragraph("MAIN REGION")),
        BackMatter(Paragraph("BACK REGION"), start_on_new_page=True),
    )
    output = tmp_path / "matter.html"

    document.save_html(output, validate=False)
    html = output.read_text(encoding="utf-8")

    front_tag = '<section class="oodocs-front-matter oodocs-page-break-before">'
    main_tag = '<section class="oodocs-main-matter oodocs-page-break-before">'
    back_tag = '<section class="oodocs-back-matter oodocs-page-break-before">'
    assert html.count(front_tag) == 1
    assert html.count(main_tag) == 1
    assert html.count(back_tag) == 1
    assert html.index("FRONT REGION") < html.index("MAIN REGION") < html.index("BACK REGION")
    assert ".oodocs-page-break-before" in html
    assert "break-before: page; page-break-before: always;" in html


def test_page_number_defaults_define_front_main_and_back_matter_policy() -> None:
    defaults = PageNumberDefaults()
    theme = Theme(page_numbers=defaults)

    assert defaults.show_page_numbers is True
    assert defaults.front_matter_counter.counter_format == "lower-roman"
    assert defaults.main_matter_counter.counter_format == "decimal"
    assert defaults.back_matter_counter is None
    assert defaults.restart_main_matter is True
    assert defaults.restart_back_matter is False
    assert theme.format_page_number(4, matter="front") == "iv"
    assert theme.format_page_number(4, matter="main") == "4"
    assert theme.format_page_number(4, matter="back") == "4"
