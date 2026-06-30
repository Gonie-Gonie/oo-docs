# Header And Footer Support Reference

OODocs covers common `fancyhdr` and `scrlayer-scrpage` running header and footer
needs through `Theme(header_footer=HeaderFooterDefaults(...))`.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Running header/footer templates | `HeaderFooterDefaults(...)` | Provides left, center, and right slots for headers and footers. |
| Page number integration | `{page}` token or `PageNumberDefaults(show_page_numbers=True)` | Legacy page-number settings are folded into effective footer templates. |
| Document title token | `{title}` | Resolves to the document title. |
| Running heading tokens | `{chapter}` and `{section}` | Resolve to the current chapter or section title where the renderer can track it. |
| First page style | `different_first_page=True` with `first_*` slots | Supports cover-page or first-page variants. |
| Odd/even page style | `different_odd_even_pages=True` with `even_*` slots | Supports even-page variants for two-sided layouts. |

## Renderer Mapping

DOCX uses section header/footer parts and Word fields such as `PAGE` and
`STYLEREF`. PDF draws header and footer text in the page callback. HTML emits a
sticky/fixed header-footer layer with print CSS, which is a visual degrade path
rather than a paginated layout engine.

Use `theme.resolve_header_footer_template(...)` and
`theme.format_header_footer_text(...)` when custom renderers need the same
template policy.
