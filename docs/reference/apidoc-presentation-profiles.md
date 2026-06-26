# apidoc Profiles

Profiles control how API objects become renderer-neutral OODocs blocks. They do
not change collection or parsing.

- `reference`: full signatures, descriptions, parameter tables, returns,
  raises, notes, warnings, examples, see-also entries, renderer notes, source
  locations, and member summaries.
- `compact`: summary-first layout with shorter tables, warning blocks, and
  fewer examples.
- `manual`: guide-friendly sections that fit into authored documents, including
  parsed notes and warnings. See-also entries render as a compact box so
  related API notes read like prose inside a surrounding guide.
- `evidence`: coverage and issue oriented output.
- `review`: editable DOCX-friendly structure with generated review-note
  comments for each rendered API object.
- `website`: anchor/source-link oriented structure for HTML output. Summary
  table names link to the stable section anchors generated for each API object.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
doc = Document(
    "API Review",
    Chapter("Classes", *[
        obj.to_section(level=2, presentation="review")
        for obj in api.select_objects(kind="class")[:3]
    ]),
)
```

The same `Document` can still be saved as DOCX, PDF, or HTML through the normal
OODocs renderers.

`compact`, `evidence`, and `review` profiles wrap long signature code blocks at
top-level parameter commas by default. `compact` and `evidence` also cap the
number of rendered signature lines so very large constructor signatures remain
usable in fixed-page outputs. This keeps the generated OODocs block tree
suitable for narrow DOCX/PDF pages before any renderer-specific output is
created. The `parameter_columns` option controls table width in the same
renderer-neutral way.

Supported parameter columns are `name`, `type`, `default`, `required`,
`description`, and `source`. Profiles normalize column names when they are
created and raise `ValueError` for unsupported names, so invalid table policies
fail before rendering starts.

```python
from dataclasses import replace
from oodocs.apidoc import ApiPresentationProfile

pdf_friendly = replace(
    ApiPresentationProfile.reference(),
    parameter_columns=("name", "type", "description"),
    max_description_chars=160,
    max_signature_width=80,
)
```

Profiles also control parsed `Notes:` and `Warnings:` sections. `compact` and
`evidence` suppress general notes to keep reference bundles short, but warnings
remain visible because they often affect API usage. The same policy is applied
to both `ApiObject` sections and `ApiModule` chapters.

Custom profiles can enable the same review workflow:

```python
from dataclasses import replace
from oodocs.apidoc import ApiPresentationProfile

profile = replace(
    ApiPresentationProfile.compact(),
    include_review_notes=True,
    review_note_text="Check whether this object needs a richer example.",
    max_signature_width=72,
    max_signature_lines=18,
    signature_wrap_indent="  ",
)
```
