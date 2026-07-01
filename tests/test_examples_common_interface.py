from __future__ import annotations

import pytest

pytestmark = pytest.mark.examples

import ast
import importlib.util
import sys
from pathlib import Path


def _load_main_module(example_dir: Path):
    module_path = example_dir / "main.py"
    spec = importlib.util.spec_from_file_location(f"examples.{example_dir.name}.main", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(example_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(example_dir))
    return module


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def test_examples_expose_common_entry_points() -> None:
    examples_dir = Path(__file__).resolve().parents[1] / "examples"
    example_dirs = [
        path
        for path in examples_dir.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    ]

    assert {path.name for path in example_dirs} >= {
        "usage_guide_example",
        "journal_paper_example",
        "native_benchmark_report",
        "release_notes_digest",
        "api_objects_example",
        "style_cleanup_smoke",
        "template_presets",
        "project_metadata_report",
        "cli_manual_example",
        "config_reference_example",
        "validation_gate_report",
        "conformance_matrix_report",
        "review_notes_example",
        "engineering_report_example",
        "page_overlay_example",
    }

    for example_dir in example_dirs:
        assert (example_dir / "README.md").exists(), example_dir.name
        assert (example_dir / "main.py").exists(), example_dir.name
        module = _load_main_module(example_dir)
        assert callable(getattr(module, "build_document", None)), example_dir.name
        assert callable(getattr(module, "build", None)), example_dir.name
        assert callable(getattr(module, "main", None)), example_dir.name


def test_focused_examples_keep_specialized_domains_separate() -> None:
    examples_dir = Path(__file__).resolve().parents[1] / "examples"
    required_domain_by_example = {
        "api_objects_example": "oodocs.apidoc",
        "engineering_report_example": "oodocs.engineering",
        "page_overlay_example": "oodocs.positioning",
        "review_notes_example": "oodocs.review",
    }
    specialized_domains = set(required_domain_by_example.values())

    for example_name, required_domain in required_domain_by_example.items():
        imports = _imported_modules(examples_dir / example_name / "main.py")

        assert required_domain in imports
        assert imports.isdisjoint(specialized_domains - {required_domain}), example_name
