# Equation numbering and aligned equations

`Equation(numbered=True)` is the default and consumes the document equation
counter. `Equation(numbered=False)` does not consume a number. An unnumbered
equation can still be linked with explicit visible text, for example
`equation.link("the loss definition")`.

`Equation.aligned(...)` and `Equation.cases(...)` are the canonical authoring
entry points for structured display math. The concrete `AlignedEquation(...)`
and `CasesEquation(...)` classes remain available from `oodocs.equations` for
code that needs explicit types; they are not part of the top-level `oodocs`
import surface.

Use `EquationLine` when a row in an aligned derivation needs its own number,
reference, or internal link. A line remains a child of `AlignedEquation`; it is
not an independent document block.

```python
from oodocs import Document, Paragraph
from oodocs.equations import AlignedEquation, EquationLine

primary = EquationLine(
    r"E_{\mathrm{area}} &= \frac{\sum_f E_f c_f}{A}",
    identifier="area-energy",
)
ghg = EquationLine(
    r"G_{\mathrm{area}} &= \frac{\sum_f E_f g_f}{A}",
)

group = AlignedEquation(primary, ghg, numbering="each")
document = Document(
    "Area metrics",
    Paragraph("The energy result is ", primary.ref(), "."),
    group,
)
```

Unescaped `&` characters mark alignment columns. OODocs keeps those markers in
the model so DOCX, PDF, and HTML renderers can align corresponding cells. A
plain renderer may use `EquationLine.render_expression()` as a readable
fallback without the markers.

## Numbering modes

`AlignedEquation.numbering` accepts exactly three values:

- `"group"` assigns one number and anchor to the aligned equation.
- `"each"` assigns a number and anchor to every row whose `numbered` field is
  true.
- `"none"` displays no equation numbers.

String rows are converted to `EquationLine` automatically. The older
`numbered=True` and `numbered=False` keywords remain compatible and map to
`"group"` and `"none"`, respectively.

An unnumbered row can still be linked by visible text:

```python
condition = EquationLine(r"m &> 0", numbered=False, identifier="mass-condition")
derivation = AlignedEquation(condition, numbering="each")
sentence = Paragraph("Assume ", condition.link("positive mass"), ".")
```

## Scoped block counters

`CounterPolicy` applies a counter style, restart scope, and output template to
tables, figures, equations, listings, or theorem-like countable blocks.
`NumberingDefaults` keeps document-wide integer numbering unless overridden.

```python
from oodocs.styles import CounterPolicy, NumberingDefaults

numbering = NumberingDefaults(
    equation=CounterPolicy(
        scope="chapter",
        include_parent=True,
        template="{parent}.{value}",
    )
)
```

The supported scopes are `"document"`, `"part"`, `"chapter"`, and
`"section"`. When `include_parent=True`, the containing scope must have a
numbered heading. For example, chapter-scoped equations become `1.1`, `1.2`,
then restart as `2.1` in the next chapter.

## Variable descriptions

Use the general `DescriptionList` component for variables immediately below a
formula. OODocs intentionally does not define an equation-only nomenclature
block. Use `Nomenclature` only when the document needs one consolidated symbol
list.

```python
from oodocs import DescriptionItem, DescriptionList

variables = DescriptionList(
    (
        DescriptionItem("A", "Reference area"),
        DescriptionItem("E_f", "Energy factor for flow f"),
    )
)
```
