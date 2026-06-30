# Chemistry Support Reference

OODocs provides mhchem-inspired helpers in the `oodocs.chemistry` namespace. The
helpers convert common chemistry notation into the same lightweight math
fragments used by DOCX, PDF, and HTML renderers; they are not a complete
`mhchem` parser.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Inline chemical formula | `chemical_formula(...)` or `ChemicalFormula(...)` | Renders numeric suffixes as subscripts and charges as superscripts. |
| mhchem-style shorthand | `ce(...)` | Accepts the same inline formula source and mirrors the familiar `\ce{...}` name. |
| Displayed reaction | `ReactionEquation(...)` | Uses the equation counter with the default reference label `Reaction`. |

Use `oodocs.chemistry` as the canonical namespace. `oodocs.chem` is kept as a
compatibility namespace for existing code.

## Formula Input Policy

| Source pattern | Status | Rendered behavior |
|---|---|---|
| `H2O`, `CO2`, `Ca(OH)2` | Supported | Digits after an element or group become subscripts. |
| `2H2 + O2 -> 2H2O` | Supported | Leading stoichiometric coefficients stay baseline; formula suffixes still become subscripts. |
| `SO4^2-`, `NH4+` | Supported | Explicit `^...` charges and trailing signs become superscripts. |
| Unicode subscripts such as `Ca(OH)₂` | Supported | Unicode subscript digits normalize to ordinary subscript runs. |
| Unicode superscripts such as `Fe³+` or `SO₄²⁻` | Supported | Unicode superscript digits and signs normalize to superscript runs. |
| Surrounding `\ce{...}` wrapper | Supported | The wrapper is stripped before parsing. |
| Reaction arrows such as `->` | Plain text | Rendered as typed; OODocs does not balance reactions or model arrow annotations. |
| Phases, catalysts, over/under arrows, equilibrium arrows, or full mhchem grammar | Not supported | Write a readable text fallback or render specialized chemistry externally as an image. |

DOCX uses editable runs with subscript and superscript formatting. HTML emits
`<sub>` and `<sup>` tags. PDF keeps text extraction readable, although the exact
visual baseline follows ReportLab text rendering rather than TeX layout.
