"""Docstring parsers for normalized API documentation metadata.

Attributes:
    DocstringParser: Callable signature for custom parser functions registered
        with ``register_docstring_parser``.
"""

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
        style: Parser style that produced the result. Built-in parser results
            use a standard ``ApiDocstringStyleName``; custom parser results may
            use repository-specific style names.
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
    style: str = "plain"
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
        """Return a parser that detects the docstring style automatically.

        Returns:
            Parser object configured with ``style="auto"``.

        Examples:
            Reuse auto detection across a repository collection:

            ```python
            from oodocs.apidoc import ApiDocstringParser, collect_api

            parser = ApiDocstringParser.auto()
            api = collect_api(".", docstring_style=parser)
            ```
        """

        return cls("auto")

    @classmethod
    def google(cls) -> ApiDocstringParser:
        """Return a Google-style parser object.

        Returns:
            Parser object configured with ``style="google"``.

        Examples:
            Parse a Google-style docstring directly, then use the same parser
            for repository collection:

            ```python
            from oodocs.apidoc import ApiDocstringParser, collect_api

            parser = ApiDocstringParser.google()
            parsed = parser.parse("Load.\\n\\nArgs:\\n    path: Input path.")
            assert parsed.parameters[0].name == "path"
            api = collect_api(".", docstring_style=parser)
            ```
        """

        return cls("google")

    @classmethod
    def numpy(cls) -> ApiDocstringParser:
        """Return a NumPy-style parser object.

        Returns:
            Parser object configured with ``style="numpy"``.

        Examples:
            Use NumPy-style parsing for a scientific package:

            ```python
            from oodocs.apidoc import ApiDocstringParser, collect_api

            parser = ApiDocstringParser.numpy()
            parsed = parser.parse(
                "Load data.\\n\\n"
                "Parameters\\n"
                "----------\\n"
                "path : str\\n"
                "    Input path.",
            )
            assert parsed.parameters[0].annotation == "str"
            api = collect_api(".", docstring_style=parser)
            ```
        """

        return cls("numpy")

    @classmethod
    def sphinx(cls) -> ApiDocstringParser:
        """Return a Sphinx/reST-style parser object.

        Returns:
            Parser object configured with ``style="sphinx"``.

        Examples:
            Parse reST field lists before rendering an API object:

            ```python
            from oodocs.apidoc import ApiDocstringParser

            parser = ApiDocstringParser.sphinx()
            parsed = parser.parse(
                "Load data.\\n\\n:param path: Input path.\\n:type path: str",
            )
            assert parsed.parameters[0].description == "Input path."
            ```
        """

        return cls("sphinx")

    @classmethod
    def markdown(cls) -> ApiDocstringParser:
        """Return a Markdown-style parser object.

        Returns:
            Parser object configured with ``style="markdown"``.

        Examples:
            Parse Markdown-section docstrings in a repository-local convention:

            ```python
            from oodocs.apidoc import ApiDocstringParser, collect_api

            parser = ApiDocstringParser.markdown()
            parsed = parser.parse(
                "Load data.\\n\\n## Parameters\\n\\n| Name | Type | Description |\\n"
                "| --- | --- | --- |\\n| path | str | Input path. |",
            )
            assert parsed.parameters[0].annotation == "str"
            api = collect_api(".", docstring_style=parser)
            ```
        """

        return cls("markdown")

    @classmethod
    def plain(cls) -> ApiDocstringParser:
        """Return a plain text parser object.

        Returns:
            Parser object configured with ``style="plain"``.

        Examples:
            Use plain parsing when a legacy package only has prose docstrings:

            ```python
            from oodocs.apidoc import ApiDocstringParser, collect_api

            parser = ApiDocstringParser.plain()
            parsed = parser.parse("Load data.\\n\\nAdditional details.")
            assert parsed.description == "Additional details."
            api = collect_api(".", docstring_style=parser)
            ```
        """

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

        Examples:
            Normalize user-facing configuration before passing it to
            ``collect_api``:

            ```python
            from oodocs.apidoc import ApiDocstringParser, collect_api

            parser = ApiDocstringParser.from_value({"style": "google"})
            api = collect_api(".", docstring_style=parser)
            ```
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

        Examples:
            Restore a parser policy from an API sidecar or config payload:

            ```python
            from oodocs.apidoc import ApiDocstringParser

            parser = ApiDocstringParser.from_dict({"style": "auto"})
            parsed = parser.parse("Summary.\\n\\nArgs:\\n    path: Input path.")
            assert parsed.style == "google"
            ```
        """

        return cls(str(data.get("style", "auto")))

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized parser data.

        Returns:
            JSON-serializable parser configuration.

        Examples:
            Store the parser policy beside an API sidecar:

            ```python
            parser = ApiDocstringParser.google()
            payload = parser.to_dict()
            ```
        """

        return {"style": self.style}

    def detect(self, text: str | None) -> str:
        """Detect the style that would be used for ``text``.

        Args:
            text: Raw docstring text.

        Returns:
            Detected style for ``"auto"`` parsers or this parser's explicit
            style when configured explicitly. Explicit custom parser styles
            are returned as their registered style name.

        Examples:
            Preview the parser choice before collection:

            ```python
            parser = ApiDocstringParser.auto()
            assert parser.detect("Args:\\n    path: Input.") == "google"
            ```
        """

        if self.style == "auto":
            return detect_docstring_style(text)
        return self.style

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

        Examples:
            Parse an isolated docstring before deciding whether to collect the
            full package:

            ```python
            parser = ApiDocstringParser.google()
            parsed = parser.parse(
                "Load a file.\\n\\nArgs:\\n    path: File path.",
                qualname="mypkg.load",
                module="mypkg",
            )
            assert parsed.parameters[0].name == "path"
            ```
        """

        return parse_docstring(text, style=self.style, qualname=qualname, module=module)

    def __call__(
        self,
        text: str | None,
        *,
        qualname: str | None = None,
        module: str | None = None,
    ) -> ParsedDocstring:
        """Parse one docstring when the parser object is called directly.

        Args:
            text: Raw docstring text.
            qualname: Optional API object qualname for diagnostics.
            module: Optional module name for diagnostics.

        Returns:
            Normalized parse result.

        Examples:
            Use a parser object as a callable in repository-local tooling:

            ```python
            from oodocs.apidoc import ApiDocstringParser

            parser = ApiDocstringParser.google()
            parsed = parser(
                "Run.\\n\\nArgs:\\n    path: Input path.",
                qualname="mypkg.run",
                module="mypkg",
            )
            assert parsed.parameters[0].name == "path"
            ```
        """

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
_MARKDOWN_DETECTION_SECTIONS = (
    "Parameters",
    "Attributes",
    "Returns",
    "Yields",
    "Raises",
    "Examples",
    "See Also",
    "Notes",
    "Warnings",
    "Renderer Notes",
    "Deprecated",
)
_GOOGLE_DETECTION_SECTIONS = (
    "Args",
    "Arguments",
    "Parameters",
    "Attributes",
    "Returns",
    "Yields",
    "Raises",
    "Examples",
    "See Also",
    "Notes",
    "Warnings",
    "Renderer Notes",
    "Deprecated",
)
_MARKDOWN_SECTION_PATTERN = (
    r"(?m)^#{1,6}\s+("
    + "|".join(re.escape(name) for name in _MARKDOWN_DETECTION_SECTIONS)
    + r")\s*$"
)
_GOOGLE_SECTION_PATTERN = (
    r"(?m)^("
    + "|".join(re.escape(name) for name in _GOOGLE_DETECTION_SECTIONS)
    + r"):\s*$"
)


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
        Register a parser for a repository-specific brief format and pass the
        parser object into collection:

        ```python
        from oodocs.apidoc import ApiDocstringParser, ParsedDocstring, collect_api
        from oodocs.apidoc.docstring import parse_docstring, register_docstring_parser

        def parse_custom(text, qualname, module):
            parsed = parse_docstring(text, style="plain", qualname=qualname, module=module)
            return ParsedDocstring(summary=f"brief: {parsed.summary}", style="brief")

        register_docstring_parser("brief", parse_custom)
        api = collect_api(".", docstring_style=ApiDocstringParser("brief"))
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

    Examples:
        Check whether a plugin module registered the expected parser:

        ```python
        from oodocs.apidoc import docstring_parser_names

        assert "google" in docstring_parser_names()
        ```
    """

    return tuple(sorted(_PARSERS))


