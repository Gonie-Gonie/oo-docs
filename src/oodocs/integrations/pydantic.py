"""Lazy optional Pydantic-to-schema integration."""

from __future__ import annotations

from typing import Any

from oodocs.integrations.json_schema import collect_json_schema
from oodocs.schema import SchemaCatalog, SchemaDiagnostic


def collect_pydantic_schema(
    model: type[object],
    *,
    key: str | None = None,
    title: object | None = None,
) -> SchemaCatalog:
    """Collect a Pydantic model without importing Pydantic at module import.

    Pydantic v2's ``model_json_schema`` and v1's ``schema`` are both
    supported. Interpretation and loss diagnostics are delegated to the JSON
    Schema integration.
    """

    try:
        import pydantic  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional environment
        raise ImportError(
            "collect_pydantic_schema requires the optional 'pydantic' package"
        ) from exc

    base_model = getattr(pydantic, "BaseModel", None)
    if not isinstance(model, type) or base_model is None or not issubclass(model, base_model):
        raise TypeError("collect_pydantic_schema expects a Pydantic BaseModel type")

    model_json_schema = getattr(model, "model_json_schema", None)
    if callable(model_json_schema):
        payload: Any = model_json_schema(ref_template="#/$defs/{model}")
        version = "v2"
    else:
        schema_method = getattr(model, "schema", None)
        if not callable(schema_method):
            raise TypeError("Pydantic model does not expose a JSON Schema method")
        payload = schema_method(ref_template="#/definitions/{model}")
        version = "v1"
    if not isinstance(payload, dict):
        raise TypeError("Pydantic JSON Schema output must be a mapping")

    catalog = collect_json_schema(
        payload,
        key=key or model.__name__,
        title=title,
    )
    catalog.diagnostics = (
        *catalog.diagnostics,
        SchemaDiagnostic(
            "pydantic-json-schema-adapter",
            (
                f"Pydantic {version} metadata was interpreted through its JSON "
                "Schema representation; inspect raw records for framework-only details."
            ),
            path="schema_catalog",
            source="pydantic",
            keyword="model_json_schema" if version == "v2" else "schema",
        ),
    )
    catalog.metadata = {
        **catalog.metadata,
        "source": "pydantic",
        "pydantic_version": getattr(pydantic, "__version__", None),
        "root_model": f"{model.__module__}.{model.__qualname__}",
    }
    return catalog


__all__ = ["collect_pydantic_schema"]
