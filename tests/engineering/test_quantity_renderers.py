from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from pypdf import PdfReader

from oodocs import Document, Paragraph, Table
from oodocs.engineering import NumberFormat, Quantity


def _quantity_document() -> Document:
    return Document(
        "Quantity Semantics",
        Paragraph(
            "Area: ",
            Quantity(2.5, "m^2", NumberFormat(decimals=2)),
            "; temperature: ",
            Quantity("21.50", "degC", uncertainty="0.25"),
            ".",
        ),
        Table(
            ["Metric", "Value"],
            [["Concentration", Quantity(400, "CO_2")]],
            caption="Measured quantities.",
        ),
    )


def test_quantity_html_has_visible_and_assistive_text(tmp_path: Path) -> None:
    output = tmp_path / "quantity.html"
    _quantity_document().save_html(output)

    html = output.read_text(encoding="utf-8")
    assert 'class="oodocs-quantity"' in html
    assert 'aria-label="2.50 m squared"' in html
    assert 'aria-label="21.50 plus or minus 0.25 degrees Celsius"' in html
    assert 'aria-label="400 CO subscript 2"' in html
    assert "2.50 m²" in html
    assert "21.50 ± 0.25 °C" in html
    assert "400 CO₂" in html


@pytest.mark.render
def test_quantity_visible_semantics_survive_docx_and_pdf(tmp_path: Path) -> None:
    document = _quantity_document()
    docx_path = tmp_path / "quantity.docx"
    pdf_path = tmp_path / "quantity.pdf"
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)

    with ZipFile(BytesIO(docx_path.read_bytes())) as archive:
        docx_xml = archive.read("word/document.xml").decode("utf-8")
    pdf_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(pdf_path.read_bytes())).pages
    )

    assert "2.50 m²" in docx_xml
    assert "21.50 ± 0.25 °C" in docx_xml
    assert "400 CO₂" in docx_xml
    assert "2.50 m²" in pdf_text
    assert "21.50 ± 0.25 °C" in pdf_text
    assert "400 CO₂" in pdf_text
