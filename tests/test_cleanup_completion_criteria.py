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
