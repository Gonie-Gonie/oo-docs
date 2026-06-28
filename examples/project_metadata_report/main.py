"""Build a project metadata report from repository configuration files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Sequence

from oodocs import (
    Chapter,
    Document,
    DocumentSettings,
    OutputBundle,
    Paragraph,
    Table,
    TableOfContents,
    inline_code,
)
from oodocs.adapters import GithubWorkflowSummary, ProjectMetadata


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path("artifacts") / "project-metadata-report"
OUTPUT_STEM = "project-metadata-report"
METADATA_JSON = "project-metadata.json"


class ProjectMetadataReportBundle:
    """Rendered project metadata report outputs plus JSON sidecar."""

    def __init__(self, rendered: OutputBundle, metadata_json: Path) -> None:
        self.rendered = rendered
        self.metadata_json = metadata_json

    def __iter__(self):
        """Iterate over rendered document outputs."""

        return iter(self.rendered)

    def __getitem__(self, output_format: str) -> Path:
        """Return the rendered path for an output format."""

        return self.rendered[output_format]

    def keys(self):
        """Return rendered output format keys."""

        return self.rendered.keys()

    def values(self):
        """Return rendered output paths."""

        return self.rendered.values()

    def items(self):
        """Return rendered output pairs."""

        return self.rendered.items()


def repo_relative(path: Path) -> str:
    """Return a repository-relative source path when possible."""

    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_project_inputs(
    pyproject: str | Path = REPO_ROOT / "pyproject.toml",
    workflow: str | Path = REPO_ROOT / ".github" / "workflows" / "release.yml",
) -> tuple[ProjectMetadata, GithubWorkflowSummary]:
    """Load project metadata and release workflow summaries."""

    return (
        ProjectMetadata.from_pyproject(pyproject),
        load_workflow_summary(workflow),
    )


def load_workflow_summary(workflow: str | Path) -> GithubWorkflowSummary:
    """Load a workflow summary, using a small fallback when PyYAML is absent."""

    workflow_path = Path(workflow)
    try:
        return GithubWorkflowSummary.from_file(workflow_path)
    except ImportError:
        return GithubWorkflowSummary(
            source_path=workflow_path,
            jobs=tuple(_fallback_workflow_jobs(workflow_path)),
        )


def _fallback_workflow_jobs(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_jobs = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            if current is not None:
                rows.append(current)
            current = {"job": match.group(1), "runs-on": "", "needs": "", "steps": 0}
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("runs-on:"):
            current["runs-on"] = stripped.partition(":")[2].strip()
        elif stripped.startswith("needs:"):
            current["needs"] = stripped.partition(":")[2].strip()
        elif re.match(r"^-\s+(name:|uses:|run:)", stripped):
            current["steps"] = int(current["steps"]) + 1
    if current is not None:
        rows.append(current)
    return rows or [{"job": "(none)", "runs-on": "", "needs": "", "steps": ""}]


def write_metadata_sidecar(
    output_dir: str | Path,
    metadata: ProjectMetadata,
    workflow: GithubWorkflowSummary,
) -> Path:
    """Write project metadata and workflow job summaries as JSON."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sidecar_path = output_path / METADATA_JSON
    payload = {
        "pyproject": repo_relative(metadata.source_path),
        "workflow": repo_relative(workflow.source_path),
        "project": dict(metadata.project),
        "build_system": dict(metadata.build_system),
        "workflow_jobs": [dict(row) for row in workflow.jobs],
    }
    sidecar_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return sidecar_path


def build_document(
    pyproject: str | Path = REPO_ROOT / "pyproject.toml",
    workflow: str | Path = REPO_ROOT / ".github" / "workflows" / "release.yml",
) -> Document:
    """Build a report from project metadata and release workflow files."""

    metadata, workflow_summary = load_project_inputs(pyproject, workflow)
    source_table = Table(
        ["Source", "Purpose"],
        [
            [repo_relative(metadata.source_path), "Package metadata, Python requirement, dependencies, and build backend."],
            [repo_relative(workflow_summary.source_path), "Release jobs, runners, dependencies, and step counts."],
        ],
        caption="Repository configuration files used by this report.",
    )
    workflow_policy_table = Table(
        ["Workflow concern", "Documented signal"],
        [
            ["Build reproducibility", "The build backend and release jobs are visible in one report."],
            ["Release review", "The JSON sidecar keeps machine-readable metadata beside the rendered document."],
            ["Workflow drift", "Changes to pyproject or release.yml change the generated report in review."],
        ],
        caption="Project metadata report policy.",
    )

    return Document(
        "Project Metadata Report",
        TableOfContents(max_level=2),
        Chapter(
            "Configuration Sources",
            Paragraph(
                "This example turns repository configuration artifacts into normal OODocs sections. "
                "It uses ",
                inline_code("ProjectMetadata.from_pyproject(...)"),
                " and ",
                inline_code("GithubWorkflowSummary.from_file(...)"),
                ".",
            ),
            source_table,
        ),
        Chapter(
            "Package Metadata",
            metadata.to_section(),
        ),
        Chapter(
            "Release Workflow",
            workflow_summary.to_section(),
        ),
        Chapter(
            "Review Policy",
            workflow_policy_table,
            Paragraph(
                "Use this pattern when release reviewers need a readable report and a JSON sidecar from the same repository inputs."
            ),
        ),
        settings=DocumentSettings(
            metadata_author="OODocs Contributors",
            subtitle="pyproject.toml and GitHub Actions workflow as document inputs",
            summary="Project metadata report generated from repository configuration files",
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> ProjectMetadataReportBundle:
    """Render the project metadata report and write its JSON sidecar."""

    output_path = Path(output_dir)
    metadata, workflow = load_project_inputs()
    metadata_json = write_metadata_sidecar(output_path, metadata, workflow)
    document = build_document(metadata.source_path, workflow.source_path)
    document.validate(raise_on_error=True)
    rendered = document.save_all(
        output_path,
        stem=OUTPUT_STEM,
        formats=tuple(output_formats or ("docx", "pdf", "html")),
        verbose=verbose,
    )
    return ProjectMetadataReportBundle(rendered, metadata_json)


def main(argv: Sequence[str] | None = None) -> None:
    """Render the example from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs project metadata report example.",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        type=Path,
        help="Directory where rendered files are written.",
    )
    parser.add_argument(
        "--outputs",
        action="append",
        choices=("docx", "pdf", "html"),
        dest="output_formats",
        help="Output format to render. Repeat for multiple formats.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress and output-path messages.",
    )
    args = parser.parse_args(argv)

    outputs = build(
        args.output_dir,
        output_formats=args.output_formats,
        verbose=not args.quiet,
    )
    if not args.quiet:
        for output_format, path in outputs:
            print(f"Wrote {output_format}: {path}")
        print(f"Wrote metadata: {outputs.metadata_json}")


if __name__ == "__main__":
    main()
