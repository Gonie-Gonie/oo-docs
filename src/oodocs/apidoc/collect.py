"""Public facade for collecting Python API documentation metadata."""

from __future__ import annotations

import ast
from dataclasses import replace
import importlib.metadata
import importlib.util
from pathlib import Path
from typing import Iterable

from oodocs.apidoc.config import ApiCollectConfig, normalize_explicit_names
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


def collect_api(
    package: str | PathLike,
    *,
    config: ApiCollectConfig | None = None,
    collector: str | None = None,
    public_policy: str | None = None,
    explicit_names: Iterable[str] | None = None,
    docstring_style: str | None = None,
    include_imported: bool | None = None,
    include_inherited: bool | None = None,
    class_signature_from_init: bool | None = None,
) -> ApiPackage:
    """Collect a package or repository into an ``ApiPackage`` tree.

    Args:
        package: Importable package/module name, Python file, or package
            directory.
        config: Optional base collection config.
        collector: Collector backend name. ``"auto"``, ``"griffe"``, and
            ``"inspect"`` currently produce the same normalized schema, with
            source-based collection used when griffe is not installed.
        public_policy: Public API boundary policy.
        explicit_names: Names used with ``public_policy="explicit"``.
        docstring_style: Docstring parser style.
        include_imported: Reserved for import-aware collectors.
        include_inherited: Reserved for import-aware collectors.
        class_signature_from_init: Whether class signatures use ``__init__``.

    Returns:
        Collected API package.

    Examples:
        Select parsed objects and compose them into a normal OODocs document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api

        api = collect_api("oodocs", public_policy="__all__")
        doc = Document("Classes", Chapter("Public Classes", *[
            obj.to_section(level=2) for obj in api.classes()[:3]
        ]))
        ```
    """

    resolved = ApiCollectConfig.from_kwargs(
        config,
        collector=collector,
        public_policy=public_policy,
        explicit_names=normalize_explicit_names(explicit_names),
        docstring_style=docstring_style,
        include_imported=include_imported,
        include_inherited=include_inherited,
        class_signature_from_init=class_signature_from_init,
    )
    if resolved.collector == "inspect":
        from oodocs.apidoc.collect_inspect import collect_package_inspect

        return collect_package_inspect(package, config=resolved)
    if resolved.collector == "griffe":
        from oodocs.apidoc.collect_griffe import collect_package_griffe

        return collect_package_griffe(package, config=resolved)
    try:
        from oodocs.apidoc.collect_griffe import collect_package_griffe

        return collect_package_griffe(package, config=resolved)
    except Exception as exc:  # pragma: no cover - fallback path is environment-sensitive.
        fallback_config = replace(resolved, collector="inspect")
        api = _collect_package_source(package, config=fallback_config)
        api.issues.append(
            ApiDocIssue(
                "info",
                "collector-auto-fallback",
                f"Fell back to inspect-compatible source collection: {exc}",
            )
        )
        return api


def collect_module_api(
    module: str | PathLike,
    *,
    config: ApiCollectConfig | None = None,
    **kwargs: object,
) -> ApiModule:
    """Collect one module into an ``ApiModule``.

    Args:
        module: Importable module name or Python file.
        config: Optional base config.
        **kwargs: Config overrides accepted by ``collect_api``.

    Returns:
        Collected module metadata.
    """

    api = collect_api(module, config=config, **kwargs)
    if len(api.modules) != 1:
        raise ValueError(f"Expected one module, collected {len(api.modules)} modules")
    return api.modules[0]


def collect_object_api(
    obj_or_qualname: str,
    *,
    config: ApiCollectConfig | None = None,
    **kwargs: object,
) -> ApiObject:
    """Collect one object by fully qualified name.

    Args:
        obj_or_qualname: Fully qualified object name.
        config: Optional base config.
        **kwargs: Config overrides accepted by ``collect_api``.

    Returns:
        Matching API object.

    Raises:
        LookupError: If the object cannot be found.
    """

    module_name = obj_or_qualname.rsplit(".", 1)[0]
    api = collect_api(module_name, config=config, **kwargs)
    found = api.find(obj_or_qualname)
    if not isinstance(found, ApiObject):
        raise LookupError(f"API object not found: {obj_or_qualname}")
    return found


