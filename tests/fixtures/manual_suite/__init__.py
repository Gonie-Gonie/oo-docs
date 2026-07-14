"""Compact, application-neutral acceptance fixture for renderer contracts."""

from .build_suite import (
    ASSET_NAMES,
    LONG_TABLE_ROW_COUNT,
    MANUAL_NAME,
    build_cli_application,
    build_manual,
    build_schema_catalog,
    build_suite,
)

__all__ = [
    "ASSET_NAMES",
    "LONG_TABLE_ROW_COUNT",
    "MANUAL_NAME",
    "build_cli_application",
    "build_manual",
    "build_schema_catalog",
    "build_suite",
]
