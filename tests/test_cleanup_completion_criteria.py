from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path


LOCAL_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:\b[A-Za-z]:[\\/]+Users[\\/]|/home/|/Users/)"
)
WINDOWS_DRIVE_PATH_PATTERN = re.compile(r"\b[A-Za-z]:[\\/]")
TRACKED_DOCUMENTATION_PATHS = (
    "README.md",
    "README-PYPI.md",
    "docs",
    "examples",
)
TRACKED_USER_FACING_PATHS = (
    "README.md",
    "README-PYPI.md",
    "docs",
    "examples",
    "src",
    "artifacts",
    ".github",
    "pyproject.toml",
)
TEXT_FILE_SUFFIXES = {
    ".cfg",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def _readme() -> str:
    return Path("README.md").read_text(encoding="utf-8")


def _python_blocks(markdown: str) -> list[str]:
    return re.findall(r"```python\n(.*?)\n```", markdown, flags=re.DOTALL)


def _documentation_text_files() -> list[Path]:
    paths = [Path("README.md"), Path("README-PYPI.md")]
    for root_name in ("docs", "examples", "src/oodocs"):
        root = Path(root_name)
        paths.extend(root.rglob("*.md"))
        paths.extend(root.rglob("*.py"))
    return sorted({path for path in paths if path.exists()})


def _tracked_user_facing_text_files() -> list[Path]:
    return _tracked_text_files(*TRACKED_USER_FACING_PATHS)


def _tracked_documentation_text_files() -> list[Path]:
    return _tracked_text_files(*TRACKED_DOCUMENTATION_PATHS)


def _tracked_text_files(*pathspecs: str) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", *pathspecs],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    paths = [Path(line) for line in result.stdout.splitlines() if line.strip()]
    return sorted(
        path
        for path in paths
        if path.suffix.lower() in TEXT_FILE_SUFFIXES and path.exists()
    )


def test_readme_quick_start_uses_small_top_level_import_surface() -> None:
    readme = _readme()
    quick_start = readme.split("## Quick Start", 1)[1].split("## Command Line", 1)[0]
    block = _python_blocks(quick_start)[0]
    module = ast.parse(block)
    oodocs_imports = [
        alias.name
        for node in module.body
        if isinstance(node, ast.ImportFrom) and node.module == "oodocs"
        for alias in node.names
    ]
    domain_only_names = {
        "Algorithm",
        "ChemicalFormula",
        "ImageBox",
        "MarginNote",
        "PdfPages",
        "Shape",
        "TextBox",
        "Todo",
        "collect_api",
        "parse_markdown",
    }

    assert 0 < len(oodocs_imports) <= 12
    assert domain_only_names.isdisjoint(oodocs_imports)


def test_readme_what_to_use_when_keeps_core_import_checkpoint() -> None:
    readme = _readme()
    section = readme.split("## What To Use When", 1)[1].split("## Features", 1)[0]
    first_block = _python_blocks(section)[0]
    module = ast.parse(first_block)
    imports = [
        alias.name
        for node in module.body
        if isinstance(node, ast.ImportFrom) and node.module == "oodocs"
        for alias in node.names
    ]
    focused_examples = {
        "`examples/engineering_report_example/`",
        "`examples/review_notes_example/`",
        "`examples/page_overlay_example/`",
        "`examples/api_objects_example/`",
    }

    assert imports == ["Chapter", "Document", "Paragraph", "Table", "ref"]
    for example in focused_examples:
        assert example in section


def test_readme_latex_translations_include_heading_style_packages() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `titlesec` / `sectsty` heading styles" in translations
    assert "`HeadingStyle(...)`" in translations
    assert "`Theme(blocks=BlockDefaults(heading_styles={...}))`" in translations
    assert "`Section(..., heading_style=...)`" in translations


def test_readme_latex_translations_include_generated_list_packages() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `tocloft` / `titletoc` / `minitoc`" in translations
    assert "`TableOfContents(scope=..., level_styles=...)`" in translations
    assert "`ListOfTables(scope=...)`" in translations
    assert "`ListOfFigures(scope=...)`" in translations


def test_readme_latex_translations_include_appendix_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `\\appendix`" in translations
    assert "`Appendix(Chapter(...), ...)`" in translations
    assert "child chapters numbered `A`, `B`, `C`" in translations
    assert "heading references use those labels" in translations
    assert "table and figure counters stay document-wide" in translations


def test_readme_latex_translations_include_booktabs_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `booktabs`" in translations
    assert "`Table(..., style=\"booktabs\")`" in translations
    assert "`TableStyle.booktabs()`" in translations
    assert "`top_rule`, `header_rule`, and `bottom_rule`" in translations
    assert "horizontal rules without vertical grid lines" in translations


def test_readme_latex_translations_include_longtable_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `longtable`" in translations
    assert "`Table(..., split=True, continuation_label=..., continued_caption_template=...)`" in translations
    assert "repeated header rows in DOCX/PDF" in translations
    assert "HTML plain-flow headers via `display: table-header-group`" in translations


def test_readme_latex_translations_include_tabularx_array_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `tabularx` / `array` column specs" in translations
    assert "`ColumnSpec(width=...)`" in translations
    assert "`ColumnSpec(flex=...)`" in translations
    assert "`Table.excerpt(...)`" in translations
    assert "`TableOverflowPolicy(action=\"allow\")`" in translations
    assert "CSV sidecar for very wide matrices" in translations


def test_readme_latex_translations_include_multirow_multicolumn_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `multirow` / `multicolumn`" in translations
    assert "`TableCell(rowspan=...)`" in translations
    assert "`TableCell(colspan=...)`" in translations
    assert "`Table.grouped_headers(...)`" in translations


def test_readme_latex_translations_include_hyperref_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `hyperref`, `\\url{...}`, and `\\href{...}{...}`" in translations
    assert "`url(...)`" in translations
    assert "`link(...)`" in translations
    assert "`ref(obj)`" in translations
    assert "`DocumentSettings(metadata=DocumentMetadata(...))`" in translations
    assert "`Theme(links=LinkDefaults(...))`" in translations


def test_readme_latex_translations_include_cleveref_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `cleveref` / `varioref` typed references" in translations
    assert "`refs([...])`" in translations
    assert "`ref_range(a, b)`" in translations
    assert "`ReferenceFormat(...)`" in translations
    assert "`bracket_ref(...)`" in translations
    assert "`paren_ref(...)`" in translations
    assert "`page_ref(...)`" in translations
    assert "`oodocs.references`" in translations


def test_readme_latex_translations_include_url_break_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `url` / `xurl` / `breakurl` long URL labels" in translations
    assert "`url(target, label=..., breakable=True)`" in translations
    assert "soft breaks" in translations
    assert "exact link targets" in translations
    assert "`overly-long-url` validation" in translations


def test_readme_latex_translations_include_enumitem_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `enumitem` list options" in translations
    assert "`BulletList(...)`" in translations
    assert "`NumberedList(start=...)`" in translations
    assert "`NumberedList(resume_from=...)`" in translations
    assert "`CounterStyle(...)`" in translations
    assert "`ListStyle(...)`" in translations
    assert "nested item children" in translations


def test_readme_latex_translations_include_glossary_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `glossaries` / `acronym` / `nomencl`" in translations
    assert "`Glossary(...)`" in translations
    assert "`glossary.term(...)`" in translations
    assert "`glossary.acronym(...)`" in translations
    assert "`glossary.use(...)`" in translations
    assert "`ListOfGlossaryTerms(...)`" in translations
    assert "`Nomenclature`" in translations


def test_readme_latex_translations_include_locale_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `babel` / `polyglossia` document language" in translations
    assert "`Theme.from_locale(\"ko-KR\")`" in translations
    assert "`LocaleDefaults.from_locale(...)`" in translations
    assert "localized labels, generated titles, dates" in translations
    assert "HTML `lang`" in translations
    assert "PDF font guidance" in translations


def test_readme_latex_translations_include_header_footer_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `fancyhdr` / `scrlayer-scrpage` running headers and footers" in translations
    assert "`Theme(header_footer=HeaderFooterDefaults(...))`" in translations
    assert "`{page}`" in translations
    assert "`{title}`" in translations
    assert "`{chapter}`" in translations
    assert "`{section}`" in translations
    assert "first-page, and even-page templates" in translations


def test_readme_latex_translations_include_page_overlay_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `eso-pic` / `background` / `wallpaper` page overlays" in translations
    assert "`Shape.rect(...)`" in translations
    assert "`TextBox(...)`" in translations
    assert "`ImageBox(...)`" in translations
    assert "`PageItemScope`" in translations
    assert "`DocumentSettings(overlays=[...])`" in translations


def test_readme_latex_translations_include_footnote_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `footmisc` / `manyfoot` notes" in translations
    assert "`footnote(...)`" in translations
    assert "`Footnote.annotated(...)`" in translations
    assert "`FootnoteDefaults(...)`" in translations
    assert "`FootnoteStyle.symbol(...)`" in translations
    assert "stream names" in translations
    assert "`ListOfFootnotes(...)` from `oodocs.generated`" in translations


def test_readme_latex_translations_include_review_annotation_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `marginnote` / `todonotes` review annotations" in translations
    assert "`todo(...)`" in translations
    assert "`Todo(...)`" in translations
    assert "`margin_note(...)`" in translations
    assert "`MarginNote(...)`" in translations
    assert "`oodocs.review`" in translations
    assert "HTML side-note output" in translations
    assert "DOCX/PDF comment fallbacks" in translations


def test_readme_latex_translations_include_template_class_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `article` / `report` / `book` / KOMA-Script classes" in translations
    assert "`JournalArticleTemplate`" in translations
    assert "`TechnicalReportTemplate`" in translations
    assert "`SoftwareManualTemplate`" in translations
    assert "`BookTemplate`" in translations
    assert "`CoverPagePreset.accented(...)` or `CoverPagePreset.centered_logo(...)`" in translations
    assert "`Section(...)`, `Chapter(...)`, `Part(...)`, and `Appendix(...)`" in translations


def test_readme_latex_translations_include_graphicx_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `\\includegraphics`" in translations
    assert "`Figure(path_or_matplotlib_figure, caption=...)`" in translations
    assert "`CropBox(...)`" in translations
    assert "`rotation=...`" in translations
    assert "`alt_text=...`" in translations


def test_readme_latex_translations_include_subcaption_subfig_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX subfigures" in translations
    assert "`SubFigure(...)`" in translations
    assert "`SubFigureGroup(...)`" in translations
    assert "LaTeX subtables" in translations
    assert "`SubTable(Table(...), caption=...)`" in translations
    assert "`SubTableGroup(...)`" in translations


def test_readme_latex_translations_include_pdfpages_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `pdfpages`" in translations
    assert "`PdfPages(\"appendix.pdf\", pages=[1, 3])`" in translations
    assert "PDF-page insertion" in translations
    assert "DOCX/HTML placeholder fallbacks" in translations


def test_table_media_support_reference_documents_media_api_policy() -> None:
    reference = Path("docs/reference/table-media-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "advanced column layout, PDF-only page insertion, and table overflow policy",
        "`Table(headers, rows)`",
        "`Table.from_records(records, columns=...)`",
        "`ColumnSpec(key=..., header=..., visible=False)`",
        "`Table.from_dataframe(data, columns=...)`",
        "`Table.from_csv(...)` or `Table.from_tsv(...)`",
        "`ColumnSpec(width=...)` or `ColumnSpec(flex=...)` from `oodocs.media`",
        "`TableOverflowPolicy(action=\"allow\")` from `oodocs.media`",
        "`column_widths=...` remains available for simple fixed-width tables",
        "Do not pass both `columns` and `column_widths`",
        "`ColumnSpec(flex=...)`, `Table.excerpt(...)`, or `Table.save_csv(...)`",
        "Use `PdfPages(...)` from `oodocs.pdf`",
        "`pdf-pages-non-pdf-output`",
        "use `image_format` and `image_dpi` rather than generic `format` or `dpi`",
        "`ImageData.savefig(...)` is a compatibility adapter",
    ):
        assert phrase in normalized


def test_readme_latex_translations_include_listings_minted_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `listings` / `minted`" in translations
    assert "`CodeBlock(..., caption=..., line_numbers=True, highlight_lines={...})`" in translations
    assert "`CodeBlock.from_file(...)`" in translations


def test_readme_latex_translations_include_algorithmicx_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `algorithm` / `algorithmicx`" in translations
    assert "`Algorithm(..., inputs=..., outputs=..., steps=...)`" in translations
    assert "`oodocs.engineering`" in translations
    assert "automatic numbering and references" in translations


def test_readme_latex_translations_include_tcolorbox_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `tcolorbox` / `mdframed` report panels" in translations
    assert "`Box(..., icon=..., title_position=\"side\")`" in translations
    assert "`CalloutBox(..., variant=\"danger\", icon=\"!\")`" in translations


def test_readme_latex_translations_include_amsmath_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `amsmath` / `mathtools` display math" in translations
    assert "`Equation(...)`" in translations
    assert "`Equation.aligned(...)`" in translations
    assert "`Equation.cases(...)`" in translations
    assert "`Equation.from_sympy(...)`" in translations
    assert "parser limits covered in `docs/reference/math-support.md`" in translations


def test_math_support_reference_documents_amsmath_policy() -> None:
    reference = Path("docs/reference/math-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "`Equation(numbered=True)` is the default",
        "`Equation(numbered=False)` does not consume a number",
        "`Equation.aligned(...)` and `Equation.cases(...)` are the canonical authoring",
        "`Equation.aligned(...)`",
        "`Equation.cases(...)`",
        "`Equation.from_sympy(...)`",
        "`AlignedEquation(...)` and `CasesEquation(...)` classes remain available from `oodocs.equations`",
        "not part of the top-level `oodocs` import surface",
        "`aligned`, `align`, `split`, and `multline` environments",
        "`matrix`, `pmatrix`, `bmatrix`, `array` environments",
        "`unsupported-latex-command` warnings",
    ):
        assert phrase in normalized


def test_readme_latex_translations_include_mhchem_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `mhchem` chemistry notation" in translations
    assert "`chemical_formula(...)`" in translations
    assert "`ce(...)`" in translations
    assert "`ReactionEquation(...)`" in translations
    assert "`oodocs.chemistry`" in translations
    assert "formula subscripts, charge superscripts, Unicode script input" in translations
    assert "reaction references" in translations


def test_chemistry_support_reference_documents_mhchem_policy() -> None:
    reference = Path("docs/reference/chemistry-support.md").read_text(encoding="utf-8")

    for phrase in (
        "OODocs provides mhchem-inspired helpers",
        "`oodocs.chemistry` namespace",
        "`chemical_formula(...)` or `ChemicalFormula(...)`",
        "`ce(...)`",
        "`ReactionEquation(...)`",
        "Renders numeric suffixes as subscripts and charges as superscripts.",
        "Unicode subscript digits normalize to ordinary subscript runs.",
        "Unicode superscript digits and signs normalize to superscript runs.",
        "Reaction arrows such as `->`",
        "full mhchem grammar",
    ):
        assert phrase in reference


def test_header_footer_support_reference_documents_fancyhdr_policy() -> None:
    reference = Path("docs/reference/header-footer-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "common `fancyhdr` and `scrlayer-scrpage` running header and footer needs",
        "`Theme(header_footer=HeaderFooterDefaults(...))`",
        "`HeaderFooterDefaults(...)`",
        "`{page}` token",
        "`PageNumberDefaults(show_page_numbers=True)`",
        "`{title}`",
        "`{chapter}` and `{section}`",
        "`different_first_page=True`",
        "`different_odd_even_pages=True`",
        "DOCX uses section header/footer parts",
        "PDF draws header and footer text in the page callback",
        "HTML emits a sticky/fixed header-footer layer with print CSS",
        "`theme.resolve_header_footer_template(...)`",
        "`theme.format_header_footer_text(...)`",
    ):
        assert phrase in normalized


def test_page_overlay_support_reference_documents_background_policy() -> None:
    reference = Path("docs/reference/page-overlay-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "common `eso-pic`, `background`, and `wallpaper` page decoration needs",
        "`Shape.rect(...)`, `Shape.ellipse(...)`, or `Shape.line(...)`",
        "`TextBox(...)`",
        "`ImageBox(...)`",
        "`DocumentSettings(overlays=[...])`",
        "`PageItemScope.all()`, `.cover()`, `.front()`, `.main()`, or `.pages(...)`",
        "`anchor=\"page\"`, `anchor=\"margin\"`, or a named item",
        "`z_index=...`",
        "`placement=\"inline\"`",
        "PDF applies page scopes to physical pages.",
        "`page-item-scope-static-output`",
        "cover-only overlays",
    ):
        assert phrase in normalized


def test_footnote_support_reference_documents_footmisc_policy() -> None:
    reference = Path("docs/reference/footnote-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "common `footmisc` and `manyfoot` authoring needs",
        "`footnote(\"term\", \"note\")`",
        "`Footnote.annotated(\"term\", \"note\")`",
        "`footnote(\"term\", \"note\", stream=\"symbols\")`",
        "`Theme(footnotes=FootnoteDefaults(...))`",
        "`FootnoteStyle.symbol()`",
        "`FootnoteStyle(CounterStyle(prefix=\"R\"))`",
        "`ListOfFootnotes()` from `oodocs.generated`",
        "`Theme(blocks=BlockDefaults(footnote_placement=\"document\"))`",
        "Custom streams such as `symbols` or `review` have independent counters.",
        "`FootnoteDefaults(stream_styles={...})`",
        "`FootnoteStyle.symbol((\"*\", \"#\"))`",
        "native page-bottom Word footnotes only for the default stream",
        "`docx-footnote-stream-generated-list`",
        "Page-bottom placement remains renderer-dependent",
    ):
        assert phrase in normalized


def test_review_annotation_support_reference_documents_todonotes_policy() -> None:
    reference = Path("docs/reference/review-annotation-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "common `marginnote` and `todonotes` authoring needs",
        "helpers in `oodocs.review`",
        "`todo(\"Verify units.\", owner=\"QA\")`",
        "`Todo(\"Verify units.\", owner=\"QA\", status=\"open\")`",
        "`margin_note(\"Keep this beside the claim.\", side=\"left\")`",
        "`MarginNote(\"Check this assumption.\", side=\"right\")`",
        "`ListOfComments(\"Collected Review Notes\")`",
        "`examples/review_notes_example/`",
        "`oodocs-margin-note-left` or `oodocs-margin-note-right`",
        "`margin-note-renderer-fallback`",
        "TODO annotations use the comment workflow across DOCX, PDF, and HTML.",
        "`owner=...`, `status=...`, `value=...`, `author=...`, and `initials=...`",
        "Use footnotes when the note is part of the published reading flow.",
    ):
        assert phrase in normalized


def test_template_preset_support_reference_documents_class_policy() -> None:
    reference = Path("docs/reference/template-preset-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "common `article`, `report`, `book`, and KOMA-Script class needs",
        "The presets create normal `Document` objects",
        "`JournalArticleTemplate(...)`",
        "`TechnicalReportTemplate(...)`",
        "`SoftwareManualTemplate(...)`",
        "`BookTemplate(...)`",
        "`front_matter=...`, `parts=...`, `chapters=...`, `appendices=...`, and `back_matter=...`",
        "`CoverPagePreset.accented(...)` or `CoverPagePreset.centered_logo(...)`",
        "`Section(...)`, `Chapter(...)`, `Part(...)`, and `Appendix(...)`",
        "`Section(..., numbered=False)`",
        "`Chapter(...)` and `Part(...)`",
        "`Appendix(...)`",
        "document classes as content presets",
        "`Theme(...)`, `DocumentSettings(title_matter=...)`, and `DocumentSettings(page_layout=...)`",
        "`examples/template_presets/`",
    ):
        assert phrase in normalized


def test_locale_support_reference_documents_babel_policy() -> None:
    reference = Path("docs/reference/locale-support.md").read_text(encoding="utf-8")

    for phrase in (
        "common `babel` and `polyglossia` document-language needs",
        "`Theme.from_locale(\"ko-KR\")`",
        "`LocaleDefaults.from_locale(\"ko-KR\")`",
        "`CaptionDefaults(...)`",
        "`GeneratedContentDefaults(...)`",
        "`theme.format_date(value)`",
        "`theme.resolve_language_tag()`",
        "HTML `lang` and DOCX language settings",
        "`theme.pdf_font_fallback_guide()`",
        "Hyphenation and script shaping remain renderer-dependent.",
    ):
        assert phrase in reference


def test_glossary_support_reference_documents_glossaries_policy() -> None:
    reference = Path("docs/reference/glossary-support.md").read_text(encoding="utf-8")

    for phrase in (
        "common `glossaries`, `acronym`, and `nomencl` authoring needs",
        "`Glossary(...)`",
        "`glossary.term(key, definition, term=...)`",
        "`glossary.acronym(key, long, short=...)`",
        "`glossary.use(key)`",
        "acronyms expand on first use and use short form later",
        "`ListOfGlossaryTerms(glossary, sort=...)`",
        "sorted by insertion order, key, or term",
        "`Nomenclature(...)`",
        "`duplicate-glossary-key` validation error",
        "`empty-glossary-list` warning",
    ):
        assert phrase in reference


def test_list_support_reference_documents_enumitem_policy() -> None:
    reference = Path("docs/reference/list-support.md").read_text(encoding="utf-8")

    for phrase in (
        "common `enumitem` list authoring needs",
        "`BulletList(...)`",
        "`NumberedList(...)`",
        "`NumberedList(..., resume_from=previous)`",
        "`start` and `resume_from` are mutually exclusive.",
        "`CounterStyle(counter_format=..., prefix=..., suffix=..., bullet=...)`",
        "`ListStyle(indent=..., marker_gap=..., item_spacing=..., block_spacing=...)`",
        "`StyleSheet.register_list(name, ListStyle(...))`",
        "`item_children=[[BulletList(...), NumberedList(...)]]`",
        "Nested lists inherit the surrounding renderer context",
    ):
        assert phrase in reference


def test_reference_support_reference_documents_cleveref_policy() -> None:
    reference = Path("docs/reference/reference-support.md").read_text(encoding="utf-8")

    for phrase in (
        "common `cleveref` and `varioref` authoring needs",
        "`ref(obj)` or `obj.ref()`",
        "`refs([a, b])`",
        "`ref_range(a, b)`",
        "`ReferenceFormat(...)`",
        "`bracket_ref(obj)` or `paren_ref(obj)`",
        "`page_ref(obj)`",
        "`page-aware-reference-degrades`",
        "`plural_label=...`",
        "`range_separator`",
        "`reference_label` settings",
        "Page-aware references are intentionally treated as a degrade path",
    ):
        assert phrase in reference


def test_hyperref_support_reference_documents_metadata_policy() -> None:
    reference = Path("docs/reference/hyperref-support.md").read_text(encoding="utf-8")

    for phrase in (
        "hyperlink, anchor, metadata, and outline behavior",
        "`link(target, label)`",
        "`url(target, breakable=True)`",
        "`ref(obj)`, `obj.ref()`, `refs(...)`, or `ref_range(...)`",
        "`Hyperlink.internal_anchor(...)`",
        "`DocumentSettings(metadata=DocumentMetadata(...))`",
        "`Theme(links=LinkDefaults(TextStyle(...)))`",
        "Core properties",
        "PDF info dictionary",
        "`<title>` and meta tags",
        "PDF outline/bookmarks",
        "Broken internal link validation",
        "Preflight error",
    ):
        assert phrase in reference


def test_hyperref_support_reference_documents_url_break_policy() -> None:
    reference = Path("docs/reference/hyperref-support.md").read_text(encoding="utf-8")
    normalized = " ".join(reference.split())

    for phrase in (
        "## URL Line-Break Policy",
        "`url(target, label=None, breakable=True)`",
        "preserves the external link target",
        "exactly while making the visible label safer",
        "zero-width soft break points",
        "DOCX, PDF, and HTML keep the original target",
        "`href` attribute",
        "`label=...`",
        "`overly-long-url`",
        "`url(..., breakable=True)` or a shorter label",
    ):
        assert phrase in normalized


def test_readme_latex_translations_include_citation_policy() -> None:
    readme = _readme()
    translations = readme.split("Common translations:", 1)[1].split(
        "The main payoff",
        1,
    )[0]

    assert "LaTeX `natbib` / `biblatex` / BibTeX citations" in translations
    assert "`CitationLibrary.from_bibtex_file(...)`" in translations
    assert "`cite(...)`" in translations
    assert "`CitationSource.cite()`" in translations
    assert "`CitationDefaults(...)`" in translations
    assert "`ListOfReferences(...)`" in translations


def test_citation_support_reference_documents_bibtex_policy() -> None:
    reference = Path("docs/reference/citation-support.md").read_text(encoding="utf-8")

    for phrase in (
        "common `natbib`, `biblatex`, and BibTeX authoring needs",
        "`CitationLibrary(...)`",
        "Requires unique non-empty keys and raises on duplicates.",
        "`cite(\"key\")`, `CitationSource.cite()`, or `CitationLibrary.cite(\"key\")`",
        "`ListOfReferences()`",
        "`ReferenceList` and `ReferencesPage` are not separate public aliases.",
        "`CitationLibrary.from_bibtex(...)` or `.from_bibtex_file(...)`",
        "Duplicate citation keys",
        "BibLaTeX-only fields",
        "CSL-level compatibility is intentionally outside",
        "`CitationDefaults(citation_style=...)`",
        "`CitationDefaults(reference_style=...)`",
        "`CitationDefaults(reference_sort=...)` or `ListOfReferences(sort=...)`",
        "`ListOfReferences(include_uncited=True)`",
    ):
        assert phrase in reference


def test_public_api_policy_doc_defines_tiers_and_guards() -> None:
    policy = Path("docs/reference/public-api-policy.md").read_text(encoding="utf-8")

    for phrase in (
        "src/oodocs/public_api.py",
        "Tier 1 core",
        "Tier 2 domain",
        "Tier 3 internal",
        "`oodocs.presets.components`",
        "`oodocs.presets.templates`",
        "TOP_LEVEL_EXPORT_LIMIT",
        "TOP_LEVEL_SYMBOL_TIERS",
        "`coerce`",
        "`normalize`",
        "`render_to_`",
        "`reference`",
        "`Ref`",
        "`math`",
        "`CalloutBox`",
        "`JournalArticleTemplate`",
        "top-level `oodocs` must not export preset names.",
        "README Quick Start examples use Tier 1 imports only.",
        "Advanced examples import their domain namespace explicitly.",
        "Template preset docs describe reusable document skeletons",
        "ordinary examples describe runnable direct-composition workflows",
    ):
        assert phrase in policy


def test_link_examples_use_target_first_argument_order() -> None:
    reversed_external_link = re.compile(
        r"link\(\s*(['\"])(?!(?:https?://|mailto:))[^'\"]+\1\s*,\s*"
        r"(['\"])(?:https?://|mailto:)[^'\"]+\2"
    )

    violations = []
    for path in _documentation_text_files():
        text = path.read_text(encoding="utf-8")
        for match in reversed_external_link.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path}:{line_number}")

    assert violations == []


