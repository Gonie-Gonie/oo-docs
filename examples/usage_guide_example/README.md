# Usage Guide Example

This example renders the OODocs user guide. It is the conceptual reference for
the package: object-oriented authoring, renderer behavior, imports, validation,
CLI workflow, layout controls, references, and presets.

Use it when you want to learn how the model fits together before choosing a
workflow-specific example.

Run the full bundle:

```powershell
python examples/usage_guide_example/main.py --output-dir artifacts/usage-guide
```

Render one format while iterating:

```powershell
python examples/usage_guide_example/main.py --outputs html --quiet
```

Programmatic entry points:

- `build_usage_guide_document()` returns the complete `Document`.
- `build_usage_guide(output_dir=..., output_formats=..., verbose=False)` writes
  selected outputs and returns an `OutputBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
