from __future__ import annotations

import json
from base64 import b64encode
from pathlib import Path

import oodocs.importers.notebook as notebook_importer
from oodocs import Document, Figure, ImageData, Table
from oodocs.components.blocks import Chapter, CodeBlock, Paragraph, Section
from oodocs.importers import from_notebook, parse_notebook

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_notebook_importer_exposes_canonical_public_names() -> None:
    assert hasattr(notebook_importer, "from_notebook")
    assert hasattr(notebook_importer, "parse_notebook")
    assert not hasattr(notebook_importer, "from_ipynb")
    assert not hasattr(notebook_importer, "parse_ipynb")
    assert hasattr(Document, "from_notebook")
    assert not hasattr(Document, "from_ipynb")


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


def test_parse_notebook_maps_cells_to_oodocs_blocks() -> None:
    blocks = parse_notebook(_sample_notebook()).blocks

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


def test_from_notebook_uses_first_h1_or_metadata_as_title(tmp_path: Path) -> None:
    notebook = _sample_notebook()
    document = from_notebook(notebook)

    assert document.title == "Notebook Report"
    assert isinstance(document.body.children[0], Paragraph)
    assert isinstance(document.body.children[1], Section)

    explicit = Document.from_notebook(notebook, title="Manual Notebook")
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
    assert Document.from_notebook(metadata_only).title == "Metadata Notebook"

    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text(json.dumps(notebook), encoding="utf-8")
    loaded = Document.from_notebook(notebook_path, include_outputs=False)
    assert loaded.title == "Notebook Report"
    assert all(
        not (isinstance(child, CodeBlock) and child.code == "42")
        for child in loaded.body.children
    )


def test_parse_notebook_can_filter_code_markdown_and_outputs() -> None:
    markdown_only = parse_notebook(
        _sample_notebook(),
        include_code=False,
        include_outputs=False,
        include_raw_cells=False,
    ).blocks

    assert len(markdown_only) == 1
    assert isinstance(markdown_only[0], Chapter)
    assert isinstance(markdown_only[0].children[1], Section)
    assert all(
        not isinstance(child, CodeBlock)
        for child in markdown_only[0].children[1].children
    )


def test_parse_notebook_imports_markdown_and_image_outputs_as_editable_blocks() -> None:
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"language_info": {"name": "python"}},
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": "# Output Report\n\n## Results\n",
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "source": "display(summary)",
                "outputs": [
                    {
                        "output_type": "display_data",
                        "data": {
                            "text/markdown": "| Metric | Value |\n| --- | ---: |\n| score | 0.98 |",
                        },
                        "metadata": {},
                    },
                    {
                        "output_type": "display_data",
                        "data": {
                            "image/png": b64encode(_TINY_PNG).decode("ascii"),
                            "text/plain": "<Figure size 100x100>",
                        },
                        "metadata": {},
                    },
                ],
            },
        ],
    }

    blocks = parse_notebook(notebook).blocks

    chapter = blocks[0]
    assert isinstance(chapter, Chapter)
    results = chapter.children[0]
    assert isinstance(results, Section)
    assert isinstance(results.children[1], Table)
    figure = results.children[2]
    assert isinstance(figure, Figure)
    assert isinstance(figure.image_source, ImageData)
    assert figure.image_source.data == _TINY_PNG
    assert figure.image_format == "png"
