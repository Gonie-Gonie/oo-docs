"""Internal source-path normalization helpers for API documentation."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath


def _safe_source_path_text(
    source_path: object,
    *,
    source_root: object | None = None,
) -> str | None:
    """Return a renderer-safe source path without local absolute prefixes."""

    text = str(source_path).strip()
    if not text:
        return None

    if source_root is not None:
        root_text = str(source_root).strip()
        if root_text:
            relative = _relative_to_source_root(text, root_text)
            if relative:
                return relative

    if _is_absolute_path_text(text) or _has_windows_drive(text):
        return _path_name_text(text)
    return _relative_path_text(text)


def _relative_to_source_root(source_path: str, source_root: str) -> str | None:
    try:
        return (
            Path(source_path)
            .resolve(strict=False)
            .relative_to(Path(source_root).resolve(strict=False))
            .as_posix()
        )
    except (OSError, ValueError):
        pass

    windows_relative = _pure_relative_to_source_root(
        PureWindowsPath(source_path),
        PureWindowsPath(source_root),
    )
    if windows_relative:
        return windows_relative

    return _pure_relative_to_source_root(
        PurePosixPath(source_path),
        PurePosixPath(source_root),
    )


def _pure_relative_to_source_root(
    source_path: PureWindowsPath | PurePosixPath,
    source_root: PureWindowsPath | PurePosixPath,
) -> str | None:
    if not source_path.is_absolute() or not source_root.is_absolute():
        return None
    try:
        return source_path.relative_to(source_root).as_posix()
    except ValueError:
        return None


def _is_absolute_path_text(text: str) -> bool:
    return (
        Path(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
        or PurePosixPath(text).is_absolute()
    )


def _has_windows_drive(text: str) -> bool:
    return bool(PureWindowsPath(text).drive)


def _path_name_text(text: str) -> str:
    if PureWindowsPath(text).is_absolute() or _has_windows_drive(text):
        return PureWindowsPath(text).name or "source"
    if PurePosixPath(text).is_absolute():
        return PurePosixPath(text).name or "source"
    return Path(text).name or "source"


def _relative_path_text(text: str) -> str:
    normalized = text.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized == ".." or normalized.startswith("../"):
        return PurePosixPath(normalized).name or "source"
    return normalized


__all__: list[str] = []
