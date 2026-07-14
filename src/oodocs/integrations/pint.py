"""Optional Pint-to-OODocs adapter.

Importing this module does not import Pint.  The adapter consumes the small
``magnitude``/``units`` protocol exposed by Pint quantities.
"""

from __future__ import annotations

from oodocs.engineering import Quantity


def quantity_from_pint(value: object) -> Quantity:
    """Return a display-only :class:`~oodocs.engineering.Quantity`.

    No conversion or dimensional analysis is requested from Pint.  Unit
    formatting prefers Pint's abbreviated ``~`` format and falls back to the
    ordinary string representation.
    """

    if not hasattr(value, "magnitude") or not hasattr(value, "units"):
        raise TypeError("quantity_from_pint expects an object with magnitude and units")
    magnitude = value.magnitude  # type: ignore[attr-defined]
    units = value.units  # type: ignore[attr-defined]
    try:
        unit = format(units, "~")
    except (TypeError, ValueError):
        unit = str(units)
    normalized_unit = None if unit.strip().lower() in {"", "dimensionless"} else unit
    return Quantity(magnitude, unit=normalized_unit)


__all__ = ["quantity_from_pint"]
