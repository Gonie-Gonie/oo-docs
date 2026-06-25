# oodocs

OODocs is an Object-Oriented Documentation Tool: a Python-first authoring toolkit for defining structured documents as ordinary objects and rendering the same source to DOCX, PDF, and HTML.

It is aimed at report, documentation, and manuscript workflows where content already lives near Python data, figures, and scripts. Instead of treating a document as a string template or a markup stream, OODocs keeps the source of record as a typed object tree.

## Object-Oriented Documentation

In OODocs, `Document` owns the artifact, `DocumentSettings` owns document-wide metadata and rendering defaults, and blocks such as `Chapter`, `Section`, `Paragraph`, `Table`, `Figure`, `Box`, and `CitationSource` carry document intent directly in Python.

That object model is the main design constraint:

- the visible outline should match the Python tree
- data-backed tables, generated figures, citations, comments, and cross-references should stay editable objects until render time
- renderer-specific behavior should live behind DOCX, PDF, and HTML renderers rather than leaking into authoring code
- the same source should be useful for writing, validating, reviewing, and releasing a document

## Install

For normal use, install OODocs from PyPI:

```powershell
pip install oodocs
```

To upgrade later:

```powershell
pip install --upgrade oodocs
```

If you need the optional dependencies used by the bundled examples:

```powershell
pip install "oodocs[examples]"
```

If you need YAML-backed repository adapters such as GitHub Actions workflow
summaries:

```powershell
pip install "oodocs[adapters]"
```

If you want to collect Python API objects from modules, packages, source-layout
repositories, and docstrings for API reference documents:

```powershell
pip install "oodocs[apidoc]"
```

The `apidoc` extra installs `griffe` for source-based API collection and
`docstring-parser` for standard Google, NumPy, and Sphinx docstring metadata.

If you want to work from a repository checkout, run the bundled example scripts, or contribute locally:

```powershell
git clone https://github.com/Gonie-Gonie/oo-docs.git
cd oo-docs
pip install -e .
```

If you want the optional example dependencies from a local checkout:

```powershell
pip install -e ".[examples]"
```

For local development and tests:

```powershell
pip install -e ".[dev]"
```

On Windows, the repository also includes a helper that creates `.venv` and installs the development dependencies from the checkout:

```powershell
.\scripts\setup-repo.cmd
```

## Quick Start

The smallest useful document is just a `Document`, one visible heading, one paragraph, and one save call. Start here before splitting code into helper functions:

```python
from oodocs import Chapter, Document, DocumentSettings, Paragraph, Section, bold

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
    settings=DocumentSettings(metadata_author="OODocs"),
)

report.save("artifacts/hello.docx")
report.save("artifacts/hello.pdf")
report.save("artifacts/hello.html")
```

`Document.save(...)` chooses the renderer from the file extension. The explicit `save_docx(...)`, `save_pdf(...)`, and `save_html(...)` methods are still available when you want the output format to be obvious in code. Document metadata and renderer defaults live under `DocumentSettings(...)`, so title matter and theme changes stay in one place.

When you want the normal review bundle in one call:

```python
paths = report.save_all("artifacts")
print(paths["docx"], paths["pdf"], paths["html"])
```

## Command Line

The installed package exposes a `oodocs` command for common build and conversion workflows:

```powershell
oodocs build report.py --out artifacts
oodocs convert README.md --to docx,pdf,html
oodocs convert notebook.ipynb --to pdf
oodocs validate report.py
```

`build` expects a Python file that exposes a `Document` as `document`, `doc`, or `report`, or a zero-argument factory such as `build_document()`. Use `--factory NAME` when the document object or builder has a different name. `convert` imports Markdown and Jupyter notebooks through the same parser APIs available in Python. Both commands validate before rendering by default and stop before writing outputs when validation errors are found.

For CI and release evidence, `oodocs validate --format json` emits a machine-readable validation summary. `oodocs build ... --fail-on-warning` and `oodocs convert ... --fail-on-warning` treat validation warnings as failures, while `--show-warnings` prints warning tables without changing the default success path. Add `--traceback` to any command when debugging needs the full Python stack trace.

