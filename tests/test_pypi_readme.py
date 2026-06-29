from __future__ import annotations

from pathlib import Path
import tomllib


def test_pyproject_uses_pypi_readme_for_long_description() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["readme"] == "README-PYPI.md"


def test_pypi_readme_excludes_repository_operations() -> None:
    readme = Path("README-PYPI.md").read_text(encoding="utf-8")

    assert "# oodocs" in readme
    assert "pip install oodocs" in readme
    assert "## Quick Start" in readme
    assert "## Development" not in readme
    assert "## Releases" not in readme
    assert ".github/workflows" not in readme
    assert "GitHub Release assets" not in readme
    assert "release-notes/" not in readme
    assert "artifacts/usage-guide/" not in readme
