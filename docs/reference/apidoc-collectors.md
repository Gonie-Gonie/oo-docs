# apidoc Collectors

Collectors normalize Python source metadata into the same `ApiPackage` schema.

- `collector="griffe"` uses griffe when installed. It captures module data,
  aliases, properties, class attributes, and line metadata without importing the
  target package.
- `collector="inspect"` uses the source-compatible collector and avoids runtime
  imports.
- `collector="auto"` tries griffe first and records a fallback issue if source
  collection is used.

Collectors mark objects as deprecated when docstrings contain `Deprecated:` or
Sphinx `.. deprecated::`, when class/function decorators are named
`deprecated`, `deprecate`, or `deprecated_alias`, or when function bodies call
`warnings.warn(..., DeprecationWarning)`. Warning messages are preserved as
`ApiObject.deprecation_message` when they are literal strings.

```python
from oodocs.apidoc import collect_api

api = collect_api(
    "oodocs",
    collector="griffe",
    public_policy="__all__",
    docstring_style="auto",
)
```

Public API boundaries default to `__all__`. If a module has no `__all__`,
underscore-prefixed names are excluded. Use `public_policy="all"` for internal
audits or `public_policy="explicit"` with `explicit_names=[...]` for curated
sets.

For repeated runs against a general development repository, create an
`ApiPublicPolicy` once and pass it to `collect_api(...)`.

```python
from oodocs.apidoc import ApiPublicPolicy, collect_api

policy = ApiPublicPolicy.explicit("pkg.Widget", "pkg.Widget.render")
api = collect_api(".", collector="griffe", public_policy=policy)
```

`ApiPublicPolicy` can be serialized with `to_dict()` and reconstructed with
`from_dict(...)`, which keeps CI scripts and release jobs aligned with the same
curated boundary.

Use `module_include_patterns` and `module_exclude_patterns` to narrow collection
before parsing module contents. Patterns match fully qualified module names with
standard glob syntax.

```python
api = collect_api(
    ".",
    collector="griffe",
    module_include_patterns=("mypkg.*",),
    module_exclude_patterns=("mypkg.tests*", "mypkg._experimental"),
)
```
