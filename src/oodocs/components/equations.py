"""Helpers for lightweight LaTeX-style equation rendering."""

from __future__ import annotations

from dataclasses import dataclass


BASELINE = "baseline"
SUPERSCRIPT = "superscript"
SUBSCRIPT = "subscript"

VERTICAL_ALIGNMENTS = {BASELINE, SUPERSCRIPT, SUBSCRIPT}


LATEX_SYMBOLS = {
    ",": " ",
    ";": "  ",
    "!": "",
    "alpha": "alpha",
    "beta": "beta",
    "gamma": "gamma",
    "delta": "delta",
    "epsilon": "epsilon",
    "varepsilon": "epsilon",
    "zeta": "zeta",
    "eta": "eta",
    "theta": "theta",
    "vartheta": "theta",
    "iota": "iota",
    "kappa": "kappa",
    "lambda": "lambda",
    "mu": "mu",
    "nu": "nu",
    "xi": "xi",
    "pi": "pi",
    "varpi": "pi",
    "rho": "rho",
    "varrho": "rho",
    "sigma": "sigma",
    "varsigma": "sigma",
    "tau": "tau",
    "upsilon": "upsilon",
    "phi": "phi",
    "varphi": "phi",
    "chi": "chi",
    "psi": "psi",
    "omega": "omega",
    "Gamma": "Gamma",
    "Delta": "Delta",
    "Theta": "Theta",
    "Lambda": "Lambda",
    "Xi": "Xi",
    "Pi": "Pi",
    "Sigma": "Sigma",
    "Upsilon": "Upsilon",
    "Phi": "Phi",
    "Psi": "Psi",
    "Omega": "Omega",
    "cdot": "*",
    "times": "x",
    "pm": "+/-",
    "mp": "-/+",
    "neq": "!=",
    "ne": "!=",
    "leq": "<=",
    "geq": ">=",
    "approx": "~=",
    "sim": "~",
    "equiv": "==",
    "propto": "prop to",
    "infty": "inf",
    "partial": "d",
    "nabla": "nabla",
    "sum": "sum",
    "prod": "prod",
    "int": "int",
    "oint": "oint",
    "forall": "forall",
    "exists": "exists",
    "in": "in",
    "notin": "notin",
    "subset": "subset",
    "subseteq": "subseteq",
    "supset": "supset",
    "supseteq": "supseteq",
    "cup": "union",
    "cap": "intersect",
    "vee": "or",
    "wedge": "and",
    "to": "->",
    "rightarrow": "->",
    "leftarrow": "<-",
    "leftrightarrow": "<->",
    "Rightarrow": "=>",
    "Leftarrow": "<=",
    "Leftrightarrow": "<=>",
    "ldots": "...",
    "cdots": "...",
    "dots": "...",
    "mid": "|",
    "vert": "|",
    "Vert": "||",
    "degree": "deg",
}

GROUP_COMMANDS = {"text", "mathrm", "mathit", "mathbf", "operatorname", "operatorname*"}
DELIMITER_COMMANDS = {"left", "right"}


@dataclass(slots=True)
class EquationSegment:
    """Text fragment plus a vertical alignment hint.

    Attributes:
        text: Text rendered for this segment.
        vertical_align: One of ``BASELINE``, ``SUPERSCRIPT``, or ``SUBSCRIPT``.

    Raises:
        ValueError: If ``vertical_align`` is unsupported.

    Examples:
        ```python
        segment = EquationSegment("2", vertical_align=SUPERSCRIPT)
        ```
    """

    text: str
    vertical_align: str = BASELINE

    def __post_init__(self) -> None:
        if self.vertical_align not in VERTICAL_ALIGNMENTS:
            raise ValueError(f"Unsupported vertical alignment: {self.vertical_align!r}")


def parse_latex_segments(source: str) -> list[EquationSegment]:
    """Parse a lightweight LaTeX-like expression into styled text segments.

    Args:
        source: LaTeX-like source text.

    Returns:
        Adjacent text segments merged by vertical alignment.

    Examples:
        ```python
        segments = parse_latex_segments(r"x^2 + y_1")
        ```
    """

    parser = _EquationParser(source)
    return _merge_adjacent(parser.parse())


def equation_plain_text(source: str) -> str:
    """Return a readable plain-text form of a LaTeX-like expression.

    Args:
        source: LaTeX-like source text.

    Returns:
        Plain-text approximation of the expression.

    Examples:
        ```python
        equation_plain_text(r"\frac{a}{b}")
        # "(a)/(b)"
        ```
    """

    return "".join(segment.text for segment in parse_latex_segments(source))


