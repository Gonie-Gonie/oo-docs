"""Conversion of schema models to ordinary OODocs blocks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
import json
import re
from typing import TYPE_CHECKING

from oodocs.components.base import Block, coerce_blocks
from oodocs.components.blocks import Chapter, CodeBlock, Paragraph, Section
from oodocs.components.inline import InlineChip, Text, coerce_inlines, line_break
from oodocs.components.media import Table
from oodocs.styles import TableStyle

from oodocs.schema.model import FieldSpec, RequirementLevel, SchemaCatalog, SchemaSpec


if TYPE_CHECKING:
    from oodocs.components.inline import InlineInput


DEFAULT_REQUIREMENT_LABELS: Mapping[RequirementLevel, InlineInput] = {
    "required": "Required",
    "optional": "Optional",
    "conditional-required": "Conditional required",
    "conditional-optional": "Conditional optional",
}
GENERIC_VALUE_TYPES = frozenset(
    {"string", "float", "integer", "enum", "boolean", "array", "object"}
)


@dataclass(frozen=True, slots=True)
class SchemaPresentation:
    """Presentation policy for generic schema tables.

    Requirement labels and type labels are caller-overridable. Named style
    references stay generic and can be replaced through the corresponding
    mappings without teaching renderers about schema semantics.
    """

    requirement_labels: Mapping[RequirementLevel, InlineInput] = field(
        default_factory=lambda: dict(DEFAULT_REQUIREMENT_LABELS)
    )
    type_labels: Mapping[str, InlineInput] = field(default_factory=dict)
    requirement_styles: Mapping[RequirementLevel, str] = field(
        default_factory=lambda: {
            level: f"schema.requirement.{level}"
            for level in DEFAULT_REQUIREMENT_LABELS
        }
    )
    type_styles: Mapping[str, str] = field(
        default_factory=lambda: {
            value_type: f"schema.type.{value_type}"
            for value_type in GENERIC_VALUE_TYPES
        }
    )
    metadata_columns: Mapping[str, InlineInput] = field(default_factory=dict)
    include_deprecated: bool = True
    include_links: bool = True
    include_target_schema: bool = True
    table_style: TableStyle | str | None = field(default_factory=TableStyle.compact)

    def __post_init__(self) -> None:
        requirement_labels = dict(DEFAULT_REQUIREMENT_LABELS)
        requirement_labels.update(self.requirement_labels)
        object.__setattr__(self, "requirement_labels", requirement_labels)
        object.__setattr__(self, "type_labels", dict(self.type_labels))
        requirement_styles = {
            level: f"schema.requirement.{level}"
            for level in DEFAULT_REQUIREMENT_LABELS
        }
        requirement_styles.update(self.requirement_styles)
        object.__setattr__(self, "requirement_styles", requirement_styles)
        type_styles = {
            value_type: f"schema.type.{value_type}"
            for value_type in GENERIC_VALUE_TYPES
        }
        type_styles.update(self.type_styles)
        object.__setattr__(self, "type_styles", type_styles)
        object.__setattr__(self, "metadata_columns", dict(self.metadata_columns))

    def with_labels(
        self,
        *,
        requirement_labels: Mapping[RequirementLevel, InlineInput] | None = None,
        type_labels: Mapping[str, InlineInput] | None = None,
    ) -> SchemaPresentation:
        """Return a presentation with selected display-label overrides."""

        requirements = dict(self.requirement_labels)
        requirements.update(requirement_labels or {})
        types = dict(self.type_labels)
        types.update(type_labels or {})
        return replace(self, requirement_labels=requirements, type_labels=types)


def _presentation(
    value: SchemaPresentation | None,
    *,
    requirement_labels: Mapping[RequirementLevel, InlineInput] | None,
    type_labels: Mapping[str, InlineInput] | None,
) -> SchemaPresentation:
    base = value or SchemaPresentation()
    return base.with_labels(
        requirement_labels=requirement_labels,
        type_labels=type_labels,
    )


def _paragraph(value: InlineInput | None) -> Paragraph:
    return Paragraph(_safe_inline(value))


def _safe_inline(value: object | None) -> object:
    if value is None or isinstance(value, (str, Text)):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_safe_inline(item) for item in value]
    return str(value)


def _display_value(value: object | None) -> InlineInput:
    if value is None:
        return ""
    if isinstance(value, Text):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _requirement_cell(
    field_spec: FieldSpec,
    presentation: SchemaPresentation,
) -> Paragraph:
    requirement = field_spec.requirement
    if requirement is None:
        return Paragraph("")
    label = presentation.requirement_labels.get(requirement, requirement)
    style = presentation.requirement_styles.get(
        requirement,
        f"schema.requirement.{requirement}",
    )
    return Paragraph(InlineChip(_plain_inline(label), kind="tag", chip_style=style))


def _type_cell(field_spec: FieldSpec, presentation: SchemaPresentation) -> Paragraph:
    value_type = field_spec.value_type
    if isinstance(value_type, str) and value_type in GENERIC_VALUE_TYPES:
        label = presentation.type_labels.get(value_type, value_type)
        style = presentation.type_styles.get(value_type, f"schema.type.{value_type}")
        return Paragraph(InlineChip(_plain_inline(label), kind="tag", chip_style=style))
    return Paragraph(value_type)


def _plain_inline(value: InlineInput) -> str:
    return "".join(fragment.plain_text() for fragment in coerce_inlines((value,)))


def _constraints_cell(value: object | None) -> Paragraph:
    if value is None:
        return Paragraph("")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, Text)):
        fragments: list[object] = []
        for index, item in enumerate(value):
            if index:
                fragments.append("; ")
            fragments.append(_safe_inline(item))
        return Paragraph(fragments)
    return Paragraph(_safe_inline(value))


def _description_cell(value: object | None) -> Paragraph:
    if value is None:
        return Paragraph("")
    if isinstance(value, Paragraph):
        return value
    if isinstance(value, (str, Text)):
        return Paragraph(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = list(value)
        if all(not isinstance(item, Block) for item in items):
            return Paragraph(items)
        fragments: list[object] = []
        for index, item in enumerate(items):
            if index:
                fragments.append(line_break())
            fragments.append(_block_plain_text(item))
        return Paragraph(fragments)
    if isinstance(value, Block):
        return Paragraph(_block_plain_text(value))
    return Paragraph(str(value))


def _block_plain_text(value: object) -> str:
    if isinstance(value, Paragraph):
        return value.plain_text()
    if isinstance(value, CodeBlock):
        return value.code
    if isinstance(value, Section):
        return value.plain_title()
    plain_text = getattr(value, "plain_text", None)
    if callable(plain_text):
        return str(plain_text())
    return str(value)


def _schema_link(target: object, label: InlineInput) -> object:
    """Create an object link through the target's public adapter point.

    Newer OODocs objects expose ``link`` for non-numbering object links. The
    ``ref`` fallback keeps the schema package compatible with older trees and
    still targets the exact section instance created by the catalog.
    """

    link_method = getattr(target, "link", None)
    if callable(link_method):
        return link_method(label)
    ref_method = getattr(target, "ref", None)
    if callable(ref_method):
        return ref_method(label)
    raise TypeError(f"Schema target is not linkable: {type(target)!r}")


def _target_cell(
    field_spec: FieldSpec,
    targets: Mapping[str, object] | None,
) -> Paragraph:
    key = field_spec.target_schema
    if key is None:
        return Paragraph("")
    target = targets.get(key) if targets is not None else None
    if target is None:
        return Paragraph(key)
    return Paragraph(_schema_link(target, key))


def _links_cell(links: Sequence[InlineInput]) -> Paragraph:
    fragments: list[object] = []
    for index, item in enumerate(links):
        if index:
            fragments.append(", ")
        fragments.append(_safe_inline(item))
    return Paragraph(fragments)


def schema_to_table(
    schema: SchemaSpec,
    *,
    presentation: SchemaPresentation | None = None,
    requirement_labels: Mapping[RequirementLevel, InlineInput] | None = None,
    type_labels: Mapping[str, InlineInput] | None = None,
    targets: Mapping[str, object] | None = None,
    caption: InlineInput | None = None,
) -> Table:
    """Build a field table without mutating the schema's raw records."""

    policy = _presentation(
        presentation,
        requirement_labels=requirement_labels,
        type_labels=type_labels,
    )
    headers: list[InlineInput] = [
        "Field",
        "Type",
        "Requirement",
        "Default",
        "Condition",
        "Constraints",
        "Unit",
        "Description",
    ]
    include_target = policy.include_target_schema
    include_deprecated = policy.include_deprecated and any(
        field.deprecated is not None for field in schema.fields
    )
    include_links = policy.include_links and any(field.links for field in schema.fields)
    if include_target:
        headers.append("Target schema")
    if include_deprecated:
        headers.append("Deprecated")
    if include_links:
        headers.append("Links")
    headers.extend(policy.metadata_columns.values())

    rows: list[list[object]] = []
    for field_spec in schema.fields:
        row: list[object] = [
            _paragraph(field_spec.name),
            _type_cell(field_spec, policy),
            _requirement_cell(field_spec, policy),
            _paragraph(_display_value(field_spec.default)),
            _paragraph(field_spec.condition),
            _constraints_cell(field_spec.constraints),
            _paragraph(field_spec.unit),
            _description_cell(field_spec.description),
        ]
        if include_target:
            row.append(_target_cell(field_spec, targets))
        if include_deprecated:
            deprecated = field_spec.deprecated
            row.append(
                _paragraph(
                    "Yes"
                    if deprecated is True
                    else ""
                    if deprecated in {False, None}
                    else deprecated
                )
            )
        if include_links:
            row.append(_links_cell(field_spec.links))
        row.extend(
            _paragraph(_display_value(field_spec.metadata.get(metadata_key)))
            for metadata_key in policy.metadata_columns
        )
        rows.append(row)

    table_options: dict[str, object] = {}
    if not isinstance(policy.table_style, str):
        table_options["repeat_header_rows"] = True
    return Table(
        headers,
        rows,
        caption=caption if caption is not None else f"Fields in {schema.key}.",
        style=policy.table_style,
        split=True,
        **table_options,
    )


