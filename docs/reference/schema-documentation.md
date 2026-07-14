# Schema documentation

`oodocs.schema` models field-oriented references independently of JSON,
YAML, TOML, Python classes, or an application-specific configuration type.
The models compose ordinary OODocs `Table`, `Section`, and `Chapter` blocks,
so they work with the existing DOCX, PDF, and HTML renderers.

## Core models

```python
from oodocs import Document, inline_math
from oodocs.schema import FieldSpec, SchemaCatalog, SchemaSpec

address = SchemaSpec(
    key="address",
    title="Address",
    fields=(
        FieldSpec("city", "string", requirement="required"),
    ),
)
customer = SchemaSpec(
    key="customer",
    title="Customer",
    fields=(
        FieldSpec(
            "credit_limit",
            "float",
            requirement="conditional-required",
            condition="Required for invoiced accounts.",
            constraints=(inline_math(r"x \geq 0"),),
            unit="USD",
            target_schema=None,
        ),
        FieldSpec("address", "object", target_schema="address"),
    ),
)

catalog = SchemaCatalog((customer, address))
catalog.validate(raise_on_error=True)
document = Document("Data model", catalog.to_chapter("Schemas"))
```

`FieldSpec.as_record()` returns the unformatted values supplied to the model.
If a collector supplied `raw_record`, unknown source keys remain in that
mapping as well. Optional `metadata`, `deprecated`, and `links` values are
preserved without introducing application-specific columns into the core
model.

`SchemaCatalog.to_chapter()` creates each schema section first and then
resolves `target_schema` keys against those exact section objects. Circular
references therefore produce ordinary object links without recursive schema
expansion. Validation reports `schema-duplicate-key` and
`schema-unknown-target` as stable structured error codes.

## Presentation

The default requirement labels are `Required`, `Optional`, `Conditional
required`, and `Conditional optional`; abbreviations are not built into the
model. Override labels directly or with `SchemaPresentation`:

```python
from oodocs.schema import SchemaPresentation

presentation = SchemaPresentation(
    requirement_labels={"required": "Must be supplied"},
    type_labels={"integer": "Whole number"},
    metadata_columns={"environment": "Environment variable"},
)
table = customer.to_table(presentation=presentation)
```

The generic types `string`, `float`, `integer`, `enum`, `boolean`, `array`,
and `object` use named chip styles such as `schema.type.string`. Requirement
styles use keys such as `schema.requirement.required`. A custom string or
inline object is rendered unchanged instead of being forced into a generic
type palette. Constraints and units accept the same inline inputs as a normal
paragraph, including quantities, math, and object links. Schema tables enable
splitting and repeated header rows by default.

## Collectors and diagnostics

External formats stay in optional integration modules:

```python
from oodocs.integrations.json_schema import collect_json_schema
from oodocs.integrations.python import collect_dataclass_schema

json_catalog = collect_json_schema("schema.json", key="settings")
python_catalog = collect_dataclass_schema(Settings)
```

The JSON Schema collector handles root properties, local `$defs` or legacy
`definitions`, requirements, defaults, common constraints, units, deprecation,
links, and local `$ref` targets. It preserves each original mapping. Keywords
that are unsupported or represented only partially produce structured
`SchemaDiagnostic` entries on `catalog.diagnostics` rather than disappearing
silently.

The dataclass collector follows nested dataclass fields, derives generic type
and requirement information, and reads generic field metadata such as
`description`, `constraints`, `unit`, `condition`, `deprecated`, and `links`.
It never invokes a default factory while building documentation; the factory
is retained raw and reported as a diagnostic.

Pydantic support is lazy and optional:

```python
from oodocs.integrations.pydantic import collect_pydantic_schema

catalog = collect_pydantic_schema(SettingsModel)
```

Importing `oodocs.schema` or the integration module does not import Pydantic.
Calling the collector without the optional package raises a focused
`ImportError`. Pydantic's generated JSON Schema is passed through the same
collector so preservation and loss diagnostics remain consistent.
