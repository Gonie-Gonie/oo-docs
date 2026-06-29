"""Write a deterministic inventory of the public OODocs API surface."""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import types
from typing import Any, Literal, get_origin


INVENTORY_MODULES = (
    "oodocs",
    "oodocs.chem",
    "oodocs.apidoc",
    "oodocs.adapters",
    "oodocs.importers.markdown",
    "oodocs.importers.notebook",
    "oodocs.styles",
    "oodocs.validation",
    "oodocs.workflows",
    "oodocs.presets",
)

CATEGORIES = {
    "document-core",
    "block",
    "inline",
    "media",
    "generated-page",
    "settings",
    "style",
    "theme",
    "validation",
    "importer",
    "workflow",
    "adapter",
    "apidoc-model",
    "apidoc-collector",
    "apidoc-parser",
    "apidoc-coverage",
    "apidoc-diff",
    "apidoc-composition",
    "preset",
    "compatibility",
    "error",
    "constant",
}

APIDOC_MODULE_CATEGORIES = {
    "oodocs.apidoc.blocks": "apidoc-composition",
    "oodocs.apidoc.collect": "apidoc-collector",
    "oodocs.apidoc.collect_griffe": "apidoc-collector",
    "oodocs.apidoc.collect_inspect": "apidoc-collector",
    "oodocs.apidoc.config": "apidoc-collector",
    "oodocs.apidoc.builtin_categories": "apidoc-composition",
    "oodocs.apidoc.categories": "apidoc-composition",
    "oodocs.apidoc.coverage": "apidoc-coverage",
    "oodocs.apidoc.diff": "apidoc-diff",
    "oodocs.apidoc.docstring": "apidoc-parser",
    "oodocs.apidoc.examples": "apidoc-parser",
    "oodocs.apidoc.help": "apidoc-composition",
    "oodocs.apidoc.model": "apidoc-model",
    "oodocs.apidoc.render": "apidoc-composition",
    "oodocs.apidoc.profiles": "apidoc-composition",
}

EXACT_CATEGORIES = {
    "__version__": "constant",
    "MAX_SECTION_LEVEL": "constant",
    "MIN_SECTION_LEVEL": "constant",
    "OUTPUT_FORMATS": "compatibility",
    "OutputFormat": "compatibility",
    "OODocsError": "error",
    "DocumentValidationError": "error",
    "ImportPolicyError": "error",
    "ApiDocIssueSeverity": "apidoc-model",
    "ApiDocstringStyleName": "apidoc-parser",
    "ApiCollectorName": "apidoc-collector",
    "ApiFallbackCollectorName": "apidoc-collector",
    "ApiKind": "apidoc-model",
    "ApiPresentationProfileName": "apidoc-composition",
    "ApiPublicPolicyName": "apidoc-collector",
    "ApiVisibility": "apidoc-model",
    "OODocs_API_CATEGORIES": "apidoc-composition",
    "ValidationSeverity": "validation",
}


def build_inventory(*, branch: str | None = None) -> dict[str, object]:
    """Build a public API inventory from module ``__all__`` lists.

    Args:
        branch: Optional branch label to write into the inventory. When
            omitted, the current Git branch is detected.

    Returns:
        Deterministic JSON-serializable inventory.

    Raises:
        SystemExit: If an exported symbol cannot be categorized.
    """

    issues: list[dict[str, object]] = []
    modules: dict[str, object] = {}
    uncategorized: list[str] = []

    for module_name in INVENTORY_MODULES:
        module = importlib.import_module(module_name)
        exports: list[dict[str, object]] = []
        for export_name in getattr(module, "__all__", ()):
            if not hasattr(module, export_name):
                issues.append(
                    {
                        "module": module_name,
                        "name": export_name,
                        "code": "missing-export",
                        "message": "Export is listed in __all__ but is not importable.",
                    }
                )
                exports.append(
                    {
                        "name": export_name,
                        "kind": "unknown",
                        "module": None,
                        "qualname": export_name,
                        "category": category_for(module_name, export_name, None),
                    }
                )
                continue

            obj = getattr(module, export_name)
            kind = object_kind(obj)
            object_module = object_module_name(obj, kind)
            category = category_for(module_name, export_name, object_module)
            if category is None:
                uncategorized.append(f"{module_name}:{export_name}")
                category = "constant"
            elif category not in CATEGORIES:
                uncategorized.append(f"{module_name}:{export_name}:{category}")
                category = "constant"
            if kind == "unknown":
                issues.append(
                    {
                        "module": module_name,
                        "name": export_name,
                        "code": "unknown-export-kind",
                        "message": "Export kind could not be determined by inspect.",
                    }
                )
            exports.append(
                {
                    "name": export_name,
                    "kind": kind,
                    "module": object_module,
                    "qualname": object_qualname(export_name, obj),
                    "category": category,
                }
            )
        modules[module_name] = {"exports": exports}

    if uncategorized:
        joined = ", ".join(sorted(uncategorized))
        raise SystemExit(f"Uncategorized public API exports: {joined}")

    return {
        "package": "oodocs",
        "branch": branch or current_branch(),
        "modules": modules,
        "issues": issues,
    }


