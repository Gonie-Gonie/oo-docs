"""Category models for user-facing API help books."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from oodocs.apidoc.model import ApiDocIssue, ApiObject, ApiPackage


@dataclass(frozen=True, slots=True)
class GuideLink:
    """Link from an API category to a related User Guide page.

    Attributes:
        title: Visible guide page title.
        target: Link target, usually an HTML anchor.

    Examples:
        ```python
        from oodocs.apidoc import GuideLink

        link = GuideLink("Tables Guide", "usage-guide.html#tables")
        paragraph = link.to_paragraph()
        ```
    """

    title: str
    target: str

    def to_paragraph(self):
        """Return this guide link as an OODocs paragraph.

        Returns:
            Paragraph containing the linked title and the raw target. Help-book
            category pages use this paragraph in their related-guide list.

        Examples:
            ```python
            from oodocs.apidoc import GuideLink

            guide_link = GuideLink("Overview", "usage-guide.html#overview")
            related_page = guide_link.to_paragraph()
            ```
        """

        from oodocs.components.blocks import Paragraph
        from oodocs.components.inline import link

        return Paragraph(link(self.target, self.title), " ", self.target)


@dataclass(frozen=True, slots=True)
class ApiCategory:
    """Public API category used by help-book rendering.

    Attributes:
        id: Stable kebab-case category identifier.
        title: Display title.
        summary: Short category introduction.
        include: Public symbol names, qualified names, or qualified-name
            prefixes ending with ``".*"`` shown in this category.
        order: Sort order.
        guide_links: Related User Guide pages.
        show_in_help_book: Whether this category is rendered by default.

    Examples:
        ```python
        from oodocs.apidoc import ApiCategory, GuideLink, collect_api

        api = collect_api("my_package")
        categories = [
            ApiCategory(
                id="core",
                title="Core Objects",
                summary="Primary classes and construction helpers.",
                include=("my_package.Document", "my_package.render", "my_package.io.*"),
                order=10,
                guide_links=(GuideLink("User Guide", "usage-guide.html#core"),),
            )
        ]
        reference = api.to_help_book(categories=categories)
        ```
    """

    id: str
    title: str
    summary: str
    include: tuple[str, ...]
    order: int
    guide_links: tuple[GuideLink, ...] = ()
    show_in_help_book: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("ApiCategory.id must not be empty")
        if not self.title.strip():
            raise ValueError("ApiCategory.title must not be empty")
        object.__setattr__(self, "include", tuple(self.include))
        object.__setattr__(self, "guide_links", tuple(self.guide_links))


def select_uncategorized_api_objects(
    api: ApiPackage,
    categories: Sequence[ApiCategory] | None = None,
    *,
    recursive: bool = False,
) -> list[ApiObject]:
    """Return public API objects missing from help-book categories.

    Args:
        api: Collected API package to check.
        categories: Category definitions to use. Defaults to the built-in
            OODocs categories for the ``oodocs`` package, or a generated public
            API category for other packages.
        recursive: Whether to check nested class members in addition to
            top-level public objects.

    Returns:
        Public API objects not matched by category include names.

    Examples:
        Add an appendix for objects that are not yet assigned to a curated
        category:

        ```python
        from oodocs.apidoc import collect_api, select_uncategorized_api_objects

        api = collect_api("oodocs", public_policy="__all__")
        uncategorized = select_uncategorized_api_objects(api)
        assert all(obj.visibility == "public" for obj in uncategorized)
        ```
    """

    category_list = tuple(categories) if categories is not None else _default_categories(api)
    exact_names, prefixes = _covered_category_matchers(category_list)
    objects = api.select_objects(
        kind=("class", "function", "data", "attribute"),
        visibility="public",
        recursive=recursive,
    )
    return [
        obj
        for obj in objects
        if not _is_category_match(obj, exact_names=exact_names, prefixes=prefixes)
    ]


def check_api_help_categories(
    api: ApiPackage,
    categories: Sequence[ApiCategory] | None = None,
    *,
    recursive: bool = False,
) -> tuple[ApiDocIssue, ...]:
    """Check that public API objects are assigned to help-book categories.

    Args:
        api: Collected API package to check.
        categories: Category definitions to use. Defaults to
            ``select_uncategorized_api_objects`` behavior.
        recursive: Whether to check nested class members.

    Returns:
        Error-level issues for uncategorized public API objects. An empty tuple
        means the category registry covers the checked API surface.

    Examples:
        Fail a release gate when a curated API reference omits public symbols:

        ```python
        from oodocs.apidoc import check_api_help_categories, collect_api

        api = collect_api("oodocs", public_policy="__all__")
        issues = check_api_help_categories(api)
        if issues:
            raise SystemExit(issues[0].message)
        ```
    """

    from oodocs.apidoc.model import ApiDocIssue

    return tuple(
        ApiDocIssue(
            "error",
            "uncategorized-api-object",
            f"{obj.qualname} is not assigned to an API help-book category.",
            source="apidoc.category",
            qualname=obj.qualname,
            module=obj.module,
            path=obj.source_path,
            line_number=obj.line_number,
        )
        for obj in select_uncategorized_api_objects(
            api,
            categories,
            recursive=recursive,
        )
    )


def _covered_category_matchers(categories: Sequence[ApiCategory]) -> tuple[set[str], tuple[str, ...]]:
    exact_names: set[str] = set()
    prefixes: list[str] = []
    for category in categories:
        for name in category.include:
            if name.endswith(".*"):
                prefixes.append(name[:-1])
                continue
            exact_names.add(name)
            exact_names.add(name.rsplit(".", 1)[-1])
    return exact_names, tuple(prefixes)


def _is_category_match(
    obj: ApiObject,
    *,
    exact_names: set[str],
    prefixes: Sequence[str],
) -> bool:
    if _category_name_matches(obj.qualname, obj.name, exact_names=exact_names, prefixes=prefixes):
        return True
    reexported_from = obj.metadata.get("reexported_from")
    if isinstance(reexported_from, str):
        return _category_name_matches(
            reexported_from,
            reexported_from.rsplit(".", 1)[-1],
            exact_names=exact_names,
            prefixes=prefixes,
        )
    return False


def _category_name_matches(
    qualname: str,
    name: str,
    *,
    exact_names: set[str],
    prefixes: Sequence[str],
) -> bool:
    return (
        qualname in exact_names
        or name in exact_names
        or any(qualname.startswith(prefix) for prefix in prefixes)
    )


def _default_categories(api: ApiPackage) -> tuple[ApiCategory, ...]:
    if api.name == "oodocs":
        from oodocs.apidoc.builtin_categories import OODocs_API_CATEGORIES

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


__all__ = [
    "ApiCategory",
    "GuideLink",
    "check_api_help_categories",
    "select_uncategorized_api_objects",
]