For imported Markdown or notebooks, `oodocs convert ... --show-import-warnings` prints diagnostics for lossy source features, and `--strict-import` fails on those diagnostics. Release evidence bundles can be generated with `python -m oodocs.evidence build --out artifacts/evidence`.

## Why Not Just LaTeX?

OODocs is not trying to replace every LaTeX workflow. It is meant for documents where Python already owns the data, plots, citations, or release process and where collaborators may still need DOCX.

Common translations:

- LaTeX `\part` -> `Part(...)` separator pages above chapters
- LaTeX `\section` / `\subsection` -> `Chapter(...)`, `Section(...)`, `Subsection(...)`
- LaTeX `\textbf{...}` / `\emph{...}` / `\texttt{...}` -> `bold(...)`, `italic(...)`, `code(...)`
- LaTeX tag chips / compact inline labels -> `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)`
- Word highlight / strikethrough / manual line break -> `highlight(...)`, `strike(...)`, `line_break()`
- LaTeX `\vspace{...}` / `\hrule` and Notion-style separators -> `VerticalSpace(...)` or `Divider(...)`
- LaTeX `\includegraphics` -> `Figure(path_or_matplotlib_figure, caption=...)`
- LaTeX subfigures -> `SubFigure(...)` children inside a captioned `SubFigureGroup(...)`
- LaTeX `tabular` or copied tables -> `Table(...)` or `Table.from_dataframe(...)`
- LaTeX `\label` / `\ref` -> use `reference(obj)` or `obj.reference()` inside `Paragraph(...)`
- LaTeX `tcolorbox`-style report panels -> editable `Box(..., background_color=..., padding=...)`
- BibTeX-style references -> `CitationLibrary`, `CitationSource.cite(...)`, and `ReferencesPage()`

The main payoff is fewer manual handoffs: a benchmark CSV can become a table, a matplotlib object can become a figure, and the same authored structure can render to DOCX for review, PDF for release, and HTML for lightweight sharing.

## Authoring Model

OODocs tries to keep the source readable:

- create objects with classes such as `Document`, `Part`, `Chapter`, `Section`, `Paragraph`, `Table`, and `Figure`
- apply inline actions with helpers such as `bold(...)`, `italic(...)`, `code(...)`, `tag(...)`, `badge(...)`, `status(...)`, `keyboard(...)`, `Text.from_markup(...)`, `Comment.annotated(...)`, `Footnote.annotated(...)`, and `CitationSource.cite()`
- import existing Markdown with `parse_markdown(...)`, `from_markdown(...)`, or `Document.from_markdown(...)` when release notes, README fragments, or generated Markdown should become editable OODocs objects
- import Jupyter notebooks with `parse_ipynb(...)`, `from_ipynb(...)`, or `Document.from_ipynb(...)` when notebook markdown, code cells, and textual outputs should become OODocs blocks
- collect Python API metadata with `oodocs.apidoc.collect_api(...)` when public classes, functions, methods, parameters, examples, and docstring coverage should become queryable objects before they become document blocks
- keep the document tree explicit so the Python structure matches the final output structure
- move document-wide metadata and theme options into `DocumentSettings(...)` when you want a single place to adjust title matter, cover pages, and renderer defaults

The default behavior is intentionally conventional:

- paragraphs are justified by default
- tables, figures, boxes, and their captions are centered by default
- parts render on their own separator pages and do not reset chapter numbering
- headings are numbered as `1`, `1.1`, `1.1.1`, and so on
- ordered and bullet lists can be customized with direct kwargs such as `indent=...`, `marker_format=...`, and `bullet=...`
- heading numbering can be customized with `HeadingNumbering(...)`
- article-style front matter can be left unnumbered with `Section(..., numbered=False)`

## What To Use When

