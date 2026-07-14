from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from oodocs.components.blocks import Equation
from oodocs.engineering import Quantity
from oodocs.integrations.pint import quantity_from_pint
from oodocs.integrations.sympy import equation_from_sympy


class _FakeUnits:
    def __init__(self, abbreviated: str) -> None:
        self.abbreviated = abbreviated

    def __format__(self, specification: str) -> str:
        assert specification == "~"
        return self.abbreviated

    def __str__(self) -> str:
        return self.abbreviated


def test_quantity_from_pint_reads_scalar_magnitude_without_conversion() -> None:
    source = SimpleNamespace(
        magnitude=Decimal("9.81"),
        units=_FakeUnits("m / s ** 2"),
    )

    quantity = quantity_from_pint(source)

    assert isinstance(quantity, Quantity)
    assert quantity.value == Decimal("9.81")
    assert quantity.unit == "m / s ** 2"
    assert quantity.plain_text() == "9.81 m / s²"


def test_quantity_from_pint_handles_dimensionless_and_invalid_objects() -> None:
    dimensionless = quantity_from_pint(
        SimpleNamespace(magnitude=Decimal("0.5"), units=_FakeUnits("dimensionless"))
    )
    assert dimensionless.plain_text() == "0.5"

    with pytest.raises(TypeError, match="magnitude and units"):
        quantity_from_pint(object())


def test_equation_from_sympy_only_passes_latex_to_existing_equation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_sympy = SimpleNamespace(latex=lambda expression: rf"x^2 + {expression}")
    monkeypatch.setitem(sys.modules, "sympy", fake_sympy)

    equation = equation_from_sympy("1", numbered=False, reference_label="Formula")

    assert type(equation) is Equation
    assert equation.expression == r"x^2 + 1"
    assert equation.numbered is False
    assert equation.reference_label == "Formula"


def test_equation_from_sympy_reports_missing_optional_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "sympy", None)
    with pytest.raises(ImportError, match="equation_from_sympy requires SymPy"):
        equation_from_sympy("x")


def test_engineering_core_and_adapter_imports_do_not_load_pint_or_sympy() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository_root / "src")
    script = """
import sys
from oodocs.engineering import Algorithm, NumberFormat, Quantity
import oodocs.integrations.pint
import oodocs.integrations.sympy

assert "pint" not in sys.modules
assert "sympy" not in sys.modules
assert Quantity(1, "m").plain_text() == "1 m"
assert NumberFormat(decimals=1).format(1) == "1.0"
assert Algorithm.__name__ == "Algorithm"
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repository_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
