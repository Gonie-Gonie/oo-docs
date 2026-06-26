"""Tables, figures, and related media components.

Attributes:
    MediaPlacement: Supported figure/table placement hints.
    TableSplit: Table splitting policy accepted by table rendering options.
    DEFAULT_LONG_TABLE_ROW_THRESHOLD: Row count where tables are treated as
        long tables by default.
    TableCellStyleInput: Accepted input for table-cell style coercion.
    TableCellInput: Accepted input for table cells.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, is_dataclass
import json
from io import BytesIO
from pathlib import Path
from typing import Callable, Literal, Mapping, Sequence, TYPE_CHECKING

from oodocs.components.base import Block
from oodocs.components.blocks import CellInput, Paragraph, coerce_cell
from oodocs.core import (
    PathLike,
    format_counter_value,
    length_to_inches,
    normalize_color,
    normalize_length_unit,
    normalize_text_alignment,
    normalize_vertical_alignment,
)
from oodocs.styles import (
    BorderStyle,
    Padding,
    TableCellStyle,
    TableCellStyleInput,
    TableStyle,
    TextStyle,
    coerce_table_cell_style,
    table_style_with_overrides,
)

if TYPE_CHECKING:
    from oodocs.components.inline import BlockReference, InlineInput
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext


MediaPlacement = Literal["auto", "here", "float", "top", "bottom", "page"]
TableSplit = bool | Literal["auto"]
DEFAULT_LONG_TABLE_ROW_THRESHOLD = 12


@dataclass(frozen=True, slots=True, init=False)
class ImageData:
    """In-memory image bytes usable anywhere a figure image source is accepted.

    Args:
        data: Image bytes or a ``BytesIO`` object.
        image_format: Image format name or extension.

    Raises:
        ValueError: If image data or image format is empty.

    Examples:
        ```python
        from oodocs import Document, Figure, ImageData

        image = ImageData(png_bytes, image_format="png")
        figure = Figure(image, caption="Generated chart")
        document = Document("Chart Report", figure)
        ```
    """

    data: bytes
    image_format: str

    def __init__(
        self,
        data: bytes | bytearray | memoryview | BytesIO,
        *,
        image_format: str = "png",
    ) -> None:
        if isinstance(data, BytesIO):
            image_bytes = data.getvalue()
        else:
            image_bytes = bytes(data)
        normalized_image_format = image_format.strip().lower().lstrip(".")
        if not image_bytes:
            raise ValueError("ImageData requires non-empty image bytes")
        if not normalized_image_format:
            raise ValueError("ImageData.image_format must not be empty")
        object.__setattr__(self, "data", image_bytes)
        object.__setattr__(self, "image_format", normalized_image_format)

    def savefig(self, target: object, **_: object) -> None:
        """Write the image bytes to a file-like target.

        Renderers already understand ``savefig``-compatible sources for plots;
        this adapter lets imported notebook images reuse that same path.

        Args:
            target: File-like object with ``write(bytes)``.
            **_: Ignored compatibility keyword arguments.
        """

        target.write(self.data)


def coerce_image_source(source: PathLike | object) -> object:
    """Normalize path-like or in-memory image inputs for media components.

    Args:
        source: Filesystem path, bytes-like object, ``BytesIO``, ``ImageData``,
            or plot-like object.

    Returns:
        ``Path`` for path-like input, ``ImageData`` for bytes input, or the
        original object for plot-like sources.

    Examples:
        ```python
        source = coerce_image_source("figures/chart.png")
        ```
    """

    if isinstance(source, ImageData):
        return source
    if isinstance(source, (bytes, bytearray, memoryview, BytesIO)):
        return ImageData(source)
    if isinstance(source, (str, Path)):
        return Path(source)
    return source


def image_source_to_buffer(
    source: object,
    *,
    image_format: str,
    image_dpi: int | None = None,
    usage: str = "image rendering",
) -> BytesIO:
    """Render an in-memory or plot-like image source into a byte buffer.

    Args:
        source: ``ImageData`` or object with ``savefig``.
        image_format: Output image format for ``savefig`` sources.
        image_dpi: Optional image DPI for ``savefig`` sources.
        usage: Human-readable usage included in error messages.

    Returns:
        Byte buffer positioned at the beginning.

    Raises:
        TypeError: If ``source`` cannot be rendered to image bytes.

    Examples:
        ```python
        buffer = image_source_to_buffer(ImageData(png_bytes), image_format="png")
        assert buffer.tell() == 0
        ```
    """

    if isinstance(source, ImageData):
        return BytesIO(source.data)
    if hasattr(source, "savefig"):
        buffer = BytesIO()
        save_kwargs: dict[str, object] = {"format": image_format}
        if image_dpi is not None:
            save_kwargs["dpi"] = image_dpi
        source.savefig(buffer, **save_kwargs)
        buffer.seek(0)
        return buffer
    raise TypeError(f"Unsupported image source for {usage}: {type(source)!r}")


def image_source_to_bytes(
    source: object,
    *,
    image_format: str,
    image_dpi: int | None = None,
    usage: str = "image rendering",
) -> bytes:
    """Return raw image bytes from an in-memory or plot-like image source.

    Args:
        source: ``ImageData`` or object with ``savefig``.
        image_format: Output image format for ``savefig`` sources.
        image_dpi: Optional image DPI for ``savefig`` sources.
        usage: Human-readable usage included in error messages.

    Returns:
        Raw image bytes.

    Raises:
        TypeError: If ``source`` cannot be rendered to image bytes.

    Examples:
        ```python
        data = image_source_to_bytes(ImageData(png_bytes), image_format="png")
        ```
    """

    if isinstance(source, ImageData):
        return source.data
    return image_source_to_buffer(
        source,
        image_format=image_format,
        image_dpi=image_dpi,
        usage=usage,
    ).getvalue()


def normalize_media_placement(value: str | None) -> MediaPlacement:
    """Normalize advanced table and figure placement options.

    Args:
        value: Placement name or shorthand. ``None`` resolves to ``"auto"``.

    Returns:
        Normalized placement value.

    Raises:
        ValueError: If the placement is unsupported.

    Examples:
        ```python
        assert normalize_media_placement("h") == "here"
        assert normalize_media_placement(None) == "auto"
        ```
    """

    if value is None:
        return "auto"
    normalized = value.strip().lower()
    aliases = {
        "h": "here",
        "here": "here",
        "float": "float",
        "tbp": "float",
        "htbp": "float",
        "t": "top",
        "top": "top",
        "b": "bottom",
        "bottom": "bottom",
        "p": "page",
        "page": "page",
        "auto": "auto",
    }
    placement = aliases.get(normalized)
    if placement is None:
        raise ValueError(f"Unsupported media placement: {value!r}")
    return placement  # type: ignore[return-value]


def normalize_table_split(value: TableSplit) -> TableSplit:
    """Normalize table splitting policy.

    Args:
        value: ``True``, ``False``, or ``"auto"``.

    Returns:
        The normalized table split policy.

    Raises:
        ValueError: If the value is unsupported.

    Examples:
        ```python
        assert normalize_table_split("auto") == "auto"
        assert normalize_table_split(True) is True
        ```
    """

    if isinstance(value, bool):
        return value
    if value == "auto":
        return value
    raise ValueError("Table split must be True, False, or 'auto'")


@dataclass(slots=True, init=False)
class TableCell:
    """A single table cell with optional row or column spanning.

    Args:
        value: Cell content.
        colspan: Number of columns this cell spans.
        rowspan: Number of rows this cell spans.
        style: Base cell style.
        background_color: Optional background color override.
        text_color: Optional text color override.
        bold: Optional bold override.
        italic: Optional italic override.
        text_alignment: Optional cell text alignment override.
        vertical_alignment: Optional vertical alignment override.

    Attributes:
        content: Cell content normalized to a paragraph.
        colspan: Number of rendered columns this cell spans.
        rowspan: Number of rendered rows this cell spans.
        background_color: Resolved cell background color.
        text_alignment: Resolved cell text alignment.
        vertical_alignment: Resolved vertical alignment.
        style: Resolved cell style after overrides are merged.

    Raises:
        ValueError: If ``colspan`` or ``rowspan`` is less than one.

    Examples:
        ```python
        from oodocs import Document, Table, TableCell

        header = TableCell("Model", colspan=2, bold=True)
        table = Table([[header]], [["Baseline", "v1"]])
        document = Document("Models", table)
        ```
    """

    content: Paragraph
    colspan: int
    rowspan: int
    background_color: str | None
    text_alignment: str | None
    vertical_alignment: str | None
    style: TableCellStyle

    def __init__(
        self,
        value: CellInput,
        *,
        colspan: int = 1,
        rowspan: int = 1,
        style: TableCellStyleInput | None = None,
        background_color: str | None = None,
        text_color: str | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        text_alignment: str | None = None,
        vertical_alignment: str | None = None,
    ) -> None:
        if colspan < 1:
            raise ValueError("TableCell.colspan must be >= 1")
        if rowspan < 1:
            raise ValueError("TableCell.rowspan must be >= 1")
        self.content = coerce_cell(value)
        self.colspan = colspan
        self.rowspan = rowspan
        base_style = (
            coerce_table_cell_style(style)
            if style is not None
            else TableCellStyle()
        )
        self.style = base_style.merged(
            TableCellStyle(
                background_color=background_color,
                text_color=text_color,
                bold=bold,
                italic=italic,
                text_alignment=text_alignment,
                vertical_alignment=vertical_alignment,
            )
        )
        self.background_color = self.style.background_color
        self.text_alignment = self.style.text_alignment
        self.vertical_alignment = self.style.vertical_alignment


TableCellInput = TableCell | CellInput


def coerce_table_cell(value: TableCellInput) -> TableCell:
    """Normalize supported cell inputs into a table cell.

    Args:
        value: Existing table cell or cell content.

    Returns:
        Table cell instance.

    Examples:
        ```python
        cell = coerce_table_cell("Accuracy")
        ```
    """

    if isinstance(value, TableCell):
        return value
    return TableCell(value)


def _is_nested_table_input(values: Sequence[object]) -> bool:
    if not values:
        return False
    return all(
        isinstance(item, Sequence) and not isinstance(item, (str, Paragraph, TableCell))
        for item in values
    )


def _coerce_table_matrix(
    values: Sequence[TableCellInput] | Sequence[Sequence[TableCellInput]],
) -> list[list[TableCell]]:
    items = list(values)
    if _is_nested_table_input(items):
        return [
            [coerce_table_cell(cell) for cell in row]
            for row in items
        ]  # type: ignore[arg-type]
    return [[coerce_table_cell(cell) for cell in items]]  # type: ignore[arg-type]


def _is_dataframe_like(value: object) -> bool:
    return hasattr(value, "columns") and (
        hasattr(value, "itertuples") or hasattr(value, "to_numpy")
    )


def _axis_labels(values: object) -> list[object]:
    if hasattr(values, "tolist"):
        return list(values.tolist())
    return list(values)


def _axis_names(values: object) -> tuple[str, ...]:
    names = getattr(values, "names", None)
    if names is not None:
        return tuple("" if name is None else str(name) for name in names)
    name = getattr(values, "name", None)
    return ("" if name is None else str(name),)


def _normalize_axis_values(values: object) -> list[tuple[str, ...]]:
    raw_values = _axis_labels(values)
    normalized: list[tuple[str, ...]] = []
    max_levels = (
        max(len(value) if isinstance(value, tuple) else 1 for value in raw_values)
        if raw_values
        else 1
    )
    for value in raw_values:
        if isinstance(value, tuple):
            parts = tuple("" if part is None else str(part) for part in value)
        else:
            parts = ("" if value is None else str(value),)
        normalized.append(parts + ("",) * (max_levels - len(parts)))
    return normalized


def _build_column_header_rows(column_values: list[tuple[str, ...]]) -> list[list[TableCell]]:
    if not column_values:
        return [[TableCell("")]]

    level_count = len(column_values[0])
    header_rows: list[list[TableCell]] = []
    for level in range(level_count):
        row: list[TableCell] = []
        column_index = 0
        while column_index < len(column_values):
            label = column_values[column_index][level]
            prefix = column_values[column_index][:level]
            if label == "":
                column_index += 1
                continue
            # Adjacent labels only merge when every parent level matches; this
            # preserves MultiIndex boundaries while still producing compact
            # spanning headers.
            colspan = 1
            while (
                column_index + colspan < len(column_values)
                and column_values[column_index + colspan][level] == label
                and column_values[column_index + colspan][:level] == prefix
            ):
                colspan += 1
            rowspan = 1
            if all(
                all(part == "" for part in column_values[offset][level + 1 :])
                for offset in range(column_index, column_index + colspan)
            ):
                rowspan = level_count - level
            row.append(TableCell(label, colspan=colspan, rowspan=rowspan))
            column_index += colspan
        header_rows.append(row)
    return header_rows


def _build_row_header_cells(index_values: list[tuple[str, ...]]) -> list[list[TableCell]]:
    if not index_values:
        return []

    row_headers: list[list[TableCell]] = [[] for _ in index_values]
    level_count = len(index_values[0])
    for level in range(level_count):
        row_index = 0
        while row_index < len(index_values):
            label = index_values[row_index][level]
            prefix = index_values[row_index][:level]
            rowspan = 1
            while (
                row_index + rowspan < len(index_values)
                and index_values[row_index + rowspan][level] == label
                and index_values[row_index + rowspan][:level] == prefix
            ):
                rowspan += 1
            row_headers[row_index].append(TableCell(label, rowspan=rowspan))
            row_index += rowspan
    return row_headers


def _dataframe_body_rows(dataframe: object, *, include_index: bool) -> list[list[TableCell]]:
    if hasattr(dataframe, "itertuples"):
        data_rows = [tuple(row) for row in dataframe.itertuples(index=False, name=None)]
    else:
        matrix = dataframe.to_numpy().tolist()  # type: ignore[call-arg]
        data_rows = [tuple(row) for row in matrix]

    body_rows: list[list[TableCell]] = []
    if include_index:
        index_values = _normalize_axis_values(dataframe.index)
        row_headers = _build_row_header_cells(index_values)
        for row_index, row_values in enumerate(data_rows):
            body_rows.append(
                row_headers[row_index]
                + [TableCell("" if value is None else str(value)) for value in row_values]
            )
        return body_rows

    for row_values in data_rows:
        body_rows.append([TableCell("" if value is None else str(value)) for value in row_values])
    return body_rows


def _dataframe_header_rows(dataframe: object, *, include_index: bool) -> list[list[TableCell]]:
    column_values = _normalize_axis_values(dataframe.columns)
    header_rows = _build_column_header_rows(column_values)
    if not include_index:
        return header_rows

    index_names = _axis_names(dataframe.index)
    if header_rows:
        header_rows[0] = [
            TableCell(name, rowspan=len(header_rows))
            for name in index_names
        ] + header_rows[0]
        return header_rows
    return [[TableCell(name) for name in index_names]]


@dataclass(slots=True)
class TablePlacement:
    """A positioned cell inside a rectangular table layout.

    Attributes:
        row: Zero-based rendered row index.
        column: Zero-based rendered column index.
        cell: Cell rendered at the position.
        header: Whether the placement belongs to a header row.
        body_row_index: Zero-based body row index when this is a body cell.

    Examples:
        ```python
        placement = TablePlacement(row=0, column=0, cell=TableCell("Metric"), header=True)
        ```
    """

    row: int
    column: int
    cell: TableCell
    header: bool
    body_row_index: int | None = None


@dataclass(slots=True)
class TableLayout:
    """Expanded rectangular table layout used by renderers.

    Attributes:
        row_count: Total rendered rows, including header rows.
        column_count: Total rendered columns after spans are expanded.
        header_row_count: Number of leading header rows.
        placements: Positioned cells that begin at each rendered grid location.

    Examples:
        ```python
        layout = build_table_layout([[TableCell("Metric")]], [[TableCell("Accuracy")]])
        assert layout.column_count == 1
        ```
    """

    row_count: int
    column_count: int
    header_row_count: int
    placements: list[TablePlacement]


def build_table_layout(
    header_rows: Sequence[Sequence[TableCell]],
    body_rows: Sequence[Sequence[TableCell]],
) -> TableLayout:
    """Expand spanned cells into positioned placements for renderer output.

    Args:
        header_rows: Header rows containing table cells.
        body_rows: Body rows containing table cells.

    Returns:
        Expanded rectangular layout used by renderers.

    Raises:
        ValueError: If row or column spans overlap.

    Examples:
        ```python
        header = [[TableCell("Metric"), TableCell("Value")]]
        body = [[TableCell("Latency"), TableCell("42 ms")]]
        layout = build_table_layout(header, body)
        assert layout.row_count == 2
        ```
    """

    all_rows = [(True, row, None) for row in header_rows] + [
        (False, row, body_row_index)
        for body_row_index, row in enumerate(body_rows)
    ]
    active_rowspans: dict[int, int] = {}
    placements: list[TablePlacement] = []
    column_count = 0

    for row_index, (is_header, row_cells, body_row_index) in enumerate(all_rows):
        pending_rowspans = {
            column: remaining - 1
            for column, remaining in active_rowspans.items()
            if remaining > 1
        }
        rowspans_from_current: dict[int, int] = {}
        column_index = 0
        for cell in row_cells:
            # Skip grid slots still occupied by rowspans from previous rows
            # before assigning the next authored cell.
            while active_rowspans.get(column_index, 0) > 0:
                column_index += 1
            placements.append(
                TablePlacement(
                    row=row_index,
                    column=column_index,
                    cell=cell,
                    header=is_header,
                    body_row_index=body_row_index,
                )
            )
            for offset in range(cell.colspan):
                column = column_index + offset
                if active_rowspans.get(column, 0) > 0:
                    raise ValueError("Table cell spans overlap")
                if cell.rowspan > 1:
                    rowspans_from_current[column] = cell.rowspan - 1
            column_index += cell.colspan

        column_count = max(
            column_count,
            column_index,
            (max(active_rowspans.keys(), default=-1) + 1) if active_rowspans else 0,
        )
        active_rowspans = pending_rowspans | rowspans_from_current

    if active_rowspans:
        column_count = max(column_count, max(active_rowspans.keys(), default=-1) + 1)

    return TableLayout(
        row_count=len(all_rows),
        column_count=column_count,
        header_row_count=len(header_rows),
        placements=placements,
    )


def _coerce_style_mapping(
    styles: Mapping[int, TableCellStyleInput] | None,
    *,
    name: str,
) -> dict[int, TableCellStyle]:
    if styles is None:
        return {}
    normalized: dict[int, TableCellStyle] = {}
    for key, value in styles.items():
        index = int(key)
        if index < 0:
            raise ValueError(f"{name} indexes must be >= 0")
        normalized[index] = coerce_table_cell_style(value)
    return normalized


RecordFormatter = Callable[[object], object] | str


def _record_mapping(value: object) -> Mapping[object, object] | None:
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return None


def _is_sequence_record(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray, memoryview, Paragraph, TableCell),
    )


def _formatter_for(
    column: object,
    formatters: Mapping[object, RecordFormatter] | None,
) -> RecordFormatter | None:
    if formatters is None:
        return None
    if column in formatters:
        return formatters[column]
    text_column = str(column)
    if text_column in formatters:
        return formatters[text_column]
    return None


def _stringify_data_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _format_data_value(
    value: object,
    *,
    column: object,
    formatters: Mapping[object, RecordFormatter] | None,
) -> str:
    formatter = _formatter_for(column, formatters)
    if formatter is None:
        return _stringify_data_value(value)
    if callable(formatter):
        return _stringify_data_value(formatter(value))
    return format(value, formatter)


def _record_value(
    record: object,
    column: object,
    *,
    strict: bool,
    missing: object,
) -> object:
    mapping = _record_mapping(record)
    if mapping is not None:
        if column in mapping:
            return mapping[column]
        if strict:
            raise ValueError(f"Record is missing column {column!r}")
        return missing

    if _is_sequence_record(record):
        try:
            index = int(column)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Sequence records require integer columns or headers-only column inference"
            ) from exc
        values = list(record)  # type: ignore[arg-type]
        if 0 <= index < len(values):
            return values[index]
        if strict:
            raise ValueError(f"Record is missing column index {index}")
        return missing

    raise TypeError(f"Unsupported record value: {type(record)!r}")


@dataclass(slots=True, init=False)
class Table(Block):
    """A table supporting explicit spans and dataframe-like inputs.

    Args:
        headers: Header cells, header rows, or a dataframe-like object when
            ``rows`` is omitted.
        rows: Body rows. Required unless ``headers`` is dataframe-like.
        caption: Optional table caption.
        column_widths: Optional widths for the expanded rendered columns.
        unit: Unit for ``column_widths``.
        identifier: Optional stable identifier for references or renderer use.
        style: Base table style.
        header_background_color: Optional header background color override.
        header_text_color: Optional header text color override.
        border: Optional border style override.
        body_background_color: Optional body background color override.
        alternate_row_background_color: Optional alternating row background.
        cell_text_alignment: Optional body cell text alignment.
        cell_vertical_alignment: Optional body cell vertical alignment.
        header_text_alignment: Optional header cell text alignment.
        header_vertical_alignment: Optional header vertical alignment.
        cell_padding: Optional cell padding override.
        repeat_header_rows: Whether fixed-page renderers repeat headers.
        include_index: Whether dataframe-like input includes index columns.
        split: Whether renderers may split the table across pages.
        placement: Optional placement policy.
        long_table_threshold: Row-count threshold for automatic splitting.
        row_styles: Optional body-row styles keyed by zero-based row index.
        column_styles: Optional column styles keyed by zero-based column index.
        header_row_styles: Optional header-row styles keyed by zero-based row
            index.

    Attributes:
        header_rows: Normalized header rows.
        rows: Normalized body rows.
        caption: Optional normalized caption paragraph.
        column_widths: Optional expanded column widths.
        unit: Unit for column widths.
        identifier: Stable identifier for references or renderer use.
        style: Resolved table style after overrides are merged.
        include_index: Whether dataframe-like input includes index columns.
        split: Effective split policy.
        placement: Effective media placement policy.
        long_table_threshold: Optional row-count threshold for splitting.
        row_styles: Resolved body-row style mapping.
        column_styles: Resolved column style mapping.
        header_row_styles: Resolved header-row style mapping.
        total_row_count: Total rendered row count, including header rows.

    Raises:
        ValueError: If rows are missing, thresholds are invalid, or column
            widths do not match the expanded layout.

    Examples:
        Build a table from explicit headers and rows:

        ```python
        from oodocs import BorderStyle, Document, Padding, Table

        table = Table(
            ["Metric", "Value"],
            [["Latency", "42 ms"], ["Errors", "0"]],
            caption="Service health",
            border=BorderStyle.solid("CBD5E1", width=0.5),
            cell_padding=Padding.symmetric(vertical=3, horizontal=5),
        )
        doc = Document("Status", table)
        ```

        Build a table from records and style a column:

        ```python
        from oodocs import Document, Table, TableCellStyle

        table = Table.from_records(
            [{"format": "docx", "status": "ok"}, {"format": "pdf", "status": "ok"}],
            caption="Renderer status",
            column_styles={1: TableCellStyle(text_color="166534", bold=True)},
        )
        doc = Document("Render Matrix", table)
        ```

    Notes:
        ``headers`` can be one row, multiple header rows, or a dataframe-like
        object when ``rows`` is omitted. Cell spans are expanded before
        rendering, so column widths and style mappings use rendered column
        indexes after spans are resolved.

    See Also:
        ``TableCell`` for spans and per-cell styling, ``TableStyle`` for
        renderer-neutral table defaults, and ``from_records``/
        ``from_dataframe`` for data-oriented constructors.
    """

    header_rows: list[list[TableCell]]
    rows: list[list[TableCell]]
    caption: Paragraph | None
    column_widths: list[float] | None
    unit: str | None
    identifier: str | None
    style: TableStyle
    include_index: bool
    split: TableSplit
    placement: MediaPlacement
    long_table_threshold: int | None
    row_styles: dict[int, TableCellStyle]
    column_styles: dict[int, TableCellStyle]
    header_row_styles: dict[int, TableCellStyle]

    def __init__(
        self,
        headers: Sequence[TableCellInput] | Sequence[Sequence[TableCellInput]] | object,
        rows: Sequence[Sequence[TableCellInput]] | None = None,
        *,
        caption: CellInput | None = None,
        column_widths: Sequence[float] | None = None,
        unit: str | None = None,
        identifier: str | None = None,
        style: TableStyle | None = None,
        header_background_color: str | None = None,
        header_text_color: str | None = None,
        border: BorderStyle | None = None,
        body_background_color: str | None = None,
        alternate_row_background_color: str | None = None,
        cell_text_alignment: str | None = None,
        cell_vertical_alignment: str | None = None,
        header_text_alignment: str | None = None,
        header_vertical_alignment: str | None = None,
        cell_padding: Padding | None = None,
        repeat_header_rows: bool | None = None,
        include_index: bool = False,
        split: TableSplit = False,
        placement: str | None = None,
        long_table_threshold: int | None = None,
        row_styles: Mapping[int, TableCellStyleInput] | None = None,
        column_styles: Mapping[int, TableCellStyleInput] | None = None,
        header_row_styles: Mapping[int, TableCellStyleInput] | None = None,
    ) -> None:
        if rows is None and _is_dataframe_like(headers):
            dataframe = headers
            self.header_rows = _dataframe_header_rows(
                dataframe,
                include_index=include_index,
            )
            self.rows = _dataframe_body_rows(dataframe, include_index=include_index)
        else:
            if rows is None:
                raise ValueError(
                    "rows is required unless the first argument is a dataframe-like object"
                )
            self.header_rows = _coerce_table_matrix(headers)  # type: ignore[arg-type]
            self.rows = [
                [coerce_table_cell(cell) for cell in row]
                for row in rows
            ]

        self.caption = coerce_cell(caption) if caption is not None else None
        self.column_widths = list(column_widths) if column_widths is not None else None
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.identifier = identifier
        self.style = table_style_with_overrides(
            style,
            header_background_color=header_background_color,
            header_text_color=header_text_color,
            border=border,
            body_background_color=body_background_color,
            alternate_row_background_color=alternate_row_background_color,
            cell_text_alignment=cell_text_alignment,
            cell_vertical_alignment=cell_vertical_alignment,
            header_text_alignment=header_text_alignment,
            header_vertical_alignment=header_vertical_alignment,
            cell_padding=cell_padding,
            repeat_header_rows=repeat_header_rows,
        )
        self.include_index = include_index
        self.split = normalize_table_split(split)
        self.placement = normalize_media_placement(placement)
        if long_table_threshold is not None and long_table_threshold < 1:
            raise ValueError("long_table_threshold must be >= 1")
        self.long_table_threshold = long_table_threshold
        self.row_styles = _coerce_style_mapping(row_styles, name="row_styles")
        self.column_styles = _coerce_style_mapping(column_styles, name="column_styles")
        self.header_row_styles = _coerce_style_mapping(
            header_row_styles,
            name="header_row_styles",
        )

        layout = self._layout()
        if self.column_widths is not None and len(self.column_widths) != layout.column_count:
            raise ValueError("column_widths must match the expanded number of table columns")

    @property
    def headers(self) -> list[TableCell]:
        """Return the first header row for compatibility with older code.

        Returns:
            The first header row.
        """

        return self.header_rows[0]

    def _layout(self) -> TableLayout:
        return build_table_layout(self.header_rows, self.rows)

    @property
    def total_row_count(self) -> int:
        """Return the total rendered row count, including headers.

        Returns:
            Header row count plus body row count.
        """

        return len(self.header_rows) + len(self.rows)

    def _resolve_split(self, default_threshold: int = DEFAULT_LONG_TABLE_ROW_THRESHOLD) -> bool:
        if self.split is True:
            return True
        threshold = self.long_table_threshold or default_threshold
        return self.total_row_count > threshold

    def _resolve_placement(self, default_threshold: int = DEFAULT_LONG_TABLE_ROW_THRESHOLD) -> MediaPlacement:
        if self.split is True or self._resolve_split(default_threshold):
            return "here"
        if self.placement == "auto":
            return "float"
        return self.placement

    def _effective_cell_style(self, placement: TablePlacement) -> TableCellStyle:
        row_style = (
            self.header_row_styles.get(placement.row)
            if placement.header
            else (
                self.row_styles.get(placement.body_row_index)
                if placement.body_row_index is not None
                else None
            )
        )
        return self._base_cell_style(placement).merged(
            self.column_styles.get(placement.column),
            row_style,
            placement.cell.style,
        )

    def _base_cell_style(self, placement: TablePlacement) -> TableCellStyle:
        if placement.header:
            return TableCellStyle(
                background_color=self.style.header_background_color,
                text_color=self.style.header_text_color,
                bold=True,
                text_alignment=self.style.header_text_alignment,
                vertical_alignment=self.style.header_vertical_alignment,
            )

        background_color = self.style.body_background_color
        if (
            self.style.alternate_row_background_color is not None
            and placement.body_row_index is not None
            and placement.body_row_index % 2 == 1
        ):
            background_color = self.style.alternate_row_background_color
        return TableCellStyle(
            background_color=background_color,
            text_alignment=self.style.cell_text_alignment,
            vertical_alignment=self.style.cell_vertical_alignment,
        )

    def _column_widths_in_inches(self, default_unit: str) -> list[float] | None:
        if self.column_widths is None:
            return None
        unit = self.unit or default_unit
        return [length_to_inches(width, unit) for width in self.column_widths]

    @classmethod
    def from_dataframe(
        cls,
        dataframe: object,
        *,
        caption: CellInput | None = None,
        column_widths: Sequence[float] | None = None,
        unit: str | None = None,
        identifier: str | None = None,
        style: TableStyle | None = None,
        header_background_color: str | None = None,
        header_text_color: str | None = None,
        border: BorderStyle | None = None,
        body_background_color: str | None = None,
        alternate_row_background_color: str | None = None,
        cell_text_alignment: str | None = None,
        cell_vertical_alignment: str | None = None,
        header_text_alignment: str | None = None,
        header_vertical_alignment: str | None = None,
        cell_padding: Padding | None = None,
        repeat_header_rows: bool | None = None,
        include_index: bool = False,
        split: TableSplit = False,
        placement: str | None = None,
        long_table_threshold: int | None = None,
        row_styles: Mapping[int, TableCellStyleInput] | None = None,
        column_styles: Mapping[int, TableCellStyleInput] | None = None,
        header_row_styles: Mapping[int, TableCellStyleInput] | None = None,
    ) -> Table:
        """Create a table directly from a dataframe-like object.

        Args:
            dataframe: Object with dataframe-like columns and rows.
            caption: Optional table caption.
            column_widths: Optional widths for expanded rendered columns.
            unit: Unit for ``column_widths``.
            identifier: Optional stable identifier.
            style: Base table style.
            header_background_color: Optional header background color override.
            header_text_color: Optional header text color override.
            border: Optional border style override.
            body_background_color: Optional body background color override.
            alternate_row_background_color: Optional alternating row background.
            cell_text_alignment: Optional body cell text alignment.
            cell_vertical_alignment: Optional body cell vertical alignment.
            header_text_alignment: Optional header cell text alignment.
            header_vertical_alignment: Optional header vertical alignment.
            cell_padding: Optional cell padding override.
            repeat_header_rows: Whether fixed-page renderers repeat headers.
            include_index: Whether to include dataframe index columns.
            split: Whether renderers may split the table across pages.
            placement: Optional placement policy.
            long_table_threshold: Row-count threshold for automatic splitting.
            row_styles: Optional body-row styles.
            column_styles: Optional column styles.
            header_row_styles: Optional header-row styles.

        Returns:
            Table built from the dataframe-like object.

        Examples:
            ```python
            from oodocs import Table

            table = Table.from_dataframe(df, caption="Experiment results")
            ```
        """

        return cls(
            dataframe,
            caption=caption,
            column_widths=column_widths,
            unit=unit,
            identifier=identifier,
            style=style,
            header_background_color=header_background_color,
            header_text_color=header_text_color,
            border=border,
            body_background_color=body_background_color,
            alternate_row_background_color=alternate_row_background_color,
            cell_text_alignment=cell_text_alignment,
            cell_vertical_alignment=cell_vertical_alignment,
            header_text_alignment=header_text_alignment,
            header_vertical_alignment=header_vertical_alignment,
            cell_padding=cell_padding,
            repeat_header_rows=repeat_header_rows,
            include_index=include_index,
            split=split,
            placement=placement,
            long_table_threshold=long_table_threshold,
            row_styles=row_styles,
            column_styles=column_styles,
            header_row_styles=header_row_styles,
        )

    @classmethod
    def from_records(
        cls,
        records: Sequence[object],
        *,
        columns: Sequence[object] | None = None,
        headers: Sequence[TableCellInput] | None = None,
        formatters: Mapping[object, RecordFormatter] | None = None,
        missing: object = "",
        strict: bool = False,
        **table_kwargs: object,
    ) -> Table:
        """Create a table from mappings, dataclasses, or sequence records.

        Args:
            records: Source records.
            columns: Column keys or sequence indexes to extract.
            headers: Optional visible header cells.
            formatters: Optional per-column callable or format-spec strings.
            missing: Value used when a record is missing a column and
                ``strict`` is false.
            strict: Whether missing columns raise errors.
            **table_kwargs: Additional arguments forwarded to ``Table``.

        Returns:
            Table built from record data.

        Raises:
            ValueError: If columns cannot be inferred or headers do not match.
            TypeError: If a record type is unsupported.

        Examples:
            ```python
            from oodocs import Table

            table = Table.from_records(
                [{"name": "docx", "status": "ok"}, {"name": "pdf", "status": "ok"}],
                caption="Renderer status",
            )
            ```
        """

        record_list = list(records)
        if columns is None:
            # Prefer mapping keys when available; sequence records need explicit
            # headers so column indexes can be inferred unambiguously.
            if not record_list:
                raise ValueError("columns is required when records is empty")
            first_mapping = _record_mapping(record_list[0])
            if first_mapping is not None:
                normalized_columns = list(first_mapping.keys())
            elif _is_sequence_record(record_list[0]) and headers is not None:
                normalized_columns = list(range(len(headers)))
            else:
                raise ValueError("columns or headers is required for sequence records")
        else:
            normalized_columns = list(columns)

        if not normalized_columns:
            raise ValueError("columns must not be empty")

        if headers is None:
            normalized_headers: Sequence[TableCellInput] = [
                str(column)
                for column in normalized_columns
            ]
        else:
            if len(headers) != len(normalized_columns):
                raise ValueError("headers must match the number of columns")
            normalized_headers = headers

        rows = [
            [
                _format_data_value(
                    _record_value(
                        record,
                        column,
                        strict=strict,
                        missing=missing,
                    ),
                    column=column,
                    formatters=formatters,
                )
                for column in normalized_columns
            ]
            for record in record_list
        ]
        return cls(normalized_headers, rows, **table_kwargs)

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[object, object],
        *,
        key_header: TableCellInput = "Field",
        value_header: TableCellInput = "Value",
        key_formatter: Callable[[object], object] | str | None = None,
        value_formatter: Callable[[object], object] | str | None = None,
        **table_kwargs: object,
    ) -> Table:
        """Create a two-column table from a mapping.

        Args:
            mapping: Source key/value pairs.
            key_header: Header for the key column.
            value_header: Header for the value column.
            key_formatter: Callable or format-spec string for keys.
            value_formatter: Callable or format-spec string for values.
            **table_kwargs: Additional arguments forwarded to ``Table``.

        Returns:
            Two-column table.

        Raises:
            ValueError: If ``mapping`` is empty.

        Examples:
            ```python
            from oodocs import Table

            table = Table.from_mapping(
                {"package": "oodocs", "version": "1.0.4"},
                caption="Build metadata",
            )
            ```
        """

        if not mapping:
            raise ValueError("mapping must not be empty")

        def format_side(value: object, formatter: Callable[[object], object] | str | None) -> str:
            if formatter is None:
                return _stringify_data_value(value)
            if callable(formatter):
                return _stringify_data_value(formatter(value))
            return format(value, formatter)

        rows = [
            [
                format_side(key, key_formatter),
                format_side(value, value_formatter),
            ]
            for key, value in mapping.items()
        ]
        return cls([key_header, value_header], rows, **table_kwargs)

    @classmethod
    def from_csv(
        cls,
        path: PathLike,
        *,
        headers: bool | Sequence[TableCellInput] = True,
        encoding: str = "utf-8-sig",
        delimiter: str = ",",
        **table_kwargs: object,
    ) -> Table:
        """Create a table from a CSV file.

        Args:
            path: CSV file path.
            headers: ``True`` to use the first row, ``False`` to generate
                generic headers, or explicit header cells.
            encoding: File encoding.
            delimiter: CSV delimiter.
            **table_kwargs: Additional arguments forwarded to ``Table``.

        Returns:
            Table built from the CSV rows.

        Raises:
            ValueError: If the file has no rows.

        Examples:
            ```python
            from oodocs import Table

            table = Table.from_csv("artifacts/evidence/results.csv", caption="Results")
            ```
        """

        with Path(path).open("r", encoding=encoding, newline="") as handle:
            matrix = list(csv.reader(handle, delimiter=delimiter))
        if not matrix:
            raise ValueError("CSV file must contain at least one row")

        if headers is True:
            table_headers = matrix[0]
            rows = matrix[1:]
        elif headers is False:
            column_count = max(len(row) for row in matrix)
            table_headers = [f"Column {index + 1}" for index in range(column_count)]
            rows = matrix
        else:
            table_headers = list(headers)
            rows = matrix
        return cls(table_headers, rows, **table_kwargs)

    @classmethod
    def from_tsv(
        cls,
        path: PathLike,
        *,
        headers: bool | Sequence[TableCellInput] = True,
        encoding: str = "utf-8-sig",
        **table_kwargs: object,
    ) -> Table:
        """Create a table from a TSV file.

        Args:
            path: TSV file path.
            headers: ``True`` to use the first row, ``False`` to generate
                generic headers, or explicit header cells.
            encoding: File encoding.
            **table_kwargs: Additional arguments forwarded to ``Table``.

        Returns:
            Table built from the TSV rows.

        Examples:
            ```python
            from oodocs import Table

            table = Table.from_tsv("data/summary.tsv", caption="Summary")
            ```
        """

        return cls.from_csv(
            path,
            headers=headers,
            encoding=encoding,
            delimiter="\t",
            **table_kwargs,
        )

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this table into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_table(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this table into PDF flowables.

        Returns:
            ReportLab flowables for this table.
        """

        return renderer.render_table(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this table into HTML markup.

        Returns:
            HTML markup for this table.
        """

        return renderer.render_table(self, context)


@dataclass(slots=True, init=False)
class Figure(Block):
    """An image block backed by a path or ``savefig()``-compatible object.

    Args:
        image_source: Path, image bytes, ``ImageData``, or plot-like object.
        caption: Optional figure caption.
        width: Optional rendered width.
        height: Optional rendered height.
        identifier: Optional stable identifier.
        unit: Unit for width and height.
        image_format: Image format for plot-like sources.
        image_dpi: Optional image DPI for plot-like sources.
        placement: Optional placement policy.

    Examples:
        Add an image from a file path:

        ```python
        from oodocs import Document, Figure

        figure = Figure("figures/architecture.png", caption="System architecture", width=4)
        document = Document("Architecture", figure)
        ```

        Add a plot-like object that supports ``savefig()``:

        ```python
        import matplotlib.pyplot as plt
        from oodocs import Document, Figure

        plot, axes = plt.subplots()
        axes.plot([1, 2, 3], [3, 1, 4])
        document = Document("Experiment", Figure(plot, caption="Measured values"))
        ```

    Notes:
        Paths are passed through to renderers, while bytes and ``BytesIO`` are
        wrapped as ``ImageData``. Plot-like objects are rendered through
        ``savefig()`` using ``image_format`` and ``image_dpi``.

    See Also:
        ``ImageData`` for in-memory images and ``SubFigureGroup`` for grouped
        figure layouts.
    """

    image_source: object
    caption: Paragraph | None
    width: float | None
    height: float | None
    unit: str | None
    identifier: str | None
    image_format: str
    image_dpi: int | None
    placement: MediaPlacement

    def __init__(
        self,
        image_source: PathLike | object,
        caption: CellInput | None = None,
        width: float | None = None,
        height: float | None = None,
        identifier: str | None = None,
        *,
        unit: str | None = None,
        image_format: str = "png",
        image_dpi: int | None = 150,
        placement: str | None = None,
    ) -> None:
        self.image_source = coerce_image_source(image_source)
        self.caption = coerce_cell(caption) if caption is not None else None
        self.width = width
        self.height = height
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.identifier = identifier
        self.image_format = (
            self.image_source.image_format
            if isinstance(self.image_source, ImageData) and image_format == "png"
            else image_format
        )
        self.image_dpi = image_dpi
        self.placement = normalize_media_placement(placement)

    @classmethod
    def from_bytes(
        cls,
        data: bytes | bytearray | memoryview,
        *,
        image_format: str = "png",
        **figure_kwargs: object,
    ) -> Figure:
        """Create a figure from in-memory image bytes.

        Args:
            data: Image bytes.
            image_format: Image format name or extension.
            **figure_kwargs: Additional arguments forwarded to ``Figure``.

        Returns:
            Figure using in-memory image bytes.

        Examples:
            ```python
            figure = Figure.from_bytes(png_bytes, caption="Generated plot")
            ```
        """

        return cls(
            ImageData(data, image_format=image_format),
            image_format=image_format,
            **figure_kwargs,
        )

    @classmethod
    def from_buffer(
        cls,
        buffer: BytesIO | object,
        *,
        image_format: str = "png",
        **figure_kwargs: object,
    ) -> Figure:
        """Create a figure from a readable or ``getvalue``-compatible buffer.

        Args:
            buffer: Object providing ``getvalue()`` or ``read()``.
            image_format: Image format name or extension.
            **figure_kwargs: Additional arguments forwarded to ``Figure``.

        Returns:
            Figure using the buffer's image bytes.

        Raises:
            TypeError: If ``buffer`` does not provide ``getvalue`` or ``read``.

        Examples:
            ```python
            from io import BytesIO

            figure = Figure.from_buffer(BytesIO(png_bytes), image_format="png")
            ```
        """

        if hasattr(buffer, "getvalue"):
            data = buffer.getvalue()
        elif hasattr(buffer, "read"):
            data = buffer.read()
        else:
            raise TypeError("buffer must provide getvalue() or read()")
        return cls.from_bytes(data, image_format=image_format, **figure_kwargs)

    def width_in_inches(self, default_unit: str) -> float | None:
        """Return figure width converted through the figure or document unit.

        Args:
            default_unit: Unit to use when the figure has no explicit unit.

        Returns:
            Width in inches, or ``None`` for automatic sizing.
        """

        if self.width is None:
            return None
        return length_to_inches(self.width, self.unit or default_unit)

    def height_in_inches(self, default_unit: str) -> float | None:
        """Return figure height converted through the figure or document unit.

        Args:
            default_unit: Unit to use when the figure has no explicit unit.

        Returns:
            Height in inches, or ``None`` for automatic sizing.
        """

        if self.height is None:
            return None
        return length_to_inches(self.height, self.unit or default_unit)

    def resolved_placement(self) -> MediaPlacement:
        """Return the effective placement for this figure.

        Returns:
            Effective media placement.
        """

        if self.placement == "auto":
            return "float"
        return self.placement

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this figure into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_figure(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this figure into PDF flowables.

        Returns:
            ReportLab flowables for this figure.
        """

        return renderer.render_figure(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this figure into HTML markup.

        Returns:
            HTML markup for this figure.
        """

        return renderer.render_figure(self, context)


@dataclass(slots=True, init=False)
class SubFigure:
    """A child image inside a numbered subfigure group.

    Args:
        image_source: Path, image bytes, ``ImageData``, or plot-like object.
        caption: Optional subfigure caption.
        width: Optional rendered width.
        height: Optional rendered height.
        identifier: Optional stable identifier.
        unit: Unit for width and height.
        image_format: Image format for plot-like sources.
        image_dpi: Optional image DPI for plot-like sources.
        label: Optional explicit subfigure label.

    Examples:
        ```python
        from oodocs import Document, SubFigure, SubFigureGroup

        left = SubFigure("before.png", caption="Before")
        group = SubFigureGroup(left, SubFigure("after.png", caption="After"), caption="Comparison")
        document = Document("Experiment", group)
        ```
    """

    image_source: object
    caption: Paragraph | None
    width: float | None
    height: float | None
    unit: str | None
    identifier: str | None
    image_format: str
    image_dpi: int | None
    label: str | None

    def __init__(
        self,
        image_source: PathLike | object,
        caption: CellInput | None = None,
        width: float | None = None,
        height: float | None = None,
        identifier: str | None = None,
        *,
        unit: str | None = None,
        image_format: str = "png",
        image_dpi: int | None = 150,
        label: str | None = None,
    ) -> None:
        self.image_source = coerce_image_source(image_source)
        self.caption = coerce_cell(caption) if caption is not None else None
        self.width = width
        self.height = height
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.identifier = identifier
        self.image_format = (
            self.image_source.image_format
            if isinstance(self.image_source, ImageData) and image_format == "png"
            else image_format
        )
        self.image_dpi = image_dpi
        self.label = label

    def width_in_inches(self, default_unit: str) -> float | None:
        """Return subfigure width converted through the subfigure or document unit.

        Args:
            default_unit: Unit to use when the subfigure has no explicit unit.

        Returns:
            Width in inches, or ``None`` for automatic sizing.
        """

        if self.width is None:
            return None
        return length_to_inches(self.width, self.unit or default_unit)

    def height_in_inches(self, default_unit: str) -> float | None:
        """Return subfigure height converted through the subfigure or document unit.

        Args:
            default_unit: Unit to use when the subfigure has no explicit unit.

        Returns:
            Height in inches, or ``None`` for automatic sizing.
        """

        if self.height is None:
            return None
        return length_to_inches(self.height, self.unit or default_unit)

    def reference(
        self,
        *label: InlineInput,
    ) -> BlockReference:
        """Create an explicit inline reference to this subfigure.

        Args:
            *label: Optional inline label override.

        Returns:
            Inline reference targeting this subfigure.
        """

        from oodocs.components.inline import reference

        return reference(self, *label)


@dataclass(slots=True, init=False)
class SubFigureGroup(Block):
    """A numbered figure composed of labeled child figures.

    Args:
        *subfigures: Child subfigures.
        caption: Optional group caption.
        columns: Number of columns in the subfigure grid.
        column_gap: Gap between columns in ``unit``.
        unit: Unit for ``column_gap``.
        identifier: Optional stable identifier.
        placement: Optional placement policy.
        label_format: Format string containing ``"{label}"``.

    Raises:
        ValueError: If no subfigures are provided or layout values are invalid.

    Examples:
        ```python
        from oodocs import Document, SubFigure, SubFigureGroup

        group = SubFigureGroup(
            SubFigure("before.png", caption="Before"),
            SubFigure("after.png", caption="After"),
            caption="Before and after comparison",
            columns=2,
        )
        document = Document("Experiment", group)
        ```
    """

    subfigures: list[SubFigure]
    caption: Paragraph | None
    columns: int
    column_gap: float
    unit: str | None
    identifier: str | None
    placement: MediaPlacement
    label_format: str

    def __init__(
        self,
        *subfigures: SubFigure,
        caption: CellInput | None = None,
        columns: int = 2,
        column_gap: float = 0.18,
        unit: str | None = None,
        identifier: str | None = None,
        placement: str | None = None,
        label_format: str = "({label})",
    ) -> None:
        if not subfigures:
            raise ValueError("SubFigureGroup requires at least one SubFigure")
        if columns < 1:
            raise ValueError("SubFigureGroup.columns must be >= 1")
        if column_gap < 0:
            raise ValueError("SubFigureGroup.column_gap must be >= 0")
        if "{label}" not in label_format:
            raise ValueError("SubFigureGroup.label_format must contain '{label}'")
        self.subfigures = list(subfigures)
        self.caption = coerce_cell(caption) if caption is not None else None
        self.columns = columns
        self.column_gap = column_gap
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.identifier = identifier
        self.placement = normalize_media_placement(placement)
        self.label_format = label_format

    def label_for_index(self, index: int) -> str:
        """Return the raw subfigure label for a zero-based child index.

        Args:
            index: Zero-based child index.

        Returns:
            Explicit label or generated lower-alpha label.
        """

        subfigure = self.subfigures[index]
        return subfigure.label or format_counter_value(index + 1, "lower-alpha")

    def formatted_label_for_index(self, index: int) -> str:
        """Return the display label for a zero-based child index.

        Args:
            index: Zero-based child index.

        Returns:
            Label formatted with ``label_format``.
        """

        return self.label_format.format(label=self.label_for_index(index))

    def resolved_placement(self) -> MediaPlacement:
        """Return the effective placement for this figure group.

        Returns:
            Effective media placement.
        """

        if self.placement == "auto":
            return "float"
        return self.placement

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this subfigure group into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_subfigure_group(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this subfigure group into PDF flowables.

        Returns:
            ReportLab flowables for this subfigure group.
        """

        return renderer.render_subfigure_group(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this subfigure group into HTML markup.

        Returns:
            HTML markup for this subfigure group.
        """

        return renderer.render_subfigure_group(self, context)


__all__ = [
    "Figure",
    "ImageData",
    "MediaPlacement",
    "SubFigure",
    "SubFigureGroup",
    "Table",
    "TableCell",
    "TableCellInput",
    "TableLayout",
    "TablePlacement",
    "TableSplit",
    "build_table_layout",
    "coerce_image_source",
    "coerce_table_cell",
    "image_source_to_buffer",
    "image_source_to_bytes",
    "normalize_media_placement",
    "normalize_table_split",
]
