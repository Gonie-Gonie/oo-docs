from __future__ import annotations

import json
from pathlib import Path

from oodocs import Document, Figure, Table
from oodocs.cli import main


def test_validation_result_serializes_to_dict_and_json() -> None:
    document = Document("Broken", Figure("missing.png", caption="Missing."))

    result = document.validate(formats=("pdf",))
    payload = result.to_dict(formats=("pdf",))
    parsed = json.loads(result.to_json(formats=("pdf",), indent=None))

    assert payload["ok"] is False
    assert payload["errors"] == 1
    assert payload["warnings"] == 0
    assert payload["issues"][0]["code"] == "missing-image-file"
    assert payload["issues"][0]["formats"] == ["docx", "pdf", "html"]
    assert parsed == payload


def test_cli_validate_can_emit_json(tmp_path: Path, capsys) -> None:
    script_path = tmp_path / "broken.py"
    script_path.write_text(
        "\n".join(
            [
                "from oodocs import Document, Figure",
                "",
                "def build_document():",
                "    return Document('Broken', Figure('missing.png', caption='Missing.'))",
                "",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        ["validate", str(script_path), "--outputs", "pdf", "--report-format", "json"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["issues"][0]["code"] == "missing-image-file"
    assert captured.err == ""


def test_cli_build_can_fail_on_validation_warning(tmp_path: Path, capsys) -> None:
    script_path = tmp_path / "warning.py"
    script_path.write_text(
        "\n".join(
            [
                "from oodocs import Document, Table",
                "",
                "def build_document():",
                "    return Document('Warning', Table(['A'], [['B']]))",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "build",
            str(script_path),
            "--outputs",
            "html",
            "--out",
            str(output_dir),
            "--fail-on-warning",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing-table-caption" in captured.err
    assert not (output_dir / "warning.html").exists()


def test_cli_traceback_prints_full_debug_output(tmp_path: Path, capsys) -> None:
    exit_code = main(["build", str(tmp_path / "missing.py"), "--traceback"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Traceback" in captured.err
    assert "FileNotFoundError" in captured.err
