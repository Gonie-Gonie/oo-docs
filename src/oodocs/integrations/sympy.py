"""Optional SymPy-to-OODocs equation adapter."""

from __future__ import annotations

from oodocs.components.blocks import Equation


def equation_from_sympy(expression: object, **equation_options: object) -> Equation:
    """Convert a SymPy expression to LaTeX and pass it to :class:`Equation`.

    SymPy is imported only when this function is called.  OODocs does not keep
    or evaluate the symbolic expression and defines no symbolic-expression DSL.
    """

    try:
        import sympy as sympy_module  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "equation_from_sympy requires SymPy. Install the appropriate optional dependency."
        ) from exc
    return Equation(str(sympy_module.latex(expression)), **equation_options)


__all__ = ["equation_from_sympy"]
