"""Renderer context objects shared with block-level render dispatch."""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from typing import Any

from oodocs.layout.indexing import RenderIndex
from oodocs.styles import RunInTitleStyle, StyleSheet, Theme
from oodocs.settings import DocumentSettings, PageLayout


def _settings_with_page_layout(
    settings: DocumentSettings,
    page_layout: PageLayout,
) -> DocumentSettings:
    """Return settings with page geometry replaced for scoped rendering."""

    if settings.page_layout == page_layout:
        return settings
    scoped = copy(settings)
    scoped.page_layout = page_layout
    scoped.page_size = page_layout.page_size
    scoped.page_margins = page_layout.page_margins
    return scoped


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
        run_in_title_style: Run-in title style inherited from the
            current section, if any.
    """

    theme: Theme
    render_index: RenderIndex
    settings: DocumentSettings
    unit: str
    word_document: Any
    in_box: bool = False
    run_in_title_style: RunInTitleStyle | None = None

    @property
    def stylesheet(self) -> StyleSheet:
        """Return the theme stylesheet."""

        return self.theme.stylesheet


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
        run_in_title_style: Run-in title style inherited from the
            current section, if any.
    """

    theme: Theme
    render_index: RenderIndex
    settings: DocumentSettings
    unit: str
    styles: Any
    in_box: bool = False
    run_in_title_style: RunInTitleStyle | None = None

    @property
    def stylesheet(self) -> StyleSheet:
        """Return the theme stylesheet."""

        return self.theme.stylesheet


@dataclass(slots=True)
class HtmlRenderContext:
    """Context needed while rendering blocks into HTML.

    Attributes:
        theme: Resolved theme used for renderer-neutral style decisions.
        render_index: Precomputed numbering, anchors, and lookup metadata.
        settings: Document settings that affect page and output behavior.
        unit: Preferred length unit for component measurements.
        in_box: Whether the current render call is inside a styled box.
        run_in_title_style: Run-in title style inherited from the
            current section, if any.
    """

    theme: Theme
    render_index: RenderIndex
    settings: DocumentSettings
    unit: str
    in_box: bool = False
    run_in_title_style: RunInTitleStyle | None = None

    @property
    def stylesheet(self) -> StyleSheet:
        """Return the theme stylesheet."""

        return self.theme.stylesheet
