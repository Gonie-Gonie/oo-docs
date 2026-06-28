# Validation Gate Report Example

This example uses `Document.validate()` as a release gate. A candidate document
is validated, warning policy is applied, diagnostics are rendered into a report,
and the raw `ValidationResult` is written to `validation-result.json`.

Use it when CI or release scripts should leave both a human-readable validation
report and a machine-readable diagnostics sidecar.

Run the full bundle:

```powershell
python examples/validation_gate_report/main.py --output-dir artifacts/validation-gate-report
```

Render one format while iterating:

```powershell
python examples/validation_gate_report/main.py --outputs html --quiet
```

Programmatic entry points:

- `build_candidate_document()` creates a document with intentional validation
  warnings.
- `evaluate_gate(result, allowed_warning_codes=...)` applies release policy.
- `build_document(validation_result=None)` returns the report `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs, writes `validation-result.json`, and returns a `ValidationGateBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
