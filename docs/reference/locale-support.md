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
| PDF font guidance | `theme.pdf_font_fallback_guide()` | Describes preferred system font families and the portable fallback policy for the active script. |

## Policies

Locale bundles are intentionally smaller than full TeX language packages. They
cover document labels, generated titles, date formatting, language metadata, and
font guidance. Hyphenation and script shaping remain renderer-dependent.

Use direct `CaptionDefaults(...)` or `GeneratedContentDefaults(...)` overrides
when one project needs custom wording on top of a built-in locale. Use explicit
typography settings when a PDF target needs an installed font for the document
script.

PDF rendering prefers the requested installed font. For a non-WinAnsi text run
whose resolved font lacks one or more glyphs, OODocs switches only that run to
a bundled ReportLab Korean CID font; ordinary ASCII text keeps the requested
font and its metrics. This portable fallback covers Korean labels and common
non-WinAnsi symbols used by the built-in locales, but it is not a universal
emoji font or a complex-script shaping engine. Select and distribute an
appropriate font explicitly when a target script falls outside that coverage.
