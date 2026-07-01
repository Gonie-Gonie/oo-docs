# Check Docstring Coverage

Use `ApiHelpBookConfig.check_docs(...)` when a repository stores apidoc settings
in `pyproject.toml` or a JSON sidecar:

```python
from oodocs.apidoc import ApiHelpBookConfig

build = ApiHelpBookConfig.from_pyproject(".")
coverage = build.check_docs(".", fail_under=0.90)
coverage.save_json("artifacts/api-coverage.json")
coverage.save_csv("artifacts/api-coverage.csv")
```

Use `check_api_docs(...)` directly when coverage evidence should be inserted
into an already collected API object tree, or use the CLI when CI should
enforce a minimum ratio.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import check_api_docs, collect_api

api = collect_api("oodocs", public_policy="__all__", collector="griffe")
coverage = check_api_docs(api, fail_under=0.90)

doc = Document("Release Evidence", Chapter("API Coverage", coverage.to_table()))
coverage.save_json("artifacts/api-coverage.json")
coverage.save_csv("artifacts/api-coverage.csv")
```

Doctest-style examples are parsed by default. When examples should also be
executed, pass a trusted namespace from Python:

```python
from oodocs.apidoc import check_api_docs, collect_api
from mypkg import connect

api = collect_api(".", public_policy="__all__")
coverage = check_api_docs(
    api,
    fail_under=0.90,
    doctest_namespace={"connect": connect},
)
```

Read the JSON sidecar back later when report generation runs in a separate job:

```python
from oodocs import Chapter, Document
from oodocs.apidoc import ApiCoverageResult

coverage = ApiCoverageResult.load_json("artifacts/api-coverage.json")
doc = Document("API Evidence", Chapter("Coverage", coverage.to_table()))
```

CLI equivalent:

```powershell
python -m oodocs apidoc check oodocs --collector griffe --public-policy __all__ --fail-under 0.90 --save-json artifacts/api-coverage.json --save-csv artifacts/api-coverage.csv
```

The JSON sidecar stores the complete coverage result for later rendering. The
CSV sidecar stores the coverage issue rows for CI artifacts and spreadsheet
review.

When a repository needs both a user-facing API reference and coverage evidence,
render the reference from the base config and the evidence output from the
profile-specific subtable:

```python
from oodocs.apidoc import ApiHelpBookConfig

ApiHelpBookConfig.from_pyproject(".").save_all(".")
ApiHelpBookConfig.from_pyproject(".", profile="evidence").save_all(".")
```

For larger repositories, gate only the API area currently under review:

```powershell
python -m oodocs apidoc check . --collector griffe --kind class --module-prefix mypkg.widgets --fail-under 0.95
```

The same `kind` and `module-prefix` filters may be stored in
`[tool.oodocs.apidoc]`, where they are reused by `check`, `snapshot`, and
`build`:

```powershell
python -m oodocs apidoc check . --config pyproject.toml --fail-under 0.95
```

Coverage issues include missing summaries, missing parameter docs, extra
parameter docs, missing return docs, example syntax errors, doctest parse or
execution failures, and missing deprecation guidance. The coverage table also
records syntax-checked examples and doctest-checked examples separately so CI
evidence can distinguish normal Python code blocks from `>>>` examples.