def _collect_package_source(
    package: str | PathLike,
    *,
    config: ApiCollectConfig,
) -> ApiPackage:
    root, package_name, files = _resolve_source_files(package)
    issues: list[ApiDocIssue] = []
    modules: list[ApiModule] = []
    for file_path in files:
        module_name = _module_name_for_file(file_path, root=root, package_name=package_name)
        try:
            module = _collect_module_from_file(file_path, module_name, config=config)
        except SyntaxError as exc:
            issues.append(
                ApiDocIssue(
                    "error",
                    "python-syntax-error",
                    str(exc),
                    module=module_name,
                    path=str(file_path),
                    line_number=exc.lineno,
                )
            )
            continue
        modules.append(module)
        issues.extend(_module_issues(module))
    return ApiPackage(
        package_name,
        version=_package_version(package_name),
        modules=sorted(modules, key=lambda item: item.name),
        issues=issues,
        metadata={"collector": config.collector, "public_policy": config.public_policy},
    )


def _collect_module_from_file(
    path: Path,
    module_name: str,
    *,
    config: ApiCollectConfig,
) -> ApiModule:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    parsed_module = parse_docstring(
        ast.get_docstring(tree),
        style=config.docstring_style,
        module=module_name,
    )
    public_names = _module_all_names(tree)
    members: list[ApiObject] = []
    module = ApiModule(
        module_name,
        summary=parsed_module.summary,
        description=parsed_module.description,
        source_path=str(path),
        line_number=1,
        end_line_number=getattr(tree, "end_lineno", None),
        metadata={"__all__": sorted(public_names) if public_names is not None else None},
    )
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_name(node.name, node.name, public_names, config):
                members.append(_function_object(node, module_name, path, config=config, parent=None))
        elif isinstance(node, ast.ClassDef):
            if _is_public_name(node.name, node.name, public_names, config):
                members.append(_class_object(node, module_name, path, config=config))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for name, annotation, default in _assignment_targets(node):
                if _is_public_name(name, name, public_names, config):
                    members.append(
                        ApiObject(
                            kind="data",
                            name=name,
                            qualname=f"{module_name}.{name}",
                            module=module_name,
                            visibility=_visibility_for(name),
                            signature=f"{name}: {annotation}" if annotation else name,
                            summary=None,
                            parameters=[],
                            source_path=str(path),
                            line_number=getattr(node, "lineno", None),
                            end_line_number=getattr(node, "end_lineno", None),
                            metadata={"default": default} if default is not None else {},
                        )
                    )
    module.members = sorted(members, key=lambda obj: (obj.line_number or 0, obj.name))
    return module


def _class_object(
    node: ast.ClassDef,
    module_name: str,
    path: Path,
    *,
    config: ApiCollectConfig,
) -> ApiObject:
    qualname = f"{module_name}.{node.name}"
    parsed = parse_docstring(
        ast.get_docstring(node),
        style=config.docstring_style,
        qualname=qualname,
        module=module_name,
    )
    init_node = _find_method(node, "__init__")
    init_parsed: ParsedDocstring | None = None
    if init_node is not None and not parsed.parameters:
        init_parsed = parse_docstring(
            ast.get_docstring(init_node),
            style=config.docstring_style,
            qualname=f"{qualname}.__init__",
            module=module_name,
        )
    signature = qualname
    signature_parameters: list[ApiParameter] = []
    if config.class_signature_from_init and init_node is not None:
        signature_parameters = _parameters_from_function(init_node, drop_first=True)
        signature = f"{qualname}({_signature_parameter_text(signature_parameters)})"
    parameters, extra_issues = _merge_parameters(
        signature_parameters,
        parsed.parameters or (init_parsed.parameters if init_parsed else []),
        qualname=qualname,
        module=module_name,
        path=path,
        line_number=getattr(node, "lineno", None),
    )
    members: list[ApiObject] = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child.name == "__init__":
                continue
            if _class_member_is_public(child.name, config):
                members.append(_function_object(child, module_name, path, config=config, parent=node.name))
        elif isinstance(child, (ast.Assign, ast.AnnAssign)):
            for name, annotation, default in _assignment_targets(child):
                if _class_member_is_public(name, config):
                    members.append(
                        ApiObject(
                            kind="attribute",
                            name=name,
                            qualname=f"{qualname}.{name}",
                            module=module_name,
                            visibility=_visibility_for(name),
                            signature=f"{name}: {annotation}" if annotation else name,
                            source_path=str(path),
                            line_number=getattr(child, "lineno", None),
                            end_line_number=getattr(child, "end_lineno", None),
                            metadata={"default": default} if default is not None else {},
                        )
                    )
    obj = ApiObject(
        kind="class",
        name=node.name,
        qualname=qualname,
        module=module_name,
        visibility=_visibility_for(node.name),
        signature=signature,
        summary=parsed.summary,
        description=parsed.description,
        parameters=parameters,
        returns=parsed.returns,
        raises=parsed.raises,
        examples=parsed.examples,
        see_also=parsed.see_also,
        renderer_notes=parsed.renderer_notes,
        members=sorted(members, key=lambda item: (item.line_number or 0, item.name)),
        source_path=str(path),
        line_number=getattr(node, "lineno", None),
        end_line_number=getattr(node, "end_lineno", None),
        deprecated=parsed.deprecated,
        deprecation_message=parsed.deprecation_message,
        metadata={
            "docstring_style": parsed.style,
            "issues": [issue.to_dict() for issue in [*parsed.issues, *extra_issues]],
        },
    )
    return obj


