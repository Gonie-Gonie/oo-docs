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

`Document.save(...)` chooses the renderer from the file extension. The explicit `save_docx(...)`, `save_pdf(...)`, and `save_html(...)` methods are still available when you want the output format to be obvious in code. Document metadata and renderer defaults live under `DocumentSettings(...)`, so title matter and theme changes stay in one place.

When you want the normal review bundle in one call:

```python
outputs = report.save_all("artifacts")
print(outputs["docx"], outputs["pdf"], outputs["html"])
```

## Command Line

The installed package exposes a `oodocs` command for common build and validation workflows:

```powershell
oodocs build report.py --out artifacts
oodocs build README.md --outputs docx,pdf,html --out artifacts
oodocs build notebook.ipynb --outputs pdf --out artifacts
oodocs validate report.py
```

`build` accepts Python, Markdown, and Jupyter notebook sources. Python sources expose a `Document` as `document`, `doc`, or `report`, or a zero-argument factory such as `build_document()`. Use `--document-factory NAME` when the document object or builder has a different name. Markdown and notebook sources import through the same parser APIs available in Python. Builds validate before rendering by default and stop before writing outputs when validation errors are found.

For CI and release evidence, `oodocs validate --report-format json` emits a machine-readable validation summary. `oodocs build ... --fail-on-warning` treats validation warnings as failures, while `--show-warnings` prints warning tables without changing the default success path. Add `--traceback` to any command when debugging needs the full Python stack trace.

For imported Markdown or notebooks, `oodocs build ... --show-import-warnings` prints diagnostics for lossy source features, and `--fail-on-import-warning` fails on those diagnostics. Release evidence bundles can be generated with `python -m oodocs.evidence build --out artifacts/evidence`.

## Why Not Just LaTeX?

OODocs is not trying to replace every LaTeX workflow. It is meant for documents where Python already owns the data, plots, citations, or release process and where collaborators may still need DOCX.

Common translations:

- LaTeX `\part` -> `Part(...)` separator pages above chapters
- LaTeX `\appendix` -> `Appendix(Chapter(...), ...)` from `oodocs.structure` with child chapters numbered `A`, `B`, `C`
- LaTeX `\section` / `\subsection` -> `Chapter(...)`, `Section(...)`, `Subsection(...)`
- LaTeX `\textbf{...}` / `\emph{...}` / `\texttt{...}` -> `bold(...)`, `italic(...)`, `inline_code(...)`
- LaTeX tag chips / compact inline labels -> `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)`
- Word highlight / strikethrough / manual line break -> `highlight(...)`, `strikethrough(...)`, `line_break()`
- LaTeX `\vspace{...}` / `\hrule` and Notion-style separators -> `VerticalSpace(...)` or `Divider(...)`
- LaTeX `\includegraphics` -> `Figure(path_or_matplotlib_figure, caption=...)`, with optional `CropBox(...)` from `oodocs.media`, `rotation=...`, and `alt_text=...`
- LaTeX subfigures -> `SubFigure(...)` children inside a captioned `SubFigureGroup(...)`
- LaTeX subtables -> `SubTable(Table(...), caption=...)` children from `oodocs.media` inside a captioned `SubTableGroup(...)`
- LaTeX `pdfpages` -> `PdfPages("appendix.pdf", pages=[1, 3])` from `oodocs.pdf` for PDF-page insertion, with DOCX/HTML placeholder fallbacks
- LaTeX `listings` / `minted` -> `CodeBlock(..., caption=..., line_numbers=True, highlight_lines={...})` or `CodeBlock.from_file(...)`
- LaTeX `algorithm` / `algorithmicx` -> `Algorithm(..., inputs=..., outputs=..., steps=...)` from `oodocs.engineering` with automatic numbering and references
- LaTeX `tabular` or copied tables -> `Table(...)` or `Table.from_dataframe(...)`
- LaTeX `booktabs` -> `Table(..., style="booktabs")` or `TableStyle.booktabs()`
- LaTeX `tabularx` / `array` column specs -> `ColumnSpec(width=...)` and `ColumnSpec(flex=...)` from `oodocs.media`, plus `Table.excerpt(...)` and a CSV sidecar for very wide matrices
- LaTeX `multirow` / `multicolumn` -> `TableCell(rowspan=...)`, `TableCell(colspan=...)`, or `Table.grouped_headers(...)`
- LaTeX `\label` / `\ref` -> use `ref(obj)` or `obj.reference()` inside `Paragraph(...)`
- LaTeX `\url{...}` / `\href{...}{...}` -> use `url(...)` for visible URLs and `link(...)` for named links
- LaTeX `enumitem` list options -> use `BulletList(...)`, `NumberedList(start=...)`, `NumberedList(resume_from=...)`, and `ListStyle(...)`
- LaTeX `glossaries` / `acronym` / `nomencl` -> use `Glossary` and `ListOfGlossaryTerms` from `oodocs.glossary`, plus `Nomenclature`
- LaTeX `tcolorbox` / `mdframed` report panels -> editable `Box(..., icon=..., title_position="side")` or `CalloutBox(..., variant="danger", icon="!")`
- BibTeX-style references -> `CitationLibrary`, `CitationSource.cite(...)`, and `ListOfReferences()`

