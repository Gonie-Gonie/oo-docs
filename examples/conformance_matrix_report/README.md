# Conformance Matrix Report Example

This example documents a wide conformance matrix without forcing every evidence
column into the PDF body. The report includes a claim boundary, status summary,
PDF excerpt matrix, failure detail appendix, and full JSON sidecar.

Use it when simulation, test, or compatibility evidence has many columns but the
review document should stay readable.

Run the full bundle:

```powershell
python examples/conformance_matrix_report/main.py --output-dir artifacts/conformance-matrix-report
```

Render one format while iterating:

```powershell
python examples/conformance_matrix_report/main.py --outputs html --quiet
```

Programmatic entry points:

- `load_results(...)` reads `data/conformance-results.csv`.
- `save_full_matrix(records, output_dir)` writes `conformance-matrix-full.json`.
- `build_document(records=None)` returns the complete `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs, writes the full matrix sidecar, and returns a
  `ConformanceMatrixBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
