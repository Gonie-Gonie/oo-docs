# Compose API Objects

Use this workflow when a Python package should contribute selected API sections
to a larger authored document. Collect the package once, select the objects you
need, and insert them as ordinary OODocs blocks.

Prefer object methods such as `ApiPackage.subset(...).to_sections(...)`,
`ApiModule.to_chapter(...)`, and `ApiObject.to_section(...)` for authored
documents; lower-level render helpers are reserved for specialized composition
adapters.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import collect_api
from oodocs.apidoc.docstring import ApiDocstringParser

parser = ApiDocstringParser.auto()
api = collect_api(
    ".",
    collector="griffe",
    public_policy="__all__",
    docstring_style=parser,
)

selected_api = api.subset(kind="class", module_prefix="mypkg")

doc = Document(
    "Developer Notes",
    Chapter(
        "Selected API",
        *selected_api.to_sections(
            level=2,
            presentation="manual",
            max_heading_level=3,
        ),
    ),
)
```

Use `presentation="manual"` for prose-oriented guide sections,
`presentation="compact"` for dense appendices, and `presentation="help"` for
standalone help pages.

## Select Objects

```python
api = collect_api(".", collector="griffe", public_policy="__all__")

classes = api.select_objects(kind="class", module_prefix="mypkg.core")
client = api.find_object("mypkg.core.Client")
```

`ApiObject.to_section(...)` returns a normal OODocs `Section`, so it can be
mixed with handwritten paragraphs, tables, figures, and generated pages.

```python
from oodocs import Chapter, Document, Paragraph

doc = Document(
    "Client Integration Guide",
    Chapter(
        "Client API",
        Paragraph("This section is generated from the current checkout."),
        client.to_section(level=2, presentation="manual") if client else Paragraph("Client API not found."),
    ),
)
```

## Add Summary Tables

When release notes or design docs need an index instead of full sections, pass
selected objects to `to_summary_table(...)`.

```python
from oodocs import Chapter, Document, Paragraph

functions = api.select_objects(kind="function", module_prefix="mypkg.adapters")

doc = Document(
    "Adapter Release Notes",
    Chapter(
        "Public Adapter Functions",
        Paragraph("This table is generated from the current checkout."),
        api.to_summary_table(functions, caption="Selected public functions."),
    ),
)
```

## Build A Reference

Use `ApiPackage.to_help_book(...)` when the whole collected package should
become a standalone API reference. By default, user-facing help books do not
append coverage evidence or uncategorized inventory.

```python
document = api.to_help_book(
    title=f"{api.name} API Reference",
    presentation="help",
    max_heading_level=3,
)
document.save_all("artifacts/api", stem=f"{api.name}-api")
api.save_json("artifacts/api/api-objects.json")
```

Use `ApiHelpBookConfig.from_pyproject(".", profile="evidence")` only when a
development or release-evidence run should include coverage/inventory output.
