"""Structured people and affiliation metadata for title matter.

Attributes:
    AffiliationInput: Accepted shorthand for affiliation metadata.
    AuthorInput: Accepted shorthand for author metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from oodocs.components.inline import Hyperlink, Text


@dataclass(slots=True)
class Affiliation:
    """Structured affiliation metadata for an author.

    Attributes:
        label: Preformatted affiliation label. When set, it overrides the
            structured fields.
        department: Department or lab name.
        organization: Institution or company name.
        city: Optional city.
        country: Optional country.

    Raises:
        ValueError: If every field is empty.

    Examples:
        ```python
        from oodocs import Author, Document, DocumentSettings, Paragraph, TitleMatter

        affiliation = Affiliation(
            department="AI Lab",
            organization="Example University",
            country="KR",
        )
        author = Author("Jane Doe", affiliations=[affiliation])
        document = Document(
            "Research Note",
            Paragraph("Summary."),
            settings=DocumentSettings(title_matter=TitleMatter(authors=[author])),
        )
        ```
    """

    label: str | None = None
    department: str | None = None
    organization: str | None = None
    city: str | None = None
    country: str | None = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.label,
                self.department,
                self.organization,
                self.city,
                self.country,
            )
        ):
            raise ValueError("Affiliation requires at least one populated field")

    def formatted(self) -> str:
        """Return a single-line affiliation label.

        Returns:
            Preformatted label or comma-separated structured fields.
        """

        if self.label is not None:
            return self.label
        return ", ".join(
            part
            for part in (
                self.department,
                self.organization,
                self.city,
                self.country,
            )
            if part
        )


AffiliationInput = Affiliation | str


@dataclass(slots=True)
class AuthorLayout:
    """Configurable title-matter layout for structured author metadata.

    Attributes:
        mode: Layout mode, either ``"journal"`` or ``"stacked"``.
        show_affiliations: Whether to show affiliation lines.
        show_details: Whether to show email, ORCID, position, and note details.
        name_separator: Separator between author names in journal mode.
        affiliation_label_format: Format string for affiliation markers.
        corresponding_marker: Marker appended to corresponding authors.

    Raises:
        ValueError: If the mode or affiliation label format is unsupported.

    Examples:
        ```python
        from oodocs import Author, Document, DocumentSettings, Paragraph, TitleMatter

        layout = AuthorLayout(mode="journal", corresponding_marker="*")
        settings = DocumentSettings(
            title_matter=TitleMatter(
                authors=[Author("Jane Doe", corresponding=True)],
                author_layout=layout,
            )
        )
        document = Document("Research Note", Paragraph("Summary."), settings=settings)
        ```
    """

    mode: str = "journal"
    show_affiliations: bool = True
    show_details: bool = True
    name_separator: str = ", "
    affiliation_label_format: str = "[{label}]"
    corresponding_marker: str = "*"

    def __post_init__(self) -> None:
        if self.mode not in {"journal", "stacked"}:
            raise ValueError(f"Unsupported author layout mode: {self.mode!r}")
        if "{label}" not in self.affiliation_label_format:
            raise ValueError(
                "author affiliation_label_format must contain a '{label}' placeholder"
            )


@dataclass(slots=True, frozen=True)
class AuthorTitleLine:
    """A typed title-matter line derived from a structured author.

    Attributes:
        kind: Line kind: ``"name"``, ``"affiliation"``, or ``"detail"``.
        fragments: Inline fragments rendered for the line.

    Raises:
        ValueError: If ``kind`` is unsupported or no fragments are supplied.

    Examples:
        ```python
        from oodocs import Author

        author = Author("Jane Doe", affiliations=["Example University"])
        lines = author.title_lines()
        ```
    """

    kind: str
    fragments: tuple[Text, ...]

    def __post_init__(self) -> None:
        if self.kind not in {"name", "affiliation", "detail"}:
            raise ValueError(f"Unsupported author title line kind: {self.kind!r}")
        if not self.fragments:
            raise ValueError("AuthorTitleLine.fragments must not be empty")


@dataclass(slots=True, init=False)
class Author:
    """Structured author metadata for title matter and document metadata.

    Args:
        name: Author display name.
        affiliations: Optional affiliations as ``Affiliation`` objects or
            simple labels.
        email: Optional email address.
        position: Optional position or role.
        corresponding: Whether this is a corresponding author.
        orcid: Optional ORCID identifier or URL.
        note: Optional author note.

    Examples:
        ```python
        from oodocs import Author, Document, DocumentSettings, Paragraph, TitleMatter

        author = Author(
            "Jane Doe",
            affiliations=["Example University"],
            email="jane@example.edu",
            corresponding=True,
        )
        settings = DocumentSettings(title_matter=TitleMatter(authors=[author]))
        doc = Document("Research Note", Paragraph("Summary."), settings=settings)
        ```
    """

    name: str
    affiliations: tuple[Affiliation, ...]
    email: str | None
    position: str | None
    corresponding: bool
    orcid: str | None
    note: str | None

    def __init__(
        self,
        name: str,
        *,
        affiliations: Sequence[AffiliationInput] | None = None,
        email: str | None = None,
        position: str | None = None,
        corresponding: bool = False,
        orcid: str | None = None,
        note: str | None = None,
    ) -> None:
        self.name = name
        self.affiliations = tuple(
            value if isinstance(value, Affiliation) else Affiliation(label=value)
            for value in (affiliations or ())
        )
        self.email = email
        self.position = position
        self.corresponding = corresponding
        self.orcid = orcid
        self.note = note

    def display_name(self) -> str:
        """Return the visible author label.

        Returns:
            Author display name.
        """

        return self.name

    def title_lines(
        self,
        *,
        corresponding_marker: str = "*",
        show_affiliations: bool = True,
        show_details: bool = True,
    ) -> tuple[AuthorTitleLine, ...]:
        """Return renderer-ready title-matter lines for this author.

        Args:
            corresponding_marker: Marker appended to corresponding authors.
            show_affiliations: Whether to include affiliation lines.
            show_details: Whether to include detail lines.

        Returns:
            Title lines for this author.
        """

        lines: list[AuthorTitleLine] = [
            AuthorTitleLine(
                "name",
                (Text(self.display_name_with_marker(corresponding_marker)),),
            )
        ]
        if show_affiliations:
            for affiliation in self.affiliations:
                lines.append(
                    AuthorTitleLine(
                        "affiliation",
                        (Text(affiliation.formatted()),),
                    )
                )
        detail = self.detail_fragments()
        if show_details and detail is not None:
            lines.append(AuthorTitleLine("detail", tuple(detail)))
        return tuple(lines)

    def display_name_with_marker(self, marker: str = "*") -> str:
        """Return the visible author label with the corresponding marker when needed.

        Args:
            marker: Marker appended for corresponding authors.

        Returns:
            Display name with marker when applicable.
        """

        if self.corresponding and marker:
            return f"{self.name}{marker}"
        return self.name

    def detail_fragments(self) -> list[Text] | None:
        """Return supplemental detail fragments for title matter.

        Returns:
            Detail fragments, or ``None`` when no details are configured.
        """

        fragments: list[Text] = []

        def append_separator() -> None:
            if fragments:
                fragments.append(Text(" | "))

        if self.position:
            append_separator()
            fragments.append(Text(self.position))
        if self.email:
            append_separator()
            fragments.append(Hyperlink.external(f"mailto:{self.email}", self.email))
        if self.orcid:
            append_separator()
            normalized_orcid = self.orcid.removeprefix("https://orcid.org/").strip("/")
            fragments.append(Text("ORCID "))
            fragments.append(
                Hyperlink.external(
                    f"https://orcid.org/{normalized_orcid}",
                    normalized_orcid,
                )
            )
        if self.note:
            append_separator()
            fragments.append(Text(self.note))
        return fragments or None


AuthorInput = Author | str


def coerce_authors(values: Sequence[AuthorInput] | None) -> tuple[Author, ...]:
    """Normalize simple author inputs into structured authors.

    Args:
        values: Author objects, strings, or ``None``.

    Returns:
        Tuple of structured author objects.

    Examples:
        ```python
        authors = coerce_authors(["Jane Doe", Author("John Smith")])
        ```
    """

    if values is None:
        return ()
    return tuple(
        value if isinstance(value, Author) else Author(str(value))
        for value in values
    )


def coerce_author_layout(value: AuthorLayout | None) -> AuthorLayout:
    """Normalize document author-layout configuration.

    Args:
        value: Author layout or ``None``.

    Returns:
        Supplied layout or the default layout.

    Examples:
        ```python
        layout = coerce_author_layout(None)
        ```
    """

    return value if value is not None else AuthorLayout()


__all__ = [
    "Affiliation",
    "AffiliationInput",
    "Author",
    "AuthorInput",
    "AuthorLayout",
    "AuthorTitleLine",
]
