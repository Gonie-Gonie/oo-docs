# Build An API Summary Table

Summary tables are useful in release evidence, module overviews, and migration
notes where a full section per object is too much.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
functions = api.select_objects(kind="function")

doc = Document(
    "Function Index",
    Chapter(
        "Public Functions",
        api.to_summary_table(
            functions,
            profile="compact",
            caption="Public function summary.",
        ),
    ),
)
doc.save_all("artifacts/function-index", stem="function-index", formats=("docx", "pdf", "html"))
```

`ApiModule.to_summary_table(...)` and `ApiPackage.to_summary_table(...)` accept
an explicit object sequence. Pass the subset you already filtered so the table
matches the surrounding document.
