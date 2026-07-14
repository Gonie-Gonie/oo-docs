from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path


LOCAL_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:\b[A-Za-z]:[\\/]+Users[\\/]|/home/|/Users/)"
)
WINDOWS_DRIVE_PATH_PATTERN = re.compile(r"\b[A-Za-z]:[\\/]")
TRACKED_DOCUMENTATION_PATHS = ("README.md", "README-PYPI.md", "docs", "examples")
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


def _assert_phrases(path: str, phrases: tuple[str, ...]) -> None:
    normalized = " ".join(Path(path).read_text(encoding="utf-8").split())
    for phrase in phrases:
        assert phrase in normalized


def test_readme_is_a_concise_entry_point_with_a_runnable_example() -> None:
    readme = _readme()
    nonblank_lines = [line for line in readme.splitlines() if line.strip()]
    quick_start = readme.split("## Quick Start", 1)[1].split("## Import Map", 1)[0]
    block = _python_blocks(quick_start)[0]
    module = ast.parse(block)
    imports = [
        alias.name
        for node in module.body
        if isinstance(node, ast.ImportFrom) and node.module == "oodocs"
        for alias in node.names
    ]

    assert 0 < len(imports) <= 12
    assert imports == ["Chapter", "Document", "Paragraph", "Section"]
    assert "document.save(\"artifacts/report.docx\")" in block
    assert "document.save(\"artifacts/report.pdf\")" in block
    assert "document.save(\"artifacts/report.html\")" in block
    assert len(nonblank_lines) <= 150
    assert "Common translations:" not in readme
    assert "## Features" not in readme


def test_readme_import_map_routes_core_domains_and_integrations() -> None:
    readme = _readme()
    import_map = readme.split("## Import Map", 1)[1].split("## Command Line", 1)[0]

    for phrase in (
        "`oodocs`",
        "`CoverPage`",
        "`FrontMatter`",
        "`MainMatter`",
        "`BackMatter`",
        "`DescriptionItem`",
        "`DescriptionList`",
        "`oodocs.schema`",
        "`FieldSpec`",
        "`SchemaSpec`",
        "`SchemaCatalog`",
        "`oodocs.clidoc`",
        "`CliApplication`",
        "`CliCommand`",
        "`CliOption`",
        "`oodocs.engineering`",
        "`NumberFormat`",
        "`Quantity`",
        "`oodocs.evidence`",
        "`EvidenceItem`",
        "`EvidenceReport`",
        "`EvidenceBundle`",
        "`oodocs.suite`",
        "`DocumentSuite`",
        "`oodocs.integrations.*`",
        "Integration APIs are deliberately not re-exported from top-level `oodocs`.",
    ):
        assert phrase in import_map


def test_readme_points_to_canonical_references_and_short_workflow_sections() -> None:
    readme = _readme()
    for heading in (
        "## Install",
        "## Quick Start",
        "## Import Map",
        "## Command Line",
        "## Examples",
        "## Development",
        "## Releases",
    ):
        assert heading in readme

    for path in (
        "docs/reference/document-matter.md",
        "docs/reference/cover-page.md",
        "docs/reference/references-and-links.md",
        "docs/reference/description-list.md",
        "docs/reference/schema-documentation.md",
        "docs/reference/cli-documentation.md",
        "docs/reference/equation-numbering.md",
        "docs/reference/quantity-formatting.md",
        "docs/reference/document-suite.md",
        "docs/reference/integrations.md",
        "docs/reference/evidence-report.md",
    ):
        assert path in readme

    assert "reference-support.md" not in readme
    assert "hyperref-support.md" not in readme


def test_reference_docs_are_consolidated() -> None:
    assert Path("docs/reference/references-and-links.md").is_file()
    assert not Path("docs/reference/reference-support.md").exists()
    assert not Path("docs/reference/hyperref-support.md").exists()


def test_table_media_support_reference_documents_media_api_policy() -> None:
    _assert_phrases(
        "docs/reference/table-media-support.md",
        (
            "advanced column layout, PDF-only page insertion, and table overflow policy",
            "`Table(headers, rows)`",
            "`Table.from_records(records, columns=...)`",
            "`ColumnSpec(key=..., header=..., visible=False)`",
            "`Table.from_dataframe(data, columns=...)`",
            "`Table.from_csv(...)` or `Table.from_tsv(...)`",
            "`ColumnSpec(width=...)` or `ColumnSpec(flex=...)` from `oodocs.media`",
            "`TableOverflowPolicy(action=\"allow\")` from `oodocs.media`",
            "Do not pass both `columns` and `column_widths`",
            "Use `PdfPages(...)` from `oodocs.pdf`",
            "`pdf-pages-non-pdf-output`",
            "`ImageData.savefig(...)` is a compatibility adapter",
        ),
    )


