# Integrations

`oodocs.integrations` contains parsers and collectors whose behavior depends on
an external tool or file format. The returned objects are generic models, so an
application can construct the same models directly from Python mappings and
sequences.

```python
from oodocs.integrations.pyproject import collect_pyproject_info
from oodocs.integrations.github_actions import collect_github_actions_workflow

project = collect_pyproject_info("pyproject.toml")
workflow = collect_github_actions_workflow(".github/workflows/ci.yml")

project_section = project.to_section()
workflow_section = workflow.to_section()
```

The project collector uses the standard-library TOML reader. The workflow
collector imports PyYAML only when it is called; install
`oodocs[integrations]` when that collector is needed. Importing `oodocs` never
loads YAML, pandas, Pint, or BibTeX backends.

Core models live outside this namespace:

- `ProjectInfo`, `WorkflowJob`, `WorkflowSummary`, and `ManifestSummary` are in
  `oodocs.metadata`.
- `EvidenceItem`, `EvidenceReport`, and `EvidenceBundle` are in
  `oodocs.evidence`.
- Optional argparse, BibTeX, Pint, and SymPy bridges live in their respective
  `oodocs.integrations.*` modules.

Integration functions use `collect_*` when they inspect an external program or
format. Core models use `from_*` for raw input, `load_*` for file restoration,
`to_*` for OODocs objects, and `as_*` for ordinary Python records.
