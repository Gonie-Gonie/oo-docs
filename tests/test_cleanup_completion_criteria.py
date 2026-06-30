from __future__ import annotations

import ast
import re
from pathlib import Path


def _readme() -> str:
    return Path("README.md").read_text(encoding="utf-8")


def _python_blocks(markdown: str) -> list[str]:
    return re.findall(r"```python\n(.*?)\n```", markdown, flags=re.DOTALL)


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


def test_readme_recommended_advanced_imports_use_domain_namespaces() -> None:
    readme = _readme()
    expected_lines = {
        "from oodocs import Chapter, Document, Paragraph, Table, ref",
        "from oodocs.apidoc import collect_api",
        "from oodocs.engineering import Algorithm",
        "from oodocs.positioning import Shape, TextBox",
        "from oodocs.review import MarginNote, Todo",
    }

    for line in expected_lines:
        assert line in readme
