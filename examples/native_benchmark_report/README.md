# Native Benchmark Report Example

This example shows a pure-Python result-to-report workflow. The script generates
a deterministic workload, benchmarks several callables, carries checksums and
timings into typed result objects, records environment metadata, writes a JSON
sidecar, and renders the report bundle.

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
- `benchmark_normalizers(...)` returns `BenchmarkResult` objects.
- `validate_benchmark_results(...)` checks checksum agreement and positive
  timings before the report is written.
- `benchmark_results_to_table(...)` converts result objects into an OODocs
  `Table`.
- `build_benchmark_document()` returns the complete `Document`.
- `build_native_benchmark_report(output_dir=..., output_formats=..., verbose=False)`
  writes selected outputs, writes `native-python-benchmark.json`, and returns a
  `BenchmarkReportBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
