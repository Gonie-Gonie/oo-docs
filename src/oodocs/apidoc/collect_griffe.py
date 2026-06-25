"""Griffe-compatible API collector."""

from __future__ import annotations

from dataclasses import replace

from oodocs.apidoc.config import ApiCollectConfig
from oodocs.apidoc.model import ApiDocIssue, ApiPackage
from oodocs.core import PathLike


def collect_package_griffe(
    package: str | PathLike,
    *,
    config: ApiCollectConfig,
) -> ApiPackage:
    """Collect package API metadata with griffe-compatible semantics.

    Args:
        package: Importable package/module name, Python file, or package
            directory.
        config: Collection config.

    Returns:
        Collected API package.

    Notes:
        The public schema intentionally matches the inspect-compatible backend.
        If ``griffe`` is not installed, this function still returns a source
        parsed package and records ``griffe-unavailable`` as an informational
        issue so explicit ``collector="griffe"`` calls remain usable.
    """

    from oodocs.apidoc.collect import _collect_package_source

    resolved = replace(config, collector="griffe")
    api = _collect_package_source(package, config=resolved)
    try:
        import griffe as _griffe  # noqa: F401
    except Exception:
        api.issues.append(
            ApiDocIssue(
                "info",
                "griffe-unavailable",
                "griffe is not installed; used source parsing with griffe-compatible output.",
            )
        )
    return api


__all__ = ["collect_package_griffe"]