The main payoff is fewer manual handoffs: a benchmark CSV can become a table, a matplotlib object can become a figure, and the same authored structure can render to DOCX for review, PDF for release, and HTML for lightweight sharing.

## Authoring Model

OODocs tries to keep the source readable:

- create objects with classes such as `Document`, `Part`, `Chapter`, `Section`, `Paragraph`, `Table`, and `Figure`
- apply inline actions with helpers such as `bold(...)`, `italic(...)`, `inline_code(...)`, `tag(...)`, `badge(...)`, `status(...)`, `keyboard(...)`, `url(...)`, `Text.from_markup(...)`, `Comment.annotated(...)`, review helpers imported from `oodocs.review`, `Footnote.annotated(...)`, and `CitationSource.cite()`
- import existing Markdown with `Document.from_markdown(...)` or `parse_markdown(...)` from `oodocs.importers` when release notes, README fragments, or generated Markdown should become editable OODocs objects
- import Jupyter notebooks with `Document.from_notebook(...)` or `parse_notebook(...)` from `oodocs.importers` when notebook markdown, code cells, and textual outputs should become OODocs blocks
- collect Python API metadata with `oodocs.apidoc.collect_api(...)` when public classes, functions, methods, parameters, examples, and docstring coverage should become queryable objects before they become document blocks
- keep the document tree explicit so the Python structure matches the final output structure
- move document-wide metadata and theme options into `DocumentSettings(...)` when you want a single place to adjust title matter, cover pages, and renderer defaults

The default behavior is intentionally conventional:

- paragraphs are justified by default
- tables, figures, boxes, and their captions are centered by default
- parts render on their own separator pages and do not reset chapter numbering
- appendices render on a separator page and switch child chapter numbering to `A`, `B`, `C`
- headings are numbered as `1`, `1.1`, `1.1.1`, and so on
- ordered and bullet lists can be customized with direct kwargs such as `indent=...`, `marker=CounterStyle(...)`, `marker_gap=...`, `item_spacing=...`, `block_spacing=...`, `start=...`, and `resume_from=...`
- heading numbering can be customized with `HeadingNumbering(...)`
- heading typography, spacing, alignment, and per-level counter formats can be customized with `HeadingStyle(...)`
- article-style front matter can be left unnumbered with `Section(..., numbered=False)`

## What To Use When

