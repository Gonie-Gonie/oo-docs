from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from oodocs.adapters import (
    build_release_evidence_bundle,
    build_release_evidence_document,
    section_from_github_workflow,
    section_from_manifest,
    section_from_pyproject,
    table_from_csv,
    table_from_records,
)
from oodocs.adapters.evidence import CHECKSUM_NAME, MANIFEST_NAME
from oodocs.components.blocks import Section
from oodocs.components.media import Table


def test_tabular_adapter_wraps_table_helpers(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("name,value\nalpha,1\n", encoding="utf-8")

    records_table = table_from_records([{"name": "alpha", "value": 1}])
    csv_table = table_from_csv(csv_path)

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

    pyproject_section = section_from_pyproject(pyproject_path)
    manifest_section = section_from_manifest(manifest_path)

    assert isinstance(pyproject_section, Section)
    assert pyproject_section.children[1].rows[0][1].content.plain_text() == "oodocs-test"
    assert isinstance(manifest_section, Section)


def test_github_actions_adapter_uses_optional_yaml(tmp_path: Path) -> None:
    workflow_path = tmp_path / "release.yml"
    workflow_path.write_text(
        "jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )

    if importlib.util.find_spec("yaml") is None:
        with pytest.raises(ImportError, match="oodocs\\[adapters\\]"):
            section_from_github_workflow(workflow_path)
        return

    section = section_from_github_workflow(workflow_path)
    assert isinstance(section, Section)
    table = section.children[1]
    assert isinstance(table, Table)
    assert table.rows[0][0].content.plain_text() == "build"


def test_build_release_evidence_bundle_creates_machine_and_document_files(
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

    bundle = build_release_evidence_bundle(
        tmp_path / "evidence",
        pyproject=pyproject_path,
        workflow=workflow_path,
        fail_on_missing_input=False,
    )

    assert (bundle.output_dir / "feature-coverage.csv").exists()
    assert (bundle.output_dir / MANIFEST_NAME).exists()
    assert (bundle.output_dir / CHECKSUM_NAME).exists()
    assert bundle.document_outputs["html"].exists()
    assert bundle.document_outputs["docx"].exists()
    assert bundle.document_outputs["pdf"].exists()
    assert "oodocs-evidence-report.html" in bundle.document_outputs["html"].name


def test_build_release_evidence_document_fail_on_missing_input_requires_inputs(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nname = \"oodocs-test\"\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing release evidence"):
        build_release_evidence_document(
            pyproject=pyproject_path,
            workflow=None,
            evidence_dir=tmp_path / "empty",
            fail_on_missing_input=True,
        )