def test_math_and_equation_references_split_parser_and_numbering_policy() -> None:
    _assert_phrases(
        "docs/reference/math-support.md",
        (
            "`Equation.aligned(...)`",
            "`Equation.cases(...)`",
            "`equation_from_sympy(...)` from `oodocs.integrations.sympy`",
            "`aligned`, `align`, `split`, and `multline` environments",
            "`matrix`, `pmatrix`, `bmatrix`, `array` environments",
            "`unsupported-latex-command` warnings",
            "[Equation numbering and aligned equations](equation-numbering.md)",
        ),
    )
    _assert_phrases(
        "docs/reference/equation-numbering.md",
        (
            "`Equation(numbered=True)` is the default",
            "`Equation(numbered=False)` does not consume a number",
            "`Equation.aligned(...)` and `Equation.cases(...)` are the canonical authoring",
            "`AlignedEquation(...)` and `CasesEquation(...)` classes remain available from `oodocs.equations`",
            "Use `EquationLine` when a row in an aligned derivation needs its own number",
            "`AlignedEquation.numbering` accepts exactly three values",
            "`\"group\"`",
            "`\"each\"`",
            "`\"none\"`",
            "`CounterPolicy` applies a counter style, restart scope, and output template",
        ),
    )
    math_support = Path("docs/reference/math-support.md").read_text(encoding="utf-8")
    assert "`Equation(numbered=True)`" not in math_support
    assert "Use `EquationLine`" not in math_support
    assert "`CounterPolicy`" not in math_support


def test_chemistry_support_reference_documents_mhchem_policy() -> None:
    _assert_phrases(
        "docs/reference/chemistry-support.md",
        (
            "OODocs provides mhchem-inspired helpers",
            "`oodocs.chemistry` namespace",
            "`chemical_formula(...)` or `ChemicalFormula(...)`",
            "`ce(...)`",
            "`ReactionEquation(...)`",
            "Renders numeric suffixes as subscripts and charges as superscripts.",
            "Unicode subscript digits normalize to ordinary subscript runs.",
            "Unicode superscript digits and signs normalize to superscript runs.",
            "full mhchem grammar",
        ),
    )


def test_header_footer_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/header-footer-support.md",
        (
            "common `fancyhdr` and `scrlayer-scrpage` running header and footer needs",
            "`Theme(header_footer=HeaderFooterDefaults(...))`",
            "`PageNumberDefaults(show_page_numbers=True)`",
            "`different_first_page=True`",
            "`different_odd_even_pages=True`",
            "DOCX uses section header/footer parts",
            "PDF draws header and footer text in the page callback",
            "HTML emits a sticky/fixed header-footer layer with print CSS",
        ),
    )


def test_page_overlay_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/page-overlay-support.md",
        (
            "common `eso-pic`, `background`, and `wallpaper` page decoration needs",
            "`Shape.rect(...)`, `Shape.ellipse(...)`, or `Shape.line(...)`",
            "`DocumentSettings(overlays=[...])`",
            "`PageItemScope.all()`, `.cover()`, `.front()`, `.main()`, or `.pages(...)`",
            "`page-item-scope-static-output`",
            "cover-only overlays",
        ),
    )


def test_footnote_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/footnote-support.md",
        (
            "common `footmisc` and `manyfoot` authoring needs",
            "`footnote(\"term\", \"note\")`",
            "`Footnote.annotated(\"term\", \"note\")`",
            "`Theme(footnotes=FootnoteDefaults(...))`",
            "Custom streams such as `symbols` or `review` have independent counters.",
            "`docx-footnote-stream-generated-list`",
            "Page-bottom placement remains renderer-dependent",
        ),
    )


def test_review_annotation_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/review-annotation-support.md",
        (
            "common `marginnote` and `todonotes` authoring needs",
            "helpers in `oodocs.review`",
            "`todo(\"Verify units.\", owner=\"QA\")`",
            "`margin_note(\"Keep this beside the claim.\", side=\"left\")`",
            "`ListOfComments(\"Collected Review Notes\")`",
            "`margin-note-renderer-fallback`",
            "TODO annotations use the comment workflow across DOCX, PDF, and HTML.",
        ),
    )


