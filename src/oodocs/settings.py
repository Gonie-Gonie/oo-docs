"""User-facing configuration objects for documents and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

from oodocs.components.inline import InlineInput, Text, coerce_inlines
from oodocs.components.positioning import PositionedItem, coerce_positioned_items
from oodocs.core import inches_to_length, length_to_inches, normalize_length_unit
from oodocs.components.people import (
    Affiliation,
    Author,
    AuthorInput,
    AuthorLayout,
    AuthorTitleLine,
    coerce_author_layout,
    coerce_authors,
)
from oodocs.styles import Theme

PageOrientation = Literal["portrait", "landscape"]


def _normalize_optional_metadata_text(value: object, *, name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_metadata_keywords(keywords: Sequence[object] | str | None) -> tuple[str, ...]:
    if keywords is None:
        return ()
    if isinstance(keywords, str):
        values: Iterable[object] = keywords.split(",")
    else:
        values = keywords
    return tuple(
        normalized
        for value in values
        if (normalized := str(value).strip())
    )


def _normalize_page_orientation(orientation: str | None) -> PageOrientation | None:
    if orientation is None:
        return None
    normalized = orientation.strip().lower()
    if normalized not in {"portrait", "landscape"}:
        raise ValueError("orientation must be 'portrait', 'landscape', or None")
    if normalized == "portrait":
        return "portrait"
    return "landscape"


@dataclass(slots=True, init=False)
class DocumentMetadata:
    """File and browser metadata written by renderers.

    Args:
        title: Optional metadata title. Defaults to the visible document title.
        author: Optional file metadata author. Defaults to structured
            ``authors`` from ``DocumentSettings``.
        subject: Optional subject written to DOCX/PDF metadata and HTML meta.
        keywords: Optional keyword list or comma-separated keyword string.
        description: Optional HTML description and DOCX comments text.

    Examples:
        ```python
        from oodocs import DocumentMetadata, DocumentSettings

        settings = DocumentSettings(
            metadata=DocumentMetadata(
                title="Short PDF Title",
                author="Documentation Team",
                subject="Release evidence",
                keywords=["release", "evidence"],
            )
        )
        ```
    """

    title: str | None
    author: str | None
    subject: str | None
    keywords: tuple[str, ...]
    description: str | None

    def __init__(
        self,
        *,
        title: str | None = None,
        author: str | None = None,
        subject: str | None = None,
        keywords: Sequence[object] | str | None = None,
        description: str | None = None,
    ) -> None:
        self.title = _normalize_optional_metadata_text(title, name="title")
        self.author = _normalize_optional_metadata_text(author, name="author")
        self.subject = _normalize_optional_metadata_text(subject, name="subject")
        self.keywords = _normalize_metadata_keywords(keywords)
        self.description = _normalize_optional_metadata_text(
            description,
            name="description",
        )

    def keywords_text(self, separator: str = ", ") -> str | None:
        """Return keywords as a metadata string.

        Args:
            separator: Separator used between keywords.

        Returns:
            Joined keywords, or ``None`` when no keywords are configured.
        """

        if not self.keywords:
            return None
        return separator.join(self.keywords)


@dataclass(slots=True, init=False)
class PageSize:
    """Physical page size used by renderers and layout helpers.

    Args:
        width: Page width in ``unit``.
        height: Page height in ``unit``.
        unit: Length unit for ``width`` and ``height``. When ``None``, callers
            must supply a default unit when resolving physical sizes.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, PageLayout, PageSize, Paragraph

        settings = DocumentSettings(page_layout=PageLayout(PageSize.letter()))
        document = Document("Letter Report", Paragraph("Body text."), settings=settings)
        ```
    """

    width: float
    height: float
    unit: str | None

    def __init__(
        self,
        width: float = 21.0,
        height: float = 29.7,
        *,
        unit: str | None = "cm",
    ) -> None:
        self.width = width
        self.height = height
        self.unit = normalize_length_unit(unit) if unit is not None else None

    @classmethod
    def a4(cls) -> PageSize:
        """Create an A4 page size.

        Returns:
            A ``PageSize`` configured as 21 x 29.7 cm.

        Examples:
            ```python
            page_size = PageSize.a4()
            ```
        """

        return cls(21.0, 29.7, unit="cm")

    @classmethod
    def letter(cls) -> PageSize:
        """Create a US Letter page size.

        Returns:
            A ``PageSize`` configured as 8.5 x 11 inches.

        Examples:
            ```python
            page_size = PageSize.letter()
            ```
        """

        return cls(8.5, 11.0, unit="in")

    def oriented(self, orientation: str | None) -> PageSize:
        """Return this page size with portrait or landscape orientation.

        Args:
            orientation: ``"portrait"`` or ``"landscape"``. ``None`` keeps
                the current width and height order.

        Returns:
            A page size with width and height swapped only when needed.

        Examples:
            ```python
            assert PageSize.a4().landscape().width > PageSize.a4().landscape().height
            ```
        """

        normalized = _normalize_page_orientation(orientation)
        if normalized is None:
            return PageSize(self.width, self.height, unit=self.unit)
        should_swap = (
            normalized == "landscape" and self.width < self.height
        ) or (
            normalized == "portrait" and self.width > self.height
        )
        if should_swap:
            return PageSize(self.height, self.width, unit=self.unit)
        return PageSize(self.width, self.height, unit=self.unit)

    def landscape(self) -> PageSize:
        """Return this page size in landscape orientation.

        Returns:
            A page size whose width is greater than or equal to its height.
        """

        return self.oriented("landscape")

    def portrait(self) -> PageSize:
        """Return this page size in portrait orientation.

        Returns:
            A page size whose height is greater than or equal to its width.
        """

        return self.oriented("portrait")

    def width_in_inches(self, default_unit: str) -> float:
        """Return the page width in inches.

        Args:
            default_unit: Unit to use when this page size has ``unit=None``.

        Returns:
            The resolved page width in inches.

        Examples:
            ```python
            assert PageSize.letter().width_in_inches("in") == 8.5
            ```
        """

        return length_to_inches(self.width, self.unit or default_unit)

    def height_in_inches(self, default_unit: str) -> float:
        """Return the page height in inches.

        Args:
            default_unit: Unit to use when this page size has ``unit=None``.

        Returns:
            The resolved page height in inches.

        Examples:
            ```python
            assert PageSize.letter().height_in_inches("in") == 11.0
            ```
        """

        return length_to_inches(self.height, self.unit or default_unit)


@dataclass(slots=True, init=False)
class PageMargins:
    """Physical page margins used by renderers and layout helpers.

    Args:
        top: Top margin in ``unit``.
        right: Right margin in ``unit``.
        bottom: Bottom margin in ``unit``.
        left: Left margin in ``unit``.
        unit: Length unit for all margin values. When ``None``, callers must
            supply a default unit when resolving physical margins.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, PageLayout, PageMargins, Paragraph

        settings = DocumentSettings(
            page_layout=PageLayout(page_margins=PageMargins(1.0, 0.8, 1.0, 0.8, unit="in"))
        )
        document = Document("Margin Report", Paragraph("Body text."), settings=settings)
        ```
    """

    top: float
    right: float
    bottom: float
    left: float
    unit: str | None

    def __init__(
        self,
        top: float = 2.54,
        right: float = 2.54,
        bottom: float = 2.54,
        left: float = 2.54,
        *,
        unit: str | None = "cm",
    ) -> None:
        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left
        self.unit = normalize_length_unit(unit) if unit is not None else None

    @classmethod
    def all(cls, value: float, *, unit: str | None = None) -> PageMargins:
        """Create margins with the same value on every side.

        Args:
            value: Margin value for all sides.
            unit: Length unit for the margin value.

        Returns:
            A ``PageMargins`` instance with equal sides.

        Examples:
            ```python
            margins = PageMargins.all(1.0, unit="in")
            ```
        """

        return cls(value, value, value, value, unit=unit)

    @classmethod
    def symmetric(
        cls,
        *,
        vertical: float,
        horizontal: float,
        unit: str | None = None,
    ) -> PageMargins:
        """Create margins from vertical and horizontal pairs.

        Args:
            vertical: Top and bottom margin value.
            horizontal: Left and right margin value.
            unit: Length unit for the margin values.

        Returns:
            A ``PageMargins`` instance with symmetric sides.

        Examples:
            ```python
            margins = PageMargins.symmetric(vertical=1.0, horizontal=0.75, unit="in")
            ```
        """

        return cls(vertical, horizontal, vertical, horizontal, unit=unit)

    def top_in_inches(self, default_unit: str) -> float:
        """Return the top margin in inches.

        Args:
            default_unit: Unit to use when these margins have ``unit=None``.

        Returns:
            The top margin in inches.

        Examples:
            ```python
            assert PageMargins.all(1.0, unit="in").top_in_inches("in") == 1.0
            ```
        """

        return length_to_inches(self.top, self.unit or default_unit)

    def right_in_inches(self, default_unit: str) -> float:
        """Return the right margin in inches.

        Args:
            default_unit: Unit to use when these margins have ``unit=None``.

        Returns:
            The right margin in inches.

        Examples:
            ```python
            margins = PageMargins.symmetric(vertical=1.0, horizontal=0.5, unit="in")
            assert margins.right_in_inches("in") == 0.5
            ```
        """

        return length_to_inches(self.right, self.unit or default_unit)

    def bottom_in_inches(self, default_unit: str) -> float:
        """Return the bottom margin in inches.

        Args:
            default_unit: Unit to use when these margins have ``unit=None``.

        Returns:
            The bottom margin in inches.

        Examples:
            ```python
            assert PageMargins.all(1.0, unit="in").bottom_in_inches("in") == 1.0
            ```
        """

        return length_to_inches(self.bottom, self.unit or default_unit)

    def left_in_inches(self, default_unit: str) -> float:
        """Return the left margin in inches.

        Args:
            default_unit: Unit to use when these margins have ``unit=None``.

        Returns:
            The left margin in inches.

        Examples:
            ```python
            margins = PageMargins.symmetric(vertical=1.0, horizontal=0.5, unit="in")
            assert margins.left_in_inches("in") == 0.5
            ```
        """

        return length_to_inches(self.left, self.unit or default_unit)


@dataclass(slots=True, init=False)
class PageLayout:
    """Document-level page geometry grouped like LaTeX ``geometry`` options.

    Args:
        page_size: Physical page size. Defaults to A4.
        page_margins: Physical page margins. Defaults to 2.54 cm on all sides.
        orientation: Optional page orientation. When omitted, ``page_size`` is
            used as supplied; ``"portrait"`` or ``"landscape"`` swaps width
            and height when needed.

    Examples:
        ```python
        from oodocs import DocumentSettings, PageLayout, PageSize

        settings = DocumentSettings(page_layout=PageLayout.landscape(PageSize.a4()))
        ```
    """

    page_size: PageSize
    page_margins: PageMargins
    orientation: PageOrientation | None

    def __init__(
        self,
        page_size: PageSize | None = None,
        page_margins: PageMargins | None = None,
        *,
        orientation: str | None = None,
    ) -> None:
        self.orientation = _normalize_page_orientation(orientation)
        self.page_size = (page_size or PageSize.a4()).oriented(self.orientation)
        self.page_margins = page_margins or PageMargins()

    @classmethod
    def portrait(
        cls,
        page_size: PageSize | None = None,
        page_margins: PageMargins | None = None,
    ) -> PageLayout:
        """Create a portrait page layout."""

        return cls(page_size, page_margins, orientation="portrait")

    @classmethod
    def landscape(
        cls,
        page_size: PageSize | None = None,
        page_margins: PageMargins | None = None,
    ) -> PageLayout:
        """Create a landscape page layout."""

        return cls(page_size, page_margins, orientation="landscape")

    def page_width_in_inches(self, default_unit: str) -> float:
        """Return the resolved page width in inches."""

        return self.page_size.width_in_inches(default_unit)

    def page_height_in_inches(self, default_unit: str) -> float:
        """Return the resolved page height in inches."""

        return self.page_size.height_in_inches(default_unit)

    def page_margin_inches(self, default_unit: str) -> tuple[float, float, float, float]:
        """Return resolved page margins as ``(top, right, bottom, left)``."""

        return (
            self.page_margins.top_in_inches(default_unit),
            self.page_margins.right_in_inches(default_unit),
            self.page_margins.bottom_in_inches(default_unit),
            self.page_margins.left_in_inches(default_unit),
        )

    def text_width_in_inches(self, default_unit: str) -> float:
        """Return writable page width after horizontal margins."""

        _, right, _, left = self.page_margin_inches(default_unit)
        return max(self.page_width_in_inches(default_unit) - left - right, 0)

    def text_height_in_inches(self, default_unit: str) -> float:
        """Return writable page height after vertical margins."""

        top, _, bottom, _ = self.page_margin_inches(default_unit)
        return max(self.page_height_in_inches(default_unit) - top - bottom, 0)


@dataclass(slots=True, init=False)
class DocumentSettings:
    """Document-level metadata and rendering configuration.

    Args:
        metadata: Optional structured metadata for DOCX/PDF properties and
            HTML head tags.
        subtitle: Optional subtitle rendered with title matter.
        authors: Optional author metadata used for title matter.
        author_layout: Layout rules for author title matter.
        cover_page: Whether renderers should place title matter on a separate
            cover page when supported.
        unit: Default length unit for values that do not carry an explicit unit.
        page_layout: Grouped page geometry.
        overlays: Absolute-positioned page decorations or overlays. Pass
            ``scope=...`` on each item for all, cover, front, main, or physical
            page-range selection.
        page_items: Compatibility alias for ``overlays``.
        theme: Rendering theme.

    Examples:
        Configure page metadata and geometry:

        ```python
        from oodocs import Author, Document, DocumentSettings, PageLayout, PageMargins, PageSize, Paragraph

        settings = DocumentSettings(
            authors=[Author("Jane Doe", email="jane@example.edu")],
            page_layout=PageLayout(
                PageSize.letter(),
                PageMargins.symmetric(vertical=1.0, horizontal=0.8, unit="in"),
            ),
            cover_page=True,
        )
        document = Document("Study Report", Paragraph("Findings."), settings=settings)
        ```

        Add a page-positioned watermark:

        ```python
        from oodocs import Document, DocumentSettings, Paragraph
        from oodocs.positioning import TextBox

        watermark = TextBox("DRAFT", x=0.75, y=0.75, width=2.0, height=0.5, font_size=24)
        cover_stamp = TextBox(
            "CONFIDENTIAL",
            x=0.75,
            y=1.25,
            width=2.0,
            height=0.5,
            scope="cover",
        )
        settings = DocumentSettings(overlays=[watermark, cover_stamp])
        document = Document("Draft Report", Paragraph("Internal review."), settings=settings)
        ```

    Notes:
        Length values without their own unit use ``unit`` as the default when
        renderers resolve physical page geometry. ``overlays`` are absolute
        overlays or decorations and are validated when settings are created.
        PDF applies page scopes to physical pages. DOCX applies scopes at
        section/header level, and HTML applies them to the static page frame.

    See Also:
        ``PageSize`` and ``PageMargins`` for page geometry, ``Theme`` for
        renderer defaults, and ``Author``/``AuthorLayout`` for title matter.
    """

    metadata: DocumentMetadata
    subtitle: list[Text] | None
    authors: tuple[Author, ...]
    author_layout: AuthorLayout
    cover_page: bool
    unit: str
    page_layout: PageLayout
    overlays: tuple[PositionedItem, ...]
    page_items: tuple[PositionedItem, ...]
    theme: Theme

    def __init__(
        self,
        *,
        metadata: DocumentMetadata | None = None,
        subtitle: InlineInput | None = None,
        authors: Sequence[AuthorInput] | None = None,
        author_layout: AuthorLayout | None = None,
        cover_page: bool = False,
        unit: str = "in",
        page_layout: PageLayout | None = None,
        overlays: Sequence[PositionedItem] | None = None,
        page_items: Sequence[PositionedItem] | None = None,
        theme: Theme | None = None,
    ) -> None:
        if metadata is not None and not isinstance(metadata, DocumentMetadata):
            raise TypeError("metadata must be a DocumentMetadata instance")
        self.metadata = metadata or DocumentMetadata()
        self.subtitle = coerce_inlines((subtitle,)) if subtitle is not None else None
        self.authors = coerce_authors(authors)
        self.author_layout = coerce_author_layout(author_layout)
        self.cover_page = cover_page
        self.unit = normalize_length_unit(unit)
        self.page_layout = page_layout or PageLayout()
        if overlays is not None and page_items is not None:
            raise ValueError("overlays cannot be combined with page_items")
        positioned_items = coerce_positioned_items(
            overlays if overlays is not None else page_items
        )
        self.overlays = positioned_items
        self.page_items = positioned_items
        self.theme = theme or Theme()

    def page_width_in_inches(self) -> float:
        """Return the resolved page width in inches.

        Returns:
            Page width converted from the configured page unit to inches.

        Examples:
            ```python
            settings = DocumentSettings(page_layout=PageLayout(PageSize.letter()))
            assert settings.page_width_in_inches() == 8.5
            ```
        """

        return self.page_layout.page_width_in_inches(self.unit)

    def page_height_in_inches(self) -> float:
        """Return the resolved page height in inches.

        Returns:
            Page height converted from the configured page unit to inches.

        Examples:
            ```python
            settings = DocumentSettings(page_layout=PageLayout(PageSize.letter()))
            assert settings.page_height_in_inches() == 11.0
            ```
        """

        return self.page_layout.page_height_in_inches(self.unit)

    def page_margin_inches(self) -> tuple[float, float, float, float]:
        """Return resolved page margins in inches.

        Returns:
            A ``(top, right, bottom, left)`` tuple in inches.

        Examples:
            ```python
            settings = DocumentSettings(
                page_layout=PageLayout(page_margins=PageMargins.all(1.0, unit="in"))
            )
            assert settings.page_margin_inches() == (1.0, 1.0, 1.0, 1.0)
            ```
        """

        return self.page_layout.page_margin_inches(self.unit)

    def text_width_in_inches(self) -> float:
        """Return the writable page width after horizontal margins.

        Returns:
            Non-negative writable width in inches.

        Examples:
            ```python
            settings = DocumentSettings(
                page_layout=PageLayout(
                    PageSize.letter(),
                    PageMargins.all(1.0, unit="in"),
                ),
            )
            assert settings.text_width_in_inches() == 6.5
            ```
        """

        return self.page_layout.text_width_in_inches(self.unit)

    def text_height_in_inches(self) -> float:
        """Return the writable page height after vertical margins.

        Returns:
            Non-negative writable height in inches.

        Examples:
            ```python
            settings = DocumentSettings(
                page_layout=PageLayout(
                    PageSize.letter(),
                    PageMargins.all(1.0, unit="in"),
                ),
            )
            assert settings.text_height_in_inches() == 9.0
            ```
        """

        return self.page_layout.text_height_in_inches(self.unit)

    def get_page_width(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        """Return the page width in a requested unit.

        Args:
            scale: Multiplier applied before conversion.
            unit: Output unit. Defaults to this settings object's default unit.

        Returns:
            The scaled page width in the requested unit.

        Examples:
            ```python
            settings = DocumentSettings(page_layout=PageLayout(PageSize.letter()))
            assert settings.get_page_width(unit="in") == 8.5
            ```
        """

        output_unit = normalize_length_unit(unit) if unit is not None else self.unit
        return inches_to_length(self.page_width_in_inches() * scale, output_unit)

    def get_page_height(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        """Return the page height in a requested unit.

        Args:
            scale: Multiplier applied before conversion.
            unit: Output unit. Defaults to this settings object's default unit.

        Returns:
            The scaled page height in the requested unit.

        Examples:
            ```python
            settings = DocumentSettings(page_layout=PageLayout(PageSize.letter()))
            assert settings.get_page_height(unit="in") == 11.0
            ```
        """

        output_unit = normalize_length_unit(unit) if unit is not None else self.unit
        return inches_to_length(self.page_height_in_inches() * scale, output_unit)

    def get_text_width(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        """Return the writable text width in a requested unit.

        Args:
            scale: Multiplier applied before conversion.
            unit: Output unit. Defaults to this settings object's default unit.

        Returns:
            The scaled writable width in the requested unit.

        Examples:
            ```python
            settings = DocumentSettings(
                page_layout=PageLayout(
                    PageSize.letter(),
                    PageMargins.all(1.0, unit="in"),
                ),
            )
            assert settings.get_text_width(unit="in") == 6.5
            ```
        """

        output_unit = normalize_length_unit(unit) if unit is not None else self.unit
        return inches_to_length(self.text_width_in_inches() * scale, output_unit)

    def get_text_height(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        """Return the writable text height in a requested unit.

        Args:
            scale: Multiplier applied before conversion.
            unit: Output unit. Defaults to this settings object's default unit.

        Returns:
            The scaled writable height in the requested unit.

        Examples:
            ```python
            settings = DocumentSettings(
                page_layout=PageLayout(
                    PageSize.letter(),
                    PageMargins.all(1.0, unit="in"),
                ),
            )
            assert settings.get_text_height(unit="in") == 9.0
            ```
        """

        output_unit = normalize_length_unit(unit) if unit is not None else self.unit
        return inches_to_length(self.text_height_in_inches() * scale, output_unit)

    def resolved_author(self) -> str | None:
        """Return the metadata author string used in file properties.

        Returns:
            The structured metadata author, a semicolon-separated author list,
            or ``None`` when no author data is
            available.

        Examples:
            ```python
            settings = DocumentSettings(authors=["Jane Doe", "John Smith"])
            assert settings.resolved_author() == "Jane Doe; John Smith"
            ```
        """

        if self.metadata.author is not None:
            return self.metadata.author
        if not self.authors:
            return None
        return "; ".join(author.name for author in self.authors)

    def resolved_metadata_title(self, document_title: object) -> str:
        """Return the title written to renderer metadata.

        Args:
            document_title: Visible document title used as the fallback.

        Returns:
            Structured metadata title or the visible document title.
        """

        return self.metadata.title or str(document_title)

    def resolved_metadata_subject(self) -> str | None:
        """Return the subject written to renderer metadata.

        Returns:
            Structured metadata subject.
        """

        return self.metadata.subject

    def resolved_metadata_description(self, document_title: object) -> str:
        """Return the HTML description and descriptive metadata text.

        Args:
            document_title: Visible document title used as the final fallback.

        Returns:
            Description, subject, or visible document title.
        """

        return (
            self.metadata.description
            or self.metadata.subject
            or str(document_title)
        )

    def resolved_metadata_keywords(self) -> tuple[str, ...]:
        """Return metadata keywords as a tuple."""

        return self.metadata.keywords

    def resolved_metadata_keywords_text(self, separator: str = ", ") -> str | None:
        """Return metadata keywords as a joined string."""

        return self.metadata.keywords_text(separator)

    def iter_author_title_lines(self) -> Iterable[tuple[AuthorTitleLine, bool]]:
        """Yield title matter lines with author-boundary markers.

        Yields:
            Tuples of ``(line, is_author_boundary)`` for renderer title matter.

        Examples:
            ```python
            settings = DocumentSettings(authors=["Jane Doe"])
            lines = list(settings.iter_author_title_lines())
            ```
        """

        if self.author_layout.mode == "stacked":
            yield from self._iter_stacked_author_title_lines()
            return
        yield from self._iter_journal_author_title_lines()

    def _iter_stacked_author_title_lines(self) -> Iterable[tuple[AuthorTitleLine, bool]]:
        for author in self.authors:
            lines = author.title_lines(
                corresponding_marker=self.author_layout.corresponding_marker,
                show_affiliations=self.author_layout.show_affiliations,
                show_details=self.author_layout.show_details,
            )
            for index, line in enumerate(lines):
                yield line, index == len(lines) - 1

    def _iter_journal_author_title_lines(self) -> Iterable[tuple[AuthorTitleLine, bool]]:
        if not self.authors:
            return

        # Journal title matter de-duplicates affiliation labels before building
        # the author line so repeated institutions share the same marker.
        affiliation_numbers: dict[str, int] = {}
        ordered_affiliations: list[str] = []
        for author in self.authors:
            for affiliation in author.affiliations:
                label = affiliation.formatted()
                if label not in affiliation_numbers:
                    affiliation_numbers[label] = len(ordered_affiliations) + 1
                    ordered_affiliations.append(label)

        name_fragments: list[Text] = []
        for index, author in enumerate(self.authors):
            if index:
                name_fragments.append(Text(self.author_layout.name_separator))
            markers = [
                str(affiliation_numbers[affiliation.formatted()])
                for affiliation in author.affiliations
            ]
            suffix = ""
            if markers:
                suffix += " " + self.author_layout.affiliation_label_format.format(
                    label=",".join(markers)
                )
            if author.corresponding and self.author_layout.corresponding_marker:
                suffix += self.author_layout.corresponding_marker
            name_fragments.append(Text(f"{author.name}{suffix}"))
        lines: list[AuthorTitleLine] = [
            AuthorTitleLine("name", tuple(name_fragments))
        ]

        if self.author_layout.show_affiliations:
            for affiliation in ordered_affiliations:
                label = affiliation_numbers[affiliation]
                lines.append(
                    AuthorTitleLine(
                        "affiliation",
                        (
                            Text(
                                f"{self.author_layout.affiliation_label_format.format(label=label)} {affiliation}"
                            ),
                        ),
                    )
                )

        if self.author_layout.show_details:
            for author in self.authors:
                detail_fragments = author.detail_fragments()
                if detail_fragments is None:
                    continue
                lines.append(
                    AuthorTitleLine(
                        "detail",
                        (Text(f"{author.name}: "), *detail_fragments),
                    )
                )

        if (
            self.author_layout.corresponding_marker
            and any(author.corresponding for author in self.authors)
        ):
            corresponding_names = ", ".join(
                author.name for author in self.authors if author.corresponding
            )
            lines.insert(
                1 + len(ordered_affiliations) if self.author_layout.show_affiliations else 1,
                AuthorTitleLine(
                    "detail",
                    (
                        Text(
                            f"{self.author_layout.corresponding_marker} Corresponding author: {corresponding_names}"
                        ),
                    ),
                ),
            )

        for index, line in enumerate(lines):
            yield line, index == len(lines) - 1


__all__ = [
    "Affiliation",
    "Author",
    "AuthorLayout",
    "DocumentMetadata",
    "DocumentSettings",
    "PageLayout",
    "PageMargins",
    "PageSize",
]