def is_docstring_style_supported(style: str | ApiDocstringParser) -> bool:
    """Return whether a docstring style can be parsed.

    Args:
        style: Parser style name or parser object.

    Returns:
        Whether ``parse_docstring`` can dispatch the style.

    Examples:
        Validate user configuration before running collection:

        ```python
        from oodocs.apidoc import ApiDocstringParser, is_docstring_style_supported

        parser = ApiDocstringParser.from_value("google")
        assert is_docstring_style_supported(parser)
        ```
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

    Examples:
        Preview automatic parser dispatch before collecting a repository:

        ```python
        from oodocs.apidoc import collect_api, detect_docstring_style

        style = detect_docstring_style(
            "Load.\\n\\nArgs:\\n    path: Input path.",
        )
        assert style == "google"
        api = collect_api(".", docstring_style="auto")
        ```
    """

    cleaned = inspect.cleandoc(text or "")
    if not cleaned:
        return "plain"
    if re.search(r"(?m)^:(param|type|returns?|rtype|yields?|ytype|yieldtype|raises?)\b", cleaned) or re.search(
        r"(?m)^\.\. (deprecated|warning|note|code-block)::",
        cleaned,
    ):
        return "sphinx"
    if re.search(r"(?m)^[A-Za-z][A-Za-z ]+\n-{3,}\s*$", cleaned):
        return "numpy"
    if re.search(_MARKDOWN_SECTION_PATTERN, cleaned):
        return "markdown"
    if re.search(_GOOGLE_SECTION_PATTERN, cleaned):
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
            parsed.returns = _parse_numpy_return_section(body)
        elif normalized == "raises" and not parsed.raises:
            parsed.raises.extend(_parse_numpy_raises(body))
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
        elif normalized == "deprecated":
            parsed.deprecated = True
            parsed.deprecation_message = " ".join(body.split()) or None
    if not parsed.examples:
        parsed.examples.extend(extract_code_blocks_from_docstring(text))
    return parsed


