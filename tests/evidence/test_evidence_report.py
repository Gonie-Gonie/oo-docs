from __future__ import annotations

import json
from pathlib import Path

import pytest

from oodocs.evidence import EvidenceItem, EvidenceReport
from oodocs.settings import DocumentMetadata, TitleMatter


def _items(tmp_path: Path) -> tuple[EvidenceItem, ...]:
    csv_path = tmp_path / "measurements.csv"
    csv_path.write_text("name,value\nalpha,1\n", encoding="utf-8")
    json_path = tmp_path / "summary.json"
    json_path.write_text(json.dumps({"status": "ready"}), encoding="utf-8")
    checksum_path = tmp_path / "inputs.sha256"
    checksum_path.write_text("abc  measurements.csv\n", encoding="utf-8")
    return (
        EvidenceItem(csv_path, title="Measurements"),
        EvidenceItem(json_path, title="Summary"),
        EvidenceItem(checksum_path, title="Input checksums"),
    )


def test_evidence_report_renders_caller_selected_csv_json_and_checksums(
    tmp_path: Path,
) -> None:
    report = EvidenceReport(
        "Verification packet",
        _items(tmp_path),
        metadata=DocumentMetadata(author="Example Laboratory"),
        title_matter=TitleMatter(subtitle="Independent inputs"),
    )

    document = report.to_document()

    assert document.title == "Verification packet"
    assert document.settings.metadata.author == "Example Laboratory"
    assert "".join(
        fragment.plain_text() for fragment in document.settings.title_matter.subtitle or ()
    ) == "Independent inputs"
    chapter = document.body.children[0]
    assert [section.plain_title() for section in chapter.children] == [
        "Measurements",
        "Summary",
        "Input checksums",
    ]


def test_evidence_bundle_uses_caller_stem_and_only_explicit_sources(
    tmp_path: Path,
) -> None:
    report = EvidenceReport("Audit", _items(tmp_path))

    bundle = report.save_bundle(
        tmp_path / "output",
        stem="verification-packet",
        formats=("html",),
    )

    assert bundle.outputs["html"].name == "verification-packet.html"
    assert {path.name for path in bundle.included_source_files} == {
        "measurements.csv",
        "summary.json",
        "inputs.sha256",
    }
    assert bundle.checksum_file.name == "checksums.sha256"
    checksum_text = bundle.checksum_file.read_text(encoding="utf-8")
    assert "sources/measurements.csv" in checksum_text
    assert "verification-packet.html" in checksum_text


def test_missing_evidence_never_creates_skeleton_data(tmp_path: Path) -> None:
    missing = tmp_path / "not-present.csv"
    report = EvidenceReport("Audit", (EvidenceItem(missing),))

    with pytest.raises(FileNotFoundError, match="Missing required evidence"):
        report.to_document()

    warned = report.to_document(missing_input_policy="warn")
    assert "not-present.csv" in warned.body.children[0].children[0].children[0].plain_text()
    assert not missing.exists()
    with pytest.raises(ValueError, match="error.*warn"):
        report.to_document(missing_input_policy="skeleton")  # type: ignore[arg-type]


def test_source_tree_has_no_project_recipe_evidence_names() -> None:
    forbidden = (
        "feature" + "-coverage.csv",
        "renderer" + "-consistency.csv",
        "validation" + "-results.csv",
        "compatibility" + "-matrix.csv",
        "oodocs" + "-evidence-report",
    )
    roots = (Path("src/oodocs"), Path("docs"), Path("examples"), Path("tests"))
    findings: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".md", ".toml"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace").casefold()
            for value in forbidden:
                if value.casefold() in text:
                    findings.append(f"{path.as_posix()}: {value}")
    assert findings == []
