# Native Benchmark Report Example

This example shows a pure-Python result-to-report workflow. The script generates
a deterministic workload, benchmarks several callables, carries checksums and
timings into tables, and renders the report bundle.

Use it when the document should explain measured Python work without requiring a
notebook, external benchmark framework, or separate report authoring step.

Run the full bundle:

```powershell
python examples/native_benchmark_report/main.py --output-dir artifacts/native-benchmark-report
```

Render one format while iterating:

```powershell
python examples/native_benchmark_report/main.py --outputs html --quiet
```

Programmatic entry points:

- `generate_payload(...)` creates deterministic benchmark inputs.
- `benchmark_normalizers(...)` returns structured timing rows.
- `build_benchmark_document()` returns the complete `Document`.
- `build_native_benchmark_report(output_dir=..., output_formats=..., verbose=False)`
  writes selected outputs and returns an `OutputBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
