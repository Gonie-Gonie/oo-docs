"""Collectors for renderer-neutral Python data models."""

from __future__ import annotations

from collections import abc
from dataclasses import MISSING, Field, fields, is_dataclass
from enum import Enum
import inspect
import types
from typing import Any, get_args, get_origin, get_type_hints, Literal, Union

from oodocs.schema import FieldSpec, SchemaCatalog, SchemaDiagnostic, SchemaSpec


def collect_dataclass_schema(
    model: type[object],
    *,
    key: str | None = None,
    title: object | None = None,
) -> SchemaCatalog:
    """Collect a dataclass and reachable dataclass fields as a schema catalog.

    Default factories are deliberately not executed. Their presence is
    retained in the raw record and reported as a diagnostic rather than
    running caller code during documentation collection.
    """

    if not isinstance(model, type) or not is_dataclass(model):
        raise TypeError("collect_dataclass_schema expects a dataclass type")

    root_key = key or model.__name__
    keys: dict[type[object], str] = {model: root_key}
    queue: list[type[object]] = [model]
    schemas: list[SchemaSpec] = []
    diagnostics: list[SchemaDiagnostic] = []
    processed: set[type[object]] = set()

    while queue:
        current = queue.pop(0)
        if current in processed:
            continue
        processed.add(current)
        current_key = keys[current]
        hints = _type_hints(current, diagnostics, schema_key=current_key)
        field_specs: list[FieldSpec] = []
        for index, dataclass_field in enumerate(fields(current)):
            annotation = hints.get(dataclass_field.name, dataclass_field.type)
            unwrapped, nullable = _unwrap_optional(annotation)
            target_types = _nested_dataclass_types(unwrapped)
            target_type = target_types[0] if target_types else None
            target_key: str | None = None
            for nested_type in target_types:
                if nested_type not in keys:
                    candidate = nested_type.__name__
                    existing_keys = set(keys.values())
                    if candidate in existing_keys:
                        candidate = (
                            f"{nested_type.__module__}.{nested_type.__qualname__}"
                        )
                    keys[nested_type] = candidate
                queue.append(nested_type)
            if target_type is not None:
                target_key = keys[target_type]
            if len(target_types) > 1:
                diagnostics.append(
                    SchemaDiagnostic(
                        "python-dataclass-ambiguous-target",
                        (
                            f"Field {current.__qualname__}.{dataclass_field.name} "
                            "references multiple dataclass types; the first target "
                            "is used for the field link."
                        ),
                        path=(
                            f"schema_catalog.schemas[{len(schemas)}]"
                            f".fields[{index}].target_schema"
                        ),
                        source=current.__module__,
                        keyword="annotation",
                        raw_value=annotation,
                    )
                )

            metadata = dict(dataclass_field.metadata)
            requirement = metadata.get("requirement")
            if requirement is None:
                requirement = (
                    "optional"
                    if nullable or _has_default(dataclass_field)
                    else "required"
                )
            default = _default_value(
                dataclass_field,
                diagnostics,
                path=f"schema_catalog.schemas[{len(schemas)}].fields[{index}].default",
                source=current.__module__,
            )
            value_type, supported = _annotation_value_type(unwrapped)
            if not supported:
                diagnostics.append(
                    SchemaDiagnostic(
                        "python-dataclass-unsupported-annotation",
                        (
                            f"Annotation for {current.__qualname__}.{dataclass_field.name} "
                            "is retained as a custom type label."
                        ),
                        path=(
                            f"schema_catalog.schemas[{len(schemas)}]"
                            f".fields[{index}].value_type"
                        ),
                        source=current.__module__,
                        keyword="annotation",
                        raw_value=annotation,
                    )
                )
            field_specs.append(
                FieldSpec(
                    name=dataclass_field.name,
                    value_type=value_type,
                    requirement=requirement,  # type: ignore[arg-type]
                    default=default,
                    condition=metadata.get("condition"),
                    constraints=metadata.get("constraints"),
                    unit=metadata.get("unit"),
                    description=metadata.get("description"),
                    target_schema=metadata.get("target_schema", target_key),
                    metadata=metadata,
                    deprecated=metadata.get("deprecated"),
                    links=metadata.get("links", ()),
                    raw_record={
                        "name": dataclass_field.name,
                        "annotation": annotation,
                        "default": (
                            dataclass_field.default
                            if dataclass_field.default is not MISSING
                            else None
                        ),
                        "default_factory": (
                            dataclass_field.default_factory
                            if dataclass_field.default_factory is not MISSING
                            else None
                        ),
                        "metadata": metadata,
                    },
                )
            )

        schemas.append(
            SchemaSpec(
                key=current_key,
                title=title if current is model and title is not None else current.__name__,
                fields=tuple(field_specs),
                description=_class_description(current),
                metadata={
                    "module": current.__module__,
                    "qualname": current.__qualname__,
                },
                raw_record={
                    "class": current,
                    "annotations": dict(getattr(current, "__annotations__", {})),
                },
            )
        )

    return SchemaCatalog(
        tuple(schemas),
        diagnostics=tuple(diagnostics),
        metadata={
            "source": "python.dataclass",
            "root_model": f"{model.__module__}.{model.__qualname__}",
        },
        raw_record={"model": model},
    )