- Use `Paragraph(...)` for prose. Pass strings and inline helpers directly; you do not need to pre-build `Text(...)` objects for normal writing.
- Use `Paragraph(..., title="Outcome")` for run-in paragraph titles such as LaTeX-style bold labels before body text. Override one paragraph with `title_style=ParagraphTitleStyle(...)`, set a section/chapter scope with `Section(..., paragraph_title_style=...)`, or set the document default with `Theme(paragraph_title_style=...)`.
- Use `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)` for compact inline labels. They share the `InlineChip(...)` model; DOCX emits small inline images, while PDF and HTML keep styled text.
- Use `highlight(...)`, `strike(...)`, and `line_break()` for Word-style emphasis and manual line breaks inside one paragraph.
- Use `Theme(paragraph_alignment=...)` for the document-wide paragraph default, and direct paragraph kwargs such as `alignment=...` when one paragraph should override it.
- Use `Paragraph(left_indent=..., right_indent=..., first_line_indent=..., unit=...)` when you need Word-like first-line or hanging indents. If `unit` is omitted, indent values follow `DocumentSettings(unit=...)`.
- Use `subscript(...)`, `superscript(...)`, and `prescript(...)` for ordinary prose. Use `Math(...)` or `Equation(...)` for lightweight LaTeX-style math, including ordinary `x^2` / `x_0` scripts and front scripts such as `\prescript{14}{6}{C}`.
- Use `Part(...)` for book-like divisions above chapters; each part gets a separator page, while chapter numbers continue across parts by default.
- Use `Chapter(...)`, `Section(...)`, `Subsection(...)`, and `Subsubsection(...)` for the visible outline. Their nesting in Python should match how you expect the final document to read.
- Use `Document.add(...)`, `Section.add(...)`, `Box.add(...)`, and `MultiColumn.add(...)` when a longer report is easier to assemble step by step. Matching `extend(...)` methods accept iterables and use the same coercion rules as constructors.
- Use `reference(obj)` or `obj.reference()` for cross-references to captioned media, headings, equations, paragraphs, code blocks, and boxes. Passing the raw object inside `Paragraph(...)` is rejected so insertion and citation are not confused.
- Use `Definition(...)`, `Lemma(...)`, `Proposition(...)`, `Theorem(...)`, `Corollary(...)`, `Example(...)`, `Remark(...)`, `Assumption(...)`, `Axiom(...)`, `Claim(...)`, and `Conjecture(...)` for theorem-like blocks that share a document-wide counter; `Proof(...)` is unnumbered by default. Use `countable_kind("Exercise", counter="exercise")` to create custom countable block classes without subclassing, or pass `counter="theorem"` when a custom block should join the same sequence.
- Use `Table(...)` for small authored tables, `Table.from_records(...)` or `Table.from_mapping(...)` for ordinary Python data, `Table.from_csv(...)` or `Table.from_tsv(...)` for delimited files, and `Table.from_dataframe(...)` when the data already lives in pandas.
- Use `TableStyle.plain()`, `TableStyle.compact()`, or `TableStyle.evidence()` when several tables should share a preset without repeating style kwargs.
- Use `TableCell(horizontal_alignment=..., vertical_alignment=...)` or table-wide `Table(..., cell_horizontal_alignment=..., cell_vertical_alignment=...)` when a table needs Word-like cell alignment. Use dictionaries in `row_styles`, `header_row_styles`, or `column_styles` when rows or columns need background color, text color, bold, or italic formatting.
- Use `Table(split=True)` when a table should render in source order and may break across pages. Leave `split=False` when the table should stay together when possible; very long tables are automatically rendered as split repeated-header tables.
- Use `Figure(...)` for image files or `savefig()`-compatible Python figure objects. Use `Figure.from_bytes(...)` or `Figure.from_buffer(...)` when image bytes are already in memory.
- Use `SubFigureGroup(SubFigure(...), SubFigure(...), caption=...)` when related images should share one figure number and expose `(a)`, `(b)`, and similar subfigure references.
- Use `Theme(table_caption_label=..., table_reference_label=..., figure_caption_label=..., figure_reference_label=...)` when captions and in-text references should use different labels such as `Figure`, `Fig.`, or localized terms.
- Use `Theme(citation_format="apa", reference_format="apa")` when inline citations and the generated references page should follow an author-year style. Numeric citation output remains the default.
- Use advanced `placement=...` hints on tables and figures only when needed. Supported values include `here`, `tbp`/`float`, `top`, `bottom`, and `page`.
- Use `Box(...)` for callouts, evidence panels, and tcolorbox-like report sections that should stay editable in Word.
- Use `Shape(...)`, `TextBox(...)`, and `ImageBox(...)` with `DocumentSettings(page_items=[...])` for page-positioned overlays that do not move the body text. Use `placement="inline"` when the same objects should sit in the text flow like Word's inline drawing mode.
- Use `DocumentSettings(...)` for document-wide choices: authors, subtitle, page size, margins, units, page overlays, and theme defaults.
- Use `document.validate()` when you want a structured preflight check before rendering. The returned `ValidationResult` prints as a compact table, can be serialized with `to_dict()` or `to_json()`, and each issue records whether it affects Word, PDF, HTML, or all outputs. `save(...)`, `save_docx(...)`, `save_pdf(...)`, `save_html(...)`, and `save_all(...)` validate before rendering by default and stop before writing when errors are found.
- Use `Document.from_markdown(...)` when a Markdown file should become a full document. Use `parse_markdown(...)` when you want a list of blocks that can be inserted, reordered, wrapped in sections, or combined with tables and figures.
- Use `parse_markdown(..., diagnostics=True)` or `parse_markdown_file(..., diagnostics=True)` when you need an `ImportResult` with import issues. Use `import_policy="strict"` when lossy Markdown features such as remote images should fail instead of being converted conservatively.
- Use `Document.from_markdown(..., numbered=False, toc=True)` when imported headings should keep their source titles without generated numbers but still appear in a generated table of contents.
- Use `heading_level_shift=1` or `heading_level_shift=-1` with `Document.from_markdown(...)` or `parse_markdown(...)` when imported Markdown should be demoted or promoted before it is inserted into a larger outline. Use `shift_heading_levels(...)` when already-created `Chapter(...)`/`Section(...)` objects need the same adjustment; paragraphs and other non-heading blocks stay unchanged, and shifts beyond the supported heading range fail.
- Use `Document.from_ipynb(...)` when a notebook should become a full document. Use `parse_ipynb(...)` when notebook cells should be merged into a larger report; markdown cells become normal document structure, code cells become `CodeBlock(...)`, and textual outputs can be included or filtered. Use `NotebookImportOptions(...)` for tag filtering, output truncation, image captions, and error-output policy.
- Use `oodocs.adapters` when repository files should become document objects: `section_from_pyproject(...)`, `section_from_github_workflow(...)`, `section_from_manifest(...)`, and `build_release_evidence_document(...)` are designed for release and audit reports.
- Use `oodocs.apidoc` when Python modules should become API documentation material. `collect_api(...)` returns an `ApiPackage`, not a pre-rendered string, so user code can query and compose the parsed API objects:

