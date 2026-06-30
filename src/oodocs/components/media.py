"""Tables, figures, and related media components.

Attributes:
    MediaPlacement: Supported figure/table placement hints.
    TableSplit: Table splitting policy accepted by table rendering options.
    DEFAULT_LONG_TABLE_ROW_THRESHOLD: Row count where tables are treated as
        long tables by default.
    PdfPagesInput: Accepted input for external PDF page selection.
    CropBox: Image crop offsets for figure rendering.
    CropBoxInput: Accepted input for image crop specifications.
    ColumnSpec: Renderer-neutral table column layout and record-selection
        metadata.
    ColumnSpecInput: Accepted input for table column specifications.
    TableCellStyleInput: Accepted input for table-cell style coercion.
    TableCellInput: Accepted input for table cells.
"""

from __future__ import annotations

import csv
from copy import copy
from dataclasses import asdict, dataclass, is_dataclass
import json
import math
from io import BytesIO
from pathlib import Path
from typing import Callable, Literal, Mapping, Sequence, TYPE_CHECKING

from oodocs.components.base import Block
from oodocs.components.blocks import CellInput, Paragraph, coerce_cell
from oodocs.core import (
    PathLike,
    length_to_inches,
    normalize_color,
    normalize_length_unit,
    normalize_text_alignment,
    normalize_vertical_alignment,
)
from oodocs.styles import (
    BorderStyle,
    CounterStyle,
    Padding,
    TableCellStyle,
    TableCellStyleInput,
    TableStyle,
    TextStyle,
    coerce_table_cell_style,
    table_style_with_overrides,
)

if TYPE_CHECKING:
    from oodocs.components.inline import BlockReference, InlineInput, ReferenceFormat
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext


MediaPlacement = Literal["auto", "here", "float", "top", "bottom", "page"]
TableSplit = bool | Literal["auto"]
DEFAULT_LONG_TABLE_ROW_THRESHOLD = 12
PdfPagesInput = Sequence[int] | range | None


@dataclass(frozen=True, slots=True)
class CropBox:
    """Image crop offsets applied before rendering a figure.

    Args:
        left: Amount to remove from the left edge.
        right: Amount to remove from the right edge.
        top: Amount to remove from the top edge.
        bottom: Amount to remove from the bottom edge.
        unit: Unit for the crop offsets. Defaults to the figure or document
            unit; ``px`` values are treated as image pixels.

    Examples:
        ```python
        from oodocs import Figure
        from oodocs.media import CropBox

        figure = Figure(
            "diagram.png",
            crop=CropBox(left=8, right=8, unit="px"),
            rotation=90,
        )
        ```
    """

    left: float = 0.0
    right: float = 0.0
    top: float = 0.0
    bottom: float = 0.0
    unit: str | None = None

    def __post_init__(self) -> None:
        for name in ("left", "right", "top", "bottom"):
            value = float(getattr(self, name))
            if value < 0:
                raise ValueError("CropBox offsets must be >= 0")
            object.__setattr__(self, name, value)
        if self.unit is not None:
            object.__setattr__(self, "unit", normalize_length_unit(self.unit))

    def offsets_in_pixels(
        self,
        default_unit: str,
        *,
        dpi_x: float,
        dpi_y: float,
    ) -> tuple[int, int, int, int]:
        """Return crop offsets as left, right, top, and bottom pixels.

        Args:
            default_unit: Unit to use when this crop box has no explicit unit.
            dpi_x: Horizontal pixels per inch for physical units.
            dpi_y: Vertical pixels per inch for physical units.

        Returns:
            Four integer pixel offsets in left, right, top, bottom order.
        """

        unit = self.unit or default_unit
        if unit in {"px", "pixel", "pixels"}:
            return (
                round(self.left),
                round(self.right),
                round(self.top),
                round(self.bottom),
            )
        return (
            round(length_to_inches(self.left, unit) * dpi_x),
            round(length_to_inches(self.right, unit) * dpi_x),
            round(length_to_inches(self.top, unit) * dpi_y),
            round(length_to_inches(self.bottom, unit) * dpi_y),
        )


CropBoxInput = CropBox | Mapping[str, object]


def coerce_crop_box(value: CropBoxInput | None) -> CropBox | None:
    """Normalize accepted crop-box inputs."""

    if value is None:
        return None
    if isinstance(value, CropBox):
        return value
    if isinstance(value, Mapping):
        return CropBox(**dict(value))
    raise TypeError(f"Unsupported crop box: {type(value)!r}")


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


def processed_image_source_to_buffer(
    source: object,
    *,
    image_format: str,
    image_dpi: int | None = None,
    crop: CropBox | None = None,
    rotation: float = 0.0,
    default_unit: str = "in",
    usage: str = "image rendering",
) -> BytesIO:
    """Return an image buffer with optional crop and rotation applied.

    Args:
        source: Path, ``ImageData``, or plot-like image source.
        image_format: Output image format for processed bytes.
        image_dpi: Optional image DPI for plot-like sources and physical crop
            unit conversion.
        crop: Optional crop offsets.
        rotation: Counter-clockwise rotation angle in degrees.
        default_unit: Unit to use when ``crop`` has no explicit unit.
        usage: Description used in error messages.

    Returns:
        Image bytes in a ``BytesIO`` buffer.
    """

    normalized_rotation = _normalize_rotation(rotation)
    if isinstance(source, Path):
        image_bytes = source.read_bytes()
    else:
        image_bytes = image_source_to_bytes(
            source,
            image_format=image_format,
            image_dpi=image_dpi,
            usage=usage,
        )
    if crop is None and normalized_rotation == 0:
        return BytesIO(image_bytes)
    return _process_image_bytes(
        image_bytes,
        image_format=image_format,
        image_dpi=image_dpi,
        crop=crop,
        rotation=normalized_rotation,
        default_unit=default_unit,
        usage=usage,
    )