- Use `Paragraph(...)` for prose. Pass strings and inline helpers directly; you do not need to pre-build `Text(...)` objects for normal writing.
- Use `Paragraph(..., title="Outcome")` for run-in paragraph titles such as LaTeX-style bold labels before body text. Override one paragraph with `title_style=RunInTitleStyle(...)`, set a section/chapter scope with `Section(..., run_in_title_style=...)`, or set the document default with `Theme(blocks=BlockDefaults(run_in_title_style=...))`.
- Use `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)` for compact inline labels. They share the `InlineChip(...)` model; DOCX emits small inline images, while PDF and HTML keep styled text.
- Use `highlight(...)`, `strikethrough(...)`, and `line_break()` for Word-style emphasis and manual line breaks inside one paragraph.
- Use `link(target, label)` for named external links and `url(target, breakable=True)` when the visible text is the URL itself. Long raw URL labels emit a validation warning because DOCX, PDF, and HTML wrap them differently.
- Use `Theme(blocks=BlockDefaults(paragraph_text_alignment=...))` for the document-wide paragraph default, and direct paragraph kwargs such as `text_alignment=...` when one paragraph should override it.
- Use `Paragraph(left_indent=..., right_indent=..., first_line_indent=..., unit=...)` when you need Word-like first-line or hanging indents. If `unit` is omitted, indent values follow `DocumentSettings(unit=...)`.
- Use `subscript(...)`, `superscript(...)`, `prescript(...)`, and `inline_math(...)` for ordinary prose. Use `Equation(...)`, `Equation.aligned(...)`, and `Equation.cases(...)` for displayed expressions, including ordinary `x^2` / `x_0` scripts, aligned derivations, piecewise cases, and front scripts such as `\prescript{14}{6}{C}`. Pass `numbered=False` when a displayed equation should not consume an equation number.
- Import `chemical_formula(...)`, `ChemicalFormula(...)`, and `ReactionEquation(...)` from `oodocs.chemistry` for mhchem-style inline chemistry and displayed reactions with automatic references.
- Use `Part(...)` for book-like divisions above chapters; each part gets a separator page, while chapter numbers continue across parts by default.
- Import `Appendix(...)` from `oodocs.structure` for appendix material; child chapters are numbered `A`, `B`, `C`, nested headings become `A.1`, `A.2`, and the appendix separator can appear in the table of contents.
- Use `Chapter(...)`, `Section(...)`, `Subsection(...)`, and `SubSubsection(...)` for the visible outline. Their nesting in Python should match how you expect the final document to read.
- Use `Theme(blocks=BlockDefaults(heading_styles={level: HeadingStyle(...)}))` for document-wide heading styling, or `Section(..., heading_style=HeadingStyle(...))` when one heading needs a local override.
- Use `TableOfContents(scope="chapter")`, `ListOfTables(scope="section")`, `ListOfFigures(scope="part")`, or `ListOfAlgorithms(scope="chapter")` for mini contents and local generated lists. Import `ListOfAlgorithms` from `oodocs.generated`; the default `scope="document"` preserves whole-document lists.
- Use `Document.add(...)`, `Section.add(...)`, `Box.add(...)`, and `MultiColumn.add(...)` when a longer report is easier to assemble step by step. Matching `extend(...)` methods accept iterables and use the same coercion rules as constructors.
- Use `ref(obj)` or `obj.reference()` for cross-references to captioned media, headings, equations, paragraphs, code blocks, and boxes. Use top-level `refs([a, b])` for plural object references and `ref_range(a, b)` for ranges. Import `ReferenceFormat`, `Ref`, `reference`, `paren_ref`, and `page_ref` from `oodocs.references` when custom reference formatting, capitalized labels, explicit helper naming, parenthesized references, or page-aware reference requests are needed. Passing the raw object inside `Paragraph(...)` is rejected so insertion and citation are not confused.
- Import theorem-like blocks such as `Definition(...)`, `Lemma(...)`, `Theorem(...)`, `Proof(...)`, and `create_countable_block_type(...)` from `oodocs.structure`; they share a document-wide counter unless configured otherwise.
- Use `Table(...)` for small authored tables, `Table.from_records(...)` or `Table.from_mapping(...)` for ordinary Python data, `Table.from_csv(...)` or `Table.from_tsv(...)` for delimited files, and `Table.from_dataframe(...)` when the data already lives in pandas.
- Use named table styles such as `Table(..., style="plain")`, `Table(..., style="compact")`, `Table(..., style="evidence")`, or `Table(..., style="booktabs")` when several tables should share a preset without repeating style kwargs. Pass a concrete `TableStyle(...)` only for one-off local styling or when registering a custom stylesheet entry.
- Import `ColumnSpec(...)` from `oodocs.media` for fixed columns and `tabularx`-style flex columns. In `Table.from_records(...)`, `ColumnSpec(key=..., header=..., visible=False)` can also choose, rename, or hide record fields.
- Use `TableCell(text_alignment=..., vertical_alignment=...)` or table-wide `Table(..., cell_text_alignment=..., cell_vertical_alignment=...)` when a table needs Word-like cell alignment. Use dictionaries in `row_styles`, `header_row_styles`, or `column_styles` when rows or columns need background color, text color, bold, or italic formatting.
- Use `TableCell(colspan=...)` and `TableCell(rowspan=...)` for one-off merged cells. Use `Table.grouped_headers(groups=[("Geometry", 2), ...], columns=[...], rows=[...])` when a table needs a common grouped header row without manually building every spanning cell.
- Use `Table(split=True, continuation_label="continued")` when a table should render in source order and may break across pages. Leave `split=False` when the table should stay together when possible; very long tables are automatically rendered as split repeated-header tables.
- Use `Figure(...)` for image files or `savefig()`-compatible Python figure objects. Use `Figure.from_bytes(...)` or `Figure.from_buffer(...)` when image bytes are already in memory. Add `crop=CropBox(...)` from `oodocs.media`, `rotation=...`, and `alt_text=...` for LaTeX `graphicx`-style image transforms and accessible output text.
- Import `PdfPages(...)` from `oodocs.pdf` when existing PDF pages should be inserted into PDF output. DOCX and HTML render a link-style placeholder because editable page import is renderer-specific.
- Use `SubFigureGroup(SubFigure(...), SubFigure(...), caption=...)` when related images should share one figure number and expose `(a)`, `(b)`, and similar subfigure references.
- Import `SubTable(...)` and `SubTableGroup(...)` from `oodocs.media` when related tables should share one table number and expose references such as `Table 1(a)`.
- Use `CodeBlock(..., caption=..., line_numbers=True, highlight_lines={...})` for numbered listings, and `CodeBlock.from_file("example.py", caption=...)` when the code should be included from a source file.
- Import `Algorithm(...)` from `oodocs.engineering` for numbered pseudocode blocks. Pass `code=...` or `body_style="code"` when the algorithm should render more like a code listing.
- Use `Theme(captions=CaptionDefaults(table_caption_label=..., table_reference_label=..., figure_caption_label=..., figure_reference_label=...))` when captions and in-text references should use different labels such as `Figure`, `Fig.`, or localized terms.
- Use `Theme.from_locale("ko-KR")` or `Theme(locale=LocaleDefaults.from_locale("ko-KR"))` for a bundled document language: localized captions, generated page titles, glossary labels, reference-list title, date formatting with `theme.format_date(...)`, HTML `lang`, and PDF font guidance via `theme.pdf_font_fallback_guide()`.
- Use `CitationLibrary.from_bibtex_file("refs.bib")` for BibTeX input, and `Theme(citations=CitationDefaults(citation_style="apa", reference_style="apa", reference_sort="author"))` when inline citations and the generated references page should follow an author-year style. Numeric citation output and citation-order references remain the default; pass `ListOfReferences(include_uncited=True)` when the generated bibliography should include uncited library entries.
- Import `Glossary(...)` and `ListOfGlossaryTerms(...)` from `oodocs.glossary` for collected terminology. `glossary.use("API")` expands acronyms on first use, and `ListOfGlossaryTerms(glossary)` renders the generated glossary table.
- Use `footnote("term", "note", stream="symbols")` with `Theme(footnotes=FootnoteDefaults(stream_styles={"symbols": FootnoteStyle.symbol()}))` when notes need independent numeric or symbol streams. Plain default footnotes still use native DOCX page footnotes; custom streams fall back to the generated notes page in DOCX.
- Import `todo(...)`, `margin_note(...)`, and `MarginNote(...)` from `oodocs.review` for review tasks and side notes that should stay next to the source prose. `MarginNote(...)` renders as an HTML side note, while DOCX and PDF keep the note through comment-style fallback output.
- Use advanced `placement=...` hints on tables and figures only when needed. Supported values include `here`, `tbp`/`float`, `top`, `bottom`, and `page`.
- Use `Box(...)` for callouts, evidence panels, and tcolorbox-like report sections that should stay editable in Word. Add `icon=...`, `title_position="side"`, or `shadow=True` when a panel needs callout-box treatment; shadows render in HTML and degrade to ordinary boxes in DOCX/PDF.
- Import `Shape(...)`, `TextBox(...)`, `ImageBox(...)`, and `PageItemScope` from `oodocs.positioning` for page-positioned overlays that do not move the body text. Use them with `DocumentSettings(overlays=[...])`; PDF applies scopes to physical pages, while DOCX and HTML use section/static-frame fallbacks. Use `placement="inline"` when the same objects should sit in the text flow like Word's inline drawing mode.
- Prefer explicit domain namespaces for advanced features: `oodocs.structure` for appendices and theorem-like blocks; `oodocs.media` for advanced media/table helpers; `oodocs.references` for advanced reference formatting helpers; `oodocs.engineering` for algorithms; `oodocs.equations` for advanced equation classes; `oodocs.chemistry` for chemistry notation; `oodocs.glossary` for glossary/acronym registries; `oodocs.review` for TODOs and margin notes; `oodocs.positioning` for page overlays; and `oodocs.generated` for generated list pages.
- Use `Theme(header_footer=HeaderFooterDefaults(header_left="{chapter}", header_right="{page}", footer_center="{title}", different_first_page=True))` for LaTeX `fancyhdr`-style running headers and footers. `{page}`, `{title}`, `{chapter}`, and `{section}` are supported; DOCX uses Word fields, PDF draws them in the page callback, and HTML emits a sticky/fixed degrade layer.
- Use `DocumentSettings(...)` for document-wide choices: file/browser metadata, authors, subtitle, page layout, units, page overlays, and theme defaults. Prefer `DocumentSettings(metadata=DocumentMetadata(title=..., author=..., keywords=[...]))` when output metadata should differ from visible title matter, and prefer `DocumentSettings(page_layout=PageLayout.landscape(PageSize.a4(), PageMargins.all(1.5, unit="cm")))` when page size, margins, and orientation should move together. Use `Section(..., page_layout=PageLayout.landscape(...))` when one section needs a different page box; DOCX/PDF create page layout sections and HTML emits a page-break CSS fallback with a validation warning.
- Use `document.validate()` when you want a structured preflight check before rendering. The returned `ValidationResult` follows the `ResultLike` protocol, prints as a compact table, can be serialized with `to_dict()`, `to_json()`, or `save_json()`, and each issue records whether it affects Word, PDF, HTML, or all outputs. `save(...)`, `save_docx(...)`, `save_pdf(...)`, `save_html(...)`, and `save_all(...)` validate before rendering by default and stop before writing when errors are found.
- Use `Document.from_markdown(...)` when a Markdown file should become a full document. Use `parse_markdown(...).blocks` when you want imported blocks that can be inserted, reordered, wrapped in sections, or combined with tables and figures.
- Import `parse_markdown(...)` or `parse_markdown_file(...)` from `oodocs.importers` when you need an `ImportResult` with import issues, `ok`, `errors`, `warnings`, `to_table()`, and JSON sidecar helpers. Use `import_policy="fail-on-lossy"` when lossy Markdown features such as remote images should fail instead of being converted conservatively.
- Use `Document.from_markdown(..., numbered=False, toc=True)` when imported headings should keep their source titles without generated numbers but still appear in a generated table of contents.
- Use `heading_level_shift=1` or `heading_level_shift=-1` with `Document.from_markdown(...)` or `parse_markdown(...)` when imported Markdown should be demoted or promoted before it is inserted into a larger outline. Import `shift_heading_levels(...)` from `oodocs.components.blocks` when already-created `Chapter(...)`/`Section(...)` objects need the same adjustment; paragraphs and other non-heading blocks stay unchanged, and shifts beyond the supported heading range fail.
- Use `Document.from_notebook(...)` when a notebook should become a full document. Import `parse_notebook(...)` and `NotebookImportOptions(...)` from `oodocs.importers` when notebook cells should be merged into a larger report; markdown cells become normal document structure, code cells become `CodeBlock(...)`, and textual outputs can be included or filtered.
- Use `oodocs.adapters` when repository files should become document objects: `ProjectMetadata.from_pyproject(...).to_section()`, `GithubWorkflowSummary.from_file(...).to_section()`, `ReleaseManifestSummary.from_file(...).to_section()`, and `ReleaseEvidence.from_directory(...).to_document()` are designed for release and audit reports.
- Use `oodocs.apidoc` when Python modules should become API documentation material. `collect_api(...)` returns an `ApiPackage`, not a pre-rendered string, so user code can query and compose the parsed API objects:

