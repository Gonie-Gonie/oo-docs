from __future__ import annotations

from pathlib import Path

from oodocs.apidoc import ApiSnapshot, collect_api, diff_api
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
    assert isinstance(diff.to_summary_table(), Table)
