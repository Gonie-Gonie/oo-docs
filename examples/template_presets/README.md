# Template Presets Example

This example shows the content-first template workflow. A template preset owns
the repeated document structure, generated pages, declarations, and default
styling, while callers provide manuscript content and metadata.

Use it when you want to start from a complete document shape instead of
assembling every chapter, generated list, and declaration block by hand.

Render every template example:

```powershell
python examples/template_presets/build_all.py --output-dir artifacts/template
```

Render only selected formats while iterating:

```powershell
python examples/template_presets/build_all.py --outputs html --quiet
python examples/template_presets/journal_article_template.py --outputs pdf --outputs html
```

Programmatic entry points:

- `journal_article_template.build_document()` returns a complete `Document`
  built from preset inputs.
- `journal_article_template.build(output_dir=..., output_formats=...)` writes
  one template output bundle.
- `build_all.build_all(output_dir=..., output_formats=...)` renders every
  template example and returns a mapping of template names to `OutputBundle`
  values.
