"""Shared output-format compatibility helpers.

Attributes:
    OutputFormat: Type alias for supported renderer output format names.
    OUTPUT_FORMATS: Ordered tuple of supported output format names.
    OUTPUT_FORMAT_LABELS: Human-readable labels for each output format.
    COMPATIBILITY_NOTES: Registry of known cross-renderer compatibility notes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal


OutputFormat = Literal["docx", "pdf", "html"]
OUTPUT_FORMATS: tuple[OutputFormat, ...] = ("docx", "pdf", "html")
OUTPUT_FORMAT_LABELS: dict[OutputFormat, str] = {
    "docx": "Word",
    "pdf": "PDF",
    "html": "HTML",
}


@dataclass(frozen=True, slots=True)
class CompatibilityNote:
    """Renderer compatibility note surfaced by document validation.

    Attributes:
        code: Stable validation code.
        message: User-facing compatibility message.
        formats: Output formats affected by the note.

    Examples:
        ```python
        note = compatibility_note("html-toc-page-numbers")
        print(note.formats)
        ```
    """

    code: str
    message: str
    formats: tuple[OutputFormat, ...]


COMPATIBILITY_NOTES: dict[str, CompatibilityNote] = {
    "html-toc-page-numbers": CompatibilityNote(
        code="html-toc-page-numbers",
        message=(
            "HTML output does not have stable rendered page numbers, "
            "so the TOC is link-only there."
        ),
        formats=("html",),
    ),
    "html-table-list-page-numbers": CompatibilityNote(
        code="html-table-list-page-numbers",
        message=(
            "HTML output does not have stable rendered page numbers, "
            "so the list of tables is link-only there."
        ),
        formats=("html",),
    ),
    "html-figure-list-page-numbers": CompatibilityNote(
        code="html-figure-list-page-numbers",
        message=(
            "HTML output does not have stable rendered page numbers, "
            "so the list of figures is link-only there."
        ),
        formats=("html",),
    ),
    "html-algorithm-list-page-numbers": CompatibilityNote(
        code="html-algorithm-list-page-numbers",
        message=(
            "HTML output does not have stable rendered page numbers, "
            "so the list of algorithms is link-only there."
        ),
        formats=("html",),
    ),
    "box-shadow-html-only": CompatibilityNote(
        code="box-shadow-html-only",
        message=(
            "Box shadows render in HTML output only; DOCX and PDF keep the "
            "box content and omit the shadow."
        ),
        formats=("docx", "pdf"),
    ),
    "page-item-scope-static-output": CompatibilityNote(
        code="page-item-scope-static-output",
        message=(
            "Scoped page items are exact in PDF; DOCX applies them at section "
            "header level and HTML applies them to the static page frame."
        ),
        formats=("docx", "html"),
    ),
    "section-page-layout-html-degrade": CompatibilityNote(
        code="section-page-layout-html-degrade",
        message=(
            "Section page_layout uses actual page sections in DOCX/PDF; HTML "
            "uses a page-break region and scoped CSS variables as a print "
            "fallback because browsers do not consistently enforce mixed page "
            "sizes in one document."
        ),
        formats=("html",),
    ),
    "docx-footnote-stream-generated-list": CompatibilityNote(
        code="docx-footnote-stream-generated-list",
        message=(
            "DOCX native page footnotes support only the default plain decimal "
            "stream; custom footnote streams or symbol markers render through "
            "the generated footnote list."
        ),
        formats=("docx",),
    ),
    "margin-note-renderer-fallback": CompatibilityNote(
        code="margin-note-renderer-fallback",
        message=(
            "MarginNote renders as an HTML side note; DOCX and PDF keep the "
            "note through comment-style fallback output."
        ),
        formats=("docx", "pdf"),
    ),
}


def compatibility_note(code: str) -> CompatibilityNote:
    """Return a named compatibility note.

    Args:
        code: Compatibility note code.

    Returns:
        The matching compatibility note.

    Raises:
        KeyError: If ``code`` is unknown.

    Examples:
        ```python
        note = compatibility_note("html-toc-page-numbers")
        assert note.formats == ("html",)
        ```
    """

    try:
        return COMPATIBILITY_NOTES[code]
    except KeyError as exc:
        raise KeyError(f"Unknown compatibility note: {code}") from exc


def normalize_output_format(value: str) -> OutputFormat:
    """Normalize a renderer/output format name.

    Args:
        value: Format name or extension, such as ``"pdf"`` or ``".html"``.

    Returns:
        Normalized output format.

    Raises:
        ValueError: If ``value`` is not a supported output format.

    Examples:
        ```python
        normalize_output_format(".htm")
        # "html"
        ```
    """

    normalized = value.lower().strip().removeprefix(".")
    if normalized == "htm":
        normalized = "html"
    if normalized not in OUTPUT_FORMATS:
        raise ValueError(
            "Unsupported document output format. Use one of: .docx, .pdf, .html "
            "(or docx, pdf, html in save_all)."
        )
    return normalized  # type: ignore[return-value]


def normalize_output_formats(
    values: Iterable[str] | None = None,
) -> tuple[OutputFormat, ...]:
    """Normalize output formats while preserving caller order.

    Args:
        values: Format names or extensions. Defaults to every supported format.

    Returns:
        Unique normalized output formats in first-seen order.

    Raises:
        ValueError: If any value is not a supported output format.

    Examples:
        ```python
        normalize_output_formats([".pdf", "html", "pdf"])
        # ("pdf", "html")
        ```
    """

    if values is None:
        return OUTPUT_FORMATS

    normalized: list[OutputFormat] = []
    seen: set[OutputFormat] = set()
    for value in values:
        output_format = normalize_output_format(value)
        if output_format in seen:
            continue
        normalized.append(output_format)
        seen.add(output_format)
    return tuple(normalized)


def format_output_formats(formats: Iterable[OutputFormat]) -> str:
    """Return a compact display label for output formats.

    Args:
        formats: Output formats to display.

    Returns:
        ``"All"``, ``"None"``, or a slash-separated list of format labels.

    Examples:
        ```python
        format_output_formats(("pdf", "html"))
        # "PDF/HTML"
        ```
    """

    normalized = normalize_output_formats(formats)
    if not normalized:
        return "None"
    if set(normalized) == set(OUTPUT_FORMATS):
        return "All"
    return "/".join(OUTPUT_FORMAT_LABELS[output_format] for output_format in normalized)


__all__ = [
    "COMPATIBILITY_NOTES",
    "OUTPUT_FORMATS",
    "OUTPUT_FORMAT_LABELS",
    "CompatibilityNote",
    "OutputFormat",
    "compatibility_note",
    "format_output_formats",
    "normalize_output_format",
    "normalize_output_formats",
]
