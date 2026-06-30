# Review Notes Example

This example shows the review annotation workflow for documents that need
editorial comments, TODOs, side notes, source footnotes, and generated review
pages from the same Python source.

Use it when review-only helpers should stay in `oodocs.review` while core
comments and footnotes remain available from the main `oodocs` namespace.

Run the full bundle:

```powershell
python examples/review_notes_example/main.py --output-dir artifacts/review-notes-example
```

Render one format while iterating:

```powershell
python examples/review_notes_example/main.py --outputs html --quiet
```

Programmatic entry points:

- `review_queue_rows()` returns the sample review queue data.
- `build_review_section()` demonstrates `Comment`, `comment(...)`, `Todo`,
  `todo(...)`, `MarginNote`, and `margin_note(...)`.
- `build_source_notes_section()` demonstrates `Footnote` and `footnote(...)`.
- `build_document()` returns the renderable `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs and returns an `OutputBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
