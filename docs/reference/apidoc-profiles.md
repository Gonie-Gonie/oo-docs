# apidoc Profiles

Profiles control how API objects become renderer-neutral OODocs blocks. They do
not change collection or parsing.

- `reference`: full signatures, descriptions, parameter tables, returns,
  raises, examples, see-also entries, renderer notes, source locations, and
  member summaries.
- `compact`: summary-first layout with shorter tables and fewer examples.
- `manual`: guide-friendly sections that fit into authored documents.
- `evidence`: coverage and issue oriented output.
- `review`: editable DOCX-friendly structure.
- `website`: anchor/source-link oriented structure for HTML output.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
doc = Document(
    "API Review",
    Chapter("Classes", *[
        obj.to_section(level=2, profile="review")
        for obj in api.select(kind="class")[:3]
    ]),
)
```

The same `Document` can still be saved as DOCX, PDF, or HTML through the normal
OODocs renderers.

