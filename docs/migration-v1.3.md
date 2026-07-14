# Migrating to OODocs 1.3

OODocs 1.3 requires Python 3.11 or later and narrows the top-level import
surface. Core authoring objects remain available from `oodocs`; focused models
belong to their domain namespaces.

## Import Changes

| 1.2 API | 1.3 replacement |
|---|---|
| `oodocs.adapters.*` | The matching collector under `oodocs.integrations.*` |
| Adapter `ProjectInfo`, `WorkflowSummary`, or `ManifestSummary` | `oodocs.metadata` |
| Adapter `EvidenceReport` | `oodocs.evidence` |
| Schema models | `oodocs.schema` |
| CLI documentation models | `oodocs.clidoc` |
| Engineering presentation models | `oodocs.engineering` |
| Multi-document composition | `oodocs.suite` |
| `Equation.from_sympy(...)` | `oodocs.integrations.sympy.equation_from_sympy(...)` |

Style and default configuration helpers are canonical under `oodocs.styles`.
Component presets are under `oodocs.presets.components`; document templates
and cover presets are under `oodocs.presets.templates`.

## Cover Pages and Document Matter

Replace the removed boolean title-page switch with a real cover object:

```python
from oodocs import CoverPage, TitleMatter

title_matter = TitleMatter(
    subtitle="Verification summary",
    cover=CoverPage(organization="Example Lab"),
)
```

Replace removed project-branded cover factories with
`CoverPagePreset.accented(...)` or `CoverPagePreset.centered_logo(...)`, and
provide organization, logo, footer, and other branding in application code.

Use `FrontMatter`, `MainMatter`, and `BackMatter` when page-number transitions
or generated front/back pages must be stable. Legacy documents without these
containers continue to use a single body flow.

## References and Links

Numbered targets use `target.ref()`. An unnumbered target has no semantic
number, so link to it with `target.link("label")` instead of inserting the raw
block into a paragraph or forcing a numbered reference.

## Optional Dependencies

The `integrations` extra installs PyYAML and Pydantic support. BibTeX, Pint,
SymPy, and API documentation dependencies use their focused `bibtex`, `pint`,
`sympy`, and `apidoc` extras. Core `NumberFormat` and `Quantity` objects need no
extra dependency.
