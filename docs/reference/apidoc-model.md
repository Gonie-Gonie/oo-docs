# apidoc Model Reference

Core objects:

- `ApiPackage`: package-level container with modules, issues, selection helpers,
  rendering helpers, and JSON sidecar IO.
- `ApiModule`: module-level container with public objects and chapter/table
  helpers.
- `ApiObject`: normalized API item for classes, functions, methods, properties,
  attributes, and data.
- `ApiParameter`: signature or docstring parameter/attribute metadata.
- `ApiReturn`, `ApiRaises`, `ApiExample`, `ApiSeeAlso`, `ApiRendererNote`:
  normalized docstring subsections.
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
