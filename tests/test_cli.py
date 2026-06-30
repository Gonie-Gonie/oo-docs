from __future__ import annotations

import json
from pathlib import Path

from oodocs.cli import main
from oodocs.workflows import build_source_outputs, validate_source_document


def test_cli_build_markdown_outputs_selected_formats(
    tmp_path: Path,
    capsys,
) -> None:
    markdown_path = tmp_path / "README.md"
    markdown_path.write_text("# CLI Report\n\nBody paragraph.\n", encoding="utf-8")
    output_dir = tmp_path / "artifacts"

    exit_code = main(
        [
            "build",
            str(markdown_path),
            "--outputs",
            "html",
            "--out",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (output_dir / "README.html").exists()
    assert "Wrote html:" in captured.out


def test_cli_build_notebook_to_pdf(tmp_path: Path, capsys) -> None:
    notebook_path = tmp_path / "notebook.ipynb"
    notebook_path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": ["# Notebook Report\n\nImported body."],
                    }
                ],
                "metadata": {"language_info": {"name": "python"}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "pdf"

    exit_code = main(
        [
            "build",
            str(notebook_path),
            "--outputs",
            "pdf",
            "--out",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (output_dir / "notebook.pdf").exists()
    assert "Wrote pdf:" in captured.out


def test_cli_build_source_outputs(tmp_path: Path, capsys) -> None:
    script_path = tmp_path / "report.py"
    script_path.write_text(
        "\n".join(
            [
                "from oodocs import Document, Paragraph",
                "",
                "def build_document():",
                "    return Document('Python Report', Paragraph('Built from Python.'))",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "build"

    exit_code = main(
        [
            "build",
            str(script_path),
            "--out",
            str(output_dir),
            "--outputs",
            "html",
            "--verbose",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (output_dir / "report.html").exists()
    assert "Wrote html:" in captured.out


def test_cli_validate_blocks_invalid_python_document(
    tmp_path: Path,
    capsys,
) -> None:
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

    exit_code = main(["validate", str(script_path), "--outputs", "pdf"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "OODocs validation failed for PDF" in captured.out
    assert "missing-image-file" in captured.out
    assert "PDF" in captured.out


def test_workflow_api_converts_and_validates_sources(tmp_path: Path) -> None:
    markdown_path = tmp_path / "notes.md"
    markdown_path.write_text("# Workflow API\n\nBody paragraph.\n", encoding="utf-8")

    result = validate_source_document(markdown_path, outputs=("html",))
    outputs = build_source_outputs(
        markdown_path,
        tmp_path / "outputs",
        outputs=("html",),
    )

    assert result.ok
    assert outputs["html"] == tmp_path / "outputs" / "notes.html"
    assert outputs["html"].exists()
