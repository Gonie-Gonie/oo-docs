"""Collector for JSON Schema documents.

The dependency-free collector intentionally supports a conservative subset of
JSON Schema. Source records are retained on the generic models, and constructs
that cannot be represented without loss are returned as catalog diagnostics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import re
from typing import Any

from oodocs.schema import FieldSpec, SchemaCatalog, SchemaDiagnostic, SchemaSpec


_PROPERTY_KEYWORDS = frozenset(
    {
        "$anchor",
        "$comment",
        "$id",
        "$ref",
        "const",
        "condition",
        "default",
        "deprecated",
        "description",
        "else",
        "enum",
        "env",
        "examples",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "if",
        "links",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "multipleOf",
        "pattern",
        "readOnly",
        "required",
        "then",
        "title",
        "type",
        "uniqueItems",
        "unit",
        "writeOnly",
        "x-unit",
    }
)
_ROOT_KEYWORDS = frozenset(
    {
        "$defs",
        "$id",
        "$schema",
        "$vocabulary",
        "additionalProperties",
        "allOf",
        "anyOf",
        "default",
        "definitions",
        "dependentRequired",
        "dependentSchemas",
        "deprecated",
        "description",
        "else",
        "examples",
        "if",
        "links",
        "not",
        "oneOf",
        "patternProperties",
        "properties",
        "propertyNames",
        "required",
        "then",
        "title",
        "type",
        "unevaluatedProperties",
    }
)
_LOSSY_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "allOf",
        "anyOf",
        "dependentSchemas",
        "else",
        "if",
        "not",
        "oneOf",
        "patternProperties",
        "propertyNames",
        "then",
        "unevaluatedProperties",
    }
)
_CONSTRAINT_LABELS = {
    "const": "constant",
    "enum": "values",
    "exclusiveMaximum": "exclusive maximum",
    "exclusiveMinimum": "exclusive minimum",
    "format": "format",
    "maximum": "maximum",
    "maxItems": "maximum items",
    "maxLength": "maximum length",
    "maxProperties": "maximum properties",
    "minimum": "minimum",
    "minItems": "minimum items",
    "minLength": "minimum length",
    "minProperties": "minimum properties",
    "multipleOf": "multiple of",
    "pattern": "pattern",
    "uniqueItems": "unique items",
}


def collect_json_schema(
    source: Mapping[str, object] | str | Path,
    *,
    key: str | None = None,
    title: object | None = None,
) -> SchemaCatalog:
    """Collect a JSON Schema mapping or file into a generic schema catalog.

    Local ``$defs``/``definitions`` records become additional schemas. The
    returned catalog always carries the untouched input mapping in
    ``raw_record`` and exposes unsupported/lossy constructs in ``diagnostics``.
    """

    data, source_label, source_path = _load_source(source)
    diagnostics: list[SchemaDiagnostic] = []
    definitions = _definitions(data)
    root_key = _schema_key(data, explicit=key, fallback=source_path.stem if source_path else None)
    root_title = title if title is not None else data.get("title", root_key)

    schemas: list[SchemaSpec] = [
        _collect_schema(
            data,
            key=root_key,
            title=root_title,
            path="#",
            source=source_label,
            diagnostics=diagnostics,
        )
    ]
    for definition_key, definition in definitions.items():
        if not isinstance(definition, Mapping):
            diagnostics.append(
                SchemaDiagnostic(
                    "json-schema-invalid-definition",
                    f"Definition {definition_key!r} is not an object and was skipped.",
                    path=f"#/$defs/{_pointer_escape(str(definition_key))}",
                    source=source_label,
                    keyword="$defs",
                    raw_value=definition,
                )
            )
            continue
        schemas.append(
            _collect_schema(
                definition,
                key=str(definition_key),
                title=definition.get("title", str(definition_key)),
                path=f"#/$defs/{_pointer_escape(str(definition_key))}",
                source=source_label,
                diagnostics=diagnostics,
            )
        )

    return SchemaCatalog(
        tuple(schemas),
        diagnostics=tuple(diagnostics),
        metadata={
            "source": source_label,
            "dialect": data.get("$schema"),
        },
        raw_record=data,
    )


def _load_source(
    source: Mapping[str, object] | str | Path,
) -> tuple[dict[str, object], str | None, Path | None]:
    if isinstance(source, Mapping):
        return dict(source), None, None
    source_path = Path(source)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("JSON Schema root must be an object")
    return dict(payload), source_path.as_posix(), source_path


def _definitions(data: Mapping[str, object]) -> dict[str, object]:
    combined: dict[str, object] = {}
    legacy = data.get("definitions")
    modern = data.get("$defs")
    if isinstance(legacy, Mapping):
        combined.update((str(key), value) for key, value in legacy.items())
    if isinstance(modern, Mapping):
        combined.update((str(key), value) for key, value in modern.items())
    return combined


def _schema_key(
    data: Mapping[str, object],
    *,
    explicit: str | None,
    fallback: str | None,
) -> str:
    if explicit:
        return explicit
    identifier = data.get("$id")
    if isinstance(identifier, str) and identifier.strip():
        candidate = identifier.rstrip("/#").rsplit("/", 1)[-1]
        candidate = re.sub(r"\.schema\.json$|\.json$", "", candidate, flags=re.IGNORECASE)
        if candidate:
            return candidate
    title = data.get("title")
    if isinstance(title, str) and title.strip():
        slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
        if slug:
            return slug
    return fallback or "schema"


def _collect_schema(
    data: Mapping[str, object],
    *,
    key: str,
    title: object,
    path: str,
    source: str | None,
    diagnostics: list[SchemaDiagnostic],
) -> SchemaSpec:
    properties = data.get("properties", {})
    if not isinstance(properties, Mapping):
        diagnostics.append(
            SchemaDiagnostic(
                "json-schema-invalid-properties",
                "The properties keyword is not an object; no fields were collected.",
                path=f"{path}/properties",
                source=source,
                keyword="properties",
                raw_value=properties,
            )
        )
        properties = {}
    raw_required = data.get("required", ())
    required_names = (
        {str(item) for item in raw_required}
        if isinstance(raw_required, Sequence)
        and not isinstance(raw_required, (str, bytes))
        else set()
    )
    conditional_names, conditions = _conditional_requirements(data)
    fields: list[FieldSpec] = []
    for name, raw_field in properties.items():
        field_path = f"{path}/properties/{_pointer_escape(str(name))}"
        if not isinstance(raw_field, Mapping):
            diagnostics.append(
                SchemaDiagnostic(
                    "json-schema-invalid-property",
                    f"Property {name!r} is not an object and was skipped.",
                    path=field_path,
                    source=source,
                    keyword="properties",
                    raw_value=raw_field,
                )
            )
            continue
        field_data = dict(raw_field)
        explicit_required = field_data.get("required")
        is_required = str(name) in required_names or explicit_required is True
        is_conditional = str(name) in conditional_names or field_data.get("condition") is not None
        if is_conditional:
            requirement = (
                "conditional-required"
                if is_required or str(name) in conditional_names
                else "conditional-optional"
            )
        else:
            requirement = "required" if is_required else "optional"
        condition = field_data.get("condition") or conditions.get(str(name))
        field_spec = FieldSpec(
            name=str(name),
            value_type=_value_type(field_data),
            requirement=requirement,
            default=field_data.get("default"),
            condition=condition,
            constraints=_constraints(field_data),
            unit=field_data.get("unit", field_data.get("x-unit")),
            description=field_data.get("description"),
            target_schema=_target_schema(field_data.get("$ref"), current_key=key),
            metadata=_field_metadata(field_data),
            deprecated=field_data.get("deprecated"),
            links=_links(field_data),
            raw_record=field_data,
        )
        fields.append(field_spec)
        _diagnose_keywords(
            field_data,
            allowed=_PROPERTY_KEYWORDS,
            path=field_path,
            source=source,
            diagnostics=diagnostics,
        )
        for keyword in _LOSSY_KEYWORDS & field_data.keys():
            _lossy_diagnostic(
                keyword,
                field_data[keyword],
                path=field_path,
                source=source,
                diagnostics=diagnostics,
            )

    for keyword in _LOSSY_KEYWORDS & data.keys():
        _lossy_diagnostic(
            keyword,
            data[keyword],
            path=path,
            source=source,
            diagnostics=diagnostics,
        )
    _diagnose_keywords(
        data,
        allowed=_ROOT_KEYWORDS,
        path=path,
        source=source,
        diagnostics=diagnostics,
    )
    return SchemaSpec(
        key=key,
        title=title,
        fields=tuple(fields),
        description=data.get("description"),
        metadata={
            "$id": data.get("$id"),
            "$schema": data.get("$schema"),
            "examples": data.get("examples"),
        },
        deprecated=data.get("deprecated"),
        links=_links(data),
        raw_record=data,
    )


def _value_type(data: Mapping[str, object]) -> object:
    if "enum" in data or "const" in data:
        return "enum"
    value = data.get("type")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        non_null = [item for item in value if item != "null"]
        value = non_null[0] if len(non_null) == 1 else " | ".join(map(str, non_null))
    aliases = {
        "number": "float",
        "str": "string",
        "int": "integer",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
    }
    if isinstance(value, str):
        if value.startswith("list["):
            return "array"
        return aliases.get(value, value)
    if "$ref" in data:
        return "object"
    if "properties" in data:
        return "object"
    return "object"


def _constraints(data: Mapping[str, object]) -> tuple[str, ...]:
    constraints: list[str] = []
    for keyword, label in _CONSTRAINT_LABELS.items():
        if keyword not in data:
            continue
        value = data[keyword]
        if keyword == "uniqueItems" and value is False:
            continue
        if isinstance(value, (list, tuple)):
            display = ", ".join(str(item) for item in value)
        else:
            display = str(value).lower() if isinstance(value, bool) else str(value)
        constraints.append(f"{label}: {display}")
    return tuple(constraints)


def _target_schema(value: object, *, current_key: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if value.strip() in {"#", "#/"}:
        return current_key
    fragment = value.rsplit("/", 1)[-1]
    return fragment.replace("~1", "/").replace("~0", "~") or None


def _field_metadata(data: Mapping[str, object]) -> dict[str, object]:
    metadata = {
        key: value
        for key, value in data.items()
        if key.startswith("x-")
        or key in {"env", "examples", "readOnly", "title", "writeOnly"}
    }
    return metadata


def _links(data: Mapping[str, object]) -> tuple[object, ...]:
    links: list[object] = []
    identifier = data.get("$id")
    if isinstance(identifier, str):
        links.append(identifier)
    raw_links = data.get("links")
    if isinstance(raw_links, Mapping):
        links.extend(f"{relation}: {target}" for relation, target in raw_links.items())
    elif isinstance(raw_links, Sequence) and not isinstance(raw_links, (str, bytes)):
        for item in raw_links:
            if isinstance(item, Mapping):
                relation = item.get("rel")
                target = item.get("href", item.get("target"))
                if relation is not None and target is not None:
                    links.append(f"{relation}: {target}")
                else:
                    links.append(json.dumps(dict(item), ensure_ascii=False, sort_keys=True))
            else:
                links.append(item)
    elif raw_links is not None:
        links.append(raw_links)
    return tuple(links)


def _conditional_requirements(
    data: Mapping[str, object],
) -> tuple[set[str], dict[str, str]]:
    names: set[str] = set()
    descriptions: dict[str, str] = {}
    dependent = data.get("dependentRequired")
    if isinstance(dependent, Mapping):
        for trigger, fields in dependent.items():
            if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes)):
                for field_name in fields:
                    name = str(field_name)
                    names.add(name)
                    descriptions[name] = f"Required when {trigger} is present."
    return names, descriptions


def _diagnose_keywords(
    data: Mapping[str, object],
    *,
    allowed: frozenset[str],
    path: str,
    source: str | None,
    diagnostics: list[SchemaDiagnostic],
) -> None:
    for keyword, value in data.items():
        if keyword in allowed or keyword.startswith("x-"):
            continue
        diagnostics.append(
            SchemaDiagnostic(
                "json-schema-unsupported-keyword",
                f"JSON Schema keyword {keyword!r} is retained raw but is not interpreted.",
                path=f"{path}/{_pointer_escape(keyword)}",
                source=source,
                keyword=keyword,
                raw_value=value,
            )
        )


def _lossy_diagnostic(
    keyword: str,
    value: object,
    *,
    path: str,
    source: str | None,
    diagnostics: list[SchemaDiagnostic],
) -> None:
    diagnostics.append(
        SchemaDiagnostic(
            "json-schema-lossy-keyword",
            f"JSON Schema keyword {keyword!r} is preserved raw but not represented in field rows.",
            path=f"{path}/{_pointer_escape(keyword)}",
            source=source,
            keyword=keyword,
            raw_value=value,
        )
    )


def _pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


__all__ = ["collect_json_schema"]
