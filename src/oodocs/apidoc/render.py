"""Composable API documentation render helpers."""

from __future__ import annotations

from typing import Sequence

from oodocs.apidoc.blocks import api_objects_to_chapter, api_objects_to_summary_table as _api_objects_to_summary_table
from oodocs.apidoc.coverage import ApiCoverageResult
from oodocs.apidoc.diff import ApiDiffResult
from oodocs.apidoc.model import ApiObject
from oodocs.apidoc.profiles import ApiPresentationProfile
from oodocs.components.blocks import Chapter, Paragraph


def api_objects_to_summary_table(
    objects: Sequence[ApiObject],
    *,
    presentation: str | ApiPresentationProfile = "compact",
    caption: str | None = None,
):
    """Return a summary table for selected API objects.

    Args:
        objects: API objects to include as rows.
        presentation: Presentation profile name or ``ApiPresentationProfile``. The website
            profile renders object names as links to object section anchors.
        caption: Optional table caption.

    Returns:
        OODocs table that can be inserted into any ``Chapter`` or ``Section``.

    Examples:
        Add a compact function index to an authored document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api, api_objects_to_summary_table

        api = collect_api("mypkg")
        functions = api.select_objects(kind="function")
        doc = Document(
            "Release Notes",
            Chapter(
                "Public Function Index",
                api_objects_to_summary_table(functions, presentation="compact"),
            ),
        )
        ```
    """

    return _api_objects_to_summary_table(objects, presentation=presentation, caption=caption)


def api_coverage_to_chapter(coverage: object) -> Chapter:
    """Return a coverage chapter from a coverage result or table.

    Args:
        coverage: ``ApiCoverageResult`` or an already-built OODocs table.

    Returns:
        Chapter containing coverage metrics and issue rows when available.

    Examples:
        Insert coverage evidence into a release report:

        ```python
        from oodocs import Document
        from oodocs.apidoc import check_api_docs, collect_api, api_coverage_to_chapter

        api = collect_api("mypkg")
        coverage = check_api_docs(api, fail_under=0.90)
        report = Document("Release Evidence", api_coverage_to_chapter(coverage))
        report.save_docx("artifacts/release-evidence.docx")
        ```
    """

    if isinstance(coverage, ApiCoverageResult):
        return coverage.to_section()
    return Chapter("API Documentation Coverage", coverage)


def api_diff_to_chapter(diff: ApiDiffResult) -> Chapter:
    """Return an API diff chapter.

    Args:
        diff: API diff result produced by ``diff_api``.

    Returns:
        Chapter containing the diff summary table and detailed change sections.

    Examples:
        Build a rendered change report from two snapshot sidecars:

        ```python
        from oodocs import Document
        from oodocs.apidoc import ApiSnapshot, api_diff_to_chapter, diff_api

        base = ApiSnapshot.load_json("artifacts/api-base.json")
        head = ApiSnapshot.load_json("artifacts/api-head.json")
        diff = diff_api(base, head)
        Document("Public API Changes", api_diff_to_chapter(diff)).save_all(
            "artifacts/api-diff"
        )
        ```
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
]
