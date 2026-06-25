from __future__ import annotations

from pathlib import Path


def test_release_workflow_uploads_curated_assets_only() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "python -m oodocs apidoc check oodocs" in workflow
    assert "--out-json artifacts/api-objects-example/oodocs-api-coverage.json" in workflow
    assert "--out-csv artifacts/api-objects-example/oodocs-api-coverage.csv" in workflow
    assert "python examples/api_objects_example/main.py" in workflow
    assert "python -m oodocs apidoc build . --config pyproject.toml" in workflow
    assert "artifacts/api-objects-example/oodocs-api-objects.pdf" in workflow
    assert "artifacts/api-objects-example/oodocs-api-objects.json" in workflow
    assert "artifacts/api-objects-example/oodocs-api-coverage.json" in workflow
    assert "artifacts/api-objects-example/oodocs-api-coverage.csv" in workflow
    assert "artifacts/api-objects-example/oodocs-full-api-reference.docx" in workflow
    assert "artifacts/api-objects-example/oodocs-full-api-reference.pdf" in workflow
    assert "artifacts/api-objects-example/oodocs-full-api-reference.html" in workflow
    assert "artifacts/api/oodocs-api.docx" in workflow
    assert "artifacts/api/oodocs-api.pdf" in workflow
    assert "artifacts/api/oodocs-api.html" in workflow
    assert "artifacts/api/oodocs-api.json" in workflow
    assert "artifacts/api/oodocs-api-coverage.json" in workflow
    assert "artifacts/api/oodocs-api-coverage.csv" in workflow
    assert "artifacts/evidence/oodocs-evidence-report.pdf" in workflow
    assert "artifacts/evidence/*" not in workflow
    assert "artifacts/api-objects-example/*" not in workflow
    assert "artifacts/api/*" not in workflow
    assert "artifacts/native-benchmark-report/native-python-benchmark.pdf" not in workflow
    assert "feature-coverage.csv" not in workflow
    assert "reproducibility-manifest.json" not in workflow
