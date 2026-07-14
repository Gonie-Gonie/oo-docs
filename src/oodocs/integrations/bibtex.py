"""BibTeX parser integrations for :mod:`oodocs` citation models.

The built-in parser has no third-party dependencies.  The optional
``BibtexparserParser`` imports :mod:`bibtexparser` only when ``parse`` is
called, keeping ``import oodocs`` and ordinary citation construction light.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Protocol, Sequence, runtime_checkable

from oodocs.components.references import CitationDiagnostic, CitationSource
from oodocs.core import OODocsError


@runtime_checkable
class BibtexParser(Protocol):
    """Protocol implemented by BibTeX parser backends."""

    def parse(self, source: str) -> Sequence[CitationSource]:
        """Parse BibTeX source into citation objects."""


class BibtexParseError(OODocsError):
    """BibTeX syntax error with entry and source-position context."""

    def __init__(
        self,
        message: str,
        *,
        entry_key: str | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self.entry_key = entry_key
        self.line = line
        self.column = column
        context: list[str] = []
        if entry_key:
            context.append(f"entry {entry_key!r}")
        if line is not None:
            location = f"line {line}"
            if column is not None:
                location += f", column {column}"
            context.append(location)
        suffix = f" ({'; '.join(context)})" if context else ""
        super().__init__(f"{message}{suffix}")


@dataclass(frozen=True, slots=True)
class _RawEntry:
    entry_type: str
    key: str
    fields: dict[str, str]
    field_offsets: dict[str, int]


@dataclass(frozen=True, slots=True)
class _FieldToken:
    name: str
    value: str
    offset: int


class BuiltinBibtexParser:
    """Dependency-free parser for ordinary BibTeX databases.

    Braced and quoted values, nested braces, parenthesized entries, string
    concatenation, Unicode, organization authors, URLs, and unknown fields are
    retained. Unsupported LaTeX commands stay in ``CitationSource.fields`` and
    produce a diagnostic instead of silently disappearing.
    """

    def parse(self, source: str) -> Sequence[CitationSource]:
        return tuple(
            _citation_from_raw_entry(source, entry)
            for entry in _parse_raw_entries(source)
        )


def _parse_raw_entries(source: str) -> tuple[_RawEntry, ...]:
    """Parse dependency-free raw entries for models and backend audits."""

    if not isinstance(source, str):
        raise TypeError("BibTeX source must be a string")

    raw_entries: list[_RawEntry] = []
    macros: dict[str, str] = {}
    cursor = 0
    while match := re.search(
        r"(?m)^[ \t]*@(?P<kind>[A-Za-z][\w:-]*)\s*(?P<open>[{(])",
        source[cursor:],
    ):
        entry_start = cursor + match.start() + match.group(0).find("@")
        body_start = cursor + match.end()
        entry_type = match.group("kind").lower()
        opening = match.group("open")
        closing = "}" if opening == "{" else ")"
        body_end = _find_entry_end(
            source,
            body_start,
            opening=opening,
            closing=closing,
        )
        if body_end is None:
            key_hint = _entry_key_hint(source[body_start:])
            line, column = _source_position(source, entry_start)
            raise BibtexParseError(
                "Unterminated BibTeX entry",
                entry_key=key_hint,
                line=line,
                column=column,
            )

        body = source[body_start:body_end]
        cursor = body_end + 1
        if entry_type in {"comment", "preamble"}:
            continue
        if entry_type == "string":
            token = _parse_string_definition(source, body, body_start)
            macros[token.name.casefold()] = _resolve_value(token.value, macros)
            continue

        key, fields_source, fields_offset = _split_entry_body(
            source,
            body,
            body_start,
        )
        tokens = _parse_fields(source, fields_source, fields_offset, entry_key=key)
        raw_entries.append(
            _RawEntry(
                entry_type=entry_type,
                key=key,
                fields={
                    token.name: _resolve_value(token.value, macros)
                    for token in tokens
                },
                field_offsets={token.name: token.offset for token in tokens},
            )
        )

    return tuple(raw_entries)


class BibtexparserParser:
    """Optional backend powered by the third-party ``bibtexparser`` package."""

    def parse(self, source: str) -> Sequence[CitationSource]:
        try:
            import bibtexparser  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "BibtexparserParser requires the optional 'bibtexparser' dependency. "
                "Install OODocs with the bibtex extra."
            ) from exc

        if not hasattr(bibtexparser, "loads"):
            raise RuntimeError(
                "This bibtexparser version does not expose loads(); use "
                "BuiltinBibtexParser or install a compatible bibtexparser release."
            )
        try:
            database = bibtexparser.loads(source)
        except Exception as exc:
            raise BibtexParseError(f"bibtexparser could not parse the source: {exc}") from exc

        try:
            raw_inventory = {
                entry.key: entry
                for entry in _parse_raw_entries(source)
            }
        except BibtexParseError:
            # A third-party backend may intentionally support syntax outside
            # the dependency-free parser.  Parsing should still succeed; only
            # the loss audit is unavailable for that input.
            raw_inventory = {}

        entries: list[CitationSource] = []
        for record in getattr(database, "entries", ()):
            normalized = {
                str(name).lower(): str(value)
                for name, value in dict(record).items()
                if str(name).upper() not in {"ENTRYTYPE", "ID"}
            }
            entry_type = str(record.get("ENTRYTYPE", "misc")).lower()
            key = str(record.get("ID", "")).strip()
            expected = raw_inventory.get(key)
            dropped_fields = (
                tuple(sorted(expected.fields.keys() - normalized.keys()))
                if expected is not None
                else ()
            )
            # Preserve the dependency-free parser's raw values even when an
            # optional backend omits an unknown field. The diagnostic records
            # that the selected backend was lossy without losing user data.
            if expected is not None:
                for field_name in dropped_fields:
                    normalized[field_name] = expected.fields[field_name]
            raw = _RawEntry(
                entry_type=entry_type,
                key=key,
                fields=normalized,
                field_offsets={},
            )
            citation = _citation_from_raw_entry(source, raw)
            if expected is not None:
                loss_diagnostics: list[CitationDiagnostic] = []
                for field_name in dropped_fields:
                    line, column = _source_position(
                        source,
                        expected.field_offsets.get(field_name),
                    )
                    loss_diagnostics.append(
                        CitationDiagnostic(
                            code="bibtex-field-loss",
                            message=(
                                f"BibTeX backend dropped field {field_name!r} "
                                f"from entry {key!r}."
                            ),
                            entry_key=key,
                            field=field_name,
                            raw_value=expected.fields[field_name],
                            line=line,
                            column=column,
                        )
                    )
                citation.diagnostics = (
                    *citation.diagnostics,
                    *loss_diagnostics,
                )
            entries.append(citation)
        return tuple(entries)


def parse_bibtex(
    source: str,
    *,
    parser: BibtexParser | None = None,
) -> tuple[CitationSource, ...]:
    """Parse BibTeX source with the selected backend."""

    return tuple((parser or BuiltinBibtexParser()).parse(source))


def _find_entry_end(
    source: str,
    start: int,
    *,
    opening: str,
    closing: str,
) -> int | None:
    delimiter_depth = 1
    brace_depth = 0
    quote = False
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quote = not quote
            continue
        if quote:
            continue
        if opening == "{":
            if char == "{":
                delimiter_depth += 1
            elif char == "}":
                delimiter_depth -= 1
                if delimiter_depth == 0:
                    return index
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth = max(brace_depth - 1, 0)
        elif brace_depth == 0 and char == "(":
            delimiter_depth += 1
        elif brace_depth == 0 and char == closing:
            delimiter_depth -= 1
            if delimiter_depth == 0:
                return index
    return None


def _split_entry_body(source: str, body: str, offset: int) -> tuple[str, str, int]:
    comma = _find_top_level(body, ",")
    if comma is None:
        line, column = _source_position(source, offset)
        raise BibtexParseError(
            "BibTeX entry must contain a citation key followed by fields",
            entry_key=body.strip() or None,
            line=line,
            column=column,
        )
    key = body[:comma].strip()
    if not key:
        line, column = _source_position(source, offset)
        raise BibtexParseError(
            "BibTeX entry key must not be empty",
            line=line,
            column=column,
        )
    return key, body[comma + 1 :], offset + comma + 1


def _parse_string_definition(source: str, body: str, offset: int) -> _FieldToken:
    tokens = _parse_fields(source, body, offset, entry_key="@string")
    if len(tokens) != 1:
        line, column = _source_position(source, offset)
        raise BibtexParseError(
            "@string must define exactly one name",
            line=line,
            column=column,
        )
    return tokens[0]


def _parse_fields(
    source: str,
    fields_source: str,
    offset: int,
    *,
    entry_key: str,
) -> list[_FieldToken]:
    tokens: list[_FieldToken] = []
    cursor = 0
    while cursor < len(fields_source):
        while cursor < len(fields_source) and (
            fields_source[cursor].isspace() or fields_source[cursor] == ","
        ):
            cursor += 1
        if cursor >= len(fields_source):
            break

        name_match = re.match(r"[A-Za-z][\w:-]*", fields_source[cursor:])
        if name_match is None:
            _raise_field_error(
                source,
                offset + cursor,
                entry_key,
                "Expected a BibTeX field name",
            )
        assert name_match is not None
        name = name_match.group(0).lower()
        cursor += name_match.end()
        while cursor < len(fields_source) and fields_source[cursor].isspace():
            cursor += 1
        if cursor >= len(fields_source) or fields_source[cursor] != "=":
            _raise_field_error(
                source,
                offset + cursor,
                entry_key,
                f"Expected '=' after field {name!r}",
            )
        cursor += 1
        while cursor < len(fields_source) and fields_source[cursor].isspace():
            cursor += 1
        value_start = cursor
        value_end = _find_value_end(fields_source, cursor)
        value = fields_source[value_start:value_end].strip()
        if not value:
            _raise_field_error(
                source,
                offset + value_start,
                entry_key,
                f"Field {name!r} has no value",
            )
        tokens.append(_FieldToken(name, value, offset + value_start))
        cursor = value_end + 1 if value_end < len(fields_source) else value_end
    return tokens


def _find_value_end(source: str, start: int) -> int:
    brace_depth = 0
    quote = False
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and brace_depth == 0:
            quote = not quote
            continue
        if quote:
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth < 0:
                return index
        elif char == "," and brace_depth == 0:
            return index
    return len(source)


def _resolve_value(value: str, macros: dict[str, str]) -> str:
    pieces = _split_top_level(value, "#")
    resolved: list[str] = []
    for piece in pieces:
        token = piece.strip()
        if len(token) >= 2 and token[0] == "{" and token[-1] == "}":
            resolved.append(token[1:-1])
        elif len(token) >= 2 and token[0] == token[-1] == '"':
            resolved.append(token[1:-1])
        else:
            resolved.append(macros.get(token.casefold(), token))
    return "".join(resolved).strip()


def _citation_from_raw_entry(source: str, entry: _RawEntry) -> CitationSource:
    decoded: dict[str, str] = {}
    diagnostics: list[CitationDiagnostic] = []
    for name, raw_value in entry.fields.items():
        value, unsupported = _latex_to_unicode(raw_value)
        decoded[name] = value
        if unsupported:
            offset = entry.field_offsets.get(name)
            line, column = _source_position(source, offset) if offset is not None else (None, None)
            diagnostics.append(
                CitationDiagnostic(
                    code="unsupported-latex-command",
                    message=(
                        f"BibTeX field {name!r} in entry {entry.key!r} contains "
                        f"unsupported LaTeX command(s): {', '.join(unsupported)}."
                    ),
                    entry_key=entry.key,
                    field=name,
                    raw_value=raw_value,
                    line=line,
                    column=column,
                )
            )

    authors: list[str] = []
    for raw_author in _split_authors(entry.fields.get("author", "")):
        decoded_author, _unsupported = _latex_to_unicode(raw_author)
        normalized_author = _strip_grouping_braces(decoded_author).strip()
        if normalized_author:
            authors.append(normalized_author)
    return CitationSource(
        decoded.get("title") or entry.key,
        key=entry.key,
        entry_type=entry.entry_type,
        authors=tuple(authors),
        organization=decoded.get("organization"),
        publisher=decoded.get("publisher"),
        year=decoded.get("year"),
        url=decoded.get("url"),
        note=decoded.get("note"),
        journal=decoded.get("journal"),
        booktitle=decoded.get("booktitle"),
        volume=decoded.get("volume"),
        number=decoded.get("number"),
        pages=decoded.get("pages"),
        doi=decoded.get("doi"),
        institution=decoded.get("institution"),
        school=decoded.get("school"),
        edition=decoded.get("edition"),
        chapter=decoded.get("chapter"),
        month=decoded.get("month"),
        address=decoded.get("address"),
        version=decoded.get("version"),
        accessed=decoded.get("accessed") or decoded.get("urldate"),
        fields=entry.fields,
        diagnostics=diagnostics,
    )


_ACCENTS = {
    "'": "\u0301",
    "`": "\u0300",
    "\"": "\u0308",
    "^": "\u0302",
    "~": "\u0303",
    "=": "\u0304",
    ".": "\u0307",
    "u": "\u0306",
    "v": "\u030c",
    "H": "\u030b",
    "c": "\u0327",
    "k": "\u0328",
}
_SIMPLE_COMMANDS = {
    "ss": "ß",
    "ae": "æ",
    "AE": "Æ",
    "oe": "œ",
    "OE": "Œ",
    "aa": "å",
    "AA": "Å",
    "o": "ø",
    "O": "Ø",
    "l": "ł",
    "L": "Ł",
}
_ESCAPED_SYMBOLS = {
    "&": "&",
    "%": "%",
    "_": "_",
    "#": "#",
    "$": "$",
    "{": "{",
    "}": "}",
    "~": "~",
}


def _latex_to_unicode(value: str) -> tuple[str, tuple[str, ...]]:
    text = value

    def replace_accent(match: re.Match[str]) -> str:
        accent = match.group("accent")
        character = match.group("braced") or match.group("plain") or ""
        return unicodedata.normalize("NFC", character + _ACCENTS[accent])

    symbolic_accent_pattern = re.compile(
        r"\\(?P<accent>['`\"\^~=\.])(?:\{(?P<braced>[^{}])\}|(?P<plain>[A-Za-z]))"
    )
    named_accent_pattern = re.compile(
        r"\\(?P<accent>[uvHck])\{(?P<braced>[^{}])\}"
    )
    text = symbolic_accent_pattern.sub(replace_accent, text)
    text = named_accent_pattern.sub(replace_accent, text)
    for command, replacement in _SIMPLE_COMMANDS.items():
        text = re.sub(rf"\\{re.escape(command)}(?:\{{\}})?(?![A-Za-z])", replacement, text)
    for symbol, replacement in _ESCAPED_SYMBOLS.items():
        text = text.replace(f"\\{symbol}", replacement)

    unsupported = tuple(dict.fromkeys(re.findall(r"\\[A-Za-z]+", text)))
    text = _strip_grouping_braces(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, unsupported


def _split_authors(value: str) -> list[str]:
    if not value:
        return []
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    index = 0
    while index < len(value):
        char = value[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(depth - 1, 0)
        if depth == 0:
            match = re.match(r"\s+and\s+", value[index:], flags=re.IGNORECASE)
            if match is not None:
                parts.append("".join(current))
                current = []
                index += match.end()
                continue
        current.append(char)
        index += 1
    parts.append("".join(current))
    return parts


def _strip_grouping_braces(value: str) -> str:
    return value.replace("{", "").replace("}", "")


def _split_top_level(value: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quote = False
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == '"' and depth == 0:
            quote = not quote
        elif not quote and char == "{":
            depth += 1
        elif not quote and char == "}":
            depth = max(depth - 1, 0)
        if char == delimiter and depth == 0 and not quote:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def _find_top_level(value: str, delimiter: str) -> int | None:
    depth = 0
    quote = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and depth == 0:
            quote = not quote
        elif not quote and char == "{":
            depth += 1
        elif not quote and char == "}":
            depth = max(depth - 1, 0)
        elif char == delimiter and depth == 0 and not quote:
            return index
    return None


def _entry_key_hint(body: str) -> str | None:
    key = body.split(",", 1)[0].strip()
    return key or None


def _source_position(source: str, offset: int | None) -> tuple[int | None, int | None]:
    if offset is None:
        return None, None
    line = source.count("\n", 0, offset) + 1
    previous_newline = source.rfind("\n", 0, offset)
    column = offset - previous_newline
    return line, column


def _raise_field_error(
    source: str,
    offset: int,
    entry_key: str,
    message: str,
) -> None:
    line, column = _source_position(source, offset)
    raise BibtexParseError(
        message,
        entry_key=entry_key,
        line=line,
        column=column,
    )


__all__ = [
    "BibtexParseError",
    "BibtexParser",
    "BibtexparserParser",
    "BuiltinBibtexParser",
    "parse_bibtex",
]
