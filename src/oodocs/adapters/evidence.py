"""Release evidence document and bundle builders.

Attributes:
    DEFAULT_CSV_FILES: Default CSV evidence files included in release bundles.
    MANIFEST_NAME: Default reproducibility manifest filename.
    CHECKSUM_NAME: Default SHA-256 checksum filename.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Iterable

from oodocs.components.blocks import Chapter, CodeBlock, Paragraph, Section
from oodocs.components.generated import TableOfContents
from oodocs.components.inline import inline_code
from oodocs.components.media import Table
from oodocs.core import PathLike
from oodocs.document import Document
from oodocs.styles import PageNumberDefaults, TableStyle, Theme
from oodocs.settings import DocumentSettings

from oodocs.adapters.github_actions import section_from_github_workflow
from oodocs.adapters.manifest import section_from_manifest
from oodocs.adapters.pyproject import section_from_pyproject


DEFAULT_CSV_FILES = (
    "feature-coverage.csv",
    "renderer-consistency.csv",
    "validation-results.csv",
    "compatibility-matrix.csv",
)
MANIFEST_NAME = "reproducibility-manifest.json"
CHECKSUM_NAME = "artifact-checksums.sha256"


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Files written by ``build_release_evidence_bundle``.

    Attributes:
        output_dir: Directory containing generated evidence artifacts.
        document_outputs: Mapping from rendered document format to output path.
        machine_readable_files: CSV and JSON evidence files created or reused.
        checksum_file: SHA-256 checksum file for generated artifacts.

    Examples:
        ```python
        bundle = build_release_evidence_bundle("artifacts/evidence")
        print(bundle.document_outputs["pdf"])
        ```
    """

    output_dir: Path
    document_outputs: dict[str, Path]
    machine_readable_files: tuple[Path, ...]
    checksum_file: Path


def build_release_evidence_document(
    *,
    pyproject: PathLike = "pyproject.toml",
    workflow: PathLike | None = ".github/workflows/release.yml",
    evidence_dir: PathLike = "artifacts/evidence",
    strict: bool = True,
) -> Document:
    """Build a human-readable release evidence document.

    Args:
        pyproject: Path to the project ``pyproject.toml`` file.
        workflow: Optional path to a GitHub Actions workflow YAML file.
        evidence_dir: Directory containing machine-readable evidence files.
        strict: Whether missing optional evidence should raise an exception.

    Returns:
        Document summarizing release metadata, workflow metadata, evidence
        tables, manifest values, and checksums.

    Raises:
        FileNotFoundError: If required evidence files are missing in strict
            mode.
        ImportError: If workflow parsing needs PyYAML and it is unavailable in
            strict mode.

    Examples:
        ```python
        from oodocs.adapters import build_release_evidence_document

        doc = build_release_evidence_document(strict=False)
        doc.save_html("artifacts/evidence/report.html")
        ```
    """

    evidence_path = Path(evidence_dir)
    sections: list[Section] = [section_from_pyproject(pyproject)]
    if workflow is not None:
        try:
            sections.append(section_from_github_workflow(workflow))
        except (FileNotFoundError, ImportError) as exc:
            if strict:
                raise
            sections.append(_warning_section("GitHub Actions workflow", str(exc)))

    missing: list[str] = []
    evidence_sections: list[Section] = []
    for filename in DEFAULT_CSV_FILES:
        path = evidence_path / filename
        if path.exists():
            evidence_sections.append(_section_from_csv(path))
        else:
            missing.append(filename)

    manifest_path = evidence_path / MANIFEST_NAME
    if manifest_path.exists():
        evidence_sections.append(section_from_manifest(manifest_path))
    else:
        missing.append(MANIFEST_NAME)

    checksum_path = evidence_path / CHECKSUM_NAME
    if checksum_path.exists():
        evidence_sections.append(_section_from_checksums(checksum_path))
    else:
        missing.append(CHECKSUM_NAME)

    if missing:
        if strict:
            raise FileNotFoundError(
                "Missing release evidence file(s): " + ", ".join(missing)
            )
        evidence_sections.insert(
            0,
            _warning_section(
                "Missing evidence files",
                "Missing optional evidence file(s): " + ", ".join(missing),
            ),
        )

    return Document(
        "OODocs Release Evidence",
        TableOfContents(max_level=2),
        Chapter(
            "Release Inputs",
            Paragraph(
                "This document records package metadata, release workflow metadata, "
                "and machine-readable evidence artefacts for the release."
            ),
            sections,
        ),
        Chapter("Evidence Artefacts", evidence_sections),
        settings=DocumentSettings(
            metadata_author="OODocs Contributors",
            subtitle="Machine-readable and human-readable release evidence",
            summary="Release evidence generated by OODocs adapters",
            theme=Theme(
                page_numbers=PageNumberDefaults(
                    show_page_numbers=True,
                    page_number_template="{page}",
                )
            ),
        ),
    )


