"""MATLAB-style API help-book composition helpers."""

from __future__ import annotations

from typing import Sequence

from oodocs.apidoc.builtin_categories import OODocs_API_CATEGORIES
from oodocs.apidoc.categories import ApiCategory
from oodocs.apidoc.coverage import check_api_docs
from oodocs.apidoc.model import ApiObject, ApiPackage
from oodocs.apidoc.profiles import ApiPresentationProfile, resolve_presentation_profile
from oodocs.components.blocks import Chapter, Paragraph, Section
from oodocs.components.generated import TableOfContents
from oodocs.components.inline import bold
from oodocs.components.media import Table
from oodocs.document import Document


def api_object_to_help_section(
    obj: ApiObject,
    *,
    level: int = 2,
    presentation: str | ApiPresentationProfile = "help",
) -> Section:
    """Return one public symbol as a help-page section.

    Args:
        obj: Collected API object to render.
        level: Heading level for the returned section.
        presentation: Presentation profile name or object. The default
            ``"help"`` profile keeps a single symbol page concise.

    Returns:
        Section containing the symbol signature, summary, parameters, examples,
        see-also links, and source metadata allowed by the presentation profile.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.apidoc import collect_api, api_object_to_help_section

        api = collect_api("oodocs", public_policy="__all__")
        paragraph = api.find_object("oodocs.Paragraph")
        section = api_object_to_help_section(paragraph, level=2)
        document = Document("Selected API", section)
        ```
    """

    profile = resolve_presentation_profile(presentation)
    return obj.to_section(level=level, profile=profile)


def api_category_to_chapter(
    category: ApiCategory,
    api: ApiPackage,
    *,
    presentation: str | ApiPresentationProfile = "help",
    max_level: int | None = None,
) -> Chapter:
    """Return a category landing page and its symbol help sections.

    Args:
        category: Category definition that names the public symbols to include.
        api: Collected package API containing the category symbols.
        presentation: Presentation profile name or object used for each symbol
            section.
        max_level: Optional deepest heading level. Values below ``2`` render
            the category landing page and index without per-symbol sections.

    Returns:
        Chapter containing the category summary, related guide links, category
        index table, and matching symbol help sections.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.apidoc import ApiCategory, api_category_to_chapter, collect_api

        api = collect_api("oodocs", public_policy="__all__")
        category = ApiCategory(
            id="tables",
            title="Tables and Figures",
            summary="Table and figure building blocks.",
            include=("oodocs.Table", "oodocs.Figure"),
            order=10,
        )
        chapter = api_category_to_chapter(category, api)
        document = Document("Selected API", chapter)
        ```
    """

    objects = _objects_for_category(api, category)
    blocks: list[object] = [Paragraph(category.summary)]
    if category.guide_links:
        blocks.append(Paragraph(bold("Related User Guide pages")))
        blocks.extend(link.to_paragraph() for link in category.guide_links)
    blocks.append(_category_index_table(category, objects))
    blocks.extend(
        api_object_to_help_section(
            obj,
            level=2,
            presentation=presentation,
        )
        for obj in objects
        if max_level is None or max_level >= 2
    )
    return Chapter(category.title, *blocks)