class _EquationParser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.position = 0

    def parse(self, stop_char: str | None = None) -> list[EquationSegment]:
        segments: list[EquationSegment] = []
        while self.position < len(self.source):
            char = self.source[self.position]
            if stop_char is not None and char == stop_char:
                self.position += 1
                break
            if char == "{":
                self.position += 1
                segments.extend(self.parse(stop_char="}"))
                continue
            if char == "}":
                self.position += 1
                continue
            if char == "\\":
                segments.extend(self._parse_command())
                continue
            if char in "^_":
                self.position += 1
                aligned = SUPERSCRIPT if char == "^" else SUBSCRIPT
                # Superscript and subscript bind to the next token only,
                # mirroring TeX's behavior for grouped or single-character
                # tokens.
                segments.extend(_apply_vertical_alignment(self._read_token(), aligned))
                continue
            segments.append(EquationSegment(char))
            self.position += 1
        return segments

    def _parse_command(self) -> list[EquationSegment]:
        self.position += 1
        if self.position >= len(self.source):
            return [EquationSegment("\\")]

        start = self.position
        if self.source[self.position].isalpha():
            while self.position < len(self.source) and self.source[self.position].isalpha():
                self.position += 1
            command = self.source[start:self.position]
        else:
            command = self.source[self.position]
            self.position += 1

        if command in DELIMITER_COMMANDS:
            return self._parse_delimiter()
        if command in GROUP_COMMANDS:
            return self._read_token()
        if command in {"frac", "dfrac", "tfrac"}:
            numerator = self._read_token()
            denominator = self._read_token()
            # Render fractions as a readable inline ratio because downstream
            # renderers consume text segments rather than full math layout.
            return (
                [EquationSegment("(")]
                + numerator
                + [EquationSegment(")/(")]
                + denominator
                + [EquationSegment(")")]
            )
        if command == "prescript":
            superscript = _apply_vertical_alignment(self._read_token(), SUPERSCRIPT)
            subscript = _apply_vertical_alignment(self._read_token(), SUBSCRIPT)
            return superscript + subscript + self._read_token()
        if command == "sqrt":
            return [EquationSegment("sqrt(")] + self._read_token() + [EquationSegment(")")]
        if command == "overline":
            return self._read_token()
        if command in {"quad", "qquad"}:
            return [EquationSegment("  " if command == "quad" else "    ")]
        if command == "\\":
            return [EquationSegment("\n")]
        if command in LATEX_SYMBOLS:
            return [EquationSegment(LATEX_SYMBOLS[command])]
        return [EquationSegment(f"\\{command}")]

    def _parse_delimiter(self) -> list[EquationSegment]:
        if self.position >= len(self.source):
            return []
        delimiter = self.source[self.position]
        self.position += 1
        if delimiter == ".":
            return []
        if delimiter == "\\":
            return self._parse_command()
        return [EquationSegment(delimiter)]

    def _read_token(self) -> list[EquationSegment]:
        if self.position >= len(self.source):
            return []
        if self.source[self.position] == "{":
            self.position += 1
            return self.parse(stop_char="}")
        if self.source[self.position] == "\\":
            return self._parse_command()
        token = [EquationSegment(self.source[self.position])]
        self.position += 1
        return token


def _apply_vertical_alignment(
    segments: list[EquationSegment],
    vertical_align: str,
) -> list[EquationSegment]:
    return [
        EquationSegment(segment.text, vertical_align=vertical_align)
        for segment in segments
        if segment.text
    ]


def _merge_adjacent(segments: list[EquationSegment]) -> list[EquationSegment]:
    merged: list[EquationSegment] = []
    for segment in segments:
        if not segment.text:
            continue
        if merged and merged[-1].vertical_align == segment.vertical_align:
            merged[-1] = EquationSegment(
                merged[-1].text + segment.text,
                vertical_align=segment.vertical_align,
            )
            continue
        merged.append(segment)
    return merged


__all__ = [
    "BASELINE",
    "DELIMITER_COMMANDS",
    "EquationSegment",
    "GROUP_COMMANDS",
    "LATEX_SYMBOLS",
    "SUBSCRIPT",
    "SUPERSCRIPT",
    "VERTICAL_ALIGNMENTS",
    "equation_plain_text",
    "parse_latex_segments",
]