def test_custom_style_guide_prefers_typed_stylesheet_register_helpers() -> None:
    guide = Path("docs/how-to/create-custom-styles.md").read_text(encoding="utf-8")
    first_block = _python_blocks(guide)[0]

    assert "styles.register_paragraph(" in first_block
    assert "styles.register_table(" in first_block
    assert "styles.register_box(" in first_block
    assert "styles.register_chip(" in first_block
    assert "styles.register(" not in first_block
    assert "category-string `register(category, name, style)`" in guide
    assert "dynamic or advanced tooling" in guide


def test_api_sections_guide_prefers_apipackage_render_methods() -> None:
    guide = Path("docs/how-to/compose-api-objects.md").read_text(encoding="utf-8")
    first_block = _python_blocks(guide)[0]

    assert "api_objects_to_chapter" not in first_block
    assert "api.subset(" in first_block
    assert "selected_api.to_sections(" in first_block
    assert "ApiPackage.subset(...).to_sections(...)" in guide
    assert "lower-level render helpers" in guide


def test_tracked_user_facing_text_has_no_local_absolute_paths() -> None:
    violations = []
    for path in _tracked_user_facing_text_files():
        text = path.read_text(encoding="utf-8")
        for match in LOCAL_ABSOLUTE_PATH_PATTERN.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path}:{line_number}")

    assert violations == []


def test_documentation_examples_do_not_use_windows_drive_paths() -> None:
    violations = []
    for path in _tracked_documentation_text_files():
        text = path.read_text(encoding="utf-8")
        for match in WINDOWS_DRIVE_PATH_PATTERN.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path}:{line_number}")

    assert violations == []
