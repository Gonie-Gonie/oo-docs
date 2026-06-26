"""Category models for user-facing API help books."""

from __future__ import annotations

from dataclasses import dataclass


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
        include: Public symbol names or qualified names shown in this category.
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
                include=("my_package.Document", "my_package.render"),
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


__all__ = ["ApiCategory", "GuideLink"]
