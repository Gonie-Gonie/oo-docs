# Review Annotation Support Reference

OODocs covers common `marginnote` and `todonotes` authoring needs with review
helpers in `oodocs.review`. These helpers are intentionally separate from the
top-level `oodocs` namespace so the core authoring surface stays small.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Inline TODO helper | `todo("Verify units.", owner="QA")` | Adds a visible `TODO` anchor and comment-style review note. |
| Explicit TODO class | `Todo("Verify units.", owner="QA", status="open")` | Stores owner and status metadata while using the same rendering path. |
| Margin note helper | `margin_note("Keep this beside the claim.", side="left")` | Creates a side note with a preferred left or right side. |
| Explicit margin note class | `MarginNote("Check this assumption.", side="right")` | Keeps the note close to source prose without making it a numbered footnote. |
| Review collection | `ListOfComments("Collected Review Notes")` | Generates a review-note page for comments, TODOs, and renderer fallbacks. |
| Example workflow | `examples/review_notes_example/` | Shows comments, TODOs, margin notes, footnotes, and generated review pages together. |

## Renderer Mapping

HTML renders `MarginNote` as an aside-like side note with
`oodocs-margin-note-left` or `oodocs-margin-note-right` classes. DOCX and PDF
cannot guarantee true margin placement, so they preserve the note through
comment-style fallback output and emit `margin-note-renderer-fallback` for those
formats.

TODO annotations use the comment workflow across DOCX, PDF, and HTML. The
visible anchor defaults to `TODO`, while `owner=...`, `status=...`, `value=...`,
`author=...`, and `initials=...` keep review metadata explicit.

Use footnotes when the note is part of the published reading flow. Use review
annotations when the note belongs to editing, QA, or reviewer handoff.
