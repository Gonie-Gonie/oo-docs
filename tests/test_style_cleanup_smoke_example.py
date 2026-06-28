from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from example_regression import assert_html_internal_links_resolve, assert_rendered_bundle


def _load_style_cleanup_smoke_example():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "style_cleanup_smoke"
        / "main.py"
    )
    spec = importlib.util.spec_from_file_location("style_cleanup_smoke_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    return example


def test_style_cleanup_smoke_example_builds_outputs(tmp_path: Path) -> None:
    example = _load_style_cleanup_smoke_example()
    document = example.build_document()
    outputs = example.build(tmp_path)

    assert document.validate().ok
    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert outputs.stylesheet_json.exists()
    stylesheet_payload = json.loads(outputs.stylesheet_json.read_text(encoding="utf-8"))
    assert "paragraph" in stylesheet_payload
    assert "body.compact" in stylesheet_payload["paragraph"]
    assert example.load_stylesheet_sidecar(outputs.stylesheet_json).to_dict() == stylesheet_payload
    html = outputs["html"].read_text(encoding="utf-8")
    assert "Custom Styles Example" in html
    assert "Requirement:" in html
    assert "Schema-style table." in html
    assert "Named styles replace repeated visual kwargs with reusable style identifiers." in html
    assert_html_internal_links_resolve(outputs["html"])


def test_style_cleanup_smoke_example_supports_common_cli(tmp_path: Path, capsys) -> None:
    example = _load_style_cleanup_smoke_example()
    output_dir = tmp_path / "cli"

    outputs = example.build(output_dir / "programmatic", output_formats=("html",))
    assert set(outputs.keys()) == {"html"}
    assert outputs["html"].exists()

    example.main(
        [
            "--output-dir",
            str(output_dir),
            "--outputs",
            "html",
            "--quiet",
        ]
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (output_dir / "style-cleanup-smoke.html").exists()
    assert (output_dir / "style-cleanup-smoke-stylesheet.json").exists()
