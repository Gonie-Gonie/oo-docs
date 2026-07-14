"""Renderer-neutral models for schema and field reference documentation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, TYPE_CHECKING


if TYPE_CHECKING:
    from oodocs.components.base import BlockInput
    from oodocs.components.blocks import Chapter, Section
    from oodocs.components.inline import InlineInput
    from oodocs.components.media import Table
    from oodocs.schema.render import SchemaPresentation
    from oodocs.validation import ValidationResult


RequirementLevel = Literal[
    "required",
    "optional",
    "conditional-required",
    "conditional-optional",
]
SchemaDiagnosticSeverity = Literal["error", "warning"]

_REQUIREMENT_LEVELS = frozenset(
    {
        "required",
        "optional",
        "conditional-required",
        "conditional-optional",
    }
)


def _required_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _mapping_copy(value: Mapping[str, object] | None, *, field_name: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return dict(value)


def _normalize_links(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (value.decode() if isinstance(value, bytes) else value,)
    if isinstance(value, Sequence):
        return tuple(value)
    return (value,)


@dataclass(frozen=True, slots=True)
class SchemaDiagnostic:
    """Structured information retained by schema collectors.

    Collectors use diagnostics for unsupported or lossy source constructs
    while still returning a usable :class:`SchemaCatalog`.
    """

    code: str
    message: str
    severity: SchemaDiagnosticSeverity = "warning"
    path: str = "schema_catalog"
    source: str | None = None
    keyword: str | None = None
    raw_value: object | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            _required_text(self.code, field_name="SchemaDiagnostic.code"),
        )
        object.__setattr__(
            self,
            "message",
            _required_text(self.message, field_name="SchemaDiagnostic.message"),
        )
        if self.severity not in {"error", "warning"}:
            raise ValueError("SchemaDiagnostic.severity must be 'error' or 'warning'")

    def as_record(self) -> dict[str, object]:
        """Return the diagnostic as a plain record."""

        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "source": self.source,
            "keyword": self.keyword,
            "raw_value": self.raw_value,
        }


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One field in a generic schema reference.

    Values are intentionally retained as caller-owned inline/block objects.
    Rendering is a separate concern and does not replace quantities, math,
    links, defaults, constraints, or source metadata with display strings.
    """

    name: str
    value_type: InlineInput
    requirement: RequirementLevel | None = None
    default: object | None = None
    condition: InlineInput | None = None
    constraints: InlineInput | Sequence[InlineInput] | None = None
    unit: InlineInput | None = None
    description: BlockInput | Sequence[BlockInput] | None = None
    target_schema: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    deprecated: bool | str | None = None
    links: tuple[InlineInput, ...] = ()
    raw_record: Mapping[str, object] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, field_name="FieldSpec.name"))
        if self.requirement is not None and self.requirement not in _REQUIREMENT_LEVELS:
            allowed = ", ".join(sorted(_REQUIREMENT_LEVELS))
            raise ValueError(f"FieldSpec.requirement must be one of {allowed}")
        if self.target_schema is not None:
            object.__setattr__(
                self,
                "target_schema",
                _required_text(self.target_schema, field_name="FieldSpec.target_schema"),
            )
        if self.deprecated is not None and not isinstance(self.deprecated, (bool, str)):
            raise TypeError("FieldSpec.deprecated must be a bool, string, or None")
        object.__setattr__(
            self,
            "metadata",
            _mapping_copy(self.metadata, field_name="FieldSpec.metadata"),
        )
        object.__setattr__(
            self,
            "raw_record",
            _mapping_copy(self.raw_record, field_name="FieldSpec.raw_record"),
        )
        object.__setattr__(self, "links", _normalize_links(self.links))

    def as_record(self) -> dict[str, object]:
        """Return raw field values without presentation-time formatting.

        Unknown keys retained in ``raw_record`` remain available alongside
        the normalized generic schema fields.
        """

        record = dict(self.raw_record)
        record.update(
            {
                "name": self.name,
                "value_type": self.value_type,
                "requirement": self.requirement,
                "default": self.default,
                "condition": self.condition,
                "constraints": self.constraints,
                "unit": self.unit,
                "description": self.description,
                "target_schema": self.target_schema,
                "metadata": dict(self.metadata),
                "deprecated": self.deprecated,
                "links": self.links,
            }
        )
        return record


