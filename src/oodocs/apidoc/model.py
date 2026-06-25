"""Structured API documentation object model."""

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
        """

        if self.default in {None, "", str(_empty), str(MISSING)}:
            return ""
        return str(self.default)

    def display_annotation(self) -> str:
        """Return normalized annotation text for display.

        Returns:
            Empty string when no annotation is known.
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
        """

        return self.to_table_cell_values(columns)

    def to_paragraph(self):
        """Return a compact paragraph describing this parameter.

        Returns:
            ``oodocs.Paragraph`` containing the parameter name and description.
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
        """Return deterministic serialized data."""

        return {
            "annotation": self.annotation,
            "description": self.description,
            "documented": self.documented,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiReturn:
        """Reconstruct return metadata from serialized data."""

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
    """

    exception: str
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data."""

        return {"exception": self.exception, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiRaises:
        """Reconstruct exception metadata from serialized data."""

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
        """Return deterministic serialized data."""

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
        """Reconstruct example metadata from serialized data."""

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
            ``oodocs.CodeBlock`` using the example language and code.
        """

        from oodocs.components.blocks import CodeBlock

        return CodeBlock(self.code, language=self.language or "text")


@dataclass(slots=True)
class ApiSeeAlso:
    """Related API reference parsed from a docstring.

    Attributes:
        label: Display label.
        target: Optional fully qualified target.
        description: Optional relationship description.
        kind: Optional target kind.
    """

    label: str
    target: str | None = None
    description: str | None = None
    kind: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data."""

        return {
            "label": self.label,
            "target": self.target,
            "description": self.description,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiSeeAlso:
        """Reconstruct see-also metadata from serialized data."""

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
    """

    format: Literal["docx", "pdf", "html"] | None
    message: str
    severity: Literal["info", "warning"] = "info"

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data."""

        return {
            "format": self.format,
            "message": self.message,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiRendererNote:
        """Reconstruct renderer-note metadata from serialized data."""

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
        """Return deterministic serialized data."""

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
        """Reconstruct an issue from serialized data."""

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
        """Return whether this object has user-facing documentation."""

        return bool(self.summary or self.description)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable object mapping.
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
        """

        if self.summary:
            return self.summary
        if self.description:
            return _first_sentence(self.description)
        return ""

    def display_name(self) -> str:
        """Return the display name used in headings and tables."""

        return self.qualname or self.name

    def display_signature(self) -> str:
        """Return callable signature text for code blocks."""

        if self.signature:
            return self.signature
        return self.display_name()

    def anchor_id(self) -> str:
        """Return a stable anchor id derived from the qualname."""

        return _anchor_id(self.qualname)

    def has_parameters(self) -> bool:
        """Return whether this object has parameter metadata."""

        return bool(self.parameters)

    def has_examples(self) -> bool:
        """Return whether this object has parsed examples."""

        return bool(self.examples)

    def has_members(self) -> bool:
        """Return whether this object has child objects."""

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
        """

        if qualname_or_name in {self.qualname, self.name}:
            return self
        for member in self.iter_members(recursive=True):
            if qualname_or_name in {member.qualname, member.name}:
                return member
        return None

    def to_summary_row(self, *, include_module: bool = True) -> list[object]:
        """Return an OODocs table row summarizing this object."""

        row: list[object] = [self.kind, self.display_name(), self.plain_summary()]
        if include_module:
            row.insert(1, self.module)
        return row

    def to_summary_paragraph(self):
        """Return a compact OODocs paragraph for this object."""

        from oodocs.apidoc.blocks import api_object_summary_paragraph

        return api_object_summary_paragraph(self)

    def to_signature_block(self, profile: object = "reference"):
        """Return this object's signature as an OODocs code block."""

        from oodocs.apidoc.blocks import api_signature_block

        return api_signature_block(self, profile)

    def to_parameter_table(self, profile: object = "reference"):
        """Return this object's parameter table, if parameters are available."""

        from oodocs.apidoc.blocks import api_parameter_table

        return api_parameter_table(self, profile)

    def to_returns_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks documenting return values."""

        from oodocs.apidoc.blocks import api_returns_blocks

        return api_returns_blocks(self, profile)

    def to_raises_table(self, profile: object = "reference"):
        """Return this object's raises table, if exceptions are documented."""

        from oodocs.apidoc.blocks import api_raises_table

        return api_raises_table(self, profile)

    def to_examples_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for examples."""

        from oodocs.apidoc.blocks import api_examples_blocks

        return api_examples_blocks(self, profile)

    def to_see_also_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for related API entries."""

        from oodocs.apidoc.blocks import api_see_also_blocks

        return api_see_also_blocks(self, profile)

    def to_renderer_notes_blocks(self, profile: object = "reference") -> list[object]:
        """Return OODocs blocks for renderer-specific notes."""

        from oodocs.apidoc.blocks import api_renderer_notes_blocks

        return api_renderer_notes_blocks(self, profile)

    def to_blocks(
        self,
        *,
        profile: object = "reference",
        level: int = 2,
    ) -> list[object]:
        """Return OODocs blocks representing this object.

        Args:
            profile: Presentation profile name or object.
            level: Heading level used for nested member sections.

        Returns:
            Renderer-neutral OODocs block list.
        """

        from oodocs.apidoc.blocks import api_object_to_blocks

        return api_object_to_blocks(self, profile=profile, level=level)

    def to_section(
        self,
        *,
        level: int = 2,
        profile: object = "reference",
        title: str | None = None,
    ):
        """Return this object as a section.

        Args:
            level: Section heading level.
            profile: Presentation profile name or object.
            title: Optional heading override.

        Returns:
            OODocs ``Section``/``Chapter`` appropriate for ``level``.
        """

        from oodocs.apidoc.blocks import api_object_to_section

        return api_object_to_section(self, level=level, profile=profile, title=title)

    def to_compact_box(self, profile: object = "compact"):
        """Return this object as a compact OODocs box."""

        from oodocs.apidoc.blocks import api_object_to_compact_box

        return api_object_to_compact_box(self, profile=profile)

    def to_index_row(self) -> list[object]:
        """Return a row suitable for API index tables."""

        location = ""
        if self.source_path:
            location = self.source_path
            if self.line_number is not None:
                location = f"{location}:{self.line_number}"
        return [self.kind, self.qualname, self.module, location, self.plain_summary()]

    def to_doc_issue_rows(self) -> list[list[object]]:
        """Return issue rows stored on this object metadata."""

        rows: list[list[object]] = []
        for item in self.metadata.get("issues", []):
            if isinstance(item, dict):
                rows.append(ApiDocIssue.from_dict(item).to_row())
        return rows


@dataclass(slots=True)
class ApiModule:
    """API metadata for one Python module.

    Attributes:
        name: Module name.
        members: Module-level API objects.
        summary: Module docstring summary.
        description: Module docstring description.
        source_path: Optional source file path.
        line_number: Optional module docstring line.
        end_line_number: Optional final source line.
        metadata: Extensible deterministic metadata.
    """

    name: str
    members: list[ApiObject] = field(default_factory=list)
    summary: str | None = None
    description: str | None = None
    source_path: str | None = None
    line_number: int | None = None
    end_line_number: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def objects(self) -> list[ApiObject]:
        """Return module-level API objects."""

        return self.members

    @property
    def qualname(self) -> str:
        """Return the module qualname."""

        return self.name

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data."""

        return {
            "name": self.name,
            "members": [member.to_dict() for member in self.members],
            "summary": self.summary,
            "description": self.description,
            "source_path": self.source_path,
            "line_number": self.line_number,
            "end_line_number": self.end_line_number,
            "metadata": _jsonable_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiModule:
        """Reconstruct a module from serialized data."""

        return cls(
            name=str(data["name"]),
            members=[
                ApiObject.from_dict(item)
                for item in data.get("members", [])  # type: ignore[union-attr]
            ],
            summary=_optional_str(data.get("summary")),
            description=_optional_str(data.get("description")),
            source_path=_optional_str(data.get("source_path")),
            line_number=_optional_int(data.get("line_number")),
            end_line_number=_optional_int(data.get("end_line_number")),
            metadata=dict(data.get("metadata", {})),  # type: ignore[arg-type]
        )

    def classes(self) -> list[ApiObject]:
        """Return module-level classes."""

        return self.select(kind="class", recursive=False)

    def functions(self) -> list[ApiObject]:
        """Return module-level functions."""

        return self.select(kind="function", recursive=False)

    def attributes(self) -> list[ApiObject]:
        """Return module-level attributes and data objects."""

        return self.select(kind=("attribute", "data"), recursive=False)

    def properties(self) -> list[ApiObject]:
        """Return properties from module classes."""

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
        """Return filtered module objects."""

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
        """Find an object by qualname or name."""

        if qualname_or_name == self.name:
            return None
        for obj in self.iter_objects(recursive=True):
            if qualname_or_name in {obj.qualname, obj.name}:
                return obj
        return None

    def to_summary_table(self, objects: Sequence[ApiObject] | None = None, **kwargs):
        """Return a summary table for module objects."""

        from oodocs.apidoc.blocks import api_objects_to_summary_table

        return api_objects_to_summary_table(objects or list(self.iter_objects()), **kwargs)

    def to_sections(self, *, profile: object = "reference", level: int = 2) -> list[object]:
        """Return module objects as OODocs sections."""

        return [obj.to_section(level=level, profile=profile) for obj in self.members]

    def to_chapter(self, *, profile: object = "reference", title: str | None = None):
        """Return this module as an OODocs chapter."""

        from oodocs.apidoc.blocks import api_module_to_chapter

        return api_module_to_chapter(self, profile=profile, title=title)

    def to_blocks(self, *, profile: object = "reference", level: int = 2) -> list[object]:
        """Return this module as renderer-neutral blocks."""

        return self.to_sections(profile=profile, level=level)


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
        doc = Document("Function API", Chapter("Summary", api.to_summary_table(functions)))
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
        """Return deterministic serialized data."""

        return {
            "name": self.name,
            "version": self.version,
            "modules": [module.to_dict() for module in self.modules],
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": _jsonable_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiPackage:
        """Reconstruct a package from serialized data."""

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

    def find(self, qualname_or_name: str) -> ApiObject | ApiModule | None:
        """Find a module or object by qualname or local name."""

        for module in self.modules:
            if module.name == qualname_or_name:
                return module
            if found := module.find(qualname_or_name):
                return found
        return None

    def modules_by_name(self) -> dict[str, ApiModule]:
        """Return modules keyed by module name."""

        return {module.name: module for module in self.modules}

    def classes(self) -> list[ApiObject]:
        """Return public classes."""

        return self.select(kind="class")

    def functions(self) -> list[ApiObject]:
        """Return public functions."""

        return self.select(kind="function")

    def methods(self) -> list[ApiObject]:
        """Return public methods."""

        return self.select(kind="method")

    def attributes(self) -> list[ApiObject]:
        """Return public attributes and data objects."""

        return self.select(kind=("attribute", "data"))

    def public_objects(self) -> list[ApiObject]:
        """Return all public API objects."""

        return self.select(visibility="public")

    def private_objects(self) -> list[ApiObject]:
        """Return private or protected API objects."""

        return [
            obj
            for obj in self.iter_objects(recursive=True)
            if obj.visibility in {"private", "protected", "internal"}
        ]

    def undocumented_public_objects(self) -> list[ApiObject]:
        """Return public API objects without docstring summary or description."""

        return self.select(visibility="public", documented=False)

    def to_summary_table(
        self,
        objects: Sequence[ApiObject] | None = None,
        **kwargs,
    ):
        """Return a package-level API summary table."""

        from oodocs.apidoc.blocks import api_objects_to_summary_table

        return api_objects_to_summary_table(objects or self.public_objects(), **kwargs)

    def to_modules_table(self, *, caption: str | None = None):
        """Return a table summarizing collected modules."""

        from oodocs.components.media import Table

        rows = [
            [module.name, str(len(module.members)), module.summary or ""]
            for module in self.modules
        ]
        return Table(["Module", "Objects", "Summary"], rows, caption=caption)

    def to_issue_table(self, *, caption: str | None = None):
        """Return collected issues as an OODocs table."""

        from oodocs.components.media import Table

        return Table(
            ["Severity", "Code", "Object", "Module", "Location", "Message"],
            [issue.to_row() for issue in self.issues],
            caption=caption,
        )

    def to_coverage_table(self, **kwargs):
        """Return documentation coverage summary as an OODocs table."""

        from oodocs.apidoc.coverage import check_api_docs

        return check_api_docs(self, **kwargs).to_table()

    def to_sections(self, *, profile: object = "reference", level: int = 1) -> list[object]:
        """Return modules as OODocs sections."""

        if level == 1:
            return [module.to_chapter(profile=profile) for module in self.modules]
        sections: list[object] = []
        for module in self.modules:
            sections.extend(module.to_sections(profile=profile, level=level))
        return sections

    def to_chapters(self, *, profile: object = "reference") -> list[object]:
        """Return modules as OODocs chapters."""

        from oodocs.apidoc.blocks import api_package_to_chapters

        return api_package_to_chapters(self, profile=profile)

    def to_blocks(self, *, profile: object = "reference") -> list[object]:
        """Return this package as renderer-neutral OODocs blocks."""

        return self.to_chapters(profile=profile)

    def to_document(
        self,
        title: str | None = None,
        *,
        profile: object = "reference",
        settings: object | None = None,
        citations: object | None = None,
        include_coverage: bool = True,
        include_modules: bool = True,
    ):
        """Return this package as a complete OODocs document.

        Args:
            title: Optional document title.
            profile: Presentation profile name or object.
            settings: Optional ``DocumentSettings``.
            citations: Optional citation library.
            include_coverage: Whether to include a coverage overview chapter.
            include_modules: Whether to include module chapters.

        Returns:
            OODocs ``Document``.
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
