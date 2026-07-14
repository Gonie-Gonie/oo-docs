"""Collector for Python project metadata files."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import tomllib

from oodocs.metadata import ProjectInfo


def collect_pyproject_info(path: str | Path = "pyproject.toml") -> ProjectInfo:
    """Collect generic project information from a ``pyproject.toml`` file."""

    source_path = Path(path)
    data = tomllib.loads(source_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    build_system = data.get("build-system", {})
    return ProjectInfo(
        project=project if isinstance(project, Mapping) else {},
        build_system=build_system if isinstance(build_system, Mapping) else {},
        source_path=source_path,
    )


__all__ = ["collect_pyproject_info"]