def _function_object(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_name: str,
    path: Path,
    *,
    config: ApiCollectConfig,
    parent: str | None,
) -> ApiObject:
    local_name = node.name
    qualname = f"{module_name}.{parent}.{local_name}" if parent else f"{module_name}.{local_name}"
    decorators = {_decorator_name(decorator) for decorator in node.decorator_list}
    if "property" in decorators:
        kind = "property"
        drop_first = True
    else:
        kind = "method" if parent else "function"
        drop_first = parent is not None and "staticmethod" not in decorators
    parsed = parse_docstring(
        ast.get_docstring(node),
        style=config.docstring_style,
        qualname=qualname,
        module=module_name,
    )
    signature_parameters = [] if kind == "property" else _parameters_from_function(node, drop_first=drop_first)
    return_annotation = _unparse(node.returns) if node.returns is not None else None
    parameters, extra_issues = _merge_parameters(
        signature_parameters,
        parsed.parameters,
        qualname=qualname,
        module=module_name,
        path=path,
        line_number=getattr(node, "lineno", None),
    )
    returns = parsed.returns
    if return_annotation:
        if returns is None:
            returns = ApiReturn(annotation=return_annotation, documented=False)
        elif returns.annotation is None:
            returns.annotation = return_annotation
    signature = None if kind == "property" else f"{qualname}({_signature_parameter_text(signature_parameters)})"
    if signature and return_annotation:
        signature = f"{signature} -> {return_annotation}"
    deprecated = parsed.deprecated or bool(decorators & {"deprecated", "deprecate", "deprecated_alias"})
    return ApiObject(
        kind=kind,  # type: ignore[arg-type]
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
        renderer_notes=parsed.renderer_notes,
        source_path=str(path),
        line_number=getattr(node, "lineno", None),
        end_line_number=getattr(node, "end_lineno", None),
        deprecated=deprecated,
        deprecation_message=parsed.deprecation_message,
        metadata={
            "decorators": sorted(name for name in decorators if name),
            "docstring_style": parsed.style,
            "issues": [issue.to_dict() for issue in [*parsed.issues, *extra_issues]],
        },
    )


def _parameters_from_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    drop_first: bool,
) -> list[ApiParameter]:
    args = list(node.args.posonlyargs) + list(node.args.args)
    defaults: list[ast.expr | None] = [None] * (len(args) - len(node.args.defaults)) + list(node.args.defaults)
    paired = list(zip(args, defaults))
    if drop_first and paired and paired[0][0].arg in {"self", "cls"}:
        paired = paired[1:]
    parameters: list[ApiParameter] = []
    for arg, default in paired:
        parameters.append(
            ApiParameter(
                name=arg.arg,
                annotation=_unparse(arg.annotation) if arg.annotation else None,
                default=_unparse(default) if default else None,
                kind="positional",
                required=default is None,
                documented=False,
                source="signature",
            )
        )
    if node.args.vararg is not None:
        parameters.append(
            ApiParameter(
                name=f"*{node.args.vararg.arg}",
                annotation=_unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None,
                kind="var-positional",
                documented=False,
                source="signature",
            )
        )
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        parameters.append(
            ApiParameter(
                name=arg.arg,
                annotation=_unparse(arg.annotation) if arg.annotation else None,
                default=_unparse(default) if default else None,
                kind="keyword-only",
                required=default is None,
                documented=False,
                source="signature",
            )
        )
    if node.args.kwarg is not None:
        parameters.append(
            ApiParameter(
                name=f"**{node.args.kwarg.arg}",
                annotation=_unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None,
                kind="var-keyword",
                documented=False,
                source="signature",
            )
        )
    return parameters


