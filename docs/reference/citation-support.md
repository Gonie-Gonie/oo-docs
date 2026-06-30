# Citation Support Reference

OODocs covers common `natbib`, `biblatex`, and BibTeX authoring needs with
structured citation objects. It does not aim to be a complete BibLaTeX or CSL
processor.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| One bibliography entry | `CitationSource(...)` | Stores title, key, authors, organization, publisher or venue, year, URL, and note. |
| Citation database | `CitationLibrary(...)` | Requires unique non-empty keys and raises on duplicates. |
| Inline citation | `cite("key")`, `CitationSource.cite()`, or `CitationLibrary.cite("key")` | Rendered labels are resolved from the document citation library. |
| Generated bibliography | `ListOfReferences()` | This is the public name; `ReferenceList` and `ReferencesPage` are not separate public aliases. |
| BibTeX input | `CitationLibrary.from_bibtex(...)` or `.from_bibtex_file(...)` | Parses a practical BibTeX subset into `CitationSource` entries. |

`Document(..., citations=...)` accepts a `CitationLibrary`, a sequence of
`CitationSource` objects, BibTeX text, or `None`.

## BibTeX Import Policy

| Feature | Status | Notes |
|---|---|---|
| `@article{...}` and other braced entries | Supported | Entry type is accepted generically; known fields are mapped to `CitationSource`. |
| `@book(...)` and other parenthesized entries | Supported | Braced field values inside the parenthesized entry are preserved. |
| `@string`, `@comment`, and `@preamble` entries | Ignored | String macro expansion is not performed. |
| Duplicate citation keys | Error | `CitationLibrary` raises `OODocsError`. |
| `title`, `author`, `organization`, `institution`, `publisher`, `journal`, `booktitle`, `howpublished`, `year`, `url`, `note` | Supported | Venue-like fields are collapsed into the `publisher` field. |
| Nested braces in field values | Supported subset | Braces are stripped after parsing so protected capitalization remains readable. |
| BibLaTeX-only fields, crossref inheritance, string concatenation, and macros | Not supported | Normalize these before import or create `CitationSource` objects directly. |
| CSL JSON/YAML import or export | Not supported | CSL-level compatibility is intentionally outside the current OODocs citation model. |

## Styles And Sorting

| Setting | Supported values |
|---|---|
| `CitationDefaults(citation_style=...)` | `numeric`, `author-year`, `apa`, `mla`, `chicago` |
| `CitationDefaults(reference_style=...)` | `plain`, `numbered`, `apa`, `mla`, `chicago`, `ieee` |
| `CitationDefaults(reference_sort=...)` or `ListOfReferences(sort=...)` | `citation`, `author`, `year`, `title`, `key` |

`ListOfReferences()` renders cited entries by default. Pass
`ListOfReferences(include_uncited=True)` when the generated bibliography should
include every source from the document citation library.
