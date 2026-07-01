# Math Support Reference

OODocs renders math as editable text fragments across DOCX, PDF, and HTML. It
does not embed a full TeX engine, so authoring should use OODocs-native blocks
for structure and lightweight LaTeX-like source for expressions.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Inline expression in prose | `inline_math(...)` or `Math(...)` | Best for short symbols and formulas inside a paragraph. |
| Display equation | `Equation(...)` | Numbered by default and referenceable. |
| Aligned derivation | `Equation.aligned(...)` | Accepts `&` alignment markers and omits them from rendered text. |
| Piecewise cases | `Equation.cases(...)` | Use OODocs case rows instead of a raw TeX `cases` environment. |
| Symbolic expression | `Equation.from_sympy(...)` | Uses `sympy.latex(...)` when SymPy is installed. |

`Equation(numbered=True)` is the default and consumes the document equation
counter. `Equation(numbered=False)` does not consume a number; references to an
unnumbered equation require an explicit label such as
`equation.ref("the loss definition")`.

`Equation.aligned(...)` and `Equation.cases(...)` are the canonical authoring
entry points for structured display math. The concrete `AlignedEquation(...)`
and `CasesEquation(...)` classes remain available from `oodocs.equations` for
advanced code that needs explicit types, but they are not part of the top-level
`oodocs` import surface.

## Lightweight Parser Matrix

| Syntax | Status | Rendered behavior |
|---|---|---|
| Plain text, numbers, operators, parentheses | Supported | Rendered as text. |
| Superscript and subscript: `x^2`, `x_0`, `x^{n+1}` | Supported | Uses vertical-align styling where the renderer supports it. |
| Front scripts: `\prescript{14}{6}{C}` | Supported | Renders the front superscript and subscript before the base. |
| Greek letters and common math symbols such as `\alpha`, `\leq`, `\to` | Supported subset | Rendered as readable text approximations. |
| Text/group commands: `\text{...}`, `\mathrm{...}`, `\mathbf{...}`, `\operatorname{...}` | Supported subset | Renders the braced content directly. |
| Fractions: `\frac{a}{b}`, `\dfrac{a}{b}`, `\tfrac{a}{b}` | Supported approximation | Renders as `(a)/(b)`, not as stacked math layout. |
| Roots: `\sqrt{x}` | Supported approximation | Renders as `sqrt(x)`. |
| Delimiters: `\left`, `\right` | Supported subset | Emits the delimiter text and skips invisible delimiters such as `\right.`. |
| Line break command: `\\` | Supported | Renders as a line break/newline inside the expression text. |
| `aligned`, `align`, `split`, and `multline` environments | Use native blocks | Use `Equation.aligned(...)` instead of raw TeX environments. |
| `cases` environment | Use native blocks | Use `Equation.cases(...)` instead of raw TeX environments. |
| `matrix`, `pmatrix`, `bmatrix`, `array` environments | Not supported | Use an OODocs `Table(...)` for matrix-like data, or provide a readable text expression. |
| Arbitrary TeX macros or packages | Not supported | Validation emits `unsupported-latex-command` warnings. |

The supported command allow-list is intentionally small so DOCX, PDF, and HTML
stay consistent. When exact mathematical layout matters more than editability,
render the equation externally as an image and insert it as a `Figure(...)`.
