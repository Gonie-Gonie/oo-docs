# References and internal links

OODocs has two related but separate ways to navigate within a document:

- `target.ref()` creates a semantic, numbered reference such as `Section 2.1`.
- `target.link("label")` creates a hyperlink to an object and uses exactly the supplied label. It does not require or display a number.

Use the module-level `link(url, label)` helper for an external URL. It is not an alias for the object method:

```python
from oodocs import Document, Paragraph, Section, link

overview = Section(
    "Overview",
    numbered=False,
    toc=False,
    anchor="overview",
)
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

An object link without an explicit label derives its text from the target's title, caption, or plain-text representation. Supply a label when the target has no meaningful default. Object links can appear anywhere inline content is accepted, including table cells, figure captions, and `DescriptionList` definitions.

## Anchors and validation

DOCX bookmarks, PDF destinations, and HTML fragment identifiers all use the same render-index anchor. An explicitly anchored section remains linkable even when both `numbered=False` and `toc=False`. Automatically generated anchors are stable for an object's identity during one document build.

Validation reports these object-link contract codes:

- `missing-object-link-target`: the linked object is not in the document body.
- `unsupported-object-link-target`: the object is present but has no renderer anchor.
- `duplicate-anchor`: two different objects claim the same explicit anchor.

Mutual links are supported: two sections can link to each other because indexing completes before rendering begins.

## Locale-aware numbered references

`Theme.references` maps a fixed target kind to a `ReferenceTemplate`. Supported keys are `part`, `chapter`, `section`, `paragraph`, `table`, `figure`, `equation`, `code_block`, `box`, and `countable`.

Each template controls both the label and the placement of `{label}` relative to `{value}`. English defaults put the label first (`Chapter 1`); the Korean locale uses suffix placement for chapters and sections (`1장`, `1.2절`):

```python
from oodocs import DocumentSettings, Theme

settings = DocumentSettings(theme=Theme.from_locale("ko-KR"))
```

Custom templates can also define plural labels and a distinct plural layout:

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

Reference formatting is resolved in this order:

1. A per-reference `ReferenceFormat`, including its optional `template`.
2. The target kind's entry in `Theme.references`.
3. The target object's `reference_label`, including a table or figure reference label.
4. The locale default.

Caption labels and reference labels are independent. Changing a table reference to `Tbl. 1` does not change its caption from `Table 1. ...`.

The helpers `refs([...])` and `ref_range(a, b)` use plural labels/templates when targets share a kind. `paren_ref`, `bracket_ref`, and `page_ref` preserve the same template. Page-aware references currently render as ordinary references and produce the `page-aware-reference-degrades` compatibility warning.
