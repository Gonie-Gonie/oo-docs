"""Reusable styled components built from the core block primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from oodocs.components.base import BlockInput
from oodocs.components.blocks import Box, CellInput
from oodocs.components.media import Table, TableCellInput
from oodocs.layout.theme import BoxStyle, TableStyle


NomenclatureEntry = tuple[TableCellInput, TableCellInput] | tuple[TableCellInput, TableCellInput, TableCellInput]


_CALLOUT_VARIANTS: dict[str, dict[str, str]] = {
    "info": {
        "border_color": "3B82F6",
        "background_color": "EFF6FF",
        "title_background_color": "DBEAFE",
        "title_text_color": "1E3A8A",
    },
    "note": {
        "border_color": "64748B",
        "background_color": "F8FAFC",
        "title_background_color": "E2E8F0",
        "title_text_color": "0F172A",
    },
    "success": {
        "border_color": "16A34A",
        "background_color": "F0FDF4",
        "title_background_color": "DCFCE7",
        "title_text_color": "14532D",
    },
    "warning": {
        "border_color": "D97706",
        "background_color": "FFFBEB",
        "title_background_color": "FEF3C7",
        "title_text_color": "78350F",
    },
}


class CalloutBox(Box):
    """A titled box preset for notes, warnings, and reviewer-facing callouts.

    Args:
        *children: Box content.
        title: Optional callout title. Defaults to the variant title.
        variant: Visual variant name.
        style: Optional base box style.
        **style_overrides: Additional arguments forwarded to ``Box``.

    Raises:
        ValueError: If ``variant`` is unsupported.
    """

    def __init__(
        self,
        *children: BlockInput,
        title: CellInput | None = None,
        variant: str = "info",
        style: BoxStyle | None = None,
        **style_overrides: object,
    ) -> None:
        normalized_variant = variant.strip().lower()
        if normalized_variant not in _CALLOUT_VARIANTS:
            supported = ", ".join(sorted(_CALLOUT_VARIANTS))
            raise ValueError(f"Unsupported callout variant {variant!r}. Use one of: {supported}")
        base_style = style or BoxStyle(**_CALLOUT_VARIANTS[normalized_variant])
        display_title = title if title is not None else normalized_variant.title()
        super().__init__(
            *children,
            title=display_title,
            style=base_style,
            **style_overrides,
        )


class CompactTable(Table):
    """A denser table preset with smaller padding and subdued borders.

    Args:
        headers: Header cells, header rows, or a dataframe-like object.
        rows: Body rows. Required unless ``headers`` is dataframe-like.
        style: Optional base table style.
        **table_options: Additional arguments forwarded to ``Table``.
    """

    def __init__(
        self,
        headers: Sequence[TableCellInput] | Sequence[Sequence[TableCellInput]] | object,
        rows: Sequence[Sequence[TableCellInput]] | None = None,
        *,
        style: TableStyle | None = None,
        **table_options: object,
    ) -> None:
        super().__init__(
            headers,
            rows,
            style=style or TableStyle(
                header_background_color="F1F5F9",
                border_color="CBD5E1",
                cell_padding=3.0,
                border_width=0.4,
            ),
            **table_options,
        )


class KeyValueTable(CompactTable):
    """A two-column table preset for metadata, settings, and option lists.

    Args:
        items: Mapping or key/value pair sequence.
        headers: Two column headers.
        caption: Optional table caption.
        style: Optional base table style.
        **table_options: Additional arguments forwarded to ``CompactTable``.
    """

    def __init__(
        self,
        items: Mapping[object, object] | Sequence[tuple[object, object]],
        *,
        headers: tuple[str, str] = ("Field", "Value"),
        caption: CellInput | None = None,
        style: TableStyle | None = None,
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
        border_color: Box border color.
        border_width: Box border width.
        padding: Box padding.
        table_style: Optional style for the internal table.
        **box_options: Additional arguments forwarded to ``Box``.

    Raises:
        ValueError: If an entry does not have two or three values.
    """

    def __init__(
        self,
        entries: Sequence[NomenclatureEntry],
        *,
        double_column: bool = False,
        title: CellInput | None = None,
        headers: tuple[str, str, str] = ("Symbol", "Meaning", "Unit"),
        border_color: str = "111827",
        border_width: float = 1.2,
        padding: float = 6.0,
        table_style: TableStyle | None = None,
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
            style=table_style or TableStyle(
                header_background_color="FFFFFF",
                border_color="FFFFFF",
                border_width=0,
                cell_padding=2.0,
                repeat_header_rows=True,
            ),
        )
        super().__init__(
            table,
            title=title,
            border_color=border_color,
            border_width=border_width,
            padding=padding,
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
    """

    return KeyValueTable(rows, headers=("Option", "Default or meaning"), caption=caption, **table_options)


def note_box(*children: BlockInput, title: CellInput | None = None, **style_options: object) -> CalloutBox:
    """Return an info callout box.

    Args:
        *children: Box content.
        title: Optional callout title.
        **style_options: Additional arguments forwarded to ``CalloutBox``.

    Returns:
        Info variant callout box.
    """

    return CalloutBox(*children, title=title, variant="info", **style_options)


__all__ = [
    "CalloutBox",
    "CompactTable",
    "KeyValueTable",
    "Nomenclature",
    "note_box",
    "option_table",
]