def _normalize_rotation(rotation: float) -> float:
    value = float(rotation)
    if not math.isfinite(value):
        raise ValueError("rotation must be a finite number")
    return value % 360


def _process_image_bytes(
    image_bytes: bytes,
    *,
    image_format: str,
    image_dpi: int | None,
    crop: CropBox | None,
    rotation: float,
    default_unit: str,
    usage: str,
) -> BytesIO:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - Pillow is a dependency.
        raise RuntimeError("Pillow is required for image crop and rotation") from exc

    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except Exception as exc:  # pragma: no cover - depends on Pillow parser.
        raise ValueError(f"Unsupported image source for {usage}: cannot crop or rotate") from exc

    output_dpi = _image_dpi(image, image_dpi)
    if crop is not None:
        left, right, top, bottom = crop.offsets_in_pixels(
            default_unit,
            dpi_x=output_dpi[0],
            dpi_y=output_dpi[1],
        )
        width, height = image.size
        if left + right >= width or top + bottom >= height:
            raise ValueError("CropBox removes the entire image")
        image = image.crop((left, top, width - right, height - bottom))
    if rotation:
        image = image.rotate(rotation, expand=True)

    output_format = _pil_image_format(image_format)
    if output_format == "JPEG" and image.mode in {"RGBA", "LA", "P"}:
        image = image.convert("RGB")
    output = BytesIO()
    image.save(output, format=output_format, dpi=output_dpi)
    output.seek(0)
    return output


def _image_dpi(image: object, fallback: int | None) -> tuple[float, float]:
    dpi = getattr(image, "info", {}).get("dpi")
    if isinstance(dpi, tuple) and len(dpi) >= 2:
        return (float(dpi[0] or fallback or 96), float(dpi[1] or fallback or 96))
    value = float(fallback or 96)
    return (value, value)


def _pil_image_format(image_format: str) -> str:
    normalized = image_format.strip().lower().lstrip(".")
    if normalized in {"jpg", "jpeg"}:
        return "JPEG"
    if normalized in {"tif", "tiff"}:
        return "TIFF"
    if normalized == "webp":
        return "WEBP"
    return "PNG"


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
    style: TableCellStyle | str

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
        overrides = TableCellStyle(
            background_color=background_color,
            text_color=text_color,
            bold=bold,
            italic=italic,
            text_alignment=text_alignment,
            vertical_alignment=vertical_alignment,
        )
        if isinstance(base_style, str):
            if any(
                getattr(overrides, field_name) is not None
                for field_name in (
                    "background_color",
                    "text_color",
                    "bold",
                    "italic",
                    "text_alignment",
                    "vertical_alignment",
                )
            ):
                raise TypeError("Named table cell styles cannot be combined with direct style overrides")
            self.style = base_style
            self.background_color = None
            self.text_alignment = None
            self.vertical_alignment = None
        else:
            self.style = base_style.merged(overrides)
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


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """Renderer-neutral column layout and record-selection metadata.

    Attributes:
        width: Fixed column width in ``unit``.
        flex: Relative share of remaining text width.
        unit: Unit for ``width``.
        text_alignment: Optional default text alignment for this column.
        vertical_alignment: Optional default vertical alignment for this
            column.
        wrap: Whether renderers should allow text wrapping when supported.
        key: Optional record key used by ``Table.from_records``.
        header: Optional header cell used by ``Table.from_records``.
        visible: Whether ``Table.from_records`` includes this column.

    Examples:
        ```python
        from oodocs import Table
        from oodocs.media import ColumnSpec

        table = Table(
            ["Metric", "Description"],
            [["Latency", "End-to-end response time"]],
            columns=[
                ColumnSpec(width=0.9, unit="in"),
                ColumnSpec(flex=1, text_alignment="left"),
            ],
        )
        ```
    """

    width: float | None = None
    flex: float | None = None
    unit: str | None = None
    text_alignment: str | None = None
    vertical_alignment: str | None = None
    wrap: bool = True
    key: object | None = None
    header: TableCellInput | None = None
    visible: bool = True

    def __post_init__(self) -> None:
        if self.width is not None and self.flex is not None:
            raise ValueError("ColumnSpec accepts width or flex, not both")
        if self.width is not None and self.width <= 0:
            raise ValueError("ColumnSpec.width must be greater than zero")
        if self.flex is not None and self.flex <= 0:
            raise ValueError("ColumnSpec.flex must be greater than zero")
        if self.unit is not None:
            object.__setattr__(self, "unit", normalize_length_unit(self.unit))
        if self.text_alignment is not None:
            object.__setattr__(
                self,
                "text_alignment",
                normalize_text_alignment(self.text_alignment),
            )
        if self.vertical_alignment is not None:
            object.__setattr__(
                self,
                "vertical_alignment",
                normalize_vertical_alignment(self.vertical_alignment),
            )
        object.__setattr__(self, "wrap", bool(self.wrap))
        object.__setattr__(self, "visible", bool(self.visible))

    def cell_style(self) -> TableCellStyle:
        """Return the cell style implied by this column specification."""

        return TableCellStyle(
            text_alignment=self.text_alignment,
            vertical_alignment=self.vertical_alignment,
        )


