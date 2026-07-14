# Description lists

Use `DescriptionList` for semantic term-and-definition content such as command
options, configuration keys, and local equation-variable explanations. A term
accepts ordinary inline content, while its definition accepts full OODocs
blocks. Strings are converted to `Paragraph` objects automatically.

```python
from oodocs import BulletList, CodeBlock, DescriptionList, Paragraph

options = DescriptionList(style="description.compact")
options.add(
    "--output FORMAT",
    Paragraph("Select an output format."),
    BulletList("html", "pdf", "docx"),
    CodeBlock("tool --output html", language="text"),
)
```

The built-in named styles are `description.default`, `description.compact`,
and `description.symbols`. `DescriptionListStyle(layout=...)` accepts
`"hanging"`, `"stacked"`, or `"run-in"` and controls term width, term text,
definition paragraph defaults, item spacing, term gap, and length unit.

HTML uses native `dl`, `dt`, and `dd` elements. DOCX uses a borderless table so
long terms and rich definitions remain stable, while PDF uses a calculated
definition indent and page-splittable flowables.

`Nomenclature` remains the specialized preset for a document-wide symbol table
with an explicit unit column or double-column layout. Use `DescriptionList`
for local definitions and avoid maintaining a second general-purpose
term/definition implementation.
