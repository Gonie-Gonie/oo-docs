# Quantity Formatting

`NumberFormat` and `Quantity` are presentation objects for values that already
have their intended meaning. They do not convert units, check dimensions, or
evaluate symbolic expressions.

```python
from decimal import Decimal

from oodocs import Paragraph, Table, TableCell
from oodocs.engineering import NumberFormat, Quantity

format_policy = NumberFormat(decimals=2, thousands_separator=True)
load = Quantity(Decimal("12500"), "N", number_format=format_policy)
temperature = Quantity("21.50", "degC")
conductivity = Quantity(0.026, "W/(m*K)", uncertainty=0.001)

paragraph = Paragraph("Design load: ", load, ".")
table = Table(
    ["Property", "Value"],
    [
        ["Temperature", TableCell(temperature)],
        ["Conductivity", conductivity],
    ],
)
```

A string value such as `"21.50"` is displayed exactly as supplied, even when a
`NumberFormat` is present. Numeric values can use decimal places, significant
digits, grouping, scientific notation, and optional trailing-zero trimming.
`decimals` and `significant_digits` are mutually exclusive.

Units are display-only strings. A space is inserted before the unit; integer
scripts such as `m^2`, `s^-1`, and `CO_2` are rendered with portable script
characters, and `degC`/`degF` become `°C`/`°F`. HTML also includes an expanded
assistive label. Because `Quantity` is an ordinary inline `Text`, it can be used
in paragraphs, table cells, captions, and description-item content.

## Optional integrations

Pint and SymPy are not core dependencies. `NumberFormat` and `Quantity` work
without either package. Install only the bridges used by the application:

```powershell
pip install "oodocs[pint,sympy]"
```

Import the integrations explicitly:

```python
from oodocs.integrations.pint import quantity_from_pint
from oodocs.integrations.sympy import equation_from_sympy

display_value = quantity_from_pint(pint_quantity)
equation = equation_from_sympy(sympy_expression, numbered=False)
```

`quantity_from_pint()` reads the existing magnitude and unit label without
conversion or dimension checking. `equation_from_sympy()` asks SymPy for a
LaTeX string and passes that string to the existing `Equation` model. The
official equation sources remain `Equation`, `AlignedEquation`, and
`CasesEquation`; OODocs does not provide a symbolic algebra DSL.
