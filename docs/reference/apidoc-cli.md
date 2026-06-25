# apidoc CLI Reference

All commands are available under `oodocs apidoc` or `python -m oodocs apidoc`.

Create repository-local apidoc settings:

```powershell
python -m oodocs apidoc init . --collector griffe --public-policy __all__ --profile website --to html --out-dir artifacts/api
python -m oodocs apidoc build . --config pyproject.toml
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
python -m oodocs apidoc build oodocs --profile reference --out artifacts/api --to docx,pdf,html
```

Write API object and coverage sidecars beside the rendered bundle:

```powershell
python -m oodocs apidoc build . --config pyproject.toml --profile reference --out artifacts/api --to docx,pdf,html --sidecars
```

The same build defaults can live in `pyproject.toml`:

```toml
[tool.oodocs.apidoc]
collector = "griffe"
public-policy = "__all__"
docstring-style = "auto"
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

Limit nested API heading depth for larger repositories:

```powershell
python -m oodocs apidoc build oodocs --profile reference --max-level 2 --out artifacts/api --to html
```

Filter build output:

```powershell
python -m oodocs apidoc build oodocs --kind class --kind function --module-prefix oodocs.components --profile compact --out artifacts/api
```

Filtered builds apply the selected profile to both the summary table and the
rendered object sections. For example, `--profile website` produces summary
table links that point at the generated object section anchors.

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
`--explicit-name`, `--docstring-style`, `--docstring-parser-module`,
`--include-imported`, `--config`, `--include-inherited`, `--module-include`,
and `--module-exclude`.
Module include/exclude patterns are applied before module contents are
collected, while `check`, `build`, and `snapshot` also accept `--kind` and
`--module-prefix` object filters after collection. `check` also accepts
`--fail-under`, `--require-examples`, `--require-renderer-notes`, `--out-json`,
and `--out-csv`. `build` also accepts `--profile`, `--to`, `--stem`,
`--max-level`, `--out`, and `--sidecars`.
When those build options are omitted, `build` can read `profile`, `formats`,
`stem`, `max-level`, `out`/`output-dir`, `sidecars`, `kind`, and
`module-prefix` from `[tool.oodocs.apidoc]`. Custom parser modules can be
stored as `docstring-parser-modules = ["mypkg.docs_parsers"]` or supplied with
`--docstring-parser-module`. `init` writes the same section to `pyproject.toml`
by default, or writes a standalone JSON config when the target path ends in
`.json` or `--format json` is passed.
