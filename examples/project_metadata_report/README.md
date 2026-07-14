# Project Metadata Report Example

This example turns repository configuration files into a rendered report and a
machine-readable sidecar. It reads `pyproject.toml` through
`collect_pyproject_info(...)`. For the release workflow, it first attempts
`collect_github_actions_workflow(...)` and uses a small regex fallback only
when PyYAML is unavailable. Both paths return generic models that can also be
constructed directly from mappings and sequences.

Use it when package metadata, build backend settings, and GitHub Actions jobs
should be reviewed as a document instead of inspected across separate files.

Run the full bundle:

```powershell
python examples/project_metadata_report/main.py --output-dir artifacts/project-metadata-report
```

Render one format while iterating:

```powershell
python examples/project_metadata_report/main.py --outputs html --quiet
```

Programmatic entry points:

- `load_project_inputs(...)` reads the pyproject and workflow files.
- `build_document(...)` returns the complete `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs, writes `project-metadata.json`, and returns a
  `ProjectMetadataReportBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
