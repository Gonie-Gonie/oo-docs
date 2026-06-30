"""Chemistry convenience API.

Attributes:
    ChemicalFormula: Inline chemical formula rendered with numeric
        subscripts.
    ReactionEquation: Displayed chemical reaction equation.
    ce: Short helper mirroring mhchem's ``\\ce{...}`` command.
    chemical_formula: Helper for creating inline chemical formulas.
"""

from __future__ import annotations

from oodocs.components.blocks import ReactionEquation
from oodocs.components.chemistry import ChemicalFormula, chemical_formula
from oodocs.styles import TextStyle


def ce(source: str, *, style: TextStyle | None = None) -> ChemicalFormula:
    """Create an inline chemical formula.

    Args:
        source: Formula source such as ``"H2O"`` or ``"SO4^2-"``.
        style: Optional inline style.

    Returns:
        Inline chemical formula fragment.

    Examples:
        ```python
        from oodocs.chemistry import ce

        water = ce("H2O")
        ```
    """

    return chemical_formula(source, style=style)


__all__ = [
    "ChemicalFormula",
    "ReactionEquation",
    "ce",
    "chemical_formula",
]
