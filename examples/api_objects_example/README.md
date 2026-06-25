# API Objects Example

This example shows the composable API-documentation workflow:

1. collect an `ApiPackage` from the `oodocs` source tree
2. render a full package API reference as DOCX, PDF, and HTML artifacts named
   `oodocs-full-api-reference`
3. render a hand-composed `oodocs-api-objects` document that inserts selected
   class sections, a function summary table, and coverage evidence into an
   ordinary OODocs document
4. write deterministic JSON and CSV sidecars for release evidence

Run it from the repository root:

```powershell
python examples/api_objects_example/main.py
```

The script writes rendered files under `artifacts/api-objects-example`.
Both the full package reference and the selected composition document are saved
as DOCX, PDF, and HTML so the generated API documentation can be reviewed,
published, or attached to release evidence directly.
