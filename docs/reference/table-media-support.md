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

## DataFrame Contract

`Table.from_dataframe(...)` is the canonical DataFrame constructor.
`Table(dataframe)` remains a convenient shortcut when no DataFrame-specific
formatting is needed, but it is auxiliary syntax rather than a second API
contract.

Pandas MultiIndex columns become grouped header rows with `colspan`; a
MultiIndex index becomes leading row-header cells with `rowspan` when
`include_index=True`. Numeric formatters can target the complete tuple key, a
leaf key, or a parent group key. A complete tuple wins first, then a leaf key,
then the nearest matching group key.

```python
from oodocs import Table

table = Table.from_dataframe(
    frame,
    include_index=True,
    formatters={
        "Metrics": ".1f",          # every numeric leaf in this group
        "Peak": ".2f",             # overrides the group for this leaf
        ("Limits", "Maximum"): ".0f",  # exact MultiIndex key
    },
)
```

## Long Tables and Rich Cells

Use `split=True` to allow page breaks and repeat every header row in DOCX and
PDF. `continuation_label` and `continued_caption_template` accept ordinary
Unicode locale text.

```python
from oodocs import Paragraph, Table, TableCell, line_break

table = Table(
    ["Item", "Description", "State"],
    [
        [TableCell("Phase A", colspan=3)],
        [
            "Check",
            Paragraph(
                "First line",
                line_break(),
                "Second line — ",
                details.link("Open details"),
            ),
            "Ready",
        ],
    ],
    caption="점검 표.",
    split=True,
    continuation_label="계속",
    continued_caption_template="{caption} — {continuation_label}",
)
```

`TableCell(..., colspan=n)` is also the ordinary body-group-row mechanism.
Cells accept `line_break()` and an object link just like normal paragraphs.
HTML places every table in a horizontal overflow container so a wide matrix
does not force the whole page wider.

## Wide Fixed-Page Output

A table does not change document page layout automatically. Place an
intentionally wide table in
`Section(page_layout=PageLayout.landscape(...))` explicitly:

```python
from oodocs import PageLayout, PageSize, Section

wide_section = Section(
    "Full matrix",
    full_table,
    page_layout=PageLayout.landscape(PageSize.a4()),
)
```

For PDF output where the full matrix is still inappropriate, publish a compact
preview and a lossless sidecar together:

```python
preview = full_table.excerpt(max_rows=12, max_columns=6)
csv_path = full_table.save_csv("artifacts/full-matrix.csv")
```

The preview remains in the document and the application can link or otherwise
distribute the returned CSV path.

## Validation Contract

The overflow policy remains intentionally small: `"warn"` reports a wide table
and `"allow"` records that overflow is deliberate. Explicit widths report the
estimated table width and available text width; implicit many-column tables
report the actual expanded column count. Grouped-header spans and explicit
column specifications are checked against the expanded table width at
construction time.

Renderer-specific semantic fallbacks are reported as structured compatibility
warnings. Ordinary tables, merged cells, repeated headers, and rich cell
content are supported by all three renderers and therefore do not need a
fallback warning merely because the output format differs.

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