ColumnSpecInput = ColumnSpec | Mapping[str, object]


def coerce_column_spec(value: ColumnSpecInput) -> ColumnSpec:
    """Normalize supported column specification inputs."""

    if isinstance(value, ColumnSpec):
        return value
    if isinstance(value, Mapping):
        return ColumnSpec(**dict(value))
    raise TypeError(f"Unsupported column specification: {type(value)!r}")


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
) -> dict[int, TableCellStyle | str]:
    if styles is None:
        return {}
    normalized: dict[int, TableCellStyle | str] = {}
    for key, value in styles.items():
        index = int(key)
        if index < 0:
            raise ValueError(f"{name} indexes must be >= 0")
        normalized[index] = coerce_table_cell_style(value)
    return normalized


def _normalize_optional_text(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")
    normalized = value.strip()
    return normalized or None


def _normalize_pdf_pages(pages: PdfPagesInput) -> tuple[int, ...] | None:
    if pages is None:
        return None
    if isinstance(pages, (str, bytes)):
        raise TypeError("PdfPages.pages must be a sequence of 1-based page numbers")
    normalized: list[int] = []
    for page in pages:
        page_number = int(page)
        if page_number < 1:
            raise ValueError("PdfPages.pages values must be >= 1")
        normalized.append(page_number)
    return tuple(normalized)


def _coerce_child_label_style(value: CounterStyle | str | None) -> CounterStyle:
    if value is None:
        return CounterStyle(counter_format="lower-alpha")
    if isinstance(value, CounterStyle):
        return value
    if isinstance(value, str):
        return CounterStyle(counter_format=value)
    raise TypeError("child label styles must be CounterStyle instances or counter format strings")


def _validate_child_label_format(value: str, *, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if "{label}" not in value:
        raise ValueError(f"{name} must contain '{{label}}'")
    return value


def _normalize_continued_caption_template(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("continued_caption_template must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError("continued_caption_template must not be empty")
    try:
        normalized.format(caption="Caption", continuation_label="continued")
    except (KeyError, ValueError) as exc:
        raise ValueError(
            "continued_caption_template must format with caption and continuation_label"
        ) from exc
    return normalized


def _resolve_table_cell_style(
    style: TableCellStyle | str | None,
    stylesheet: object | None,
) -> TableCellStyle | None:
    if style is None or isinstance(style, TableCellStyle):
        return style
    if stylesheet is None:
        raise TypeError("Named table cell styles require a stylesheet")
    return stylesheet.resolve("table_cell", style)  # type: ignore[no-any-return]


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
    fail_on_missing: bool,
    missing: object,
) -> object:
    mapping = _record_mapping(record)
    if mapping is not None:
        if column in mapping:
            return mapping[column]
        if fail_on_missing:
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
        if fail_on_missing:
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
        columns: Optional column specifications. Mutually exclusive with
            ``column_widths``.
        unit: Unit for ``column_widths``.
        identifier: Optional stable identifier for references or renderer use.
        style: Base table style.
        header_background_color: Optional header background color override.
        header_text_color: Optional header text color override.
        border: Optional border style override.
        top_rule: Optional top horizontal rule override.
        header_rule: Optional rule below the last header row.
        bottom_rule: Optional bottom horizontal rule override.
        body_background_color: Optional body background color override.
        alternate_row_background_color: Optional alternating row background.
        cell_text_alignment: Optional body cell text alignment.
        cell_vertical_alignment: Optional body cell vertical alignment.
        header_text_alignment: Optional header cell text alignment.
        header_vertical_alignment: Optional header vertical alignment.
        cell_padding: Optional cell padding override.
        repeat_header_rows: Whether fixed-page renderers repeat headers.
        continuation_label: Optional label for repeated-header continuation
            metadata.
        continued_caption_template: Template used to describe continuation
            captions. It receives ``caption`` and ``continuation_label``.
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
        columns: Optional expanded column specifications.
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
    columns: list[ColumnSpec] | None
    unit: str | None
    identifier: str | None
    style: TableStyle | str
    include_index: bool
    split: TableSplit
    placement: MediaPlacement
    long_table_threshold: int | None
    continuation_label: str | None
    continued_caption_template: str
    row_styles: dict[int, TableCellStyle | str]
    column_styles: dict[int, TableCellStyle | str]
    header_row_styles: dict[int, TableCellStyle | str]

    def __init__(
        self,
        headers: Sequence[TableCellInput] | Sequence[Sequence[TableCellInput]] | object,
        rows: Sequence[Sequence[TableCellInput]] | None = None,
        *,
        caption: CellInput | None = None,
        column_widths: Sequence[float] | None = None,
        columns: Sequence[ColumnSpecInput] | None = None,
        unit: str | None = None,
        identifier: str | None = None,
        style: TableStyle | str | None = None,
        header_background_color: str | None = None,
        header_text_color: str | None = None,
        border: BorderStyle | None = None,
        top_rule: BorderStyle | None = None,
        header_rule: BorderStyle | None = None,
        bottom_rule: BorderStyle | None = None,
        body_background_color: str | None = None,
        alternate_row_background_color: str | None = None,
        cell_text_alignment: str | None = None,
        cell_vertical_alignment: str | None = None,
        header_text_alignment: str | None = None,
        header_vertical_alignment: str | None = None,
        cell_padding: Padding | None = None,
        repeat_header_rows: bool | None = None,
        continuation_label: str | None = None,
        continued_caption_template: str = "{caption} ({continuation_label})",
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
        if column_widths is not None and columns is not None:
            raise ValueError("column_widths and columns are mutually exclusive")
        self.column_widths = list(column_widths) if column_widths is not None else None
        self.columns = (
            [coerce_column_spec(column) for column in columns]
            if columns is not None
            else None
        )
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.identifier = identifier
        self.style = table_style_with_overrides(
            style,
            header_background_color=header_background_color,
            header_text_color=header_text_color,
            border=border,
            top_rule=top_rule,
            header_rule=header_rule,
            bottom_rule=bottom_rule,
            body_background_color=body_background_color,
            alternate_row_background_color=alternate_row_background_color,
            cell_text_alignment=cell_text_alignment,
            cell_vertical_alignment=cell_vertical_alignment,
            header_text_alignment=header_text_alignment,
            header_vertical_alignment=header_vertical_alignment,
            cell_padding=cell_padding,
            repeat_header_rows=repeat_header_rows,
        )
        self.continuation_label = _normalize_optional_text(
            continuation_label,
            name="continuation_label",
        )
        self.continued_caption_template = _normalize_continued_caption_template(
            continued_caption_template,
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
        if self.columns is not None and len(self.columns) != layout.column_count:
            raise ValueError("columns must match the expanded number of table columns")

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

    def excerpt(
        self,
        *,
        max_rows: int | None = 10,
        max_columns: int | None = 6,
        caption: CellInput | None = None,
    ) -> Table:
        """Return a compact plain-text excerpt of this table.

        Args:
            max_rows: Maximum body rows to include, or ``None`` for all rows.
            max_columns: Maximum rendered columns to include, or ``None`` for
                all columns.
            caption: Optional caption for the excerpt. Defaults to the source
                table caption.

        Returns:
            New ``Table`` containing a flattened preview suitable for fixed-page
            outputs.

        Examples:
            ```python
            excerpt = full_table.excerpt(max_rows=12, max_columns=5)
            full_table.save_csv("artifacts/full-table.csv")
            ```
        """

        if max_rows is None and max_columns is None:
            raise ValueError("max_rows or max_columns is required")
        if max_rows is not None and max_rows < 1:
            raise ValueError("max_rows must be >= 1")
        if max_columns is not None and max_columns < 1:
            raise ValueError("max_columns must be >= 1")

        matrix = self._plain_text_matrix()
        header_count = len(self.header_rows)
        column_limit = max_columns if max_columns is not None else None
        row_limit = max_rows if max_rows is not None else None
        header_rows = [
            row[:column_limit] if column_limit is not None else list(row)
            for row in matrix[:header_count]
        ]
        body_rows = [
            row[:column_limit] if column_limit is not None else list(row)
            for row in matrix[header_count : header_count + row_limit]
        ]
        if not header_rows:
            header_rows = [[]]
        excerpt_column_count = len(header_rows[0]) if header_rows else 0
        excerpt_columns = (
            self.columns[:excerpt_column_count]
            if self.columns is not None
            else None
        )
        excerpt_column_widths = (
            self.column_widths[:excerpt_column_count]
            if self.column_widths is not None and excerpt_columns is None
            else None
        )
        return Table(
            header_rows,
            body_rows,
            caption=caption if caption is not None else self.caption,
            column_widths=excerpt_column_widths,
            columns=excerpt_columns,
            unit=self.unit,
            style=self.style,
            split=self.split,
            placement=self.placement,
            long_table_threshold=self.long_table_threshold,
        )

    def save_csv(
        self,
        path: PathLike,
        *,
        encoding: str = "utf-8",
        include_headers: bool = True,
    ) -> Path:
        """Write the full flattened table as a CSV sidecar.

        Args:
            path: Destination CSV path.
            encoding: File encoding.
            include_headers: Whether to include header rows.

        Returns:
            Written path.
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding=encoding, newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(
                self._plain_text_matrix(include_headers=include_headers)
            )
        return output_path

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

    def continued_caption_text(self) -> str | None:
        """Return continuation caption text for split-table metadata.

        Returns:
            Formatted continuation caption text, or ``None`` when the table has
            no caption or continuation label.
        """

        if self.caption is None or self.continuation_label is None:
            return None
        return self.continued_caption_template.format(
            caption=self.caption.plain_text(),
            continuation_label=self.continuation_label,
        )

    def _effective_cell_style(
        self,
        placement: TablePlacement,
        *,
        stylesheet: object | None = None,
        table_style: TableStyle | None = None,
    ) -> TableCellStyle:
        row_style = (
            self.header_row_styles.get(placement.row)
            if placement.header
            else (
                self.row_styles.get(placement.body_row_index)
                if placement.body_row_index is not None
                else None
            )
        )
        return self._base_cell_style(placement, table_style=table_style).merged(
            self._column_spec_cell_style(placement.column),
            _resolve_table_cell_style(self.column_styles.get(placement.column), stylesheet),
            _resolve_table_cell_style(row_style, stylesheet),
            _resolve_table_cell_style(placement.cell.style, stylesheet),
        )

    def _column_spec_cell_style(self, column: int) -> TableCellStyle | None:
        if self.columns is None or column >= len(self.columns):
            return None
        return self.columns[column].cell_style()

    def _column_wrap_enabled(self, column: int) -> bool:
        if self.columns is None or column >= len(self.columns):
            return True
        return self.columns[column].wrap

    def _plain_text_matrix(self, *, include_headers: bool = True) -> list[list[str]]:
        layout = self._layout()
        matrix = [
            ["" for _ in range(layout.column_count)]
            for _ in range(layout.row_count)
        ]
        for placement in layout.placements:
            text = placement.cell.content.plain_text()
            for row_offset in range(placement.cell.rowspan):
                row_index = placement.row + row_offset
                if row_index >= layout.row_count:
                    continue
                for column_offset in range(placement.cell.colspan):
                    column_index = placement.column + column_offset
                    if column_index < layout.column_count:
                        matrix[row_index][column_index] = text
        if include_headers:
            return matrix
        return matrix[layout.header_row_count:]

    def _base_cell_style(
        self,
        placement: TablePlacement,
        *,
        table_style: TableStyle | None = None,
    ) -> TableCellStyle:
        style = table_style or self.style
        if isinstance(style, str):
            raise TypeError("Named table styles must be resolved before cell styles are computed")
        if placement.header:
            return TableCellStyle(
                background_color=style.header_background_color,
                text_color=style.header_text_color,
                bold=True,
                text_alignment=style.header_text_alignment,
                vertical_alignment=style.header_vertical_alignment,
            )

        background_color = style.body_background_color
        if (
            style.alternate_row_background_color is not None
            and placement.body_row_index is not None
            and placement.body_row_index % 2 == 1
        ):
            background_color = style.alternate_row_background_color
        return TableCellStyle(
            background_color=background_color,
            text_alignment=style.cell_text_alignment,
            vertical_alignment=style.cell_vertical_alignment,
        )

    def _column_widths_in_inches(
        self,
        default_unit: str,
        *,
        available_width: float | None = None,
    ) -> list[float] | None:
        if self.column_widths is None and self.columns is None:
            return None
        if self.column_widths is not None:
            unit = self.unit or default_unit
            return [length_to_inches(width, unit) for width in self.column_widths]
        assert self.columns is not None
        fixed_widths: list[float | None] = []
        fixed_total = 0.0
        flexible_total = 0.0
        for column in self.columns:
            if column.width is not None:
                width = length_to_inches(column.width, column.unit or self.unit or default_unit)
                fixed_widths.append(width)
                fixed_total += width
            else:
                fixed_widths.append(None)
                flexible_total += column.flex or 1.0
        if all(width is not None for width in fixed_widths):
            return [width for width in fixed_widths if width is not None]
        if available_width is None:
            return None
        remaining = max(available_width - fixed_total, 0.0)
        return [
            width
            if width is not None
            else remaining * ((column.flex or 1.0) / flexible_total)
            for width, column in zip(fixed_widths, self.columns)
        ]

    @classmethod
    def grouped_headers(
        cls,
        *,
        groups: Sequence[tuple[TableCellInput, int] | TableCell],
        columns: Sequence[TableCellInput],
        rows: Sequence[Sequence[TableCellInput]],
        column_specs: Sequence[ColumnSpecInput] | None = None,
        **table_kwargs: object,
    ) -> Table:
        """Create a table with a spanning grouped header row.

        Args:
            groups: Top-level header groups as ``(label, colspan)`` pairs or
                explicit ``TableCell`` objects.
            columns: Leaf column header cells under the groups.
            rows: Body rows.
            column_specs: Optional layout specifications forwarded to
                ``Table(columns=...)``.
            **table_kwargs: Additional arguments forwarded to ``Table``.

        Returns:
            Table with two header rows: grouped headers and leaf columns.

        Raises:
            ValueError: If group spans do not match the rendered column count.

        Examples:
            ```python
            from oodocs import Table

            table = Table.grouped_headers(
                groups=[("Geometry", 2), ("Performance", 2)],
                columns=["Width", "Height", "Latency", "Status"],
                rows=[["8.5 in", "11 in", "14 ms", "ok"]],
            )
            ```
        """

        group_row: list[TableCell] = []
        for group in groups:
            if isinstance(group, TableCell):
                group_row.append(group)
                continue
            label, colspan = group
            group_row.append(
                TableCell(
                    label,
                    colspan=colspan,
                    bold=True,
                    text_alignment="center",
                )
            )
        column_row = [coerce_table_cell(column) for column in columns]
        group_column_count = sum(cell.colspan for cell in group_row)
        leaf_column_count = sum(cell.colspan for cell in column_row)
        if group_column_count != leaf_column_count:
            raise ValueError("group spans must match the number of rendered columns")
        if column_specs is not None:
            table_kwargs = dict(table_kwargs)
            table_kwargs["columns"] = column_specs
        return cls([group_row, column_row], rows, **table_kwargs)

    @classmethod
    def from_dataframe(
        cls,
        dataframe: object,
        *,
        caption: CellInput | None = None,
        column_widths: Sequence[float] | None = None,
        columns: Sequence[ColumnSpecInput] | None = None,
        unit: str | None = None,
        identifier: str | None = None,
        style: TableStyle | str | None = None,
        header_background_color: str | None = None,
        header_text_color: str | None = None,
        border: BorderStyle | None = None,
        top_rule: BorderStyle | None = None,
        header_rule: BorderStyle | None = None,
        bottom_rule: BorderStyle | None = None,
        body_background_color: str | None = None,
        alternate_row_background_color: str | None = None,
        cell_text_alignment: str | None = None,
        cell_vertical_alignment: str | None = None,
        header_text_alignment: str | None = None,
        header_vertical_alignment: str | None = None,
        cell_padding: Padding | None = None,
        repeat_header_rows: bool | None = None,
        continuation_label: str | None = None,
        continued_caption_template: str = "{caption} ({continuation_label})",
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
            columns: Optional column specifications. Mutually exclusive with
                ``column_widths``.
            unit: Unit for ``column_widths``.
            identifier: Optional stable identifier.
            style: Base table style.
            header_background_color: Optional header background color override.
            header_text_color: Optional header text color override.
            border: Optional border style override.
            top_rule: Optional top horizontal rule override.
            header_rule: Optional rule below the last header row.
            bottom_rule: Optional bottom horizontal rule override.
            body_background_color: Optional body background color override.
            alternate_row_background_color: Optional alternating row background.
            cell_text_alignment: Optional body cell text alignment.
            cell_vertical_alignment: Optional body cell vertical alignment.
            header_text_alignment: Optional header cell text alignment.
            header_vertical_alignment: Optional header vertical alignment.
            cell_padding: Optional cell padding override.
            repeat_header_rows: Whether fixed-page renderers repeat headers.
            continuation_label: Optional label for repeated-header
                continuation metadata.
            continued_caption_template: Template used to describe continuation
                captions. It receives ``caption`` and ``continuation_label``.
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
            columns=columns,
            unit=unit,
            identifier=identifier,
            style=style,
            header_background_color=header_background_color,
            header_text_color=header_text_color,
            border=border,
            top_rule=top_rule,
            header_rule=header_rule,
            bottom_rule=bottom_rule,
            body_background_color=body_background_color,
            alternate_row_background_color=alternate_row_background_color,
            cell_text_alignment=cell_text_alignment,
            cell_vertical_alignment=cell_vertical_alignment,
            header_text_alignment=header_text_alignment,
            header_vertical_alignment=header_vertical_alignment,
            cell_padding=cell_padding,
            repeat_header_rows=repeat_header_rows,
            continuation_label=continuation_label,
            continued_caption_template=continued_caption_template,
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
        fail_on_missing: bool = False,
        **table_kwargs: object,
    ) -> Table:
        """Create a table from mappings, dataclasses, or sequence records.

        Args:
            records: Source records.
            columns: Column keys or sequence indexes to extract. ``ColumnSpec``
                entries may also set layout and visibility policy.
            headers: Optional visible header cells. When omitted, visible
                ``ColumnSpec.header`` values are used before falling back to
                column keys.
            formatters: Optional per-column callable or format-spec strings.
            missing: Value used when a record is missing a column and
                ``fail_on_missing`` is false.
            fail_on_missing: Whether missing columns raise errors.
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
            inferred_headers = [str(column) for column in normalized_columns]
        else:
            raw_columns = list(columns)
            if any(isinstance(column, (ColumnSpec, Mapping)) for column in raw_columns):
                normalized_columns = []
                inferred_headers: list[TableCellInput] = []
                table_columns: list[ColumnSpec] = []
                for column in raw_columns:
                    if isinstance(column, ColumnSpec):
                        spec = column
                    elif isinstance(column, Mapping):
                        spec = coerce_column_spec(column)
                    else:
                        spec = ColumnSpec(key=column)
                    if not spec.visible:
                        continue
                    if spec.key is None:
                        raise ValueError("ColumnSpec.key is required in Table.from_records")
                    normalized_columns.append(spec.key)
                    inferred_headers.append(spec.header if spec.header is not None else str(spec.key))
                    table_columns.append(spec)
                table_kwargs = dict(table_kwargs)
                table_kwargs["columns"] = table_columns
            else:
                normalized_columns = raw_columns
                inferred_headers = [str(column) for column in normalized_columns]

        if not normalized_columns:
            raise ValueError("columns must not be empty")

        if headers is None:
            normalized_headers: Sequence[TableCellInput] = inferred_headers
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
                        fail_on_missing=fail_on_missing,
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
                {"package": "oodocs", "version": "1.1.0"},
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

    def _render_to_docx(
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

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this table into PDF flowables.

        Returns:
            ReportLab flowables for this table.
        """

        return renderer.render_table(self, context)

    def _render_to_html(
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
class PdfPages(Block):
    """External PDF pages inserted into PDF output.

    Args:
        source: Existing PDF file to insert.
        pages: Optional 1-based page numbers to include. Defaults to all
            pages.
        title: Optional human-readable label used by DOCX/HTML fallback
            renderers.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.pdf import PdfPages

        appendix = PdfPages("appendix/material-safety-data.pdf", pages=[1, 3])
        document = Document("Report", appendix)
        ```
    """

    source: Path
    pages: tuple[int, ...] | None
    title: str | None

    def __init__(
        self,
        source: PathLike,
        *,
        pages: PdfPagesInput = None,
        title: str | None = None,
    ) -> None:
        self.source = Path(source)
        self.pages = _normalize_pdf_pages(pages)
        self.title = _normalize_optional_text(title, name="title")

    def page_label(self) -> str:
        """Return a compact label describing the selected pages."""

        if self.pages is None:
            return "all pages"
        return "page " + ", ".join(str(page) for page in self.pages)

    def selected_page_indexes(self) -> list[int]:
        """Return selected external PDF page indexes in zero-based form.

        Raises:
            FileNotFoundError: If ``source`` does not exist.
            ValueError: If a requested page is outside the external PDF.
        """

        from pypdf import PdfReader

        reader = PdfReader(str(self.source))
        page_count = len(reader.pages)
        if self.pages is None:
            return list(range(page_count))
        indexes: list[int] = []
        for page in self.pages:
            if page > page_count:
                raise ValueError(
                    f"PdfPages page {page} is outside {self.source} ({page_count} pages)"
                )
            indexes.append(page - 1)
        return indexes

    def _render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render a DOCX fallback for this external PDF."""

        renderer.render_pdf_pages(container, self, context)

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render PDF page placeholders that are replaced after PDF build."""

        return renderer.render_pdf_pages(self, context)

    def _render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render an HTML fallback for this external PDF."""

        return renderer.render_pdf_pages(self, context)


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
        crop: Optional crop offsets applied before rendering.
        rotation: Optional counter-clockwise rotation angle in degrees.
        alt_text: Optional alternative text for accessible outputs.

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
    crop: CropBox | None
    rotation: float
    alt_text: str | None

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
        crop: CropBoxInput | None = None,
        rotation: float = 0.0,
        alt_text: str | None = None,
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
        self.crop = coerce_crop_box(crop)
        self.rotation = _normalize_rotation(rotation)
        self.alt_text = _normalize_optional_text(alt_text, name="alt_text")

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

    def _render_to_docx(
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

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this figure into PDF flowables.

        Returns:
            ReportLab flowables for this figure.
        """

        return renderer.render_figure(self, context)

    def _render_to_html(
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
        crop: Optional crop offsets applied before rendering.
        rotation: Optional counter-clockwise rotation angle in degrees.
        alt_text: Optional alternative text for accessible outputs.

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
    crop: CropBox | None
    rotation: float
    alt_text: str | None

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
        crop: CropBoxInput | None = None,
        rotation: float = 0.0,
        alt_text: str | None = None,
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
        self.crop = coerce_crop_box(crop)
        self.rotation = _normalize_rotation(rotation)
        self.alt_text = _normalize_optional_text(alt_text, name="alt_text")

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

    def ref(
        self,
        *label: InlineInput,
        style: TextStyle | None = None,
        reference_format: ReferenceFormat | None = None,
    ) -> BlockReference:
        """Create an explicit inline reference to this subfigure.

        Args:
            *label: Optional inline label override.

        Returns:
            Inline reference targeting this subfigure.
        """

        from oodocs.components.inline import ref

        return ref(self, *label, style=style, reference_format=reference_format)


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
        label_style: Counter style or counter-format name used for generated
            child labels.
        reference_label_format: Optional format string for references to child
            figures. Defaults to ``label_format``.

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
    label_style: CounterStyle
    reference_label_format: str

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
        label_style: CounterStyle | str | None = None,
        reference_label_format: str | None = None,
    ) -> None:
        if not subfigures:
            raise ValueError("SubFigureGroup requires at least one SubFigure")
        if columns < 1:
            raise ValueError("SubFigureGroup.columns must be >= 1")
        if column_gap < 0:
            raise ValueError("SubFigureGroup.column_gap must be >= 0")
        self.subfigures = list(subfigures)
        self.caption = coerce_cell(caption) if caption is not None else None
        self.columns = columns
        self.column_gap = column_gap
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.identifier = identifier
        self.placement = normalize_media_placement(placement)
        self.label_format = _validate_child_label_format(
            label_format,
            name="SubFigureGroup.label_format",
        )
        self.label_style = _coerce_child_label_style(label_style)
        self.reference_label_format = _validate_child_label_format(
            reference_label_format if reference_label_format is not None else label_format,
            name="SubFigureGroup.reference_label_format",
        )

    def label_for_index(self, index: int) -> str:
        """Return the raw subfigure label for a zero-based child index.

        Args:
            index: Zero-based child index.

        Returns:
            Explicit label or generated counter-style label.
        """

        subfigure = self.subfigures[index]
        return subfigure.label or self.label_style.format_value(self.label_style.start + index)

    def formatted_label_for_index(self, index: int) -> str:
        """Return the display label for a zero-based child index.

        Args:
            index: Zero-based child index.

        Returns:
            Label formatted with ``label_format``.
        """

        return self.label_format.format(label=self.label_for_index(index))

    def formatted_reference_label_for_index(self, index: int) -> str:
        """Return the child label suffix used in references.

        Args:
            index: Zero-based child index.

        Returns:
            Label formatted with ``reference_label_format``.
        """

        return self.reference_label_format.format(label=self.label_for_index(index))

    def resolved_placement(self) -> MediaPlacement:
        """Return the effective placement for this figure group.

        Returns:
            Effective media placement.
        """

        if self.placement == "auto":
            return "float"
        return self.placement

    def _render_to_docx(
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

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this subfigure group into PDF flowables.

        Returns:
            ReportLab flowables for this subfigure group.
        """

        return renderer.render_subfigure_group(self, context)

    def _render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this subfigure group into HTML markup.

        Returns:
            HTML markup for this subfigure group.
        """

        return renderer.render_subfigure_group(self, context)


@dataclass(slots=True, init=False)
class SubTable:
    """A child table inside a numbered subtable group.

    Args:
        table: Table content rendered as a child table.
        caption: Optional subtable caption. Defaults to ``table.caption`` when
            omitted.
        identifier: Optional stable identifier.
        label: Optional explicit subtable label.

    Examples:
        ```python
        from oodocs import Table
        from oodocs.media import SubTable, SubTableGroup

        baseline = SubTable(Table(["Metric"], [["AUC"]]), caption="Baseline")
        tuned = SubTable(Table(["Metric"], [["AUC"]]), caption="Tuned")
        group = SubTableGroup(baseline, tuned, caption="Sensitivity tables")
        ```
    """

    table: Table
    caption: Paragraph | None
    identifier: str | None
    label: str | None

    def __init__(
        self,
        table: Table,
        caption: CellInput | None = None,
        identifier: str | None = None,
        *,
        label: str | None = None,
    ) -> None:
        if not isinstance(table, Table):
            raise TypeError("SubTable.table must be a Table instance")
        self.table = table
        self.caption = coerce_cell(caption) if caption is not None else table.caption
        self.identifier = identifier if identifier is not None else table.identifier
        self.label = label

    def table_without_caption(self) -> Table:
        """Return a shallow table copy suitable for child rendering.

        Returns:
            Table copy with captions suppressed and placement constrained to
            the current position.
        """

        table = copy(self.table)
        table.caption = None
        table.placement = "here"
        return table

    def width_in_inches(
        self,
        default_unit: str,
        *,
        available_width: float | None = None,
    ) -> float | None:
        """Return the rendered child-table width when it is explicitly known."""

        column_widths = self.table._column_widths_in_inches(
            default_unit,
            available_width=available_width,
        )
        if column_widths is None:
            return None
        return sum(column_widths)

    def ref(
        self,
        *label: InlineInput,
        style: TextStyle | None = None,
        reference_format: ReferenceFormat | None = None,
    ) -> BlockReference:
        """Create an explicit inline reference to this subtable."""

        from oodocs.components.inline import ref

        return ref(self, *label, style=style, reference_format=reference_format)


@dataclass(slots=True, init=False)
class SubTableGroup(Block):
    """A numbered table composed of labeled child tables.

    Args:
        *subtables: Child subtables.
        caption: Optional group caption.
        columns: Number of columns in the subtable grid.
        column_gap: Gap between columns in ``unit``.
        unit: Unit for ``column_gap``.
        identifier: Optional stable identifier.
        placement: Optional placement policy.
        label_format: Format string containing ``"{label}"``.
        label_style: Counter style or counter-format name used for generated
            child labels.
        reference_label_format: Optional format string for references to child
            tables. Defaults to ``label_format``.

    Examples:
        ```python
        from oodocs import Table
        from oodocs.media import SubTable, SubTableGroup

        group = SubTableGroup(
            SubTable(Table(["Case", "Value"], [["A", "0.91"]]), caption="Baseline"),
            SubTable(Table(["Case", "Value"], [["B", "0.94"]]), caption="Tuned"),
            caption="Sensitivity tables.",
            columns=2,
        )
        ```
    """

    subtables: list[SubTable]
    caption: Paragraph | None
    columns: int
    column_gap: float
    unit: str | None
    identifier: str | None
    placement: MediaPlacement
    label_format: str
    label_style: CounterStyle
    reference_label_format: str

    def __init__(
        self,
        *subtables: SubTable,
        caption: CellInput | None = None,
        columns: int = 2,
        column_gap: float = 0.18,
        unit: str | None = None,
        identifier: str | None = None,
        placement: str | None = None,
        label_format: str = "({label})",
        label_style: CounterStyle | str | None = None,
        reference_label_format: str | None = None,
    ) -> None:
        if not subtables:
            raise ValueError("SubTableGroup requires at least one SubTable")
        if columns < 1:
            raise ValueError("SubTableGroup.columns must be >= 1")
        if column_gap < 0:
            raise ValueError("SubTableGroup.column_gap must be >= 0")
        self.subtables = list(subtables)
        self.caption = coerce_cell(caption) if caption is not None else None
        self.columns = columns
        self.column_gap = column_gap
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.identifier = identifier
        self.placement = normalize_media_placement(placement)
        self.label_format = _validate_child_label_format(
            label_format,
            name="SubTableGroup.label_format",
        )
        self.label_style = _coerce_child_label_style(label_style)
        self.reference_label_format = _validate_child_label_format(
            reference_label_format if reference_label_format is not None else label_format,
            name="SubTableGroup.reference_label_format",
        )

    def label_for_index(self, index: int) -> str:
        """Return the raw subtable label for a zero-based child index."""

        subtable = self.subtables[index]
        return subtable.label or self.label_style.format_value(self.label_style.start + index)

    def formatted_label_for_index(self, index: int) -> str:
        """Return the display label for a zero-based child index."""

        return self.label_format.format(label=self.label_for_index(index))

    def formatted_reference_label_for_index(self, index: int) -> str:
        """Return the child label suffix used in references."""

        return self.reference_label_format.format(label=self.label_for_index(index))

    def resolved_placement(self) -> MediaPlacement:
        """Return the effective placement for this table group."""

        if self.placement == "auto":
            return "float"
        return self.placement

    def ref(
        self,
        *label: InlineInput,
        style: TextStyle | None = None,
        reference_format: ReferenceFormat | None = None,
    ) -> BlockReference:
        """Create an explicit inline reference to this subtable group."""

        from oodocs.components.inline import ref

        return ref(self, *label, style=style, reference_format=reference_format)

    def _render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this subtable group into a DOCX container."""

        renderer.render_subtable_group(container, self, context)

    def _render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this subtable group into PDF flowables."""

        return renderer.render_subtable_group(self, context)

    def _render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this subtable group into HTML markup."""

        return renderer.render_subtable_group(self, context)


__all__ = [
    "ColumnSpec",
    "ColumnSpecInput",
    "CropBox",
    "CropBoxInput",
    "Figure",
    "ImageData",
    "MediaPlacement",
    "PdfPages",
    "PdfPagesInput",
    "SubFigure",
    "SubFigureGroup",
    "SubTable",
    "SubTableGroup",
    "Table",
    "TableCell",
    "TableCellInput",
    "TableLayout",
    "TablePlacement",
    "TableSplit",
    "coerce_column_spec",
    "coerce_crop_box",
    "coerce_table_cell",
]
