from __future__ import annotations

from html import unescape
import importlib.util
from io import BytesIO
from pathlib import Path
import re
import zipfile

from pypdf import PdfReader

from example_regression import (
    assert_docx_structure,
    assert_html_internal_links_resolve,
    assert_pdf_text_and_pages,
    assert_rendered_bundle,
)


def _load_example_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "page_overlay_example"
        / "main.py"
    )
    spec = importlib.util.spec_from_file_location("page_overlay_example_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalized_html_text(html_path: Path) -> str:
    html_text = html_path.read_text(encoding="utf-8")
    html_text = re.sub(r"<style.*?>.*?</style>", " ", html_text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html_text)
    return " ".join(unescape(text).split())


def test_page_overlay_example_builds_outputs(tmp_path: Path) -> None:
    example = _load_example_module()
    document = example.build_document()
    outputs = example.build(tmp_path)

    assert document.validate().ok
    assert example.overlay_summary_rows()[0][0] == "Named frame"
    assert len(example.build_overlays()) >= 5
    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])

    with zipfile.ZipFile(outputs["docx"]) as archive:
        word_xml = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist()
            if name.startswith("word/") and name.endswith(".xml")
        )
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(outputs["pdf"].read_bytes())).pages)
    html_raw = outputs["html"].read_text(encoding="utf-8")
    html_text = _normalized_html_text(outputs["html"])

    assert "APPROVAL AREA" in word_xml
    assert "COVER BADGE" in word_xml
    assert "<v:rect" in word_xml
    assert "<v:imagedata" in word_xml
    assert "APPROVAL AREA" in pdf_text
    assert "MAIN WATERMARK" in pdf_text
    assert "PAGE 2 CHECK" in pdf_text
    assert "Page Overlay Example" in html_text
    assert "APPROVAL AREA" in html_text
    assert 'class="oodocs-page-items"' in html_raw
    assert html_raw.count("data:image/png;base64,") >= 1
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=("Page Overlay Example", "1 Overlay Workflow"),
        min_tables=1,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=("Page Overlay Example", "APPROVAL AREA"),
        min_pages=1,
    )
    assert_html_internal_links_resolve(outputs["html"])


def test_page_overlay_example_supports_common_cli(tmp_path: Path, capsys) -> None:
    example = _load_example_module()
    output_dir = tmp_path / "cli"

    outputs = example.build(output_dir / "programmatic", output_formats=("html",))
    assert set(outputs.keys()) == {"html"}
    assert outputs["html"].exists()

    example.main(
        [
            "--output-dir",
            str(output_dir),
            "--outputs",
            "html",
            "--quiet",
        ]
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (output_dir / "page-overlay.html").exists()
