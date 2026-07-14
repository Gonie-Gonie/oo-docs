from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

from PIL import Image
from pypdf import PdfReader
import pytest

from oodocs import Document, Figure, ImageData, Paragraph, Section, Table, link
from oodocs.components import DescriptionList, Hyperlink, ObjectLink
from oodocs.layout.indexing import build_render_index
from oodocs.positioning import Shape


def _sample_png() -> ImageData:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "#4F81BD").save(buffer, format="PNG")
    return ImageData(buffer.getvalue())


def _document_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def _pdf_link_destinations(path: Path) -> set[str]:
    reader = PdfReader(path)
    destinations = set(reader.named_destinations)
    for page in reader.pages:
        for annotation_ref in page.get("/Annots", ()):
            annotation = annotation_ref.get_object()
            destination = annotation.get("/Dest")
            if destination is not None:
                destinations.add(str(destination))
    return destinations


def test_object_link_and_external_link_have_distinct_roles() -> None:
    section = Section(
        "Unnumbered overview",
        numbered=False,
        toc=False,
        anchor="overview",
    )

    internal = section.link()
    external = link("https://example.com/guide", "web guide")

    assert isinstance(internal, ObjectLink)
    assert internal.target is section
    assert internal.plain_text() == "Unnumbered overview"
    assert isinstance(external, Hyperlink)
    assert external.target == "https://example.com/guide"
    assert external.internal is False


@pytest.mark.render
def test_mutual_object_links_work_in_nested_content_and_all_renderers(
    tmp_path: Path,
) -> None:
    overview = Section(
        "Overview",
        numbered=False,
        toc=False,
        anchor="overview",
        level=1,
    )
    details = Section("Details", level=1)

    overview.add(Paragraph("Continue with ", details.ref(), "."))
    details.add(Paragraph("Return to ", overview.link(), "."))

    link_table = Table(
        ["Location"],
        [[Paragraph("Open ", details.link("the details"), ".")]],
        caption="Link inside a table cell.",
    )
    link_figure = Figure(
        _sample_png(),
        caption=Paragraph("Figure caption links to ", overview.link("the overview"), "."),
        alt_text="A blue square used as a rendering fixture.",
    )
    descriptions = DescriptionList().add(
        "Navigation",
        Paragraph("Definition links to ", overview.link("Overview"), "."),
    )
    document = Document(
        "Object links",
        overview,
        details,
        link_table,
        link_figure,
        descriptions,
    )

    validation = document.validate()
    assert not validation.errors

    render_index = build_render_index(document)
    overview_anchor = render_index.anchor_for(overview)
    details_anchor = render_index.anchor_for(details)
    assert overview_anchor == "overview"
    assert details_anchor is not None
    assert render_index.heading_number(overview) is None
    assert render_index.heading_number(details) == "1"

    docx_path = document.save_docx(tmp_path / "object-links.docx")
    pdf_path = document.save_pdf(tmp_path / "object-links.pdf")
    html_path = document.save_html(tmp_path / "object-links.html")

    html = html_path.read_text(encoding="utf-8")
    assert 'id="overview"' in html
    assert f'id="{details_anchor}"' in html
    assert html.count('href="#overview"') >= 3
    assert html.count(f'href="#{details_anchor}"') >= 2
    assert "Chapter 1" in html

    document_xml = _document_xml(docx_path)
    assert 'w:name="overview"' in document_xml
    assert f'w:name="{details_anchor}"' in document_xml
    assert document_xml.count('w:anchor="overview"') >= 3
    assert document_xml.count(f'w:anchor="{details_anchor}"') >= 2

    pdf_destinations = _pdf_link_destinations(pdf_path)
    # ReportLab resolves named anchors to explicit page destinations when the
    # PDF is written. Two distinct destination arrays prove that both sides of
    # the mutual link survived that resolution.
    resolved_page_destinations = {
        destination for destination in pdf_destinations if "/XYZ" in destination
    }
    assert len(resolved_page_destinations) >= 2


def test_object_link_validation_reports_absent_target_with_contract_code() -> None:
    absent = Section(
        "Not in the document",
        numbered=False,
        toc=False,
        anchor="absent",
    )
    document = Document(
        "Missing target",
        Paragraph("See ", absent.link("the missing section"), "."),
    )

    errors = document.validate().errors

    assert [issue.code for issue in errors] == ["missing-object-link-target"]
    assert errors[0].path.endswith("content[1]")


def test_duplicate_explicit_anchors_use_the_validation_contract_code() -> None:
    first = Section("First", numbered=False, toc=False, anchor="shared")
    second = Section("Second", numbered=False, toc=False, anchor="shared")

    errors = Document("Duplicate anchors", first, second).validate().errors

    assert "duplicate-anchor" in {issue.code for issue in errors}


def test_positioning_coordinate_anchors_are_not_document_link_anchors() -> None:
    first = Shape.rect(width=1.0, height=0.5, placement="inline")
    second = Shape.rect(width=1.0, height=0.5, placement="inline")

    errors = Document("Drawing anchors", first, second).validate().errors

    assert "duplicate-anchor" not in {issue.code for issue in errors}
