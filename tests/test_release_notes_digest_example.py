from __future__ import annotations

import importlib.util
from html import unescape
from io import BytesIO
from pathlib import Path
import re

from docx import Document as WordDocument
from pypdf import PdfReader


def _load_example_module(example_dir: str):
    module_path = Path(__file__).resolve().parents[1] / "examples" / example_dir / "main.py"
    spec = importlib.util.spec_from_file_location(f"examples.{example_dir}.main", module_path)
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


def test_release_notes_digest_example_builds_outputs(tmp_path: Path) -> None:
    release_notes_example = _load_example_module("release_notes_digest")
    files = release_notes_example.release_note_files()

    expected_count = len(list(Path(release_notes_example.RELEASE_NOTES_DIR).glob("*.md")))
    assert len(files) == expected_count
    assert [path.name for path in files[:2]] == ["v0.10.0.md", "v0.9.1.md"]
    assert files == sorted(
        files,
        key=release_notes_example.version_parts_from_filename,
        reverse=True,
    )
    assert release_notes_example.release_type_from_version((0, 10, 0)) == "Minor"
    assert release_notes_example.release_type_from_version((0, 9, 1)) == "Patch"
    assert release_notes_example.release_type_from_version((0, 9, 0)) == "Minor"

    docx_path, pdf_path = release_notes_example.build_release_notes(tmp_path)
    html_path = tmp_path / "docscriptor-release-notes.html"

    assert docx_path.exists()
    assert pdf_path.exists()
    assert html_path.exists()

    word_document = WordDocument(docx_path)
    paragraph_texts = [paragraph.text for paragraph in word_document.paragraphs]
    table_text = "\n".join(
        cell.text
        for table in word_document.tables
        for row in table.rows
        for cell in row.cells
    )
    pdf_reader = PdfReader(BytesIO(pdf_path.read_bytes()))
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    normalized_html_text = _normalized_html_text(html_path)
    html_text = html_path.read_text(encoding="utf-8")

    assert "Docscriptor Release Notes" in paragraph_texts
    assert "Contents" in paragraph_texts
    assert any("Release Note Index" in text for text in paragraph_texts)
    assert any("Release-note digest workflow" in text for text in paragraph_texts)
    assert any("Version Management" in text for text in paragraph_texts)
    assert "3 Version History" in paragraph_texts
    assert any("Release runbook" in text for text in paragraph_texts)
    assert any("setuptools-scm" in text for text in paragraph_texts + [table_text])
    assert "v0.10.0.md" in table_text
    assert "latest" in table_text
    assert any("release-notes/v0.10.0.md" in text for text in paragraph_texts)
    assert "v0.10.0" in paragraph_texts
    assert "Highlights" in paragraph_texts
    assert "3 v0.10.0" not in paragraph_texts
    assert "3.1 v0.10.0" not in paragraph_texts
    assert "4 v0.10.0" not in paragraph_texts
    assert not any(
        re.fullmatch(r"\d+(?:\.\d+)* Highlights", text)
        for text in paragraph_texts
    )
    assert any(
        "Version-management rules demonstrated by this example." in text
        for text in paragraph_texts
    )
    assert any(
        "Release note files collected from the repository." in text
        for text in paragraph_texts
    )
    assert len(word_document.tables) == 2

    assert "Docscriptor Release Notes" in pdf_text
    assert "Contents" in pdf_text
    assert "Release Note Index" in pdf_text
    assert "Release-note digest workflow" in pdf_text
    assert "Version Management" in pdf_text
    assert "Version History" in pdf_text
    assert "release-notes/v0.10.0.md" in pdf_text
    assert "setuptools-scm" in pdf_text
    assert len(pdf_reader.pages) >= 3

    assert "Docscriptor Release Notes" in normalized_html_text
    assert "Contents" in normalized_html_text
    assert "Release Note Index" in normalized_html_text
    assert "Release-note digest workflow" in normalized_html_text
    assert "Version Management" in normalized_html_text
    assert "Version History" in normalized_html_text
    assert "Release runbook" in normalized_html_text
    assert "release-notes/v0.10.0.md" in normalized_html_text
    assert "vMAJOR.MINOR.PATCH" in normalized_html_text
    assert (
        'class="docscriptor-toc-entry docscriptor-toc-entry-no-page '
        'docscriptor-toc-entry-level-1"'
    ) in html_text
    toc_html = html_text.split("</nav>", 1)[0]
    assert ">3 Version History</a>" in toc_html
    assert ">v0.10.0</a>" in toc_html
    assert ">Highlights</a>" not in toc_html
