# Configuration Reference Example

This example reads a TOML config file and a JSON schema, then renders a field
reference with required fields, optional fields, defaults, current values,
examples, and environment variable overrides.

Use it when project configuration should become a reviewable reference instead
of living only as schema files and inline comments.

Run the full bundle:

```powershell
python examples/config_reference_example/main.py --output-dir artifacts/config-reference-example
```

Render one format while iterating:

```powershell
python examples/config_reference_example/main.py --outputs html --quiet
```

Programmatic entry points:

- `ConfigField` represents one schema-backed config field.
- `ConfigReference.to_summary_table()` and `ConfigReference.to_section()`
  convert config metadata into OODocs blocks.
- `load_config_reference(...)` reads `sample_config.toml` and
  `sample_schema.json`.
- `build_document(reference=None)` returns the complete `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs and returns an `OutputBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
