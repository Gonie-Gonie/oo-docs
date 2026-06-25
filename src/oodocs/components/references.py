"""Bibliography objects and citation library helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING, Sequence

from oodocs.core import OODocsError

if TYPE_CHECKING:
    from oodocs.components.inline import Citation, Text
    from oodocs.layout.theme import TextStyle


_CITATION_FORMAT_ALIASES = {
    "numeric": "numeric",
    "numbered": "numeric",
    "ieee": "numeric",
    "author-year": "author-year",
    "authoryear": "author-year",
    "apa": "apa",
    "mla": "mla",
    "chicago": "chicago",
}

_REFERENCE_FORMAT_ALIASES = {
    "default": "plain",
    "plain": "plain",
    "numeric": "numbered",
    "numbered": "numbered",
    "apa": "apa",
    "mla": "mla",
    "chicago": "chicago",
    "ieee": "ieee",
}


def normalize_citation_format(value: str) -> str:
    """Return the canonical name for an inline citation format.

    Args:
        value: Citation format name or alias.

    Returns:
        Canonical citation format.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the format is unsupported.
    """

    if not isinstance(value, str):
        raise TypeError("citation_format must be a string")
    key = re.sub(r"[\s_]+", "-", value.strip().lower())
    if key not in _CITATION_FORMAT_ALIASES:
        supported = ", ".join(sorted(_CITATION_FORMAT_ALIASES))
        raise ValueError(
            f"Unsupported citation_format: {value!r}. Supported values: {supported}"
        )
    return _CITATION_FORMAT_ALIASES[key]


def normalize_reference_format(value: str) -> str:
    """Return the canonical name for a bibliography entry format.

    Args:
        value: Reference format name or alias.

    Returns:
        Canonical reference format.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the format is unsupported.
    """

    if not isinstance(value, str):
        raise TypeError("reference_format must be a string")
    key = re.sub(r"[\s_]+", "-", value.strip().lower())
    if key not in _REFERENCE_FORMAT_ALIASES:
        supported = ", ".join(sorted(_REFERENCE_FORMAT_ALIASES))
        raise ValueError(
            f"Unsupported reference_format: {value!r}. Supported values: {supported}"
        )
    return _REFERENCE_FORMAT_ALIASES[key]


def format_citation_label(
    source: CitationSource,
    number: int,
    citation_format: str,
) -> str:
    """Format the visible inline citation label for a cited source.

    Args:
        source: Citation source being cited.
        number: Assigned citation number.
        citation_format: Citation format name or alias.

    Returns:
        Visible inline citation label.
    """

    resolved_format = normalize_citation_format(citation_format)
    if resolved_format == "numeric":
        return f"[{number}]"

    author = _short_author_label(source)
    if resolved_format == "mla":
        return f"({author})"
    if resolved_format == "chicago":
        return f"({author} {_citation_year(source)})"
    return f"({author}, {_citation_year(source)})"


def reference_entry_marker(
    number: int,
    *,
    citation_format: str,
    reference_format: str,
) -> str:
    """Return the visible marker prefix for a references-page entry.

    Args:
        number: Assigned reference number.
        citation_format: Active inline citation format.
        reference_format: Active bibliography entry format.

    Returns:
        Marker prefix, or an empty string for unnumbered references.
    """

    resolved_citation_format = normalize_citation_format(citation_format)
    resolved_reference_format = normalize_reference_format(reference_format)
    if resolved_citation_format == "numeric" or resolved_reference_format in {"numbered", "ieee"}:
        return f"[{number}]"
    return ""


@dataclass(slots=True, init=False)
class CitationSource:
    """Structured bibliography metadata for a single reference entry.

    Args:
        title: Reference title.
        key: Optional citation key.
        authors: Author names.
        organization: Optional organization author.
        publisher: Optional publisher, journal, or venue.
        year: Optional publication year.
        url: Optional URL.
        note: Optional note.
    """

    title: str
    key: str | None
    authors: tuple[str, ...] = ()
    organization: str | None = None
    publisher: str | None = None
    year: str | None = None
    url: str | None = None
    note: str | None = None

    def __init__(
        self,
        title: str,
        *,
        key: str | None = None,
        authors: Sequence[str] = (),
        organization: str | None = None,
        publisher: str | None = None,
        year: str | None = None,
        url: str | None = None,
        note: str | None = None,
    ) -> None:
        self.title = title
        self.key = key
        self.authors = tuple(authors)
        self.organization = organization
        self.publisher = publisher
        self.year = year
        self.url = url
        self.note = note

    def format_reference(self, reference_format: str = "plain") -> str:
        """Format the entry as a plain bibliography string.

        Args:
            reference_format: Reference format name or alias.

        Returns:
            Formatted reference string.
        """

        return _format_reference_text(self, reference_format)

    def reference_fragments(self, reference_format: str = "plain") -> list[Text]:
        """Return renderer-friendly inline fragments for a reference entry.

        Args:
            reference_format: Reference format name or alias.

        Returns:
            Inline fragments, with the URL turned into a hyperlink when present
            in the formatted reference.
        """

        from oodocs.components.inline import Hyperlink, Text

        text = self.format_reference(reference_format)
        if not self.url or self.url not in text:
            return [Text(text)]

        before, after = text.split(self.url, 1)
        fragments: list[Text] = []
        if before:
            fragments.append(Text(before))
        fragments.append(Hyperlink.external(self.url, self.url))
        if after:
            fragments.append(Text(after))
        return fragments

    def cite(self, *, style: TextStyle | None = None) -> Citation:
        """Create an inline citation that points to this source.

        Args:
            style: Optional inline style.

        Returns:
            Inline citation fragment.
        """

        from oodocs.components.inline import Citation

        return Citation.reference(self, style=style)


@dataclass(slots=True)
class CitationLibrary:
    """Registry of bibliography entries addressable by citation key.

    Args:
        entries: Optional citation sources to register.
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

        return Citation.reference(key, style=style)

    @classmethod
    def from_bibtex(cls, source: str) -> CitationLibrary:
        """Parse BibTeX text into a citation library.

        Args:
            source: BibTeX source text.

        Returns:
            Citation library containing parsed entries.
        """

        entries: list[CitationSource] = []
        for key, fields in _parse_bibtex_entries(source):
            authors = tuple(
                part.strip()
                for part in fields.get("author", "").split(" and ")
                if part.strip()
            )
            entries.append(
                CitationSource(
                    title=fields.get("title", key),
                    key=key,
                    authors=authors,
                    organization=fields.get("organization") or fields.get("institution"),
                    publisher=(
                        fields.get("publisher")
                        or fields.get("journal")
                        or fields.get("booktitle")
                        or fields.get("howpublished")
                    ),
                    year=fields.get("year"),
                    url=fields.get("url"),
                    note=fields.get("note"),
                )
            )
        return cls(entries)


