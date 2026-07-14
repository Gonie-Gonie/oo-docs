# Citation Support Reference

OODocs covers common `natbib`, `biblatex`, and BibTeX authoring needs with
structured citation objects. It does not aim to be a complete BibLaTeX or CSL
processor.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| One bibliography entry | `CitationSource(...)` | Stores common fields as attributes and retains the complete source field mapping in `fields`. |
| Citation database | `CitationLibrary(...)` | Requires unique non-empty keys and raises on duplicates. |
| Inline citation | `cite("key")`, `CitationSource.cite()`, or `CitationLibrary.cite("key")` | Rendered labels are resolved from the document citation library. |
| Generated bibliography | `ListOfReferences()` | This is the public name; `ReferenceList` and `ReferencesPage` are not separate public aliases. |
| BibTeX input | `CitationLibrary.from_bibtex(...)` or `.from_bibtex_file(...)` | Uses the dependency-free parser by default and accepts another `BibtexParser` backend explicitly. |

`Document(..., citations=...)` accepts a `CitationLibrary`, a sequence of
`CitationSource` objects, BibTeX text, or `None`.

## BibTeX Import Policy

| Feature | Status | Notes |
|---|---|---|
| `@article{...}` and other braced entries | Supported | The entry type is retained as `CitationSource.entry_type`. |
| `@book(...)` and other parenthesized entries | Supported | Braced field values inside the parenthesized entry are preserved. |
| `@string`, `@comment`, and `@preamble` entries | Supported | String definitions are expanded; comments and preambles do not create citation entries. |
| Duplicate citation keys | Error | `CitationLibrary` raises `OODocsError`. |
| Common publication fields | Supported | `journal`, `booktitle`, `volume`, `number`, `pages`, `doi`, `institution`, `school`, `edition`, `chapter`, `month`, `address`, `version`, and `accessed` have convenience attributes. |
| Unknown fields | Preserved | Every parsed value remains in `CitationSource.fields`; `as_bibtex_record()` returns it with the entry type and key. |
| Nested braces, quoted values, concatenation, organization authors, Unicode, and URLs | Supported | Protected capitalization is readable through convenience attributes while the retained field keeps grouping braces. |
| LaTeX accents and escaped symbols | Supported subset | Common accents and escapes become Unicode. Unsupported commands remain in `fields` and add a source-located `CitationDiagnostic`. |
| BibLaTeX-only fields and crossref inheritance | Preserved, not interpreted | Records remain lossless, but OODocs does not resolve inheritance or add formatter-specific meaning for every extension field. |
| CSL JSON/YAML import or export | Not supported | CSL-level compatibility is intentionally outside the current OODocs citation model. |

The parser raises `BibtexParseError` with the entry key and line/column whenever
malformed syntax can be tied to a record. To opt into the third-party backend,
install and pass it explicitly; importing OODocs does not import
`bibtexparser`:

```powershell
pip install "oodocs[bibtex]"
```

```python
from oodocs import CitationLibrary
from oodocs.integrations.bibtex import BibtexparserParser

library = CitationLibrary.from_bibtex(
    bibtex_source,
    parser=BibtexparserParser(),
)
```

The optional backend changes parsing, not the lossless citation model. In both
cases, inspect `source.fields`, `source.diagnostics`, and
`source.as_bibtex_record()` when fidelity matters.

## Styles And Sorting

| Setting | Supported values |
|---|---|
| `CitationDefaults(citation_style=...)` | `numeric`, `author-year`, `apa`, `mla`, `chicago` |
| `CitationDefaults(reference_style=...)` | `plain`, `numbered`, `apa`, `mla`, `chicago`, `ieee` |
| `CitationDefaults(reference_sort=...)` or `ListOfReferences(sort=...)` | `citation`, `author`, `year`, `title`, `key` |

`ListOfReferences()` renders cited entries by default. Pass
`ListOfReferences(include_uncited=True)` when the generated bibliography should
include every source from the document citation library.

All bibliography styles use available container, volume/issue/page,
responsibility, edition/chapter, version, DOI, URL, access-date, and note data
where relevant. DOI and URL text are emitted as hyperlink fragments in DOCX,
PDF, and HTML rather than flattened into an unlinked bibliography string.
