"""Docstring parsers for normalized API documentation metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import importlib
import importlib.util
import re
from typing import Callable, Iterable, Mapping

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
        attributes: Parsed attribute documentation from module or class
            docstrings.
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
    attributes: list[ApiParameter] = field(default_factory=list)
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

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized parser output.

        Returns:
            JSON-serializable mapping containing every normalized docstring
            section and parser diagnostic.

        Examples:
            Persist parser output before deciding how to render it:

            ```python
            from oodocs.apidoc import parse_docstring

            parsed = parse_docstring("Summary.\\n\\nArgs:\\n    path: Input.")
            payload = parsed.to_dict()
            ```
        """

        return {
            "summary": self.summary,
            "description": self.description,
            "parameters": [item.to_dict() for item in self.parameters],
            "attributes": [item.to_dict() for item in self.attributes],
            "returns": self.returns.to_dict() if self.returns is not None else None,
            "raises": [item.to_dict() for item in self.raises],
            "examples": [item.to_dict() for item in self.examples],
            "see_also": [item.to_dict() for item in self.see_also],
            "renderer_notes": [item.to_dict() for item in self.renderer_notes],
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "style": self.style,
            "issues": [item.to_dict() for item in self.issues],
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ParsedDocstring:
        """Reconstruct parser output from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Parsed docstring object with normalized section metadata.

        Examples:
            Rehydrate parser output from a custom cache:

            ```python
            from oodocs.apidoc import ParsedDocstring

            parsed = ParsedDocstring.from_dict(saved_payload)
            ```
        """

        returns_data = data.get("returns")
        return cls(
            summary=_optional_str(data.get("summary")),
            description=_optional_str(data.get("description")),
            parameters=[
                ApiParameter.from_dict(item)
                for item in data.get("parameters", [])  # type: ignore[union-attr]
            ],
            attributes=[
                ApiParameter.from_dict(item)
                for item in data.get("attributes", [])  # type: ignore[union-attr]
            ],
            returns=ApiReturn.from_dict(returns_data) if isinstance(returns_data, dict) else None,
            raises=[
                ApiRaises.from_dict(item)
                for item in data.get("raises", [])  # type: ignore[union-attr]
            ],
            examples=[
                ApiExample.from_dict(item)
                for item in data.get("examples", [])  # type: ignore[union-attr]
            ],
            see_also=[
                ApiSeeAlso.from_dict(item)
                for item in data.get("see_also", [])  # type: ignore[union-attr]
            ],
            renderer_notes=[
                ApiRendererNote.from_dict(item)
                for item in data.get("renderer_notes", [])  # type: ignore[union-attr]
            ],
            notes=[str(item) for item in data.get("notes", [])],  # type: ignore[union-attr]
            warnings=[str(item) for item in data.get("warnings", [])],  # type: ignore[union-attr]
            style=str(data.get("style", "plain")),  # type: ignore[arg-type]
            issues=[
                ApiDocIssue.from_dict(item)
                for item in data.get("issues", [])  # type: ignore[union-attr]
            ],
            deprecated=bool(data.get("deprecated", False)),
            deprecation_message=_optional_str(data.get("deprecation_message")),
        )


@dataclass(frozen=True, slots=True)
class ApiDocstringParser:
    """Reusable docstring parser configuration.

    Attributes:
        style: Parser style name. ``"auto"`` detects the style per docstring;
            registered custom parser names are also accepted.

    Examples:
        Reuse one parser while collecting or parsing several objects:

        ```python
        from oodocs.apidoc import ApiDocstringParser, collect_api

        parser = ApiDocstringParser.auto()
        api = collect_api(".", collector="griffe", docstring_style=parser)
        parsed = parser.parse("Summary.\\n\\nArgs:\\n    path: Input path.")
        ```
    """

    style: str = "auto"

    def __post_init__(self) -> None:
        normalized = self.style.strip().lower()
        if not normalized:
            raise ValueError("docstring parser style must not be empty")
        object.__setattr__(self, "style", normalized)

    @classmethod
    def auto(cls) -> ApiDocstringParser:
        """Return a parser that detects the docstring style automatically."""

        return cls("auto")

    @classmethod
    def google(cls) -> ApiDocstringParser:
        """Return a Google-style parser object."""

        return cls("google")

    @classmethod
    def numpy(cls) -> ApiDocstringParser:
        """Return a NumPy-style parser object."""

        return cls("numpy")

    @classmethod
    def sphinx(cls) -> ApiDocstringParser:
        """Return a Sphinx/reST-style parser object."""

        return cls("sphinx")

    @classmethod
    def markdown(cls) -> ApiDocstringParser:
        """Return a Markdown-style parser object."""

        return cls("markdown")

    @classmethod
    def plain(cls) -> ApiDocstringParser:
        """Return a plain text parser object."""

        return cls("plain")

    @classmethod
    def from_value(
        cls,
        value: ApiDocstringParser | str | Mapping[str, object] | None = None,
    ) -> ApiDocstringParser:
        """Return a parser object from a string, mapping, or existing parser.

        Args:
            value: Parser object, style name, serialized mapping, or ``None``.

        Returns:
            Normalized parser object.
        """

        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls.from_dict(value)
        return cls("auto" if value is None else value)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ApiDocstringParser:
        """Reconstruct a parser object from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Parser object.
        """

        return cls(str(data.get("style", "auto")))

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized parser data."""

        return {"style": self.style}

    def detect(self, text: str | None) -> ApiDocstringStyleName:
        """Detect the style that would be used for ``text``.

        Args:
            text: Raw docstring text.

        Returns:
            Detected style for ``"auto"`` parsers or this parser's explicit
            style when configured explicitly.
        """

        if self.style == "auto":
            return detect_docstring_style(text)
        return self.style  # type: ignore[return-value]

    def parse(
        self,
        text: str | None,
        *,
        qualname: str | None = None,
        module: str | None = None,
    ) -> ParsedDocstring:
        """Parse one docstring with this parser configuration.

        Args:
            text: Raw docstring text.
            qualname: Optional API object qualname for diagnostics.
            module: Optional module name for diagnostics.

        Returns:
            Normalized parse result.
        """

        return parse_docstring(text, style=self.style, qualname=qualname, module=module)

    def __call__(
        self,
        text: str | None,
        *,
        qualname: str | None = None,
        module: str | None = None,
    ) -> ParsedDocstring:
        """Parse one docstring when the object is called directly."""

        return self.parse(text, qualname=qualname, module=module)


_PARSERS: dict[str, DocstringParser] = {}
_STANDARD_STYLES = {"google", "numpy", "sphinx", "markdown", "plain"}
_DOCSTRING_PARSER_STYLES = {
    "google": "GOOGLE",
    "numpy": "NUMPYDOC",
    "sphinx": "REST",
}
_GOOGLE_SECTION_NAMES = {
    "args",
    "arguments",
    "parameters",
    "attributes",
    "attribute",
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
    style: str | ApiDocstringParser = "auto",
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
    parser_config = ApiDocstringParser.from_value(style)
    requested = parser_config.style
    detected = detect_docstring_style(cleaned) if requested == "auto" else requested
    parser = _PARSERS.get(detected)
    if parser is None:
        raise ValueError(f"Unsupported docstring style: {style!r}")
    parsed = parser(cleaned, qualname, module)
    if requested != "auto" and requested in _STANDARD_STYLES:
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


def load_docstring_parser_modules(modules: Iterable[str] | None) -> tuple[str, ...]:
    """Import modules that register custom docstring parsers.

    Args:
        modules: Importable module names. Each module is expected to call
            ``register_docstring_parser(...)`` at import time.

    Returns:
        Normalized module names that were imported.

    Raises:
        ImportError: If a parser module cannot be imported.

    Examples:
        Load repository-local parser hooks before collecting a package:

        ```python
        from oodocs.apidoc import collect_api, load_docstring_parser_modules

        load_docstring_parser_modules(["mypkg.docs.parsers"])
        api = collect_api(".", docstring_style="my-custom-style")
        ```
    """

    normalized = tuple(str(module).strip() for module in modules or () if str(module).strip())
    for module in normalized:
        importlib.import_module(module)
    return normalized


def docstring_parser_names() -> tuple[str, ...]:
    """Return registered explicit parser style names.

    Returns:
        Sorted parser style names. ``"auto"`` is not included because it is a
        dispatch mode rather than a concrete parser.
    """

    return tuple(sorted(_PARSERS))


def is_docstring_style_supported(style: str | ApiDocstringParser) -> bool:
    """Return whether a docstring style can be parsed.

    Args:
        style: Parser style name or parser object.

    Returns:
        Whether ``parse_docstring`` can dispatch the style.
    """

    normalized = ApiDocstringParser.from_value(style).style
    return normalized == "auto" or normalized in _PARSERS


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


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
    if re.search(r"(?m)^#{1,6}\s+(Parameters|Attributes|Returns|Raises|Examples|See Also|Notes|Warnings|Renderer Notes|Deprecated)\s*$", cleaned):
        return "markdown"
    if re.search(r"(?m)^(Args|Arguments|Parameters|Attributes|Returns|Yields|Raises|Examples|See Also|Notes|Warnings|Renderer Notes|Deprecated):\s*$", cleaned):
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
    parsed = _parse_with_docstring_parser(text, "google", qualname, module) or ParsedDocstring(
        summary=summary,
        description=description,
        style="google",
    )
    if parsed.summary is None:
        parsed.summary = summary
    if parsed.description is None:
        parsed.description = description
    for name, body in sections:
        normalized = name.lower()
        if normalized in {"args", "arguments", "parameters"} and not parsed.parameters:
            parsed.parameters.extend(_parse_colon_items(body))
        elif normalized in {"attributes", "attribute"} and not parsed.attributes:
            parsed.attributes.extend(_parse_colon_items(body))
        elif normalized in {"returns", "yields"} and parsed.returns is None:
            parsed.returns = _parse_return_section(body)
        elif normalized == "raises" and not parsed.raises:
            parsed.raises.extend(
                ApiRaises(item.name, item.description)
                for item in _parse_colon_items(body, annotation_in_name=True)
            )
        elif normalized in {"examples", "example"} and not parsed.examples:
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
    parsed = _parse_with_docstring_parser(text, "numpy", qualname, module) or ParsedDocstring(
        summary=summary,
        description=description,
        style="numpy",
    )
    if parsed.summary is None:
        parsed.summary = summary
    if parsed.description is None:
        parsed.description = description
    for name, body in sections:
        normalized = name.lower()
        if normalized == "parameters" and not parsed.parameters:
            parsed.parameters.extend(_parse_numpy_parameters(body))
        elif normalized == "attributes" and not parsed.attributes:
            parsed.attributes.extend(_parse_numpy_parameters(body))
        elif normalized in {"returns", "yields"} and parsed.returns is None:
            parsed.returns = _parse_return_section(body)
        elif normalized == "raises" and not parsed.raises:
            parsed.raises.extend(
                ApiRaises(item.name, item.description)
                for item in _parse_numpy_parameters(body, annotation_in_name=True)
            )
        elif normalized == "examples" and not parsed.examples:
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
    parsed = _parse_with_docstring_parser(text, "sphinx", qualname, module) or ParsedDocstring(style="sphinx")
    param_map: dict[str, ApiParameter] = {}
    return_annotation: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if match := re.match(r"^:param\s+([A-Za-z_][\w.]*)\s*:\s*(.*)$", stripped):
            name, desc = match.groups()
            if not parsed.parameters:
                param_map[name] = ApiParameter(name=name, description=desc or None, documented=True)
        elif match := re.match(r"^:type\s+([A-Za-z_][\w.]*)\s*:\s*(.*)$", stripped):
            name, annotation = match.groups()
            if not parsed.parameters:
                param_map.setdefault(name, ApiParameter(name=name, documented=True)).annotation = annotation or None
        elif match := re.match(r"^:returns?\s*:\s*(.*)$", stripped):
            if parsed.returns is None:
                parsed.returns = ApiReturn(description=match.group(1) or None, documented=True)
        elif match := re.match(r"^:rtype\s*:\s*(.*)$", stripped):
            return_annotation = match.group(1) or None
        elif match := re.match(r"^:raises?\s+([^:]+)\s*:\s*(.*)$", stripped):
            if not parsed.raises:
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
            if code_text and not parsed.examples:
                parsed.examples.append(ApiExample(code_text, language=language))
        elif stripped.startswith(":"):
            pass
        else:
            preamble_lines.append(line)
        i += 1
    if parsed.summary is None and parsed.description is None:
        parsed.summary, parsed.description = _summary_and_description("\n".join(preamble_lines))
    if not parsed.parameters:
        parsed.parameters = list(param_map.values())
    if return_annotation:
        if parsed.returns is None:
            parsed.returns = ApiReturn(documented=True)
        parsed.returns.annotation = return_annotation
    if not parsed.examples:
        parsed.examples.extend(extract_code_blocks_from_docstring(text))
    return parsed


def _parse_with_docstring_parser(
    text: str,
    style: ApiDocstringStyleName,
    qualname: str | None,
    module: str | None,
) -> ParsedDocstring | None:
    if importlib.util.find_spec("docstring_parser") is None:
        return None
    try:
        import docstring_parser
    except Exception:
        return None
    style_name = _DOCSTRING_PARSER_STYLES.get(style)
    if style_name is None:
        return None
    try:
        parsed_doc = docstring_parser.parse(
            text,
            style=getattr(docstring_parser.Style, style_name),
        )
    except Exception as exc:
        return ParsedDocstring(
            style=style,
            issues=[
                ApiDocIssue(
                    "warning",
                    "docstring-parser-failed",
                    f"docstring-parser could not parse this docstring: {exc}",
                    qualname=qualname,
                    module=module,
                )
            ],
        )
    parsed = ParsedDocstring(
        summary=parsed_doc.short_description or None,
        description=parsed_doc.long_description or None,
        style=style,
    )
    for meta in parsed_doc.meta:
        class_name = type(meta).__name__
        if class_name == "DocstringParam":
            parameter = ApiParameter(
                name=str(getattr(meta, "arg_name", "") or ""),
                annotation=getattr(meta, "type_name", None),
                default=getattr(meta, "default", None),
                description=getattr(meta, "description", None),
                required=not bool(getattr(meta, "is_optional", False)),
                documented=True,
                source="docstring",
            )
            meta_args = [str(arg).lower() for arg in getattr(meta, "args", []) if arg is not None]
            if meta_args and meta_args[0] in {"attribute", "attributes", "ivar", "cvar", "var"}:
                parsed.attributes.append(parameter)
            else:
                parsed.parameters.append(parameter)
        elif class_name == "DocstringReturns":
            parsed.returns = ApiReturn(
                annotation=getattr(meta, "type_name", None),
                description=getattr(meta, "description", None),
                documented=True,
            )
        elif class_name == "DocstringRaises":
            exception = getattr(meta, "type_name", None)
            if exception:
                parsed.raises.append(ApiRaises(str(exception), getattr(meta, "description", None)))
        elif class_name == "DocstringExample":
            parsed.examples.extend(_examples_from_docstring_parser_meta(meta))
        elif class_name == "DocstringDeprecated":
            parsed.deprecated = True
            parsed.deprecation_message = getattr(meta, "description", None)
    parsed.parameters = [parameter for parameter in parsed.parameters if parameter.name]
    parsed.attributes = [attribute for attribute in parsed.attributes if attribute.name]
    if not parsed.examples:
        parsed.examples.extend(extract_code_blocks_from_docstring(text))
    return parsed


def _examples_from_docstring_parser_meta(meta: object) -> list[ApiExample]:
    snippet = getattr(meta, "snippet", None)
    description = getattr(meta, "description", None)
    examples: list[ApiExample] = []
    if snippet:
        snippet_text = str(snippet)
        examples.append(ApiExample(snippet_text, language=_example_language(snippet_text)))
    if description:
        examples.extend(extract_code_blocks_from_docstring(str(description)))
        if not examples:
            examples.append(ApiExample(str(description), language="text"))
    return examples


def _example_language(text: str) -> str:
    return "pycon" if re.search(r"(?m)^\s*(>>>|\.\.\.)", text) else "python"


def _parse_markdown(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
    preamble, sections = _split_markdown_sections(text)
    summary, description = _summary_and_description(preamble)
    parsed = ParsedDocstring(summary=summary, description=description, style="markdown")
    for name, body in sections:
        normalized = name.lower()
        if normalized == "parameters":
            parsed.parameters.extend(_parse_markdown_parameters(body))
        elif normalized == "attributes":
            parsed.attributes.extend(_parse_markdown_parameters(body))
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
                source="docstring",
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
                source="docstring",
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
                    source="docstring",
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
                source="docstring",
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
    "ApiDocstringParser",
    "DocstringParser",
    "ParsedDocstring",
    "detect_docstring_style",
    "docstring_parser_names",
    "is_docstring_style_supported",
    "load_docstring_parser_modules",
    "parse_docstring",
    "register_docstring_parser",
]
