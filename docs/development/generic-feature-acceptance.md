# Generic documentation feature acceptance

This cleanup keeps OODocs focused on reusable document objects. An external
manual suite was reviewed only as acceptance input; no application-specific
class, function, preset, filename, title, footer, or build recipe belongs in
the library API.

## v2.0.0 cleanup record

The original review covered the renderer, component, settings, indexing,
workflow, preset, adapter, and evidence surfaces. In v2.0.0 the legacy
`src/oodocs/adapters/` package and monolithic `src/oodocs/evidence.py` module
were replaced and removed.

The current implementation is split by responsibility:

- `src/oodocs/integrations/` contains external parsers and collectors.
- `src/oodocs/evidence/` contains the neutral evidence model, renderer, and CLI.
- `src/oodocs/metadata.py` contains neutral project and workflow summaries.
- `src/oodocs/suite.py` contains multi-document composition and asset policy.
- `src/oodocs/components/`, `layout/`, `styles/`, and `renderers/` contain the
  shared document semantics used by every output format.

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
