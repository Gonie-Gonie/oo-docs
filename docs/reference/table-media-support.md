# Table And Media Support Reference

OODocs keeps common table and media authoring on the top-level document API,
while advanced column layout, PDF-only page insertion, and table overflow
policy live in explicit domain namespaces.

## Table Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Small authored table | `Table(headers, rows)` | Best for short hand-written tables. |
| Record data | `Table.from_records(records, columns=...)` | `ColumnSpec(key=..., header=..., visible=False)` can select, rename, or hide fields. |
| DataFrame-like data | `Table.from_dataframe(data, columns=...)` | Keeps tabular data close to the Python processing step. |
| Delimited file | `Table.from_csv(...)` or `Table.from_tsv(...)` | Accepts the same column layout options as other data constructors. |
| Repeated styling | `style="compact"` or `style=TableStyle(...)` | Use named table styles before repeating many direct style kwargs. |
| Advanced column layout | `ColumnSpec(width=...)` or `ColumnSpec(flex=...)` from `oodocs.media` | Canonical path for fixed widths, flex columns, column alignment, and column cell styles. |
| Cell-level exception | `TableCell(...)` | Use for one-off `rowspan`, `colspan`, alignment, or cell style. |
| Wide table policy | `TableOverflowPolicy(action="allow")` from `oodocs.media` | Suppresses the `wide-table` warning only when overflow is intentional. |

`column_widths=...` remains available for simple fixed-width tables, but
`columns=[ColumnSpec(...)]` is the canonical advanced path. Do not pass both
`columns` and `column_widths` for the same table.

When a table is too wide for the page text area, prefer `ColumnSpec(flex=...)`,
`Table.excerpt(...)`, or `Table.save_csv(...)` before allowing overflow. This
keeps fixed-page output readable while preserving full data in a sidecar.

## PDF Pages

Use `PdfPages(...)` from `oodocs.pdf` when an existing PDF page must be inserted
into PDF output. It is intentionally not a top-level `oodocs` export because the
feature is renderer-specific.

PDF output inserts the selected pages. DOCX and HTML render a link-style
placeholder, and validation emits `pdf-pages-non-pdf-output` for those formats.

## Image Naming

Image-oriented public APIs use `image_format` and `image_dpi` rather than
generic `format` or `dpi` names. This applies to `ImageData(...)`,
`Figure(...)`, `Figure.from_bytes(...)`, `Figure.from_buffer(...)`,
`SubFigure(...)`, and `ImageBox(...)`.

`ImageData.savefig(...)` is a compatibility adapter for plot-like renderer
paths. Prefer passing `ImageData(...)`, file paths, bytes, buffers, or
`savefig()`-compatible figure objects to `Figure(...)` instead of calling the
adapter directly.