```python
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
# A repository checkout with src/, setuptools, hatch, Poetry, PDM, or Flit layout
# metadata also works. When the apidoc extra is installed, collector="griffe"
# reads source without importing the target repo.
# api = collect_api(".", public_policy="__all__", collector="griffe")
# ApiDocstringParser.auto() can be passed as docstring_style when one parser
# configuration should be reused across collection and coverage steps.
# Custom parser names can be loaded from repo modules through
# docstring-parser-modules in pyproject.toml or --docstring-parser-module.
# For curated public boundaries, pass an ApiPublicPolicy object instead of a
# string and reuse it across collect/check/build steps.
# ApiCollectConfig.from_pyproject(".") can load [tool.oodocs.apidoc], and
# ApiCollectConfig.write_json("apidoc-config.json") stores the same policy so
# CLI commands can reuse it with --config.
classes = api.select(kind="class", module_prefix="oodocs.components")
functions = api.select(kind="function")

doc = Document(
    "Selected API Notes",
    Chapter(
        "Important Classes",
        Paragraph("This chapter is assembled from parsed API objects."),
        *[obj.to_section(level=2, profile="manual") for obj in classes[:5]],
    ),
    Chapter(
        "Function Index",
        api.to_summary_table(functions, caption="Selected public functions."),
    ),
)
```

- Use `document.save_all("artifacts")` when a workflow normally needs DOCX, PDF, and HTML together.

