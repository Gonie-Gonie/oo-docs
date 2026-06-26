"""Adapters for Python project metadata."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import tomllib

from oodocs.components.blocks import Paragraph, Section
from oodocs.components.inline import inline_code
from oodocs.components.media import Table
from oodocs.core import PathLike
from oodocs.styles import TableStyle


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """Python project metadata read from ``pyproject.toml``.

    Attributes:
        source_path: TOML file used as the metadata source.
        project: ``[project]`` metadata table.
        build_system: ``[build-system]`` metadata table.

    Examples:
        Build an OODocs section from the current project's metadata:

        ```python
        from oodocs import Document
        from oodocs.adapters import ProjectMetadata

        metadata = ProjectMetadata.from_pyproject()
        doc = Document("Package Metadata", metadata.to_section())
        ```
    """

    source_path: Path
    project: Mapping[str, object]
    build_system: Mapping[str, object]

    @classmethod
    def from_pyproject(cls, path: PathLike = "pyproject.toml") -> ProjectMetadata:
        """Read Python project metadata from ``pyproject.toml``.

        Args:
            path: TOML file containing Python project metadata.

        Returns:
            Parsed project metadata.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            tomllib.TOMLDecodeError: If the file is not valid TOML.
        """

        source_path = Path(path)
        data = tomllib.loads(source_path.read_text(encoding="utf-8"))
        project = data.get("project", {})
        build_system = data.get("build-system", {})
        return cls(
            source_path=source_path,
            project=project if isinstance(project, Mapping) else {},
            build_system=build_system if isinstance(build_system, Mapping) else {},
        )

    def to_table(self, *, caption: str | None = None) -> Table:
        """Convert project metadata into an OODocs table.

        Args:
            caption: Optional table caption. A package metadata caption is used
                when omitted.

        Returns:
            Table containing common project and build-system fields.
        """

        rows = [
            ["name", str(self.project.get("name", ""))],
            ["version", str(self.project.get("version", "dynamic"))],
            ["requires-python", str(self.project.get("requires-python", ""))],
            ["description", str(self.project.get("description", ""))],
            ["dependencies", _string_list(self.project.get("dependencies", []))],
            ["build-backend", str(self.build_system.get("build-backend", ""))],
        ]
        return Table(
            ["Field", "Value"],
            rows,
            caption=caption or "Package metadata from pyproject.toml.",
            style=TableStyle.evidence(),
        )

    def to_section(self) -> Section:
        """Convert project metadata into an OODocs section.

        Returns:
            Section containing a source note and metadata table.
        """

        return Section(
            "Package metadata",
            Paragraph("Read from ", inline_code(self.source_path.as_posix()), "."),
            self.to_table(),
            numbered=False,
            toc=True,
        )


def _string_list(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value) if value else ""


__all__ = ["ProjectMetadata"]
