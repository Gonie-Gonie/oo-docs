# Template Presets Example

This example shows the content-first template workflow. A template preset owns
the repeated document structure, generated pages, declarations, and default
styling, while callers provide manuscript content and metadata.

Use it when you want to start from a complete document shape instead of
assembling every chapter, generated list, and declaration block by hand.

Canonical preset APIs live under `oodocs.presets.templates` for document
builders and `oodocs.presets.components` for reusable component presets.
`oodocs.presets` re-exports both groups for convenience, while top-level
`oodocs` stays focused on core document primitives. The files in this directory
are runnable examples that demonstrate those preset APIs; they are not an
additional public template namespace.

Render every template example:

```powershell
python examples/template_presets/main.py --output-dir artifacts/template
```

Render only selected formats while iterating:

```powershell
python examples/template_presets/main.py --outputs html --quiet
python examples/template_presets/journal_article_template.py --outputs pdf --outputs html
```

Programmatic entry points:

- `journal_article_template.build_document()` returns a complete `Document`
  built from preset inputs.
- `journal_article_template.build_minimal_document()` returns a minimal article
  where `acknowledgements=None` and `data_availability=None` omit those headings.
- The rendered journal template includes a template catalog covering
  `CoverPagePreset`, `JournalArticleTemplate`, `TechnicalReportTemplate`,
  `SoftwareManualTemplate`, and `BookTemplate`, plus a
  `JournalArticleTemplate.build(...)` input schema, and a comparison with the
  direct assembly workflow in `journal_paper_example`.
- `main.build(...)` exposes the directory-level common example interface and
  delegates to every template in the catalog.
- `journal_article_template.build(output_dir=..., output_formats=...)` writes
  one template output bundle.
- `build_all.build_all(output_dir=..., output_formats=...)` renders every
  template example and returns a mapping of template names to `OutputBundle`
  values.
