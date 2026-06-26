from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_public_api_inventory_matches_snapshot(tmp_path: Path) -> None:
    output_path = tmp_path / "public-api-inventory.json"

    subprocess.run(
        [
            sys.executable,
            "tools/api_surface_inventory.py",
            "--branch",
            "main",
            "--out",
            str(output_path),
        ],
        check=True,
    )

    actual = json.loads(output_path.read_text(encoding="utf-8"))
    expected = json.loads(
        Path("tests/snapshots/public-api-inventory.json").read_text(encoding="utf-8")
    )

    assert actual == expected
