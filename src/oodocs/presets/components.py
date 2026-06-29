"""Reusable styled components built from the core block primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from oodocs.components.base import BlockInput
from oodocs.components.blocks import Box, CellInput
from oodocs.components.media import Table, TableCellInput
from oodocs.styles import BorderStyle, BoxStyle, Padding, TableStyle


NomenclatureEntry = tuple[TableCellInput, TableCellInput] | tuple[TableCellInput, TableCellInput, TableCellInput]


_CALLOUT_TITLES = {
    "info": "Info",
    "note": "Note",
    "success": "Success",
    "warning": "Warning",
}


class CalloutBox(Box):
    """A titled box preset backed by a named box style.

    Args:
        *children: Box content.
        title: Optional callout title. Defaults to a title derived from the
            named style when possible.
        style: Named box style or concrete box style.
        **box_options: Additional arguments forwarded to ``Box``.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, StyleSheet, Theme
        from oodocs.presets import CalloutBox

        styles = StyleSheet.default()
        doc = Document(
            "Review",
            CalloutBox("Check logs before release.", style="warning"),
            settings=DocumentSettings(theme=Theme(stylesheet=styles)),
        )
        ```
    """

    def __init__(
        self,
        *children: BlockInput,
        title: CellInput | None = None,
        style: BoxStyle | str | None = "info",
        **box_options: object,
    ) -> None:
        display_title = title if title is not None else _callout_title(style)
        super().__init__(
            *children,
            title=display_title,
            style=style,
            **box_options,
        )


class CompactTable(Table):
    """A table preset using the named compact table style.

    Args:
        headers: Header cells, header rows, or a dataframe-like object.
        rows: Body rows. Required unless ``headers`` is dataframe-like.
        style: Named table style or concrete table style.
        **table_options: Additional arguments forwarded to ``Table``.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.presets import CompactTable

        table = CompactTable(["Metric", "Value"], [["Latency", "42 ms"]])
        document = Document("Metrics", table)

        grouped = CompactTable.grouped_headers(
            groups=[("Geometry", 2), ("Performance", 2)],
            columns=["Width", "Height", "Latency", "Status"],
            rows=[["8.5 in", "11 in", "14 ms", "ok"]],
        )
        ```
    """

    def __init__(
        self,
        headers: Sequence[TableCellInput] | Sequence[Sequence[TableCellInput]] | object,
        rows: Sequence[Sequence[TableCellInput]] | None = None,
        *,
        style: TableStyle | str | None = "compact",
        **table_options: object,
    ) -> None:
        super().__init__(
            headers,
            rows,
            style=style,
            **table_options,
        )


class KeyValueTable(CompactTable):
    """A two-column table preset for metadata, settings, and option lists.

    Args:
        items: Mapping or key/value pair sequence.
        headers: Two column headers.
        caption: Optional table caption.
        style: Named table style or concrete table style.
        **table_options: Additional arguments forwarded to ``CompactTable``.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.presets import KeyValueTable

        table = KeyValueTable({"Environment": "prod", "Version": "1.2.0"})
        document = Document("Deployment", table)
        ```
    """

    def __init__(
        self,
        items: Mapping[object, object] | Sequence[tuple[object, object]],
        *,
        headers: tuple[str, str] = ("Field", "Value"),
        caption: CellInput | None = None,
        style: TableStyle | str | None = "compact",
        **table_options: object,
    ) -> None:
        pairs = items.items() if isinstance(items, Mapping) else items
        rows = [[str(key), str(value)] for key, value in pairs]
        super().__init__(
            headers,
            rows,
            caption=caption,
            style=style,
            **table_options,
        )


class Nomenclature(Box):
    """A boxed symbol list with no internal table rules.

    Args:
        entries: Sequence of ``(symbol, meaning)`` or
            ``(symbol, meaning, unit)`` tuples.
        double_column: Whether to split entries into two side-by-side groups.
        title: Optional box title.
        headers: Header labels for symbol, meaning, and unit columns.
        border: Box border style.
        padding: Box padding.
        table_style: Named table style or concrete style for the internal table.
        **box_options: Additional arguments forwarded to ``Box``.

    Raises:
        ValueError: If an entry does not have two or three values.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.presets import Nomenclature

        symbols = Nomenclature([("R", "Recall"), ("P", "Precision")], title="Symbols")
        document = Document("Model Report", symbols)
        ```
    """

    def __init__(
        self,
        entries: Sequence[NomenclatureEntry],
        *,
        double_column: bool = False,
        title: CellInput | None = None,
        headers: tuple[str, str, str] = ("Symbol", "Meaning", "Unit"),
        border: BorderStyle | None = None,
        padding: Padding | None = None,
        table_style: TableStyle | str | None = "nomenclature.inner",
        **box_options: object,
    ) -> None:
        normalized_entries = self._entries(entries)
        include_unit = any(unit is not None and unit != "" for _, _, unit in normalized_entries)
        header_group = list(headers if include_unit else headers[:2])
        rows = self._rows(
            normalized_entries,
            double_column=double_column,
            include_unit=include_unit,
        )
        table_headers = header_group + header_group if double_column else header_group
        table = Table(
            table_headers,
            rows,
            style=table_style,
        )
        super().__init__(
            table,
            title=title,
            border=border or BorderStyle.solid("111827", width=1.2),
            padding=padding or Padding.all(6.0),
            **box_options,
        )

    def _entries(
        self,
        entries: Sequence[NomenclatureEntry],
    ) -> list[tuple[TableCellInput, TableCellInput, TableCellInput | None]]:
        normalized: list[tuple[TableCellInput, TableCellInput, TableCellInput | None]] = []
        for entry in entries:
            if len(entry) == 2:
                symbol, meaning = entry
                normalized.append((symbol, meaning, None))
                continue
            if len(entry) == 3:
                symbol, meaning, unit = entry
                normalized.append((symbol, meaning, unit))
                continue
            raise ValueError("Nomenclature entries must be (symbol, meaning) or (symbol, meaning, unit)")
        return normalized

    def _rows(
        self,
        entries: Sequence[tuple[TableCellInput, TableCellInput, TableCellInput | None]],
        *,
        double_column: bool,
        include_unit: bool,
    ) -> list[list[TableCellInput]]:
        def cells(entry: tuple[TableCellInput, TableCellInput, TableCellInput | None]) -> list[TableCellInput]:
            symbol, meaning, unit = entry
            if include_unit:
                return [symbol, meaning, "" if unit is None else unit]
            return [symbol, meaning]

        if not double_column:
            return [cells(entry) for entry in entries]

        midpoint = (len(entries) + 1) // 2
        left = list(entries[:midpoint])
        right = list(entries[midpoint:])
        rows: list[list[TableCellInput]] = []
        for index, left_entry in enumerate(left):
            right_cells = cells(right[index]) if index < len(right) else [""] * (3 if include_unit else 2)
            rows.append([*cells(left_entry), *right_cells])
        return rows


def option_table(
    rows: Mapping[object, object] | Sequence[tuple[object, object]],
    *,
    caption: CellInput | None = None,
    **table_options: object,
) -> KeyValueTable:
    """Return a compact two-column table for documenting user-facing options.

    Args:
        rows: Mapping or option/value pair sequence.
        caption: Optional table caption.
        **table_options: Additional arguments forwarded to ``KeyValueTable``.

    Returns:
        Key/value table with option-oriented headers.

    Examples:
        ```python
        from oodocs.presets import option_table

        table = option_table({"timeout": "30 seconds", "retries": 3})
        ```
    """

    return KeyValueTable(rows, headers=("Option", "Default or meaning"), caption=caption, **table_options)


def note_box(
    *children: BlockInput,
    title: CellInput | None = None,
    style: BoxStyle | str | None = "note",
    **box_options: object,
) -> CalloutBox:
    """Return a note callout box.

    Args:
        *children: Box content.
        title: Optional callout title.
        style: Named box style or concrete box style.
        **box_options: Additional arguments forwarded to ``CalloutBox``.

    Returns:
        Note callout box.

    Examples:
        ```python
        from oodocs.presets import note_box

        box = note_box("Rendered documents include generated references.")
        ```
    """

    return CalloutBox(*children, title=title, style=style, **box_options)


def info_box(
    *children: BlockInput,
    title: CellInput | None = None,
    style: BoxStyle | str | None = "info",
    **box_options: object,
) -> CalloutBox:
    """Return an info callout box.

    Args:
        *children: Box content.
        title: Optional callout title.
        style: Named box style or concrete box style.
        **box_options: Additional arguments forwarded to ``CalloutBox``.

    Returns:
        Info callout box.

    Examples:
        ```python
        from oodocs.presets import info_box

        box = info_box("Rendered documents include generated references.")
        ```
    """

    return CalloutBox(*children, title=title, style=style, **box_options)


def warning_box(
    *children: BlockInput,
    title: CellInput | None = None,
    style: BoxStyle | str | None = "warning",
    **box_options: object,
) -> CalloutBox:
    """Return a warning callout box.

    Args:
        *children: Box content.
        title: Optional callout title.
        style: Named box style or concrete box style.
        **box_options: Additional arguments forwarded to ``CalloutBox``.

    Returns:
        Warning callout box.

    Examples:
        ```python
        from oodocs.presets import warning_box

        box = warning_box("Review this before publishing.")
        ```
    """

    return CalloutBox(*children, title=title, style=style, **box_options)


def success_box(
    *children: BlockInput,
    title: CellInput | None = None,
    style: BoxStyle | str | None = "success",
    **box_options: object,
) -> CalloutBox:
    """Return a success callout box.

    Args:
        *children: Box content.
        title: Optional callout title.
        style: Named box style or concrete box style.
        **box_options: Additional arguments forwarded to ``CalloutBox``.

    Returns:
        Success callout box.

    Examples:
        ```python
        from oodocs.presets import success_box

        box = success_box("Validation passed.")
        ```
    """

    return CalloutBox(*children, title=title, style=style, **box_options)


def _callout_title(style: BoxStyle | str | None) -> str:
    if not isinstance(style, str):
        return "Callout"
    normalized = style.strip().lower().removeprefix("box.")
    return _CALLOUT_TITLES.get(normalized, "Callout")


__all__ = [
    "CalloutBox",
    "CompactTable",
    "info_box",
    "KeyValueTable",
    "Nomenclature",
    "note_box",
    "option_table",
    "success_box",
    "warning_box",
]