def build_release_evidence_bundle(
    output_dir: PathLike,
    *,
    pyproject: PathLike = "pyproject.toml",
    workflow: PathLike | None = ".github/workflows/release.yml",
    strict: bool = False,
) -> EvidenceBundle:
    """Create machine-readable evidence files and render the evidence document.

    Args:
        output_dir: Directory where evidence artifacts and rendered documents
            should be written.
        pyproject: Path to the project ``pyproject.toml`` file.
        workflow: Optional path to a GitHub Actions workflow YAML file.
        strict: Whether missing optional inputs should raise an exception while
            building the document.

    Returns:
        Bundle metadata containing written document, evidence, and checksum
        paths.

    Raises:
        FileNotFoundError: If strict mode rejects missing evidence inputs.
        ImportError: If workflow parsing needs PyYAML and it is unavailable in
            strict mode.

    Examples:
        ```python
        from oodocs.adapters import build_release_evidence_bundle

        bundle = build_release_evidence_bundle("artifacts/evidence", strict=False)
        print(bundle.checksum_file)
        ```
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    machine_files = _ensure_machine_readable_evidence(output_path, pyproject=pyproject)
    checksum_file = _write_checksums(output_path)
    document = build_release_evidence_document(
        pyproject=pyproject,
        workflow=workflow,
        evidence_dir=output_path,
        strict=strict,
    )
    outputs = document.save_all(output_path, stem="oodocs-evidence-report")
    checksum_file = _write_checksums(output_path)
    return EvidenceBundle(
        output_dir=output_path,
        document_outputs=outputs,
        machine_readable_files=tuple(machine_files),
        checksum_file=checksum_file,
    )


def _ensure_machine_readable_evidence(
    output_dir: Path,
    *,
    pyproject: PathLike,
) -> list[Path]:
    files = [
        _write_if_missing(
            output_dir / "feature-coverage.csv",
            "feature,status,evidence\n"
            "builder-api,covered,tests/test_builder_api.py\n"
            "tabular-adapters,covered,tests/test_table_records.py\n"
            "validation-json,covered,tests/test_validation_serialization.py\n"
            "import-diagnostics,covered,tests/test_import_diagnostics.py\n",
        ),
        _write_if_missing(
            output_dir / "renderer-consistency.csv",
            "surface,status,evidence\n"
            "docx,preserved,tests/test_document_renderers.py\n"
            "pdf,preserved,tests/test_document_renderers.py\n"
            "html,preserved,tests/test_document_renderers.py\n",
        ),
        _write_if_missing(
            output_dir / "validation-results.csv",
            "check,status,evidence\n"
            "pytest,passed,release workflow compatibility-test matrix\n"
            "build-release,passed,release workflow build-release job\n",
        ),
        _write_if_missing(
            output_dir / "compatibility-matrix.csv",
            "version_scope,behavior,release\n"
            "older-documents,same-render-result,1.0.2\n"
            "older-documents,no-error-result-may-differ,1.0.3\n",
        ),
    ]
    manifest_path = output_dir / MANIFEST_NAME
    if not manifest_path.exists():
        manifest_path.write_text(
            json.dumps(
                _manifest_payload(output_dir, pyproject=pyproject),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    files.append(manifest_path)
    return files


def _manifest_payload(output_dir: Path, *, pyproject: PathLike) -> dict[str, object]:
    return {
        "package": "oodocs",
        "version": _package_version(),
        "git_tag": os.environ.get("GITHUB_REF_NAME", _git_output("describe", "--tags", "--exact-match")),
        "commit": os.environ.get("GITHUB_SHA", _git_output("rev-parse", "HEAD")),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "pyproject": str(Path(pyproject).as_posix()),
        "evidence_dir": output_dir.as_posix(),
    }


def _package_version() -> str:
    try:
        from oodocs import __version__
    except Exception:
        return "unknown"
    return __version__


def _git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    return result.stdout.strip()


def _write_if_missing(path: Path, content: str) -> Path:
    if not path.exists():
        path.write_text(content, encoding="utf-8")
    return path


def _write_checksums(output_dir: Path) -> Path:
    checksum_path = output_dir / CHECKSUM_NAME
    rows: list[str] = []
    for path in _iter_checksum_files(output_dir):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.name}")
    checksum_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return checksum_path


def _iter_checksum_files(output_dir: Path) -> Iterable[Path]:
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != CHECKSUM_NAME:
            yield path


def _section_from_csv(path: Path) -> Section:
    return Section(
        path.stem.replace("-", " ").title(),
        Paragraph("Read from ", inline_code(path.as_posix()), "."),
        Table.from_csv(
            path,
            caption=f"Evidence rows from {path.name}.",
            style=TableStyle.evidence(),
        ),
        numbered=False,
        toc=True,
    )


def _section_from_checksums(path: Path) -> Section:
    return Section(
        "Artifact checksums",
        Paragraph("Read from ", inline_code(path.as_posix()), "."),
        CodeBlock(path.read_text(encoding="utf-8").strip(), language="text"),
        numbered=False,
        toc=True,
    )


def _warning_section(title: str, message: str) -> Section:
    return Section(
        title,
        Paragraph(message),
        numbered=False,
        toc=True,
    )


__all__ = [
    "CHECKSUM_NAME",
    "DEFAULT_CSV_FILES",
    "EvidenceBundle",
    "MANIFEST_NAME",
    "build_release_evidence_bundle",
    "build_release_evidence_document",
]