def _type_hints(
    model: type[object],
    diagnostics: list[SchemaDiagnostic],
    *,
    schema_key: str,
) -> dict[str, object]:
    try:
        return dict(get_type_hints(model, include_extras=True))
    except (NameError, TypeError) as exc:
        diagnostics.append(
            SchemaDiagnostic(
                "python-dataclass-unresolved-type-hint",
                f"Some type hints for {model.__qualname__} could not be resolved: {exc}",
                path=f"schema_catalog.{schema_key}.annotations",
                source=model.__module__,
                keyword="annotation",
                raw_value=dict(getattr(model, "__annotations__", {})),
            )
        )
        return dict(getattr(model, "__annotations__", {}))


def _has_default(field_value: Field[object]) -> bool:
    return (
        field_value.default is not MISSING
        or field_value.default_factory is not MISSING
    )


def _default_value(
    field_value: Field[object],
    diagnostics: list[SchemaDiagnostic],
    *,
    path: str,
    source: str,
) -> object | None:
    if field_value.default is not MISSING:
        return field_value.default
    if field_value.default_factory is not MISSING:
        factory = field_value.default_factory
        name = getattr(factory, "__qualname__", getattr(factory, "__name__", repr(factory)))
        diagnostics.append(
            SchemaDiagnostic(
                "python-dataclass-default-factory-not-evaluated",
                f"Default factory {name} was retained without being executed.",
                path=path,
                source=source,
                keyword="default_factory",
                raw_value=factory,
            )
        )
        return f"<factory {name}>"
    return None


def _unwrap_optional(annotation: object) -> tuple[object, bool]:
    origin = get_origin(annotation)
    if origin in {Union, types.UnionType}:
        args = get_args(annotation)
        non_null = tuple(arg for arg in args if arg is not type(None))
        if len(non_null) == 1 and len(non_null) != len(args):
            return non_null[0], True
    return annotation, False


def _is_dataclass_type(annotation: object) -> bool:
    return isinstance(annotation, type) and is_dataclass(annotation)


def _nested_dataclass_types(annotation: object) -> tuple[type[object], ...]:
    if _is_dataclass_type(annotation):
        return (annotation,)  # type: ignore[return-value]
    discovered: list[type[object]] = []
    for argument in get_args(annotation):
        if argument is type(None):
            continue
        for nested_type in _nested_dataclass_types(argument):
            if nested_type not in discovered:
                discovered.append(nested_type)
    return tuple(discovered)


def _annotation_value_type(annotation: object) -> tuple[str, bool]:
    if annotation is str:
        return "string", True
    if annotation is float:
        return "float", True
    if annotation is int:
        return "integer", True
    if annotation is bool:
        return "boolean", True
    if annotation in {dict, object, Any}:
        return "object", True
    if annotation in {list, tuple, set, frozenset}:
        return "array", True
    if _is_dataclass_type(annotation):
        return "object", True
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return "enum", True

    origin = get_origin(annotation)
    if origin is Literal:
        return "enum", True
    if origin in {
        list,
        tuple,
        set,
        frozenset,
        abc.Collection,
        abc.Iterable,
        abc.Sequence,
    }:
        return "array", True
    if origin in {dict, abc.Mapping}:
        return "object", True
    if origin in {Union, types.UnionType}:
        return " | ".join(_annotation_label(item) for item in get_args(annotation)), False
    return _annotation_label(annotation), False


def _annotation_label(annotation: object) -> str:
    if isinstance(annotation, str):
        return annotation
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation).replace("typing.", "")


def _class_description(model: type[object]) -> str | None:
    description = inspect.getdoc(model)
    if not description or description.startswith(f"{model.__name__}("):
        return None
    return description


__all__ = ["collect_dataclass_schema"]
