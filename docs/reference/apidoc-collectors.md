# apidoc Collectors

Collectors normalize Python source metadata into the same `ApiPackage` schema.
Targets may be importable package/module names, one Python file, a package
directory, a `src/` layout package, a `src/` layout namespace package that
omits `__init__.py`, or a repository root that publishes direct module files
through `[tool.setuptools] py-modules`. Repository roots that use setuptools
custom source roots are also supported through
`[tool.setuptools] package-dir = {"" = "lib"}` or
`[tool.setuptools.packages.find] where = ["lib"]`, hatch wheel
`packages`/`only-include` settings, Poetry `packages` entries, PDM
`[tool.pdm.build] package-dir`/`includes` settings.
Multiple hatch `packages` entries are grouped under their common source roots,
so one repository reference can include several top-level packages.
When `[project] import-names` or `import-namespaces` is present, OODocs uses
those packaging-standard import names to find the published modules and avoids
including unrelated helper packages from the checkout.
Flit projects are resolved by import name: the default import name is the
`[project] name` with hyphens translated to underscores, and
`[tool.flit.module] name` is honored when the distribution and import names
differ.

```toml
[project]
name = "sample-project"

[tool.setuptools]
package-dir = {"" = "lib"}
```

```python
from oodocs.apidoc import collect_api

api = collect_api(".", collector="inspect", public_policy="__all__")
assert api.find("samplepkg.run") is not None
```

PDM projects with a custom source directory can be targeted the same way:

```toml
[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"

[project]
name = "sample-project"

[tool.pdm.build]
package-dir = "lib"
```

```python
from oodocs.apidoc import collect_api

api = collect_api(".", collector="griffe", public_policy="__all__")
assert api.find("samplepkg.run") is not None
```

Hatch projects that publish a package through `only-include` are also resolved
from the repository root. When the included path points at a package directory,
OODocs uses that directory's parent as the import root so rendered names stay
`samplepkg.*`, not `lib.samplepkg.*`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sample-project"

[tool.hatch.build.targets.wheel]
only-include = ["lib/samplepkg"]
```

```python
from oodocs.apidoc import collect_api

api = collect_api(".", collector="inspect", public_policy="__all__")
assert api.find("samplepkg.run") is not None
assert api.find("lib.samplepkg.run") is None
```

For backend-independent import metadata, declare the import names directly in
`[project]`:

```toml
[project]
name = "published-name"
import-names = ["import_name"]
```

```python
from oodocs.apidoc import collect_api

api = collect_api(".", collector="griffe", public_policy="__all__")
assert api.find("import_name.run") is not None
```

Flit projects that publish a different import name can also be targeted by the
repository root. OODocs narrows collection to the declared Flit import module
instead of sweeping unrelated packages from the checkout:

```toml
[build-system]
requires = ["flit_core >=3.11,<5"]
build-backend = "flit_core.buildapi"

[project]
name = "published-name"

[tool.flit.module]
name = "import_name"
```

```python
from oodocs.apidoc import collect_api

api = collect_api(".", collector="inspect", public_policy="__all__")
assert api.find("import_name.run") is not None
```

For a single-module project, pass the repository root. OODocs uses the declared
source root and keeps the public module name stable in rendered anchors and JSON
sidecars:

```toml
[project]
name = "reporting"

[tool.setuptools]
package-dir = {"" = "src"}
py-modules = ["reporting"]
```

```python
from oodocs.apidoc import collect_api

api = collect_api(".", collector="inspect", public_policy="__all__")
assert api.find("reporting.build_report") is not None
```

PDM module-file repositories can declare the module through `includes`:

```toml
[tool.pdm.build]
includes = ["reporting.py"]
```

Flit single-module repositories use the default import name from `[project]`
or the explicit `[tool.flit.module] name`, so sibling helper files are not
published in the generated API tree.

For a standalone module file, pass the file path directly. The file stem becomes
the package/module name in generated sidecars and rendered references:

```python
from oodocs.apidoc import ApiDocstringParser, collect_api

api = collect_api(
    "tools/reporting.py",
    collector="inspect",
    public_policy="underscore",
    docstring_style=ApiDocstringParser.auto(),
)
assert api.find("reporting.build_report") is not None
api.to_document(profile="reference").save_all(
    "artifacts/api",
    stem="reporting-api",
    formats=("docx", "pdf", "html"),
)
```

- `collector="griffe"` uses griffe when installed. It captures module data,
  aliases, properties, class attributes, public `__init__` instance
  attributes, and line metadata without importing the target package.
- `collector="inspect"` uses the source-compatible collector and avoids runtime
  imports while normalizing the same object kinds when they can be inferred from
  source. It records an informational `inspect-source-collector` issue so
  JSON sidecars and issue tables make the import-safe path explicit.
- `collector="auto"` tries griffe first and records a fallback issue if source
  collection is used.

By default, griffe failures fall back to the inspect-compatible source
collector and add an informational issue such as `griffe-unavailable` or
`griffe-load-failed` to the API sidecar. Set `fallback_collector="none"` when
CI should fail loudly instead of rendering a best-effort fallback reference:

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

Overloaded functions are represented as one callable object for the runtime
implementation. Source and griffe collection skip `@overload` stubs as separate
objects and store their signatures in `ApiObject.metadata["overloads"]`:

```python
api = collect_api(".", collector="griffe", public_policy="__all__")
parse = api.find("mypkg.parse")
for overload in parse.metadata.get("overloads", []):
    print(overload["signature"])
```

When griffe resolves a public re-export inside the collected package, OODocs
copies missing documentation fields from the collected target object onto the
alias. This keeps top-level convenience imports such as `mypkg.Widget` or
`mypkg.OutputFormat` useful in rendered reference pages while preserving
`metadata["reexported_from"]` for traceability.

Class signatures use `__init__` parameters by default. When a class docstring
does not document those parameters directly, both source and griffe collection
can use the `__init__` docstring's parameter section as the class constructor
parameter documentation. Disable that behavior with
`class-signature-from-init = false` in config or
`--no-class-signature-from-init` on the CLI.

For dataclasses without an explicit `__init__`, source-compatible collection
uses public dataclass fields to build the class signature and constructor
parameter metadata. Fields marked `field(init=False)` remain attributes but are
not treated as constructor parameters.

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

Use `include_private=True` when an internal reference should collect
underscore-prefixed objects in addition to the normal public boundary. Collected
objects keep their original `visibility`, so `api.public_objects()` still
returns only public entries while `api.private_objects()` can be used for an
internal appendix.

```python
api = collect_api(
    ".",
    collector="inspect",
    public_policy="__all__",
    include_private=True,
)
internal = api.private_objects()
```

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
from oodocs.apidoc import ApiBuildConfig

build = ApiBuildConfig.from_pyproject(".")
outputs = build.save_all(".", output_dir="artifacts/api")
api_json = outputs["api-json"]
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

When griffe collection is used with a standard style (`auto`, `google`,
`numpy`, or `sphinx`), OODocs passes the same style hint to `griffe.load(...)`
and then normalizes the raw docstring through the OODocs parser schema. Custom,
Markdown, and plain parser styles stay in the OODocs parser layer.

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
