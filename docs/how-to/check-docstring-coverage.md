# Check Docstring Coverage

Use `check_api_docs(...)` from Python when coverage evidence should be inserted
into a document, or use the CLI when CI should enforce a minimum ratio.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import check_api_docs, collect_api

api = collect_api("oodocs", public_policy="__all__", collector="griffe")
coverage = check_api_docs(api, fail_under=0.90)

doc = Document("Release Evidence", Chapter("API Coverage", coverage.to_table()))
coverage.write_json("artifacts/api-coverage.json")
coverage.write_csv("artifacts/api-coverage.csv")
```

CLI equivalent:

```powershell
python -m oodocs apidoc check oodocs --collector griffe --public-policy __all__ --fail-under 0.90
```

For larger repositories, gate only the API area currently under review:

```powershell
python -m oodocs apidoc check . --collector griffe --kind class --module-prefix mypkg.widgets --fail-under 0.95
```

Coverage issues include missing summaries, missing parameter docs, extra
parameter docs, missing return docs, example syntax errors, and missing
deprecation guidance.
