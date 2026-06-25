# apidoc CLI Reference

All commands are available under `oodocs apidoc` or `python -m oodocs apidoc`.

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
`--explicit-name`, `--docstring-style`, `--include-imported`, `--config`,
`--include-inherited`, `--module-include`, and `--module-exclude`.
Module include/exclude patterns are applied before module contents are
collected, while `check`, `build`, and `snapshot` also accept `--kind` and
`--module-prefix` object filters after collection. `build` also accepts
`--max-level` to cap nested API section depth and the generated table of
contents. Use `--sidecars` when one build should leave the rendered documents,
the collected API object JSON, and coverage JSON/CSV evidence in the same
output directory.
