# Generic documentation feature acceptance

This cleanup keeps OODocs focused on reusable document objects. An external
manual suite was reviewed only as acceptance input; no application-specific
class, function, preset, filename, title, footer, or build recipe belongs in
the library API.

## Direct review scope

The following files are the direct review surface for the cleanup:

- `src/oodocs/presets/templates.py`
- `src/oodocs/adapters/__init__.py`
- `src/oodocs/adapters/evidence.py`
- `src/oodocs/adapters/github_actions.py`
- `src/oodocs/adapters/manifest.py`
- `src/oodocs/adapters/pyproject.py`
- `src/oodocs/evidence.py`
- `src/oodocs/document.py`
- `src/oodocs/settings.py`
- `src/oodocs/components/base.py`
- `src/oodocs/components/blocks.py`
- `src/oodocs/components/inline.py`
- `src/oodocs/components/media.py`
- `src/oodocs/components/references.py`
- `src/oodocs/layout/indexing.py`
- `src/oodocs/styles/theme.py`
- `src/oodocs/renderers/docx.py`
- `src/oodocs/renderers/pdf.py`
- `src/oodocs/renderers/html.py`
- `src/oodocs/workflows.py`

The legacy adapter paths are listed because they must be replaced by generic
models and explicit integrations, then removed.

## Generic acceptance requirements

- Multiple documents can share cover policy, locale, bibliography, asset
  roots, variables, and release metadata without copying builder wiring.
- Front matter can use lower-Roman page numbers and main matter can restart
  with decimal page numbers.
- Tables, figures, sections, and equations support mutual references.
- An unnumbered target can be linked with caller-authored text.
- Repeated field specifications and command-line argument descriptions use
  reusable document objects.
- Grouped headers, long and wide tables, subfigures, code listings, and
  footnotes compose in the same document.
- Each line of an aligned equation can have its own reference target.

## API boundary

New APIs must describe document semantics, not one application's vocabulary.
External file formats and tools live under `oodocs.integrations`; core models
accept ordinary Python mappings and sequences. Visual choices use `style`,
while content-selection policy uses `profile` or `presentation`.

Public method names follow these rules:

- `to_*` returns an OODocs document object.
- `as_*` returns a raw Python value or record.
- `from_*` is a classmethod that creates an object from external input.
- `collect_*` gathers metadata from an external program, parser, or runtime.
- `load_*` restores an existing model from a file.
- `save_*` writes a file.
- `validate_*` returns structured validation data.
- `integration` identifies a parser or collector coupled to an external tool.