```python
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
# A repository checkout with src/, setuptools, hatch, Poetry, PDM, Flit, or
# [project] import-names metadata also works. When the apidoc extra is
# installed, collector="griffe" reads source without importing the target repo.
# api = collect_api(".", public_policy="__all__", collector="griffe")
# ApiDocstringParser.auto() can be passed as docstring_style when one parser
# configuration should be reused across collection and coverage steps.
# Custom parser names can be loaded from repo modules through
# docstring-parser-modules in pyproject.toml or --docstring-parser-module.
# For curated public boundaries, pass an ApiPublicPolicy object instead of a
# string and reuse it across collect/check/build steps.
# ApiCollectConfig.from_pyproject(".") can load [tool.oodocs.apidoc], and
# ApiCollectConfig.save_json("apidoc-config.json") stores the same policy so
# CLI commands can reuse it with --config.
classes = api.select_objects(kind="class", module_prefix="oodocs.components")
functions = api.select_objects(kind="function")

doc = Document(
    "Selected API Notes",
    Chapter(
        "Important Classes",
        Paragraph("This chapter is assembled from parsed API objects."),
        *[obj.to_section(level=2, presentation="manual") for obj in classes[:5]],
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
- Markdown and GitHub Flavored Markdown import for headings, paragraphs, lists, task-list markers, block quotes, fenced code, thematic breaks, tables, local images, links, autolinks, emphasis, inline code, strikethrough, and import diagnostics
- Jupyter notebook import for markdown cells, code cells, raw cells, textual stream/result/error outputs, tag filtering, output truncation, image captions, and import diagnostics
- block objects for paragraphs, lists, code blocks, equations, boxes, tables, figures, and generated pages
- Pygments-backed syntax highlighting for code blocks across Python, JavaScript, SQL, YAML, shell, and other supported languages, with optional captions, references, line numbers, highlighted lines, and file-backed source loading
- numbered algorithm blocks with input/output clauses, prose steps, code-style pseudocode, line numbering, and cross-references
- editable report panels with `Box(...)` kwargs for width, block alignment, title color, and per-side padding
- portable comments, TODO annotations, margin notes, and footnotes that stay stable across DOCX, PDF, and HTML
- footnotes target page-bottom placement by default when the renderer supports it; `Theme(blocks=BlockDefaults(footnote_placement="document"))` keeps the collected-notes pattern, and `FootnoteDefaults` supports independent numeric or symbol footnote streams
- captioned tables and figures with automatic numbering and in-text references
- independent document-level labels for table/figure captions and in-text references
- table support for `TableCell(...)`, `rowspan`, `colspan`, banded rows, ordinary Python records, CSV/TSV files, dataframe-like inputs, and cell/row/column styling
- automatic split-table rendering for long tables, with repeated headers where renderers support them
- advanced table and figure placement hints for here/float/top/bottom/page-style workflows
- figure support for stored image files, in-memory bytes, buffers, and `savefig()`-compatible Python objects
- PDF page insertion with `oodocs.pdf.PdfPages(...)`, plus subfigure and subtable groups with automatic child labels and references such as `Figure 1(a)` or `Table 1(a)`
- page-positioned `Shape.rect(...)`, `Shape.ellipse(...)`, `Shape.line(...)`, `TextBox(...)`, and `ImageBox(...)` objects imported from `oodocs.positioning`, with anchors to the page, the margin box, or an earlier named shape, plus all/cover/front/main/page-range scopes for overlays and watermarks
- inline drawing placement for positioning objects, similar to using an image directly in the document flow
- inline chips through `InlineChip(...)`, `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)`
- bibliography support through `CitationSource`, `CitationLibrary`, direct citation objects, BibTeX import, and configurable inline/Reference styles such as APA
- glossary and acronym registries through `oodocs.glossary`, plus the existing `Nomenclature` preset
- optional title matter such as subtitle, structured `Author(...)` metadata, `AuthorLayout(...)`, affiliations, and a cover page
- inline hyperlinks, breakable URL labels, theme-controlled link styling, heading/caption anchors, plural/range object-reference helpers, and validation for broken internal links
- release evidence adapters for pyproject metadata, GitHub Actions workflows, JSON manifests, CSV/TSV evidence tables, checksums, and generated evidence reports
- API object collection, docstring coverage checks, API snapshots, API diffs, and composable API-reference sections through `oodocs.apidoc`

## Example Scripts

The repository includes twelve standalone example directories:

- `examples/usage_guide_example/`
- `examples/journal_paper_example/`
- `examples/native_benchmark_report/`
- `examples/release_notes_digest/`
- `examples/api_objects_example/`
- `examples/style_cleanup_smoke/`
- `examples/template_presets/`
- `examples/project_metadata_report/`
- `examples/cli_manual_example/`
- `examples/config_reference_example/`
- `examples/validation_gate_report/`
- `examples/conformance_matrix_report/`

Choose the example by task. The usage guide explains OODocs concepts; the other
examples are workflow entry points and intentionally avoid repeating the guide.

| Task | Example | Use it when |
|---|---|---|
| Learn OODocs concepts | `usage_guide_example` | You want the object model, renderer behavior, imports, validation, presets, and CLI workflow in one reference-style guide. |
| Write a manuscript from data and figures | `journal_paper_example` | You have CSV-backed tables, matplotlib figures, citations, and article-style sections to assemble into a manuscript. |
| Document Python computation results | `native_benchmark_report` | You want a pure-Python result-to-report workflow with benchmark data, summary tables, and generated prose. |
| Reuse release-note Markdown | `release_notes_digest` | You already maintain versioned Markdown release notes and want a bundled DOCX/PDF/HTML digest. |
| Document Python API objects | `api_objects_example` | You need docstring-collected API objects for help-book pages, composable reference sections, and release sidecars. |
| Create reusable named styles | `style_cleanup_smoke` | You want to extend document-wide paragraph, table, box, and chip styles through a `StyleSheet`. |
| Start from a template | `template_presets` | You want preset objects that turn structured content inputs into complete documents. |
| Review project metadata | `project_metadata_report` | You want `pyproject.toml` and GitHub Actions workflow metadata as a document plus JSON sidecar. |
| Publish a CLI manual | `cli_manual_example` | You want an `argparse` parser rendered as usage, options, subcommands, exit codes, and examples. |
| Publish a config reference | `config_reference_example` | You want TOML config and JSON schema fields rendered as required/optional/default/env-var documentation. |
| Document a validation gate | `validation_gate_report` | You want `Document.validate()` diagnostics rendered as a release-gate report and JSON sidecar. |
| Report a conformance matrix | `conformance_matrix_report` | You want a readable PDF excerpt plus full JSON sidecar for a wide test/simulation matrix. |

Run them directly from the repository checkout:

```powershell
.\.venv\Scripts\python.exe .\examples\usage_guide_example\main.py --output-dir artifacts/usage-guide
.\.venv\Scripts\python.exe .\examples\journal_paper_example\main.py --output-dir artifacts/journal-paper
.\.venv\Scripts\python.exe .\examples\native_benchmark_report\main.py --output-dir artifacts/native-benchmark-report
.\.venv\Scripts\python.exe .\examples\release_notes_digest\main.py --output-dir artifacts/release-notes
.\.venv\Scripts\python.exe .\examples\api_objects_example\main.py . --config pyproject.toml --output-dir artifacts/api-objects-example
.\.venv\Scripts\python.exe .\examples\style_cleanup_smoke\main.py --output-dir artifacts/style-cleanup-smoke
.\.venv\Scripts\python.exe .\examples\template_presets\main.py --output-dir artifacts/template
.\.venv\Scripts\python.exe .\examples\project_metadata_report\main.py --output-dir artifacts/project-metadata-report
.\.venv\Scripts\python.exe .\examples\cli_manual_example\main.py --output-dir artifacts/cli-manual-example
.\.venv\Scripts\python.exe .\examples\config_reference_example\main.py --output-dir artifacts/config-reference-example
.\.venv\Scripts\python.exe .\examples\validation_gate_report\main.py --output-dir artifacts/validation-gate-report
.\.venv\Scripts\python.exe .\examples\conformance_matrix_report\main.py --output-dir artifacts/conformance-matrix-report
```

Most examples accept repeatable `--outputs` and `--quiet` flags:

```powershell
.\.venv\Scripts\python.exe .\examples\native_benchmark_report\main.py --outputs html --quiet
```

The package API reference can also be rendered directly from the
repository-local `apidoc` config:

```python
from oodocs.apidoc import ApiHelpBookConfig

