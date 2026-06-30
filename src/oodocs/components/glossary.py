"""Glossary and acronym authoring helpers.

Attributes:
    GlossaryTermKind: Supported glossary entry kind names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from oodocs.components.inline import Text
from oodocs.styles import TextStyle


GlossaryTermKind = Literal["term", "acronym"]


@dataclass(slots=True)
class GlossaryTerm:
    """One glossary or acronym entry.

    Args:
        key: Stable lookup key used by ``Glossary.use(...)``.
        term: Display label for glossary tables.
        definition: Definition or expansion shown in generated lists.
        kind: Entry kind, either ``"term"`` or ``"acronym"``.
        short: Optional acronym short form.
        long: Optional acronym long form.
    """

    key: str
    term: str
    definition: str
    kind: GlossaryTermKind = "term"
    short: str | None = None
    long: str | None = None

    def __post_init__(self) -> None:
        self.key = _normalize_glossary_text(self.key, "key")
        self.term = _normalize_glossary_text(self.term, "term")
        self.definition = _normalize_glossary_text(self.definition, "definition")
        if self.kind not in {"term", "acronym"}:
            raise ValueError("GlossaryTerm.kind must be 'term' or 'acronym'")
        if self.kind == "acronym":
            self.short = _normalize_glossary_text(self.short or self.term, "short")
            self.long = _normalize_glossary_text(self.long or self.definition, "long")

    def display_text(self, *, first_use: bool = False) -> str:
        """Return inline text for a glossary use.

        Args:
            first_use: Whether acronym entries should expand to long form.

        Returns:
            Display text for insertion into a paragraph.
        """

        if self.kind != "acronym":
            return self.term
        short = self.short or self.term
        long = self.long or self.definition
        return f"{long} ({short})" if first_use else short

    def list_label(self) -> str:
        """Return the label shown in a generated glossary table.

        Returns:
            Term or acronym label.
        """

        return self.short or self.term

    def list_definition(self) -> str:
        """Return the definition shown in a generated glossary table.

        Returns:
            Definition or acronym expansion text.
        """

        if self.kind != "acronym":
            return self.definition
        long = self.long or self.definition
        if self.definition == long:
            return long
        return f"{long} - {self.definition}"


class Acronym(GlossaryTerm):
    """Glossary entry with first-use long-form expansion.

    Args:
        key: Stable lookup key.
        long: Expanded acronym text.
        short: Optional visible short form. Defaults to ``key``.
        definition: Optional generated-list definition. Defaults to ``long``.
    """

    def __init__(
        self,
        key: str,
        long: str,
        *,
        short: str | None = None,
        definition: str | None = None,
    ) -> None:
        short_text = short or key
        super().__init__(
            key=key,
            term=short_text,
            definition=definition or long,
            kind="acronym",
            short=short_text,
            long=long,
        )


class Glossary:
    """Registry for glossary terms and acronym use.

    Args:
        entries: Optional initial glossary entries.

    Attributes:
        entries: Registered glossary and acronym entries.

    Examples:
        ```python
        from oodocs import Paragraph
        from oodocs.glossary import Glossary, ListOfGlossaryTerms

        glossary = Glossary()
        glossary.acronym("HVAC", "Heating, ventilation, and air conditioning")
        paragraph = Paragraph(glossary.use("HVAC"), " requirements are tracked.")
        glossary_page = ListOfGlossaryTerms(glossary)
        ```
    """

    def __init__(self, entries: list[GlossaryTerm] | None = None) -> None:
        self.entries: list[GlossaryTerm] = list(entries or [])
        self._used_keys: set[str] = set()

    def term(
        self,
        key: str,
        definition: str,
        *,
        term: str | None = None,
    ) -> GlossaryTerm:
        """Add a glossary term and return it.

        Args:
            key: Stable lookup key.
            definition: Definition shown in generated glossary lists.
            term: Optional display label. Defaults to ``key``.

        Returns:
            Registered glossary term.
        """

        entry = GlossaryTerm(
            key=key,
            term=term or key,
            definition=definition,
        )
        self.entries.append(entry)
        return entry

    def acronym(
        self,
        key: str,
        long: str,
        *,
        short: str | None = None,
        definition: str | None = None,
    ) -> Acronym:
        """Add an acronym and return it.

        Args:
            key: Stable lookup key.
            long: Expanded acronym text.
            short: Optional visible short form. Defaults to ``key``.
            definition: Optional generated-list definition. Defaults to
                ``long``.

        Returns:
            Registered acronym entry.
        """

        entry = Acronym(key, long, short=short, definition=definition)
        self.entries.append(entry)
        return entry

    def use(
        self,
        key: str,
        *,
        first_use: bool | None = None,
        style: TextStyle | None = None,
    ) -> Text:
        """Return inline text for one glossary key.

        Acronyms expand on the first call for a key, then use the short form on
        later calls. Pass ``first_use=True`` or ``False`` to override that
        policy at a specific call site.

        Args:
            key: Stable lookup key.
            first_use: Optional first-use expansion override.
            style: Optional inline text style.

        Returns:
            Inline text fragment for the glossary entry.
        """

        entry = self.get(key)
        first = key not in self._used_keys if first_use is None else bool(first_use)
        self._used_keys.add(entry.key)
        return Text(entry.display_text(first_use=first), style=TextStyle().merged(style))

    def get(self, key: str) -> GlossaryTerm:
        """Return the first entry matching ``key``.

        Args:
            key: Stable lookup key.

        Returns:
            Matching glossary entry.

        Raises:
            KeyError: If no entry exists for ``key``.
        """

        normalized = _normalize_glossary_text(key, "key")
        for entry in self.entries:
            if entry.key == normalized:
                return entry
        raise KeyError(f"Glossary key not found: {normalized!r}")

    def sorted_entries(self, sort: str = "insertion") -> list[GlossaryTerm]:
        """Return entries in insertion, key, or term order.

        Args:
            sort: Sort order: ``"insertion"``, ``"key"``, or ``"term"``.

        Returns:
            Glossary entries in the requested order.

        Raises:
            ValueError: If ``sort`` is unsupported.
        """

        normalized = str(sort).lower()
        if normalized == "insertion":
            return list(self.entries)
        if normalized == "key":
            return sorted(self.entries, key=lambda entry: entry.key.lower())
        if normalized == "term":
            return sorted(self.entries, key=lambda entry: entry.list_label().lower())
        raise ValueError("Glossary sort must be 'insertion', 'key', or 'term'")

    def duplicate_keys(self) -> set[str]:
        """Return duplicated entry keys.

        Returns:
            Keys registered more than once.
        """

        seen: set[str] = set()
        duplicates: set[str] = set()
        for entry in self.entries:
            if entry.key in seen:
                duplicates.add(entry.key)
            seen.add(entry.key)
        return duplicates


def _normalize_glossary_text(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"Glossary {name} must not be empty")
    return text


__all__ = [
    "Acronym",
    "Glossary",
    "GlossaryTerm",
    "GlossaryTermKind",
]