def object_kind(obj: Any) -> str:
    """Return the inventory kind for an exported object."""

    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        return "function"
    if get_origin(obj) is Literal or isinstance(obj, (types.GenericAlias, types.UnionType)):
        return "type-alias"
    if type(obj).__module__ == "typing":
        return "type-alias"
    if isinstance(obj, (str, int, float, bool, tuple, frozenset, type(None))):
        return "constant"
    return "unknown"


def object_module_name(obj: Any, kind: str) -> str | None:
    """Return a stable module label for an exported object."""

    if kind == "type-alias":
        return "typing"
    return getattr(obj, "__module__", None)


def object_qualname(export_name: str, obj: Any) -> str:
    """Return the best stable qualified name for an exported object."""

    if object_kind(obj) == "type-alias":
        return export_name
    module_name = getattr(obj, "__module__", None)
    qualname = getattr(obj, "__qualname__", None)
    if module_name and qualname:
        return f"{module_name}.{qualname}"
    return export_name


def category_for(
    inventory_module: str,
    export_name: str,
    object_module: str | None,
) -> str | None:
    """Return the cleanup category for one export."""

    if export_name in EXACT_CATEGORIES:
        return EXACT_CATEGORIES[export_name]
    if inventory_module == "oodocs.apidoc":
        return APIDOC_MODULE_CATEGORIES.get(object_module or "")
    if inventory_module == "oodocs.adapters":
        return "adapter"
    if inventory_module == "oodocs.chem":
        if export_name == "ReactionEquation":
            return "block"
        return "inline"
    if inventory_module.startswith("oodocs.importers."):
        return "importer"
    if inventory_module == "oodocs.validation":
        return "validation"
    if inventory_module == "oodocs.workflows":
        return "workflow"
    if inventory_module == "oodocs.presets":
        return "preset"
    if inventory_module == "oodocs.styles":
        if export_name == "Theme" or export_name.endswith("Defaults"):
            return "theme"
        return "style"

    module = object_module or ""
    if module == "oodocs.core":
        return "error"
    if module == "oodocs.compatibility":
        return "compatibility"
    if module == "oodocs.document":
        return "document-core"
    if module.startswith("oodocs.importers."):
        return "importer"
    if module == "oodocs.components.blocks":
        return "block"
    if module == "oodocs.components.generated":
        return "generated-page"
    if module in {"oodocs.components.inline", "oodocs.components.chemistry"}:
        return "inline"
    if module == "oodocs.components.glossary":
        return "document-core"
    if module in {"oodocs.components.media", "oodocs.components.positioning"}:
        return "media"
    if module in {"oodocs.components.people", "oodocs.settings"}:
        return "settings"
    if module in {"oodocs.components.references", "oodocs.components.markup"}:
        return "document-core"
    if module == "oodocs.importers.results":
        return "importer"
    if module == "oodocs.validation":
        return "validation"
    if module == "oodocs.workflows":
        return "workflow"
    if module.startswith("oodocs.styles."):
        if export_name == "Theme":
            return "theme"
        if export_name.endswith("Defaults"):
            return "theme"
        return "style"
    return None


def current_branch() -> str:
    """Return the current Git branch or commit label."""

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    branch = result.stdout.strip()
    if branch:
        return branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def main(argv: list[str] | None = None) -> int:
    """Run the public API inventory writer."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="artifacts/api-surface/public-api-inventory.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--branch",
        help="Branch label to write into the inventory. Defaults to the current Git branch.",
    )
    args = parser.parse_args(argv)

    inventory = build_inventory(branch=args.branch)
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote public API inventory: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
