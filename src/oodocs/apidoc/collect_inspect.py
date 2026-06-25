"""Inspect-compatible API collector.

This backend currently uses source parsing instead of importing target modules
so ordinary repositories can be documented without installing their runtime
dependencies or executing import side effects.
"""

from __future__ import annotations

from dataclasses import replace

from oodocs.apidoc.config import ApiCollectConfig
from oodocs.apidoc.model import ApiDocIssue, ApiPackage
from oodocs.core import PathLike


def collect_package_inspect(
    package: str | PathLike,
    *,
    config: ApiCollectConfig,
) -> ApiPackage:
    """Collect package API metadata with inspect-compatible semantics.

    Args:
        package: Importable package/module name, Python file, or package
            directory.
        config: Collection config.

    Returns:
        Collected API package.
    """

    from oodocs.apidoc.collect import _collect_package_source

    resolved = replace(config, collector="inspect")
    api = _collect_package_source(package, config=resolved)
    api.issues.append(
        ApiDocIssue(
            "info",
            "inspect-source-collector",
            "Collected API metadata from source to avoid import side effects.",
        )
    )
    return api


__all__ = ["collect_package_inspect"]
