from __future__ import annotations

import re
from pathlib import Path


EXPECTED_RELEASE_ASSETS = [
    "dist/*",
    "artifacts/usage-guide/oodocs-user-guide.pdf",
    "artifacts/api/oodocs-api.pdf",
]


def _release_asset_blocks(workflow: str) -> list[list[str]]:
    blocks = re.findall(r"          files: \|\n((?:            .+\n)+)", workflow)
    return [
        [line.strip() for line in block.splitlines() if line.strip()]
        for block in blocks
    ]


def test_release_workflow_uploads_curated_assets_only() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "python -m oodocs apidoc check ." in workflow
    assert "--config pyproject.toml" in workflow
    assert "python examples/usage_guide_example/main.py --outputs pdf" in workflow
    assert "output_formats=(\"pdf\",)" in workflow
    assert "sidecars=False" in workflow
    assert "artifacts/api/oodocs-api.pdf" in workflow

    asset_blocks = _release_asset_blocks(workflow)
    assert len(asset_blocks) == 2
    assert all(block == EXPECTED_RELEASE_ASSETS for block in asset_blocks)

    assert "python examples/native_benchmark_report/main.py" not in workflow
    assert "python examples/api_objects_example/main.py" not in workflow
    assert "python examples/style_cleanup_smoke/main.py" not in workflow
    assert "python examples/template_presets/build_all.py" not in workflow
    assert "python examples/project_metadata_report/main.py" not in workflow
    assert "python examples/cli_manual_example/main.py" not in workflow
    assert "python examples/config_reference_example/main.py" not in workflow
    assert "python examples/validation_gate_report/main.py" not in workflow
    assert "python examples/conformance_matrix_report/main.py" not in workflow

    assert "--save-json" not in workflow
    assert "--save-csv" not in workflow
    assert "artifacts/api-objects-example/*" not in workflow
    assert "artifacts/api/*" not in workflow
    assert ".docx" not in "\n".join(sum(asset_blocks, []))
    assert ".html" not in "\n".join(sum(asset_blocks, []))
    assert ".json" not in "\n".join(sum(asset_blocks, []))
    assert ".csv" not in "\n".join(sum(asset_blocks, []))
    assert "artifacts/evidence/" not in workflow
    assert "feature-coverage.csv" not in workflow
    assert "reproducibility-manifest.json" not in workflow
