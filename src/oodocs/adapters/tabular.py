"""Tabular adapters built on OODocs table helpers."""

from __future__ import annotations

from typing import Sequence

from oodocs.components.media import Table
from oodocs.core import PathLike


def table_from_records(records: Sequence[object], **kwargs: object) -> Table:
    """Return a ``Table`` from ordinary Python records.

    Args:
        records: Sequence of mappings, dataclass instances, or ordinary
            objects accepted by ``Table.from_records``.
        **kwargs: Additional keyword arguments forwarded to
            ``Table.from_records``.

    Returns:
        Table built from the supplied records.

    Examples:
        ```python
        from oodocs.adapters import table_from_records

        table = table_from_records(
            [{"name": "docx", "status": "passed"}],
            caption="Renderer status",
        )
        ```
    """

    return Table.from_records(records, **kwargs)


def table_from_csv(path: PathLike, **kwargs: object) -> Table:
    """Return a ``Table`` from a CSV file.

    Args:
        path: CSV file to read.
        **kwargs: Additional keyword arguments forwarded to ``Table.from_csv``.

    Returns:
        Table built from the CSV file.

    Raises:
        FileNotFoundError: If ``path`` does not exist.

    Examples:
        ```python
        from oodocs.adapters import table_from_csv

        table = table_from_csv("artifacts/evidence/results.csv")
        ```
    """

    return Table.from_csv(path, **kwargs)


def table_from_tsv(path: PathLike, **kwargs: object) -> Table:
    """Return a ``Table`` from a TSV file.

    Args:
        path: TSV file to read.
        **kwargs: Additional keyword arguments forwarded to ``Table.from_tsv``.

    Returns:
        Table built from the TSV file.

    Raises:
        FileNotFoundError: If ``path`` does not exist.

    Examples:
        ```python
        from oodocs.adapters import table_from_tsv

        table = table_from_tsv("data/summary.tsv", caption="Summary rows")
        ```
    """

    return Table.from_tsv(path, **kwargs)


__all__ = ["table_from_csv", "table_from_records", "table_from_tsv"]
