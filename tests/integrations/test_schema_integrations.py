from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
import sys
from types import ModuleType

import pytest

from oodocs.integrations.json_schema import collect_json_schema
from oodocs.integrations.pydantic import collect_pydantic_schema
from oodocs.integrations.python import collect_dataclass_schema


@dataclass
class _ChildFixture:
    name: str


@dataclass
class _ParentFixture:
    child: _ChildFixture
    retries: int = field(
        default=3,
        metadata={
            "description": "Retry count.",
            "constraints": ("minimum: 0",),
            "unit": "attempts",
            "deprecated": False,
            "links": ("retry-policy",),
        },
    )
    tags: list[str] = field(default_factory=list)


@dataclass
class _GroupFixture:
    children: list[_ChildFixture]


def test_json_schema_collector_preserves_records_links_defs_and_diagnostics() -> None:
    source = {
        "title": "Graph",
        "type": "object",
        "properties": {
            "node": {"$ref": "#/$defs/Node", "description": "Root node."},
        },
        "$defs": {
            "Node": {
                "title": "Node",
                "type": "object",
                "properties": {
                    "parent": {"$ref": "#/$defs/Node"},
                    "label": {
                        "type": "string",
                        "minLength": 1,
                        "vendorKeyword": "retained",
                    },
                },
                "required": ["label"],
            }
        },
        "oneOf": [{"required": ["node"]}],
    }

    catalog = collect_json_schema(source, key="graph")
    assert [schema.key for schema in catalog.schemas] == ["graph", "Node"]
    assert catalog.schemas[0].fields[0].target_schema == "Node"
    assert catalog.schemas[1].fields[0].target_schema == "Node"
    label = catalog.schemas[1].fields[1]
    assert label.requirement == "required"
    assert label.constraints == ("minimum length: 1",)
    assert label.raw_record["vendorKeyword"] == "retained"
    assert catalog.raw_record["$defs"] is source["$defs"]
    assert {diagnostic.code for diagnostic in catalog.diagnostics} >= {
        "json-schema-lossy-keyword",
        "json-schema-unsupported-keyword",
    }
    assert catalog.validate().ok


def test_json_schema_collector_keeps_definitions_only_root_diagnostics() -> None:
    catalog = collect_json_schema(
        {
            "$defs": {
                "Item": {"type": "object", "properties": {}},
            },
            "oneOf": [{"$ref": "#/$defs/Item"}],
            "vendorRoot": "retained",
        },
        key="root",
    )

    assert [schema.key for schema in catalog.schemas] == ["root", "Item"]
    assert catalog.schemas[0].raw_record["vendorRoot"] == "retained"
    assert {diagnostic.code for diagnostic in catalog.diagnostics} >= {
        "json-schema-lossy-keyword",
        "json-schema-unsupported-keyword",
    }


def test_dataclass_collector_handles_nested_types_metadata_and_safe_factories() -> None:
    catalog = collect_dataclass_schema(_ParentFixture, key="parent")
    assert [schema.key for schema in catalog.schemas] == ["parent", "_ChildFixture"]
    parent = catalog.schemas[0]
    assert parent.fields[0].value_type == "object"
    assert parent.fields[0].target_schema == "_ChildFixture"
    assert parent.fields[0].requirement == "required"
    assert parent.fields[1].default == 3
    assert parent.fields[1].constraints == ("minimum: 0",)
    assert parent.fields[1].unit == "attempts"
    assert parent.fields[2].value_type == "array"
    assert parent.fields[2].default.startswith("<factory")
    assert any(
        diagnostic.code == "python-dataclass-default-factory-not-evaluated"
        for diagnostic in catalog.diagnostics
    )
    assert catalog.validate().ok

    group_catalog = collect_dataclass_schema(_GroupFixture, key="group")
    assert [schema.key for schema in group_catalog.schemas] == [
        "group",
        "_ChildFixture",
    ]
    assert group_catalog.schemas[0].fields[0].value_type == "array"
    assert group_catalog.schemas[0].fields[0].target_schema == "_ChildFixture"


def test_pydantic_collector_keeps_optional_dependency_lazy() -> None:
    class NotAPydanticModel:
        pass

    if importlib.util.find_spec("pydantic") is None:
        with pytest.raises(ImportError, match="optional 'pydantic'"):
            collect_pydantic_schema(NotAPydanticModel)
    else:
        with pytest.raises(TypeError, match="Pydantic BaseModel"):
            collect_pydantic_schema(NotAPydanticModel)


def test_pydantic_collector_supports_v2_and_v1_schema_methods(monkeypatch) -> None:
    pydantic_module = ModuleType("pydantic")

    class BaseModel:
        pass

    pydantic_module.BaseModel = BaseModel
    pydantic_module.__version__ = "test"
    monkeypatch.setitem(sys.modules, "pydantic", pydantic_module)

    class V2Model(BaseModel):
        @classmethod
        def model_json_schema(cls, *, ref_template: str):
            assert ref_template == "#/$defs/{model}"
            return {
                "title": "V2 model",
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }

    class V1Model(BaseModel):
        @classmethod
        def schema(cls, *, ref_template: str):
            assert ref_template == "#/definitions/{model}"
            return {
                "title": "V1 model",
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
            }

    v2_catalog = collect_pydantic_schema(V2Model)
    v1_catalog = collect_pydantic_schema(V1Model)

    assert v2_catalog.schemas[0].fields[0].requirement == "required"
    assert v2_catalog.schemas[0].fields[0].value_type == "string"
    assert v1_catalog.schemas[0].fields[0].requirement == "optional"
    assert v1_catalog.schemas[0].fields[0].value_type == "boolean"
    assert v2_catalog.metadata["source"] == "pydantic"
    assert v1_catalog.metadata["source"] == "pydantic"
    assert any(
        diagnostic.code == "pydantic-json-schema-adapter"
        for diagnostic in (*v2_catalog.diagnostics, *v1_catalog.diagnostics)
    )
