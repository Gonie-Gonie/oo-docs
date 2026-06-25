# apidoc Collectors

Collectors normalize Python source metadata into the same `ApiPackage` schema.
Repository paths may point at a package directory, a `src/` layout package, or
a `src/` layout namespace package that omits `__init__.py`.

- `collector="griffe"` uses griffe when installed. It captures module data,
  aliases, properties, class attributes, public `__init__` instance
  attributes, and line metadata without importing the target package.
- `collector="inspect"` uses the source-compatible collector and avoids runtime
  imports while normalizing the same object kinds when they can be inferred from
  source.
- `collector="auto"` tries griffe first and records a fallback issue if source
  collection is used.

By default, griffe failures fall back to the inspect-compatible source
collector. Set `fallback_collector="none"` when CI should fail loudly instead
of rendering a best-effort fallback reference:

```python
api = collect_api(".", collector="griffe", fallback_collector="none")
```

```toml
[tool.oodocs.apidoc]
collector = "griffe"
fallback-collector = "none"
```

Collectors mark objects as deprecated when docstrings contain `Deprecated:` or
Sphinx `.. deprecated::`, when class/function decorators are named
`deprecated`, `deprecate`, or `deprecated_alias`, or when function bodies call
`warnings.warn(..., DeprecationWarning)`. Warning messages are preserved as
`ApiObject.deprecation_message` when they are literal strings.

Class signatures use `__init__` parameters by default. When a class docstring
does not document those parameters directly, both source and griffe collection
can use the `__init__` docstring's parameter section as the class constructor
parameter documentation. Disable that behavior with
`class-signature-from-init = false` in config or
`--no-class-signature-from-init` on the CLI.

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
curated boundary. Use `ApiCollectConfig.from_pyproject(...)` when a repository
stores its policy in `pyproject.toml`, or `ApiCollectConfig.write_json(...)`
when the full collection policy should be shared as a standalone sidecar.
Use `ApiBuildConfig.from_pyproject(...)` when the same repository config should
also supply rendered-document defaults such as profile, formats, filters, and
sidecar generation.

```toml
[tool.oodocs.apidoc]
collector = "griffe"
public-policy = "__all__"
docstring-style = "auto"
class-signature-from-init = true
module-exclude-patterns = ["mypkg.tests*"]
object-exclude-patterns = ["render_to_docx", "render_to_pdf", "render_to_html"]
profile = "website"
formats = ["html"]
sidecars = true
```

```python
from oodocs.apidoc import ApiBuildConfig, collect_api

build = ApiBuildConfig.from_pyproject(".")
api = collect_api(".", config=build.collection)
```

When a repository defines a custom parser, store the import hook next to the
style name. OODocs imports those modules before validating the configured
style, so the hook can register parser names that are not built in:

```toml
[tool.oodocs.apidoc]
docstring-style = "brief"
docstring-parser-modules = ["mypkg.docs_parsers"]
```

To create that config from Python instead of the CLI:

```python
from oodocs.apidoc import ApiBuildConfig

ApiBuildConfig(profile="website", output_formats=("html",), sidecars=True).write_pyproject(".")
```

```powershell
python -m oodocs apidoc build . --config pyproject.toml --out artifacts/api
```

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

Use `object_include_patterns` and `object_exclude_patterns` when the repository
has public names that should not appear in user-facing API docs. These filters
run after collection and match either fully qualified object names or local
object names.

```python
api = collect_api(
    ".",
    collector="griffe",
    object_exclude_patterns=("render_to_pdf", "render_to_html"),
)
```

Use `include_imported=True` when a package intentionally exposes imported
objects as part of its public boundary. Internal re-exports are resolved to the
collected target object when possible. External imports that source collection
cannot inspect safely are still represented as public `data` objects with
`metadata["imported_from"]`.

```python
api = collect_api(
    ".",
    collector="inspect",
    public_policy="__all__",
    include_imported=True,
)
```

Use `include_inherited=True` when class references should include inherited
methods, properties, or attributes. Source collection can include same-module
base class members; griffe-backed collection walks the class MRO. Both record
the original member qualname in `metadata["inherited_from"]` so rendered
references can distinguish local API from inherited API.

```python
api = collect_api(
    ".",
    collector="griffe",
    public_policy="underscore",
    include_inherited=True,
)
```

Use `include_attributes`, `include_properties`, and `include_methods` to control
which class and module member kinds appear in the collected tree before any
rendering profile runs. This is useful when a public package reference should
list classes and factory functions but omit implementation-oriented constants,
properties, or methods from the generated document.

```python
api = collect_api(
    ".",
    collector="griffe",
    public_policy="__all__",
    include_attributes=False,
    include_properties=False,
    include_methods=False,
)
```

Use `include_source_locations=False` when generated sidecars or rendered
references should not expose local source paths and line numbers. Collection
still uses source positions internally to keep stable object ordering, then
strips source paths, line numbers, and location-like metadata from the returned
API tree.

```python
api = collect_api(
    ".",
    collector="inspect",
    public_policy="__all__",
    include_source_locations=False,
)
api.to_document(profile="website").save_html("artifacts/api/index.html")
```
