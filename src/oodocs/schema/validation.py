"""Validation for generic schema catalogs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from oodocs.validation import ValidationIssue, ValidationResult


if TYPE_CHECKING:
    from oodocs.schema.model import SchemaCatalog


class SchemaValidationError(ValueError):
    """Raised when requested catalog validation finds blocking errors."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        summary = "; ".join(issue.message for issue in result.errors)
        super().__init__(summary or "Schema catalog validation failed")


def validate_schema_catalog(
    catalog: SchemaCatalog,
    *,
    raise_on_error: bool = False,
) -> ValidationResult:
    """Validate duplicate keys, unresolved targets, and collector diagnostics."""

    issues: list[ValidationIssue] = []
    first_indexes: dict[str, int] = {}
    for schema_index, schema in enumerate(catalog.schemas):
        first_index = first_indexes.setdefault(schema.key, schema_index)
        if first_index != schema_index:
            issues.append(
                ValidationIssue(
                    "error",
                    "schema-duplicate-key",
                    (
                        f"Schema key {schema.key!r} duplicates "
                        f"schemas[{first_index}]."
                    ),
                    source="oodocs.schema",
                    path=f"schema_catalog.schemas[{schema_index}].key",
                )
            )

    known_keys = set(first_indexes)
    for schema_index, schema in enumerate(catalog.schemas):
        for field_index, field_spec in enumerate(schema.fields):
            target = field_spec.target_schema
            if target is not None and target not in known_keys:
                issues.append(
                    ValidationIssue(
                        "error",
                        "schema-unknown-target",
                        (
                            f"Field {field_spec.name!r} targets unknown schema "
                            f"key {target!r}."
                        ),
                        source="oodocs.schema",
                        path=(
                            f"schema_catalog.schemas[{schema_index}]"
                            f".fields[{field_index}].target_schema"
                        ),
                    )
                )

    issues.extend(
        ValidationIssue(
            diagnostic.severity,
            diagnostic.code,
            diagnostic.message,
            source=diagnostic.source,
            path=diagnostic.path,
        )
        for diagnostic in catalog.diagnostics
    )
    result = ValidationResult(tuple(issues))
    if raise_on_error and not result.ok:
        raise SchemaValidationError(result)
    return result


__all__ = ["SchemaValidationError", "validate_schema_catalog"]
