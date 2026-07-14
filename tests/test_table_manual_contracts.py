from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile

from pypdf import PdfReader
import pytest

from oodocs import (
    Chapter,
    Document,
    DocumentSettings,
    PageLayout,
    PageMargins,
    PageSize,
    Paragraph,
    Section,
    Table,
    TableCell,
    line_break,
)
from oodocs.media import TableOverflowPolicy


def _docx_document_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def test_split_table_repeats_all_header_rows_in_docx_and_pdf(tmp_path: Path) -> None:
    table = Table.grouped_headers(
        groups=[("LONG GROUP HEADER", 2)],
        columns=["RECORD HEADER", "VALUE HEADER"],
        rows=[
            [f"ROW {index:03d}", f"VALUE {index:03d}"]
            for index in range(120)
        ],
        caption="Long repeated-header matrix.",
        split=True,
    )
    document = Document("Long Table Contract", table)
    docx_path = tmp_path / "long-table.docx"
    pdf_path = tmp_path / "long-table.pdf"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)

    docx_xml = _docx_document_xml(docx_path)
    assert docx_xml.count("w:tblHeader") >= 2

    pdf_reader = PdfReader(BytesIO(pdf_path.read_bytes()))
    row_pages = [
        page.extract_text() or ""
        for page in pdf_reader.pages
        if "ROW " in (page.extract_text() or "")
    ]
    assert len(row_pages) >= 2
    for page_text in row_pages:
        assert "LONG GROUP HEADER" in page_text
        assert "RECORD HEADER" in page_text
        assert "VALUE HEADER" in page_text


def test_group_rows_multiline_links_and_localized_continuation_render(
    tmp_path: Path,
) -> None:
    details = Section(
        "Details",
        Paragraph("Linked details live in the same document."),
        numbered=False,
        anchor="details",
    )
    table = Table(
        headers=["Item", "Description", "State"],
        rows=[
            [TableCell("Phase A", colspan=3, bold=True)],
            [
                "Check",
                Paragraph(
                    "First line",
                    line_break(),
                    "Second line — ",
                    details.link("Open details"),
                ),
                "Ready",
            ],
        ],
        caption="점검 표.",
        split=True,
        continuation_label="계속",
        continued_caption_template="{caption} — {continuation_label}",
    )
    document = Document(
        "Table Cell Contract",
        Chapter("Report", details, table),
    )
    docx_path = tmp_path / "cells.docx"
    pdf_path = tmp_path / "cells.pdf"
    html_path = tmp_path / "cells.html"

    document.save_docx(docx_path)
    document.save_pdf(pdf_path)
    document.save_html(html_path)

    docx_xml = _docx_document_xml(docx_path)
    pdf_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(pdf_path).pages
    )
    html = html_path.read_text(encoding="utf-8")

    assert table.continued_caption_text() == "점검 표. — 계속"
    assert "w:br" in docx_xml
    assert "w:hyperlink" in docx_xml
    assert "Phase A" in pdf_text
    assert "First line" in pdf_text
    assert "Second line" in pdf_text
    assert "Open details" in pdf_text
    assert 'colspan="3"' in html
    assert "overflow-x: auto" in html
    assert 'data-continuation-label="계속"' in html
    assert 'data-continued-caption="점검 표. — 계속"' in html
    assert "<br" in html
    assert re.search(r'href="#[^"]+"[^>]*>Open details</a>', html)


def test_wide_table_validation_and_layout_policy_stay_explicit() -> None:
    settings = DocumentSettings(
        unit="in",
        page_layout=PageLayout(
            PageSize.letter(),
            PageMargins.all(1.0, unit="in"),
        ),
    )
    explicit_width = Table.grouped_headers(
        groups=[("Expanded", 3)],
        columns=["A", "B", "C"],
        rows=[["a", "b", "c"]],
        column_widths=[3.0, 3.0, 3.0],
        unit="in",
    )
    many_columns = Table(
        headers=[f"C{index}" for index in range(8)],
        rows=[[str(index) for index in range(8)]],
    )

    result = Document(
        "Wide Tables",
        explicit_width,
        many_columns,
        settings=settings,
    ).validate()

    assert explicit_width._layout().column_count == 3
    assert any(
        issue.code == "wide-table"
        and "9.00in" in issue.message
        and "6.50in" in issue.message
        for issue in result.warnings
    )
    assert any(
        issue.code == "many-table-columns" and "8 columns" in issue.message
        for issue in result.warnings
    )
    assert not hasattr(explicit_width, "page_layout")

    landscape_result = Document(
        "Landscape Table",
        Section(
            "Full Matrix",
            explicit_width,
            numbered=False,
            page_layout=PageLayout.landscape(PageSize.letter()),
        ),
    ).validate(formats=("html",))
    assert any(
        issue.code == "section-page-layout-html-degrade"
        and issue.formats == ("html",)
        for issue in landscape_result.warnings
    )

    allowed = Table(
        headers=["A", "B"],
        rows=[["a", "b"]],
        column_widths=[4.0, 4.0],
        unit="in",
        overflow_policy="allow",
    )
    allowed_result = Document("Allowed", allowed, settings=settings).validate()
    assert "wide-table" not in {issue.code for issue in allowed_result.warnings}
    assert TableOverflowPolicy("warn").action == "warn"
    assert TableOverflowPolicy("allow").action == "allow"
    with pytest.raises(ValueError, match="'warn' or 'allow'"):
        TableOverflowPolicy("clip")  # type: ignore[arg-type]


def test_table_reference_documents_fixed_page_and_sidecar_patterns() -> None:
    reference = Path("docs/reference/table-media-support.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(reference.split())

    for phrase in (
        "`Table.from_dataframe(...)` is the canonical",
        "`Table(dataframe)`",
        "MultiIndex",
        "`split=True`",
        "`continuation_label`",
        "`TableCell(..., colspan=n)`",
        "`line_break()`",
        "object link",
        "`Section(page_layout=PageLayout.landscape(...))`",
        "horizontal overflow container",
        "does not change document page layout automatically",
        "`Table.excerpt(...)`",
        "`Table.save_csv(...)`",
    ):
        assert phrase in normalized
