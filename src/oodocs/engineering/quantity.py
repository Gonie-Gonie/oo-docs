"""Renderer-neutral numeric and unit presentation objects.

This module formats values for documents.  It deliberately does not convert
units, validate dimensions, or implement an expression language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import re
from typing import TypeAlias

from oodocs.components.inline import Text
from oodocs.styles import TextStyle


NumberValue: TypeAlias = int | float | Decimal | str

_SUPERSCRIPT_DIGITS = str.maketrans(
    "0123456789+-",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻",
)
_SUBSCRIPT_DIGITS = str.maketrans(
    "0123456789+-",
    "₀₁₂₃₄₅₆₇₈₉₊₋",
)
_SUPERSCRIPT_REVERSE = {
    character: source
    for source, character in zip("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", strict=True)
}
_SUBSCRIPT_REVERSE = {
    character: source
    for source, character in zip("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋", strict=True)
}
_SUPERSCRIPT_PATTERN = re.compile("[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+")
_SUBSCRIPT_PATTERN = re.compile("[₀₁₂₃₄₅₆₇₈₉₊₋]+")
_SCRIPT_SOURCE_PATTERN = re.compile(
    r"\s*(?P<marker>[\^_])\s*\{?\s*(?P<digits>[+\-]?\d+)\s*\}?"
)


@dataclass(frozen=True, slots=True)
class NumberFormat:
    """Presentation policy for a numeric value.

    ``decimals`` and ``significant_digits`` are mutually exclusive because
    they describe different rounding contracts.  The policy is ignored when a
    :class:`Quantity` value is already a string.
    """

    decimals: int | None = None
    significant_digits: int | None = None
    thousands_separator: bool = False
    scientific: bool = False
    trim_trailing_zeros: bool = False

    def __post_init__(self) -> None:
        if self.decimals is not None and self.decimals < 0:
            raise ValueError("NumberFormat.decimals must be >= 0")
        if self.significant_digits is not None and self.significant_digits < 1:
            raise ValueError("NumberFormat.significant_digits must be >= 1")
        if self.decimals is not None and self.significant_digits is not None:
            raise ValueError(
                "NumberFormat.decimals and significant_digits are mutually exclusive"
            )

    def format(self, value: NumberValue) -> str:
        """Return ``value`` formatted for display without changing its meaning."""

        if isinstance(value, str):
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise TypeError("NumberFormat values must be int, float, Decimal, or str")

        if self.scientific:
            if self.significant_digits is not None:
                precision = self.significant_digits - 1
            elif self.decimals is not None:
                precision = self.decimals
            else:
                precision = 6
            rendered = format(value, f".{precision}e")
        elif self.significant_digits is not None:
            grouping = "," if self.thousands_separator else ""
            rendered = format(value, f"{grouping}.{self.significant_digits}g")
        elif self.decimals is not None:
            grouping = "," if self.thousands_separator else ""
            rendered = format(value, f"{grouping}.{self.decimals}f")
        elif self.thousands_separator:
            rendered = format(value, ",")
        else:
            rendered = str(value)

        return _trim_numeric_zeros(rendered) if self.trim_trailing_zeros else rendered


@dataclass(slots=True)
class Quantity(Text):
    """A number and optional unit rendered as an ordinary inline fragment.

    The original ``value`` remains available to callers.  Rendering is derived
    by :meth:`plain_text`; no conversion or dimensional analysis is performed.

    Args:
        value: Numeric value or an already-formatted string.
        unit: Optional display-only unit. ``^``/``_`` integer scripts and
            ``degC``/``degF`` degree aliases are normalized for presentation.
        number_format: Optional numeric presentation policy.
        uncertainty: Optional value displayed after a plus/minus sign.
        style: Optional inline text style.
    """

    value: NumberValue
    style: TextStyle = field(default_factory=TextStyle, kw_only=True)
    unit: str | None = None
    number_format: NumberFormat | None = None
    uncertainty: NumberValue | None = None

    def __post_init__(self) -> None:
        _validate_number_value(self.value, name="value")
        if self.uncertainty is not None:
            _validate_number_value(self.uncertainty, name="uncertainty")
        if self.number_format is not None and not isinstance(self.number_format, NumberFormat):
            raise TypeError("Quantity.number_format must be a NumberFormat or None")
        if not isinstance(self.style, TextStyle):
            raise TypeError("Quantity.style must be a TextStyle")
        if self.unit is not None:
            if not isinstance(self.unit, str):
                raise TypeError("Quantity.unit must be a string or None")
            normalized_unit = self.unit.strip()
            self.unit = normalized_unit or None

    def plain_text(self) -> str:
        """Return the formatted value, uncertainty, and unit as readable text."""

        rendered = self._format_value(self.value)
        if self.uncertainty is not None:
            rendered += f" ± {self._format_value(self.uncertainty)}"
        if self.unit is not None:
            rendered += f" {_normalize_unit_text(self.unit)}"
        return rendered

    def screen_reader_text(self) -> str:
        """Return an expanded text label suitable for HTML assistive tools."""

        text = self.plain_text().replace("±", " plus or minus ")
        text = text.replace("°C", " degrees Celsius")
        text = text.replace("°F", " degrees Fahrenheit")
        text = text.replace("°", " degrees")
        text = text.replace("·", " times ").replace("/", " per ")
        text = _SUPERSCRIPT_PATTERN.sub(_speak_superscript, text)
        text = _SUBSCRIPT_PATTERN.sub(_speak_subscript, text)
        return " ".join(text.split())

    def _format_value(self, value: NumberValue) -> str:
        if isinstance(value, str):
            return value
        if self.number_format is None:
            return str(value)
        return self.number_format.format(value)


def _validate_number_value(value: object, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise TypeError(f"Quantity.{name} must be int, float, Decimal, or str")


def _trim_numeric_zeros(rendered: str) -> str:
    exponent_marker = "e" if "e" in rendered else "E" if "E" in rendered else None
    if exponent_marker is None:
        mantissa, exponent = rendered, ""
    else:
        mantissa, exponent_value = rendered.split(exponent_marker, 1)
        exponent = exponent_marker + exponent_value
    if "." in mantissa:
        mantissa = mantissa.rstrip("0").rstrip(".")
    return mantissa + exponent


def _normalize_unit_text(unit: str) -> str:
    normalized = unit.replace("**", "^")
    degree_aliases = (
        (r"\b(?:degrees?|deg)[\s_]*c(?:elsius)?\b", "°C"),
        (r"\b(?:degrees?|deg)[\s_]*f(?:ahrenheit)?\b", "°F"),
        (r"\b(?:degrees?|deg)\b", "°"),
    )
    for pattern, replacement in degree_aliases:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    def replace_script(match: re.Match[str]) -> str:
        digits = match.group("digits")
        translation = _SUPERSCRIPT_DIGITS if match.group("marker") == "^" else _SUBSCRIPT_DIGITS
        return digits.translate(translation)

    return _SCRIPT_SOURCE_PATTERN.sub(replace_script, normalized)


def _speak_superscript(match: re.Match[str]) -> str:
    exponent = "".join(_SUPERSCRIPT_REVERSE[character] for character in match.group())
    if exponent == "2":
        return " squared"
    if exponent == "3":
        return " cubed"
    return f" to the power of {exponent}"


def _speak_subscript(match: re.Match[str]) -> str:
    subscript = "".join(_SUBSCRIPT_REVERSE[character] for character in match.group())
    return f" subscript {subscript}"


__all__ = ["NumberFormat", "Quantity"]
