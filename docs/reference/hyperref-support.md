# Hyperref Support Reference

OODocs handles hyperlink, anchor, metadata, and outline behavior through
document objects rather than raw LaTeX commands.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Named external link | `link(target, label)` | Keeps link text separate from the target URL. |
| Visible URL | `url(target, breakable=True)` | Inserts soft break points in long visible URL labels. |
| Internal object reference | `ref(obj)`, `obj.ref()`, `refs(...)`, or `ref_range(...)` | Uses renderer-managed anchors for headings, captions, equations, boxes, algorithms, listings, and other numbered blocks. |
| Explicit internal HTML-style anchor | `Hyperlink.internal_anchor(...)` | Advanced API for linking to a known generated or authored anchor. |
| Output metadata | `DocumentSettings(metadata=DocumentMetadata(...))` | Maps title, author, subject, description, and keywords to supported renderers. |
| Link styling | `Theme(links=LinkDefaults(TextStyle(...)))` | Sets the default inline style for hyperlink labels. |

## Renderer Mapping

| Feature | DOCX | PDF | HTML |
|---|---|---|---|
| External hyperlinks | Word hyperlink relationships | URI links | `<a href="...">` |
| Internal references | Word bookmarks and links | PDF named destinations | Fragment links |
| Heading and caption anchors | Word bookmarks | PDF bookmarks/destinations | Element `id` attributes |
| PDF/document metadata | Core properties | PDF info dictionary | `<title>` and meta tags |
| PDF outline/bookmarks | Uses Word navigation from headings/bookmarks | Headings with `toc=True` create PDF outline entries | Browser outline comes from headings and anchors |
| Link color and underline | Inline run styling | Inline text styling | Inline CSS from `LinkDefaults` |
| Broken internal link validation | Preflight error | Preflight error | Preflight error |

## Policies

- `DocumentMetadata.title` overrides the visible document title for file/browser
  metadata. If it is omitted, renderers fall back to the document title.
- `DocumentMetadata.description` maps to DOCX comments and HTML description.
  PDF has no separate description field in the current metadata model.
- Headings that participate in generated contents (`toc=True`) also participate
  in PDF outline generation. Use `toc=False` for headings that should remain
  visible but not appear in contents or PDF bookmarks.
- Raw object insertion inside `Paragraph(...)` is rejected for references; use
  `ref(obj)` or `obj.ref()` so validation can verify the target.
- Page-aware references degrade where rendered page numbers are not stable.