def _parse_sphinx(text: str, qualname: str | None, module: str | None) -> ParsedDocstring:
    lines = text.splitlines()
    preamble_lines: list[str] = []
    parsed = _parse_with_docstring_parser(text, "sphinx", qualname, module) or ParsedDocstring(style="sphinx")
    param_map: dict[str, ApiParameter] = {}
    attr_map: dict[str, ApiParameter] = {}
    return_annotation: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if match := re.match(
            r"^:param\s+(?:(?P<type>[^:\s]+)\s+)?(?P<name>[A-Za-z_][\w.]*)\s*:\s*(?P<body>.*)$",
            stripped,
        ):
            name = match.group("name")
            desc, next_index = _collect_sphinx_field_body(lines, i, match.group("body"))
            if not parsed.parameters:
                param_map[name] = ApiParameter(
                    name=name,
                    annotation=match.group("type"),
                    description=desc,
                    documented=True,
                )
            i = next_index - 1
        elif match := re.match(r"^:type\s+([A-Za-z_][\w.]*)\s*:\s*(.*)$", stripped):
            name, annotation = match.groups()
            annotation, next_index = _collect_sphinx_field_body(lines, i, annotation)
            if not parsed.parameters:
                param_map.setdefault(name, ApiParameter(name=name, documented=True)).annotation = annotation
            i = next_index - 1
        elif match := re.match(
            r"^:(?:ivar|var|cvar)\s+(?:(?P<type>[^:\s]+)\s+)?(?P<name>[A-Za-z_][\w.]*)\s*:\s*(?P<body>.*)$",
            stripped,
        ):
            name = match.group("name")
            desc, next_index = _collect_sphinx_field_body(lines, i, match.group("body"))
            if not parsed.attributes:
                attr_map[name] = ApiParameter(
                    name=name,
                    annotation=match.group("type"),
                    description=desc,
                    documented=True,
                    source="docstring",
                )
            i = next_index - 1
        elif match := re.match(r"^:vartype\s+([A-Za-z_][\w.]*)\s*:\s*(.*)$", stripped):
            name, annotation = match.groups()
            annotation, next_index = _collect_sphinx_field_body(lines, i, annotation)
            if not parsed.attributes:
                attr_map.setdefault(
                    name,
                    ApiParameter(name=name, documented=True, source="docstring"),
                ).annotation = annotation
            i = next_index - 1
        elif match := re.match(r"^:(?:returns?|yields?)\s*:\s*(.*)$", stripped):
            description, next_index = _collect_sphinx_field_body(lines, i, match.group(1))
            if parsed.returns is None:
                parsed.returns = ApiReturn(description=description, documented=True)
            i = next_index - 1
        elif match := re.match(r"^:(?:rtype|ytype|yieldtype)\s*:\s*(.*)$", stripped):
            return_annotation, next_index = _collect_sphinx_field_body(lines, i, match.group(1))
            i = next_index - 1
        elif match := re.match(r"^:raises?\s+([^:]+)\s*:\s*(.*)$", stripped):
            description, next_index = _collect_sphinx_field_body(lines, i, match.group(2))
            if not parsed.raises:
                parsed.raises.append(ApiRaises(match.group(1).strip(), description))
            i = next_index - 1
        elif stripped.startswith(".. deprecated::"):
            parsed.deprecated = True
            parsed.deprecation_message = _collect_directive_body(lines, i)
            i = _skip_sphinx_body(lines, i) - 1
        elif stripped.startswith(".. warning::"):
            parsed.warnings.append(_collect_directive_body(lines, i))
            i = _skip_sphinx_body(lines, i) - 1
        elif stripped.startswith(".. note::"):
            parsed.notes.append(_collect_directive_body(lines, i))
            i = _skip_sphinx_body(lines, i) - 1
        elif stripped.startswith(".. code-block::"):
            language = stripped.partition("::")[2].strip() or "text"
            code_text = _collect_directive_body(lines, i, preserve=True)
            if code_text and not parsed.examples:
                parsed.examples.append(ApiExample(code_text, language=language))
            i = _skip_sphinx_body(lines, i) - 1
        elif stripped.startswith(":"):
            pass
        else:
            preamble_lines.append(line)
        i += 1
    if parsed.summary is None and parsed.description is None:
        parsed.summary, parsed.description = _summary_and_description("\n".join(preamble_lines))
    if not parsed.parameters:
        parsed.parameters = list(param_map.values())
    if not parsed.attributes:
        parsed.attributes = list(attr_map.values())
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
            parsed.raises.extend(_parse_markdown_raises(body))
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