ApiHelpBookConfig.from_pyproject(".").save_all(".")
```

Direct example scripts print slow major render steps. Imported build functions stay quiet by default; pass `verbose=True` when you want the same progress messages.

What they show:

- `usage_guide_example` is a detailed guide that keeps almost all assembly in one `main.py` so the source stays easy to read; it now covers the core authoring model, validation, CLI workflows, theorem-like countable blocks, layout controls, imports, presets, and renderer differences
- the usage guide includes Markdown and notebook import patterns that bring existing authored files into normal OODocs document objects
- `journal_paper_example` shows a longer manuscript-style workflow with article-style sections, unnumbered abstract/highlights/acknowledgements, CSV-backed tables, and matplotlib figures inserted directly from Python objects
- `native_benchmark_report` shows a compact Python-native workflow where a script generates an in-memory workload, benchmarks several callables, turns structured result objects into tables and prose, and exports one report bundle
- `release_notes_digest` collects `release-notes/*.md`, sorts semantic versions from filenames, imports the Markdown bodies, and builds a release-note document with a version-management table and runbook
- `api_objects_example` collects the OODocs API, renders a help-book API reference as DOCX/PDF/HTML, inserts selected API object sections and summary tables into a separate composable document, and writes API object tree JSON plus coverage JSON/CSV sidecars for release evidence
- `style_cleanup_smoke` exercises named paragraph, table, box, and chip styles through a document-level `StyleSheet`, including JSON export/import and category-mismatch validation
- `template_presets` renders ready-to-customize cover page, article, technical report, software manual, and book template presets built from ordinary OODocs blocks
- `project_metadata_report` turns `pyproject.toml` and `.github/workflows/release.yml` into a project metadata report plus JSON sidecar
- `cli_manual_example` turns a runnable `argparse` parser into a command manual with usage, options, subcommands, exit codes, and examples
- `config_reference_example` turns TOML config and JSON schema inputs into a field reference with required fields, defaults, examples, and environment variables
- `validation_gate_report` turns `Document.validate()` output into a release-gate report with warning policy and JSON diagnostics
- `conformance_matrix_report` keeps a wide conformance matrix in JSON while rendering a readable claim boundary, summary, excerpt, and failure appendix

By default they write outputs under:

- `artifacts/usage-guide/`
- `artifacts/journal-paper/`
- `artifacts/native-benchmark-report/`
- `artifacts/release-notes/`
- `artifacts/api-objects-example/`
- `artifacts/style-cleanup-smoke/`
- `artifacts/template/`
- `artifacts/api/`
- `artifacts/project-metadata-report/`
- `artifacts/cli-manual-example/`
- `artifacts/config-reference-example/`
- `artifacts/validation-gate-report/`
- `artifacts/conformance-matrix-report/`

When you run the examples locally, the main exported filenames are:

- `artifacts/usage-guide/oodocs-user-guide.pdf`
- `artifacts/journal-paper/oodocs-development-philosophy.pdf`
- `artifacts/native-benchmark-report/native-python-benchmark.pdf`
- `artifacts/native-benchmark-report/native-python-benchmark.json`
- `artifacts/release-notes/oodocs-release-notes.pdf`
- `artifacts/release-notes/release-notes-import-diagnostics.json`
- `artifacts/api-objects-example/oodocs-api-object-composition.pdf`
- `artifacts/api-objects-example/oodocs-api-object-tree.json`
- `artifacts/api-objects-example/oodocs-api-coverage.json`
- `artifacts/api-objects-example/oodocs-api-coverage.csv`
- `artifacts/style-cleanup-smoke/style-cleanup-smoke.pdf`
- `artifacts/style-cleanup-smoke/style-cleanup-smoke-stylesheet.json`
- `artifacts/template/journal-article-template.pdf`
- `artifacts/project-metadata-report/project-metadata-report.pdf`
- `artifacts/project-metadata-report/project-metadata.json`
- `artifacts/cli-manual-example/cli-manual.pdf`
- `artifacts/config-reference-example/config-reference.pdf`
- `artifacts/validation-gate-report/validation-gate-report.pdf`
- `artifacts/validation-gate-report/validation-result.json`
- `artifacts/conformance-matrix-report/conformance-matrix-report.pdf`
- `artifacts/conformance-matrix-report/conformance-matrix-full.json`
- `artifacts/api-objects-example/oodocs-api-reference.docx`
- `artifacts/api-objects-example/oodocs-api-reference.pdf`
- `artifacts/api-objects-example/oodocs-api-reference.html`
- `artifacts/api/oodocs-api.docx`
- `artifacts/api/oodocs-api.pdf`
- `artifacts/api/oodocs-api.html`
- `artifacts/api/oodocs-api-object-tree.json`
- `artifacts/api/oodocs-api-coverage.json`
- `artifacts/api/oodocs-api-coverage.csv`

## Project Layout

The package is organized by responsibility:

- `src/oodocs/document.py` for the root `Document`
- `src/oodocs/settings.py` for `DocumentSettings` plus grouped configuration exports
- `src/oodocs/components/` for the concrete authoring model (`base.py`, `blocks.py`, `equations.py`, `generated.py`, `inline.py`, `markup.py`, `media.py`, `people.py`, `positioning.py`, and `references.py`)
- `src/oodocs/importers/` for adapters that convert external formats such as Markdown into OODocs objects
- `src/oodocs/adapters/` and `src/oodocs/evidence.py` for repository artefact adapters and release evidence bundles
- `src/oodocs/styles/` for reusable visual styles, grouped theme defaults, and stylesheets
- `src/oodocs/layout/` for low-level render indexing support
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

PyPI uses `README-PYPI.md` as the package long description. Keep the repository
README focused on contributor and release workflow details, and keep the PyPI
README focused on installation, first use, features, and public links.

## Releases

OODocs versions are derived from git tags through `setuptools-scm`.

Create and push a release tag like this:

```powershell
.\scripts\release.ps1 1.1.0
```

That pushes `v1.1.0`, and the GitHub release workflow runs the test suite, enforces API documentation coverage with `oodocs apidoc check`, builds the wheel/sdist artifacts, renders the user guide and API reference PDFs, attaches the user-facing assets to the matching GitHub Release, and uploads the Python distributions to PyPI.

GitHub Release assets are intentionally limited to:

- Python distributions from `dist/*`
- `artifacts/usage-guide/oodocs-user-guide.pdf`
- `artifacts/api/oodocs-api.pdf`

Example outputs, machine-readable sidecars, DOCX variants, and HTML variants stay out of the release download list. Build them locally from the example scripts when needed.

If you want a curated release body instead of GitHub's generated notes, add a file such as `release-notes/v1.1.0.md` before pushing the tag.

The `examples/release_notes_digest/` script demonstrates the same convention as a document workflow: it scans the semantic-versioned Markdown files under `release-notes/`, builds an index, includes the version-management rules, and imports each release body into one DOCX/PDF/HTML bundle.

PyPI publishing uses Trusted Publishing through the `pypi` GitHub environment. The PyPI project or pending publisher must trust repository `Gonie-Gonie/oo-docs`, workflow `.github/workflows/release.yml`, and environment `pypi`.
