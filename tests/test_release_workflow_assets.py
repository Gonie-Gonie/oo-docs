from __future__ import annotations

from pathlib import Path


def test_release_workflow_uploads_curated_assets_only() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "python -m oodocs apidoc check ." in workflow
    assert "--config pyproject.toml" in workflow
    assert "--save-json artifacts/api-objects-example/oodocs-api-coverage.json" in workflow
    assert "--save-csv artifacts/api-objects-example/oodocs-api-coverage.csv" in workflow
    assert "python examples/native_benchmark_report/main.py" in workflow
    assert "python examples/api_objects_example/main.py . --config pyproject.toml" in workflow
    assert "python examples/style_cleanup_smoke/main.py" in workflow
    assert "python examples/template_presets/build_all.py" in workflow
    assert 'ApiHelpBookConfig.from_pyproject(".").save_all(".")' in workflow
    assert "artifacts/api-objects-example/oodocs-api-object-composition.pdf" in workflow
    assert "artifacts/native-benchmark-report/native-python-benchmark.pdf" in workflow
    assert "artifacts/template/journal-article-template.pdf" in workflow
    assert "artifacts/api-objects-example/oodocs-api-object-tree.json" in workflow
    assert "artifacts/api-objects-example/oodocs-api-coverage.json" in workflow
    assert "artifacts/api-objects-example/oodocs-api-coverage.csv" in workflow
    assert "artifacts/api-objects-example/oodocs-api-reference.docx" in workflow
    assert "artifacts/api-objects-example/oodocs-api-reference.pdf" in workflow
    assert "artifacts/api-objects-example/oodocs-api-reference.html" in workflow
    assert "artifacts/api/oodocs-api.docx" in workflow
    assert "artifacts/api/oodocs-api.pdf" in workflow
    assert "artifacts/api/oodocs-api.html" in workflow
    assert "artifacts/api/oodocs-api-object-tree.json" in workflow
    assert "artifacts/api/oodocs-api-coverage.json" in workflow
    assert "artifacts/api/oodocs-api-coverage.csv" in workflow
    assert "artifacts/evidence/oodocs-evidence-report.pdf" in workflow
    assert "artifacts/evidence/*" not in workflow
    assert "artifacts/api-objects-example/*" not in workflow
    assert "artifacts/api/*" not in workflow
    assert "artifacts/style-cleanup-smoke/style-cleanup-smoke.pdf" not in workflow
    assert "feature-coverage.csv" not in workflow
    assert "reproducibility-manifest.json" not in workflow
