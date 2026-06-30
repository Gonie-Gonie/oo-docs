from __future__ import annotations

from pathlib import Path

from apidoc_samples import write_mixed_docstring_repo
from example_regression import (
    assert_docx_structure,
    assert_html_internal_links_resolve,
    assert_pdf_text_and_pages,
    assert_rendered_bundle,
)
from oodocs.apidoc import ApiDiffResult, ApiDocstringParser, ApiSnapshot, collect_api, diff_api
from oodocs.components.blocks import Chapter
from oodocs.components.media import Table


def _write_package(root: Path, body: str) -> Path:
    package_dir = root / "diffpkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text(body, encoding="utf-8")
    return package_dir


def test_apidoc_diff_detects_added_and_changed_api(tmp_path) -> None:
    base = _write_package(
        tmp_path / "base",
        'def run(path: str) -> str:\n    """Run task."""\n    return path\n',
    )
    head = _write_package(
        tmp_path / "head",
        'def run(path: str, force: bool = False) -> str:\n'
        '    """Run task with force."""\n'
        "    return path\n\n"
        'def added() -> None:\n    """Added function."""\n',
    )

    diff = diff_api(
        ApiSnapshot.from_package(collect_api(base, public_policy="underscore")),
        ApiSnapshot.from_package(collect_api(head, public_policy="underscore")),
    )

    assert diff.added
    assert diff.changed_signatures
    assert not diff.ok
    assert diff.errors
    assert diff.infos
    assert ApiDiffResult.from_json(diff.to_json()).changed_signatures
    assert "breaking" in diff.format_text()
    assert isinstance(diff.to_table(), Table)
    assert isinstance(diff.to_summary_table(), Table)
    assert isinstance(diff.to_chapter(), Chapter)


def test_apidoc_diff_renders_mixed_repo_auto_parser_evidence(tmp_path) -> None:
    base_repo = write_mixed_docstring_repo(tmp_path / "base")
    head_repo = write_mixed_docstring_repo(tmp_path / "head")
    head_init = head_repo / "src" / "mixedpkg" / "__init__.py"
    head_core = head_repo / "src" / "mixedpkg" / "core.py"
    head_init.write_text(
        head_init.read_text(encoding="utf-8").replace(
            "from .core import Client, connect, stream",
            "from .core import Client, connect, ping, stream",
        ).replace(
            '__all__ = ["Client", "connect", "stream"]',
            '__all__ = ["Client", "connect", "ping", "stream"]',
        ),
        encoding="utf-8",
    )
    head_core.write_text(
        head_core.read_text(encoding="utf-8").replace(
            "def connect(self, timeout: float = 1.0) -> bool:",
            "def connect(self, timeout: float = 2.0) -> bool:",
        ).replace(
            "Connect to the configured endpoint.",
            "Connect to the configured endpoint with retries.",
        ).replace(
            "Timeout in seconds.",
            "Timeout in seconds before retry.",
            1,
        )
        + '''

def ping(endpoint: str, retries: int = 1) -> bool:
    """Ping an endpoint.

    Args:
        endpoint: Base endpoint URL.
        retries: Retry count.

    Returns:
        bool: Whether the endpoint responded.
    """

    return bool(endpoint) and retries >= 0
''',
        encoding="utf-8",
    )

    parser = ApiDocstringParser.auto()
    base = collect_api(
        base_repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=parser,
    )
    head = collect_api(
        head_repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=parser,
    )
    diff = diff_api(ApiSnapshot.from_package(base), ApiSnapshot.from_package(head))
    diff_json = diff.save_json(tmp_path / "mixed-api-diff.json")
    readback = ApiDiffResult.load_json(diff_json)
    outputs = readback.to_document(title="Mixed API Change Report").save_all(
        tmp_path / "mixed-api-diff",
        stem="mixed-api-diff",
        formats=("docx", "pdf", "html"),
    )

    added_names = {obj.qualname for obj in readback.added}
    changed_default_names = {base_obj.qualname for base_obj, _ in readback.changed_defaults}
    changed_docstring_names = {base_obj.qualname for base_obj, _ in readback.changed_docstrings}

    assert "mixedpkg.ping" in added_names
    assert "mixedpkg.core.ping" in added_names
    assert "mixedpkg.Client.connect" in changed_default_names
    assert "mixedpkg.core.Client.connect" in changed_default_names
    assert "mixedpkg.Client.connect" in changed_docstring_names
    assert "mixedpkg.core.Client.connect" in changed_docstring_names
    assert readback.coverage_delta["head_public_object_count"] > readback.coverage_delta["base_public_object_count"]
    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "Mixed API Change Report",
            "1 Summary",
            "2 Coverage Delta",
            "3 Added API",
            "4 Changed Signatures",
            "5 Changed Defaults",
            "6 Changed Docstrings",
        ),
        min_tables=6,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "Mixed API Change Report",
            "mixedpkg.ping",
            "mixedpkg.Client.connect",
        ),
        min_pages=1,
    )
    assert_html_internal_links_resolve(
        outputs["html"],
        required_text=(
            "Mixed API Change Report",
            "mixedpkg.ping",
            "mixedpkg.Client.connect",
            "Coverage Delta",
        ),
    )
