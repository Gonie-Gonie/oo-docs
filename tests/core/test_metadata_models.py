from __future__ import annotations

import json
from pathlib import Path

from oodocs.metadata import ManifestSummary, ProjectInfo, WorkflowJob, WorkflowSummary
from oodocs.integrations.pyproject import collect_pyproject_info


def test_generic_metadata_models_accept_mappings_and_sequences(tmp_path: Path) -> None:
    project = ProjectInfo(
        project={"name": "sample", "dependencies": ["alpha", "beta"]},
        build_system={"build-backend": "sample.backend"},
    )
    workflow = WorkflowSummary(
        jobs=(
            WorkflowJob("test", runs_on="runner", needs=("lint",), steps=2),
            {"job": "publish", "runs-on": "runner", "needs": ["test"], "steps": 1},
        )
    )
    manifest = ManifestSummary.from_mapping({"version": "1.0", "commit": "abc"})

    assert project.to_table().rows[0][1].content.plain_text() == "sample"
    assert workflow.jobs[1].name == "publish"
    assert workflow.to_table().rows[0][0].content.plain_text() == "test"
    assert manifest.as_mapping() == {"version": "1.0", "commit": "abc"}

    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"status": "ready"}), encoding="utf-8")
    assert ManifestSummary.load_json(path).as_mapping()["status"] == "ready"


def test_pyproject_collector_is_separate_from_generic_model(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        "[build-system]\n"
        'build-backend = "sample.backend"\n'
        "[project]\n"
        'name = "sample"\n'
        'dependencies = ["alpha"]\n',
        encoding="utf-8",
    )

    info = collect_pyproject_info(path)

    assert isinstance(info, ProjectInfo)
    assert info.project["name"] == "sample"
    assert info.build_system["build-backend"] == "sample.backend"
