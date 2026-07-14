# Cover Pages

`CoverPage` is a renderer-neutral container for optional cover-only content.
The visible document title still comes from `Document.title`; the subtitle and
authors still come from `TitleMatter`. This keeps a cover from duplicating or
overriding document identity.

```python
from oodocs import Author, CoverPage, Document, DocumentSettings, Paragraph, TitleMatter

cover = CoverPage(
    eyebrow="TECHNICAL NOTE",
    organization="Example Lab",
    logo="assets/example-logo.png",
    date="2026-07-14",
    footer="Internal review",
    note=Paragraph("Distribution is limited to the review team."),
)
settings = DocumentSettings(
    title_matter=TitleMatter(
        subtitle="Renderer comparison",
        authors=[Author("Review Lead")],
        cover=cover,
    )
)
document = Document("Output Quality Report", Paragraph("Body."), settings=settings)
```

All cover fields are neutral by default: eyebrow, organization, logo, date,
footer, and note are absent until the caller supplies them. `extra_top` and
`extra_bottom` accept ordinary blocks, while `note` accepts one block or a
sequence of blocks for legal, confidentiality, or distribution text.

## Logo Inputs

`CoverPage.logo` accepts the same inputs as `Figure`:

- a string or `Path` pointing to an image;
- image bytes or `ImageData`;
- an object with a compatible `savefig(...)` method.

The selected `CoverPageStyle` constrains the rendered logo with
`logo_max_width` and `logo_max_height`. It does not invent a logo or rewrite the
source asset. A missing or unsupported logo is reported as
`cover-asset-missing` during validation.

## Styles and Presets

`CoverPageStyle` controls only alignment, vertical position, spacing, text
styles, accent presentation, and maximum logo size. It does not carry project
content.

Use `CoverPagePreset.accented(...)` for a left-accented cover or
`CoverPagePreset.centered_logo(...)` for a centered, logo-led cover.

```python
from oodocs.presets.templates import CoverPagePreset

accented = CoverPagePreset.accented(
    organization="Example Lab",
    footer="Draft",
)
centered = CoverPagePreset.centered_logo(
    "assets/example-logo.png",
    organization="Example Lab",
)

accented_settings = accented.settings(subtitle="Verification summary")
centered_settings = centered.settings(subtitle="Annual review")
```

The preset names are `"Accented cover"` and `"Centered logo cover"`. Their
footer is `None` unless explicitly provided.

## Renderer and Validation Semantics

When `TitleMatter.cover` is `None`, renderers retain inline title-matter
behavior. When a cover is present, the cover consumes the title, subtitle, and
author display once and the body begins on a separate page in paginated
formats. HTML emits a `section` with the `oodocs-cover-page` class and applies
the `oodocs-page-break-after` print rule when document content follows.

Cover-scoped overlays remain ordinary `DocumentSettings.overlays`. Validation
reports `cover-overlay-without-cover` if such an overlay is configured without
a `TitleMatter.cover`. Cover assets are validated together with normal figure
assets before rendering.
