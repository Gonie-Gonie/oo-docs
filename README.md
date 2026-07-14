# oodocs

OODocs is a Python-first toolkit for building one structured document tree and
rendering it to DOCX, PDF, and HTML. Content stays as ordinary Python objects,
so reports can share data, figures, citations, validation, and layout policy
without maintaining separate format-specific sources.

## Install

```powershell
pip install oodocs
```

OODocs requires Python 3.11 or later.

Optional extras keep integrations out of the core install:

```powershell
pip install "oodocs[integrations]"  # YAML- and Pydantic-backed collectors
pip install "oodocs[bibtex]"       # third-party BibTeX parser backend
pip install "oodocs[pint]"         # Pint bridge
pip install "oodocs[sympy]"        # SymPy bridge
pip install "oodocs[apidoc]"       # Python API collection
```

`NumberFormat`, `Quantity`, and the other built-in engineering presentation
objects do not require an extra. Install `pint` or `sympy` only when using the
corresponding bridge under `oodocs.integrations`.

## Quick Start

```python
from oodocs import Chapter, Document, Paragraph, Section

document = Document(
    "Example report",
    Chapter(
        "Results",
        Section("Summary", Paragraph("The same source renders everywhere.")),
    ),
)

document.save("artifacts/report.docx")
document.save("artifacts/report.pdf")
document.save("artifacts/report.html")
```

`Document.save(...)` selects the renderer from the extension. Use
`document.save_all("artifacts")` to create the normal DOCX/PDF/HTML bundle, and
`document.validate()` to inspect structured issues before rendering.

## Import Map

Keep common document composition at the top level and import specialized models
from their domain namespace.

| Import from | Use for |
|---|---|
| `oodocs` | `Document`, `DocumentSettings`, `Chapter`, `Section`, `Paragraph`, `Table`, `Figure`, `CoverPage`, `FrontMatter`, `MainMatter`, `BackMatter`, `DescriptionItem`, and `DescriptionList` |
| `oodocs.styles` | `Theme`, reusable styles, numbering policy, reference templates, and locale defaults |
| `oodocs.schema` | `FieldSpec`, `SchemaSpec`, and `SchemaCatalog` |
| `oodocs.clidoc` | `CliApplication`, `CliCommand`, and `CliOption` |
| `oodocs.engineering` | `NumberFormat`, `Quantity`, and other engineering presentation objects |
| `oodocs.evidence` | `EvidenceItem`, `EvidenceReport`, and `EvidenceBundle` |
| `oodocs.suite` | `AssetResolver`, `DocumentSuiteContext`, `DocumentSuiteItem`, `DocumentSuite`, and `DocumentSuiteBundle` |
| `oodocs.integrations.*` | Optional external parsers and collectors, including argparse, BibTeX, Pint, SymPy, pyproject, and GitHub Actions collectors |
| `oodocs.apidoc` | Python API collection and API-reference composition |

Integration APIs are deliberately not re-exported from top-level `oodocs`.
For example, use
`from oodocs.integrations.sympy import equation_from_sympy` and
`from oodocs.integrations.bibtex import parse_bibtex` rather than looking for
tool-specific helpers in the core namespace.

The main reference pages are:

- [cover pages](docs/reference/cover-page.md) and
  [document matter](docs/reference/document-matter.md)
- [references and links](docs/reference/references-and-links.md)
- [description lists](docs/reference/description-list.md),
  [schema documentation](docs/reference/schema-documentation.md), and
  [CLI documentation](docs/reference/cli-documentation.md)
- [math syntax](docs/reference/math-support.md),
  [equation numbering](docs/reference/equation-numbering.md), and
  [quantity formatting](docs/reference/quantity-formatting.md)
- [document suites](docs/reference/document-suite.md),
  [integrations](docs/reference/integrations.md), and
  [evidence reports](docs/reference/evidence-report.md)

## Command Line

```powershell
oodocs build report.py --out artifacts
oodocs validate report.py
```

`build` accepts Python, Markdown, and Jupyter notebook sources. Run
`oodocs --help` and `oodocs <command> --help` for the complete command surface.
Python sources are imported to discover the document object, so build only
trusted Python files and keep command execution behind a `__main__` guard.

## Examples

Runnable examples live under [`examples/`](examples/). Start with
[`usage_guide_example`](examples/usage_guide_example/) for direct composition,
then use the focused
[`config_reference_example`](examples/config_reference_example/),
[`cli_manual_example`](examples/cli_manual_example/),
[`engineering_report_example`](examples/engineering_report_example/),
[`api_objects_example`](examples/api_objects_example/), and
[`document_suite_example`](examples/document_suite_example/) for their
respective namespaces. Evidence bundles are covered by the
[evidence report reference](docs/reference/evidence-report.md). The
[`release_notes_digest`](examples/release_notes_digest/) directory is an
application composition example, not a core release-note API.

From a repository checkout, run an example directly:

```powershell
.\.venv\Scripts\python.exe .\examples\usage_guide_example\main.py --output-dir artifacts/usage-guide
```

## Upgrading from 1.x

Version 1.3 removes `oodocs.adapters`, moves external collectors under
`oodocs.integrations.*`, and replaces `Equation.from_sympy(...)` with
`oodocs.integrations.sympy.equation_from_sympy(...)`. Import schema, CLI,
engineering, evidence, and suite models from their focused namespaces. See the
[v1.3 migration guide](docs/migration-v1.3.md) for the complete mapping.

## Development

```powershell
.\scripts\setup-repo.cmd
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m build
```

See [the testing guide](docs/development/testing.md),
[public API policy](docs/reference/public-api-policy.md), and
[generic feature acceptance](docs/development/generic-feature-acceptance.md)
for contributor contracts.

## Releases

Versions are derived from git tags through `setuptools-scm`. Prepare the
matching `release-notes/v<version>.md`, then create and push the tag with:

```powershell
.\scripts\release.ps1 <version>
```

The release workflow tests the package, checks API documentation coverage,
builds distributions and user-facing documentation, publishes to PyPI through
Trusted Publishing, and attaches the curated artifacts to the GitHub Release.