## Features

- DOCX, PDF, and HTML rendering from the same document tree
- Markdown and GitHub Flavored Markdown import for headings, paragraphs, lists, task-list markers, block quotes, fenced code, thematic breaks, tables, local images, links, autolinks, emphasis, inline code, strikethrough, and optional import diagnostics
- Jupyter notebook import for markdown cells, code cells, raw cells, textual stream/result/error outputs, tag filtering, output truncation, image captions, and optional import diagnostics
- block objects for paragraphs, lists, code blocks, equations, boxes, tables, figures, and generated pages
- Pygments-backed syntax highlighting for code blocks across Python, JavaScript, SQL, YAML, shell, and other supported languages
- editable report panels with `Box(...)` kwargs for width, alignment, title color, and per-side padding
- portable comments and footnotes that stay stable across DOCX, PDF, and HTML
- footnotes target page-bottom placement by default when the renderer supports it; `Theme(footnote_placement="document")` keeps the collected-notes pattern
- captioned tables and figures with automatic numbering and in-text references
- independent document-level labels for table/figure captions and in-text references
- table support for `TableCell(...)`, `rowspan`, `colspan`, banded rows, ordinary Python records, CSV/TSV files, dataframe-like inputs, and cell/row/column styling
- automatic split-table rendering for long tables, with repeated headers where renderers support them
- advanced table and figure placement hints for here/float/top/bottom/page-style workflows
- figure support for stored image files, in-memory bytes, buffers, and `savefig()`-compatible Python objects
- subfigure groups with automatic child labels and references such as `Figure 1(a)`
- page-positioned `Shape.rect(...)`, `Shape.ellipse(...)`, `Shape.line(...)`, `TextBox(...)`, and `ImageBox(...)` objects with anchors to the page, the margin box, or an earlier named shape
- inline drawing placement for `Shape(...)`, `TextBox(...)`, and `ImageBox(...)`, similar to using an image directly in the document flow
- inline chips through `InlineChip(...)`, `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)`
- bibliography support through `CitationSource`, `CitationLibrary`, direct citation objects, BibTeX import, and configurable inline/reference formats such as APA
- optional title matter such as subtitle, structured `Author(...)` metadata, `AuthorLayout(...)`, affiliations, and a cover page
- inline hyperlinks and heading/caption anchors for cross-references
- release evidence adapters for pyproject metadata, GitHub Actions workflows, JSON manifests, CSV/TSV evidence tables, checksums, and generated evidence reports
- API object collection, docstring coverage checks, API snapshots, API diffs, and composable API-reference sections through `oodocs.apidoc`

## Example Scripts

The repository includes five standalone example directories:

- `examples/usage_guide_example/`
- `examples/journal_paper_example/`
- `examples/native_benchmark_report/`
- `examples/release_notes_digest/`
- `examples/api_objects_example/`

Run them directly from the repository checkout:

```powershell
.\.venv\Scripts\python.exe .\examples\usage_guide_example\main.py
.\.venv\Scripts\python.exe .\examples\journal_paper_example\main.py
.\.venv\Scripts\python.exe .\examples\native_benchmark_report\main.py
.\.venv\Scripts\python.exe .\examples\release_notes_digest\main.py
.\.venv\Scripts\python.exe .\examples\api_objects_example\main.py . --config pyproject.toml
```

The full package API reference can also be rendered directly from the
repository-local `apidoc` config:

```powershell
.\.venv\Scripts\python.exe -m oodocs apidoc build . --config pyproject.toml
```

Direct example scripts print slow major render steps. Imported build functions stay quiet by default; pass `verbose=True` when you want the same progress messages.

What they show:

