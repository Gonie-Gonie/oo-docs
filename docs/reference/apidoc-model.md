# apidoc Model Reference

Core objects:

- `ApiPackage`: package-level container with modules, issues, selection helpers,
  rendering helpers, and JSON sidecar IO.
- `ApiModule`: module-level container with public objects, parsed module
  notes/warnings/renderer notes, and chapter/table helpers.
- `ApiObject`: normalized API item for classes, functions, methods, properties,
  attributes, and data.
- `ApiParameter`: signature or docstring parameter/attribute metadata.
- `ApiReturn`, `ApiRaises`, `ApiExample`, `ApiSeeAlso`, `ApiRendererNote`,
  plus `ApiObject.notes` and `ApiObject.warnings`: normalized docstring
  subsections.
- `ApiDocIssue`: stable diagnostics from parsing, collection, coverage, and
  examples.
- `ApiSnapshot` and `ApiDiffResult`: release comparison sidecars for added,
  removed, signature-changed, default-changed, annotation-changed,
  documentation-changed, and deprecated API objects.

```python
from oodocs.apidoc import ApiPackage, collect_api

api: ApiPackage = collect_api("oodocs", public_policy="__all__")
obj = api.find("oodocs.Document")

if obj is not None:
    print(obj.display_signature())
    print(obj.to_dict()["qualname"])
```

Every model object that is written as a sidecar supports deterministic
serialization through `to_dict()`/`from_dict()` or package/snapshot JSON helpers.
Diff sidecars preserve parameter annotation and return annotation changes as
first-class lists so compatibility reports do not need to infer them from the
rendered signature string.

Parsed notes and warnings remain on each `ApiObject`, survive JSON sidecars, and
can be inserted directly with `obj.to_notes_blocks()` or
`obj.to_warnings_blocks()` when a document wants those sections outside the
full `obj.to_section(...)` rendering.

Leaf metadata objects are composable too. `ApiReturn`, `ApiRaises`,
`ApiExample`, `ApiSeeAlso`, and `ApiRendererNote` expose row helpers for custom
tables, and paragraph/block helpers for inserting a single parsed item into a
hand-authored chapter without rendering the whole `ApiObject`.

```python
from oodocs import Chapter, Document, Table
from oodocs.apidoc import collect_api

api = collect_api(".")
obj = api.functions()[0]
rows = [item.to_row() for item in obj.raises]
doc = Document(
    "API Review",
    Chapter(
        "Raises",
        Table(["Exception", "Description"], rows),
        *(example.to_block() for example in obj.examples),
    ),
)
```

Module docstring notes, warnings, and renderer notes are preserved on
`ApiModule` as well. `module.to_blocks(...)` and `module.to_chapter(...)` render
them before the module API summary table so overview-level guidance is not lost
when a repository uses module docstrings as reference introductions or embeds a
module reference inside a larger hand-authored document.

For package-wide querying, `ApiPackage` exposes `classes()`, `functions()`,
`methods()`, `properties()`, `attributes()`, `public_objects()`, and the more
general `select(...)` helper. `ApiModule` exposes matching module-local
helpers for classes, functions, properties, and attributes.

Use `max_level` when a large repository should render a shallower reference.
For example, `api.to_document(profile="reference", max_level=2)` renders module
chapters and top-level object sections while keeping deeper class members in
summary tables instead of expanding them as their own headings.

Use `api.iter_issues()` or `api.to_issue_table()` when parser diagnostics stored
on individual API objects should appear beside package-level collection issues.