def _parse_numpy_raises(text: str) -> list[ApiRaises]:
    items: list[ApiRaises] = []
    current: ApiRaises | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        match = re.match(
            r"^([A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*)(?:\s*:\s*(.*))?$",
            line,
        )
        if match and not raw_line.startswith((" ", "\t")):
            exception, description = match.groups()
            current = ApiRaises(exception.strip(), description or None)
            items.append(current)
        elif current is not None:
            current.description = _join_text(current.description, line.strip())
    return items


def _parse_numpy_return_section(text: str) -> ApiReturn:
    entries: list[tuple[str | None, str | None, str | None]] = []
    current_index: int | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        name: str | None = None
        annotation: str | None = stripped
        named_match = None
        if ":" in stripped:
            possible_name, possible_annotation = stripped.split(":", 1)
            if re.match(r"^[A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*$", possible_name.strip()):
                named_match = (possible_name.strip(), possible_annotation.strip() or None)

        if named_match is None and current_index is not None:
            name, annotation, description = entries[current_index]
            entries[current_index] = (name, annotation, _join_text(description, stripped))
            continue
        if named_match is not None:
            name, annotation = named_match

        entries.append((name, annotation or None, None))
        current_index = len(entries) - 1

    if not entries:
        return ApiReturn(documented=True)
    if len(entries) == 1:
        name, annotation, description = entries[0]
        if name:
            description = _join_text(f"{name}:", description)
        return ApiReturn(annotation=annotation, description=description, documented=True)

    description_lines: list[str] = []
    for name, annotation, description in entries:
        label = name or annotation or "return"
        if name and annotation:
            label = f"{name} ({annotation})"
        description_lines.append(_join_text(f"{label}:", description) or f"{label}:")
    return ApiReturn(description="\n".join(description_lines), documented=True)


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
                    annotation=None if annotation_in_name else _plain_code_text(annotation),
                    description=_plain_code_text(description) or None,
                    documented=True,
                    source="docstring",
                )
            )
    return items


