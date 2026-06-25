"""Docstring parsers for normalized API documentation metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import re
from typing import Callable

from oodocs.apidoc.model import (
    ApiDocIssue,
    ApiDocstringStyleName,
    ApiExample,
    ApiParameter,
    ApiRaises,
    ApiRendererNote,
    ApiReturn,
    ApiSeeAlso,
)
from oodocs.apidoc.examples import extract_code_blocks_from_docstring


DocstringParser = Callable[[str, str | None, str | None], "ParsedDocstring"]


@dataclass(slots=True)
class ParsedDocstring:
    """Normalized docstring parse result.

    Attributes:
        summary: First sentence or short paragraph.
        description: Longer prose after the summary.
        parameters: Parsed parameter documentation.
        returns: Parsed return/yield documentation.
        raises: Parsed exception documentation.
        examples: Parsed code examples.
        see_also: Related API references.
        renderer_notes: Renderer-specific behavior notes.
        notes: Additional notes.
        warnings: Warning notes.
        style: Parser style that produced the result.
        issues: Parser diagnostics.
        deprecated: Whether the docstring marks the object as deprecated.
        deprecation_message: Optional deprecation guidance.

    Examples:
        Parse one docstring and use the result to populate an API object:

        ```python
        from oodocs.apidoc.docstring import parse_docstring

        parsed = parse_docstring("Summary.\\n\\nArgs:\\n    path: Output path.")
        assert parsed.parameters[0].name == "path"
        ```
    """

    summary: str | None = None
    description: str | None = None
    parameters: list[ApiParameter] = field(default_factory=list)
    returns: ApiReturn | None = None
    raises: list[ApiRaises] = field(default_factory=list)
    examples: list[ApiExample] = field(default_factory=list)
    see_also: list[ApiSeeAlso] = field(default_factory=list)
    renderer_notes: list[ApiRendererNote] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    style: ApiDocstringStyleName = "plain"
    issues: list[ApiDocIssue] = field(default_factory=list)
    deprecated: bool = False
    deprecation_message: str | None = None


_PARSERS: dict[str, DocstringParser] = {}
_GOOGLE_SECTION_NAMES = {
    "args",
    "arguments",
    "parameters",
    "returns",
    "yields",
    "raises",
    "examples",
    "example",
    "see also",
    "notes",
    "warnings",
    "renderer notes",
    "deprecated",
}


def parse_docstring(
    text: str | None,
    style: ApiDocstringStyleName = "auto",
    *,
    qualname: str | None = None,
    module: str | None = None,
) -> ParsedDocstring:
    """Parse a docstring into normalized API metadata.

    Args:
        text: Raw docstring text.
        style: Parser style or ``"auto"``.
        qualname: Optional API object qualname used in diagnostics.
        module: Optional module name used in diagnostics.

    Returns:
        Parsed docstring object.

    Raises:
        ValueError: If an unsupported explicit style is requested.

    Examples:
        ```python
        parsed = parse_docstring(
            \"\"\"Load a file.

            Args:
                path: File path.

            Returns:
                Loaded content.
            \"\"\",
            style="google",
        )
        assert parsed.returns.documented
        ```
    """

    cleaned = inspect.cleandoc(text or "")
    requested = style
    detected = detect_docstring_style(cleaned) if requested == "auto" else requested
    parser = _PARSERS.get(detected)
    if parser is None:
        raise ValueError(f"Unsupported docstring style: {style!r}")
    parsed = parser(cleaned, qualname, module)
    if requested != "auto":
        auto_style = detect_docstring_style(cleaned)
        if cleaned and auto_style != requested:
            parsed.issues.append(
                ApiDocIssue(
                    "warning",
                    "docstring-style-mismatch",
                    f"Requested {requested!r} but docstring looks like {auto_style!r}.",
                    qualname=qualname,
                    module=module,
                )
            )
    return parsed


def register_docstring_parser(name: str, parser: DocstringParser) -> None:
    """Register a custom docstring parser.

    Args:
        name: Style name.
        parser: Parser callable.

    Raises:
        ValueError: If the style name is empty or already registered.

    Examples:
        ```python
        from oodocs.apidoc.docstring import register_docstring_parser

        def parse_custom(text, qualname, module):
            return parse_docstring(text, style="plain")

        register_docstring_parser("custom", parse_custom)
        ```
    """

    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("docstring parser name must not be empty")
    if normalized in _PARSERS:
        raise ValueError(f"Docstring parser already registered: {name!r}")
    _PARSERS[normalized] = parser


def detect_docstring_style(text: str | None) -> ApiDocstringStyleName:
    """Detect the most likely docstring style.

    Args:
        text: Raw docstring text.

    Returns:
        Detected style name.
    """

    cleaned = inspect.cleandoc(text or "")
    if not cleaned:
        return "plain"
    if re.search(r"(?m)^:(param|type|returns?|rtype|raises?)\b", cleaned) or re.search(
        r"(?m)^\.\. (deprecated|warning|note|code-block)::",
        cleaned,
    ):
        return "sphinx"
    if re.search(r"(?m)^[A-Za-z][A-Za-z ]+\n-{3,}\s*$", cleaned):
        return "numpy"
    if re.search(r"(?m)^#{1,6}\s+(Parameters|Returns|Raises|Examples|See Also|Renderer Notes)\s*$", cleaned):
        return "markdown"
    if re.search(r"(?m)^(Args|Arguments|Parameters|Returns|Yields|Raises|Examples|See Also|Notes|Renderer Notes|Deprecated):\s*$", cleaned):
        return "google"
    return "plain"


def _parse_plain(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
    paragraphs = _paragraphs(text)
    if not paragraphs:
        return ParsedDocstring(style="plain")
    summary = paragraphs[0]
    description = "\n\n".join(paragraphs[1:]) or None
    examples = extract_code_blocks_from_docstring(text)
    return ParsedDocstring(
        summary=summary,
        description=description,
        examples=examples,
        style="plain",
    )


def _parse_google(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
    preamble, sections = _split_google_sections(text)
    summary, description = _summary_and_description(preamble)
    parsed = ParsedDocstring(summary=summary, description=description, style="google")
    for name, body in sections:
        normalized = name.lower()
        if normalized in {"args", "arguments", "parameters"}:
            parsed.parameters.extend(_parse_colon_items(body))
        elif normalized in {"returns", "yields"}:
            parsed.returns = _parse_return_section(body)
        elif normalized == "raises":
            parsed.raises.extend(
                ApiRaises(item.name, item.description)
                for item in _parse_colon_items(body, annotation_in_name=True)
            )
        elif normalized in {"examples", "example"}:
            parsed.examples.extend(_examples_or_text(body))
        elif normalized == "see also":
            parsed.see_also.extend(_parse_see_also(body))
        elif normalized == "notes":
            parsed.notes.extend(_paragraphs(body))
        elif normalized == "warnings":
            parsed.warnings.extend(_paragraphs(body))
        elif normalized == "renderer notes":
            parsed.renderer_notes.extend(_parse_renderer_notes(body))
        elif normalized == "deprecated":
            parsed.deprecated = True
            parsed.deprecation_message = " ".join(body.split()) or None
    if not parsed.examples:
        parsed.examples.extend(extract_code_blocks_from_docstring(text))
    return parsed


def _parse_numpy(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
    preamble, sections = _split_numpy_sections(text)
    summary, description = _summary_and_description(preamble)
    parsed = ParsedDocstring(summary=summary, description=description, style="numpy")
    for name, body in sections:
        normalized = name.lower()
        if normalized == "parameters":
            parsed.parameters.extend(_parse_numpy_parameters(body))
        elif normalized in {"returns", "yields"}:
            parsed.returns = _parse_return_section(body)
        elif normalized == "raises":
            parsed.raises.extend(
                ApiRaises(item.name, item.description)
                for item in _parse_numpy_parameters(body, annotation_in_name=True)
            )
        elif normalized == "examples":
            parsed.examples.extend(_examples_or_text(body))
        elif normalized == "see also":
            parsed.see_also.extend(_parse_see_also(body))
        elif normalized == "notes":
            parsed.notes.extend(_paragraphs(body))
        elif normalized == "warnings":
            parsed.warnings.extend(_paragraphs(body))
        elif normalized == "renderer notes":
            parsed.renderer_notes.extend(_parse_renderer_notes(body))
    if not parsed.examples:
        parsed.examples.extend(extract_code_blocks_from_docstring(text))
    return parsed


def _parse_sphinx(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
    lines = text.splitlines()
    preamble_lines: list[str] = []
    parsed = ParsedDocstring(style="sphinx")
    param_map: dict[str, ApiParameter] = {}
    return_annotation: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if match := re.match(r"^:param\s+([A-Za-z_][\w.]*)\s*:\s*(.*)$", stripped):
            name, desc = match.groups()
            param_map[name] = ApiParameter(name=name, description=desc or None, documented=True)
        elif match := re.match(r"^:type\s+([A-Za-z_][\w.]*)\s*:\s*(.*)$", stripped):
            name, annotation = match.groups()
            param_map.setdefault(name, ApiParameter(name=name, documented=True)).annotation = annotation or None
        elif match := re.match(r"^:returns?\s*:\s*(.*)$", stripped):
            parsed.returns = ApiReturn(description=match.group(1) or None, documented=True)
        elif match := re.match(r"^:rtype\s*:\s*(.*)$", stripped):
            return_annotation = match.group(1) or None
        elif match := re.match(r"^:raises?\s+([^:]+)\s*:\s*(.*)$", stripped):
            parsed.raises.append(ApiRaises(match.group(1).strip(), match.group(2) or None))
        elif stripped.startswith(".. deprecated::"):
            parsed.deprecated = True
            parsed.deprecation_message = _collect_directive_body(lines, i)
        elif stripped.startswith(".. warning::"):
            parsed.warnings.append(_collect_directive_body(lines, i))
        elif stripped.startswith(".. note::"):
            parsed.notes.append(_collect_directive_body(lines, i))
        elif stripped.startswith(".. code-block::"):
            language = stripped.partition("::")[2].strip() or "text"
            code_text = _collect_directive_body(lines, i, preserve=True)
            if code_text:
                parsed.examples.append(ApiExample(code_text, language=language))
        elif stripped.startswith(":"):
            pass
        else:
            preamble_lines.append(line)
        i += 1
    parsed.summary, parsed.description = _summary_and_description("\n".join(preamble_lines))
    parsed.parameters = list(param_map.values())
    if return_annotation:
        if parsed.returns is None:
            parsed.returns = ApiReturn(documented=True)
        parsed.returns.annotation = return_annotation
    if not parsed.examples:
        parsed.examples.extend(extract_code_blocks_from_docstring(text))
    return parsed


def _parse_markdown(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
    preamble, sections = _split_markdown_sections(text)
    summary, description = _summary_and_description(preamble)
    parsed = ParsedDocstring(summary=summary, description=description, style="markdown")
    for name, body in sections:
        normalized = name.lower()
        if normalized == "parameters":
            parsed.parameters.extend(_parse_markdown_parameters(body))
        elif normalized in {"returns", "yields"}:
            parsed.returns = _parse_return_section(body)
        elif normalized == "raises":
            parsed.raises.extend(
                ApiRaises(item.name, item.description)
                for item in _parse_markdown_parameters(body, annotation_in_name=True)
            )
        elif normalized == "examples":
            parsed.examples.extend(_examples_or_text(body))
        elif normalized == "see also":
            parsed.see_also.extend(_parse_see_also(body))
        elif normalized == "renderer notes":
            parsed.renderer_notes.extend(_parse_renderer_notes(body))
    if not parsed.examples:
        parsed.examples.extend(extract_code_blocks_from_docstring(text))
    return parsed


def _split_google_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    preamble: list[str] = []
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        candidate = stripped[:-1].lower() if stripped.endswith(":") else ""
        if candidate in _GOOGLE_SECTION_NAMES and not line.startswith((" ", "\t")):
            if current_name is not None:
                sections.append((current_name, current_lines))
            current_name = stripped[:-1]
            current_lines = []
        elif current_name is None:
            preamble.append(line)
        else:
            current_lines.append(line)
    if current_name is not None:
        sections.append((current_name, current_lines))
    return "\n".join(preamble), [(name, inspect.cleandoc("\n".join(body))) for name, body in sections]


def _split_numpy_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    lines = text.splitlines()
    section_indexes: list[tuple[int, str]] = []
    for index in range(len(lines) - 1):
        name = lines[index].strip()
        if name and re.match(r"^-{3,}\s*$", lines[index + 1].strip()):
            section_indexes.append((index, name))
    if not section_indexes:
        return text, []
    preamble = "\n".join(lines[: section_indexes[0][0]])
    sections: list[tuple[str, str]] = []
    for position, (index, name) in enumerate(section_indexes):
        start = index + 2
        end = section_indexes[position + 1][0] if position + 1 < len(section_indexes) else len(lines)
        sections.append((name, inspect.cleandoc("\n".join(lines[start:end]))))
    return preamble, sections


def _split_markdown_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    preamble: list[str] = []
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines:
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            name = match.group(1).strip()
            if current_name is not None:
                sections.append((current_name, current_lines))
            elif not preamble:
                pass
            current_name = name
            current_lines = []
        elif current_name is None:
            preamble.append(line)
        else:
            current_lines.append(line)
    if current_name is not None:
        sections.append((current_name, current_lines))
    return "\n".join(preamble), [(name, inspect.cleandoc("\n".join(body))) for name, body in sections]


def _parse_colon_items(
    text: str,
    *,
    annotation_in_name: bool = False,
) -> list[ApiParameter]:
    items: list[ApiParameter] = []
    current: ApiParameter | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        match = re.match(r"^\s*([*]{0,2}[A-Za-z_][\w.]*)(?:\s*\(([^)]*)\))?\s*:\s*(.*)$", line)
        if match:
            name, annotation, description = match.groups()
            current = ApiParameter(
                name=name,
                annotation=None if annotation_in_name else annotation,
                description=description or None,
                documented=True,
            )
            items.append(current)
        elif current is not None:
            extra = line.strip()
            current.description = _join_text(current.description, extra)
    return items


def _parse_numpy_parameters(
    text: str,
    *,
    annotation_in_name: bool = False,
) -> list[ApiParameter]:
    items: list[ApiParameter] = []
    current: ApiParameter | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        match = re.match(r"^([A-Za-z_][\w.]*)\s*:\s*(.*)$", line)
        if match and not raw_line.startswith((" ", "\t")):
            name, annotation = match.groups()
            current = ApiParameter(
                name=name,
                annotation=None if annotation_in_name else annotation or None,
                documented=True,
            )
            items.append(current)
        elif current is not None:
            current.description = _join_text(current.description, line.strip())
    return items


def _parse_markdown_parameters(
    text: str,
    *,
    annotation_in_name: bool = False,
) -> list[ApiParameter]:
    table_items = _parse_markdown_parameter_table(text, annotation_in_name=annotation_in_name)
    if table_items:
        return table_items
    items: list[ApiParameter] = []
    for line in text.splitlines():
        match = re.match(r"^\s*[-*]\s+`?([*]{0,2}[A-Za-z_][\w.]*)`?(?:\s*\(([^)]*)\))?\s*:\s*(.*)$", line)
        if match:
            name, annotation, description = match.groups()
            items.append(
                ApiParameter(
                    name=name,
                    annotation=None if annotation_in_name else annotation,
                    description=description or None,
                    documented=True,
                )
            )
    return items


def _parse_markdown_parameter_table(
    text: str,
    *,
    annotation_in_name: bool,
) -> list[ApiParameter]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = [cell.strip().lower() for cell in lines[0].strip("|").split("|")]
    if "name" not in headers:
        return []
    items: list[ApiParameter] = []
    for row in lines[2:]:
        cells = [cell.strip().strip("`") for cell in row.strip("|").split("|")]
        values = {header: cells[index] if index < len(cells) else "" for index, header in enumerate(headers)}
        items.append(
            ApiParameter(
                name=values.get("name", ""),
                annotation=None if annotation_in_name else values.get("type") or values.get("annotation") or None,
                description=values.get("description") or None,
                documented=True,
            )
        )
    return [item for item in items if item.name]


def _parse_return_section(text: str) -> ApiReturn:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ApiReturn(documented=True)
    first = lines[0]
    match = re.match(r"^([^:]+):\s*(.*)$", first)
    if match:
        annotation, description = match.groups()
        tail = " ".join(lines[1:])
        return ApiReturn(
            annotation=annotation.strip(),
            description=_join_text(description or None, tail),
            documented=True,
        )
    return ApiReturn(description=" ".join(lines), documented=True)


def _parse_see_also(text: str) -> list[ApiSeeAlso]:
    items: list[ApiSeeAlso] = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        if not stripped:
            continue
        if ":" in stripped:
            label, description = stripped.split(":", 1)
            items.append(ApiSeeAlso(label.strip("` "), target=label.strip("` "), description=description.strip()))
        else:
            items.append(ApiSeeAlso(stripped.strip("` "), target=stripped.strip("` ")))
    return items


def _parse_renderer_notes(text: str) -> list[ApiRendererNote]:
    notes: list[ApiRendererNote] = []
    for line in text.splitlines():
        match = re.match(r"^\s*(DOCX|PDF|HTML|ALL)\s*:\s*(.*)$", line.strip(), flags=re.I)
        if match:
            output_format, message = match.groups()
            notes.append(
                ApiRendererNote(
                    None if output_format.lower() == "all" else output_format.lower(),
                    message.strip(),
                    "warning" if "warning" in message.lower() else "info",
                )
            )
    if not notes and text.strip():
        notes.append(ApiRendererNote(None, " ".join(text.split())))
    return notes


def _examples_or_text(text: str) -> list[ApiExample]:
    examples = extract_code_blocks_from_docstring(text)
    if examples:
        return examples
    cleaned = inspect.cleandoc(text)
    return [ApiExample(cleaned)] if cleaned else []


def _summary_and_description(text: str) -> tuple[str | None, str | None]:
    paragraphs = _paragraphs(text)
    if not paragraphs:
        return None, None
    return paragraphs[0], "\n\n".join(paragraphs[1:]) or None


def _paragraphs(text: str) -> list[str]:
    return [" ".join(part.split()) for part in re.split(r"\n\s*\n", inspect.cleandoc(text)) if part.strip()]


def _join_text(left: str | None, right: str | None) -> str | None:
    pieces = [piece.strip() for piece in (left, right) if piece and piece.strip()]
    return " ".join(pieces) if pieces else None


def _collect_directive_body(
    lines: list[str],
    start: int,
    *,
    preserve: bool = False,
) -> str:
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip().startswith((":",".. ")) and not line.startswith((" ", "\t")):
            break
        if line.startswith((" ", "\t")) or not line.strip():
            body.append(line)
        else:
            break
    text = "\n".join(body)
    return inspect.cleandoc(text) if not preserve else inspect.cleandoc(text)


_PARSERS.update(
    {
        "plain": _parse_plain,
        "google": _parse_google,
        "numpy": _parse_numpy,
        "sphinx": _parse_sphinx,
        "markdown": _parse_markdown,
    }
)


__all__ = [
    "DocstringParser",
    "ParsedDocstring",
    "detect_docstring_style",
    "parse_docstring",
    "register_docstring_parser",
]
