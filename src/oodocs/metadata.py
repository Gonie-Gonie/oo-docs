"""Generic project, workflow, and manifest metadata models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

from oodocs._paths import display_path
from oodocs.components.blocks import Paragraph, Section
from oodocs.components.inline import inline_code
from oodocs.components.media import Table
from oodocs.styles import TableStyle


def _frozen_mapping(value: Mapping[str, object] | None) -> Mapping[str, object]:
    return MappingProxyType(dict(value or {}))


def _string_list(value: object) -> str:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return ", ".join(str(item) for item in value)
    return str(value) if value not in {None, ""} else ""


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    """Tool-neutral project metadata supplied as ordinary mappings."""

    project: Mapping[str, object] = field(default_factory=dict)
    build_system: Mapping[str, object] = field(default_factory=dict)
    source_path: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project", _frozen_mapping(self.project))
        object.__setattr__(self, "build_system", _frozen_mapping(self.build_system))
        if self.source_path is not None:
            object.__setattr__(self, "source_path", Path(self.source_path))

    def to_table(self, *, caption: str | None = None) -> Table:
        """Return common project metadata as an OODocs table."""

        rows = [
            ["name", str(self.project.get("name", ""))],
            ["version", str(self.project.get("version", "dynamic"))],
            ["requires-python", str(self.project.get("requires-python", ""))],
            ["description", str(self.project.get("description", ""))],
            ["dependencies", _string_list(self.project.get("dependencies", ()))],
            ["build-backend", str(self.build_system.get("build-backend", ""))],
        ]
        return Table(
            ["Field", "Value"],
            rows,
            caption=caption or "Project metadata.",
            style=TableStyle.evidence(),
        )

    def to_section(self, *, title: str = "Project metadata") -> Section:
        """Return project metadata as an OODocs section."""

        children: list[object] = []
        if self.source_path is not None:
            children.append(
                Paragraph("Read from ", inline_code(display_path(self.source_path)), ".")
            )
        children.append(self.to_table())
        return Section(title, children, numbered=False, toc=True)


@dataclass(frozen=True, slots=True)
class WorkflowJob:
    """One generic workflow job, independent of its source file format."""

    name: str
    runs_on: str = ""
    needs: tuple[str, ...] = ()
    steps: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name))
        object.__setattr__(self, "runs_on", str(self.runs_on))
        needs = self.needs
        if isinstance(needs, str):
            normalized_needs = (needs,) if needs else ()
        else:
            normalized_needs = tuple(str(item) for item in needs)
        object.__setattr__(self, "needs", normalized_needs)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> WorkflowJob:
        """Create a workflow job from a raw record."""

        raw_needs = value.get("needs", ())
        if isinstance(raw_needs, str):
            needs = (raw_needs,) if raw_needs else ()
        elif isinstance(raw_needs, Sequence):
            needs = tuple(str(item) for item in raw_needs)
        else:
            needs = ()
        raw_steps = value.get("steps")
        steps = raw_steps if isinstance(raw_steps, int) else None
        return cls(
            name=str(value.get("name", value.get("job", ""))),
            runs_on=str(value.get("runs_on", value.get("runs-on", ""))),
            needs=needs,
            steps=steps,
        )

    def as_record(self) -> dict[str, object]:
        """Return a raw table record."""

        return {
            "job": self.name,
            "runs-on": self.runs_on,
            "needs": ", ".join(self.needs),
            "steps": "" if self.steps is None else self.steps,
        }


@dataclass(frozen=True, slots=True)
class WorkflowSummary:
    """A generic workflow summary built from jobs or raw job mappings."""

    jobs: tuple[WorkflowJob, ...] = ()
    name: str = "Workflow"
    source_path: Path | None = None

    def __post_init__(self) -> None:
        normalized = tuple(
            item if isinstance(item, WorkflowJob) else WorkflowJob.from_mapping(item)
            for item in self.jobs
        )
        object.__setattr__(self, "jobs", normalized)
        if self.source_path is not None:
            object.__setattr__(self, "source_path", Path(self.source_path))

    def to_table(self, *, caption: str | None = None) -> Table:
        """Return workflow jobs as an OODocs table."""

        records = [job.as_record() for job in self.jobs]
        if not records:
            records = [{"job": "(none)", "runs-on": "", "needs": "", "steps": ""}]
        return Table.from_records(
            records,
            columns=["job", "runs-on", "needs", "steps"],
            headers=["Job", "Runs on", "Needs", "Steps"],
            caption=caption or f"Jobs in {self.name}.",
            style=TableStyle.evidence(),
        )

    def to_section(self, *, title: str | None = None) -> Section:
        """Return workflow metadata as an OODocs section."""

        children: list[object] = []
        if self.source_path is not None:
            children.append(
                Paragraph("Read from ", inline_code(display_path(self.source_path)), ".")
            )
        children.append(self.to_table())
        return Section(title or self.name, children, numbered=False, toc=True)


@dataclass(frozen=True, slots=True)
class ManifestSummary:
    """A generic manifest payload with optional source provenance."""

    data: object
    source_path: Path | None = None

    def __post_init__(self) -> None:
        if self.source_path is not None:
            object.__setattr__(self, "source_path", Path(self.source_path))

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
        *,
        source_path: str | Path | None = None,
    ) -> ManifestSummary:
        """Create a manifest summary from a raw mapping."""

        return cls(dict(value), None if source_path is None else Path(source_path))

    @classmethod
    def load_json(cls, path: str | Path) -> ManifestSummary:
        """Load a manifest summary from JSON."""

        source_path = Path(path)
        return cls(
            json.loads(source_path.read_text(encoding="utf-8")),
            source_path=source_path,
        )

    def as_mapping(self) -> Mapping[str, object]:
        """Return manifest data as a raw mapping when possible."""

        if not isinstance(self.data, Mapping):
            raise TypeError("Manifest data is not a mapping")
        return dict(self.data)

    def to_table(self, *, caption: str | None = None) -> Table:
        """Return the manifest payload as an OODocs table."""

        source_name = self.source_path.name if self.source_path is not None else "manifest"
        if isinstance(self.data, Mapping):
            return Table.from_mapping(
                self.data,
                caption=caption or f"Values from {source_name}.",
                style=TableStyle.evidence(),
            )
        if isinstance(self.data, list) and all(isinstance(item, Mapping) for item in self.data):
            return Table.from_records(
                self.data,
                caption=caption or f"Rows from {source_name}.",
                style=TableStyle.evidence(),
            )
        return Table(
            ["Value"],
            [[json.dumps(self.data, ensure_ascii=False)]],
            caption=caption or f"Value from {source_name}.",
            style=TableStyle.evidence(),
        )

    def to_section(self, *, title: str = "Manifest") -> Section:
        """Return the manifest summary as an OODocs section."""

        children: list[object] = []
        if self.source_path is not None:
            children.append(
                Paragraph("Read from ", inline_code(display_path(self.source_path)), ".")
            )
        children.append(self.to_table())
        return Section(title, children, numbered=False, toc=True)


__all__ = ["ManifestSummary", "ProjectInfo", "WorkflowJob", "WorkflowSummary"]
