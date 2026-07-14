from __future__ import annotations

import subprocess
import sys

import pytest

import oodocs
import oodocs.integrations as integrations


pytestmark = pytest.mark.contracts


def test_import_oodocs_does_not_eagerly_import_optional_integrations() -> None:
    script = (
        "import json, sys, oodocs; "
        "print(json.dumps(sorted(name for name in sys.modules "
        "if name.split('.')[0] in {'yaml','pandas','pint','bibtexparser'})))"
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