- `usage_guide_example` is a detailed guide that keeps almost all assembly in one `main.py` so the source stays easy to read; it now covers the core authoring model, validation, CLI workflows, theorem-like countable blocks, layout controls, imports, presets, and renderer differences
- the usage guide includes Markdown and notebook import patterns that bring existing authored files into normal OODocs document objects
- `journal_paper_example` shows a longer manuscript-style workflow with article-style sections, unnumbered abstract/highlights/acknowledgements, CSV-backed tables, and matplotlib figures inserted directly from Python objects
- `native_benchmark_report` shows a compact Python-native workflow where a script generates an in-memory workload, benchmarks several callables, turns structured result objects into tables and prose, and exports one report bundle
- `release_notes_digest` collects `release-notes/*.md`, sorts semantic versions from filenames, imports the Markdown bodies, and builds a release-note document with a version-management table and runbook
- `api_objects_example` collects the OODocs API, renders a full package API reference as DOCX/PDF/HTML, inserts selected API object sections and summary tables into a separate composable document, and writes API JSON plus coverage JSON/CSV sidecars for release evidence

By default they write outputs under:

- `artifacts/usage-guide/`
- `artifacts/journal-paper/`
- `artifacts/native-benchmark-report/`
- `artifacts/release-notes/`
- `artifacts/api-objects-example/`
- `artifacts/api/`

The main exported filenames are:

- `artifacts/usage-guide/oodocs-user-guide.pdf`
- `artifacts/journal-paper/oodocs-development-philosophy.pdf`
- `artifacts/native-benchmark-report/native-python-benchmark.pdf`
- `artifacts/release-notes/oodocs-release-notes.pdf`
- `artifacts/api-objects-example/oodocs-api-objects.pdf`
- `artifacts/api-objects-example/oodocs-full-api-reference.docx`
- `artifacts/api-objects-example/oodocs-full-api-reference.pdf`
- `artifacts/api-objects-example/oodocs-full-api-reference.html`
- `artifacts/api/oodocs-api.docx`
- `artifacts/api/oodocs-api.pdf`
- `artifacts/api/oodocs-api.html`
- `artifacts/api/oodocs-api.json`
- `artifacts/api/oodocs-api-coverage.json`
- `artifacts/api/oodocs-api-coverage.csv`

## Project Layout

The package is organized by responsibility:

- `src/oodocs/document.py` for the root `Document`
- `src/oodocs/settings.py` for `DocumentSettings` plus grouped configuration exports
- `src/oodocs/components/` for the concrete authoring model (`base.py`, `blocks.py`, `equations.py`, `generated.py`, `inline.py`, `markup.py`, `media.py`, `people.py`, `positioning.py`, and `references.py`)
- `src/oodocs/importers/` for adapters that convert external formats such as Markdown into OODocs objects
- `src/oodocs/adapters/` and `src/oodocs/evidence.py` for repository artefact adapters and release evidence bundles
- `src/oodocs/layout/` for low-level theme and indexing support
- `src/oodocs/renderers/docx.py`, `src/oodocs/renderers/pdf.py`, and `src/oodocs/renderers/html.py` for format-specific layout

## Development

Assuming Python 3.11 or newer is installed:

```powershell
.\scripts\setup-repo.cmd
```

Or:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-repo.ps1
```

That setup script creates `.venv` and installs `.[dev]`.
If dependency metadata changes later, rerun the setup script or refresh the environment with:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Build distribution artifacts:

```powershell
.\.venv\Scripts\python.exe -m build
```

## Releases

OODocs versions are derived from git tags through `setuptools-scm`.

Create and push a release tag like this:

```powershell
.\scripts\release.ps1 1.0.4
```

That pushes `v1.0.4`, and the GitHub release workflow runs the test suite, enforces API documentation coverage with `oodocs apidoc check`, builds the wheel/sdist artifacts, renders the release documents, builds the release evidence bundle, attaches the curated documents and API evidence sidecars to the matching GitHub Release, and uploads the Python distributions to PyPI.

If you want a curated release body instead of GitHub's generated notes, add a file such as `release-notes/v1.0.4.md` before pushing the tag.

The `examples/release_notes_digest/` script demonstrates the same convention as a document workflow: it scans the semantic-versioned Markdown files under `release-notes/`, builds an index, includes the version-management rules, and imports each release body into one DOCX/PDF/HTML bundle.

PyPI publishing uses Trusted Publishing through the `pypi` GitHub environment. The PyPI project or pending publisher must trust repository `Gonie-Gonie/oo-docs`, workflow `.github/workflows/release.yml`, and environment `pypi`.
