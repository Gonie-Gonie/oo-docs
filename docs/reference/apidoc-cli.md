# apidoc CLI Reference

All commands are available under `oodocs apidoc` or `python -m oodocs apidoc`.

Create repository-local apidoc settings:

```powershell
python -m oodocs apidoc init . --collector griffe --public-policy __all__ --presentation-profile website --outputs html --out-dir artifacts/api
python -m oodocs apidoc build . --config pyproject.toml
```

`init` can validate custom parser styles registered by modules inside the
target repository. The command temporarily adds the repository root and `src/`
directory while it builds the config:

```powershell
python -m oodocs apidoc init C:\work\mypkg --docstring-parser-module docs_parsers --docstring-style brief --outputs html
python -m oodocs apidoc build C:\work\mypkg --config C:\work\mypkg\pyproject.toml
```

Collect an API tree:

```powershell
python -m oodocs apidoc collect oodocs --collector griffe --public-policy __all__ --out artifacts/api-index.json
```

Reuse a collection config JSON or `pyproject.toml`:

```powershell
python -m oodocs apidoc collect . --config apidoc-config.json --out artifacts/api-index.json
python -m oodocs apidoc collect . --config pyproject.toml --out artifacts/api-index.json
```

Check documentation coverage:

```powershell
python -m oodocs apidoc check oodocs --collector griffe --public-policy __all__ --fail-under 0.90
```

Write coverage evidence while checking:

```powershell
python -m oodocs apidoc check . --config pyproject.toml --fail-under 0.90 --out-json artifacts/api-coverage.json --out-csv artifacts/api-coverage.csv
```

The JSON output stores the complete coverage result; the CSV output stores the
issue rows.

Filter coverage to selected object kinds or module prefixes:

```powershell
python -m oodocs apidoc check oodocs --kind class --module-prefix oodocs.components --fail-under 0.95
```

Build rendered API documents:

```powershell
python -m oodocs apidoc build oodocs --presentation-profile reference --out artifacts/api --outputs docx,pdf,html
```

Without `--kind` or `--module-prefix`, `build` renders a complete package API
reference through `ApiPackage.to_document(...)`. The resulting document contains
an API contents section, coverage overview, module summaries, object sections,
and any sidecars requested for later review or release evidence.

Write API object and coverage sidecars beside the rendered bundle:

```powershell
python -m oodocs apidoc build . --config pyproject.toml --presentation-profile reference --out artifacts/api --outputs docx,pdf,html --sidecars
```

The same build defaults can live in `pyproject.toml`:

```toml
[tool.oodocs.apidoc]
collector = "griffe"
public-policy = "__all__"
docstring-style = "auto"
object-exclude-patterns = ["render_to_docx", "render_to_pdf", "render_to_html"]
include-private = false
include-attributes = true
include-properties = true
include-methods = true
include-source-locations = true
profile = "website"
formats = ["html"]
out = "artifacts/api"
sidecars = true
module-exclude-patterns = ["mypkg.tests*"]
```

```powershell
python -m oodocs apidoc build . --config pyproject.toml
```

Custom docstring parser modules can live in the same section:

```toml
[tool.oodocs.apidoc]
docstring-style = "brief"
docstring-parser-modules = ["mypkg.docs_parsers"]
```

The same parser hook can be supplied directly on the command line. When the
target is a repository path, `apidoc` temporarily adds that repository root,
its configured source roots (`src/`, `package-dir`, or `packages.find.where`),
hatch/Poetry/PDM package roots, and the package parent to Python's import
path while loading parser modules:

```powershell
python -m oodocs apidoc build . --docstring-parser-module docs_parsers --docstring-style brief --out artifacts/api
```

Limit nested API heading depth for larger repositories:

```powershell
python -m oodocs apidoc build oodocs --presentation-profile reference --max-level 2 --out artifacts/api --outputs html
```

Filter build output:

