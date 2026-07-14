from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import oodocs
import oodocs.integrations as integrations


pytestmark = pytest.mark.contracts


def test_import_oodocs_does_not_eagerly_import_optional_integrations() -> None:
    script = (
        "import json, sys, oodocs; "
        "print(json.dumps(sorted(name for name in sys.modules "
        "if name.split('.')[0] in {'yaml','pandas','pint','pydantic','bibtexparser'})))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "[]"


def test_integration_collectors_stay_out_of_top_level_namespace() -> None:
    assert integrations.__all__ == []
    assert not hasattr(oodocs, "collect_pyproject_info")
    assert not hasattr(oodocs, "collect_github_actions_workflow")


def test_optional_dependency_extras_match_integration_boundaries() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = project["project"]["optional-dependencies"]

    assert any(requirement.lower().startswith("bibtexparser") for requirement in extras["bibtex"])
    assert any(requirement.lower().startswith("pyyaml") for requirement in extras["integrations"])
    assert any(requirement.lower().startswith("pydantic") for requirement in extras["integrations"])
    assert extras["engineering"] == []
    assert any(requirement.lower().startswith("pint") for requirement in extras["pint"])
    assert any(requirement.lower().startswith("sympy") for requirement in extras["sympy"])