def test_template_preset_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/template-preset-support.md",
        (
            "common `article`, `report`, `book`, and KOMA-Script class needs",
            "The presets create normal `Document` objects",
            "`JournalArticleTemplate(...)`",
            "`TechnicalReportTemplate(...)`",
            "`SoftwareManualTemplate(...)`",
            "`BookTemplate(...)`",
            "`CoverPagePreset.accented(...)` or `CoverPagePreset.centered_logo(...)`",
            "document classes as content presets",
            "`examples/template_presets/`",
        ),
    )


def test_locale_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/locale-support.md",
        (
            "common `babel` and `polyglossia` document-language needs",
            "`Theme.from_locale(\"ko-KR\")`",
            "`LocaleDefaults.from_locale(\"ko-KR\")`",
            "HTML `lang` and DOCX language settings",
            "`theme.pdf_font_fallback_guide()`",
            "Hyphenation and script shaping remain renderer-dependent.",
        ),
    )


def test_glossary_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/glossary-support.md",
        (
            "common `glossaries`, `acronym`, and `nomencl` authoring needs",
            "`Glossary(...)`",
            "`glossary.term(key, definition, term=...)`",
            "`glossary.acronym(key, long, short=...)`",
            "acronyms expand on first use and use short form later",
            "`duplicate-glossary-key` validation error",
            "`empty-glossary-list` warning",
        ),
    )


def test_list_support_reference_documents_policy() -> None:
    _assert_phrases(
        "docs/reference/list-support.md",
        (
            "common `enumitem` list authoring needs",
            "`BulletList(...)`",
            "`NumberedList(...)`",
            "`NumberedList(..., resume_from=previous)`",
            "`start` and `resume_from` are mutually exclusive.",
            "`StyleSheet.register_list(name, ListStyle(...))`",
            "Nested lists inherit the surrounding renderer context",
        ),
    )


def test_references_and_links_documents_reference_and_hyperlink_policy() -> None:
    _assert_phrases(
        "docs/reference/references-and-links.md",
        (
            "common `cleveref`, `varioref`, and `hyperref` authoring needs",
            "`ref(obj)` or `obj.ref()`",
            "`refs([a, b])`",
            "`ref_range(a, b)`",
            "`ReferenceFormat(...)`",
            "`bracket_ref(obj)` or `paren_ref(obj)`",
            "`page_ref(obj)`",
            "`obj.link(\"label\")`",
            "`link(target, label)`",
            "`url(target, breakable=True)`",
            "`Hyperlink.internal_anchor(...)`",
            "`page-aware-reference-degrades`",
            "`missing-object-link-target`",
            "`unsupported-object-link-target`",
            "`duplicate-anchor`",
            "`plural_label=...`",
            "`range_separator`",
            "Page-aware references are intentionally treated as a degrade path",
            "`DocumentSettings(metadata=DocumentMetadata(...))`",
            "`Theme(links=LinkDefaults(TextStyle(...)))`",
            "PDF info dictionary",
            "`<title>` and meta tags",
            "PDF outline/bookmarks",
            "Broken internal link validation is a preflight error",
            "## URL line-break policy",
            "`url(target, label=None, breakable=True)`",
            "zero-width soft break points",
            "`href` attribute",
            "`overly-long-url`",
        ),
    )


def test_citation_support_reference_documents_bibtex_policy() -> None:
    _assert_phrases(
        "docs/reference/citation-support.md",
        (
            "common `natbib`, `biblatex`, and BibTeX authoring needs",
            "`CitationLibrary(...)`",
            "Requires unique non-empty keys and raises on duplicates.",
            "`cite(\"key\")`, `CitationSource.cite()`, or `CitationLibrary.cite(\"key\")`",
            "`ListOfReferences()`",
            "`ReferenceList` and `ReferencesPage` are not separate public aliases.",
            "`CitationLibrary.from_bibtex(...)` or `.from_bibtex_file(...)`",
            "BibLaTeX-only fields",
            "CSL-level compatibility is intentionally outside",
            "`CitationDefaults(reference_sort=...)` or `ListOfReferences(sort=...)`",
        ),
    )


def test_public_api_policy_doc_defines_tiers_and_guards() -> None:
    _assert_phrases(
        "docs/reference/public-api-policy.md",
        (
            "src/oodocs/public_api.py",
            "Tier 1 core",
            "Tier 2 domain",
            "Tier 3 internal",
            "TOP_LEVEL_EXPORT_LIMIT",
            "TOP_LEVEL_SYMBOL_TIERS",
            "top-level `oodocs` must not export preset names.",
            "README Quick Start examples use Tier 1 imports only.",
            "Advanced examples import their domain namespace explicitly.",
            "Template preset docs describe reusable document skeletons",
            "ordinary examples describe runnable direct-composition workflows",
        ),
    )


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
