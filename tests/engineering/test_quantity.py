from __future__ import annotations

from decimal import Decimal

import pytest

from oodocs import Paragraph, Table, TableCell
from oodocs.components.descriptions import DescriptionItem
from oodocs.components.inline import Text
from oodocs.engineering import Algorithm, NumberFormat, Quantity


def test_engineering_package_preserves_algorithm_export() -> None:
    assert Algorithm.__name__ == "Algorithm"


def test_number_format_supports_explicit_presentation_policies() -> None:
    assert NumberFormat(decimals=2, thousands_separator=True).format(Decimal("12500")) == (
        "12,500.00"
    )
    assert NumberFormat(significant_digits=3).format(Decimal("12.3456")) == "12.3"
    assert NumberFormat(
        significant_digits=4,
        scientific=True,
        trim_trailing_zeros=True,
    ).format(Decimal("12000")) == "1.2e+4"
    assert NumberFormat(decimals=4, trim_trailing_zeros=True).format(Decimal("1.2300")) == (
        "1.23"
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"decimals": -1}, "decimals"),
        ({"significant_digits": 0}, "significant_digits"),
        (
            {"decimals": 2, "significant_digits": 3},
            "mutually exclusive",
        ),
    ],
)
def test_number_format_rejects_ambiguous_or_invalid_precision(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        NumberFormat(**kwargs)  # type: ignore[arg-type]


def test_quantity_preserves_raw_values_and_formats_plain_text() -> None:
    raw_value = Decimal("12500")
    quantity = Quantity(
        raw_value,
        "N",
        NumberFormat(decimals=2, thousands_separator=True),
        Decimal("25"),
    )

    assert isinstance(quantity, Text)
    assert quantity.value is raw_value
    assert quantity.plain_text() == "12,500.00 ± 25.00 N"
    assert not hasattr(quantity, "to")
    assert not hasattr(quantity, "dimensionality")


def test_quantity_keeps_preformatted_string_values_exact() -> None:
    quantity = Quantity(
        "001.2300",
        "kg",
        NumberFormat(decimals=1, thousands_separator=True, scientific=True),
        "0.0100",
    )

    assert quantity.plain_text() == "001.2300 ± 0.0100 kg"


def test_quantity_normalizes_portable_unit_scripts_and_degree_symbols() -> None:
    assert Quantity(2, "m^2").plain_text() == "2 m²"
    assert Quantity(9.81, "m/s^-2").plain_text() == "9.81 m/s⁻²"
    assert Quantity("0.026", "W/(m*K)").plain_text() == "0.026 W/(m*K)"
    assert Quantity(21, "degC").plain_text() == "21 °C"
    assert Quantity(70, "degrees Fahrenheit").plain_text() == "70 °F"
    assert Quantity(1, "CO_2").plain_text() == "1 CO₂"

    assert Quantity(2, "m^2").screen_reader_text() == "2 m squared"
    assert Quantity(21, "degC", uncertainty=1).screen_reader_text() == (
        "21 plus or minus 1 degrees Celsius"
    )
    assert Quantity(1, "CO_2").screen_reader_text() == "1 CO subscript 2"


def test_quantity_is_accepted_by_inline_authoring_surfaces() -> None:
    quantity = Quantity(12.5, "m^2", NumberFormat(decimals=1))
    paragraph = Paragraph("Area: ", quantity)
    table_cell = TableCell(quantity)
    table = Table(
        ["Metric", "Value"],
        [["Area", quantity]],
        caption=Quantity("12.5", "m^2"),
    )
    description = DescriptionItem(quantity, Paragraph("Measured area."))

    assert paragraph.plain_text() == "Area: 12.5 m²"
    assert table_cell.content.plain_text() == "12.5 m²"
    assert table.rows[0][1].content.plain_text() == "12.5 m²"
    assert table.caption is not None
    assert table.caption.plain_text() == "12.5 m²"
    assert description.plain_term() == "12.5 m²"


@pytest.mark.parametrize("value", [True, object(), [1, 2]])
def test_quantity_rejects_non_scalar_values(value: object) -> None:
    with pytest.raises(TypeError, match="Quantity.value"):
        Quantity(value)  # type: ignore[arg-type]
