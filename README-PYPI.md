# oodocs

OODocs is an Object-Oriented Documentation Tool: a Python-first toolkit for
building structured documents as ordinary Python objects and rendering the same
source to DOCX, PDF, and HTML.

It is useful when reports, manuals, API references, manuscripts, or release
documents already live near Python data, figures, and scripts. Instead of
treating a document as a string template, OODocs keeps the source of record as a
typed object tree.

## Install

```bash
pip install oodocs
```

OODocs requires Python 3.11 or later.

Optional extras are available for focused workflows:

```bash
pip install "oodocs[examples]"
pip install "oodocs[integrations]"
pip install "oodocs[bibtex]"
pip install "oodocs[pint]"
pip install "oodocs[sympy]"
pip install "oodocs[apidoc]"
```

- `examples` installs dependencies used by the bundled example scripts, such as
  matplotlib and pandas.
- `integrations` installs PyYAML and Pydantic support for their optional
  collectors.
- `bibtex` installs the optional `bibtexparser` backend; the built-in parser
  remains available without it.
- `pint` and `sympy` install only their respective integration bridges.
- `apidoc` installs API collection and docstring parsing dependencies.

Core engineering presentation objects such as `NumberFormat` and `Quantity`
need no optional dependency.

## Quick Start

```python
from oodocs import Chapter, Document, DocumentMetadata, DocumentSettings, Paragraph, Section, bold

report = Document(
    "Hello oodocs",
    Chapter(
        "Getting Started",
        Section(
            "Overview",
            Paragraph(
                "This document was defined with ",
                bold("Python objects"),
                ".",
            ),
        ),
    ),
    settings=DocumentSettings(metadata=DocumentMetadata(author="OODocs")),
)

report.save("artifacts/hello.docx")
report.save("artifacts/hello.pdf")
report.save("artifacts/hello.html")
```

`Document.save(...)` chooses the renderer from the file extension. Use
`save_all(...)` when a workflow normally needs DOCX, PDF, and HTML together:

```python
outputs = report.save_all("artifacts")
print(outputs["docx"], outputs["pdf"], outputs["html"])
```

## Command Line

The package installs an `oodocs` command for common build and validation tasks:

```bash
oodocs build report.py --out artifacts
oodocs build README.md --outputs docx,pdf,html --out artifacts
oodocs build notebook.ipynb --outputs pdf --out artifacts
oodocs validate report.py
```

Python sources can expose a `Document` as `document`, `doc`, or `report`, or a
zero-argument factory such as `build_document()`. Markdown and notebook sources
are imported through the same parser APIs available from Python.
Because a Python source is imported during discovery, build only trusted Python
files and keep command execution behind an `if __name__ == "__main__"` guard.

## What You Can Build

- DOCX, PDF, and HTML documents from one Python object tree
- document-level page layout for page size, margins, and portrait/landscape
  orientation
- authored prose, headings, lists, equations, code blocks, boxes, tables, and
  figures
- captioned tables and figures with automatic numbering and cross-references
- explicit cover/front/main/back matter plus plain object links for unnumbered
  targets
- description lists, schema and CLI reference models, per-line equation
  references, quantities, and multi-document suites
- report panels and reusable visual styles that stay editable in Word
- document comments, footnotes, hyperlinks, citations, and generated references
- Markdown and Jupyter notebook imports that become editable OODocs blocks
- API reference material from Python packages, modules, source trees, and
  docstrings through `oodocs.apidoc`
- release and audit documents from generic metadata models, explicit
  `oodocs.integrations`, and caller-configured `oodocs.evidence` reports

## API Documentation Workflows

Install the `apidoc` extra to collect public Python API objects and render them
as ordinary OODocs content:

```python
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
classes = api.select_objects(kind="class", module_prefix="oodocs.components")

doc = Document(
    "Selected API Notes",
    Chapter(
        "Important Classes",
        Paragraph("This chapter is assembled from parsed API objects."),
        *[obj.to_section(level=2, presentation="manual") for obj in classes[:5]],
    ),
)

doc.save_all("artifacts/api-notes")
```

Repository-level API reference builds can also be configured in `pyproject.toml`
and rendered with `ApiHelpBookConfig.from_pyproject(".").save_all(".")`.

## Upgrading from 1.x

Version 2.0 removes `oodocs.adapters`; import external collectors from
`oodocs.integrations.*`. Replace `Equation.from_sympy(...)` with
`oodocs.integrations.sympy.equation_from_sympy(...)`, and import schema, CLI,
engineering, evidence, and suite models from their focused namespaces. See the
[v2 migration guide](https://github.com/Gonie-Gonie/oo-docs/blob/main/docs/migration-v2.md).

## Links

- Repository: https://github.com/Gonie-Gonie/oo-docs
- Issues: https://github.com/Gonie-Gonie/oo-docs/issues
- License: MIT
