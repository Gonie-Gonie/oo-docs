"""Collector for GitHub Actions workflow metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from oodocs.metadata import WorkflowJob, WorkflowSummary


def collect_github_actions_workflow(path: str | Path) -> WorkflowSummary:
    """Collect a generic workflow summary from a GitHub Actions YAML file."""

    source_path = Path(path)
    payload = _load_yaml(source_path)
    raw_jobs = payload.get("jobs", {}) if isinstance(payload, Mapping) else {}
    jobs: list[WorkflowJob] = []
    if isinstance(raw_jobs, Mapping):
        for job_name, raw_job in raw_jobs.items():
            config = raw_job if isinstance(raw_job, Mapping) else {}
            raw_needs = config.get("needs", ())
            if isinstance(raw_needs, str):
                needs = (raw_needs,) if raw_needs else ()
            elif isinstance(raw_needs, Sequence):
                needs = tuple(str(item) for item in raw_needs)
            else:
                needs = ()
            raw_steps = config.get("steps", ())
            steps = len(raw_steps) if isinstance(raw_steps, Sequence) else None
            jobs.append(
                WorkflowJob(
                    name=str(job_name),
                    runs_on=str(config.get("runs-on", "")),
                    needs=needs,
                    steps=steps,
                )
            )
    return WorkflowSummary(
        jobs=tuple(jobs),
        name="Workflow",
        source_path=source_path,
    )


def _load_yaml(path: Path) -> object:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            "Workflow collection requires PyYAML. Install with "
            "'pip install \"oodocs[integrations]\"'."
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


__all__ = ["collect_github_actions_workflow"]
