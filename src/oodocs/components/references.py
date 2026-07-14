"""Bibliography objects and citation library helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import TYPE_CHECKING, Sequence

from oodocs.core import OODocsError, PathLike

if TYPE_CHECKING:
    from oodocs.components.inline import Citation, Text
    from oodocs.integrations.bibtex import BibtexParser
    from oodocs.styles import TextStyle


_CITATION_STYLE_ALIASES = {
    "numeric": "numeric",
    "numbered": "numeric",
    "ieee": "numeric",
    "author-year": "author-year",
    "authoryear": "author-year",
    "apa": "apa",
    "mla": "mla",
    "chicago": "chicago",
}

_REFERENCE_STYLE_ALIASES = {
    "default": "plain",
    "plain": "plain",
    "numeric": "numbered",
    "numbered": "numbered",
    "apa": "apa",
    "mla": "mla",
    "chicago": "chicago",
    "ieee": "ieee",
}

_REFERENCE_SORT_ALIASES = {
    "citation": "citation",
    "citation-order": "citation",
    "cited": "citation",
    "author": "author",
    "authors": "author",
    "year": "year",
    "date": "year",
    "title": "title",
    "key": "key",
}


def normalize_citation_style(value: str) -> str:
    """Return the canonical name for an inline citation style.

    Args:
        value: Citation style name or alias.

    Returns:
        Canonical citation style.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the style is unsupported.

    Examples:
        ```python
        normalize_citation_style("APA")
        # "apa"
        ```
    """

    if not isinstance(value, str):
        raise TypeError("citation_style must be a string")
    key = re.sub(r"[\s_]+", "-", value.strip().lower())
    if key not in _CITATION_STYLE_ALIASES:
        supported = ", ".join(sorted(_CITATION_STYLE_ALIASES))
        raise ValueError(
            f"Unsupported citation_style: {value!r}. Supported values: {supported}"
        )
    return _CITATION_STYLE_ALIASES[key]


def normalize_reference_style(value: str) -> str:
    """Return the canonical name for a bibliography entry format.

    Args:
        value: Reference style name or alias.

    Returns:
        Canonical reference style.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the style is unsupported.

    Examples:
        ```python
        normalize_reference_style("ieee")
        # "ieee"
        ```
    """

    if not isinstance(value, str):
        raise TypeError("reference_style must be a string")
    key = re.sub(r"[\s_]+", "-", value.strip().lower())
    if key not in _REFERENCE_STYLE_ALIASES:
        supported = ", ".join(sorted(_REFERENCE_STYLE_ALIASES))
        raise ValueError(
            f"Unsupported reference_style: {value!r}. Supported values: {supported}"
        )
    return _REFERENCE_STYLE_ALIASES[key]


def normalize_reference_sort(value: str) -> str:
    """Return the canonical name for reference-list sorting.

    Args:
        value: Reference sort style name or alias.

    Returns:
        Canonical reference sort style.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the sort style is unsupported.

    Examples:
        ```python
        normalize_reference_sort("citation-order")
        # "citation"
        ```
    """

    if not isinstance(value, str):
        raise TypeError("reference_sort must be a string")
    key = re.sub(r"[\s_]+", "-", value.strip().lower())
    if key not in _REFERENCE_SORT_ALIASES:
        supported = ", ".join(sorted(_REFERENCE_SORT_ALIASES))
        raise ValueError(
            f"Unsupported reference_sort: {value!r}. Supported values: {supported}"
        )
    return _REFERENCE_SORT_ALIASES[key]


def format_citation_label(
    source: CitationSource,
    number: int,
    citation_style: str,
) -> str:
    """Format the visible inline citation label for a cited source.

    Args:
        source: Citation source being cited.
        number: Assigned citation number.
        citation_style: Citation style name or alias.

    Returns:
        Visible inline citation label.

    Examples:
        ```python
        source = CitationSource("A Study", authors=("Doe",), year="2024")
        label = format_citation_label(source, 1, "author-year")
        # "(Doe, 2024)"
        ```
    """

    resolved_style = normalize_citation_style(citation_style)
    if resolved_style == "numeric":
        return f"[{number}]"

    author = _short_author_label(source)
    if resolved_style == "mla":
        return f"({author})"
    if resolved_style == "chicago":
        return f"({author} {_citation_year(source)})"
    return f"({author}, {_citation_year(source)})"


def reference_entry_marker(
    number: int,
    *,
    citation_style: str,
    reference_style: str,
) -> str:
    """Return the visible marker prefix for a references-page entry.

    Args:
        number: Assigned reference number.
        citation_style: Active inline citation style.
        reference_style: Active bibliography entry style.

    Returns:
        Marker prefix, or an empty string for unnumbered references.

    Examples:
        ```python
        marker = reference_entry_marker(
            1,
            citation_style="numeric",
            reference_style="plain",
        )
        # "[1]"
        ```
    """

    resolved_citation_style = normalize_citation_style(citation_style)
    resolved_reference_style = normalize_reference_style(reference_style)
    if resolved_citation_style == "numeric" or resolved_reference_style in {"numbered", "ieee"}:
        return f"[{number}]"
    return ""


@dataclass(frozen=True, slots=True)
class CitationDiagnostic:
    """Non-fatal diagnostic retained while citation data is normalized.

    ``raw_value`` and source coordinates make a lossy-looking conversion
    inspectable without forcing the core model to understand BibTeX syntax.
    """

    code: str
    message: str
    entry_key: str | None = None
    field: str | None = None
    raw_value: str | None = None
    line: int | None = None
    column: int | None = None


@dataclass(slots=True, init=False)
class CitationSource:
    """Structured bibliography metadata for a single reference entry.

    Args:
        title: Reference title.
        key: Optional citation key.
        authors: Author names.
        entry_type: Optional source type such as ``article`` or ``manual``.
        organization: Optional organization author.
        publisher: Optional publisher.
        year: Optional publication year.
        url: Optional URL.
        note: Optional note.
        fields: Original citation fields. Parsed BibTeX values are retained
            here even when a convenience attribute exposes a normalized value.

    Examples:
        ```python
        from oodocs import Document, Paragraph, cite

        source = CitationSource(
            "Reliable APIs",
            key="doe2024",
            authors=("Jane Doe",),
            publisher="Journal of Docs",
            year="2024",
        )
        document = Document("Paper", Paragraph("See ", cite("doe2024"), "."), citations=[source])
        ```
    """

    title: str
    key: str | None
    authors: tuple[str, ...] = ()
    entry_type: str | None = None
    organization: str | None = None
    publisher: str | None = None
    year: str | None = None
    url: str | None = None
    note: str | None = None
    journal: str | None = None
    booktitle: str | None = None
    volume: str | None = None
    number: str | None = None
    pages: str | None = None
    doi: str | None = None
    institution: str | None = None
    school: str | None = None
    edition: str | None = None
    chapter: str | None = None
    month: str | None = None
    address: str | None = None
    version: str | None = None
    accessed: str | None = None
    fields: Mapping[str, str]
    diagnostics: tuple[CitationDiagnostic, ...]

    def __init__(
        self,
        title: str,
        *,
        key: str | None = None,
        authors: Sequence[str] = (),
        entry_type: str | None = None,
        organization: str | None = None,
        publisher: str | None = None,
        year: str | None = None,
        url: str | None = None,
        note: str | None = None,
        journal: str | None = None,
        booktitle: str | None = None,
        volume: str | None = None,
        number: str | None = None,
        pages: str | None = None,
        doi: str | None = None,
        institution: str | None = None,
        school: str | None = None,
        edition: str | None = None,
        chapter: str | None = None,
        month: str | None = None,
        address: str | None = None,
        version: str | None = None,
        accessed: str | None = None,
        fields: Mapping[str, object] | None = None,
        diagnostics: Sequence[CitationDiagnostic] = (),
    ) -> None:
        field_entry_type = _mapping_metadata(fields, "entry_type", "entrytype")
        field_key = _mapping_metadata(fields, "key", "id")
        raw_fields = _normalize_citation_fields(fields)
        normalized_authors = tuple(str(author).strip() for author in authors if str(author).strip())
        if not normalized_authors and raw_fields.get("author"):
            normalized_authors = tuple(
                part.strip()
                for part in re.split(r"\s+and\s+", raw_fields["author"], flags=re.IGNORECASE)
                if part.strip()
            )

        self.title = str(title)
        self.key = _optional_text(key) or field_key
        self.authors = normalized_authors
        self.entry_type = _optional_text(entry_type) or field_entry_type
        self.journal = _field_value(journal, raw_fields, "journal")
        self.booktitle = _field_value(booktitle, raw_fields, "booktitle")
        self.institution = _field_value(institution, raw_fields, "institution")
        self.school = _field_value(school, raw_fields, "school")
        self.organization = (
            _field_value(organization, raw_fields, "organization")
            or self.institution
        )
        self.publisher = (
            _field_value(publisher, raw_fields, "publisher")
            or self.journal
            or self.booktitle
            or _field_value(None, raw_fields, "howpublished")
        )
        self.year = _field_value(year, raw_fields, "year")
        self.url = _field_value(url, raw_fields, "url")
        self.note = _field_value(note, raw_fields, "note")
        self.volume = _field_value(volume, raw_fields, "volume")
        self.number = _field_value(number, raw_fields, "number")
        self.pages = _field_value(pages, raw_fields, "pages")
        self.doi = _field_value(doi, raw_fields, "doi")
        self.edition = _field_value(edition, raw_fields, "edition")
        self.chapter = _field_value(chapter, raw_fields, "chapter")
        self.month = _field_value(month, raw_fields, "month")
        self.address = _field_value(address, raw_fields, "address")
        self.version = _field_value(version, raw_fields, "version")
        self.accessed = (
            _field_value(accessed, raw_fields, "accessed")
            or _field_value(None, raw_fields, "urldate")
        )

        _retain_explicit_citation_fields(
            raw_fields,
            title=self.title,
            authors=self.authors,
            organization=organization,
            publisher=publisher,
            year=year,
            url=url,
            note=note,
            journal=journal,
            booktitle=booktitle,
            volume=volume,
            number=number,
            pages=pages,
            doi=doi,
            institution=institution,
            school=school,
            edition=edition,
            chapter=chapter,
            month=month,
            address=address,
            version=version,
            accessed=accessed,
        )
        self.fields = dict(raw_fields)
        self.diagnostics = tuple(diagnostics)

    def as_bibtex_record(self) -> dict[str, str]:
        """Return the retained BibTeX-style record as a raw mapping.

        The record uses lowercase ``entry_type`` and ``key`` metadata keys and
        otherwise returns the original field mapping. Unknown fields and raw
        LaTeX commands are therefore not discarded.
        """

        record = dict(self.fields)
        if self.entry_type is not None:
            record["entry_type"] = self.entry_type
        if self.key is not None:
            record["key"] = self.key
        return record

    def format_reference(self, reference_style: str = "plain") -> str:
        """Format the entry as a plain bibliography string.

        Args:
            reference_style: Reference style name or alias.

        Returns:
            Formatted reference string.
        """

        return _format_reference_text(self, reference_style)

    def reference_fragments(self, reference_style: str = "plain") -> list[Text]:
        """Return renderer-friendly inline fragments for a reference entry.

        Args:
            reference_style: Reference style name or alias.

        Returns:
            Inline fragments, with the URL turned into a hyperlink when present
            in the formatted reference.
        """

        from oodocs.components.inline import Hyperlink, Text

        text = self.format_reference(reference_style)
        links = _reference_links(self)
        if not links:
            return [Text(text)]

        fragments: list[Text] = []
        cursor = 0
        occurrences = sorted(
            (
                (position, visible, target)
                for visible, target in links
                if (position := text.find(visible)) >= 0
            ),
            key=lambda item: item[0],
        )
        for position, visible, target in occurrences:
            if position < cursor:
                continue
            if position > cursor:
                fragments.append(Text(text[cursor:position]))
            fragments.append(Hyperlink.external(target, visible))
            cursor = position + len(visible)
        if cursor < len(text):
            fragments.append(Text(text[cursor:]))
        return fragments or [Text(text)]

    def cite(self, *, style: TextStyle | None = None) -> Citation:
        """Create an inline citation that points to this source.

        Args:
            style: Optional inline style.

        Returns:
            Inline citation fragment.
        """

        from oodocs.components.inline import Citation

        return Citation(self, style=style)


@dataclass(slots=True)
class CitationLibrary:
    """Registry of bibliography entries addressable by citation key.

    Args:
        entries: Optional citation sources to register.

    Examples:
        ```python
        from oodocs import Document, Paragraph, cite

        library = CitationLibrary([
            CitationSource("Reliable APIs", key="doe2024", authors=("Jane Doe",))
        ])
        document = Document("Paper", Paragraph("See ", cite("doe2024"), "."), citations=library)
        ```
    """

    entries: dict[str, CitationSource] = field(default_factory=dict)

    def __init__(self, entries: Sequence[CitationSource] | None = None) -> None:
        self.entries = {}
        if entries is not None:
            for entry in entries:
                self.add(entry)

    def add(self, entry: CitationSource) -> None:
        """Register a citation source under its key.

        Args:
            entry: Citation source to register.

        Raises:
            OODocsError: If the entry has no key or duplicates an existing key.
        """

        if not entry.key:
            raise OODocsError(
                "CitationSource.key is required when adding entries to a CitationLibrary"
            )
        if entry.key in self.entries:
            raise OODocsError(f"Duplicate citation key: {entry.key!r}")
        self.entries[entry.key] = entry

    def resolve(self, key: str) -> CitationSource:
        """Resolve a registered citation key to a source entry.

        Args:
            key: Citation key.

        Returns:
            Registered citation source.

        Raises:
            OODocsError: If the key is unknown.
        """

        if key not in self.entries:
            raise OODocsError(f"Unknown citation key: {key!r}")
        return self.entries[key]

    def cite(self, key: str, *, style: TextStyle | None = None) -> Citation:
        """Create an inline citation from a registered citation key.

        Args:
            key: Citation key.
            style: Optional inline style.

        Returns:
            Inline citation fragment.
        """

        from oodocs.components.inline import Citation

        return Citation(key, style=style)

    @classmethod
    def from_bibtex(
        cls,
        source: str,
        *,
        parser: BibtexParser | None = None,
    ) -> CitationLibrary:
        """Parse BibTeX text into a citation library.

        Args:
            source: BibTeX source text.
            parser: Optional parser backend. The built-in dependency-free
                parser is used when omitted.

        Returns:
            Citation library containing parsed entries.

        Examples:
            ```python
            library = CitationLibrary.from_bibtex(
                "@article{doe2024, title={Reliable APIs}, author={Doe, Jane}}"
            )
            ```
        """

        from oodocs.integrations.bibtex import BuiltinBibtexParser

        backend = parser or BuiltinBibtexParser()
        return cls(tuple(backend.parse(source)))

    @classmethod
    def from_bibtex_file(
        cls,
        path: PathLike,
        *,
        encoding: str = "utf-8",
        parser: BibtexParser | None = None,
    ) -> CitationLibrary:
        """Load a BibTeX file into a citation library.

        Args:
            path: BibTeX file path.
            encoding: Text encoding used to read the file.
            parser: Optional parser backend.

        Returns:
            Citation library containing parsed entries.

        Examples:
            ```python
            library = CitationLibrary.from_bibtex_file("references.bib")
            ```
        """

        return cls.from_bibtex(
            Path(path).read_text(encoding=encoding),
            parser=parser,
        )


def coerce_citation_library(
    value: CitationLibrary | Sequence[CitationSource] | str | None,
) -> CitationLibrary:
    """Normalize any supported citation input into a citation library.

    Args:
        value: Existing library, citation sources, BibTeX source text, or
            ``None``.

    Returns:
        Citation library instance.

    Examples:
        ```python
        library = coerce_citation_library(
            [CitationSource("Reliable APIs", key="doe2024")]
        )
        ```
    """

    if value is None:
        return CitationLibrary()
    if isinstance(value, CitationLibrary):
        return value
    if isinstance(value, str):
        return CitationLibrary.from_bibtex(value)
    return CitationLibrary(value)


def _normalize_citation_fields(fields: Mapping[str, object] | None) -> dict[str, str]:
    if fields is None:
        return {}
    normalized: dict[str, str] = {}
    for name, value in fields.items():
        key = str(name).strip().lower()
        if not key or key in {"entry_type", "entrytype", "key", "id"} or value is None:
            continue
        normalized[key] = str(value)
    return normalized


def _mapping_metadata(
    fields: Mapping[str, object] | None,
    *names: str,
) -> str | None:
    if fields is None:
        return None
    accepted = {name.casefold() for name in names}
    for name, value in fields.items():
        if str(name).casefold() in accepted:
            return _optional_text(value)
    return None


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _field_value(
    explicit: object | None,
    fields: Mapping[str, str],
    name: str,
) -> str | None:
    return _optional_text(explicit) or _optional_text(fields.get(name))


def _retain_explicit_citation_fields(
    fields: dict[str, str],
    *,
    title: str,
    authors: Sequence[str],
    **values: object | None,
) -> None:
    fields.setdefault("title", title)
    if authors:
        fields.setdefault("author", " and ".join(authors))
    for name, value in values.items():
        normalized = _optional_text(value)
        if normalized is not None:
            fields.setdefault(name, normalized)


def _format_reference_text(source: CitationSource, reference_style: str) -> str:
    resolved_style = normalize_reference_style(reference_style)
    if resolved_style in {"plain", "numbered"}:
        return _format_plain_reference(source)
    if resolved_style == "apa":
        return _format_apa_reference(source)
    if resolved_style == "mla":
        return _format_mla_reference(source)
    if resolved_style == "chicago":
        return _format_chicago_reference(source)
    if resolved_style == "ieee":
        return _format_ieee_reference(source)
    raise ValueError(f"Unsupported reference_style: {reference_style!r}")


def _format_plain_reference(source: CitationSource) -> str:
    return _join_reference_segments(
        _display_author_text(source),
        source.title,
        _container_title(source),
        _publication_responsibility(source),
        _edition_chapter(source),
        _volume_issue_pages(source, style="plain"),
        _publication_date(source),
        _version_text(source),
        _doi_url(source.doi),
        source.url,
        _accessed_text(source),
        source.note,
    )


def _format_apa_reference(source: CitationSource) -> str:
    return _join_reference_segments(
        _apa_author_text(source),
        f"({_publication_date(source) or 'n.d.'})",
        source.title,
        _apa_publication_text(source),
        _publication_responsibility(source),
        _edition_chapter(source),
        _version_text(source),
        _doi_url(source.doi),
        source.url,
        _accessed_text(source),
        source.note,
    )


def _format_mla_reference(source: CitationSource) -> str:
    title = _clean_reference_segment(source.title)
    quoted_title = (
        f'"{title}"'
        if title and _entry_uses_article_title(source)
        else title
    )
    return _join_reference_segments(
        _mla_author_text(source),
        quoted_title,
        _container_title(source),
        _publication_responsibility(source),
        _volume_issue_pages(source, style="mla"),
        _publication_date(source),
        _edition_chapter(source),
        _version_text(source),
        _doi_url(source.doi),
        source.url,
        _accessed_text(source),
        source.note,
    )


def _format_chicago_reference(source: CitationSource) -> str:
    publication = _join_comma_segments(
        _container_title(source),
        _volume_issue_pages(source, style="chicago"),
        _publication_responsibility(source),
        _publication_date(source),
    )
    return _join_reference_segments(
        _mla_author_text(source),
        source.title,
        publication,
        _edition_chapter(source),
        _version_text(source),
        _doi_url(source.doi),
        source.url,
        _accessed_text(source),
        source.note,
    )


def _format_ieee_reference(source: CitationSource) -> str:
    title = _clean_reference_segment(source.title)
    quoted_title = f'"{title}"' if title and _entry_uses_article_title(source) else title
    publication = _join_comma_segments(
        _container_title(source),
        _volume_issue_pages(source, style="ieee"),
        _publication_responsibility(source),
        _publication_date(source),
    )
    return _join_reference_segments(
        _display_author_text(source),
        quoted_title,
        publication,
        _edition_chapter(source),
        _version_text(source),
        _doi_url(source.doi),
        source.url,
        _accessed_text(source),
        source.note,
    )


def _entry_uses_article_title(source: CitationSource) -> bool:
    return (source.entry_type or "").lower() in {
        "article",
        "inbook",
        "incollection",
        "inproceedings",
        "conference",
    }


def _container_title(source: CitationSource) -> str | None:
    return source.journal or source.booktitle


def _publication_responsibility(source: CitationSource) -> str | None:
    container = _clean_reference_segment(_container_title(source))
    values = (
        source.publisher,
        source.institution,
        source.school,
        source.organization,
        source.address,
    )
    unique = tuple(
        value
        for value in _unique_text(values)
        if container is None or value.casefold() != container.casefold()
    )
    return _join_comma_segments(*unique)


def _publication_date(source: CitationSource) -> str | None:
    return _join_space_segments(source.month, source.year)


def _edition_chapter(source: CitationSource) -> str | None:
    edition = f"{source.edition} ed." if source.edition else None
    chapter = f"chap. {source.chapter}" if source.chapter else None
    return _join_comma_segments(edition, chapter)


def _version_text(source: CitationSource) -> str | None:
    return f"Version {source.version}" if source.version else None


def _accessed_text(source: CitationSource) -> str | None:
    return f"Accessed {source.accessed}" if source.accessed else None


def _volume_issue_pages(source: CitationSource, *, style: str) -> str | None:
    if style == "apa":
        volume = source.volume
        if volume and source.number:
            volume = f"{volume}({source.number})"
        elif source.number:
            volume = f"({source.number})"
        return _join_comma_segments(volume, source.pages)

    volume = f"vol. {source.volume}" if source.volume else None
    issue = f"no. {source.number}" if source.number else None
    page_prefix = "pp." if source.pages and ("-" in source.pages or "–" in source.pages) else "p."
    pages = f"{page_prefix} {source.pages}" if source.pages else None
    return _join_comma_segments(volume, issue, pages)


def _apa_publication_text(source: CitationSource) -> str | None:
    return _join_comma_segments(
        _container_title(source),
        _volume_issue_pages(source, style="apa"),
    )


def _join_space_segments(*segments: str | None) -> str | None:
    cleaned = [item for segment in segments if (item := _clean_reference_segment(segment))]
    return " ".join(cleaned) or None


def _unique_text(values: Sequence[str | None]) -> tuple[str | None, ...]:
    seen: set[str] = set()
    result: list[str | None] = []
    for value in values:
        cleaned = _clean_reference_segment(value)
        if cleaned is None or cleaned.casefold() in seen:
            continue
        seen.add(cleaned.casefold())
        result.append(cleaned)
    return tuple(result)


def _doi_url(doi: str | None) -> str | None:
    normalized = _optional_text(doi)
    if normalized is None:
        return None
    if normalized.lower().startswith("doi:"):
        normalized = normalized[4:].strip()
    if normalized.lower().startswith(("https://doi.org/", "http://doi.org/")):
        suffix = re.sub(
            r"^https?://doi\.org/",
            "",
            normalized,
            count=1,
            flags=re.IGNORECASE,
        )
        return f"https://doi.org/{suffix}"
    return f"https://doi.org/{normalized}"


def _reference_links(source: CitationSource) -> tuple[tuple[str, str], ...]:
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for visible, target in (
        (_doi_url(source.doi), _doi_url(source.doi)),
        (source.url, source.url),
    ):
        if visible is None or target is None or visible in seen:
            continue
        seen.add(visible)
        links.append((visible, target))
    return tuple(links)


def _join_reference_segments(*segments: str | None) -> str:
    cleaned = list(_unique_text(segments))
    if not cleaned:
        return ""
    return ". ".join(cleaned) + "."


def _join_comma_segments(*segments: str | None) -> str | None:
    cleaned = [
        cleaned_segment
        for segment in segments
        if (cleaned_segment := _clean_reference_segment(segment)) is not None
    ]
    if not cleaned:
        return None
    return ", ".join(cleaned)


def _clean_reference_segment(segment: str | None) -> str | None:
    if segment is None:
        return None
    cleaned = " ".join(str(segment).split()).strip().rstrip(".")
    return cleaned or None


def _display_author_text(source: CitationSource) -> str | None:
    if source.authors:
        return ", ".join(source.authors)
    return source.organization


def _apa_author_text(source: CitationSource) -> str | None:
    if source.authors:
        return _join_apa_author_names(source.authors)
    return source.organization


def _mla_author_text(source: CitationSource) -> str | None:
    if source.authors:
        names = [_invert_person_name(author) for author in source.authors]
        if len(names) == 1:
            return names[0]
        return ", ".join(names[:-1]) + f", and {names[-1]}"
    return source.organization


def _join_apa_author_names(authors: Sequence[str]) -> str:
    names = [_apa_person_name(author) for author in authors if author.strip()]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, & {names[1]}"
    return ", ".join(names[:-1]) + f", & {names[-1]}"


def _apa_person_name(name: str) -> str:
    cleaned = _clean_reference_segment(name)
    if cleaned is None:
        return ""
    if "," in cleaned:
        surname, given = (part.strip() for part in cleaned.split(",", 1))
        initials = _initials(given)
        return f"{surname}, {initials}" if initials else surname

    parts = cleaned.split()
    if len(parts) == 1:
        return cleaned
    surname = parts[-1]
    initials = _initials(" ".join(parts[:-1]))
    return f"{surname}, {initials}" if initials else surname


def _invert_person_name(name: str) -> str:
    cleaned = _clean_reference_segment(name)
    if cleaned is None:
        return ""
    if "," in cleaned:
        return cleaned
    parts = cleaned.split()
    if len(parts) == 1:
        return cleaned
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _initials(given_names: str) -> str:
    initials: list[str] = []
    for part in re.split(r"\s+", given_names.strip()):
        for piece in part.split("-"):
            cleaned = re.sub(r"[^A-Za-z]", "", piece)
            if cleaned:
                initials.append(f"{cleaned[0].upper()}.")
    return " ".join(initials)


def _short_author_label(source: CitationSource) -> str:
    if source.authors:
        surnames = [_family_name(author) for author in source.authors if author.strip()]
        if len(surnames) == 1:
            return surnames[0]
        if len(surnames) == 2:
            return f"{surnames[0]} & {surnames[1]}"
        return f"{surnames[0]} et al."
    if source.organization:
        return source.organization
    return _short_title_label(source.title)


def _family_name(name: str) -> str:
    cleaned = _clean_reference_segment(name)
    if cleaned is None:
        return ""
    if "," in cleaned:
        return cleaned.split(",", 1)[0].strip()
    return cleaned.split()[-1]


def _short_title_label(title: str) -> str:
    cleaned = _clean_reference_segment(title) or "Untitled"
    words = cleaned.split()
    if len(words) <= 3:
        return cleaned
    return " ".join(words[:3])


def _citation_year(source: CitationSource) -> str:
    return source.year or "n.d."


__all__ = [
    "CitationDiagnostic",
    "CitationLibrary",
    "CitationSource",
    "format_citation_label",
    "reference_entry_marker",
]
