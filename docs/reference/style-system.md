# Style System Reference

OODocs separates visual style objects from document-level defaults:

- `TextStyle`, `ParagraphStyle`, `RunInTitleStyle`, `ListStyle`, `BoxStyle`, `TableStyle`, `TableCellStyle`, and `InlineChipStyle` describe reusable visual treatments.
- `TypographyDefaults`, `CaptionDefaults`, `CitationDefaults`, `GeneratedContentDefaults`, `PageNumberDefaults`, `TitleMatterDefaults`, and `BlockDefaults` describe document-level defaults grouped under `Theme`.
- `StyleSheet` stores named styles that blocks can reference by string.

## Naming Rules

| Meaning | Field name |
|---|---|
| Text color | `text_color` |
| Background or fill behind content | `background_color` |
| Border color | `border.color` through `BorderStyle` |
| Vector shape fill | `fill_color` |
| Vector shape stroke | `stroke` through `StrokeStyle` |
| Text alignment | `text_alignment` |
| Block placement alignment | `block_alignment` |
| Vertical content alignment | `vertical_alignment` |
| Counter notation | `CounterStyle(counter_format=...)` |

## Style Categories

| Category | Style object | Typical consumer |
|---|---|---|
| `text` | `TextStyle` | Named inline text styles |
| `paragraph` | `ParagraphStyle` | `Paragraph`, `CodeBlock` |
| `run_in_title` | `RunInTitleStyle` | Paragraph titles |
| `list` | `ListStyle` | `BulletList`, `NumberedList` |
| `box` | `BoxStyle` | `Box`, callout presets |
| `table` | `TableStyle` | `Table` |
| `table_cell` | `TableCellStyle` | `TableCell`, row/column styles |
| `chip` | `InlineChipStyle` | `InlineChip`, `tag`, `badge`, `status`, `keyboard` |

## Named Styles

```python
from oodocs import Document, DocumentSettings, Paragraph, StyleSheet, Table, Theme

styles = StyleSheet.default()

doc = Document(
    "Named Styles",
    Paragraph("Compact body copy.", style="body.compact"),
    Table(["Field", "Value"], [["status", "ready"]], style="compact"),
    settings=DocumentSettings(theme=Theme(stylesheet=styles)),
)

doc.save_all("artifacts/named-styles")
```

Unknown style names are reported by `document.validate()` before rendering. A
style name is resolved against the matching category, so `Table(style="warning")`
fails unless `warning` is registered as a table style.

## Renderer Support

| Feature | DOCX | PDF | HTML |
|---|---|---|---|
| Named paragraph, box, table, and chip styles | Yes | Yes | Yes |
| `css_class` on style objects | Ignored | Ignored | Added to HTML class attributes |
| `Padding` and `BorderStyle` primitives | Yes | Yes | Yes |
| `BoxStyle.title_position="side"` | Yes | Yes | Yes |
| `BoxStyle.shadow` | Degrades to a normal box | Degrades to a normal box | Renders `box-shadow` |
| `CounterStyle` for lists/headings/page numbers | Yes | Yes | Yes |

Use direct block keyword arguments for local changes, concrete style objects for
one-off reusable values, and `StyleSheet` entries when a style name should be
shared across a document or organization.
Built-in box style names include `note`, `info`, `warning`, `danger`, and
`success`, which are also the default `CalloutBox(variant=...)` values.
