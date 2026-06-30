# Locale Support Reference

OODocs covers common `babel` and `polyglossia` document-language needs with
locale bundles under `Theme`.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Locale bundle | `Theme.from_locale("ko-KR")` | Creates a `Theme` from built-in locale defaults. |
| Direct locale defaults | `LocaleDefaults.from_locale("ko-KR")` | Returns labels, generated page titles, typography defaults, date formatting, and PDF font guidance. |
| Caption localization | `CaptionDefaults(...)` or locale defaults | Controls table and figure caption labels and reference labels. |
| Generated title localization | `GeneratedContentDefaults(...)` or locale defaults | Controls table of contents, lists, references, glossary, and similar generated page titles. |
| Date formatting | `theme.format_date(value)` | Formats `date` objects and ISO date strings with the active locale. |
| Language tag | `theme.resolve_language_tag()` | Supplies renderer language metadata such as HTML `lang` and DOCX language settings. |
| PDF font guidance | `theme.pdf_font_fallback_guide()` | Describes font families that should support the active script. |

## Policies

Locale bundles are intentionally smaller than full TeX language packages. They
cover document labels, generated titles, date formatting, language metadata, and
font guidance. Hyphenation and script shaping remain renderer-dependent.

Use direct `CaptionDefaults(...)` or `GeneratedContentDefaults(...)` overrides
when one project needs custom wording on top of a built-in locale. Use explicit
typography settings when a PDF target needs an installed font for the document
script.
