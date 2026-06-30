"""Chemistry authoring helpers for formulas and reactions.

Attributes:
    ChemicalFormula: Inline chemical formula rendered with numeric
        subscripts.
    chemical_formula: Helper for creating inline chemical formulas.
    chemical_formula_math_source: Convert chemical formula notation to the
        lightweight math source used by renderers.
    chemical_formula_plain_text: Return a readable plain-text chemical formula.
"""

from __future__ import annotations

from oodocs.components.inline import Math
from oodocs.styles import TextStyle


SUBSCRIPT_DIGITS = {
    "\u2080": "0",
    "\u2081": "1",
    "\u2082": "2",
    "\u2083": "3",
    "\u2084": "4",
    "\u2085": "5",
    "\u2086": "6",
    "\u2087": "7",
    "\u2088": "8",
    "\u2089": "9",
}
SUPERSCRIPT_CHARS = {
    "\u2070": "0",
    "\u00b9": "1",
    "\u00b2": "2",
    "\u00b3": "3",
    "\u2074": "4",
    "\u2075": "5",
    "\u2076": "6",
    "\u2077": "7",
    "\u2078": "8",
    "\u2079": "9",
    "\u207a": "+",
    "\u207b": "-",
}
CHARGE_SIGNS = {"+", "-"}


class ChemicalFormula(Math):
    """Inline chemical formula with renderer-neutral subscripts.

    Args:
        source: Chemical formula source such as ``"H2O"``, ``"Ca(OH)2"``, or
            ``"SO4^2-"``. A surrounding ``\\ce{...}`` wrapper is accepted.
        style: Optional inline style.

    Examples:
        ```python
        from oodocs import Document, Paragraph
        from oodocs.chemistry import ChemicalFormula

        paragraph = Paragraph("Water is ", ChemicalFormula("H2O"), ".")
        document = Document("Chemistry Note", paragraph)
        ```
    """

    __slots__ = ("source",)

    source: str

    def __init__(self, source: str, style: TextStyle | None = None) -> None:
        self.source = _normalize_chemical_source(source)
        super().__init__(chemical_formula_math_source(self.source), style=style)

    def plain_text(self) -> str:
        """Return the formula as readable plain text.

        Returns:
            Plain-text formula with Unicode subscript and superscript characters
            normalized to ordinary digits and signs.
        """

        return chemical_formula_plain_text(self.source)

    @classmethod
    def inline(
        cls,
        source: str,
        *,
        style: TextStyle | None = None,
    ) -> ChemicalFormula:
        """Create an inline chemical formula.

        Args:
            source: Chemical formula source.
            style: Optional inline style.

        Returns:
            Inline chemical formula fragment.
        """

        return cls(source, style=style)


def chemical_formula(
    source: str,
    *,
    style: TextStyle | None = None,
) -> ChemicalFormula:
    """Create an inline chemical formula fragment.

    Args:
        source: Chemical formula source.
        style: Optional inline style.

    Returns:
        Inline chemical formula fragment.

    Examples:
        ```python
        from oodocs.chemistry import chemical_formula

        fragment = chemical_formula("CO2")
        ```
    """

    return ChemicalFormula.inline(source, style=style)


def chemical_formula_math_source(source: str) -> str:
    """Convert chemical formula notation into lightweight math source.

    Numeric suffixes after element symbols or grouped formulas become
    subscripts. Explicit charge notation such as ``^2-`` or a trailing ``+`` or
    ``-`` becomes superscript text. Stoichiometric coefficients at token starts
    remain baseline text.

    Args:
        source: Chemical formula or reaction source.

    Returns:
        Lightweight math source consumed by the existing math renderers.
    """

    normalized = _normalize_chemical_source(source)
    result: list[str] = []
    index = 0
    can_take_suffix = False
    while index < len(normalized):
        char = normalized[index]
        if char in SUBSCRIPT_DIGITS:
            result.append(f"_{SUBSCRIPT_DIGITS[char]}")
            can_take_suffix = True
            index += 1
            continue
        if char in SUPERSCRIPT_CHARS:
            token, index = _consume_unicode_superscript(normalized, index)
            result.append(f"^{{{token}}}")
            can_take_suffix = True
            continue
        if char == "^":
            token, index = _consume_charge_token(normalized, index + 1)
            if token:
                result.append(f"^{{{token}}}")
                can_take_suffix = True
                continue
            result.append(char)
            can_take_suffix = False
            continue
        if char.isdigit():
            token, index = _consume_digits(normalized, index)
            result.append(f"_{{{token}}}" if can_take_suffix else token)
            can_take_suffix = can_take_suffix or bool(token)
            continue
        if char in CHARGE_SIGNS and can_take_suffix and _is_trailing_charge(normalized, index):
            result.append(f"^{{{char}}}")
            index += 1
            can_take_suffix = True
            continue
        result.append(char)
        can_take_suffix = _can_precede_formula_suffix(char)
        index += 1
    return "".join(result)


def chemical_formula_plain_text(source: str) -> str:
    """Return a readable plain-text formula.

    Args:
        source: Chemical formula or reaction source.

    Returns:
        Formula with ``\\ce{...}`` wrappers and Unicode subscript/superscript
        digits normalized to ASCII characters.
    """

    normalized = _normalize_chemical_source(source)
    result: list[str] = []
    index = 0
    while index < len(normalized):
        char = normalized[index]
        if char in SUBSCRIPT_DIGITS:
            result.append(SUBSCRIPT_DIGITS[char])
        elif char in SUPERSCRIPT_CHARS:
            result.append(SUPERSCRIPT_CHARS[char])
        elif char == "^":
            token, index = _consume_charge_token(normalized, index + 1)
            result.append(token)
            continue
        else:
            result.append(char)
        index += 1
    return "".join(result)


def _normalize_chemical_source(source: str) -> str:
    normalized = str(source).strip()
    if normalized.startswith(r"\ce{") and normalized.endswith("}"):
        normalized = normalized[4:-1].strip()
    if not normalized:
        raise ValueError("chemical formula source must not be empty")
    return normalized


def _consume_digits(source: str, index: int) -> tuple[str, int]:
    start = index
    while index < len(source) and source[index].isdigit():
        index += 1
    return source[start:index], index


def _consume_unicode_superscript(source: str, index: int) -> tuple[str, int]:
    result: list[str] = []
    while index < len(source) and source[index] in SUPERSCRIPT_CHARS:
        result.append(SUPERSCRIPT_CHARS[source[index]])
        index += 1
    return "".join(result), index


def _consume_charge_token(source: str, index: int) -> tuple[str, int]:
    if index >= len(source):
        return "", index
    if source[index] == "{":
        end = source.find("}", index + 1)
        if end == -1:
            return "", index
        return source[index + 1 : end], end + 1
    start = index
    while index < len(source) and (source[index].isdigit() or source[index] in CHARGE_SIGNS):
        index += 1
    return source[start:index], index


def _is_trailing_charge(source: str, index: int) -> bool:
    next_index = index + 1
    return next_index >= len(source) or source[next_index].isspace() or source[next_index] in ",;.)]"


def _can_precede_formula_suffix(char: str) -> bool:
    if char.isalpha():
        return True
    return char in ")]}"


__all__ = [
    "ChemicalFormula",
    "chemical_formula",
    "chemical_formula_math_source",
    "chemical_formula_plain_text",
]
