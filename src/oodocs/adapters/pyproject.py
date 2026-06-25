"""Adapters for Python project metadata."""

from __future__ import annotations

from pathlib import Path
import tomllib

from oodocs.components.blocks import Paragraph, Section
from oodocs.components.inline import code
from oodocs.components.media import Table
from oodocs.core import PathLike
from oodocs.layout.theme import TableStyle


def section_from_pyproject(path: PathLike = "pyproject.toml") -> Section:
    """Create a metadata section from ``pyproject.toml``.

    Args:
        path: TOML file containing Python project metadata.

    Returns:
        Section containing key project and build-system metadata.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """

    source_path = Path(path)
    data = tomllib.loads(source_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    build_system = data.get("build-system", {})
    rows = [
        ["name", str(project.get("name", ""))],
        ["version", str(project.get("version", "dynamic"))],
        ["requires-python", str(project.get("requires-python", ""))],
        ["description", str(project.get("description", ""))],
        ["dependencies", ", ".join(str(item) for item in project.get("dependencies", []))],
        ["build-backend", str(build_system.get("build-backend", ""))],
    ]
    return Section(
        "Package metadata",
        Paragraph("Read from ", code(source_path.as_posix()), "."),
        Table(
            ["Field", "Value"],
            rows,
            caption="Package metadata from pyproject.toml.",
            style=TableStyle.evidence(),
        ),
        numbered=False,
        toc=True,
    )


__all__ = ["section_from_pyproject"]