def api_package_to_help_book(
    api: ApiPackage,
    *,
    title: str | None = None,
    categories: Sequence[ApiCategory] | None = None,
    presentation: str | ApiPresentationProfile = "help",
    settings: object | None = None,
    citations: object | None = None,
    include_coverage: bool = True,
    max_level: int | None = None,
) -> Document:
    """Build a category-based API reference help book.

    Args:
        api: Collected package API.
        title: Optional document title. Defaults to
            ``"{api.name} API Reference"``.
        categories: Optional category definitions. Defaults to curated OODocs
            categories for the ``oodocs`` package, or a generated ``Public API``
            category for other packages.
        presentation: Presentation profile name or object used for symbol
            pages.
        settings: Optional document settings passed to ``Document``.
        citations: Optional citation library passed to ``Document``.
        include_coverage: Whether to append API documentation coverage evidence
            after category pages.
        max_level: Optional deepest heading level for the table of contents and
            generated symbol sections.

    Returns:
        Document containing the API contents page, category chapters, per-symbol
        help pages, and optional coverage appendix.

    Raises:
        ValueError: If ``max_level`` is less than ``1``.

    Examples:
        ```python
        from pathlib import Path
        from oodocs import DocumentSettings
        from oodocs.apidoc import collect_api, api_package_to_help_book

        api = collect_api("oodocs", public_policy="__all__")
        reference = api_package_to_help_book(
            api,
            title="OODocs API Reference",
            settings=DocumentSettings(cover_page=True),
        )
        reference.save(Path("build/oodocs-api-reference.html"))
        ```
    """

    if max_level is not None and max_level < 1:
        raise ValueError("max_level must be >= 1")
    category_list = tuple(categories) if categories is not None else _default_categories(api)
    visible_categories = tuple(
        sorted(
            (category for category in category_list if category.show_in_help_book),
            key=lambda category: category.order,
        )
    )
    children: list[object] = [
        TableOfContents(title="API Contents", max_level=max_level),
        _contents_chapter(api, visible_categories),
    ]
    children.extend(
        api_category_to_chapter(
            category,
            api,
            presentation=presentation,
            max_level=max_level,
        )
        for category in visible_categories
    )
    if include_coverage:
        children.append(check_api_docs(api).to_section())
    return Document(
        title or f"{api.name} API Reference",
        *children,
        settings=settings,  # type: ignore[arg-type]
        citations=citations,  # type: ignore[arg-type]
    )


def _contents_chapter(api: ApiPackage, categories: Sequence[ApiCategory]) -> Chapter:
    rows = []
    for category in categories:
        objects = _objects_for_category(api, category)
        rows.append(
            [
                category.title,
                category.summary,
                str(len(objects)),
            ]
        )
    return Chapter(
        "API Contents",
        Paragraph("Find public symbols by category. Coverage evidence is appended at the end."),
        Table(
            ["Category", "Purpose", "Symbols"],
            rows,
            caption=None,
            split=True,
        ),
    )


def _default_categories(api: ApiPackage) -> tuple[ApiCategory, ...]:
    if api.name == "oodocs":
        return OODocs_API_CATEGORIES
    public_objects = api.select_objects(
        kind=("class", "function", "data", "attribute"),
        visibility="public",
        recursive=False,
    )
    return (
        ApiCategory(
            id="public-api",
            title="Public API",
            summary=f"Public API symbols exported by {api.name}.",
            include=tuple(obj.qualname for obj in public_objects),
            order=10,
        ),
    )


def _category_index_table(category: ApiCategory, objects: Sequence[ApiObject]) -> Table:
    rows = [
        [
            obj.name,
            obj.summary_text(),
            _common_use(obj),
            f"{category.title} > {obj.name}",
        ]
        for obj in objects
    ]
    return Table(
        ["Object", "Purpose", "Common use", "Page"],
        rows,
        caption=None,
        split=True,
    )


def _objects_for_category(api: ApiPackage, category: ApiCategory) -> tuple[ApiObject, ...]:
    found: list[ApiObject] = []
    seen: set[str] = set()
    for name in category.include:
        obj = api.find_object(name)
        if obj is None:
            obj = api.find_object(name.rsplit(".", 1)[-1])
        if obj is None or obj.qualname in seen:
            continue
        found.append(obj)
        seen.add(obj.qualname)
    return tuple(found)


def _common_use(obj: ApiObject) -> str:
    if obj.kind == "class":
        return "Create or configure this object directly."
    if obj.kind in {"function", "method"}:
        return "Call this helper from Python code."
    if obj.kind in {"attribute", "data"}:
        return "Use as a constant or configuration value."
    return "Use from the documented API surface."


__all__ = [
    "api_category_to_chapter",
    "api_object_to_help_section",
    "api_package_to_help_book",
]
