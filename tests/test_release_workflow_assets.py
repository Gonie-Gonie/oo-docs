from __future__ import annotations

from pathlib import Path


def test_release_workflow_uploads_curated_assets_only() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "artifacts/evidence/oodocs-evidence-report.pdf" in workflow
    assert "artifacts/evidence/*" not in workflow
    assert "artifacts/native-benchmark-report/native-python-benchmark.pdf" not in workflow
    assert "feature-coverage.csv" not in workflow
    assert "reproducibility-manifest.json" not in workflow