def coerce_citation_library(
    value: CitationLibrary | Sequence[CitationSource] | str | None,
) -> CitationLibrary:
    """Normalize any supported citation input into a citation library.

    Args:
        value: Existing library, citation sources, BibTeX source text, or
            ``None``.

    Returns:
        Citation library instance.
    """

    if value is None:
        return CitationLibrary()
    if isinstance(value, CitationLibrary):
        return value
    if isinstance(value, str):
        return CitationLibrary.from_bibtex(value)
    return CitationLibrary(value)


def _format_reference_text(source: CitationSource, reference_format: str) -> str:
    resolved_format = normalize_reference_format(reference_format)
    if resolved_format in {"plain", "numbered"}:
        return _format_plain_reference(source)
    if resolved_format == "apa":
        return _format_apa_reference(source)
    if resolved_format == "mla":
        return _format_mla_reference(source)
    if resolved_format == "chicago":
        return _format_chicago_reference(source)
    if resolved_format == "ieee":
        return _format_ieee_reference(source)
    raise ValueError(f"Unsupported reference_format: {reference_format!r}")


def _format_plain_reference(source: CitationSource) -> str:
    return _join_reference_segments(
        _display_author_text(source),
        source.title,
        source.publisher,
        source.year,
        source.url,
        source.note,
    )


def _format_apa_reference(source: CitationSource) -> str:
    return _join_reference_segments(
        _apa_author_text(source),
        f"({source.year or 'n.d.'})",
        source.title,
        source.publisher,
        source.url,
        source.note,
    )


def _format_mla_reference(source: CitationSource) -> str:
    title = _clean_reference_segment(source.title)
    quoted_title = f'"{title}"' if title else None
    return _join_reference_segments(
        _mla_author_text(source),
        quoted_title,
        source.publisher,
        source.year,
        source.url,
        source.note,
    )


def _format_chicago_reference(source: CitationSource) -> str:
    publication = _join_comma_segments(source.publisher, source.year)
    return _join_reference_segments(
        _mla_author_text(source),
        source.title,
        publication,
        source.url,
        source.note,
    )


def _format_ieee_reference(source: CitationSource) -> str:
    title = _clean_reference_segment(source.title)
    quoted_title = f'"{title}"' if title else None
    publication = _join_comma_segments(source.publisher, source.year)
    return _join_reference_segments(
        _display_author_text(source),
        quoted_title,
        publication,
        source.url,
        source.note,
    )


def _join_reference_segments(*segments: str | None) -> str:
    cleaned = [
        cleaned_segment
        for segment in segments
        if (cleaned_segment := _clean_reference_segment(segment)) is not None
    ]
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


def _parse_bibtex_entries(source: str) -> list[tuple[str, dict[str, str]]]:
    entries: list[tuple[str, dict[str, str]]] = []
    cursor = 0

    while True:
        match = re.search(r"@\w+\s*\{", source[cursor:])
        if match is None:
            break
        entry_start = cursor + match.start()
        body_start = entry_start + match.group(0).rfind("{") + 1
        depth = 1
        position = body_start
        # Track brace depth so commas and closing braces inside field values do
        # not prematurely terminate the entry body.
        while position < len(source) and depth > 0:
            char = source[position]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            position += 1
        body = source[body_start : position - 1].strip()
        cursor = position
        if not body:
            continue

        key, _, fields_text = body.partition(",")
        fields = _parse_bibtex_fields(fields_text)
        entries.append((key.strip(), fields))

    return entries


def _parse_bibtex_fields(source: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in _split_bibtex_fields(source):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        cleaned = value.strip().rstrip(",").strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            cleaned = cleaned[1:-1]
        elif cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        fields[key.strip().lower()] = cleaned.strip()
    return fields


def _split_bibtex_fields(source: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []

    for char in source:
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(depth - 1, 0)

        # Top-level commas separate fields; commas inside braced values remain
        # part of the current field.
        if char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


__all__ = [
    "CitationLibrary",
    "CitationSource",
    "coerce_citation_library",
    "format_citation_label",
    "normalize_citation_format",
    "normalize_reference_format",
    "reference_entry_marker",
]
