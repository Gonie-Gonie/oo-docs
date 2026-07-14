# Glossary Support Reference

OODocs covers common `glossaries`, `acronym`, and `nomencl` authoring needs
with explicit registries and generated glossary blocks.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Glossary registry | `Glossary(...)` | Stores terms and acronyms by stable lookup key. |
| Term entry | `glossary.term(key, definition, term=...)` | Adds an ordinary term with display text and definition. |
| Acronym entry | `glossary.acronym(key, long, short=...)` | Adds an `Acronym` entry with first-use expansion support. |
| Inline term use | `glossary.use(key)` | Emits inline text; acronyms expand on first use and use short form later. |
| Generated glossary | `ListOfGlossaryTerms(glossary, sort=...)` | Renders a generated table sorted by insertion order, key, or term. |
| Symbol table | `Nomenclature(...)` | Provides the report-panel preset for authored symbol, meaning, and unit rows. |

## Policies

Glossary keys have surrounding whitespace removed, but lookup remains
case-sensitive. Duplicate keys in a generated glossary emit a
`duplicate-glossary-key` validation error, and an empty generated glossary
emits an `empty-glossary-list` warning.

Use `ListOfGlossaryTerms(...)` when terms should be collected from a registry.
Use `Nomenclature(...)` when the document needs an authored symbol table rather
than an automatic glossary registry.
