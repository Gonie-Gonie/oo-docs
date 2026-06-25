"""Composable API documentation render helpers."""

from __future__ import annotations

from typing import Sequence

from oodocs.apidoc.blocks import api_objects_to_chapter, api_objects_to_summary_table as _api_objects_to_summary_table
from oodocs.apidoc.coverage import ApiCoverageResult
from oodocs.apidoc.diff import ApiDiffResult
from oodocs.apidoc.model import ApiObject, ApiPackage
from oodocs.apidoc.styles import ApiDocProfile
from oodocs.components.blocks import Chapter, Paragraph
from oodocs.components.generated import TableOfContents
from oodocs.document import Document


def api_package_to_document(
    api: ApiPackage,
    *,
    title: str | None = None,
    profile: str | ApiDocProfile = "reference",
    settings: object | None = None,
    citations: object | None = None,
    include_coverage: bool = True,
    include_modules: bool = True,
) -> Document:
    """Build a complete OODocs document from an API package.

    Args:
        api: API package object.
        title: Optional document title.
        profile: Presentation profile.
        settings: Optional document settings.
        citations: Optional citation library.
        include_coverage: Whether to include a coverage overview chapter.
        include_modules: Whether to include module chapters.

    Returns:
        OODocs document ready for ``save_docx``, ``save_pdf``, ``save_html``,
        or ``save_all``.
    """

    children: list[object] = [TableOfContents(title="API Contents")]
    if include_coverage:
        children.append(api_coverage_to_chapter(api.to_coverage_table()))
    if include_modules:
        children.extend(api.to_chapters(profile=profile))
    return Document(
        title or f"{api.name} API Reference",
        *children,
        settings=settings,  # type: ignore[arg-type]
        citations=citations,  # type: ignore[arg-type]
    )


def api_objects_to_summary_table(
    objects: Sequence[ApiObject],
    *,
    profile: str | ApiDocProfile = "compact",
    caption: str | None = None,
):
    """Return a summary table for selected API objects."""

    return _api_objects_to_summary_table(objects, profile=profile, caption=caption)


def api_coverage_to_chapter(coverage: object) -> Chapter:
    """Return a coverage chapter from a coverage result or table.

    Args:
        coverage: ``ApiCoverageResult`` or an OODocs table.

    Returns:
        Coverage chapter.
    """

    if isinstance(coverage, ApiCoverageResult):
        return coverage.to_section()
    return Chapter("API Documentation Coverage", coverage)


def api_diff_to_chapter(diff: ApiDiffResult) -> Chapter:
    """Return an API diff chapter.

    Args:
        diff: API diff result.

    Returns:
        Chapter containing diff summary and details.
    """

    return Chapter(
        "API Diff",
        Paragraph(f"{diff.base_name} -> {diff.head_name}"),
        diff.to_summary_table(),
        *diff.to_sections(),
    )


__all__ = [
    "api_coverage_to_chapter",
    "api_diff_to_chapter",
    "api_objects_to_chapter",
    "api_objects_to_summary_table",
    "api_package_to_document",
]
