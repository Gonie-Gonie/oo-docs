"""Shared output-format compatibility helpers."""

from __future__ import annotations

from typing import Iterable, Literal


OutputFormat = Literal["docx", "pdf", "html"]
OUTPUT_FORMATS: tuple[OutputFormat, ...] = ("docx", "pdf", "html")
OUTPUT_FORMAT_LABELS: dict[OutputFormat, str] = {
    "docx": "Word",
    "pdf": "PDF",
    "html": "HTML",
}


def normalize_output_format(value: str) -> OutputFormat:
    """Normalize a renderer/output format name."""

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
    """Normalize a sequence of output formats while preserving order."""

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
    """Return a compact display label for output formats."""

    normalized = normalize_output_formats(formats)
    if not normalized:
        return "None"
    if set(normalized) == set(OUTPUT_FORMATS):
        return "All"
    return "/".join(OUTPUT_FORMAT_LABELS[output_format] for output_format in normalized)


__all__ = [
    "OUTPUT_FORMATS",
    "OUTPUT_FORMAT_LABELS",
    "OutputFormat",
    "format_output_formats",
    "normalize_output_format",
    "normalize_output_formats",
]
