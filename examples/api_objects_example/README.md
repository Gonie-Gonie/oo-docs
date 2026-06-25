# API Objects Example

This example shows the composable API-documentation workflow:

1. collect an `ApiPackage` from the `oodocs` source tree
2. render a full package API reference as
   `oodocs-full-api-reference.html`
3. render a hand-composed `oodocs-api-objects` document that inserts selected
   class sections, a function summary table, and coverage evidence into an
   ordinary OODocs document
4. write deterministic JSON and CSV sidecars for release evidence

Run it from the repository root:

```powershell
python examples/api_objects_example/main.py
```

The script writes rendered files under `artifacts/api-objects-example`.
The full reference is HTML-first so it remains practical for the entire public
API, while the selected composition document is saved as DOCX, PDF, and HTML.
