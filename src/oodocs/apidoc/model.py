"""Structured API documentation object model.

Attributes:
    ApiKind: Literal object kinds stored in an ``ApiObject`` tree.
    ApiVisibility: Literal visibility labels assigned during collection.
    ApiDocIssueSeverity: Literal issue severities used by coverage and parser
        diagnostics.
    ApiDocstringStyleName: Literal built-in docstring parser style names.
    ApiPresentationProfileName: Literal API reference presentation profile
        names.
"""

from __future__ import annotations

from dataclasses import MISSING, dataclass, field
from inspect import _empty
import json
from pathlib import Path
import re
from typing import Iterable, Iterator, Literal, Sequence

from oodocs.core import PathLike


ApiKind = Literal[
    "package",
    "module",
    "class",
    "function",
    "method",
    "property",
    "attribute",
    "data",
]
ApiVisibility = Literal["public", "private", "protected", "internal"]
ApiDocIssueSeverity = Literal["error", "warning", "info"]
ApiDocstringStyleName = Literal[
    "auto",
    "google",
    "numpy",
    "sphinx",
    "markdown",
    "plain",
]
ApiPresentationProfileName = Literal[
    "reference",
    "compact",
    "manual",
    "evidence",
    "review",
    "website",
]


@dataclass(slots=True)
class ApiParameter:
    """Function, method, class, or property parameter metadata.

    Attributes:
        name: Parameter name.
        annotation: Optional type annotation text.
        default: Optional default value text.
        kind: Optional signature kind such as ``"positional"`` or
            ``"keyword-only"``.
        description: Optional docstring description.
        required: Whether callers must provide the argument.
        documented: Whether this parameter was documented in the docstring.
        source: Optional source of the parameter metadata.

    Examples:
        Use parsed parameters as editable table rows in an OODocs document:

        ```python
        from oodocs import Document
        from oodocs.apidoc import ApiParameter, ApiObject

        obj = ApiObject(
            kind="function",
            name="render",
            qualname="pkg.render",
            module="pkg",
            parameters=[ApiParameter("path", "str", description="Output path.")],
        )
        doc = Document("API Notes", obj.to_parameter_table())
        ```
    """

    name: str
    annotation: str | None = None
    default: str | None = None
    kind: str | None = None
    description: str | None = None
    required: bool = True
    documented: bool = False
    source: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return this parameter as deterministic serialized data.

        Returns:
            JSON-serializable parameter mapping.

        Examples:
            Store parameter metadata in a custom sidecar:

            ```python
            from oodocs.apidoc import ApiParameter

            parameter = ApiParameter("path", "str", description="Input path.")
            payload = parameter.to_dict()
            ```
        """

        return {
            "name": self.name,
            "annotation": self.annotation,
            "default": self.default,
            "kind": self.kind,
            "description": self.description,
            "required": self.required,
            "documented": self.documented,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiParameter:
        """Reconstruct a parameter from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Parameter object.

        Examples:
            Rehydrate a parameter before building a review table:

            ```python
            from oodocs.apidoc import ApiParameter

            parameter = ApiParameter.from_dict({
                "name": "path",
                "annotation": "str",
                "description": "Input path.",
            })
            ```
        """

        return cls(
            name=str(data["name"]),
            annotation=_optional_str(data.get("annotation")),
            default=_optional_str(data.get("default")),
            kind=_optional_str(data.get("kind")),
            description=_optional_str(data.get("description")),
            required=bool(data.get("required", True)),
            documented=bool(data.get("documented", False)),
            source=_optional_str(data.get("source")),
        )

    def display_default(self) -> str:
        """Return the default value for table/prose display.

        Returns:
            Empty string when there is no default, otherwise stable default
            text.

        Examples:
            Display a default in a custom parameter table:

            ```python
            from oodocs.apidoc import ApiParameter

            parameter = ApiParameter("retries", "int", default="3")
            assert parameter.display_default() == "3"
            ```
        """

        if self.default in {None, "", str(_empty), str(MISSING)}:
            return ""
        return str(self.default)

    def display_annotation(self) -> str:
        """Return normalized annotation text for display.

        Returns:
            Empty string when no annotation is known.

        Examples:
            Normalize imported typing prefixes for display:

            ```python
            from oodocs.apidoc import ApiParameter

            parameter = ApiParameter("items", "typing.Sequence[str]")
            assert parameter.display_annotation() == "Sequence[str]"
            ```
        """

        if self.annotation in {None, "", str(_empty)}:
            return ""
        return str(self.annotation).replace("typing.", "")

    def to_table_cell_values(
        self,
        columns: Sequence[str] = ("name", "type", "default", "description"),
    ) -> list[object]:
        """Return table cell values for selected parameter columns.

        Args:
            columns: Column names to include.

        Returns:
            Values suitable for ``oodocs.Table`` rows.

        Examples:
            Build a row for a custom OODocs table:

            ```python
            from oodocs import Table
            from oodocs.apidoc import ApiParameter

            parameter = ApiParameter("path", "str", description="Input path.")
            table = Table(
                ["Name", "Type", "Description"],
                [parameter.to_table_cell_values(("name", "type", "description"))],
            )
            ```
        """

        values = {
            "name": self.name,
            "type": self.display_annotation(),
            "default": self.display_default(),
            "required": "yes" if self.required else "no",
            "description": self.description or "",
            "source": self.source or "",
        }
        return [values[column] for column in columns]

    def to_row(
        self,
        columns: Sequence[str] = ("name", "type", "default", "description"),
    ) -> list[object]:
        """Return this parameter as a table row.

        Args:
            columns: Column names to include.

        Returns:
            List of table cell values.

        Examples:
            Use the shorthand row helper with a compact column set:

            ```python
            from oodocs.apidoc import ApiParameter

            parameter = ApiParameter("verbose", "bool", default="False")
            row = parameter.to_row(("name", "default", "required"))
            ```
        """

        return self.to_table_cell_values(columns)

    def to_paragraph(self):
        """Return a compact paragraph describing this parameter.

        Returns:
            ``oodocs.Paragraph`` containing the parameter name and description.

        Examples:
            Add a single parameter note to an authored chapter:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiParameter

            parameter = ApiParameter("path", "str", description="Input path.")
            doc = Document("API Notes", Chapter("Parameter", parameter.to_paragraph()))
            ```
        """

        from oodocs.components.blocks import Paragraph
        from oodocs.components.inline import code

        pieces: list[object] = [code(self.name)]
        if self.annotation:
            pieces.extend([" (", code(self.display_annotation()), ")"])
        if self.description:
            pieces.extend([": ", self.description])
        return Paragraph(*pieces)


@dataclass(slots=True)
class ApiReturn:
    """Return value documentation.

    Attributes:
        annotation: Optional return type text.
        description: Optional return description.
        documented: Whether a returns/yields section documented the value.

    Examples:
        ```python
        from oodocs.apidoc import ApiReturn

        result = ApiReturn("bool", "Whether validation passed.", documented=True)
        ```
    """

    annotation: str | None = None
    description: str | None = None
    documented: bool = False

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable return metadata.

        Examples:
            Store return metadata in an API sidecar:

            ```python
            from oodocs.apidoc import ApiReturn

            payload = ApiReturn("bool", "Whether validation passed.").to_dict()
            ```
        """

        return {
            "annotation": self.annotation,
            "description": self.description,
            "documented": self.documented,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiReturn:
        """Reconstruct return metadata from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Return metadata object.

        Examples:
            Rehydrate return metadata before attaching it to an API object:

            ```python
            from oodocs.apidoc import ApiReturn

            returns = ApiReturn.from_dict({
                "annotation": "bool",
                "description": "Whether validation passed.",
                "documented": True,
            })
            ```
        """

        return cls(
            annotation=_optional_str(data.get("annotation")),
            description=_optional_str(data.get("description")),
            documented=bool(data.get("documented", False)),
        )


@dataclass(slots=True)
class ApiRaises:
    """Exception documented by an API object.

    Attributes:
        exception: Exception class or label.
        description: Optional reason the exception is raised.

    Examples:
        Attach documented exceptions to a parsed API object:

        ```python
        from oodocs.apidoc import ApiObject, ApiRaises

        obj = ApiObject(
            "function",
            "load",
            "mypkg.load",
            "mypkg",
            raises=[ApiRaises("ValueError", "If the path is invalid.")],
        )
        ```
    """

    exception: str
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable exception metadata.

        Examples:
            Serialize an exception entry for a sidecar:

            ```python
            from oodocs.apidoc import ApiRaises

            payload = ApiRaises("ValueError", "Invalid path.").to_dict()
            ```
        """

        return {"exception": self.exception, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiRaises:
        """Reconstruct exception metadata from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Exception metadata object.

        Examples:
            Rehydrate an exception entry from API JSON:

            ```python
            from oodocs.apidoc import ApiRaises

            item = ApiRaises.from_dict({
                "exception": "ValueError",
                "description": "Invalid path.",
            })
            ```
        """

        return cls(
            exception=str(data["exception"]),
            description=_optional_str(data.get("description")),
        )


@dataclass(slots=True)
class ApiExample:
    """Executable or illustrative code example from a docstring.

    Attributes:
        code: Example source code.
        language: Syntax language label.
        caption: Optional caption for rendered examples.
        source: Optional source label.
        syntax_ok: Optional syntax check result.
        doctest_ok: Optional doctest check result.

    Examples:
        Insert one parsed example into an authored section:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import ApiExample

        example = ApiExample("print('hello')", caption="Minimal use")
        doc = Document("Examples", Chapter("Snippet", example.to_block()))
        ```
    """

    code: str
    language: str = "python"
    caption: str | None = None
    source: str | None = None
    syntax_ok: bool | None = None
    doctest_ok: bool | None = None

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable example metadata.

        Examples:
            Store a parsed example in a sidecar:

            ```python
            from oodocs.apidoc import ApiExample

            payload = ApiExample("print('ok')", language="python").to_dict()
            ```
        """

        return {
            "code": self.code,
            "language": self.language,
            "caption": self.caption,
            "source": self.source,
            "syntax_ok": self.syntax_ok,
            "doctest_ok": self.doctest_ok,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiExample:
        """Reconstruct example metadata from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Example metadata object.

        Examples:
            Rehydrate an example and render it as a code block:

            ```python
            from oodocs.apidoc import ApiExample

            example = ApiExample.from_dict({
                "code": "print('ok')",
                "language": "python",
            })
            block = example.to_block()
            ```
        """

        return cls(
            code=str(data["code"]),
            language=str(data.get("language", "python")),
            caption=_optional_str(data.get("caption")),
            source=_optional_str(data.get("source")),
            syntax_ok=_optional_bool(data.get("syntax_ok")),
            doctest_ok=_optional_bool(data.get("doctest_ok")),
        )

    def to_block(self):
        """Return this example as a code block.

        Returns:
            ``oodocs.CodeBlock`` using the example language and code, with
            XML-incompatible control characters escaped for renderer safety.

        Examples:
            Insert a parsed example into an OODocs document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiExample

            example = ApiExample("print('ok')", language="python")
            doc = Document("Examples", Chapter("Quickstart", example.to_block()))
            ```
        """

        from oodocs.components.blocks import CodeBlock

        return CodeBlock(_xml_safe_text(self.code), language=self.language or "text")


@dataclass(slots=True)
class ApiSeeAlso:
    """Related API reference parsed from a docstring.

    Attributes:
        label: Display label.
        target: Optional fully qualified target.
        description: Optional relationship description.
        kind: Optional target kind.

    Examples:
        Attach related API entries to an object reference:

        ```python
        from oodocs.apidoc import ApiObject, ApiSeeAlso

        obj = ApiObject(
            "function",
            "load",
            "mypkg.load",
            "mypkg",
            see_also=[ApiSeeAlso("save", target="mypkg.save", kind="function")],
        )
        ```
    """

    label: str
    target: str | None = None
    description: str | None = None
    kind: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable related API metadata.

        Examples:
            Store a see-also entry in API JSON:

            ```python
            from oodocs.apidoc import ApiSeeAlso

            payload = ApiSeeAlso("save", target="mypkg.save").to_dict()
            ```
        """

        return {
            "label": self.label,
            "target": self.target,
            "description": self.description,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiSeeAlso:
        """Reconstruct see-also metadata from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Related API metadata object.

        Examples:
            Rehydrate a related API entry from a sidecar:

            ```python
            from oodocs.apidoc import ApiSeeAlso

            item = ApiSeeAlso.from_dict({
                "label": "save",
                "target": "mypkg.save",
                "kind": "function",
            })
            ```
        """

        return cls(
            label=str(data["label"]),
            target=_optional_str(data.get("target")),
            description=_optional_str(data.get("description")),
            kind=_optional_str(data.get("kind")),
        )


@dataclass(slots=True)
class ApiRendererNote:
    """Renderer-specific behavior note.

    Attributes:
        format: Optional output format label.
        message: Note text.
        severity: Note severity.

    Examples:
        Attach output-format guidance to an API object:

        ```python
        from oodocs.apidoc import ApiObject, ApiRendererNote

        obj = ApiObject(
            "function",
            "plot",
            "mypkg.plot",
            "mypkg",
            renderer_notes=[ApiRendererNote("pdf", "Wide tables may wrap.")],
        )
        ```
    """

    format: Literal["docx", "pdf", "html"] | None
    message: str
    severity: Literal["info", "warning"] = "info"

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable renderer note metadata.

        Examples:
            Store renderer-specific guidance in a sidecar:

            ```python
            from oodocs.apidoc import ApiRendererNote

            payload = ApiRendererNote("html", "Adds anchors.").to_dict()
            ```
        """

        return {
            "format": self.format,
            "message": self.message,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiRendererNote:
        """Reconstruct renderer-note metadata from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Renderer note metadata object.

        Examples:
            Rehydrate renderer guidance before rendering reference docs:

            ```python
            from oodocs.apidoc import ApiRendererNote

            note = ApiRendererNote.from_dict({
                "format": "pdf",
                "message": "Wide tables may wrap.",
                "severity": "warning",
            })
            ```
        """

        return cls(
            format=data.get("format"),  # type: ignore[arg-type]
            message=str(data["message"]),
            severity=str(data.get("severity", "info")),  # type: ignore[arg-type]
        )


@dataclass(slots=True)
class ApiDocIssue:
    """Documentation collection, parsing, or coverage issue.

    Attributes:
        severity: Issue severity.
        code: Stable kebab-case issue code.
        message: Human-readable message.
        qualname: Optional API object qualname.
        module: Optional module name.
        path: Optional source path.
        line_number: Optional 1-based source line.

    Examples:
        ```python
        issue = ApiDocIssue("warning", "missing-docstring", "No docstring.")
        ```
    """

    severity: ApiDocIssueSeverity
    code: str
    message: str
    qualname: str | None = None
    module: str | None = None
    path: str | None = None
    line_number: int | None = None

    def __post_init__(self) -> None:
        self.code = _normalize_issue_code(self.code)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable diagnostic mapping.

        Examples:
            Store parser or coverage diagnostics in API JSON:

            ```python
            from oodocs.apidoc import ApiDocIssue

            payload = ApiDocIssue(
                "warning",
                "missing-docstring",
                "No docstring.",
                qualname="mypkg.load",
            ).to_dict()
            ```
        """

        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "qualname": self.qualname,
            "module": self.module,
            "path": self.path,
            "line_number": self.line_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiDocIssue:
        """Reconstruct an issue from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Diagnostic issue object.

        Examples:
            Rehydrate a diagnostic from an API sidecar:

            ```python
            from oodocs.apidoc import ApiDocIssue

            issue = ApiDocIssue.from_dict({
                "severity": "warning",
                "code": "missing-docstring",
                "message": "No docstring.",
            })
            ```
        """

        return cls(
            severity=str(data["severity"]),  # type: ignore[arg-type]
            code=str(data["code"]),
            message=str(data["message"]),
            qualname=_optional_str(data.get("qualname")),
            module=_optional_str(data.get("module")),
            path=_optional_str(data.get("path")),
            line_number=_optional_int(data.get("line_number")),
        )

    def to_row(self) -> list[object]:
        """Return this issue as a table row.

        Returns:
            ``[severity, code, qualname, module, location, message]``.

        Examples:
            Convert diagnostics into table rows for release evidence:

            ```python
            from oodocs import Table
            from oodocs.apidoc import ApiDocIssue

            issue = ApiDocIssue("warning", "missing-docstring", "No docstring.")
            table = Table(
                ["Severity", "Code", "Object", "Module", "Location", "Message"],
                [issue.to_row()],
            )
            ```
        """

        location = ""
        if self.path:
            location = self.path
            if self.line_number is not None:
                location = f"{location}:{self.line_number}"
        return [
            self.severity,
            self.code,
            self.qualname or "",
            self.module or "",
            location,
            self.message,
        ]


@dataclass(slots=True)
class ApiObject:
    """Normalized API object that can be queried or rendered as OODocs blocks.

    Attributes:
        kind: Object kind.
        name: Local object name.
        qualname: Fully qualified name.
        module: Module name.
        visibility: Public/private classification.
        signature: Optional callable signature text.
        summary: First docstring sentence or paragraph.
        description: Additional docstring prose.
        parameters: Signature/docstring parameter metadata.
        returns: Optional return metadata.
        raises: Documented exceptions.
        examples: Parsed code examples.
        see_also: Parsed related API entries.
        notes: Parsed general notes.
        warnings: Parsed warning notes.
        renderer_notes: Renderer-specific notes.
        members: Child methods, properties, attributes, or nested objects.
        source_path: Optional source file path.
        line_number: Optional first source line.
        end_line_number: Optional final source line.
        deprecated: Whether the object is deprecated.
        deprecation_message: Optional deprecation guidance.
        metadata: Extensible deterministic metadata.

    Examples:
        Compose selected API objects into a normal OODocs document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api

        api = collect_api("oodocs", public_policy="__all__")
        classes = api.select(kind="class", module_prefix="oodocs.components")
        doc = Document("Component API", Chapter("Classes", *[
            obj.to_section(level=2, profile="manual") for obj in classes[:3]
        ]))
        ```
    """

    kind: ApiKind
    name: str
    qualname: str
    module: str
    visibility: ApiVisibility = "public"
    signature: str | None = None
    summary: str | None = None
    description: str | None = None
    parameters: list[ApiParameter] = field(default_factory=list)
    returns: ApiReturn | None = None
    raises: list[ApiRaises] = field(default_factory=list)
    examples: list[ApiExample] = field(default_factory=list)
    see_also: list[ApiSeeAlso] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    renderer_notes: list[ApiRendererNote] = field(default_factory=list)
    members: list[ApiObject] = field(default_factory=list)
    source_path: str | None = None
    line_number: int | None = None
    end_line_number: int | None = None
    deprecated: bool = False
    deprecation_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def documented(self) -> bool:
        """Return whether this object has user-facing documentation.

        Examples:
            Filter collected objects to find missing summaries:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            missing = [obj for obj in api.public_objects() if not obj.documented]
            ```
        """

        return bool(self.summary or self.description)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable object mapping.

        Examples:
            Persist one selected object into a custom sidecar:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            payload = api.functions()[0].to_dict()
            ```
        """

        return {
            "kind": self.kind,
            "name": self.name,
            "qualname": self.qualname,
            "module": self.module,
            "visibility": self.visibility,
            "signature": self.signature,
            "summary": self.summary,
            "description": self.description,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "returns": self.returns.to_dict() if self.returns else None,
            "raises": [item.to_dict() for item in self.raises],
            "examples": [item.to_dict() for item in self.examples],
            "see_also": [item.to_dict() for item in self.see_also],
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "renderer_notes": [item.to_dict() for item in self.renderer_notes],
            "members": [member.to_dict() for member in self.members],
            "source_path": self.source_path,
            "line_number": self.line_number,
            "end_line_number": self.end_line_number,
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
            "metadata": _jsonable_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiObject:
        """Reconstruct an API object from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            API object tree.

        Examples:
            Rehydrate one object and insert it into an OODocs document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiObject

            obj = ApiObject.from_dict(saved_payload)
            doc = Document("API", Chapter("Object", obj.to_section()))
            ```
        """

        returns_data = data.get("returns")
        return cls(
            kind=str(data["kind"]),  # type: ignore[arg-type]
            name=str(data["name"]),
            qualname=str(data["qualname"]),
            module=str(data["module"]),
            visibility=str(data.get("visibility", "public")),  # type: ignore[arg-type]
            signature=_optional_str(data.get("signature")),
            summary=_optional_str(data.get("summary")),
            description=_optional_str(data.get("description")),
            parameters=[
                ApiParameter.from_dict(item)
                for item in data.get("parameters", [])  # type: ignore[union-attr]
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
            notes=[str(item) for item in data.get("notes", [])],  # type: ignore[union-attr]
            warnings=[str(item) for item in data.get("warnings", [])],  # type: ignore[union-attr]
            renderer_notes=[
                ApiRendererNote.from_dict(item)
                for item in data.get("renderer_notes", [])  # type: ignore[union-attr]
            ],
            members=[
                ApiObject.from_dict(item)
                for item in data.get("members", [])  # type: ignore[union-attr]
            ],
            source_path=_optional_str(data.get("source_path")),
            line_number=_optional_int(data.get("line_number")),
            end_line_number=_optional_int(data.get("end_line_number")),
            deprecated=bool(data.get("deprecated", False)),
            deprecation_message=_optional_str(data.get("deprecation_message")),
            metadata=dict(data.get("metadata", {})),  # type: ignore[arg-type]
        )

    def plain_summary(self) -> str:
        """Return the best short description for this object.

        Returns:
            Summary text, first description sentence, or an empty string.

        Examples:
            Build a compact custom index from parsed objects:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            rows = [(obj.qualname, obj.plain_summary()) for obj in api.public_objects()]
            ```
        """

        if self.summary:
            return self.summary
        if self.description:
            return _first_sentence(self.description)
        return ""

    def display_name(self) -> str:
        """Return the display name used in headings and tables.

        Returns:
            Fully qualified name when available, otherwise the local object
            name.

        Examples:
            Use the same display label as generated API sections:

            ```python
            from oodocs.apidoc import ApiObject

            obj = ApiObject("function", "load", "mypkg.load", "mypkg")
            assert obj.display_name() == "mypkg.load"
            ```
        """

        return self.qualname or self.name

    def display_signature(self) -> str:
        """Return callable signature text for code blocks.

        Returns:
            Explicit signature text when collected, otherwise the display name.

        Examples:
            Preview the signature before rendering a code block:

            ```python
            from oodocs.apidoc import ApiObject

            obj = ApiObject(
                "function",
                "load",
                "mypkg.load",
                "mypkg",
                signature="load(path: str) -> str",
            )
            assert obj.display_signature() == "load(path: str) -> str"
            ```
        """

        if self.signature:
            return self.signature
        return self.display_name()

    def anchor_id(self) -> str:
        """Return a stable anchor id derived from the qualname.

        Returns:
            HTML-safe anchor id for the object.

        Examples:
            Use the anchor as an internal HTML link target:

            ```python
            from oodocs.apidoc import ApiObject

            obj = ApiObject("class", "Client", "mypkg.Client", "mypkg")
            anchor = obj.anchor_id()
            ```
        """

        return _anchor_id(self.qualname)

    def has_parameters(self) -> bool:
        """Return whether this object has parameter metadata.

        Returns:
            Whether ``parameters`` contains at least one item.

        Examples:
            Select only objects that can render parameter tables:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            parameterized = [obj for obj in api.functions() if obj.has_parameters()]
            ```
        """

        return bool(self.parameters)

    def has_examples(self) -> bool:
        """Return whether this object has parsed examples.

        Returns:
            Whether ``examples`` contains at least one item.

        Examples:
            Build an examples-only appendix:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            with_examples = [obj for obj in api.public_objects() if obj.has_examples()]
            ```
        """

        return bool(self.examples)

    def has_members(self) -> bool:
        """Return whether this object has child objects.

        Returns:
            Whether ``members`` contains at least one child object.

        Examples:
            Find class-like objects that have nested member documentation:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            documented_classes = [obj for obj in api.classes() if obj.has_members()]
            ```
        """

        return bool(self.members)

    def iter_members(
        self,
        kind: str | Iterable[str] | None = None,
        *,
        recursive: bool = False,
    ) -> Iterator[ApiObject]:
        """Iterate over child API objects.

        Args:
            kind: Optional kind or set of kinds to include.
            recursive: Whether to descend into nested members.

        Yields:
            Matching child objects in source order.

        Examples:
            Iterate class methods recursively:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            cls = api.classes()[0]
            methods = list(cls.iter_members(kind="method", recursive=True))
            ```
        """

        kinds = _normalize_kind_filter(kind)
        for member in self.members:
            if kinds is None or member.kind in kinds:
                yield member
            if recursive:
                yield from member.iter_members(kind, recursive=True)

    def select(
        self,
        *,
        kind: str | Iterable[str] | None = None,
        visibility: str | None = None,
        documented: bool | None = None,
        deprecated: bool | None = None,
        recursive: bool = True,
    ) -> list[ApiObject]:
        """Return filtered child API objects.

        Args:
            kind: Optional kind or kinds to include.
            visibility: Optional visibility to require.
            documented: Optional documentation-state filter.
            deprecated: Optional deprecation-state filter.
            recursive: Whether to include nested members.

        Returns:
            Matching objects in deterministic order.

        Examples:
            Select documented public methods from one class:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            cls = api.classes()[0]
            methods = cls.select(kind="method", visibility="public", documented=True)
            ```
        """

        objects = list(self.iter_members(kind, recursive=recursive))
        return [
            obj
            for obj in objects
            if _matches_object(
                obj,
                visibility=visibility,
                documented=documented,
                deprecated=deprecated,
            )
        ]

    def find(self, qualname_or_name: str) -> ApiObject | None:
        """Find a child object by qualname or local name.

        Args:
            qualname_or_name: Fully qualified or local object name.

        Returns:
            Matching object, or ``None``.

        Examples:
            Look up a nested method by fully qualified name:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            cls = api.classes()[0]
            method = cls.find(f"{cls.qualname}.render")
            ```
        """

        if qualname_or_name in {self.qualname, self.name}:
            return self
        for member in self.iter_members(recursive=True):
            if qualname_or_name in {member.qualname, member.name}:
                return member
        return None

    def to_summary_row(
        self,
        *,
        include_module: bool = True,
        link_name: bool = False,
    ) -> list[object]:
        """Return an OODocs table row summarizing this object.

        Args:
            include_module: Whether to include the module column.
            link_name: Whether the name cell should link to this object's
                section anchor.

        Returns:
            Table row suitable for ``ApiPackage.to_summary_table``.

        Examples:
            Build a custom summary table row:

            ```python
            from oodocs import Table
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            table = Table(["Kind", "Module", "Name", "Summary"], [obj.to_summary_row()])
            ```
        """

        name: object = self.display_name()
        if link_name:
            from oodocs.components.inline import Hyperlink

            name = Hyperlink.internal_anchor(self.anchor_id(), self.display_name())
        row: list[object] = [self.kind, name, self.plain_summary()]
        if include_module:
            row.insert(1, self.module)
        return row

    def to_summary_paragraph(self):
        """Return a compact OODocs paragraph for this object.

        Returns:
            OODocs paragraph containing the object kind, display name, and
            short summary.

        Examples:
            Insert one API summary into a hand-authored chapter:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document("API Notes", Chapter("Selected API", obj.to_summary_paragraph()))
            ```
        """

        from oodocs.apidoc.blocks import api_object_summary_paragraph

        return api_object_summary_paragraph(self)

    def to_signature_block(self, profile: object = "reference"):
        """Return this object's signature as an OODocs code block.

        Args:
            profile: Presentation profile name or object controlling signature
                wrapping and visibility.

        Returns:
            OODocs code block, or ``None`` when the profile suppresses
            signatures or the object has no signature.

        Examples:
            Insert the generated signature block into a custom chapter:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            block = obj.to_signature_block(profile="reference")
            doc = Document("API", Chapter("Signature", block))
            ```
        """

        from oodocs.apidoc.blocks import api_signature_block

        return api_signature_block(self, profile)

    def to_parameter_table(self, profile: object = "reference"):
        """Return this object's parameter table, if parameters are available.

        Args:
            profile: Presentation profile name or object controlling parameter
                columns and truncation.

        Returns:
            OODocs table, or ``None`` when the object has no parameters or the
            profile suppresses parameter tables.

        Examples:
            Add a function's parameters to a review document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            fn = api.functions()[0]
            table = fn.to_parameter_table(profile="review")
            doc = Document(
                "API Review",
                Chapter("Parameters", table) if table is not None else Chapter("Parameters"),
            )
            ```
        """

        from oodocs.apidoc.blocks import api_parameter_table

        return api_parameter_table(self, profile)

    def to_returns_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks documenting return values.

        Args:
            profile: Presentation profile name or object.

        Returns:
            Renderer-neutral OODocs blocks. Returns an empty list when no return
            documentation should render.

        Examples:
            Add return documentation to an authored section:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document("API", Chapter("Returns", *obj.to_returns_blocks()))
            ```
        """

        from oodocs.apidoc.blocks import api_returns_blocks

        return api_returns_blocks(self, profile)

    def to_raises_table(self, profile: object = "reference"):
        """Return this object's raises table, if exceptions are documented.

        Args:
            profile: Presentation profile name or object.

        Returns:
            OODocs table, or ``None`` when no exception documentation should
            render.

        Examples:
            Render documented exceptions as an editable table:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            table = obj.to_raises_table(profile="review")
            doc = Document("API Review", Chapter("Raises", table))
            ```
        """

        from oodocs.apidoc.blocks import api_raises_table

        return api_raises_table(self, profile)

    def to_examples_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for examples.

        Args:
            profile: Presentation profile name or object controlling example
                inclusion and maximum example count.

        Returns:
            OODocs code blocks and optional captions for parsed examples.

        Examples:
            Insert parsed examples into a tutorial:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document("Tutorial", Chapter("Examples", *obj.to_examples_blocks()))
            ```
        """

        from oodocs.apidoc.blocks import api_examples_blocks

        return api_examples_blocks(self, profile)

    def to_see_also_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for related API entries.

        Args:
            profile: Presentation profile name or object.

        Returns:
            OODocs blocks for parsed ``See Also`` entries.

        Examples:
            Render related API references as a small appendix:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document("API", Chapter("Related", *obj.to_see_also_blocks()))
            ```
        """

        from oodocs.apidoc.blocks import api_see_also_blocks

        return api_see_also_blocks(self, profile)

    def to_notes_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for parsed general notes.

        Args:
            profile: Presentation profile name or object.

        Returns:
            OODocs paragraphs for parsed notes.

        Examples:
            Include parsed notes in a review document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document("API Review", Chapter("Notes", *obj.to_notes_blocks()))
            ```
        """

        from oodocs.apidoc.blocks import api_notes_blocks

        return api_notes_blocks(self, profile)

    def to_warnings_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for parsed warning notes.

        Args:
            profile: Presentation profile name or object.

        Returns:
            OODocs warning blocks for parsed warning notes.

        Examples:
            Surface parsed warnings in release evidence:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document("Evidence", Chapter("Warnings", *obj.to_warnings_blocks()))
            ```
        """

        from oodocs.apidoc.blocks import api_warnings_blocks

        return api_warnings_blocks(self, profile)

    def to_renderer_notes_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for renderer-specific notes.

        Args:
            profile: Presentation profile name or object.

        Returns:
            OODocs blocks for parsed renderer-specific notes.

        Examples:
            Include renderer notes in a compatibility report:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document(
                "Compatibility",
                Chapter("Renderer Notes", *obj.to_renderer_notes_blocks()),
            )
            ```
        """

        from oodocs.apidoc.blocks import api_renderer_notes_blocks

        return api_renderer_notes_blocks(self, profile)

    def to_blocks(
        self,
        *,
        profile: object = "reference",
        level: int = 2,
        max_level: int | None = None,
    ) -> list[object]:
        """Return OODocs blocks representing this object.

        Args:
            profile: Presentation profile name or object.
            level: Heading level used for nested member sections.
            max_level: Optional deepest heading level to render for nested
                member sections.

        Returns:
            Renderer-neutral OODocs block list.

        Examples:
            Insert one API object into an existing chapter without adding a new
            heading:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.find("mypkg.load")
            assert obj is not None
            doc = Document("API Notes", Chapter("load", *obj.to_blocks(profile="manual")))
            ```
        """

        from oodocs.apidoc.blocks import api_object_to_blocks

        return api_object_to_blocks(
            self,
            profile=profile,
            level=level,
            max_level=max_level,
        )

    def to_section(
        self,
        *,
        level: int = 2,
        profile: object = "reference",
        title: str | None = None,
        max_level: int | None = None,
    ):
        """Return this object as a section.

        Args:
            level: Section heading level.
            profile: Presentation profile name or object.
            title: Optional heading override.
            max_level: Optional deepest heading level to render for nested
                member sections.

        Returns:
            OODocs ``Section``/``Chapter`` appropriate for ``level``.

        Examples:
            Compose selected classes into a normal OODocs document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            classes = api.select(kind="class", module_prefix="mypkg.widgets")
            doc = Document(
                "Widget API",
                Chapter("Classes", *[item.to_section(level=2) for item in classes]),
            )
            ```
        """

        from oodocs.apidoc.blocks import api_object_to_section

        return api_object_to_section(
            self,
            level=level,
            profile=profile,
            title=title,
            max_level=max_level,
        )

    def to_compact_box(self, profile: object = "compact"):
        """Return this object as a compact OODocs box.

        Args:
            profile: Presentation profile name or object.

        Returns:
            OODocs box with the object summary and optional signature.

        Examples:
            Add a compact API callout to a guide chapter:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            obj = api.functions()[0]
            doc = Document("Guide", Chapter("Related API", obj.to_compact_box()))
            ```
        """

        from oodocs.apidoc.blocks import api_object_to_compact_box

        return api_object_to_compact_box(self, profile=profile)

    def to_index_row(self) -> list[object]:
        """Return a row suitable for API index tables.

        Returns:
            ``[kind, qualname, module, location, summary]``.

        Examples:
            Build a custom API index table:

            ```python
            from oodocs import Table
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            rows = [obj.to_index_row() for obj in api.public_objects()]
            table = Table(["Kind", "Name", "Module", "Location", "Summary"], rows)
            ```
        """

        location = ""
        if self.source_path:
            location = self.source_path
            if self.line_number is not None:
                location = f"{location}:{self.line_number}"
        return [self.kind, self.qualname, self.module, location, self.plain_summary()]

    def to_doc_issue_rows(self) -> list[list[object]]:
        """Return issue rows stored on this object metadata.

        Returns:
            Rows converted from parser or merge diagnostics stored in
            ``metadata["issues"]``.

        Examples:
            Add object-local parser diagnostics to a review table:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".", docstring_style="google")
            obj = api.functions()[0]
            issue_rows = obj.to_doc_issue_rows()
            ```
        """

        rows: list[list[object]] = []
        for item in self.metadata.get("issues", []):
            if isinstance(item, dict):
                rows.append(ApiDocIssue.from_dict(item).to_row())
        return rows

    def to_issue_rows(self) -> list[list[object]]:
        """Return object-local diagnostics as stable issue table rows.

        This is the public, checklist-aligned alias for
        ``to_doc_issue_rows()``. It preserves the same row shape used by
        ``ApiPackage.to_issue_table(...)`` and coverage CSV sidecars.

        Returns:
            Rows converted from parser or collection diagnostics stored in this
            object's metadata.

        Examples:
            Insert object-local parser issues into a custom evidence document:

            ```python
            from oodocs import Chapter, Document, Table
            from oodocs.apidoc import collect_api

            api = collect_api(".", docstring_style="google")
            obj = api.functions()[0]
            rows = obj.to_issue_rows()
            doc = Document(
                "API Evidence",
                Chapter(
                    "Parser Issues",
                    Table(
                        [
                            "Severity",
                            "Code",
                            "Object",
                            "Module",
                            "Location",
                            "Message",
                        ],
                        rows,
                    ),
                ),
            )
            ```
        """

        return self.to_doc_issue_rows()


@dataclass(slots=True)
class ApiModule:
    """API metadata for one Python module.

    Attributes:
        name: Module name.
        members: Module-level API objects.
        summary: Module docstring summary.
        description: Module docstring description.
        notes: Parsed module-level notes.
        warnings: Parsed module-level warning notes.
        renderer_notes: Parsed module-level renderer notes.
        source_path: Optional source file path.
        line_number: Optional module docstring line.
        end_line_number: Optional final source line.
        metadata: Extensible deterministic metadata.

    Examples:
        Add one collected module to a hand-authored API reference:

        ```python
        from oodocs import Document
        from oodocs.apidoc import collect_api

        api = collect_api(".")
        module = api.modules_by_name()["mypkg.widgets"]
        doc = Document("Widget API", module.to_chapter(profile="reference"))
        ```
    """

    name: str
    members: list[ApiObject] = field(default_factory=list)
    summary: str | None = None
    description: str | None = None
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    renderer_notes: list[ApiRendererNote] = field(default_factory=list)
    source_path: str | None = None
    line_number: int | None = None
    end_line_number: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def objects(self) -> list[ApiObject]:
        """Return module-level API objects.

        Returns:
            The module's top-level API objects.

        Examples:
            Build a compact module summary from top-level objects only:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            doc = Document("Module Summary", Chapter("Objects", module.to_summary_table(module.objects)))
            ```
        """

        return self.members

    @property
    def qualname(self) -> str:
        """Return the module qualname.

        Returns:
            Fully qualified module name.

        Examples:
            Use module qualnames as stable generated chapter titles:

            ```python
            from oodocs import Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            chapters = [
                module.to_chapter(title=module.qualname)
                for module in api
            ]
            doc = Document("API Reference", *chapters)
            ```
        """

        return self.name

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-compatible module payload containing members, module
            docstring metadata, source locations, and renderer metadata.

        Examples:
            Store one module payload inside a custom review artifact:

            ```python
            import json
            from pathlib import Path
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            Path("build/widgets-api.json").write_text(
                json.dumps(module.to_dict(), indent=2),
                encoding="utf-8",
            )
            ```
        """

        return {
            "name": self.name,
            "members": [member.to_dict() for member in self.members],
            "summary": self.summary,
            "description": self.description,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "renderer_notes": [item.to_dict() for item in self.renderer_notes],
            "source_path": self.source_path,
            "line_number": self.line_number,
            "end_line_number": self.end_line_number,
            "metadata": _jsonable_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiModule:
        """Reconstruct a module from serialized data.

        Args:
            data: Payload previously returned by ``to_dict``.

        Returns:
            Reconstructed module metadata object.

        Examples:
            Load a cached module payload and render it without recollecting
            source files:

            ```python
            import json
            from pathlib import Path
            from oodocs import Document
            from oodocs.apidoc.model import ApiModule

            payload = json.loads(Path("build/widgets-api.json").read_text())
            module = ApiModule.from_dict(payload)
            doc = Document("Widget API", module.to_chapter())
            ```
        """

        return cls(
            name=str(data["name"]),
            members=[
                ApiObject.from_dict(item)
                for item in data.get("members", [])  # type: ignore[union-attr]
            ],
            summary=_optional_str(data.get("summary")),
            description=_optional_str(data.get("description")),
            notes=[str(item) for item in data.get("notes", [])],  # type: ignore[union-attr]
            warnings=[str(item) for item in data.get("warnings", [])],  # type: ignore[union-attr]
            renderer_notes=[
                ApiRendererNote.from_dict(item)
                for item in data.get("renderer_notes", [])  # type: ignore[union-attr]
            ],
            source_path=_optional_str(data.get("source_path")),
            line_number=_optional_int(data.get("line_number")),
            end_line_number=_optional_int(data.get("end_line_number")),
            metadata=dict(data.get("metadata", {})),  # type: ignore[arg-type]
        )

    def classes(self) -> list[ApiObject]:
        """Return module-level classes.

        Returns:
            Public and private top-level class objects in this module,
            according to the collected module data.

        Examples:
            Render only class reference sections for a single module:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            doc = Document(
                "Widget Classes",
                Chapter("Classes", *[cls.to_section(level=2) for cls in module.classes()]),
            )
            ```
        """

        return self.select(kind="class", recursive=False)

    def functions(self) -> list[ApiObject]:
        """Return module-level functions.

        Returns:
            Top-level function objects in this module.

        Examples:
            Put module functions into a quick function index:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            functions = module.functions()
            doc = Document("Widget Functions", Chapter("Index", module.to_summary_table(functions)))
            ```
        """

        return self.select(kind="function", recursive=False)

    def attributes(self) -> list[ApiObject]:
        """Return module-level attributes and data objects.

        Returns:
            Top-level attributes and data objects in this module.

        Examples:
            Document constants separately from functions and classes:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.settings"]
            doc = Document(
                "Settings API",
                Chapter("Constants", module.to_summary_table(module.attributes())),
            )
            ```
        """

        return self.select(kind=("attribute", "data"), recursive=False)

    def properties(self) -> list[ApiObject]:
        """Return properties from module classes.

        Returns:
            Property objects collected from classes in this module.

        Examples:
            Add an appendix of computed attributes for one module:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            properties = module.properties()
            doc = Document("Widget Properties", Chapter("Properties", module.to_summary_table(properties)))
            ```
        """

        return self.select(kind="property", recursive=True)

    def iter_objects(
        self,
        kind: str | Iterable[str] | None = None,
        *,
        recursive: bool = True,
    ) -> Iterator[ApiObject]:
        """Iterate module objects.

        Args:
            kind: Optional kind or kinds to include.
            recursive: Whether to include nested members.

        Yields:
            Matching objects in source order.

        Examples:
            Generate sections for every class and method in one module:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            sections = [
                obj.to_section(level=2)
                for obj in module.iter_objects(kind=("class", "method"))
            ]
            doc = Document("Widget API", Chapter("Objects", *sections))
            ```
        """

        kinds = _normalize_kind_filter(kind)
        for member in self.members:
            if kinds is None or member.kind in kinds:
                yield member
            if recursive:
                yield from member.iter_members(kind, recursive=True)

    def select(
        self,
        *,
        kind: str | Iterable[str] | None = None,
        visibility: str | None = None,
        documented: bool | None = None,
        deprecated: bool | None = None,
        recursive: bool = True,
    ) -> list[ApiObject]:
        """Return filtered module objects.

        Args:
            kind: Optional kind or kinds to include.
            visibility: Optional visibility classification to include.
            documented: Optional documentation-state filter.
            deprecated: Optional deprecation-state filter.
            recursive: Whether to include nested members.

        Returns:
            Objects that match all supplied filters.

        Examples:
            Build a focused public class table for one module:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            public_classes = module.select(kind="class", visibility="public")
            doc = Document("Widget Classes", Chapter("Summary", module.to_summary_table(public_classes)))
            ```
        """

        return [
            obj
            for obj in self.iter_objects(kind, recursive=recursive)
            if _matches_object(
                obj,
                visibility=visibility,
                documented=documented,
                deprecated=deprecated,
            )
        ]

    def find(self, qualname_or_name: str) -> ApiObject | None:
        """Find an object by qualname or name.

        Args:
            qualname_or_name: Fully qualified object name or local object name.

        Returns:
            Matching API object, or ``None`` when no object matches. Passing
            this module's name returns ``None`` because the receiver already
            represents the module.

        Examples:
            Find a class before inserting just that class into a document:

            ```python
            from oodocs import Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            widget = module.find("Widget")
            doc = Document("Widget", widget.to_section(level=1)) if widget else None
            ```
        """

        if qualname_or_name == self.name:
            return None
        for obj in self.iter_objects(recursive=True):
            if qualname_or_name in {obj.qualname, obj.name}:
                return obj
        return None

    def to_summary_table(self, objects: Sequence[ApiObject] | None = None, **kwargs):
        """Return a summary table for module objects.

        Args:
            objects: Optional objects to summarize. Defaults to all recursive
                objects in this module.
            **kwargs: Additional options forwarded to
                ``api_objects_to_summary_table``.

        Returns:
            OODocs table summarizing the selected module objects.

        Examples:
            Add a module object index before detailed sections:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            doc = Document(
                "Widget API",
                Chapter("Index", module.to_summary_table(caption="Widget symbols")),
                module.to_chapter(),
            )
            ```
        """

        from oodocs.apidoc.blocks import api_objects_to_summary_table

        return api_objects_to_summary_table(objects or list(self.iter_objects()), **kwargs)

    def to_sections(
        self,
        *,
        profile: object = "reference",
        level: int = 2,
        max_level: int | None = None,
    ) -> list[object]:
        """Return module objects as OODocs sections.

        Args:
            profile: Presentation profile name or object.
            level: Heading level for top-level module members.
            max_level: Optional deepest heading level for nested API members.

        Returns:
            OODocs sections for this module's top-level members.

        Examples:
            Embed module member sections inside a larger chapter:

            ```python
            from oodocs import Chapter, Document, Paragraph
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            doc = Document(
                "Developer Guide",
                Chapter("Widget API", Paragraph("Public widget surface."), *module.to_sections(level=2)),
            )
            ```
        """

        return [
            obj.to_section(level=level, profile=profile, max_level=max_level)
            for obj in self.members
        ]

    def to_chapter(
        self,
        *,
        profile: object = "reference",
        title: str | None = None,
        max_level: int | None = None,
    ):
        """Return this module as an OODocs chapter.

        Args:
            profile: Presentation profile name or object.
            title: Optional chapter title. Defaults to the module name.
            max_level: Optional deepest heading level for nested API members.

        Returns:
            OODocs chapter representing this module.

        Examples:
            Render a standalone document for a single collected module:

            ```python
            from oodocs import Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            doc = Document("Widget Module", module.to_chapter(title="mypkg.widgets"))
            ```
        """

        from oodocs.apidoc.blocks import api_module_to_chapter

        return api_module_to_chapter(
            self,
            profile=profile,
            title=title,
            max_level=max_level,
        )

    def to_blocks(
        self,
        *,
        profile: object = "reference",
        level: int = 2,
        max_level: int | None = None,
    ) -> list[object]:
        """Return this module as renderer-neutral blocks.

        Args:
            profile: Presentation profile name or object.
            level: Heading level for the module title or top-level members.
            max_level: Optional deepest heading level for nested API members.

        Returns:
            Renderer-neutral OODocs blocks for insertion into an existing
            document.

        Examples:
            Append generated module reference blocks after narrative content:

            ```python
            from oodocs import Document, Paragraph
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            doc = Document("Widget Guide", Paragraph("Usage notes."), *module.to_blocks(level=2))
            ```
        """

        from oodocs.apidoc.blocks import api_module_to_blocks

        return api_module_to_blocks(
            self,
            profile=profile,
            level=level,
            max_level=max_level,
        )


@dataclass(slots=True)
class ApiPackage:
    """Collected API metadata for a Python package or repository.

    Attributes:
        name: Package or project name.
        version: Optional package version.
        modules: Collected modules.
        issues: Collection, parsing, and coverage issues.
        metadata: Extensible deterministic metadata.

    Examples:
        Query, compose, and render selected API objects:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api

        api = collect_api("oodocs", public_policy="__all__")
        functions = api.select(kind="function")
        doc = Document(
            "Function API",
            Chapter("Summary", api.to_summary_table(functions)),
        )
        ```

        Persist the collected API sidecar for a later documentation build:

        ```python
        from oodocs.apidoc import ApiPackage, collect_api

        collect_api(".").write_json("build/api.json")
        api = ApiPackage.read_json("build/api.json")
        doc = api.to_document("API Reference")
        ```
    """

    name: str
    version: str | None = None
    modules: list[ApiModule] = field(default_factory=list)
    issues: list[ApiDocIssue] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def __iter__(self) -> Iterator[ApiModule]:
        """Iterate modules in deterministic order."""

        return iter(self.modules)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-compatible package payload containing modules, collected
            issues, version metadata, and extensible metadata.

        Examples:
            Embed API metadata in a build artifact alongside rendered docs:

            ```python
            import json
            from pathlib import Path
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            Path("build/api-package.json").write_text(
                json.dumps(api.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            doc = api.to_document("API Reference")
            ```
        """

        return {
            "name": self.name,
            "version": self.version,
            "modules": [module.to_dict() for module in self.modules],
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": _jsonable_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiPackage:
        """Reconstruct a package from serialized data.

        Args:
            data: Payload previously returned by ``to_dict``.

        Returns:
            Reconstructed API package object.

        Examples:
            Rebuild a package object from a CI-generated payload and render it:

            ```python
            import json
            from pathlib import Path
            from oodocs.apidoc import ApiPackage

            payload = json.loads(Path("build/api-package.json").read_text())
            api = ApiPackage.from_dict(payload)
            doc = api.to_document("API Reference", include_coverage=True)
            ```
        """

        return cls(
            name=str(data["name"]),
            version=_optional_str(data.get("version")),
            modules=[
                ApiModule.from_dict(item)
                for item in data.get("modules", [])  # type: ignore[union-attr]
            ],
            issues=[
                ApiDocIssue.from_dict(item)
                for item in data.get("issues", [])  # type: ignore[union-attr]
            ],
            metadata=dict(data.get("metadata", {})),  # type: ignore[arg-type]
        )

    def write_json(self, path: PathLike) -> Path:
        """Write this API package as deterministic JSON.

        Args:
            path: Output JSON path.

        Returns:
            Written path.

        Examples:
            Save a sidecar next to generated API reference outputs:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".", collector="griffe")
            sidecar_path = api.write_json("build/api/objects.json")
            doc = api.to_document("API Reference")
            ```
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def read_json(cls, path: PathLike) -> ApiPackage:
        """Read an API package JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            API package object.

        Examples:
            Render API reference from a previously collected sidecar:

            ```python
            from oodocs.apidoc import ApiPackage

            api = ApiPackage.read_json("build/api/objects.json")
            doc = api.to_document("API Reference", profile="reference")
            ```
        """

        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def iter_objects(
        self,
        kind: str | Iterable[str] | None = None,
        *,
        recursive: bool = True,
    ) -> Iterator[ApiObject]:
        """Iterate collected objects.

        Args:
            kind: Optional kind or kinds to include.
            recursive: Whether to include class/member descendants.

        Yields:
            Matching objects in module and source order.

        Examples:
            Build an index from every collected public class and method:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            objects = list(api.iter_objects(kind=("class", "method")))
            doc = Document("API Index", Chapter("Objects", api.to_summary_table(objects)))
            ```
        """

        for module in self.modules:
            yield from module.iter_objects(kind, recursive=recursive)

    def select(
        self,
        *,
        kind: str | Iterable[str] | None = None,
        module: str | None = None,
        module_prefix: str | None = None,
        visibility: str | None = "public",
        documented: bool | None = None,
        deprecated: bool | None = None,
        recursive: bool = True,
    ) -> list[ApiObject]:
        """Return filtered API objects.

        Args:
            kind: Optional kind or kinds to include.
            module: Optional exact module name.
            module_prefix: Optional module prefix.
            visibility: Optional visibility to include. Defaults to public.
            documented: Optional documentation-state filter.
            deprecated: Optional deprecation-state filter.
            recursive: Whether to include nested members.

        Returns:
            Matching API objects.

        Examples:
            Render a focused reference for one package namespace:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            widgets = api.select(
                kind=("class", "function"),
                module_prefix="mypkg.widgets",
                visibility="public",
            )
            doc = Document("Widget API", Chapter("Summary", api.to_summary_table(widgets)))
            ```
        """

        selected: list[ApiObject] = []
        for api_module in self.modules:
            if module is not None and api_module.name != module:
                continue
            if module_prefix is not None and not api_module.name.startswith(module_prefix):
                continue
            selected.extend(
                api_module.select(
                    kind=kind,
                    visibility=visibility,
                    documented=documented,
                    deprecated=deprecated,
                    recursive=recursive,
                )
            )
        return selected

    def filtered(
        self,
        *,
        kind: str | Iterable[str] | None = None,
        module: str | None = None,
        module_prefix: str | None = None,
        visibility: str | None = "public",
        documented: bool | None = None,
        deprecated: bool | None = None,
        recursive: bool = True,
    ) -> ApiPackage:
        """Return a package containing only matching API objects.

        Args:
            kind: Optional kind or kinds to include.
            module: Optional exact module name.
            module_prefix: Optional module prefix.
            visibility: Optional visibility to include. Defaults to public.
            documented: Optional documentation-state filter.
            deprecated: Optional deprecation-state filter.
            recursive: Whether to include nested members.

        Returns:
            New package with filtered module members and matching issues.

        Examples:
            Build a coverage gate for only public classes in one package area:

            ```python
            from oodocs.apidoc import check_api_docs, collect_api

            api = collect_api(".")
            coverage = check_api_docs(
                api.filtered(kind="class", module_prefix="mypkg.widgets")
            )
            ```
        """

        selected = self.select(
            kind=kind,
            module=module,
            module_prefix=module_prefix,
            visibility=visibility,
            documented=documented,
            deprecated=deprecated,
            recursive=recursive,
        )
        selected = _drop_descendants_of_selected_objects(selected)
        modules_by_name = self.modules_by_name()
        grouped: dict[str, list[ApiObject]] = {}
        selected_qualnames: set[str] = set()
        for obj in selected:
            grouped.setdefault(obj.module, []).append(ApiObject.from_dict(obj.to_dict()))
            selected_qualnames.add(obj.qualname)
            selected_qualnames.update(member.qualname for member in obj.iter_members(recursive=True))
        filtered_modules: list[ApiModule] = []
        for module_name in sorted(grouped):
            source_module = modules_by_name.get(module_name)
            filtered_modules.append(
                ApiModule(
                    name=module_name,
                    members=sorted(grouped[module_name], key=lambda obj: (obj.line_number or 0, obj.name)),
                    summary=source_module.summary if source_module else None,
                    description=source_module.description if source_module else None,
                    notes=list(source_module.notes) if source_module else [],
                    warnings=list(source_module.warnings) if source_module else [],
                    renderer_notes=list(source_module.renderer_notes) if source_module else [],
                    source_path=source_module.source_path if source_module else None,
                    line_number=source_module.line_number if source_module else None,
                    end_line_number=source_module.end_line_number if source_module else None,
                    metadata=dict(source_module.metadata) if source_module else {},
                )
            )
        included_modules = set(grouped)
        filtered_issues = [
            issue
            for issue in self.issues
            if _issue_matches_filtered_package(issue, selected_qualnames, included_modules)
        ]
        metadata = dict(self.metadata)
        metadata["filters"] = {
            "kind": sorted(_normalize_kind_filter(kind) or []),
            "module": module,
            "module_prefix": module_prefix,
            "visibility": visibility,
            "documented": documented,
            "deprecated": deprecated,
            "recursive": recursive,
        }
        return ApiPackage(
            self.name,
            version=self.version,
            modules=filtered_modules,
            issues=filtered_issues,
            metadata=metadata,
        )

    def find(self, qualname_or_name: str) -> ApiObject | ApiModule | None:
        """Find a module or object by qualname or local name.

        Args:
            qualname_or_name: Fully qualified module/object name or local
                object name.

        Returns:
            Matching module or API object, or ``None`` when no item matches.

        Examples:
            Locate one object and render only its reference section:

            ```python
            from oodocs import Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            item = api.find("mypkg.widgets.Widget")
            doc = Document("Widget", item.to_section(level=1)) if item else None
            ```
        """

        for module in self.modules:
            if module.name == qualname_or_name:
                return module
            if found := module.find(qualname_or_name):
                return found
        return None

    def modules_by_name(self) -> dict[str, ApiModule]:
        """Return modules keyed by module name.

        Returns:
            Mapping from module name to ``ApiModule``.

        Examples:
            Render one collected module as its own API document:

            ```python
            from oodocs import Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            module = api.modules_by_name()["mypkg.widgets"]
            Document("Widgets API", module.to_chapter(profile="reference")).save_html(
                "widgets.html"
            )
            ```
        """

        return {module.name: module for module in self.modules}

    def classes(self) -> list[ApiObject]:
        """Return public classes.

        Returns:
            Public class objects across collected modules.

        Examples:
            Insert class sections into a hand-authored guide:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document(
                "Class Guide",
                Chapter("Classes", *[item.to_section(level=2) for item in api.classes()]),
            )
            ```
        """

        return self.select(kind="class")

    def functions(self) -> list[ApiObject]:
        """Return public functions.

        Returns:
            Public function objects across collected modules.

        Examples:
            Add a public function summary to a package reference:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document(
                "Function Reference",
                Chapter("Functions", api.to_summary_table(api.functions())),
            )
            ```
        """

        return self.select(kind="function")

    def methods(self) -> list[ApiObject]:
        """Return public methods.

        Returns:
            Public method objects from collected classes.

        Examples:
            Review method-level documentation coverage in a generated appendix:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            methods = api.methods()
            doc = Document("Method API", Chapter("Methods", api.to_summary_table(methods)))
            ```
        """

        return self.select(kind="method")

    def attributes(self) -> list[ApiObject]:
        """Return public attributes and data objects.

        Returns:
            Public module attributes, class attributes, and data objects.

        Examples:
            Render constants and data objects as a separate reference chapter:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document(
                "Data API",
                Chapter("Attributes", api.to_summary_table(api.attributes())),
            )
            ```
        """

        return self.select(kind=("attribute", "data"))

    def properties(self) -> list[ApiObject]:
        """Return public properties.

        Returns:
            Public property objects from collected classes.

        Examples:
            Build a computed-attribute appendix across the whole package:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            properties = api.properties()
            doc = Document(
                "Property API",
                Chapter("Properties", api.to_summary_table(properties)),
            )
            ```
        """

        return self.select(kind="property")

    def public_objects(self) -> list[ApiObject]:
        """Return all public API objects.

        Returns:
            Public objects matching the configured public API boundary.

        Examples:
            Create the default public API index for a documentation bundle:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".", public_policy="__all__")
            doc = Document(
                "Public API",
                Chapter("Index", api.to_summary_table(api.public_objects())),
            )
            ```
        """

        return self.select(visibility="public")

    def private_objects(self) -> list[ApiObject]:
        """Return private or protected API objects.

        Returns:
            Objects classified as private, protected, or internal.

        Examples:
            Build an internal review report without publishing private details:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            private_api = api.private_objects()
            doc = Document("Internal API Review", Chapter("Private Objects", api.to_summary_table(private_api)))
            ```
        """

        return [
            obj
            for obj in self.iter_objects(recursive=True)
            if obj.visibility in {"private", "protected", "internal"}
        ]

    def undocumented_public_objects(self) -> list[ApiObject]:
        """Return public API objects without docstring summary or description.

        Returns:
            Public API objects whose parsed docstring has no summary or
            description.

        Examples:
            Build a review appendix listing missing docs:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            missing = api.undocumented_public_objects()
            doc = Document("Doc Review", Chapter("Missing Docs", api.to_summary_table(missing)))
            ```
        """

        return self.select(visibility="public", documented=False)

    def iter_issues(self, *, include_object_issues: bool = True) -> Iterator[ApiDocIssue]:
        """Iterate package and object-level diagnostics.

        Args:
            include_object_issues: Whether to include parser/merge issues
                stored on collected API objects.

        Yields:
            Package issues followed by object metadata issues in deterministic
            object order.

        Examples:
            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".", docstring_style="google")
            style_warnings = [
                issue for issue in api.iter_issues()
                if issue.code == "docstring-style-mismatch"
            ]
            ```
        """

        yield from self.issues
        if not include_object_issues:
            return
        for obj in self.iter_objects(recursive=True):
            for item in obj.metadata.get("issues", []):
                if isinstance(item, dict):
                    yield ApiDocIssue.from_dict(item)

    def to_summary_table(
        self,
        objects: Sequence[ApiObject] | None = None,
        **kwargs,
    ):
        """Return a package-level API summary table.

        Args:
            objects: Optional objects to include. Defaults to all public
                objects.
            **kwargs: Additional options forwarded to
                ``api_objects_to_summary_table``, such as ``profile`` or
                ``caption``.

        Returns:
            OODocs table summarizing selected API objects.

        Examples:
            Add a public function index to a release document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            functions = api.select(kind="function")
            doc = Document(
                "Release Evidence",
                Chapter(
                    "Function Index",
                    api.to_summary_table(functions, profile="compact"),
                ),
            )
            ```
        """

        from oodocs.apidoc.blocks import api_objects_to_summary_table

        return api_objects_to_summary_table(objects or self.public_objects(), **kwargs)

    def to_modules_table(self, *, caption: str | None = None):
        """Return a table summarizing collected modules.

        Args:
            caption: Optional table caption.

        Returns:
            OODocs table containing module names, object counts, and module
            summaries.

        Examples:
            Start a package reference with a module inventory:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document(
                "API Reference",
                Chapter("Modules", api.to_modules_table(caption="Collected modules")),
                *api.to_chapters(),
            )
            ```
        """

        from oodocs.components.media import Table

        rows = [
            [module.name, str(len(module.members)), module.summary or ""]
            for module in self.modules
        ]
        return Table(["Module", "Objects", "Summary"], rows, caption=caption, split=True)

    def to_issue_table(
        self,
        *,
        caption: str | None = None,
        include_object_issues: bool = True,
    ):
        """Return collected issues as an OODocs table.

        Args:
            caption: Optional table caption.
            include_object_issues: Whether to include parser/merge diagnostics
                stored on API objects.

        Returns:
            OODocs table with package and object-level diagnostics.

        Examples:
            Include parser and coverage diagnostics in an evidence document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".", docstring_style="google")
            doc = Document(
                "API Evidence",
                Chapter("Diagnostics", api.to_issue_table(caption="API issues")),
            )
            ```
        """

        from oodocs.components.media import Table

        return Table(
            ["Severity", "Code", "Object", "Module", "Location", "Message"],
            [
                issue.to_row()
                for issue in self.iter_issues(
                    include_object_issues=include_object_issues
                )
            ],
            caption=caption,
            split=True,
        )

    def to_coverage_table(self, **kwargs):
        """Return documentation coverage summary as an OODocs table.

        Args:
            **kwargs: Options forwarded to ``check_api_docs``, such as
                ``fail_under`` or ``require_examples``.

        Returns:
            OODocs coverage metric table.

        Examples:
            Include coverage metrics in an evidence document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document("API Evidence", Chapter("Coverage", api.to_coverage_table()))
            ```
        """

        from oodocs.apidoc.coverage import check_api_docs

        return check_api_docs(self, **kwargs).to_table()

    def to_sections(
        self,
        *,
        profile: object = "reference",
        level: int = 1,
        max_level: int | None = None,
    ) -> list[object]:
        """Return modules as OODocs sections.

        Args:
            profile: Presentation profile name or object.
            level: Heading level for module sections. ``1`` returns chapters.
            max_level: Optional deepest heading level for nested API members.

        Returns:
            OODocs section or chapter blocks for collected modules.

        Examples:
            Compose package API sections inside a custom guide chapter:

            ```python
            from oodocs import Chapter, Document, Paragraph
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document(
                "Developer Guide",
                Chapter("API", Paragraph("Generated reference."), *api.to_sections(level=2)),
            )
            ```
        """

        if level == 1:
            return [
                module.to_chapter(profile=profile, max_level=max_level)
                for module in self.modules
            ]
        sections: list[object] = []
        for module in self.modules:
            sections.extend(
                module.to_sections(
                    profile=profile,
                    level=level,
                    max_level=max_level,
                )
            )
        return sections

    def to_chapters(
        self,
        *,
        profile: object = "reference",
        max_level: int | None = None,
    ) -> list[object]:
        """Return modules as OODocs chapters.

        Args:
            profile: Presentation profile name or object.
            max_level: Optional deepest heading level for nested API members.

        Returns:
            List of OODocs chapters, one per collected module.

        Examples:
            Render each collected module as a top-level document chapter:

            ```python
            from oodocs import Document
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document("API Reference", *api.to_chapters(max_level=3))
            ```
        """

        from oodocs.apidoc.blocks import api_package_to_chapters

        return api_package_to_chapters(
            self,
            profile=profile,
            max_level=max_level,
        )

    def to_blocks(
        self,
        *,
        profile: object = "reference",
        max_level: int | None = None,
    ) -> list[object]:
        """Return this package as renderer-neutral OODocs blocks.

        Args:
            profile: Presentation profile name or object.
            max_level: Optional deepest heading level for nested API members.

        Returns:
            OODocs blocks suitable for insertion into an existing document.

        Examples:
            Append a package API appendix to a custom document:

            ```python
            from oodocs import Document, Paragraph
            from oodocs.apidoc import collect_api

            api = collect_api(".")
            doc = Document("Guide", Paragraph("Usage notes."), *api.to_blocks())
            ```
        """

        return self.to_chapters(profile=profile, max_level=max_level)

    def to_document(
        self,
        title: str | None = None,
        *,
        profile: object = "reference",
        settings: object | None = None,
        citations: object | None = None,
        include_coverage: bool = True,
        include_modules: bool = True,
        max_level: int | None = None,
    ):
        """Return this package as a complete OODocs document.

        Args:
            title: Optional document title.
            profile: Presentation profile name or object.
            settings: Optional ``DocumentSettings``.
            citations: Optional citation library.
            include_coverage: Whether to include a coverage overview chapter.
            include_modules: Whether to include module chapters.
            max_level: Optional deepest heading level to render and include
                in the table of contents.

        Returns:
            OODocs ``Document``.

        Examples:
            Render a complete API reference bundle for a general Python repo:

            ```python
            from oodocs.apidoc import collect_api

            api = collect_api(".", collector="griffe", public_policy="__all__")
            api.to_document(profile="reference", max_level=3).save_all(
                "artifacts/api",
                stem=f"{api.name}-api",
            )
            ```

            Render only coverage evidence from the same collected tree:

            ```python
            evidence = api.to_document(
                title="API Documentation Evidence",
                include_modules=False,
            )
            evidence.save_docx("artifacts/api-evidence.docx")
            ```
        """

        from oodocs.apidoc.render import api_package_to_document

        return api_package_to_document(
            self,
            title=title,
            profile=profile,
            settings=settings,
            citations=citations,
            include_coverage=include_coverage,
            include_modules=include_modules,
            max_level=max_level,
        )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _normalize_kind_filter(kind: str | Iterable[str] | None) -> set[str] | None:
    if kind is None:
        return None
    if isinstance(kind, str):
        return {kind}
    return set(kind)


def _drop_descendants_of_selected_objects(objects: Sequence[ApiObject]) -> list[ApiObject]:
    kept: list[ApiObject] = []
    parent_prefixes: list[str] = []
    for obj in sorted(objects, key=lambda item: (item.qualname.count("."), item.qualname)):
        if any(obj.qualname.startswith(prefix) for prefix in parent_prefixes):
            continue
        kept.append(obj)
        if obj.has_members():
            parent_prefixes.append(f"{obj.qualname}.")
    return kept


def _issue_matches_filtered_package(
    issue: ApiDocIssue,
    selected_qualnames: set[str],
    included_modules: set[str],
) -> bool:
    if issue.qualname:
        return issue.qualname in selected_qualnames or any(
            qualname.startswith(f"{issue.qualname}.")
            for qualname in selected_qualnames
        )
    return bool(issue.module and issue.module in included_modules)


def _matches_object(
    obj: ApiObject,
    *,
    visibility: str | None,
    documented: bool | None,
    deprecated: bool | None,
) -> bool:
    if visibility is not None and obj.visibility != visibility:
        return False
    if documented is not None and obj.documented != documented:
        return False
    if deprecated is not None and obj.deprecated != deprecated:
        return False
    return True


def _anchor_id(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-")
    return text.replace(".", "-").lower() or "api-object"


def _first_sentence(value: str) -> str:
    match = re.match(r"(.+?[.!?])(?:\s|$)", value.strip(), flags=re.DOTALL)
    if match:
        return " ".join(match.group(1).split())
    return " ".join(value.strip().split())


def _normalize_issue_code(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "api-doc-issue"


def _xml_safe_text(value: str) -> str:
    chars: list[str] = []
    for char in value:
        codepoint = ord(char)
        if char in {"\t", "\n", "\r"}:
            chars.append(char)
        elif codepoint < 32 or 0x7F <= codepoint <= 0x9F:
            chars.append(f"\\x{codepoint:02x}")
        else:
            chars.append(char)
    return "".join(chars)


def _jsonable_metadata(metadata: dict[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(metadata, sort_keys=True, default=str))


__all__ = [
    "ApiDocIssue",
    "ApiDocIssueSeverity",
    "ApiDocstringStyleName",
    "ApiExample",
    "ApiKind",
    "ApiModule",
    "ApiObject",
    "ApiPackage",
    "ApiParameter",
    "ApiPresentationProfileName",
    "ApiRaises",
    "ApiRendererNote",
    "ApiReturn",
    "ApiSeeAlso",
    "ApiVisibility",
]
