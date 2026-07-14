# Math Support Reference

OODocs renders math as editable text fragments across DOCX, PDF, and HTML. It
does not embed a full TeX engine, so authoring should use OODocs-native blocks
for structure and lightweight LaTeX-like source for expressions.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Inline expression in prose | `inline_math(...)` or `Math(...)` | Best for short symbols and formulas inside a paragraph. |
| Display equation | `Equation(...)` | A structured display block; numbering is documented separately. |
| Aligned derivation | `Equation.aligned(...)` | Accepts `&` alignment markers and omits them from rendered text. |
| Piecewise cases | `Equation.cases(...)` | Use OODocs case rows instead of a raw TeX `cases` environment. |
| Symbolic expression | `equation_from_sympy(...)` from `oodocs.integrations.sympy` | Uses `sympy.latex(...)` when SymPy is installed. |

Use `Equation.aligned(...)` and `Equation.cases(...)` as the canonical
top-level authoring entry points for structured display math. See
[Equation numbering and aligned equations](equation-numbering.md) for numbered
and unnumbered displays, per-line references, concrete aligned/cases classes,
and scoped counter policies.

SymPy support stays outside the core equation model. Install the `sympy`
optional dependency and import the integration explicitly:

```powershell
pip install "oodocs[sympy]"
```

```python
from oodocs.integrations.sympy import equation_from_sympy

equation = equation_from_sympy(sympy_expression, numbered=False)
```

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
