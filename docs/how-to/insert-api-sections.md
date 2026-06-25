# Insert API Sections

Collect an API tree, select the objects that belong in your authored document,
and convert each object to a `Section`.

```python
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
component_classes = api.select(kind="class", module_prefix="oodocs.components")

doc = Document(
    "Developer Notes",
    Chapter(
        "Selected API",
        Paragraph("These sections are generated from docstrings and signatures."),
        *[obj.to_section(level=2, profile="manual") for obj in component_classes[:5]],
    ),
)
```

Use `profile="compact"` for dense reference appendices, `profile="manual"` for
guide-like prose, and `profile="reference"` when you want signatures,
parameters, returns, examples, see-also entries, and source locations.

