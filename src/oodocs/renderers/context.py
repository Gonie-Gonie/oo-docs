"""Renderer context objects shared with block-level render dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oodocs.layout.indexing import RenderIndex
from oodocs.layout.theme import Theme
from oodocs.settings import DocumentSettings


@dataclass(slots=True)
class DocxRenderContext:
    """Context needed while rendering blocks into DOCX.

    Attributes:
        theme: Resolved theme used for renderer-neutral style decisions.
        render_index: Precomputed numbering, anchors, and lookup metadata.
        settings: Document settings that affect page and output behavior.
        unit: Preferred length unit for component measurements.
        word_document: Active ``python-docx`` document object.
        in_box: Whether the current render call is inside a styled box.
    """

    theme: Theme
    render_index: RenderIndex
    settings: DocumentSettings
    unit: str
    word_document: Any
    in_box: bool = False


@dataclass(slots=True)
class PdfRenderContext:
    """Context needed while rendering blocks into PDF.

    Attributes:
        theme: Resolved theme used for renderer-neutral style decisions.
        render_index: Precomputed numbering, anchors, and lookup metadata.
        settings: Document settings that affect page and output behavior.
        unit: Preferred length unit for component measurements.
        styles: Active ReportLab stylesheet.
        in_box: Whether the current render call is inside a styled box.
    """

    theme: Theme
    render_index: RenderIndex
    settings: DocumentSettings
    unit: str
    styles: Any
    in_box: bool = False


@dataclass(slots=True)
class HtmlRenderContext:
    """Context needed while rendering blocks into HTML.

    Attributes:
        theme: Resolved theme used for renderer-neutral style decisions.
        render_index: Precomputed numbering, anchors, and lookup metadata.
        settings: Document settings that affect page and output behavior.
        unit: Preferred length unit for component measurements.
        in_box: Whether the current render call is inside a styled box.
    """

    theme: Theme
    render_index: RenderIndex
    settings: DocumentSettings
    unit: str
    in_box: bool = False
