# References and links

OODocs keeps semantic references, plain internal links, and external hyperlinks
as separate authoring choices. Together they cover common `cleveref`,
`varioref`, and `hyperref` authoring needs without raw LaTeX commands.

## Choose the right object

| Need | Use | Result |
|---|---|---|
| Single typed reference | `ref(obj)` or `obj.ref()` | A renderer-managed label such as `Figure 1` or `Section 2.1`. |
| Plural references | `refs([a, b])` | Several same-kind targets, using `plural_label=...` when configured. |
| Reference range | `ref_range(a, b)` | A compact range controlled by `range_separator`. |
| Bracketed or parenthesized reference | `bracket_ref(obj)` or `paren_ref(obj)` | A wrapper such as `[Figure 1]` or `(Section 2)`. |
| Page-aware request | `page_ref(obj)` | A structured request that can emit `page-aware-reference-degrades`. |
| Plain object link | `obj.link("label")` | A hyperlink to the object without a typed number. |
| Named external link | `link(target, label)` | A label whose destination is an external URL. |
| Visible URL | `url(target, breakable=True)` | The URL as visible text with safe soft-break opportunities. |
| Advanced explicit anchor | `Hyperlink.internal_anchor(...)` | A link to a known generated or authored anchor. |

`ReferenceFormat(...)` controls `label`, `plural_label`, capitalization,
separators, `range_separator`, prefix, suffix, and an optional template. Page-aware
references are intentionally treated as a degrade path because DOCX, PDF, and
HTML do not share one stable page model.

The following example uses a numbered reference, an unnumbered object link, and
an external link in one document:

```python
from oodocs import Document, Paragraph, Section, link

overview = Section("Overview", numbered=False, toc=False, anchor="overview")
details = Section("Details", level=1)

overview.add(Paragraph("Continue with ", details.ref(), "."))
details.add(Paragraph("Return to ", overview.link(), "."))

document = Document(
    "Navigation",
    overview,
    details,
    Paragraph("External guide: ", link("https://example.com", "website")),
)
```

An object link without an explicit label derives its text from the target's
title, caption, or plain-text representation. Supply a label when the target
has no meaningful default. Object links can appear anywhere inline content is
accepted, including table cells, figure captions, and `DescriptionList`
definitions. Raw object insertion inside `Paragraph(...)` is rejected; use a
reference or link so validation can verify the target.

## Anchors and validation

DOCX bookmarks, PDF destinations, and HTML fragment identifiers use the same
render-index anchor. An explicitly anchored section remains linkable even when
both `numbered=False` and `toc=False`. Automatically generated anchors are
stable for an object's identity during one document build. Mutual links work
because indexing completes before rendering begins.

Validation reports these relevant codes:

- `missing-object-link-target`: the linked object is not in the document body.
- `unsupported-object-link-target`: the object has no renderer anchor.
- `duplicate-anchor`: two different objects claim the same explicit anchor.
- `page-aware-reference-degrades`: stable page numbers are not portable.
- `overly-long-url`: a raw visible URL cannot wrap safely.

Broken internal link validation is a preflight error for DOCX, PDF, and HTML.

## Locale-aware labels and templates

`Theme.references` maps a target kind to a `ReferenceTemplate`. Supported keys
include `part`, `chapter`, `section`, `paragraph`, `table`, `figure`, `equation`,
`code_block`, `box`, and `countable`.

Each template controls both the label and the placement of `{label}` relative
to `{value}`. English defaults put the label first (`Chapter 1`); the Korean
locale uses suffix placement for chapters and sections (`1장`, `1.2절`):

```python
from oodocs import DocumentSettings, Theme

settings = DocumentSettings(theme=Theme.from_locale("ko-KR"))
```

Custom templates can define singular and plural layouts:

```python
from oodocs import Theme
from oodocs.styles import ReferenceDefaults, ReferenceTemplate

theme = Theme(
    references=ReferenceDefaults(
        {
            "figure": ReferenceTemplate(
                "Diagram",
                plural_label="Diagrams",
                template="{label} {value}",
                plural_template="{label} ({value})",
            )
        }
    )
)
```

Reference formatting resolves in this order:

1. A per-reference `ReferenceFormat(...)`, including its optional template.
2. The target kind's entry in `Theme.references`.
3. The target object's `reference_label` settings.
4. The locale default.

Caption labels and reference labels are independent. Changing an in-text table
reference to `Tbl. 1` does not change its caption from `Table 1. ...`.

## URL line-break policy

`url(target, label=None, breakable=True)` preserves the external link target
exactly while making the visible label safer for fixed-page renderers. With no
label, OODocs inserts zero-width soft break points into the displayed URL.
DOCX, PDF, and HTML keep the original target in their hyperlink relationship,
URI action, or `href` attribute.

Use `label=...` for short human-readable text. If the URL itself must be shown,
use `url(..., breakable=True)` to avoid renderer-dependent wrapping and the
`overly-long-url` warning.

## Metadata, outlines, and renderer mapping

OODocs manages hyperlink, anchor, metadata, and outline behavior through
document objects:

- `DocumentSettings(metadata=DocumentMetadata(...))` maps title, author,
  subject, description, and keywords to supported outputs.
- `Theme(links=LinkDefaults(TextStyle(...)))` controls hyperlink label styling.
- `DocumentMetadata.title` overrides the visible title for file and browser
  metadata; otherwise renderers use the document title.
- Headings with `toc=True` participate in generated contents and PDF
  outline/bookmarks. Use `toc=False` to omit a visible heading from both.

| Feature | DOCX | PDF | HTML |
|---|---|---|---|
| External links | Word hyperlink relationships | URI links | `<a href="...">` |
| Internal links | Word bookmarks and links | Named destinations | Fragment links |
| Metadata | Core properties | PDF info dictionary | `<title>` and meta tags |
| Outline | Word navigation | PDF outline/bookmarks | Heading/anchor structure |
| Broken target | Preflight error | Preflight error | Preflight error |
