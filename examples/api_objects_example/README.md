# API Objects Example

This example shows the composable API-documentation workflow:

1. collect an `ApiPackage` from the `oodocs` source tree
2. build a full package API document
3. build a hand-selected class chapter
4. build a function summary table for insertion into another document
5. write deterministic JSON and CSV sidecars for release evidence

Run it from the repository root:

```powershell
python examples/api_objects_example/main.py
```

The script writes rendered files under `artifacts/api-objects-example`.
