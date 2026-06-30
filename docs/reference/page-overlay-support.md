# Page Overlay Support Reference

OODocs covers common `eso-pic`, `background`, and `wallpaper` page decoration
needs with positioning objects and scoped overlays.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Shape overlay | `Shape.rect(...)`, `Shape.ellipse(...)`, or `Shape.line(...)` | Draws positioned rules, frames, and badges. |
| Text watermark | `TextBox(...)` | Places fixed text such as `DRAFT`, review labels, or cover marks. |
| Image watermark | `ImageBox(...)` | Places a fixed image or logo. |
| Overlay registration | `DocumentSettings(overlays=[...])` | Keeps positioned objects out of the normal body flow. |
| Page scope | `PageItemScope.all()`, `.cover()`, `.front()`, `.main()`, or `.pages(...)` | Limits overlays to all pages, the cover page, front matter, main matter, or page ranges. |
| Anchoring | `anchor="page"`, `anchor="margin"`, or a named item | Positions one object relative to a page box, margin box, or earlier named item. |
| Stacking | `z_index=...` | Controls ordering among overlay items. |
| Inline drawing | `placement="inline"` | Places the same positioned object in the text flow instead of the page overlay layer. |

## Renderer Policy

PDF applies page scopes to physical pages. DOCX and HTML use section or static
frame fallbacks for scoped overlays and validation emits
`page-item-scope-static-output` when a scope cannot be represented exactly.

Cover page presets can return settings with cover-only overlays. This keeps
title-page decoration separate from body content and avoids the older
`page_items` naming in public user APIs.