def _parse_markdown_raises(text: str) -> list[ApiRaises]:
    table_items = _parse_markdown_raises_table(text)
    if table_items:
        return table_items
    items = _parse_markdown_parameters(text, annotation_in_name=True)
    if not items:
        items = _parse_colon_items(text, annotation_in_name=True)
    return [ApiRaises(item.name, item.description) for item in items]


def _parse_markdown_raises_table(text: str) -> list[ApiRaises]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = [cell.strip().lower() for cell in lines[0].strip("|").split("|")]
    name_header = next(
        (header for header in ("exception", "raises", "name", "type") if header in headers),
        None,
    )
    if name_header is None:
        return []
    result: list[ApiRaises] = []
    for row in lines[2:]:
        cells = [_plain_code_text(cell) or "" for cell in row.strip("|").split("|")]
        values = {header: cells[index] if index < len(cells) else "" for index, header in enumerate(headers)}
        exception = values.get(name_header, "")
        description = values.get("description") or values.get("reason") or values.get("when") or None
        if exception:
            result.append(ApiRaises(exception, description))
    return result


def _parse_markdown_parameter_table(
    text: str,
    *,
    annotation_in_name: bool,
) -> list[ApiParameter]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = [cell.strip().lower() for cell in lines[0].strip("|").split("|")]
    if "name" not in headers and "parameter" not in headers:
        return []
    items: list[ApiParameter] = []
    for row in lines[2:]:
        cells = [_plain_code_text(cell) for cell in row.strip("|").split("|")]
        values = {header: cells[index] if index < len(cells) else "" for index, header in enumerate(headers)}
        items.append(
            ApiParameter(
                name=values.get("name", "") or values.get("parameter", ""),
                annotation=None if annotation_in_name else values.get("type") or values.get("annotation") or None,
                description=values.get("description") or None,
                documented=True,
                source="docstring",
            )
        )
    return [item for item in items if item.name]


def _plain_code_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return re.sub(r"`([^`]+)`", r"\1", text)


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


def _collect_sphinx_field_body(
    lines: list[str],
    start: int,
    first_line: str,
) -> tuple[str | None, int]:
    body = [first_line.strip()] if first_line.strip() else []
    index = start + 1
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith((":", ".. ")) and not line.startswith((" ", "\t")):
            break
        if line.startswith((" ", "\t")) or not stripped:
            if stripped:
                body.append(stripped)
            index += 1
            continue
        break
    return (" ".join(body) if body else None), index


def _collect_directive_body(
    lines: list[str],
    start: int,
    *,
    preserve: bool = False,
) -> str:
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip().startswith((":", ".. ")) and not line.startswith((" ", "\t")):
            break
        if line.startswith((" ", "\t")) or not line.strip():
            body.append(line)
        else:
            break
    text = "\n".join(body)
    return inspect.cleandoc(text) if not preserve else inspect.cleandoc(text)


def _skip_sphinx_body(lines: list[str], start: int) -> int:
    index = start + 1
    while index < len(lines):
        line = lines[index]
        if line.strip().startswith((":",".. ")) and not line.startswith((" ", "\t")):
            break
        if line.startswith((" ", "\t")) or not line.strip():
            index += 1
            continue
        break
    return index


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
