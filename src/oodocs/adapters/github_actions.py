"""Adapters for GitHub Actions workflow metadata."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from oodocs.adapters._paths import _display_path
from oodocs.components.blocks import Paragraph, Section
from oodocs.components.inline import inline_code
from oodocs.components.media import Table
from oodocs.core import PathLike
from oodocs.styles import TableStyle


@dataclass(frozen=True, slots=True)
class GithubWorkflowSummary:
    """Summary of a GitHub Actions workflow file.

    Attributes:
        source_path: Workflow YAML file used as the metadata source.
        jobs: Job summary rows with ``job``, ``runs-on``, ``needs``, and
            ``steps`` values.

    Examples:
        Add release workflow metadata to a document:

        ```python
        from oodocs import Document
        from oodocs.adapters import GithubWorkflowSummary

        workflow = GithubWorkflowSummary.from_file(".github/workflows/release.yml")
        doc = Document("Release Workflow", workflow.to_section())
        ```
    """

    source_path: Path
    jobs: tuple[Mapping[str, object], ...]

    @classmethod
    def from_file(cls, path: PathLike) -> GithubWorkflowSummary:
        """Read a GitHub Actions workflow YAML file.

        Args:
            path: Workflow YAML file to read.

        Returns:
            Parsed workflow summary.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            ImportError: If PyYAML is not installed.
        """

        source_path = Path(path)
        workflow = _load_yaml(source_path)
        jobs = workflow.get("jobs", {}) if isinstance(workflow, Mapping) else {}
        rows: list[Mapping[str, object]] = []
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
        return cls(source_path=source_path, jobs=tuple(rows))

    def to_table(self, *, caption: str | None = None) -> Table:
        """Convert workflow jobs into an OODocs table.

        Args:
            caption: Optional table caption. A workflow summary caption is used
                when omitted.

        Returns:
            Table containing job runner, dependency, and step-count metadata.
        """

        return Table.from_records(
            self.jobs,
            columns=["job", "runs-on", "needs", "steps"],
            headers=["Job", "Runs on", "Needs", "Steps"],
            caption=caption or "GitHub Actions jobs in the release workflow.",
            style=TableStyle.evidence(),
        )

    def to_section(self) -> Section:
        """Convert workflow metadata into an OODocs section.

        Returns:
            Section containing a source note and job summary table.
        """

        return Section(
            "GitHub Actions workflow",
            Paragraph("Read from ", inline_code(_display_path(self.source_path)), "."),
            self.to_table(),
            numbered=False,
            toc=True,
        )


def _load_yaml(path: Path) -> object:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            "GithubWorkflowSummary.from_file requires PyYAML. Install with "
            "'pip install \"oodocs[adapters]\"'."
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _stringify_needs(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


__all__ = ["GithubWorkflowSummary"]
