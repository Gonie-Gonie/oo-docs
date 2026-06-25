"""Griffe-backed API collector."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import textwrap
from typing import Iterable

from oodocs.apidoc.config import ApiCollectConfig
from oodocs.apidoc.docstring import ParsedDocstring, parse_docstring
from oodocs.apidoc.model import (
    ApiDocIssue,
    ApiModule,
    ApiObject,
    ApiPackage,
    ApiParameter,
    ApiReturn,
)
from oodocs.core import PathLike


_DEPRECATION_DECORATORS = {"deprecated", "deprecate", "deprecated_alias"}


def collect_package_griffe(
    package: str | PathLike,
    *,
    config: ApiCollectConfig,
) -> ApiPackage:
    """Collect package API metadata with griffe.

    Args:
        package: Importable package/module name, Python file, or package
            directory.
        config: Collection config.

    Returns:
        Collected API package.

    Notes:
        ``griffe`` is optional. If it is unavailable or cannot load the target,
        this function falls back to the source collector and records a
        diagnostic issue while preserving the same public schema.

    Examples:
        Prefer griffe-compatible collection for a normal source-layout
        repository and then render the result through OODocs:

        ```python
        from oodocs.apidoc import ApiCollectConfig
        from oodocs.apidoc.collect_griffe import collect_package_griffe

        config = ApiCollectConfig(
            collector="griffe",
            public_policy="__all__",
            docstring_style="auto",
            module_exclude_patterns=("mypkg.tests*",),
        )
        api = collect_package_griffe(".", config=config)
        api.to_document(profile="reference").save_all(
            "artifacts/api",
            stem="mypkg-api",
        )
        ```
    """

    try:
        import griffe
    except Exception:
        return _fallback_collect(
            package,
            config=config,
            code="griffe-unavailable",
            message="griffe is not installed; used source parsing with griffe-compatible output.",
        )

    from oodocs.apidoc.collect import (
        _module_is_included,
        _module_name_for_file,
        _package_version,
        _resolve_source_files,
    )

    resolved = replace(config, collector="griffe")
    try:
        root, package_name, files = _resolve_source_files(package)
        loaded = griffe.load(
            package_name,
            search_paths=[str(root)],
            submodules=True,
            allow_inspection=False,
        )
    except Exception as exc:
        return _fallback_collect(
            package,
            config=resolved,
            code="griffe-load-failed",
            message=f"griffe could not load the target; used source parsing instead: {exc}",
        )

    modules: list[ApiModule] = []
    issues: list[ApiDocIssue] = []
    for module_obj in _iter_griffe_modules(loaded):
        filepath = _object_filepath(module_obj)
        if filepath is None:
            continue
        module_name = _module_name_for_file(filepath, root=root, package_name=package_name)
        if not _module_is_included(module_name, resolved):
            continue
        module = _module_from_griffe(module_obj, module_name, config=resolved)
        modules.append(module)
        issues.extend(_module_issues(module))

    collected_names = {module.name for module in modules}
    for file_path in files:
        module_name = _module_name_for_file(file_path, root=root, package_name=package_name)
        if not _module_is_included(module_name, resolved):
            continue
        if module_name not in collected_names:
            issues.append(
                ApiDocIssue(
                    "warning",
                    "griffe-module-missing",
                    "griffe did not return this source module.",
                    module=module_name,
                    path=str(file_path),
                )
            )

    return ApiPackage(
        package_name,
        version=_package_version(package_name),
        modules=sorted(modules, key=lambda item: item.name),
        issues=issues,
        metadata={
            "collector": "griffe",
            "file_count": sum(
                1
                for file_path in files
                if _module_is_included(
                    _module_name_for_file(file_path, root=root, package_name=package_name),
                    resolved,
                )
            ),
            "public_policy": resolved.public_policy,
            "source_root": str(root),
        },
    )


def _fallback_collect(
    package: str | PathLike,
    *,
    config: ApiCollectConfig,
    code: str,
    message: str,
) -> ApiPackage:
    from oodocs.apidoc.collect import _collect_package_source

    api = _collect_package_source(package, config=replace(config, collector="griffe"))
    api.issues.append(ApiDocIssue("info", code, message))
    return api


def _module_from_griffe(
    module_obj: object,
    module_name: str,
    *,
    config: ApiCollectConfig,
) -> ApiModule:
    parsed = _parse_object_docstring(module_obj, module=module_name, config=config)
    public_names = _griffe_all_names(module_obj)
    module = ApiModule(
        module_name,
        summary=parsed.summary,
        description=parsed.description,
        notes=parsed.notes,
        warnings=parsed.warnings,
        renderer_notes=parsed.renderer_notes,
        source_path=str(_object_filepath(module_obj)) if _object_filepath(module_obj) else None,
        metadata={"__all__": sorted(public_names) if public_names is not None else None},
    )
    members: list[ApiObject] = []
    for name, member in _members(module_obj).items():
        if name == "__all__" or _kind(member) == "module":
            continue
        is_alias = bool(getattr(member, "is_alias", False))
        is_public_reexport = public_names is not None and name in public_names
        if is_alias and not config.include_imported and not is_public_reexport:
            continue
        target = _final_target(member)
        if target is None:
            continue
        if _kind(target) not in {"class", "function", "attribute"}:
            continue
        if not _is_public_name(name, f"{module_name}.{name}", public_names, config):
            continue
        obj = _object_from_griffe(
            target,
            local_name=name,
            module_name=module_name,
            config=config,
            parent_class=None,
        )
        if obj is not None:
            if is_alias:
                obj.metadata["reexported_from"] = getattr(member, "target_path", None) or getattr(target, "path", None)
            members.append(obj)
    from oodocs.apidoc.collect import _merge_attribute_docs

    module.members = sorted(
        _merge_attribute_docs(members, parsed.attributes),
        key=lambda item: (item.line_number or 0, item.name),
    )
    return module


def _object_from_griffe(
    obj: object,
    *,
    local_name: str,
    module_name: str,
    config: ApiCollectConfig,
    parent_class: str | None,
) -> ApiObject | None:
    kind = _kind(obj)
    if kind == "class":
        return _class_from_griffe(obj, local_name=local_name, module_name=module_name, config=config)
    if kind == "function":
        return _function_from_griffe(
            obj,
            local_name=local_name,
            module_name=module_name,
            config=config,
            parent_class=parent_class,
        )
    if kind == "attribute":
        return _attribute_from_griffe(
            obj,
            local_name=local_name,
            module_name=module_name,
            parent_class=parent_class,
            config=config,
        )
    return None


def _class_from_griffe(
    obj: object,
    *,
    local_name: str,
    module_name: str,
    config: ApiCollectConfig,
) -> ApiObject:
    qualname = f"{module_name}.{local_name}"
    parsed = _parse_object_docstring(obj, qualname=qualname, module=module_name, config=config)
    init_parsed = None
    if not parsed.parameters:
        init_member = _final_target(_members(obj).get("__init__"))
        if init_member is not None:
            init_parsed = _parse_object_docstring(
                init_member,
                qualname=f"{qualname}.__init__",
                module=module_name,
                config=config,
            )
    signature_parameters = []
    if config.class_signature_from_init:
        signature_parameters = _parameters_from_griffe(getattr(obj, "parameters", ()), drop_first=True)
    from oodocs.apidoc.collect import _class_parameter_docs

    parameters, extra_issues = _merge_parameters(
        signature_parameters,
        _class_parameter_docs(signature_parameters, parsed, init_parsed),
        qualname=qualname,
        module=module_name,
        path=_object_filepath(obj),
        line_number=getattr(obj, "lineno", None),
    )
    members: list[ApiObject] = []
    for name, member in _members(obj).items():
        if name == "__init__" or not config.include_inherited and _is_inherited(member, obj):
            continue
        target = _final_target(member)
        if target is None:
            continue
        if not _class_member_is_public(name, config, f"{qualname}.{name}"):
            continue
        child = _object_from_griffe(
            target,
            local_name=name,
            module_name=module_name,
            config=config,
            parent_class=local_name,
        )
        if child is not None:
            members.append(child)
    from oodocs.apidoc.collect import _class_attribute_docs, _merge_attribute_docs

    members = _merge_attribute_docs(members, _class_attribute_docs(parsed))
    signature = f"{qualname}({_signature_parameter_text(parameters)})"
    decorators = [_decorator_name(decorator) for decorator in getattr(obj, "decorators", [])]
    deprecated = parsed.deprecated or _has_deprecation_decorator(decorators)
    return ApiObject(
        kind="class",
        name=local_name,
        qualname=qualname,
        module=module_name,
        visibility=_visibility_for(local_name),
        signature=signature,
        summary=parsed.summary,
        description=parsed.description,
        parameters=parameters,
        returns=parsed.returns,
        raises=parsed.raises,
        examples=parsed.examples,
        see_also=parsed.see_also,
        notes=parsed.notes,
        warnings=parsed.warnings,
        renderer_notes=parsed.renderer_notes,
        members=sorted(members, key=lambda item: (item.line_number or 0, item.name)),
        source_path=str(_object_filepath(obj)) if _object_filepath(obj) else None,
        line_number=getattr(obj, "lineno", None),
        end_line_number=getattr(obj, "endlineno", None),
        deprecated=deprecated,
        deprecation_message=parsed.deprecation_message,
        metadata={
            "decorators": [name for name in decorators if name],
            "docstring_style": parsed.style,
            "issues": [
                issue.to_dict()
                for issue in [
                    *parsed.issues,
                    *(init_parsed.issues if init_parsed else []),
                    *extra_issues,
                ]
            ],
        },
    )


def _function_from_griffe(
    obj: object,
    *,
    local_name: str,
    module_name: str,
    config: ApiCollectConfig,
    parent_class: str | None,
) -> ApiObject:
    labels = set(getattr(obj, "labels", set()) or set())
    qualname = f"{module_name}.{parent_class}.{local_name}" if parent_class else f"{module_name}.{local_name}"
    parsed = _parse_object_docstring(obj, qualname=qualname, module=module_name, config=config)
    drop_first = parent_class is not None and "staticmethod" not in labels
    signature_parameters = _parameters_from_griffe(getattr(obj, "parameters", ()), drop_first=drop_first)
    parameters, extra_issues = _merge_parameters(
        signature_parameters,
        parsed.parameters,
        qualname=qualname,
        module=module_name,
        path=_object_filepath(obj),
        line_number=getattr(obj, "lineno", None),
    )
    return_annotation = _display_expr(getattr(obj, "returns", None))
    returns = parsed.returns
    if return_annotation:
        if returns is None:
            returns = ApiReturn(annotation=return_annotation, documented=False)
        elif returns.annotation is None:
            returns.annotation = return_annotation
    signature = f"{qualname}({_signature_parameter_text(parameters)})"
    if return_annotation:
        signature = f"{signature} -> {return_annotation}"
    decorators = [_decorator_name(decorator) for decorator in getattr(obj, "decorators", [])]
    warning_message = _griffe_deprecation_warning_message(obj)
    deprecated = (
        parsed.deprecated
        or _has_deprecation_decorator(decorators)
        or warning_message is not None
    )
    return ApiObject(
        kind="method" if parent_class else "function",
        name=local_name,
        qualname=qualname,
        module=module_name,
        visibility=_visibility_for(local_name),
        signature=signature,
        summary=parsed.summary,
        description=parsed.description,
        parameters=parameters,
        returns=returns,
        raises=parsed.raises,
        examples=parsed.examples,
        see_also=parsed.see_also,
        notes=parsed.notes,
        warnings=parsed.warnings,
        renderer_notes=parsed.renderer_notes,
        source_path=str(_object_filepath(obj)) if _object_filepath(obj) else None,
        line_number=getattr(obj, "lineno", None),
        end_line_number=getattr(obj, "endlineno", None),
        deprecated=deprecated,
        deprecation_message=parsed.deprecation_message or warning_message,
        metadata={
            "decorators": [name for name in decorators if name],
            "docstring_style": parsed.style,
            "issues": [issue.to_dict() for issue in [*parsed.issues, *extra_issues]],
        },
    )


def _attribute_from_griffe(
    obj: object,
    *,
    local_name: str,
    module_name: str,
    parent_class: str | None,
    config: ApiCollectConfig,
) -> ApiObject:
    labels = set(getattr(obj, "labels", set()) or set())
    qualname = f"{module_name}.{parent_class}.{local_name}" if parent_class else f"{module_name}.{local_name}"
    parsed = _parse_object_docstring(obj, qualname=qualname, module=module_name, config=config)
    annotation = _display_expr(getattr(obj, "annotation", None))
    default = _display_expr(getattr(obj, "value", None))
    kind = "property" if "property" in labels else ("attribute" if parent_class else "data")
    return ApiObject(
        kind=kind,  # type: ignore[arg-type]
        name=local_name,
        qualname=qualname,
        module=module_name,
        visibility=_visibility_for(local_name),
        signature=f"{local_name}: {annotation}" if annotation else local_name,
        summary=parsed.summary,
        description=parsed.description,
        parameters=parsed.parameters,
        returns=ApiReturn(annotation=annotation, description=parsed.summary, documented=bool(parsed.summary))
        if kind == "property" and annotation
        else parsed.returns,
        raises=parsed.raises,
        examples=parsed.examples,
        see_also=parsed.see_also,
        notes=parsed.notes,
        warnings=parsed.warnings,
        renderer_notes=parsed.renderer_notes,
        source_path=str(_object_filepath(obj)) if _object_filepath(obj) else None,
        line_number=getattr(obj, "lineno", None),
        end_line_number=getattr(obj, "endlineno", None),
        deprecated=parsed.deprecated,
        deprecation_message=parsed.deprecation_message,
        metadata={
            "default": default,
            "docstring_style": parsed.style,
            "griffe_labels": sorted(labels),
            "issues": [issue.to_dict() for issue in parsed.issues],
        },
    )


def _parse_object_docstring(
    obj: object,
    *,
    config: ApiCollectConfig,
    qualname: str | None = None,
    module: str | None = None,
) -> ParsedDocstring:
    docstring = getattr(obj, "docstring", None)
    return parse_docstring(
        getattr(docstring, "value", None),
        style=config.docstring_style,
        qualname=qualname,
        module=module,
    )


def _parameters_from_griffe(parameters: Iterable[object], *, drop_first: bool) -> list[ApiParameter]:
    items = list(parameters)
    if drop_first and items and getattr(items[0], "name", None) in {"self", "cls"}:
        items = items[1:]
    result: list[ApiParameter] = []
    for parameter in items:
        default = _display_expr(getattr(parameter, "default", None))
        result.append(
            ApiParameter(
                name=str(getattr(parameter, "name", "")),
                annotation=_display_expr(getattr(parameter, "annotation", None)),
                default=default,
                kind=_display_parameter_kind(getattr(parameter, "kind", None)),
                required=default is None,
                documented=False,
                source="signature",
            )
        )
    return [parameter for parameter in result if parameter.name]


def _merge_parameters(
    signature_parameters: list[ApiParameter],
    doc_parameters: list[ApiParameter],
    *,
    qualname: str,
    module: str,
    path: Path | None,
    line_number: int | None,
) -> tuple[list[ApiParameter], list[ApiDocIssue]]:
    issues: list[ApiDocIssue] = []
    doc_by_name = {_normalize_param_name(parameter.name): parameter for parameter in doc_parameters}
    merged: list[ApiParameter] = []
    for parameter in signature_parameters:
        doc_parameter = doc_by_name.pop(_normalize_param_name(parameter.name), None)
        if doc_parameter is not None:
            parameter.description = doc_parameter.description
            parameter.documented = True
            if parameter.annotation is None:
                parameter.annotation = doc_parameter.annotation
        merged.append(parameter)
    for extra in doc_by_name.values():
        extra.source = "docstring"
        merged.append(extra)
        issues.append(
            ApiDocIssue(
                "warning",
                "extra-parameter-doc",
                f"Docstring documents parameter {extra.name!r} that is not in the signature.",
                qualname=qualname,
                module=module,
                path=str(path) if path else None,
                line_number=line_number,
            )
        )
    return merged, issues


def _iter_griffe_modules(obj: object) -> list[object]:
    modules: list[object] = []
    if _kind(obj) == "module":
        modules.append(obj)
    for member in _members(obj).values():
        target = _final_target(member)
        if target is not None and _kind(target) == "module":
            modules.extend(_iter_griffe_modules(target))
    unique: dict[str, object] = {}
    for module in modules:
        unique[getattr(module, "path", "")] = module
    return list(unique.values())


def _module_issues(module: ApiModule) -> list[ApiDocIssue]:
    issues: list[ApiDocIssue] = []
    for obj in module.iter_objects(recursive=True):
        for item in obj.metadata.get("issues", []):
            if isinstance(item, dict):
                issues.append(ApiDocIssue.from_dict(item))
    return issues


def _members(obj: object) -> dict[str, object]:
    return dict(getattr(obj, "members", {}) or {})


def _final_target(obj: object) -> object | None:
    if getattr(obj, "is_alias", False):
        try:
            return getattr(obj, "final_target")
        except Exception:
            return None
    return obj


def _griffe_all_names(module_obj: object) -> set[str] | None:
    member = _members(module_obj).get("__all__")
    value = _display_expr(getattr(member, "value", None)) if member is not None else None
    if not value:
        return None
    try:
        import ast

        parsed = ast.literal_eval(value)
    except Exception:
        return None
    if isinstance(parsed, (list, tuple, set)):
        return {item for item in parsed if isinstance(item, str)}
    return None


def _kind(obj: object) -> str:
    kind = getattr(obj, "kind", None)
    return str(getattr(kind, "value", kind or "")).lower()


def _object_filepath(obj: object) -> Path | None:
    value = getattr(obj, "filepath", None)
    if isinstance(value, (list, tuple, set)):
        value = next(iter(value), None)
    if value is None:
        return None
    return Path(value)


def _display_expr(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text in {"", "None"}:
        return None
    return text


def _display_parameter_kind(value: object) -> str | None:
    if value is None:
        return None
    text = str(getattr(value, "value", value))
    return text.replace(" ", "-")


def _signature_parameter_text(parameters: list[ApiParameter]) -> str:
    pieces: list[str] = []
    for parameter in parameters:
        piece = parameter.name
        if parameter.annotation:
            piece = f"{piece}: {parameter.annotation}"
        if parameter.default is not None:
            piece = f"{piece} = {parameter.default}"
        pieces.append(piece)
    return ", ".join(pieces)


def _normalize_param_name(name: str) -> str:
    return name.lstrip("*")


def _is_public_name(
    name: str,
    qualname: str,
    public_names: set[str] | None,
    config: ApiCollectConfig,
) -> bool:
    return config.public_api_policy().module_name_is_public(name, qualname, public_names)


def _class_member_is_public(
    name: str,
    config: ApiCollectConfig,
    qualname: str | None = None,
) -> bool:
    return config.public_api_policy().member_name_is_public(name, qualname)


def _visibility_for(name: str):
    if name.startswith("__") and name.endswith("__"):
        return "internal"
    if name.startswith("_"):
        return "protected"
    return "public"


def _is_inherited(member: object, owner: object) -> bool:
    member_path = str(getattr(member, "path", ""))
    owner_path = str(getattr(owner, "path", ""))
    return bool(member_path and owner_path and not member_path.startswith(f"{owner_path}."))


def _has_deprecation_decorator(names: Iterable[str | None]) -> bool:
    return any(_decorator_leaf(name) in _DEPRECATION_DECORATORS for name in names if name)


def _decorator_name(decorator: object) -> str | None:
    path = getattr(decorator, "callable_path", None)
    if path:
        return str(path)
    value = getattr(decorator, "value", None)
    return _display_expr(value if value is not None else decorator)


def _decorator_leaf(name: str | None) -> str:
    if not name:
        return ""
    cleaned = str(name).strip().lstrip("@")
    cleaned = cleaned.split("(", 1)[0].strip()
    return cleaned.rsplit(".", 1)[-1]


def _griffe_deprecation_warning_message(obj: object) -> str | None:
    filepath = _object_filepath(obj)
    lineno = getattr(obj, "lineno", None)
    endlineno = getattr(obj, "endlineno", None)
    source: str | None = None
    if filepath is not None and lineno is not None and endlineno is not None:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        source = "\n".join(lines[max(int(lineno) - 1, 0) : int(endlineno)])
    if not source:
        value = getattr(obj, "source", None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if value:
            source = str(value)
    if not source:
        return None
    try:
        module = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return None
    from oodocs.apidoc.collect import _deprecation_warning_message

    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return _deprecation_warning_message(node)
    return None


__all__ = ["collect_package_griffe"]