def _schema_description_blocks(schema: SchemaSpec) -> list[Block]:
    blocks: list[Block] = []
    if schema.description is not None:
        values = (
            schema.description
            if isinstance(schema.description, Sequence)
            and not isinstance(schema.description, (str, bytes, Block))
            else (schema.description,)
        )
        blocks.extend(coerce_blocks(values))  # type: ignore[arg-type]
    if schema.deprecated is not None:
        value = (
            "Yes"
            if schema.deprecated is True
            else "No"
            if schema.deprecated is False
            else schema.deprecated
        )
        blocks.append(Paragraph("Deprecated: ", value))
    if schema.links:
        blocks.append(Paragraph("Links: ", _links_cell(schema.links).content))
    return blocks


def _schema_anchor(key: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", key.casefold()).strip("-")
    return f"schema-{normalized or 'item'}"


def schema_to_section(
    schema: SchemaSpec,
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
    """Build one schema section from ordinary paragraph and table blocks."""

    return Section(
        schema.title if title is None else title,
        *_schema_description_blocks(schema),
        schema_to_table(
            schema,
            presentation=presentation,
            requirement_labels=requirement_labels,
            type_labels=type_labels,
            targets=targets,
        ),
        level=level,
        numbered=numbered,
        toc=toc,
        anchor=_schema_anchor(schema.key),
    )


def catalog_to_chapter(
    catalog: SchemaCatalog,
    *,
    title: InlineInput = "Schema reference",
    presentation: SchemaPresentation | None = None,
    requirement_labels: Mapping[RequirementLevel, InlineInput] | None = None,
    type_labels: Mapping[str, InlineInput] | None = None,
    numbered: bool = True,
    toc: bool = True,
) -> Chapter:
    """Create schema sections once, then populate links against those objects."""

    sections: list[Section] = []
    targets: dict[str, Section] = {}
    anchor_counts: dict[str, int] = {}
    for schema in catalog.schemas:
        anchor = _schema_anchor(schema.key)
        anchor_counts[anchor] = anchor_counts.get(anchor, 0) + 1
        if anchor_counts[anchor] > 1:
            anchor = f"{anchor}-{anchor_counts[anchor]}"
        section = Section(
            schema.title,
            level=2,
            numbered=numbered,
            toc=toc,
            anchor=anchor,
        )
        sections.append(section)
        targets.setdefault(schema.key, section)

    for schema, section in zip(catalog.schemas, sections):
        section.extend(_schema_description_blocks(schema))
        section.add(
            schema_to_table(
                schema,
                presentation=presentation,
                requirement_labels=requirement_labels,
                type_labels=type_labels,
                targets=targets,
            )
        )

    return Chapter(title, sections, numbered=numbered, toc=toc)


__all__ = [
    "DEFAULT_REQUIREMENT_LABELS",
    "GENERIC_VALUE_TYPES",
    "SchemaPresentation",
    "catalog_to_chapter",
    "schema_to_section",
    "schema_to_table",
]
