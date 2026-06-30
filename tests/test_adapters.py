from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from oodocs.adapters import (
    GithubWorkflowSummary,
    ProjectMetadata,
    ReleaseEvidence,
    ReleaseManifestSummary,
)
from oodocs.adapters.evidence import (
    CHECKSUM_NAME,
    MANIFEST_NAME,
    VALIDATION_RESULT_NAME,
    _manifest_payload,
)
from oodocs.validation import ValidationResult
from oodocs.components.blocks import Section
from oodocs.components.media import Table


def test_table_factories_replace_tabular_adapter_wrappers(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("name,value\nalpha,1\n", encoding="utf-8")

    records_table = Table.from_records([{"name": "alpha", "value": 1}])
    csv_table = Table.from_csv(csv_path)

    assert isinstance(records_table, Table)
    assert isinstance(csv_table, Table)
    assert csv_table.rows[0][0].content.plain_text() == "alpha"


def test_pyproject_and_manifest_adapters_create_sections(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "\n".join(
            [
                "[build-system]",
                'build-backend = "setuptools.build_meta"',
                "[project]",
                'name = "oodocs-test"',
                'requires-python = ">=3.11"',
                'description = "Test project"',
                'dependencies = ["Pillow"]',
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"tag": "v1.0.3", "commit": "abc"}), encoding="utf-8")

    pyproject_section = ProjectMetadata.from_pyproject(pyproject_path).to_section()
    manifest_section = ReleaseManifestSummary.from_file(manifest_path).to_section()

    assert isinstance(pyproject_section, Section)
    assert pyproject_section.children[1].rows[0][1].content.plain_text() == "oodocs-test"
    assert isinstance(manifest_section, Section)


def test_adapters_render_repository_source_paths_without_local_absolute_prefixes() -> None:
    pyproject_section = ProjectMetadata.from_pyproject(Path.cwd() / "pyproject.toml").to_section()
    manifest = ReleaseManifestSummary(
        source_path=Path.cwd() / "artifacts" / "evidence" / "manifest.json",
        data={"tag": "v1.0.0"},
    )
    manifest_section = manifest.to_section()

    assert pyproject_section.children[0].plain_text() == "Read from pyproject.toml."
    assert manifest_section.children[0].plain_text() == "Read from artifacts/evidence/manifest.json."


def test_release_evidence_manifest_uses_repository_relative_paths() -> None:
    payload = _manifest_payload(
        Path.cwd() / "artifacts" / "evidence",
        pyproject=Path.cwd() / "pyproject.toml",
    )

    assert payload["pyproject"] == "pyproject.toml"
    assert payload["evidence_dir"] == "artifacts/evidence"


def test_github_actions_adapter_uses_optional_yaml(tmp_path: Path) -> None:
    workflow_path = tmp_path / "release.yml"
    workflow_path.write_text(
        "jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )

    if importlib.util.find_spec("yaml") is None:
        with pytest.raises(ImportError, match="oodocs\\[adapters\\]"):
            GithubWorkflowSummary.from_file(workflow_path)
        return

    section = GithubWorkflowSummary.from_file(workflow_path).to_section()
    assert isinstance(section, Section)
    table = section.children[1]
    assert isinstance(table, Table)
    assert table.rows[0][0].content.plain_text() == "build"


def test_release_evidence_save_bundle_default_requires_existing_inputs(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "\n".join(
            [
                "[build-system]",
                'build-backend = "setuptools.build_meta"',
                "[project]",
                'name = "oodocs-test"',
                'requires-python = ">=3.11"',
                'description = "Test project"',
            ]
        ),
        encoding="utf-8",
    )
    evidence_dir = tmp_path / "evidence"

    with pytest.raises(FileNotFoundError, match="Missing release evidence"):
        ReleaseEvidence.from_directory(
            evidence_dir,
            pyproject=pyproject_path,
            workflow=None,
        ).save_bundle()

    assert not (evidence_dir / "feature-coverage.csv").exists()
    assert not (evidence_dir / VALIDATION_RESULT_NAME).exists()
    assert not (evidence_dir / MANIFEST_NAME).exists()


def test_release_evidence_ensure_inputs_then_save_bundle_renders_existing_inputs(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "\n".join(
            [
                "[build-system]",
                'build-backend = "setuptools.build_meta"',
                "[project]",
                'name = "oodocs-test"',
                'requires-python = ">=3.11"',
                'description = "Test project"',
            ]
        ),
        encoding="utf-8",
    )
    workflow_path = tmp_path / "missing-release.yml"
    evidence = ReleaseEvidence.from_directory(
        tmp_path / "evidence",
        pyproject=pyproject_path,
        workflow=workflow_path,
    )
    input_files = evidence.ensure_inputs()
    bundle = evidence.save_bundle(missing_input_policy="warn")

    assert (bundle.output_dir / "feature-coverage.csv").exists()
    assert (bundle.output_dir / VALIDATION_RESULT_NAME).exists()
    assert (bundle.output_dir / MANIFEST_NAME).exists()
    assert (bundle.output_dir / CHECKSUM_NAME).exists()
    assert bundle.outputs["html"].exists()
    assert bundle.outputs["docx"].exists()
    assert bundle.outputs["pdf"].exists()
    assert "oodocs-evidence-report.html" in bundle.outputs["html"].name
    assert any(path.name == CHECKSUM_NAME for path in input_files)
    assert any(path.name == VALIDATION_RESULT_NAME for path in input_files)
    assert any(path.name == VALIDATION_RESULT_NAME for path in bundle.data_files)
    assert any(path.name == MANIFEST_NAME for path in bundle.data_files)
    assert ValidationResult.load_json(bundle.output_dir / VALIDATION_RESULT_NAME).ok
    assert VALIDATION_RESULT_NAME in bundle.outputs["html"].read_text(encoding="utf-8")


def test_release_evidence_save_bundle_skeleton_policy_creates_machine_inputs(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nname = \"oodocs-test\"\n", encoding="utf-8")

    bundle = ReleaseEvidence.from_directory(
        tmp_path / "evidence",
        pyproject=pyproject_path,
        workflow=None,
    ).save_bundle(missing_input_policy="skeleton")

    assert (bundle.output_dir / "feature-coverage.csv").exists()
    assert (bundle.output_dir / VALIDATION_RESULT_NAME).exists()
    assert (bundle.output_dir / MANIFEST_NAME).exists()
    assert (bundle.output_dir / CHECKSUM_NAME).exists()
    assert bundle.outputs["html"].exists()


def test_release_evidence_to_document_missing_input_policy_error_requires_inputs(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nname = \"oodocs-test\"\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing release evidence"):
        ReleaseEvidence.from_directory(
            tmp_path / "empty",
            pyproject=pyproject_path,
            workflow=None,
        ).to_document(missing_input_policy="error")