```powershell
python -m oodocs apidoc build oodocs --kind class --kind function --module-prefix oodocs.components --presentation-profile compact --out artifacts/api
```

Filtered builds apply the selected profile to both the summary table and the
rendered object sections. For example, `--presentation-profile website` produces summary
table links that point at the generated object section anchors.

Object include/exclude filters are applied after collection and match either a
fully qualified name or the local object name:

```powershell
python -m oodocs apidoc build . --object-exclude render_to_pdf --object-exclude render_to_html --out artifacts/api
python -m oodocs apidoc collect . --object-include mypkg.Client --out artifacts/client-api.json
```

Member kind switches are applied during collection. They are useful when a
reference should keep modules, classes, and functions but omit selected nested
member kinds:

```powershell
python -m oodocs apidoc build . --no-attributes --no-properties --no-methods --out artifacts/api
```

Private and protected names can be collected for internal review documents:

```powershell
python -m oodocs apidoc collect . --include-private --out artifacts/internal-api.json
```

Curated public boundaries can be built with `public-policy=explicit` and one
or more `--explicit-name` values:

```powershell
python -m oodocs apidoc build . --public-policy explicit --explicit-name mypkg.Client --explicit-name mypkg.connect --out artifacts/api --outputs html --sidecars
```

Source locations can also be stripped during collection when rendered
references or JSON sidecars should not expose local paths:

```powershell
python -m oodocs apidoc build . --no-source-locations --out artifacts/api
```

Snapshot and diff:

```powershell
python -m oodocs apidoc snapshot oodocs --out artifacts/api-snapshot.json
python -m oodocs apidoc snapshot oodocs --kind function --module-prefix oodocs.adapters --out artifacts/api-functions.json
python -m oodocs apidoc diff --base artifacts/api-base.json --head artifacts/api-snapshot.json --out artifacts/api-diff
```

The diff command reports added and removed objects, signature changes, default
value changes, parameter annotation changes, return annotation changes,
docstring changes, deprecated objects, and coverage deltas.

Common collection options are `--collector`, `--public-policy`,
`--fallback-collector`, `--explicit-name`, `--docstring-style`,
`--docstring-parser-module`, `--include-private`, `--no-private`,
`--include-imported`, `--config`, `--include-inherited`,
`--include-attributes`, `--no-attributes`,
`--include-properties`, `--no-properties`, `--include-methods`,
`--no-methods`, `--include-source-locations`, `--no-source-locations`,
`--class-signature-from-init`,
`--no-class-signature-from-init`, `--module-include`, `--module-exclude`,
`--object-include`, and `--object-exclude`.
Module include/exclude patterns are applied before module contents are
collected. Object include/exclude patterns are applied after collection and can
remove public-but-internal hooks such as renderer adapters from the generated
tree. `check`, `build`, and `snapshot` also accept `--kind` and
`--module-prefix` object filters after collection. `check` also accepts
`--fail-under`, `--require-examples`, `--require-renderer-notes`, `--out-json`,
and `--out-csv`. `build` also accepts `--presentation-profile`, `--outputs`, `--stem`,
`--max-level`, `--out`, and `--sidecars`.
When those build options are omitted, `build` can read `profile`, `formats`,
`stem`, `max-level`, `out`/`output-dir`, and `sidecars` from
`[tool.oodocs.apidoc]`. The `kind` and `module-prefix` settings in the same
section are object filters shared by `check`, `snapshot`, and `build`, with
explicit CLI flags taking precedence. In `pyproject.toml`, `module-prefix` is a
single string such as `module-prefix = "mypkg.adapters"`; use
`module-include-patterns = ["mypkg.*", "plugins.*"]` when collection should
include several module families. Custom parser modules can be stored as
`docstring-parser-modules = ["mypkg.docs_parsers"]` or supplied with
`--docstring-parser-module`. `init` writes the same section to `pyproject.toml`
by default, or writes a standalone JSON config when the target path ends in
`.json` or `--config-format json` is passed.
