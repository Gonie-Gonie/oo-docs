# Reference Support Reference

OODocs covers common `cleveref` and `varioref` authoring needs with structured
object references instead of raw LaTeX commands.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Single typed reference | `ref(obj)` or `obj.ref()` | Uses the target object's renderer-managed label such as `Figure 1`, `Table 2`, `Equation 3`, or `Theorem 1`. |
| Plural references | `refs([a, b])` | Joins several targets and can use `plural_label=...` or `ReferenceFormat(plural_label=...)`. |
| Reference range | `ref_range(a, b)` | Renders a compact range with `range_separator`, for example `Tables 1--4`. |
| Formatting policy | `ReferenceFormat(...)` | Controls `label`, `plural_label`, `capitalized`, `separator`, `last_separator`, `range_separator`, `prefix`, and `suffix`. |
| Bracketed or parenthesized references | `bracket_ref(obj)` or `paren_ref(obj)` | Provides convenient wrappers for report styles such as `[Figure 1]` or `(Theorem 1)`. |
| Page-aware reference request | `page_ref(obj)` | Keeps the reference structured, but validation emits `page-aware-reference-degrades` where stable page numbers are not portable. |

Use `Theme(captions=CaptionDefaults(...))` when figure and table caption labels
should differ from in-text reference labels. Equation, algorithm, code block,
box, and theorem-like block references use their own `reference_label` settings
where those blocks expose one.

## Renderer Policy

DOCX, PDF, and HTML render ordinary references as editable text with links or
anchors where the renderer supports them. Plural and range helpers resolve at
render time from the document index, so they work across tables, figures,
headings, equations, boxes, algorithms, listings, and theorem-like blocks.

Page-aware references are intentionally treated as a degrade path because DOCX,
PDF, and HTML do not share one stable page model. Prefer ordinary object
references for portable output, and reserve `page_ref(...)` for formats where a
renderer-specific page number is acceptable.
