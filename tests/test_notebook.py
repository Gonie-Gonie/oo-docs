from __future__ import annotations

import json
from pathlib import Path

from docscriptor import Document, from_ipynb, parse_ipynb
from docscriptor.components.blocks import Chapter, CodeBlock, Paragraph, Section


def _sample_notebook() -> dict[str, object]:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "language_info": {"name": "python"},
            "title": "Metadata Notebook",
        },
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Notebook Report\n", "\n", "Intro with **bold** text."],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": "## Analysis\n\nA table follows.",
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "source": ["value = 41\n", "value + 1\n"],
                "outputs": [
                    {
                        "output_type": "execute_result",
                        "execution_count": 1,
                        "data": {"text/plain": "42"},
                        "metadata": {},
                    }
                ],
            },
            {
                "cell_type": "code",
                "execution_count": 2,
                "metadata": {},
                "source": "print('done')\n",
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": ["done\n"],
                    }
                ],
            },
            {
                "cell_type": "raw",
                "metadata": {},
                "source": "Raw attachment notes.",
            },
        ],
    }


def test_parse_ipynb_maps_cells_to_docscriptor_blocks() -> None:
    blocks = parse_ipynb(_sample_notebook())

    assert len(blocks) == 1
    chapter = blocks[0]
    assert isinstance(chapter, Chapter)
    assert chapter.plain_title() == "Notebook Report"

    intro = chapter.children[0]
    assert isinstance(intro, Paragraph)
    assert intro.plain_text() == "Intro with bold text."
    assert any(fragment.style.bold for fragment in intro.content)

    analysis = chapter.children[1]
    assert isinstance(analysis, Section)
    assert analysis.plain_title() == "Analysis"
    assert [type(child).__name__ for child in analysis.children] == [
        "Paragraph",
        "CodeBlock",
        "CodeBlock",
        "CodeBlock",
        "CodeBlock",
        "CodeBlock",
    ]
    assert analysis.children[1].code == "value = 41\nvalue + 1"
    assert analysis.children[1].language == "python"
    assert analysis.children[2].code == "42"
    assert analysis.children[2].show_language is False
    assert analysis.children[5].code == "Raw attachment notes."


def test_from_ipynb_uses_first_h1_or_metadata_as_title(tmp_path: Path) -> None:
    notebook = _sample_notebook()
    document = from_ipynb(notebook)

    assert document.title == "Notebook Report"
    assert isinstance(document.body.children[0], Paragraph)
    assert isinstance(document.body.children[1], Section)

    explicit = Document.from_ipynb(notebook, title="Manual Notebook")
    assert explicit.title == "Manual Notebook"
    assert isinstance(explicit.body.children[0], Chapter)

    metadata_only = dict(notebook)
    metadata_only["cells"] = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": "No heading here.",
        }
    ]
    assert Document.from_ipynb(metadata_only).title == "Metadata Notebook"

    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text(json.dumps(notebook), encoding="utf-8")
    loaded = Document.from_ipynb(notebook_path, include_outputs=False)
    assert loaded.title == "Notebook Report"
    assert all(
        not (isinstance(child, CodeBlock) and child.code == "42")
        for child in loaded.body.children
    )


def test_parse_ipynb_can_filter_code_markdown_and_outputs() -> None:
    markdown_only = parse_ipynb(
        _sample_notebook(),
        include_code=False,
        include_outputs=False,
        include_raw=False,
    )

    assert len(markdown_only) == 1
    assert isinstance(markdown_only[0], Chapter)
    assert isinstance(markdown_only[0].children[1], Section)
    assert all(
        not isinstance(child, CodeBlock)
        for child in markdown_only[0].children[1].children
    )
