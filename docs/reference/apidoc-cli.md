# apidoc CLI Reference

All commands are available under `oodocs apidoc` or `python -m oodocs apidoc`.
The CLI collects, checks, snapshots, and diffs API object data. Rendered API
documents are created through the Python API with `ApiHelpBookConfig.save_all(...)`.

## Initialize Config

Create repository-local apidoc settings:

```powershell
python -m oodocs apidoc init . --collector griffe --public-policy __all__ --presentation website --outputs html --out-dir artifacts/api
```

`init` can validate custom parser styles registered by modules inside the
target repository. The command temporarily adds the repository root and `src/`
directory while it builds the config:

```powershell
python -m oodocs apidoc init ../mypkg --docstring-parser-module docs_parsers --docstring-style brief --outputs html
```

Render from that config in Python:

```python
from oodocs.apidoc import ApiHelpBookConfig

build = ApiHelpBookConfig.from_pyproject(".")
outputs = build.save_all(".")
```

## Collect

Collect an API tree:

```powershell
python -m oodocs apidoc collect oodocs --collector griffe --public-policy __all__ --save-json artifacts/api-index.json
```

Reuse a collection config JSON or `pyproject.toml`:

```powershell
python -m oodocs apidoc collect . --config apidoc-config.json --save-json artifacts/api-index.json
python -m oodocs apidoc collect . --config pyproject.toml --save-json artifacts/api-index.json
```

## Check

Check documentation coverage:

```powershell
python -m oodocs apidoc check oodocs --collector griffe --public-policy __all__ --fail-under 0.90
```

Write coverage evidence while checking:

```powershell
python -m oodocs apidoc check . --config pyproject.toml --fail-under 0.90 --save-json artifacts/api-coverage.json --save-csv artifacts/api-coverage.csv
```

Emit a JSON report on stdout:

```powershell
python -m oodocs apidoc check . --config pyproject.toml --report-format json
```

The JSON sidecar stores the complete coverage result. The CSV sidecar stores
the issue rows.

## Snapshot And Diff

Create snapshots and a machine-readable diff:

```powershell
python -m oodocs apidoc snapshot oodocs --save-json artifacts/api-base.json
python -m oodocs apidoc snapshot oodocs --kind function --module-prefix oodocs.adapters --save-json artifacts/api-head.json
python -m oodocs apidoc diff artifacts/api-base.json artifacts/api-head.json --save-json artifacts/api-diff.json
```

Render a diff document in Python:

```python
from oodocs.apidoc import ApiDiffResult

diff = ApiDiffResult.load_json("artifacts/api-diff.json")
diff.to_document().save_all("artifacts/api-diff", stem="api-diff")
```

## Render API Documents

Use `ApiHelpBookConfig` when API object data should be composed into OODocs
documents:

```python
from oodocs.apidoc import ApiHelpBookConfig

build = ApiHelpBookConfig.from_pyproject(".")
outputs = build.save_all(".")
```

For ad-hoc rendering without a config file:

```python
from oodocs.apidoc import ApiHelpBookConfig, ApiCollectConfig

build = ApiHelpBookConfig(
    collection=ApiCollectConfig(collector="griffe", public_policy="__all__"),
    presentation="reference",
    output_formats=("docx", "pdf", "html"),
    output_dir="artifacts/api",
    sidecars=True,
)
outputs = build.save_all("oodocs")
```

## Common Options

Common collection options are `--collector`, `--public-policy`,
`--fallback-collector`, `--explicit-name`, `--docstring-style`,
`--docstring-parser-module`, `--include-private`, `--no-private`,
`--include-imported`, `--config`, `--include-inherited`,
`--include-attributes`, `--no-attributes`, `--include-properties`,
`--no-properties`, `--include-methods`, `--no-methods`,
`--include-source-locations`, `--no-source-locations`,
`--source-root`, `--class-signature-from-init`, `--no-class-signature-from-init`,
`--module-include`, `--module-exclude`, `--object-include`, and
`--object-exclude`.

`check` and `snapshot` also accept `--kind` and `--module-prefix` object
filters after collection. `check` accepts `--fail-under`,
`--require-examples`, `--require-renderer-notes`, `--report-format`,
`--save-json`, and `--save-csv`. `collect`, `snapshot`, and `diff` write JSON
with `--save-json`.
