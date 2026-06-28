# Release Notes Digest Example

This example reuses versioned Markdown release notes as document input. It sorts
release-note files by semantic version, reads tag dates from git, imports each
Markdown body, records Markdown import diagnostics, and renders a release-note
digest bundle.

Use it when repository Markdown artifacts should become reviewable DOCX/PDF/HTML
outputs without copying release text into another tool.

Run the full bundle:

```powershell
python examples/release_notes_digest/main.py --output-dir artifacts/release-notes
```

Render one format while iterating:

```powershell
python examples/release_notes_digest/main.py --outputs html --quiet
python examples/release_notes_digest/main.py --mode index-only --outputs pdf
```

Programmatic entry points:

- `release_note_files(...)`, `version_parts_from_filename(...)`, and
  `release_dates_from_git(...)` collect release metadata.
- `build_release_notes_document(mode="full")` returns the complete `Document`;
  pass `mode="index-only"` for long repositories where the body should be
  summarized instead of imported in full.
- `build_release_notes(output_dir=..., output_formats=..., mode=..., verbose=False)`
  writes selected outputs, writes `release-notes-import-diagnostics.json`, and
  returns a `ReleaseNotesBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
