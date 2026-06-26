from __future__ import annotations

import json
from base64 import b64encode

import pytest

from oodocs import Document, ImportPolicyError, ImportResult, NotebookImportOptions
from oodocs.cli import main
from oodocs.importers.markdown import parse_markdown, parse_markdown_file
from oodocs.importers.notebook import parse_notebook

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_parse_markdown_diagnostics_preserves_default_return() -> None:
    blocks = parse_markdown("![Remote](https://example.com/plot.png)")
    result = parse_markdown(
        "![Remote](https://example.com/plot.png)",
        diagnostics=True,
    )

    assert isinstance(blocks, list)
    assert isinstance(result, ImportResult)
    assert len(result.blocks) == len(blocks)
    assert result.issues[0].code == "remote-image-lossy"

    with pytest.raises(ImportPolicyError):
        parse_markdown(
            "![Remote](https://example.com/plot.png)",
            import_policy="fail-on-lossy",
        )


def test_parse_markdown_file_records_source_for_raw_html(tmp_path) -> None:
    markdown_path = tmp_path / "raw.md"
    markdown_path.write_text("<div>raw</div>\n", encoding="utf-8")

    result = parse_markdown_file(
        markdown_path,
        diagnostics=True,
        import_policy="record-lossy",
    )

    assert isinstance(result, ImportResult)
    assert result.issues[0].code == "raw-html-unsupported"
    assert result.issues[0].source == str(markdown_path.resolve())
    assert result.issues[0].line_number == 1


def test_parse_notebook_options_filter_truncate_and_caption_outputs() -> None:
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"language_info": {"name": "python"}},
        "cells": [
            {
                "cell_type": "code",
                "metadata": {"tags": ["skip-report"]},
                "source": "print('skip')",
                "outputs": [],
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": "display(data)",
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": "one\ntwo\nthree\n",
                    },
                    {
                        "output_type": "display_data",
                        "data": {
                            "image/png": b64encode(_TINY_PNG).decode("ascii"),
                        },
                        "metadata": {},
                    },
                    {
                        "output_type": "display_data",
                        "data": {"application/vnd.custom": "payload"},
                        "metadata": {},
                    },
                ],
            },
        ],
    }

    result = parse_notebook(
        notebook,
        options=NotebookImportOptions(
            exclude_tags=("skip-report",),
            max_output_lines=2,
            image_caption="Output image from cell {cell_index}",
        ),
        diagnostics=True,
    )

    assert isinstance(result, ImportResult)
    assert [issue.code for issue in result.issues] == [
        "notebook-cell-excluded",
        "notebook-output-truncated",
        "unsupported-notebook-mime-type",
    ]
    assert any(getattr(block, "caption", None) is not None for block in result.blocks)


def test_document_from_notebook_accepts_options() -> None:
    document = Document.from_notebook(
        {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {"title": "Notebook"},
            "cells": [
                {
                    "cell_type": "code",
                    "metadata": {"tags": ["hide"]},
                    "source": "print('hidden')",
                    "outputs": [],
                }
            ],
        },
        options=NotebookImportOptions(exclude_tags=("hide",)),
    )

    assert document.title == "Notebook"
    assert document.body.children == []


def test_cli_build_can_show_and_fail_on_import_warnings(tmp_path, capsys) -> None:
    markdown_path = tmp_path / "remote.md"
    markdown_path.write_text("# Remote\n\n![Plot](https://example.com/plot.png)\n", encoding="utf-8")

    exit_code = main(
        [
            "build",
            str(markdown_path),
            "--outputs",
            "html",
            "--out",
            str(tmp_path / "out"),
            "--show-import-warnings",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "remote-image-lossy" in captured.out

    fail_exit_code = main(
        [
            "build",
            str(markdown_path),
            "--outputs",
            "html",
            "--out",
            str(tmp_path / "fail"),
            "--fail-on-import-warning",
        ]
    )
    captured = capsys.readouterr()
    assert fail_exit_code == 2
    assert "remote-image-lossy" in captured.err
