# Template Preset Support Reference

OODocs covers common `article`, `report`, `book`, and KOMA-Script class needs
with template presets and ordinary document blocks. The presets create normal
`Document` objects; callers can still add blocks, validate, and render through
the standard APIs.

## LaTeX Class Mapping

| LaTeX need | Use | Notes |
|---|---|---|
| Article-style manuscript | `JournalArticleTemplate(...)` | Builds title matter, optional abstract, keywords, article sections, acknowledgements, data availability, and references. |
| Technical report | `TechnicalReportTemplate(...)` | Builds cover-page title matter, optional table of contents, executive summary, sections, appendices, and references. |
| Software manual | `SoftwareManualTemplate(...)` | Builds overview, manual sections, appendices, and optional generated pages for documentation workflows. |
| Book-like document | `BookTemplate(...)` | Accepts `front_matter=...`, `parts=...`, `chapters=...`, `appendices=...`, and `back_matter=...`. |
| Reusable cover page | `CoverPagePreset.eplus_simple(...)` | Produces `DocumentSettings(...)` with cover-scoped overlays and title-matter defaults. |
| Direct assembly | `Section(...)`, `Chapter(...)`, `Part(...)`, and `Appendix(...)` | Use when the document shape is unique and a preset would hide more than it helps. |

## Matter And Structure Policy

OODocs treats document classes as content presets, not as raw TeX class
emulation. Use `Section(..., numbered=False)` for article-style front matter
such as abstracts, acknowledgements, and declarations. Use `Chapter(...)` and
`Part(...)` for report or book bodies, and `Appendix(...)` for appendix material
that should switch child chapter labels to `A`, `B`, `C`.

Report, manual, and book presets expose `front_matter=...` and
`back_matter=...` inputs. `BookTemplate(...)` also exposes `parts=...` and
`chapters=...`, which map to book-like divisions without requiring a separate
document-class object.

## Styling Boundary

KOMA-Script-style typography and layout defaults should be expressed through
`Theme(...)`, `DocumentSettings(title_matter=...)`, and
`DocumentSettings(page_layout=...)`. Template presets provide useful starting
points, while local `Section(...)`, `HeadingStyle(...)`, and theme overrides
remain available for project-specific rules.

The runnable catalog in `examples/template_presets/` demonstrates
`CoverPagePreset`, `JournalArticleTemplate`, `TechnicalReportTemplate`,
`SoftwareManualTemplate`, and `BookTemplate` alongside direct manuscript
assembly.
