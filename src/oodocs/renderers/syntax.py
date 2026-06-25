"""Shared syntax highlighting helpers for renderer-specific code output."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from functools import lru_cache

from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound


@dataclass(frozen=True, slots=True)
class SyntaxToken:
    """Syntax-highlighted text segment.

    Attributes:
        text: Source text for this token.
        color: Optional hex color without a leading ``#``.
        bold: Whether the token should render in bold.
        italic: Whether the token should render in italics.
    """

    text: str
    color: str | None = None
    bold: bool = False
    italic: bool = False


@lru_cache(maxsize=1)
def _pygments_style() -> object:
    return get_style_by_name("friendly")


def _lexer(language: str | None) -> object:
    if not language:
        return TextLexer()
    try:
        return get_lexer_by_name(language.strip())
    except ClassNotFound:
        return TextLexer()


def _style_for_token(style: object, token_type: object) -> dict[str, object]:
    current = token_type
    while current is not None:
        try:
            return style.style_for_token(current)  # type: ignore[attr-defined]
        except KeyError:
            current = getattr(current, "parent", None)
    return {}


def syntax_tokens(source: str, language: str | None = None) -> list[SyntaxToken]:
    """Return Pygments-highlighted tokens for a code block.

    Args:
        source: Code text to tokenize.
        language: Optional Pygments lexer name. Unknown languages fall back to
            plain text.

    Returns:
        Ordered syntax tokens preserving the source text.
    """

    style = _pygments_style()
    tokens: list[SyntaxToken] = []
    for token_type, text in lex(source, _lexer(language)):
        if not text:
            continue
        # Pygments token styles inherit from parent token classes, so climb the
        # token hierarchy until a style entry exists.
        token_style = _style_for_token(style, token_type)
        tokens.append(
            SyntaxToken(
                text=text,
                color=token_style.get("color") or None,
                bold=bool(token_style.get("bold")),
                italic=bool(token_style.get("italic")),
            )
        )
    return tokens


def syntax_html(source: str, language: str | None = None) -> str:
    """Return inline HTML spans for highlighted code inside a ``pre`` block.

    Args:
        source: Code text to highlight.
        language: Optional Pygments lexer name. Unknown languages fall back to
            plain text.

    Returns:
        Escaped HTML containing optional inline span styles for highlighted
        tokens.
    """

    pieces: list[str] = []
    for token in syntax_tokens(source, language):
        text = escape(token.text)
        styles: list[str] = []
        if token.color is not None:
            styles.append(f"color: #{token.color}")
        if token.bold:
            styles.append("font-weight: 700")
        if token.italic:
            styles.append("font-style: italic")
        if not styles:
            pieces.append(text)
            continue
        pieces.append(
            f'<span class="oodocs-code-token" style="{"; ".join(styles)}">{text}</span>'
        )
    return "".join(pieces)


def syntax_pdf_markup(source: str, language: str | None = None) -> str:
    """Return ReportLab paragraph markup for highlighted code.

    Args:
        source: Code text to highlight.
        language: Optional Pygments lexer name. Unknown languages fall back to
            plain text.

    Returns:
        Escaped ReportLab paragraph markup with font, bold, and italic tags.
    """

    pieces: list[str] = []
    for token in syntax_tokens(source, language):
        text = escape(token.text)
        if token.color is not None:
            text = f'<font color="#{token.color}">{text}</font>'
        if token.bold:
            text = f"<b>{text}</b>"
        if token.italic:
            text = f"<i>{text}</i>"
        pieces.append(text)
    return "".join(pieces)


__all__ = ["SyntaxToken", "syntax_html", "syntax_pdf_markup", "syntax_tokens"]
