# docscriptor

Docscriptor is a Python-first document authoring toolkit for people who want to define structured documents with normal Python code and render the same source to DOCX, PDF, and HTML.

It is aimed at report, documentation, and manuscript workflows where content already lives near Python data, figures, and scripts.

## Install

Docscriptor is not published on PyPI yet, so `pip install docscriptor` will not work at the moment.

For normal use, install it directly from GitHub:

```powershell
pip install "docscriptor @ git+https://github.com/Gonie-Gonie/docscriptor.git"
```

To upgrade later:

```powershell
pip install --upgrade "docscriptor @ git+https://github.com/Gonie-Gonie/docscriptor.git"
```

If you want to work from a repository checkout, run the bundled example scripts, or contribute locally:

```powershell
git clone https://github.com/Gonie-Gonie/docscriptor.git
cd docscriptor
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
from docscriptor import Chapter, Document, DocumentSettings, Paragraph, Section, bold

report = Document(
    "Hello docscriptor",
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
    settings=DocumentSettings(author="Docscriptor"),
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

## Why Not Just LaTeX?

Docscriptor is not trying to replace every LaTeX workflow. It is meant for documents where Python already owns the data, plots, citations, or release process and where collaborators may still need DOCX.

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

Docscriptor tries to keep the source readable:

- create objects with classes such as `Document`, `Part`, `Chapter`, `Section`, `Paragraph`, `Table`, and `Figure`
- apply inline actions with helpers such as `bold(...)`, `italic(...)`, `code(...)`, `tag(...)`, `badge(...)`, `status(...)`, `keyboard(...)`, `Text.from_markup(...)`, `Comment.annotated(...)`, `Footnote.annotated(...)`, and `CitationSource.cite()`
- import existing Markdown with `parse_markdown(...)`, `from_markdown(...)`, or `Document.from_markdown(...)` when release notes, README fragments, or generated Markdown should become editable docscriptor objects
- import Jupyter notebooks with `parse_ipynb(...)`, `from_ipynb(...)`, or `Document.from_ipynb(...)` when notebook markdown, code cells, and textual outputs should become docscriptor blocks
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
- Use `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)` for compact inline labels. They share the `InlineChip(...)` model; DOCX emits small inline images, while PDF and HTML keep styled text.
- Use `highlight(...)`, `strike(...)`, and `line_break()` for Word-style emphasis and manual line breaks inside one paragraph.
- Use `Theme(paragraph_alignment=...)` for the document-wide paragraph default, and direct paragraph kwargs such as `alignment=...` when one paragraph should override it.
- Use `Paragraph(left_indent=..., right_indent=..., first_line_indent=..., unit=...)` when you need Word-like first-line or hanging indents. If `unit` is omitted, indent values follow `DocumentSettings(unit=...)`.
- Use `subscript(...)`, `superscript(...)`, and `prescript(...)` for ordinary prose. Use `Math(...)` or `Equation(...)` for lightweight LaTeX-style math, including ordinary `x^2` / `x_0` scripts and front scripts such as `\prescript{14}{6}{C}`.
- Use `Part(...)` for book-like divisions above chapters; each part gets a separator page, while chapter numbers continue across parts by default.
- Use `Chapter(...)`, `Section(...)`, `Subsection(...)`, and `Subsubsection(...)` for the visible outline. Their nesting in Python should match how you expect the final document to read.
- Use `reference(obj)` or `obj.reference()` for cross-references to captioned media, headings, equations, paragraphs, code blocks, and boxes. Passing the raw object inside `Paragraph(...)` is rejected so insertion and citation are not confused.
- Use `Table(...)` for small authored tables and `Table.from_dataframe(...)` when the data already lives in pandas.
- Use `TableCell(horizontal_alignment=..., vertical_alignment=...)` or table-wide `Table(..., cell_horizontal_alignment=..., cell_vertical_alignment=...)` when a table needs Word-like cell alignment. Use dictionaries in `row_styles`, `header_row_styles`, or `column_styles` when rows or columns need background color, text color, bold, or italic formatting.
- Use `Table(split=True)` when a table should render in source order and may break across pages. Leave `split=False` when the table should stay together when possible; very long tables are automatically rendered as split repeated-header tables.
- Use `Figure(...)` for image files or `savefig()`-compatible Python figure objects.
- Use `SubFigureGroup(SubFigure(...), SubFigure(...), caption=...)` when related images should share one figure number and expose `(a)`, `(b)`, and similar subfigure references.
- Use `Theme(table_caption_label=..., table_reference_label=..., figure_caption_label=..., figure_reference_label=...)` when captions and in-text references should use different labels such as `Figure`, `Fig.`, or localized terms.
- Use `Theme(citation_format="apa", reference_format="apa")` when inline citations and the generated references page should follow an author-year style. Numeric citation output remains the default.
- Use advanced `placement=...` hints on tables and figures only when needed. Supported values include `here`, `tbp`/`float`, `top`, `bottom`, and `page`.
- Use `Box(...)` for callouts, evidence panels, and tcolorbox-like report sections that should stay editable in Word.
- Use `Shape(...)`, `TextBox(...)`, and `ImageBox(...)` with `Document(..., page_items=[...])` for page-positioned overlays that do not move the body text. Use `placement="inline"` when the same objects should sit in the text flow like Word's inline drawing mode.
- Use `DocumentSettings(...)` for document-wide choices: authors, subtitle, page size, margins, units, and theme defaults.
- Use `Document.from_markdown(...)` when a Markdown file should become a full document. Use `parse_markdown(...)` when you want a list of blocks that can be inserted, reordered, wrapped in sections, or combined with tables and figures.
- Use `Document.from_ipynb(...)` when a notebook should become a full document. Use `parse_ipynb(...)` when notebook cells should be merged into a larger report; markdown cells become normal document structure, code cells become `CodeBlock(...)`, and textual outputs can be included or filtered.
- Use `document.save_all("artifacts")` when a workflow normally needs DOCX, PDF, and HTML together.

## Features

- DOCX, PDF, and HTML rendering from the same document tree
- Markdown and GitHub Flavored Markdown import for headings, paragraphs, lists, task-list markers, block quotes, fenced code, thematic breaks, tables, local images, links, autolinks, emphasis, inline code, and strikethrough
- Jupyter notebook import for markdown cells, code cells, raw cells, and textual stream/result/error outputs
- block objects for paragraphs, lists, code blocks, equations, boxes, tables, figures, and generated pages
- Pygments-backed syntax highlighting for code blocks across Python, JavaScript, SQL, YAML, shell, and other supported languages
- editable report panels with `Box(...)` kwargs for width, alignment, title color, and per-side padding
- portable comments and footnotes that stay stable across DOCX, PDF, and HTML
- footnotes target page-bottom placement by default when the renderer supports it; `Theme(footnote_placement="document")` keeps the collected-notes pattern
- captioned tables and figures with automatic numbering and in-text references
- independent document-level labels for table/figure captions and in-text references
- table support for `TableCell(...)`, `rowspan`, `colspan`, banded rows, dataframe-like inputs, and cell/row/column styling
- automatic split-table rendering for long tables, with repeated headers where renderers support them
- advanced table and figure placement hints for here/float/top/bottom/page-style workflows
- figure support for both stored image files and `savefig()`-compatible Python objects
- subfigure groups with automatic child labels and references such as `Figure 1(a)`
- page-positioned `Shape.rect(...)`, `Shape.ellipse(...)`, `Shape.line(...)`, `TextBox(...)`, and `ImageBox(...)` objects with anchors to the page, the margin box, or an earlier named shape
- inline drawing placement for `Shape(...)`, `TextBox(...)`, and `ImageBox(...)`, similar to using an image directly in the document flow
- inline chips through `InlineChip(...)`, `tag(...)`, `badge(...)`, `status(...)`, and `keyboard(...)`
- bibliography support through `CitationSource`, `CitationLibrary`, direct citation objects, BibTeX import, and configurable inline/reference formats such as APA
- optional title matter such as subtitle, structured `Author(...)` metadata, `AuthorLayout(...)`, affiliations, and a cover page
- inline hyperlinks and heading/caption anchors for cross-references

## Example Scripts

The repository includes two standalone example directories:

- `examples/usage_guide_example/`
- `examples/journal_paper_example/`

Run them directly from the repository checkout:

```powershell
.\.venv\Scripts\python.exe .\examples\usage_guide_example\main.py
.\.venv\Scripts\python.exe .\examples\journal_paper_example\main.py
```

What they show:

- `usage_guide_example` is a detailed guide that keeps almost all assembly in one `main.py` so the source stays easy to read
- the usage guide includes Markdown and notebook import patterns that bring existing authored files into normal docscriptor document objects
- `journal_paper_example` shows a longer manuscript-style workflow with article-style sections, unnumbered abstract/highlights/acknowledgements, CSV-backed tables, and matplotlib figures inserted directly from Python objects

By default they write outputs under:

- `artifacts/usage-guide/`
- `artifacts/journal-paper/`

The main exported filenames are:

- `artifacts/usage-guide/docscriptor-user-guide.pdf`
- `artifacts/journal-paper/docscriptor-development-philosophy.pdf`

## Project Layout

The package is organized by responsibility:

- `src/docscriptor/document.py` for the root `Document`
- `src/docscriptor/settings.py` for `DocumentSettings` plus grouped configuration exports
- `src/docscriptor/components/` for the concrete authoring model (`base.py`, `blocks.py`, `equations.py`, `generated.py`, `inline.py`, `markup.py`, `media.py`, `people.py`, `positioning.py`, and `references.py`)
- `src/docscriptor/importers/` for adapters that convert external formats such as Markdown into docscriptor objects
- `src/docscriptor/layout/` for low-level theme and indexing support
- `src/docscriptor/renderers/docx.py`, `src/docscriptor/renderers/pdf.py`, and `src/docscriptor/renderers/html.py` for format-specific layout

## Development

Assuming Python 3.14 is installed:

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

Docscriptor versions are derived from git tags through `setuptools-scm`.

Create and push a release tag like this:

```powershell
.\scripts\release.ps1 0.3.0
```

That pushes `v0.3.0`, and the GitHub release workflow builds the wheel/sdist artifacts plus the two example PDFs and attaches them to the matching GitHub Release automatically.

If you want a curated release body instead of GitHub's generated notes, add a file such as `release-notes/v0.3.0.md` before pushing the tag.
