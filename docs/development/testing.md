# Testing

Use a small test set during normal development and reserve full rendering,
example builds, and self-API inventory checks for release or merge gates.

## Fast Development Loop

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not slow and not render and not apidoc_full and not examples"
```

This keeps the public API contract, ordinary unit tests, importers, validation,
and lightweight apidoc model tests in the loop while skipping expensive
artifact generation.

For the public API and naming contract only:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contracts
```

## Release Gate

Before release or merge, run the complete suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The full suite includes:

- `render`: DOCX/PDF/HTML rendering coverage
- `apidoc_full`: full OODocs self-API collection and reference bundle checks
- `examples`: example script smoke tests
- `slow`: repository-layout and integration tests
- `contracts`: public API and naming contract tests

The API documentation gate is separate from pytest and should also pass before
release:

```powershell
.\.venv\Scripts\oodocs.exe apidoc check . --config pyproject.toml --fail-under 0.90
```

## Marker Policy

- Mark DOCX/PDF/HTML renderer-heavy tests with `@pytest.mark.render`.
- Mark full `collect_api("oodocs")` or repository-wide self-reference tests with
  `@pytest.mark.apidoc_full`.
- Mark example script tests with `@pytest.mark.examples`.
- Mark packaging-layout and multi-step integration tests with `@pytest.mark.slow`.
- Keep `contracts` tests small and policy-oriented. Avoid exact full namespace
  snapshots unless the snapshot is the test's purpose.
