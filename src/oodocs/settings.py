"""User-facing configuration objects for documents and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

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
from oodocs.layout.theme import (
    BoxStyle,
    BlockOptions,
    CaptionOptions,
    CitationOptions,
    GeneratedPageOptions,
    HeadingNumbering,
    ListStyle,
    PageNumberOptions,
    ParagraphStyle,
    TableStyle,
    TextStyle,
    TitleMatterOptions,
    TypographyOptions,
    Theme,
)


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
        from oodocs import Document, DocumentSettings, PageSize, Paragraph

        settings = DocumentSettings(page_size=PageSize.letter())
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
        from oodocs import Document, DocumentSettings, PageMargins, Paragraph

        settings = DocumentSettings(page_margins=PageMargins(1.0, 0.8, 1.0, 0.8, unit="in"))
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
class DocumentSettings:
    """Document-level metadata and rendering configuration.

    Args:
        metadata_author: Author string written to file metadata. Defaults to
            the configured document authors when omitted.
        summary: Optional document summary or description.
        subtitle: Optional subtitle rendered with title matter.
        authors: Optional author metadata used for title matter.
        author_layout: Layout rules for author title matter.
        cover_page: Whether renderers should place title matter on a separate
            cover page when supported.
        unit: Default length unit for values that do not carry an explicit unit.
        page_size: Physical page size.
        page_margins: Physical page margins.
        page_items: Absolute-positioned page decorations or overlays.
        theme: Rendering theme.

    Examples:
        ```python
        from oodocs import Author, Document, DocumentSettings, PageMargins, PageSize, Paragraph

        settings = DocumentSettings(
            authors=[Author("Jane Doe", email="jane@example.edu")],
            page_size=PageSize.letter(),
            page_margins=PageMargins.symmetric(vertical=1.0, horizontal=0.8, unit="in"),
            cover_page=True,
        )
        document = Document("Study Report", Paragraph("Findings."), settings=settings)
        ```
    """

    metadata_author: str | None
    summary: str | None
    subtitle: list[Text] | None
    authors: tuple[Author, ...]
    author_layout: AuthorLayout
    cover_page: bool
    unit: str
    page_size: PageSize
    page_margins: PageMargins
    page_items: tuple[PositionedItem, ...]
    theme: Theme

    def __init__(
        self,
        *,
        metadata_author: str | None = None,
        summary: str | None = None,
        subtitle: InlineInput | None = None,
        authors: Sequence[AuthorInput] | None = None,
        author_layout: AuthorLayout | None = None,
        cover_page: bool = False,
        unit: str = "in",
        page_size: PageSize | None = None,
        page_margins: PageMargins | None = None,
        page_items: Sequence[PositionedItem] | None = None,
        theme: Theme | None = None,
    ) -> None:
        self.metadata_author = metadata_author
        self.summary = summary
        self.subtitle = coerce_inlines((subtitle,)) if subtitle is not None else None
        self.authors = coerce_authors(authors)
        self.author_layout = coerce_author_layout(author_layout)
        self.cover_page = cover_page
        self.unit = normalize_length_unit(unit)
        self.page_size = page_size or PageSize.a4()
        self.page_margins = page_margins or PageMargins()
        self.page_items = coerce_positioned_items(page_items)
        self.theme = theme or Theme()

    def page_width_in_inches(self) -> float:
        """Return the resolved page width in inches.

        Returns:
            Page width converted from the configured page unit to inches.

        Examples:
            ```python
            settings = DocumentSettings(page_size=PageSize.letter())
            assert settings.page_width_in_inches() == 8.5
            ```
        """

        return self.page_size.width_in_inches(self.unit)

    def page_height_in_inches(self) -> float:
        """Return the resolved page height in inches.

        Returns:
            Page height converted from the configured page unit to inches.

        Examples:
            ```python
            settings = DocumentSettings(page_size=PageSize.letter())
            assert settings.page_height_in_inches() == 11.0
            ```
        """

        return self.page_size.height_in_inches(self.unit)

    def page_margin_inches(self) -> tuple[float, float, float, float]:
        """Return resolved page margins in inches.

        Returns:
            A ``(top, right, bottom, left)`` tuple in inches.

        Examples:
            ```python
            settings = DocumentSettings(page_margins=PageMargins.all(1.0, unit="in"))
            assert settings.page_margin_inches() == (1.0, 1.0, 1.0, 1.0)
            ```
        """

        return (
            self.page_margins.top_in_inches(self.unit),
            self.page_margins.right_in_inches(self.unit),
            self.page_margins.bottom_in_inches(self.unit),
            self.page_margins.left_in_inches(self.unit),
        )

    def text_width_in_inches(self) -> float:
        """Return the writable page width after horizontal margins.

        Returns:
            Non-negative writable width in inches.

        Examples:
            ```python
            settings = DocumentSettings(
                page_size=PageSize.letter(),
                page_margins=PageMargins.all(1.0, unit="in"),
            )
            assert settings.text_width_in_inches() == 6.5
            ```
        """

        _, right, _, left = self.page_margin_inches()
        return max(self.page_width_in_inches() - left - right, 0)

    def text_height_in_inches(self) -> float:
        """Return the writable page height after vertical margins.

        Returns:
            Non-negative writable height in inches.

        Examples:
            ```python
            settings = DocumentSettings(
                page_size=PageSize.letter(),
                page_margins=PageMargins.all(1.0, unit="in"),
            )
            assert settings.text_height_in_inches() == 9.0
            ```
        """

        top, _, bottom, _ = self.page_margin_inches()
        return max(self.page_height_in_inches() - top - bottom, 0)

    def get_page_width(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        """Return the page width in a requested unit.

        Args:
            scale: Multiplier applied before conversion.
            unit: Output unit. Defaults to this settings object's default unit.

        Returns:
            The scaled page width in the requested unit.

        Examples:
            ```python
            settings = DocumentSettings(page_size=PageSize.letter())
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
            settings = DocumentSettings(page_size=PageSize.letter())
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
                page_size=PageSize.letter(),
                page_margins=PageMargins.all(1.0, unit="in"),
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
                page_size=PageSize.letter(),
                page_margins=PageMargins.all(1.0, unit="in"),
            )
            assert settings.get_text_height(unit="in") == 9.0
            ```
        """

        output_unit = normalize_length_unit(unit) if unit is not None else self.unit
        return inches_to_length(self.text_height_in_inches() * scale, output_unit)

    def resolved_author(self) -> str | None:
        """Return the metadata author string used in file properties.

        Returns:
            The explicit metadata author, a semicolon-separated author list, or
            ``None`` when no author data is available.

        Examples:
            ```python
            settings = DocumentSettings(authors=["Jane Doe", "John Smith"])
            assert settings.resolved_author() == "Jane Doe; John Smith"
            ```
        """

        if self.metadata_author is not None:
            return self.metadata_author
        if not self.authors:
            return None
        return "; ".join(author.name for author in self.authors)

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
    "BlockOptions",
    "BoxStyle",
    "CaptionOptions",
    "CitationOptions",
    "DocumentSettings",
    "GeneratedPageOptions",
    "HeadingNumbering",
    "ListStyle",
    "PageNumberOptions",
    "PageMargins",
    "PageSize",
    "ParagraphStyle",
    "TableStyle",
    "TextStyle",
    "TitleMatterOptions",
    "TypographyOptions",
    "Theme",
]
