# Create Custom Styles

Use `StyleSheet.default()` as the base when you want all built-in styles plus a
few project-specific names.

```python
from oodocs import (
    Box,
    Document,
    DocumentSettings,
    InlineChip,
    Paragraph,
    Table,
    Theme,
)
from oodocs.styles import (
    BlockDefaults,
    BorderStyle,
    BoxStyle,
    InlineChipStyle,
    Padding,
    ParagraphStyle,
    StyleSheet,
    TableStyle,
)

styles = StyleSheet.default()
styles.register_paragraph(
    "body.note",
    ParagraphStyle(text_alignment="left", space_after=6),
)
styles.register_table(
    "schema",
    TableStyle(
        header_background_color="E7EEF7",
        alternate_row_background_color="F8FBFD",
        border=BorderStyle.solid("B8C6D6", width=0.5),
        cell_padding=Padding.all(4),
    ),
)
styles.register_box(
    "scope",
    BoxStyle(background_color="F4F8FB", padding=Padding.all(8)),
)
styles.register_chip(
    "req.required",
    InlineChipStyle(background_color="2563EB", text_color="FFFFFF"),
)

doc = Document(
    "Custom Styles",
    Paragraph("This paragraph uses a named style.", style="body.note"),
    Paragraph("Requirement: ", InlineChip("R", chip_style="req.required")),
    Box("Scope text", title="Scope", style="scope"),
    Table(
        ["Field", "Value"],
        [["name", "example"], ["status", "pass"]],
        caption="Schema-style table.",
        style="schema",
    ),
    settings=DocumentSettings(
        theme=Theme(
            blocks=BlockDefaults(paragraph_text_alignment="left"),
            stylesheet=styles,
        )
    ),
)

doc.validate(raise_on_error=True)
outputs = doc.save_all("artifacts/custom-styles")
print(outputs["pdf"])
```

Use category-specific helpers such as `register_paragraph(...)`,
`register_table(...)`, `register_box(...)`, and `register_chip(...)` in ordinary
authoring code. The category-string `register(category, name, style)` API is
still available for dynamic or advanced tooling, and its category must match the
style object. Keep category names narrow: table styles should not be reused as
box or paragraph styles. When a style should affect every block by default, put
that choice in grouped `Theme` defaults instead of registering a named style.
