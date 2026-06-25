"""Public facade for collecting Python API documentation metadata."""

from __future__ import annotations

import ast
from dataclasses import replace
import copy
import fnmatch
import importlib.metadata
import importlib.util
from pathlib import Path
import re
from typing import Iterable

from oodocs.apidoc.config import ApiCollectConfig, ApiPublicPolicy, normalize_explicit_names
from oodocs.apidoc.docstring import ApiDocstringParser, ParsedDocstring, parse_docstring
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


def collect_api(
    package: str | PathLike,
    *,
    config: ApiCollectConfig | None = None,
    collector: str | None = None,
    public_policy: str | ApiPublicPolicy | None = None,
    explicit_names: Iterable[str] | None = None,
    docstring_style: str | ApiDocstringParser | None = None,
    include_imported: bool | None = None,
    include_inherited: bool | None = None,
    class_signature_from_init: bool | None = None,
    module_include_patterns: Iterable[str] | None = None,
    module_exclude_patterns: Iterable[str] | None = None,
) -> ApiPackage:
    """Collect a package or repository into an ``ApiPackage`` tree.

    Args:
        package: Importable package/module name, Python file, or package
            directory.
        config: Optional base collection config.
        collector: Collector backend name. ``"auto"``, ``"griffe"``, and
            ``"inspect"`` currently produce the same normalized schema, with
            source-based collection used when griffe is not installed.
        public_policy: Public API boundary policy name or reusable
            ``ApiPublicPolicy`` object.
        explicit_names: Names used with ``public_policy="explicit"``.
        docstring_style: Docstring parser style name or reusable
            ``ApiDocstringParser`` object.
        include_imported: Whether imported public aliases should be included.
            Source collection records unresolved external imports as ``data``
            objects; griffe can resolve richer imported targets when available.
        include_inherited: Whether import-aware collectors should include
            inherited class members when available.
        class_signature_from_init: Whether class signatures use ``__init__``.
        module_include_patterns: Optional glob-style module names to include
            before collection.
        module_exclude_patterns: Optional glob-style module names to exclude
            before collection.

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

    config_kwargs: dict[str, object | None] = {
        "collector": collector,
        "public_policy": public_policy,
        "docstring_style": docstring_style,
        "include_imported": include_imported,
        "include_inherited": include_inherited,
        "class_signature_from_init": class_signature_from_init,
        "module_include_patterns": tuple(module_include_patterns)
        if module_include_patterns is not None
        else None,
        "module_exclude_patterns": tuple(module_exclude_patterns)
        if module_exclude_patterns is not None
        else None,
    }
    if explicit_names is not None:
        config_kwargs["explicit_names"] = normalize_explicit_names(explicit_names)
    resolved = ApiCollectConfig.from_kwargs(config, **config_kwargs)
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

    errors: list[Exception] = []
    for module_name in _candidate_module_prefixes(obj_or_qualname):
        try:
            api = collect_api(module_name, config=config, **kwargs)
        except Exception as exc:
            errors.append(exc)
            continue
        found = api.find(obj_or_qualname)
        if isinstance(found, ApiObject):
            return found
    if errors:
        raise LookupError(f"API object not found: {obj_or_qualname}") from errors[-1]
    raise LookupError(f"API object not found: {obj_or_qualname}")


def _collect_package_source(
    package: str | PathLike,
    *,
    config: ApiCollectConfig,
) -> ApiPackage:
    root, package_name, files = _resolve_source_files(package)
    issues: list[ApiDocIssue] = []
    modules: list[ApiModule] = []
    module_files = [
        (file_path, _module_name_for_file(file_path, root=root, package_name=package_name))
        for file_path in files
    ]
    included_module_files = [
        (file_path, module_name)
        for file_path, module_name in module_files
        if _module_is_included(module_name, config)
    ]
    for file_path, module_name in included_module_files:
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
    _add_reexported_objects(modules)
    _add_imported_objects(modules, include_imported=config.include_imported)
    return ApiPackage(
        package_name,
        version=_package_version(package_name),
        modules=sorted(modules, key=lambda item: item.name),
        issues=issues,
        metadata={
            "collector": config.collector,
            "file_count": len(included_module_files),
            "public_policy": config.public_policy,
            "source_root": str(root),
        },
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
        metadata={
            "__all__": sorted(public_names) if public_names is not None else None,
            "imports": _module_imports(tree, module_name, public_names, config),
            "reexports": _module_reexports(tree, module_name, public_names, config),
        },
    )
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_name(node.name, f"{module_name}.{node.name}", public_names, config):
                members.append(_function_object(node, module_name, path, config=config, parent=None))
        elif isinstance(node, ast.ClassDef):
            if _is_public_name(node.name, f"{module_name}.{node.name}", public_names, config):
                members.append(_class_object(node, module_name, path, config=config))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for name, annotation, default in _assignment_targets(node):
                if _is_public_name(name, f"{module_name}.{name}", public_names, config):
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
    module.members = sorted(
        _merge_attribute_docs(members, parsed_module.attributes),
        key=lambda obj: (obj.line_number or 0, obj.name),
    )
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
            if _class_member_is_public(child.name, config, f"{qualname}.{child.name}"):
                members.append(_function_object(child, module_name, path, config=config, parent=node.name))
        elif isinstance(child, (ast.Assign, ast.AnnAssign)):
            for name, annotation, default in _assignment_targets(child):
                if _class_member_is_public(name, config, f"{qualname}.{name}"):
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
    members = _merge_attribute_docs(members, _class_attribute_docs(parsed))
    decorators = {_decorator_name(decorator) for decorator in node.decorator_list}
    deprecated = parsed.deprecated or bool(decorators & _DEPRECATION_DECORATORS)
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
        deprecated=deprecated,
        deprecation_message=parsed.deprecation_message,
        metadata={
            "decorators": sorted(name for name in decorators if name),
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
    warning_message = _deprecation_warning_message(node)
    deprecated = (
        parsed.deprecated
        or bool(decorators & _DEPRECATION_DECORATORS)
        or warning_message is not None
    )
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
        deprecation_message=parsed.deprecation_message or warning_message,
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


def _merge_attribute_docs(
    members: list[ApiObject],
    doc_attributes: list[ApiParameter],
) -> list[ApiObject]:
    """Apply class or module ``Attributes:`` docs to child API objects."""

    if not doc_attributes:
        return members
    docs_by_name = {
        _normalize_param_name(attribute.name): attribute
        for attribute in doc_attributes
        if attribute.name
    }
    for member in members:
        if member.kind not in {"attribute", "property", "data"}:
            continue
        attribute_doc = docs_by_name.get(_normalize_param_name(member.name))
        if attribute_doc is None:
            continue
        summary, description = _summary_description_from_attribute(attribute_doc.description)
        if summary and not member.summary:
            member.summary = summary
        if description and not member.description:
            member.description = description
        if attribute_doc.annotation:
            if ":" not in (member.signature or ""):
                member.signature = f"{member.name}: {attribute_doc.annotation}"
            member.metadata.setdefault("annotation", attribute_doc.annotation)
        member.metadata.setdefault("docstring_source", "attributes")
    return members


def _class_attribute_docs(parsed: ParsedDocstring) -> list[ApiParameter]:
    """Return docs that can describe child class attributes."""

    by_name: dict[str, ApiParameter] = {}
    for parameter in parsed.parameters:
        by_name.setdefault(_normalize_param_name(parameter.name), parameter)
    for attribute in parsed.attributes:
        by_name[_normalize_param_name(attribute.name)] = attribute
    return list(by_name.values())


def _summary_description_from_attribute(text: str | None) -> tuple[str | None, str | None]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return None, None
    match = re.match(r"(.+?[.!?])(?:\s+|$)(.*)$", cleaned)
    if not match:
        return cleaned, None
    summary = match.group(1).strip()
    remainder = match.group(2).strip()
    return summary, remainder or None


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
        if (resolved / "__init__.py").exists():
            files = _python_files_under(resolved)
            return resolved.parent, resolved.name, files

        project_name = _project_name_from_pyproject(resolved) or resolved.name
        src_root = resolved / "src"
        if src_root.is_dir():
            package_dirs = _package_dirs(src_root)
            if package_dirs:
                files = [file_path for package_dir in package_dirs for file_path in _python_files_under(package_dir)]
                package_name = package_dirs[0].name if len(package_dirs) == 1 else project_name
                return src_root, package_name, sorted(files)

        package_dirs = _package_dirs(resolved)
        if package_dirs:
            files = [file_path for package_dir in package_dirs for file_path in _python_files_under(package_dir)]
            package_name = package_dirs[0].name if len(package_dirs) == 1 else project_name
            return resolved, package_name, sorted(files)

        files = _python_files_under(resolved)
        return resolved, project_name, files

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
    if not parts:
        return package_name
    if parts and parts[0] == package_name:
        return ".".join(parts)
    if parts and (root / parts[0] / "__init__.py").exists():
        return ".".join(parts)
    if not package_name:
        return ".".join(parts)
    return ".".join([package_name, *parts]) if package_name not in parts[:1] else ".".join(parts)


def _module_is_included(module_name: str, config: ApiCollectConfig) -> bool:
    includes = config.module_include_patterns
    excludes = config.module_exclude_patterns
    if includes and not any(fnmatch.fnmatchcase(module_name, pattern) for pattern in includes):
        return False
    return not any(fnmatch.fnmatchcase(module_name, pattern) for pattern in excludes)


def _python_files_under(directory: Path) -> list[Path]:
    ignored = {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "artifacts",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "site-packages",
    }
    return sorted(
        path
        for path in directory.rglob("*.py")
        if not any(part in ignored for part in path.relative_to(directory).parts)
    )


def _package_dirs(source_root: Path) -> list[Path]:
    return sorted(
        path
        for path in source_root.iterdir()
        if path.is_dir()
        and (path / "__init__.py").exists()
        and not path.name.startswith(".")
        and path.name != "__pycache__"
    )


def _project_name_from_pyproject(directory: Path) -> str | None:
    path = directory / "pyproject.toml"
    if not path.exists():
        return None
    in_project = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if in_project and stripped.startswith("name") and "=" in stripped:
            value = stripped.split("=", 1)[1].strip().strip("\"'")
            return value.replace("-", "_") or None
    return None


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


def _module_reexports(
    tree: ast.Module,
    module_name: str,
    public_names: set[str] | None,
    config: ApiCollectConfig,
) -> list[dict[str, str]]:
    reexports: list[dict[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        target_module = _resolve_import_from_module(module_name, node.module, node.level)
        if target_module is None:
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            if not _is_public_name(local_name, f"{module_name}.{local_name}", public_names, config):
                continue
            reexports.append(
                {
                    "name": local_name,
                    "target_module": target_module,
                    "target_name": alias.name,
                    "target_qualname": f"{target_module}.{alias.name}",
                }
            )
    return reexports


def _module_imports(
    tree: ast.Module,
    module_name: str,
    public_names: set[str] | None,
    config: ApiCollectConfig,
) -> list[dict[str, object]]:
    imports: list[dict[str, object]] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".", 1)[0]
                if not _is_public_name(local_name, f"{module_name}.{local_name}", public_names, config):
                    continue
                imports.append(
                    {
                        "name": local_name,
                        "target_module": alias.name,
                        "target_name": None,
                        "target_qualname": alias.name,
                        "line_number": getattr(node, "lineno", None),
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            target_module = _resolve_import_from_module(module_name, node.module, node.level)
            if target_module is None:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                if not _is_public_name(local_name, f"{module_name}.{local_name}", public_names, config):
                    continue
                imports.append(
                    {
                        "name": local_name,
                        "target_module": target_module,
                        "target_name": alias.name,
                        "target_qualname": f"{target_module}.{alias.name}",
                        "line_number": getattr(node, "lineno", None),
                    }
                )
    return imports


def _add_reexported_objects(modules: list[ApiModule]) -> None:
    object_map = {
        obj.qualname: obj
        for module in modules
        for obj in module.iter_objects(recursive=True)
    }
    for module in modules:
        existing_names = {member.name for member in module.members}
        for item in module.metadata.get("reexports", []):
            if not isinstance(item, dict):
                continue
            local_name = str(item.get("name", ""))
            target_qualname = str(item.get("target_qualname", ""))
            target = object_map.get(target_qualname)
            if not local_name or local_name in existing_names or target is None:
                continue
            alias = _reexport_alias(target, module.name, local_name, target_qualname)
            module.members.append(alias)
            existing_names.add(local_name)
            object_map[alias.qualname] = alias
        module.members.sort(key=lambda obj: (obj.line_number or 0, obj.name))


def _add_imported_objects(
    modules: list[ApiModule],
    *,
    include_imported: bool,
) -> None:
    if not include_imported:
        return
    for module in modules:
        existing_names = {member.name for member in module.members}
        for item in module.metadata.get("imports", []):
            if not isinstance(item, dict):
                continue
            local_name = str(item.get("name", ""))
            target_qualname = str(item.get("target_qualname", ""))
            if not local_name or local_name in existing_names:
                continue
            line_number = item.get("line_number")
            module.members.append(
                ApiObject(
                    kind="data",
                    name=local_name,
                    qualname=f"{module.name}.{local_name}",
                    module=module.name,
                    visibility=_visibility_for(local_name),
                    signature=local_name,
                    source_path=module.source_path,
                    line_number=line_number if isinstance(line_number, int) else None,
                    metadata={
                        "imported": True,
                        "imported_from": target_qualname,
                        "target_module": item.get("target_module"),
                        "target_name": item.get("target_name"),
                    },
                )
            )
            existing_names.add(local_name)
        module.members.sort(key=lambda obj: (obj.line_number or 0, obj.name))


def _reexport_alias(
    target: ApiObject,
    module_name: str,
    local_name: str,
    target_qualname: str,
) -> ApiObject:
    alias = ApiObject.from_dict(copy.deepcopy(target.to_dict()))
    alias.name = local_name
    alias.module = module_name
    alias.qualname = f"{module_name}.{local_name}"
    if alias.signature and alias.signature.startswith(target_qualname):
        alias.signature = alias.qualname + alias.signature[len(target_qualname) :]
    alias.metadata = dict(alias.metadata)
    alias.metadata["reexported_from"] = target_qualname
    return alias


def _resolve_import_from_module(
    current_module: str,
    imported_module: str | None,
    level: int,
) -> str | None:
    if level == 0:
        return imported_module
    current_parts = current_module.split(".")
    base_length = max(0, len(current_parts) - level + 1)
    base_parts = current_parts[:base_length]
    if imported_module:
        base_parts.extend(imported_module.split("."))
    return ".".join(part for part in base_parts if part)


def _candidate_module_prefixes(qualname: str) -> list[str]:
    pieces = qualname.split(".")
    candidates: list[str] = []
    for end in range(len(pieces), 0, -1):
        candidate = ".".join(pieces[:end])
        try:
            spec = importlib.util.find_spec(candidate)
        except (ImportError, AttributeError, ValueError):
            spec = None
        if spec is not None:
            candidates.append(candidate)
    if "." in qualname:
        candidates.append(qualname.rsplit(".", 1)[0])
    return list(dict.fromkeys(candidates))


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


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _deprecation_warning_message(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str | None:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not _is_warnings_warn_call(child):
            continue
        if not _call_uses_deprecation_warning(child):
            continue
        return _literal_message(child.args[0]) if child.args else None
    return None


def _is_warnings_warn_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "warn"
        and isinstance(func.value, ast.Name)
        and func.value.id == "warnings"
    )


def _call_uses_deprecation_warning(node: ast.Call) -> bool:
    positional = node.args[1:] if len(node.args) > 1 else []
    keyword_values = [
        keyword.value
        for keyword in node.keywords
        if keyword.arg in {"category", "warning"}
    ]
    return any(_is_deprecation_warning_expr(value) for value in [*positional, *keyword_values])


def _is_deprecation_warning_expr(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "DeprecationWarning"
    if isinstance(node, ast.Attribute):
        return node.attr == "DeprecationWarning"
    return False


def _literal_message(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


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
