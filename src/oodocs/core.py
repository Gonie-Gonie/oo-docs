"""Core shared utilities used across the document model and renderers."""

from __future__ import annotations

from pathlib import Path


PathLike = str | Path
LengthUnit = str

UNIT_TO_INCHES = {
    "in": 1.0,
    "inch": 1.0,
    "inches": 1.0,
    "cm": 1.0 / 2.54,
    "centimeter": 1.0 / 2.54,
    "centimeters": 1.0 / 2.54,
    "mm": 1.0 / 25.4,
    "millimeter": 1.0 / 25.4,
    "millimeters": 1.0 / 25.4,
    "pt": 1.0 / 72.0,
    "point": 1.0 / 72.0,
    "points": 1.0 / 72.0,
    "pc": 1.0 / 6.0,
    "pica": 1.0 / 6.0,
    "picas": 1.0 / 6.0,
    "px": 1.0 / 96.0,
    "pixel": 1.0 / 96.0,
    "pixels": 1.0 / 96.0,
    "twip": 1.0 / 1440.0,
    "twips": 1.0 / 1440.0,
}

COUNTER_FORMATS = {
    "decimal",
    "lower-alpha",
    "upper-alpha",
    "lower-roman",
    "upper-roman",
    "bullet",
    "none",
}

TEXT_ALIGNMENTS = {"left", "center", "right", "justify"}
VERTICAL_ALIGNMENTS = {"top", "middle", "center", "bottom"}


class OODocsError(Exception):
    """Base exception for errors raised by OODocs.

    Args:
        *args: Exception message arguments forwarded to ``Exception``.
    """


def normalize_color(value: str | None) -> str | None:
    """Normalize a hex color string to six uppercase digits.

    Args:
        value: A color in ``RRGGBB`` or ``#RRGGBB`` form.

    Returns:
        The normalized uppercase ``RRGGBB`` string, or ``None`` when
        ``value`` is ``None``.

    Raises:
        ValueError: If the supplied value is not a six-digit hex color.
    """

    if value is None:
        return None

    normalized = value.strip().lstrip("#").upper()
    if len(normalized) != 6 or any(char not in "0123456789ABCDEF" for char in normalized):
        raise ValueError(f"Expected a 6-digit hex color, got: {value!r}")
    return normalized


def normalize_length_unit(value: str) -> str:
    """Validate and normalize a supported physical length unit.

    Args:
        value: Unit name or abbreviation to normalize.

    Returns:
        The lowercase normalized unit string.

    Raises:
        ValueError: If ``value`` is not a supported length unit.
    """

    normalized = value.strip().lower()
    if normalized not in UNIT_TO_INCHES:
        raise ValueError(f"Unsupported length unit: {value!r}")
    return normalized


def length_to_inches(value: float, unit: str) -> float:
    """Convert a numeric length to inches.

    Args:
        value: Length value in ``unit``.
        unit: Supported unit name or abbreviation.

    Returns:
        The equivalent length in inches.

    Raises:
        ValueError: If ``unit`` is not supported.
    """

    return float(value) * UNIT_TO_INCHES[normalize_length_unit(unit)]


def inches_to_length(value: float, unit: str) -> float:
    """Convert an inch length to the requested unit.

    Args:
        value: Length value in inches.
        unit: Supported unit name or abbreviation for the output.

    Returns:
        The equivalent length in ``unit``.

    Raises:
        ValueError: If ``unit`` is not supported.
    """

    return float(value) / UNIT_TO_INCHES[normalize_length_unit(unit)]


def normalize_counter_format(value: str) -> str:
    """Validate and normalize a supported counter format name.

    Args:
        value: Counter format name to normalize.

    Returns:
        The lowercase normalized counter format.

    Raises:
        ValueError: If ``value`` is not a supported counter format.
    """

    normalized = value.strip().lower()
    if normalized not in COUNTER_FORMATS:
        raise ValueError(f"Unsupported counter format: {value!r}")
    return normalized


def normalize_text_alignment(value: str) -> str:
    """Validate and normalize a supported horizontal text alignment.

    Args:
        value: Alignment name to normalize.

    Returns:
        The lowercase normalized alignment.

    Raises:
        ValueError: If ``value`` is not a supported horizontal alignment.
    """

    normalized = value.strip().lower()
    if normalized not in TEXT_ALIGNMENTS:
        raise ValueError(f"Unsupported text alignment: {value!r}")
    return normalized


def normalize_vertical_alignment(value: str) -> str:
    """Validate and normalize a supported vertical alignment.

    Args:
        value: Alignment name to normalize. ``"center"`` is accepted as an
            alias for ``"middle"``.

    Returns:
        The lowercase normalized alignment.

    Raises:
        ValueError: If ``value`` is not a supported vertical alignment.
    """

    normalized = value.strip().lower()
    if normalized not in VERTICAL_ALIGNMENTS:
        raise ValueError(f"Unsupported vertical alignment: {value!r}")
    return "middle" if normalized == "center" else normalized


def _alpha_counter(value: int) -> str:
    if value < 1:
        raise ValueError("Alphabetic counters require values >= 1")

    characters: list[str] = []
    number = value
    # Spreadsheet-style base-26 numbering has no zero digit, so each step
    # decrements before taking the modulus.
    while number > 0:
        number -= 1
        characters.append(chr(ord("a") + (number % 26)))
        number //= 26
    return "".join(reversed(characters))


def _roman_counter(value: int) -> str:
    if value < 1:
        raise ValueError("Roman numeral counters require values >= 1")

    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = value
    parts: list[str] = []
    for numeral_value, glyph in numerals:
        while remaining >= numeral_value:
            parts.append(glyph)
            remaining -= numeral_value
    return "".join(parts)


def format_counter_value(value: int, counter_format: str, *, bullet: str = "\u2022") -> str:
    """Format an integer using one of the supported numbering styles.

    Args:
        value: The counter value to format.
        counter_format: One of the supported values in ``COUNTER_FORMATS``.
        bullet: The glyph to use for ``"bullet"`` format.

    Returns:
        A display-ready string for the counter.

    Raises:
        ValueError: If ``counter_format`` is unsupported, or if an alphabetic
            or roman counter receives a value smaller than one.
    """

    normalized = normalize_counter_format(counter_format)
    if normalized == "decimal":
        return str(value)
    if normalized == "lower-alpha":
        return _alpha_counter(value)
    if normalized == "upper-alpha":
        return _alpha_counter(value).upper()
    if normalized == "lower-roman":
        return _roman_counter(value).lower()
    if normalized == "upper-roman":
        return _roman_counter(value)
    if normalized == "bullet":
        return bullet
    return ""
