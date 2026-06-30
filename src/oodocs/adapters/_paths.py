from __future__ import annotations

from pathlib import Path


def _display_path(path: Path) -> str:
    """Return a stable, local-safe path for human-facing document text."""

    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()