def _merge_parameters(
    signature_parameters: list[ApiParameter],
    doc_parameters: list[ApiParameter],
    *,
    qualname: str,
    module: str,
    path: Path,
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
                path=str(path),
                line_number=line_number,
            )
        )
    return merged, issues


def _signature_parameter_text(parameters: list[ApiParameter]) -> str:
    pieces: list[str] = []
    for parameter in parameters:
        name = parameter.name
        piece = name
        if parameter.annotation:
            piece = f"{piece}: {parameter.annotation}"
        if parameter.default is not None:
            piece = f"{piece} = {parameter.default}"
        pieces.append(piece)
    return ", ".join(pieces)


def _resolve_source_files(package: str | PathLike) -> tuple[Path, str, list[Path]]:
    candidate = Path(str(package))
    if candidate.exists():
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved.parent, resolved.stem, [resolved]
        package_name = resolved.name
        root = resolved.parent if (resolved / "__init__.py").exists() else resolved
        files = sorted(path for path in resolved.rglob("*.py") if "__pycache__" not in path.parts)
        return root, package_name, files

    spec = importlib.util.find_spec(str(package))
    if spec is None:
        raise ModuleNotFoundError(f"Cannot find Python package or module: {package}")
    if spec.submodule_search_locations:
        package_dir = Path(next(iter(spec.submodule_search_locations))).resolve()
        files = sorted(path for path in package_dir.rglob("*.py") if "__pycache__" not in path.parts)
        return package_dir.parent, str(package), files
    if spec.origin is None:
        raise ModuleNotFoundError(f"Python module has no source file: {package}")
    source = Path(spec.origin).resolve()
    return source.parent, str(package), [source]


def _module_name_for_file(path: Path, *, root: Path, package_name: str) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if parts and parts[0] == package_name:
        return ".".join(parts)
    if len(parts) == 1 and parts[0] == "__init__":
        return package_name
    return ".".join([package_name, *parts]) if package_name not in parts[:1] else ".".join(parts)


def _module_all_names(tree: ast.Module) -> set[str] | None:
    names: set[str] | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    names = _string_sequence(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            names = _string_sequence(node.value)
    return names


def _string_sequence(node: ast.AST | None) -> set[str] | None:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: set[str] = set()
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                values.add(element.value)
        return values
    return None


def _assignment_targets(node: ast.Assign | ast.AnnAssign) -> list[tuple[str, str | None, str | None]]:
    annotation = _unparse(node.annotation) if isinstance(node, ast.AnnAssign) and node.annotation is not None else None
    value = node.value if isinstance(node, ast.AnnAssign) else getattr(node, "value", None)
    default = _unparse(value) if value is not None else None
    if isinstance(node, ast.AnnAssign):
        targets = [node.target]
    else:
        targets = list(node.targets)
    results: list[tuple[str, str | None, str | None]] = []
    for target in targets:
        if isinstance(target, ast.Name) and target.id != "__all__":
            results.append((target.id, annotation, default))
    return results


def _find_method(node: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
            return child
    return None


def _is_public_name(
    name: str,
    qualname: str,
    public_names: set[str] | None,
    config: ApiCollectConfig,
) -> bool:
    if config.public_policy == "all":
        return True
    if config.public_policy == "explicit":
        return name in config.explicit_names or qualname in config.explicit_names
    if config.public_policy == "__all__" and public_names is not None:
        return name in public_names or qualname in public_names
    return not name.startswith("_")


def _class_member_is_public(name: str, config: ApiCollectConfig) -> bool:
    if config.public_policy == "all":
        return True
    if config.public_policy == "explicit":
        return name in config.explicit_names
    return not name.startswith("_")


def _visibility_for(name: str):
    if name.startswith("__") and name.endswith("__"):
        return "internal"
    if name.startswith("_"):
        return "protected"
    return "public"


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _normalize_param_name(name: str) -> str:
    return name.lstrip("*")


def _unparse(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    return ast.unparse(node)


def _module_issues(module: ApiModule) -> list[ApiDocIssue]:
    issues: list[ApiDocIssue] = []
    for obj in module.iter_objects(recursive=True):
        for item in obj.metadata.get("issues", []):
            if isinstance(item, dict):
                issues.append(ApiDocIssue.from_dict(item))
    return issues


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name.split(".")[0])
    except importlib.metadata.PackageNotFoundError:
        return None


__all__ = [
    "collect_api",
    "collect_module_api",
    "collect_object_api",
]