@dataclass(slots=True)
class SchemaSpec:
    """A named collection of generic field specifications."""

    key: str
    title: InlineInput
    fields: tuple[FieldSpec, ...]
    description: BlockInput | Sequence[BlockInput] | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    deprecated: bool | str | None = None
    links: tuple[InlineInput, ...] = ()
    raw_record: Mapping[str, object] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.key = _required_text(self.key, field_name="SchemaSpec.key")
        self.fields = tuple(self.fields)
        if not all(isinstance(item, FieldSpec) for item in self.fields):
            raise TypeError("SchemaSpec.fields must contain FieldSpec values")
        self.metadata = _mapping_copy(self.metadata, field_name="SchemaSpec.metadata")
        self.raw_record = _mapping_copy(self.raw_record, field_name="SchemaSpec.raw_record")
        self.links = _normalize_links(self.links)  # type: ignore[assignment]
        if self.deprecated is not None and not isinstance(self.deprecated, (bool, str)):
            raise TypeError("SchemaSpec.deprecated must be a bool, string, or None")

    def as_record(self) -> dict[str, object]:
        """Return raw schema values without display conversion."""

        record = dict(self.raw_record)
        record.update(
            {
                "key": self.key,
                "title": self.title,
                "fields": tuple(field.as_record() for field in self.fields),
                "description": self.description,
                "metadata": dict(self.metadata),
                "deprecated": self.deprecated,
                "links": self.links,
            }
        )
        return record

    def to_table(
        self,
        *,
        presentation: SchemaPresentation | None = None,
        requirement_labels: Mapping[RequirementLevel, InlineInput] | None = None,
        type_labels: Mapping[str, InlineInput] | None = None,
        targets: Mapping[str, object] | None = None,
        caption: InlineInput | None = None,
    ) -> Table:
        """Convert the fields to an ordinary OODocs table."""

        from oodocs.schema.render import schema_to_table

        return schema_to_table(
            self,
            presentation=presentation,
            requirement_labels=requirement_labels,
            type_labels=type_labels,
            targets=targets,
            caption=caption,
        )

    def to_section(
        self,
        *,
        title: InlineInput | None = None,
        level: int = 2,
        numbered: bool = True,
        toc: bool = True,
        presentation: SchemaPresentation | None = None,
        requirement_labels: Mapping[RequirementLevel, InlineInput] | None = None,
        type_labels: Mapping[str, InlineInput] | None = None,
        targets: Mapping[str, object] | None = None,
    ) -> Section:
        """Convert this schema to an ordinary OODocs section."""

        from oodocs.schema.render import schema_to_section

        return schema_to_section(
            self,
            title=title,
            level=level,
            numbered=numbered,
            toc=toc,
            presentation=presentation,
            requirement_labels=requirement_labels,
            type_labels=type_labels,
            targets=targets,
        )


@dataclass(slots=True)
class SchemaCatalog:
    """A collection of schemas plus collector diagnostics and raw metadata."""

    schemas: tuple[SchemaSpec, ...]
    diagnostics: tuple[SchemaDiagnostic, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
    raw_record: Mapping[str, object] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.schemas = tuple(self.schemas)
        self.diagnostics = tuple(self.diagnostics)
        if not all(isinstance(item, SchemaSpec) for item in self.schemas):
            raise TypeError("SchemaCatalog.schemas must contain SchemaSpec values")
        if not all(isinstance(item, SchemaDiagnostic) for item in self.diagnostics):
            raise TypeError("SchemaCatalog.diagnostics must contain SchemaDiagnostic values")
        self.metadata = _mapping_copy(self.metadata, field_name="SchemaCatalog.metadata")
        self.raw_record = _mapping_copy(
            self.raw_record,
            field_name="SchemaCatalog.raw_record",
        )

    def schema_for(self, key: str) -> SchemaSpec:
        """Return the first schema matching ``key`` or raise ``KeyError``."""

        for schema in self.schemas:
            if schema.key == key:
                return schema
        raise KeyError(key)

    def as_record(self) -> dict[str, object]:
        """Return the catalog, source record, and diagnostics as raw values."""

        record = dict(self.raw_record)
        record.update(
            {
                "schemas": tuple(schema.as_record() for schema in self.schemas),
                "diagnostics": tuple(
                    diagnostic.as_record() for diagnostic in self.diagnostics
                ),
                "metadata": dict(self.metadata),
            }
        )
        return record

    def validate(self, *, raise_on_error: bool = False) -> ValidationResult:
        """Validate catalog keys and references with stable issue codes."""

        from oodocs.schema.validation import validate_schema_catalog

        return validate_schema_catalog(self, raise_on_error=raise_on_error)

    def to_chapter(
        self,
        title: InlineInput = "Schema reference",
        *,
        presentation: SchemaPresentation | None = None,
        requirement_labels: Mapping[RequirementLevel, InlineInput] | None = None,
        type_labels: Mapping[str, InlineInput] | None = None,
        numbered: bool = True,
        toc: bool = True,
        validate: bool = False,
    ) -> Chapter:
        """Build every schema section once and connect catalog references."""

        from oodocs.schema.render import catalog_to_chapter

        if validate:
            self.validate(raise_on_error=True)
        return catalog_to_chapter(
            self,
            title=title,
            presentation=presentation,
            requirement_labels=requirement_labels,
            type_labels=type_labels,
            numbered=numbered,
            toc=toc,
        )


__all__ = [
    "FieldSpec",
    "RequirementLevel",
    "SchemaCatalog",
    "SchemaDiagnostic",
    "SchemaDiagnosticSeverity",
    "SchemaSpec",
]
