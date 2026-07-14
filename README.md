# oodocs

OODocs is a Python-first toolkit for building one structured document tree and
rendering it to DOCX, PDF, and HTML. Content stays as ordinary Python objects,
so reports can share data, figures, citations, validation, and layout policy
without maintaining separate format-specific sources.

## Install

```powershell
pip install oodocs
```

Optional extras keep integrations out of the core install:

```powershell
pip install "oodocs[integrations]"  # YAML-backed collectors
pip install "oodocs[bibtex]"       # third-party BibTeX parser backend
pip install "oodocs[apidoc]"       # Python API collection
```

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
| `oodocs.integrations.*` | Optional external parsers and collectors, including argparse, BibTeX, Pint, SymPy, pyproject, and GitHub Actions adapters |
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

## Examples

Runnable examples live under [`examples/`](examples/). Start with
[`usage_guide_example`](examples/usage_guide_example/) for direct composition,
then use the focused schema, CLI, engineering, evidence, API-documentation, and
document-suite examples for their respective namespaces. The
[`release_notes_digest`](examples/release_notes_digest/) directory is an
application composition example, not a core release-note API.

From a repository checkout, run an example directly:

```powershell
.\.venv\Scripts\python.exe .\examples\usage_guide_example\main.py --output-dir artifacts/usage-guide
```

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
