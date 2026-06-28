"""Generated page blocks and document summaries.

Attributes:
    TocLevelStyleInput: Accepted input for table-of-contents level style
        overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TYPE_CHECKING

from oodocs.components.base import Block
from oodocs.components.inline import InlineInput, Text, coerce_inlines

if TYPE_CHECKING:
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext


@dataclass(slots=True)
class TocLevelStyle:
    """Optional display overrides for a table-of-contents level.

    Attributes:
        indent: Optional level indent.
        space_before: Optional spacing before entries at this level.
        space_after: Optional spacing after entries at this level.
        font_size_delta: Optional font-size delta from the base TOC style.
        bold: Optional bold override.
        italic: Optional italic override.

    Examples:
        ```python
        from oodocs import Document, Section, TableOfContents, TocLevelStyle

        toc = TableOfContents(level_styles={1: TocLevelStyle(indent=0.25, bold=True)})
        document = Document("Report", toc, Section("Summary"))
        ```
    """

    indent: float | None = None
    space_before: float | None = None
    space_after: float | None = None
    font_size_delta: float | None = None
    bold: bool | None = None
    italic: bool | None = None


TocLevelStyleInput = TocLevelStyle | Mapping[str, object]


def coerce_toc_level_style(value: TocLevelStyleInput) -> TocLevelStyle:
    """Normalize a table-of-contents level style.

    Args:
        value: Existing style or mapping of ``TocLevelStyle`` fields.

    Returns:
        A table-of-contents level style.

    Raises:
        TypeError: If ``value`` cannot be converted.

    Examples:
        ```python
        style = coerce_toc_level_style({"indent": 0.25, "bold": True})
        ```
    """

    if isinstance(value, TocLevelStyle):
        return value
    if isinstance(value, Mapping):
        return TocLevelStyle(**dict(value))
    raise TypeError(f"Unsupported TOC level style: {type(value)!r}")


@dataclass(slots=True, init=False)
class ListOfTables(Block):
    """Generated list of captioned tables.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.
        show_page_numbers: Whether fixed-page renderers should display page
            numbers.
        leader: Leader character between caption text and page number.

    Examples:
        ```python
        from oodocs import Document, ListOfTables

        doc = Document("Report", ListOfTables("Tables", leader="."))
        ```
    """

    title: list[Text] | None
    show_page_numbers: bool
    leader: str

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        show_page_numbers: bool = True,
        leader: str = ".",
    ) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None
        self.show_page_numbers = show_page_numbers
        self.leader = leader

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this table list into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_list_of_tables(self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this table list into PDF flowables.

        Returns:
            ReportLab flowables for the generated table list.
        """

        return renderer.render_list_of_tables(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this table list into HTML markup.

        Returns:
            HTML markup for the generated table list.
        """

        return renderer.render_list_of_tables(self, context)


@dataclass(slots=True, init=False)
class ListOfFigures(Block):
    """Generated list of captioned figures.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.
        show_page_numbers: Whether fixed-page renderers should display page
            numbers.
        leader: Leader character between caption text and page number.

    Examples:
        ```python
        from oodocs import Document, ListOfFigures

        doc = Document("Report", ListOfFigures("Figures", show_page_numbers=False))
        ```
    """

    title: list[Text] | None
    show_page_numbers: bool
    leader: str

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        show_page_numbers: bool = True,
        leader: str = ".",
    ) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None
        self.show_page_numbers = show_page_numbers
        self.leader = leader

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this figure list into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_list_of_figures(self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this figure list into PDF flowables.

        Returns:
            ReportLab flowables for the generated figure list.
        """

        return renderer.render_list_of_figures(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this figure list into HTML markup.

        Returns:
            HTML markup for the generated figure list.
        """

        return renderer.render_list_of_figures(self, context)


@dataclass(slots=True, init=False)
class ReferenceList(Block):
    """Generated reference list for cited bibliography entries.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.

    Examples:
        ```python
        from oodocs import Document, ReferenceList

        doc = Document("Paper", ReferenceList("Bibliography"))
        ```
    """

    title: list[Text] | None

    def __init__(self, title: InlineInput | None = None) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this reference list into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_reference_list(self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this reference list into PDF flowables.

        Returns:
            ReportLab flowables for the generated reference list.
        """

        return renderer.render_reference_list(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this reference list into HTML markup.

        Returns:
            HTML markup for the generated reference list.
        """

        return renderer.render_reference_list(self, context)


@dataclass(slots=True, init=False)
class CommentList(Block):
    """Generated list of numbered inline comments.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.

    Examples:
        ```python
        from oodocs import CommentList, Document

        doc = Document("Review", CommentList("Reviewer Notes"))
        ```
    """

    title: list[Text] | None

    def __init__(self, title: InlineInput | None = None) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this comment list into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_comment_list(self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this comment list into PDF flowables.

        Returns:
            ReportLab flowables for the generated comment list.
        """

        return renderer.render_comment_list(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this comment list into HTML markup.

        Returns:
            HTML markup for the generated comment list.
        """

        return renderer.render_comment_list(self, context)


@dataclass(slots=True, init=False)
class FootnoteList(Block):
    """Generated list of numbered portable footnotes.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.

    Examples:
        ```python
        from oodocs import Document, FootnoteList

        doc = Document("Report", FootnoteList())
        ```
    """

    title: list[Text] | None

    def __init__(self, title: InlineInput | None = None) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this footnote list into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_footnote_list(self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this footnote list into PDF flowables.

        Returns:
            ReportLab flowables for the generated footnote list.
        """

        return renderer.render_footnote_list(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this footnote list into HTML markup.

        Returns:
            HTML markup for the generated footnote list.
        """

        return renderer.render_footnote_list(self, context)


@dataclass(slots=True, init=False)
class TableOfContents(Block):
    """Generated outline of authored headings.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.
        show_page_numbers: Whether fixed-page renderers should display page
            numbers.
        leader: Leader character between heading text and page number.
        max_level: Highest heading level to include. ``None`` includes all
            levels.
        level_styles: Optional display overrides keyed by heading level.

    Raises:
        ValueError: If ``max_level`` is negative.

    Examples:
        ```python
        from oodocs import Document, TableOfContents, TocLevelStyle

        toc = TableOfContents(
            "Contents",
            max_level=2,
            level_styles={1: TocLevelStyle(bold=True)},
        )
        doc = Document("Report", toc)
        ```
    """

    title: list[Text] | None
    show_page_numbers: bool
    leader: str
    max_level: int | None
    level_styles: dict[int, TocLevelStyle]

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        show_page_numbers: bool = True,
        leader: str = ".",
        max_level: int | None = None,
        level_styles: Mapping[int, TocLevelStyleInput] | None = None,
    ) -> None:
        if max_level is not None and max_level < 0:
            raise ValueError("TableOfContents.max_level must be >= 0")
        self.title = coerce_inlines((title,)) if title is not None else None
        self.show_page_numbers = show_page_numbers
        self.leader = leader
        self.max_level = max_level
        self.level_styles = {
            int(level): coerce_toc_level_style(style)
            for level, style in (level_styles or {}).items()
        }

    def includes_level(self, level: int) -> bool:
        """Return whether a heading level is included.

        Args:
            level: Heading level to test.

        Returns:
            ``True`` when the heading should be listed.
        """

        return self.max_level is None or level <= self.max_level

    def style_for_level(self, level: int) -> TocLevelStyle:
        """Return display overrides for a heading level.

        Args:
            level: Heading level to look up.

        Returns:
            Configured style or a default empty style.
        """

        return self.level_styles.get(level, TocLevelStyle())

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this table of contents into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_table_of_contents(self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this table of contents into PDF flowables.

        Returns:
            ReportLab flowables for the table of contents.
        """

        return renderer.render_table_of_contents(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this table of contents into HTML markup.

        Returns:
            HTML markup for the table of contents.
        """

        return renderer.render_table_of_contents(self, context)


__all__ = [
    "CommentList",
    "ListOfFigures",
    "FootnoteList",
    "ReferenceList",
    "ListOfTables",
    "TableOfContents",
    "TocLevelStyleInput",
    "TocLevelStyle",
    "coerce_toc_level_style",
]
