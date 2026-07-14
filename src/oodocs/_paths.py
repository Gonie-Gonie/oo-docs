"""Internal path display helpers."""

from __future__ import annotations

from pathlib import Path


def display_path(path: Path) -> str:
    """Return a stable path without exposing a local home-directory prefix."""

    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


__all__ = ["display_path"]
