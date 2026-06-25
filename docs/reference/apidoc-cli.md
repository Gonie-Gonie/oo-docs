# apidoc CLI Reference

All commands are available under `oodocs apidoc` or `python -m oodocs apidoc`.

Collect an API tree:

```powershell
python -m oodocs apidoc collect oodocs --collector griffe --public-policy __all__ --out artifacts/api-index.json
```

Check documentation coverage:

```powershell
python -m oodocs apidoc check oodocs --collector griffe --public-policy __all__ --fail-under 0.90
```

Build rendered API documents:

```powershell
python -m oodocs apidoc build oodocs --profile reference --out artifacts/api --to docx,pdf,html
```

Filter build output:

```powershell
python -m oodocs apidoc build oodocs --kind class --kind function --module-prefix oodocs.components --profile compact --out artifacts/api
```

Snapshot and diff:

```powershell
python -m oodocs apidoc snapshot oodocs --out artifacts/api-snapshot.json
python -m oodocs apidoc diff --base artifacts/api-base.json --head artifacts/api-snapshot.json --out artifacts/api-diff
```

Common collection options are `--collector`, `--public-policy`,
`--explicit-name`, and `--docstring-style`.

