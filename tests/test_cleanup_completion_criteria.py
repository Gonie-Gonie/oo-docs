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

    for phrase in (
        "`Equation(numbered=True)` is the default",
        "`Equation(numbered=False)` does not consume a number",
        "`Equation.aligned(...)`",
        "`Equation.cases(...)`",
        "`Equation.from_sympy(...)`",
        "`aligned`, `align`, `split`, and `multline` environments",
        "`matrix`, `pmatrix`, `bmatrix`, `array` environments",
        "`unsupported-latex-command` warnings",
    ):
        assert phrase in reference


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
    guide = Path("docs/how-to/insert-api-sections.md").read_text(encoding="utf-8")
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
