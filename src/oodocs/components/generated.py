"""Generated page blocks and document summaries.

Attributes:
    TocLevelStyleInput: Accepted input for table-of-contents level style
        overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, TYPE_CHECKING

from oodocs.components.base import Block
from oodocs.components.blocks import Section
from oodocs.components.glossary import Glossary
from oodocs.components.inline import InlineInput, Text, coerce_inlines
from oodocs.components.media import Table
from oodocs.components.references import normalize_reference_sort

if TYPE_CHECKING:
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext


GeneratedListScope = Literal["document", "part", "chapter", "section"]
_GENERATED_LIST_SCOPES = {"document", "part", "chapter", "section"}


def normalize_generated_list_scope(scope: GeneratedListScope | str) -> GeneratedListScope:
    """Return a normalized generated-list scope.

    Args:
        scope: Scope name to validate.

    Returns:
        Normalized scope name.

    Raises:
        ValueError: If the scope is unsupported.
    """

    normalized = str(scope).lower()
    if normalized not in _GENERATED_LIST_SCOPES:
        raise ValueError(
            "generated list scope must be 'document', 'part', 'chapter', or 'section'"
        )
    return normalized  # type: ignore[return-value]


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
        from oodocs import Document, Section, TableOfContents
        from oodocs.generated import TocLevelStyle

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
        scope: Document region to include: ``"document"``, ``"part"``,
            ``"chapter"``, or ``"section"``.
        show_page_numbers: Whether fixed-page renderers should display page
            numbers.
        leader: Leader character between caption text and page number.

    Examples:
        ```python
        from oodocs import Document, ListOfTables

        doc = Document("Report", ListOfTables("Tables", scope="chapter", leader="."))
        ```
    """

    title: list[Text] | None
    scope: GeneratedListScope
    show_page_numbers: bool
    leader: str

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        scope: GeneratedListScope | str = "document",
        show_page_numbers: bool = True,
        leader: str = ".",
    ) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None
        self.scope = normalize_generated_list_scope(scope)
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
        scope: Document region to include: ``"document"``, ``"part"``,
            ``"chapter"``, or ``"section"``.
        show_page_numbers: Whether fixed-page renderers should display page
            numbers.
        leader: Leader character between caption text and page number.

    Examples:
        ```python
        from oodocs import Document, ListOfFigures

        doc = Document("Report", ListOfFigures("Figures", scope="part", show_page_numbers=False))
        ```
    """

    title: list[Text] | None
    scope: GeneratedListScope
    show_page_numbers: bool
    leader: str

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        scope: GeneratedListScope | str = "document",
        show_page_numbers: bool = True,
        leader: str = ".",
    ) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None
        self.scope = normalize_generated_list_scope(scope)
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
class ListOfAlgorithms(Block):
    """Generated list of numbered algorithms.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.
        scope: Document region to include: ``"document"``, ``"part"``,
            ``"chapter"``, or ``"section"``.
        show_page_numbers: Whether fixed-page renderers should display page
            numbers.
        leader: Leader character between caption text and page number.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.engineering import Algorithm
        from oodocs.generated import ListOfAlgorithms

        doc = Document("Methods", ListOfAlgorithms(), Algorithm("Coverage", steps=["Load"]))
        ```
    """

    title: list[Text] | None
    scope: GeneratedListScope
    show_page_numbers: bool
    leader: str

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        scope: GeneratedListScope | str = "document",
        show_page_numbers: bool = True,
        leader: str = ".",
    ) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None
        self.scope = normalize_generated_list_scope(scope)
        self.show_page_numbers = show_page_numbers
        self.leader = leader

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this algorithm list into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_list_of_algorithms(self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this algorithm list into PDF flowables.

        Returns:
            ReportLab flowables for the generated algorithm list.
        """

        return renderer.render_list_of_algorithms(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this algorithm list into HTML markup.

        Returns:
            HTML markup for the generated algorithm list.
        """

        return renderer.render_list_of_algorithms(self, context)


@dataclass(slots=True, init=False)
class ReferenceList(Block):
    """Generated reference list for bibliography entries.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.
        include_uncited: Whether to include entries from the document citation
            library that were not cited inline.
        sort: Optional reference sort override. Supported values are
            ``"citation"``, ``"author"``, ``"year"``, ``"title"``, and
            ``"key"``.

    Attributes:
        title: Optional generated page title fragments.
        include_uncited: Whether uncited library entries are displayed.
        sort: Optional normalized reference sort override.

    Examples:
        ```python
        from oodocs import Document, ReferenceList

        doc = Document("Paper", ReferenceList("Bibliography"))
        ```
    """

    title: list[Text] | None
    include_uncited: bool
    sort: str | None

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        include_uncited: bool = False,
        sort: str | None = None,
    ) -> None:
        self.title = coerce_inlines((title,)) if title is not None else None
        self.include_uncited = bool(include_uncited)
        self.sort = None if sort is None else normalize_reference_sort(sort)

    def sort_style(self, default: str) -> str:
        """Return the effective reference sort style.

        Args:
            default: Theme-level default sort style.

        Returns:
            Normalized reference sort style.
        """

        return self.sort or normalize_reference_sort(default)

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
class GlossaryList(Block):
    """Generated glossary table from a ``Glossary`` registry.

    Args:
        glossary: Glossary registry to display.
        title: Optional section title. Defaults to the active theme locale.
        headers: Term and definition column labels.
        sort: Entry order: ``"insertion"``, ``"key"``, or ``"term"``.
    """

    glossary: Glossary
    title: list[Text] | None
    headers: tuple[str, str]
    sort: str

    def __init__(
        self,
        glossary: Glossary,
        title: InlineInput | None = None,
        *,
        headers: tuple[str, str] = ("Term", "Definition"),
        sort: str = "insertion",
    ) -> None:
        if not isinstance(glossary, Glossary):
            raise TypeError("GlossaryList.glossary must be a Glossary")
        if len(headers) != 2:
            raise ValueError("GlossaryList.headers must contain two labels")
        normalized_sort = str(sort).lower()
        if normalized_sort not in {"insertion", "key", "term"}:
            raise ValueError("GlossaryList.sort must be 'insertion', 'key', or 'term'")
        self.glossary = glossary
        self.title = coerce_inlines((title,)) if title is not None else None
        self.headers = (str(headers[0]), str(headers[1]))
        self.sort = normalized_sort

    def rows(self) -> list[list[str]]:
        """Return table rows for the configured glossary."""

        return [
            [entry.list_label(), entry.list_definition()]
            for entry in self.glossary.sorted_entries(self.sort)
        ]

    def to_table(self, headers: tuple[str, str] | None = None) -> Table:
        """Return the generated glossary as a table block."""

        resolved_headers = (
            headers
            if self.headers == ("Term", "Definition") and headers
            else self.headers
        )
        return Table(list(resolved_headers), self.rows())

    def _section(
        self,
        *,
        default_title: str = "Glossary",
        default_headers: tuple[str, str] | None = None,
    ) -> Section:
        title = self.title if self.title is not None else default_title
        return Section(
            title,
            self.to_table(default_headers),
            numbered=False,
            toc=False,
        )

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this glossary list into a DOCX container."""

        self._section(
            default_title=context.theme.resolve_generated_page_title("glossary_list"),
            default_headers=context.theme.resolve_glossary_headers(),
        ).render_to_docx(renderer, container, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this glossary list into PDF flowables."""

        return self._section(
            default_title=context.theme.resolve_generated_page_title("glossary_list"),
            default_headers=context.theme.resolve_glossary_headers(),
        ).render_to_pdf(renderer, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this glossary list into HTML markup."""

        return self._section(
            default_title=context.theme.resolve_generated_page_title("glossary_list"),
            default_headers=context.theme.resolve_glossary_headers(),
        ).render_to_html(renderer, context)


@dataclass(slots=True, init=False)
class CommentList(Block):
    """Generated list of numbered inline comments.

    Args:
        title: Optional page title. Renderers use their default title when
            omitted.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.generated import CommentList

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
        from oodocs import Document
        from oodocs.generated import FootnoteList

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
        scope: Document region to include: ``"document"``, ``"part"``,
            ``"chapter"``, or ``"section"``.
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
        from oodocs import Document, TableOfContents
        from oodocs.generated import TocLevelStyle

        toc = TableOfContents(
            "Contents",
            scope="document",
            max_level=2,
            level_styles={1: TocLevelStyle(bold=True)},
        )
        doc = Document("Report", toc)
        ```
    """

    title: list[Text] | None
    scope: GeneratedListScope
    show_page_numbers: bool
    leader: str
    max_level: int | None
    level_styles: dict[int, TocLevelStyle]

    def __init__(
        self,
        title: InlineInput | None = None,
        *,
        scope: GeneratedListScope | str = "document",
        show_page_numbers: bool = True,
        leader: str = ".",
        max_level: int | None = None,
        level_styles: Mapping[int, TocLevelStyleInput] | None = None,
    ) -> None:
        if max_level is not None and max_level < 0:
            raise ValueError("TableOfContents.max_level must be >= 0")
        self.title = coerce_inlines((title,)) if title is not None else None
        self.scope = normalize_generated_list_scope(scope)
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
    "GlossaryList",
    "ListOfAlgorithms",
    "ListOfFigures",
    "FootnoteList",
    "ReferenceList",
    "ListOfTables",
    "TableOfContents",
    "TocLevelStyleInput",
    "TocLevelStyle",
    "coerce_toc_level_style",
    "normalize_generated_list_scope",
]
