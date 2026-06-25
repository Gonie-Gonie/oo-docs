"""Adapters for GitHub Actions workflow metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from oodocs.components.blocks import Paragraph, Section
from oodocs.components.inline import code
from oodocs.components.media import Table
from oodocs.core import PathLike
from oodocs.layout.theme import TableStyle


def section_from_github_workflow(path: PathLike) -> Section:
    """Create a summary section from a GitHub Actions workflow YAML file.

    Args:
        path: Workflow YAML file to read.

    Returns:
        Section containing a job summary table with runner, dependency, and
        step-count metadata.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ImportError: If PyYAML is not installed.
    """

    source_path = Path(path)
    workflow = _load_yaml(source_path)
    jobs = workflow.get("jobs", {}) if isinstance(workflow, Mapping) else {}
    rows = []
    if isinstance(jobs, Mapping):
        for job_name, job_config in jobs.items():
            # GitHub allows compact or non-mapping job definitions; preserve
            # the job name and leave unavailable metadata blank.
            if isinstance(job_config, Mapping):
                needs = job_config.get("needs", "")
                runs_on = job_config.get("runs-on", "")
                steps = job_config.get("steps", [])
                step_count = len(steps) if isinstance(steps, list) else ""
            else:
                needs = ""
                runs_on = ""
                step_count = ""
            rows.append(
                {
                    "job": str(job_name),
                    "runs-on": str(runs_on),
                    "needs": _stringify_needs(needs),
                    "steps": step_count,
                }
            )
    if not rows:
        rows.append({"job": "(none)", "runs-on": "", "needs": "", "steps": ""})

    return Section(
        "GitHub Actions workflow",
        Paragraph("Read from ", code(source_path.as_posix()), "."),
        Table.from_records(
            rows,
            columns=["job", "runs-on", "needs", "steps"],
            headers=["Job", "Runs on", "Needs", "Steps"],
            caption="GitHub Actions jobs in the release workflow.",
            style=TableStyle.evidence(),
        ),
        numbered=False,
        toc=True,
    )


def _load_yaml(path: Path) -> object:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            "section_from_github_workflow requires PyYAML. Install with "
            "'pip install \"oodocs[adapters]\"'."
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _stringify_needs(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


__all__ = ["section_from_github_workflow"]
