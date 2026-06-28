# Journal Paper Example

This example shows a manuscript workflow where CSV tables, matplotlib figures,
citations, author metadata, and article-style sections are assembled into one
document bundle.

Use it when your source evidence already lives in Python data files and figures,
and the final artifact needs to read like a manuscript rather than a reference
manual.

Run the full bundle:

```powershell
python examples/journal_paper_example/main.py --output-dir artifacts/journal-paper
```

The artifact stem remains `oodocs-development-philosophy` for release
continuity; in the example catalog this is the `manuscript-data-workflow`
pattern.

Render one format while iterating:

```powershell
python examples/journal_paper_example/main.py --outputs html --quiet
```

Programmatic entry points:

- `load_inputs()` returns a `ManuscriptInputs` bundle with dataframes,
  citations, asset paths, and source paths.
- `build_quality_latency_figure(...)` and `build_revision_effort_figure()` make
  the manuscript figures.
- `build_journal_paper_document(inputs=None)` returns the complete `Document`.
- `build_journal_paper(output_dir=..., output_formats=..., verbose=False)`
  writes selected outputs and returns an `OutputBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
