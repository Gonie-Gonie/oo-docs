from __future__ import annotations

import json
from pathlib import Path

import pytest

from oodocs import Document, Figure, Table, ValidationPolicy, ValidationResult
from oodocs.cli import main
from oodocs.validation import DocumentValidationError


def test_validation_result_serializes_to_dict_and_json(tmp_path: Path) -> None:
    document = Document("Broken", Figure("missing.png", caption="Missing."))

    result = document.validate(formats=("pdf",))
    payload = result.to_dict(formats=("pdf",))
    parsed = json.loads(result.to_json(formats=("pdf",), indent=None))

    assert payload["ok"] is False
    assert payload["errors"] == 1
    assert payload["warnings"] == 0
    assert payload["infos"] == 0
    assert payload["issues"][0]["code"] == "missing-image-file"
    assert "source" in payload["issues"][0]
    assert "line_number" in payload["issues"][0]
    assert payload["issues"][0]["formats"] == ["docx", "pdf", "html"]
    assert parsed == payload
    assert result.infos == ()
    assert isinstance(result.to_table(formats=("pdf",)), Table)

    restored = ValidationResult.from_json(result.to_json(formats=("pdf",)))
    assert restored.errors[0].code == "missing-image-file"
    sidecar = result.save_json(tmp_path / "validation.json", formats=("pdf",))
    assert ValidationResult.load_json(sidecar).errors[0].code == "missing-image-file"


def test_validation_policy_blocks_selected_warnings(tmp_path: Path) -> None:
    document = Document("Warning", Table(["A"], [["B"]]))
    result = document.validate()
    policy = ValidationPolicy(
        allow_warnings={"html-toc-page-numbers"},
        deny_warnings={"missing-table-caption"},
        fail_on_unlisted_warnings=True,
    )

    blocking = result.blocking_warnings(policy)
    payload = result.to_dict(policy=policy)
    policy_path = policy.save_json(tmp_path / "policy.json")

    assert [issue.code for issue in blocking] == ["missing-table-caption"]
    assert payload["ok"] is True
    assert payload["blocking_warnings"] == 1
    assert payload["warning_policy"] == policy.to_dict()
    assert ValidationPolicy.load_json(policy_path) == policy
    with pytest.raises(DocumentValidationError) as exc_info:
        document.validate(raise_on_error=True, policy=policy)
    assert [issue.code for issue in exc_info.value.blocking_warnings] == [
        "missing-table-caption"
    ]


def test_validation_policy_fail_on_unlisted_warnings() -> None:
    document = Document("Warning", Table(["A"], [["B"]]))
    result = document.validate()
    allow_policy = ValidationPolicy(allow_warnings={"missing-table-caption"})
    unlisted_policy = ValidationPolicy(fail_on_unlisted_warnings=True)

    assert result.blocking_warnings(allow_policy) == ()
    assert [issue.code for issue in result.blocking_warnings(unlisted_policy)] == [
        "missing-table-caption"
    ]


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


def test_cli_validate_warning_policy_blocks_warnings(tmp_path: Path, capsys) -> None:
    script_path = tmp_path / "warning.py"
    policy_path = tmp_path / "policy.json"
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
    ValidationPolicy(deny_warnings={"missing-table-caption"}).save_json(policy_path)

    exit_code = main(
        [
            "validate",
            str(script_path),
            "--outputs",
            "html",
            "--warning-policy",
            str(policy_path),
            "--report-format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["ok"] is True
    assert payload["blocking_warnings"] == 1
    assert payload["warning_policy"]["deny_warnings"] == ["missing-table-caption"]
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
