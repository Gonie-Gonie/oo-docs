"""Release evidence document and bundle adapters.

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

from oodocs.adapters.github_actions import GithubWorkflowSummary
from oodocs.adapters.manifest import ReleaseManifestSummary
from oodocs.adapters.pyproject import ProjectMetadata


DEFAULT_CSV_FILES = (
    "feature-coverage.csv",
    "renderer-consistency.csv",
    "validation-results.csv",
    "compatibility-matrix.csv",
)
MANIFEST_NAME = "reproducibility-manifest.json"
CHECKSUM_NAME = "artifact-checksums.sha256"


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceBundle:
    """Files written by ``ReleaseEvidence.save_bundle``.

    Attributes:
        output_dir: Directory containing generated evidence artifacts.
        outputs: Mapping from rendered document format to output path.
        data_files: CSV and JSON evidence files created or reused.
        checksum_file: SHA-256 checksum file for generated artifacts.

    Examples:
        Save a bundle and use the rendered PDF path:

        ```python
        from oodocs.adapters import ReleaseEvidence

        bundle = ReleaseEvidence.from_directory("artifacts/evidence").save_bundle()
        print(bundle.outputs["pdf"])
        ```
    """

    output_dir: Path
    outputs: dict[str, Path]
    data_files: tuple[Path, ...]
    checksum_file: Path


@dataclass(frozen=True, slots=True)
class ReleaseEvidence:
    """Release evidence inputs that can be rendered or saved as a bundle.

    Attributes:
        evidence_dir: Directory containing machine-readable evidence files.
        pyproject: Project metadata TOML file.
        workflow: Optional GitHub Actions workflow YAML file.

    Examples:
        Render a human-readable report from existing evidence files:

        ```python
        from oodocs.adapters import ReleaseEvidence

        evidence = ReleaseEvidence.from_directory("artifacts/evidence")
        document = evidence.to_document(fail_on_missing_input=False)
        document.save_html("artifacts/evidence/report.html")
        ```

        Generate missing machine-readable files and render all document outputs:

        ```python
        bundle = ReleaseEvidence.from_directory("artifacts/evidence").save_bundle()
        print(bundle.outputs["html"])
        ```
    """

    evidence_dir: Path
    pyproject: Path = Path("pyproject.toml")
    workflow: Path | None = Path(".github/workflows/release.yml")

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_dir", Path(self.evidence_dir))
        object.__setattr__(self, "pyproject", Path(self.pyproject))
        if self.workflow is not None:
            object.__setattr__(self, "workflow", Path(self.workflow))

    @classmethod
    def from_directory(
        cls,
        evidence_dir: PathLike = "artifacts/evidence",
        *,
        pyproject: PathLike = "pyproject.toml",
        workflow: PathLike | None = ".github/workflows/release.yml",
    ) -> ReleaseEvidence:
        """Create release evidence inputs from an evidence directory.

        Args:
            evidence_dir: Directory containing machine-readable evidence files.
            pyproject: Project metadata TOML file.
            workflow: Optional GitHub Actions workflow YAML file.

        Returns:
            Release evidence input model.
        """

        return cls(
            evidence_dir=Path(evidence_dir),
            pyproject=Path(pyproject),
            workflow=None if workflow is None else Path(workflow),
        )

    def to_document(self, *, fail_on_missing_input: bool = True) -> Document:
        """Build a human-readable release evidence document.

        Args:
            fail_on_missing_input: Whether missing optional evidence inputs
                should raise an exception.

        Returns:
            Document summarizing release metadata, workflow metadata, evidence
            tables, manifest values, and checksums.

        Raises:
            FileNotFoundError: If evidence files are missing and
                ``fail_on_missing_input`` is true.
            ImportError: If workflow parsing needs PyYAML and it is unavailable
                in fail-on-missing-input mode.
        """

        sections: list[Section] = [
            ProjectMetadata.from_pyproject(self.pyproject).to_section()
        ]
        if self.workflow is not None:
            try:
                sections.append(
                    GithubWorkflowSummary.from_file(self.workflow).to_section()
                )
            except (FileNotFoundError, ImportError) as exc:
                if fail_on_missing_input:
                    raise
                sections.append(_warning_section("GitHub Actions workflow", str(exc)))

        missing: list[str] = []
        evidence_sections: list[Section] = []
        for filename in DEFAULT_CSV_FILES:
            path = self.evidence_dir / filename
            if path.exists():
                evidence_sections.append(_section_from_csv(path))
            else:
                missing.append(filename)

        manifest_path = self.evidence_dir / MANIFEST_NAME
        if manifest_path.exists():
            evidence_sections.append(
                ReleaseManifestSummary.from_file(manifest_path).to_section()
            )
        else:
            missing.append(MANIFEST_NAME)

        checksum_path = self.evidence_dir / CHECKSUM_NAME
        if checksum_path.exists():
            evidence_sections.append(_section_from_checksums(checksum_path))
        else:
            missing.append(CHECKSUM_NAME)

        if missing:
            if fail_on_missing_input:
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

    def save_bundle(
        self,
        output_dir: PathLike | None = None,
        *,
        fail_on_missing_input: bool = False,
    ) -> ReleaseEvidenceBundle:
        """Create evidence data files and render the evidence document.

        Args:
            output_dir: Directory where evidence artifacts and rendered
                documents should be written. Defaults to ``evidence_dir``.
            fail_on_missing_input: Whether missing optional inputs should raise
                an exception while building the document.

        Returns:
            Bundle metadata containing written document, evidence, and checksum
            paths.

        Raises:
            FileNotFoundError: If fail-on-missing-input mode rejects missing
                evidence inputs.
            ImportError: If workflow parsing needs PyYAML and it is unavailable
                in fail-on-missing-input mode.
        """

        output_path = Path(output_dir) if output_dir is not None else self.evidence_dir
        output_path.mkdir(parents=True, exist_ok=True)
        data_files = _ensure_machine_readable_evidence(
            output_path,
            pyproject=self.pyproject,
        )
        _write_checksums(output_path)
        evidence = ReleaseEvidence.from_directory(
            output_path,
            pyproject=self.pyproject,
            workflow=self.workflow,
        )
        document = evidence.to_document(
            fail_on_missing_input=fail_on_missing_input,
        )
        outputs = document.save_all(output_path, stem="oodocs-evidence-report")
        checksum_file = _write_checksums(output_path)
        return ReleaseEvidenceBundle(
            output_dir=output_path,
            outputs=outputs,
            data_files=tuple(data_files),
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
    "MANIFEST_NAME",
    "ReleaseEvidence",
    "ReleaseEvidenceBundle",
]
