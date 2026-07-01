# API Coverage Evidence

Use API coverage checks as release/development evidence, not as the first page
of the user-facing API Reference.

## Check Coverage

```python
from oodocs.apidoc import ApiHelpBookConfig

build = ApiHelpBookConfig.from_pyproject(".")
coverage = build.check_docs(".", fail_under=0.90)
coverage.save_json("artifacts/api-coverage.json")
coverage.save_csv("artifacts/api-coverage.csv")
```

CLI equivalent:

```powershell
python -m oodocs apidoc check . --config pyproject.toml --fail-under 0.90 --save-json artifacts/api-coverage.json --save-csv artifacts/api-coverage.csv
```

## Render Evidence

When a release review needs a rendered evidence document, load the evidence
profile rather than changing the user-facing reference config:

```python
from oodocs.apidoc import ApiHelpBookConfig

ApiHelpBookConfig.from_pyproject(".", profile="evidence").save_all(".")
```

The repository release workflow also keeps the user-facing API reference free of
coverage tables and checks category coverage separately with
`check_api_help_categories(...)`.

## What Coverage Checks

Coverage issues include missing summaries, missing parameter docs, extra
parameter docs, missing return docs, example syntax errors, doctest parse or
execution failures, and missing deprecation guidance.

Doctest-style examples are parsed by default. Execute them only when the test
can provide a trusted namespace:

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
