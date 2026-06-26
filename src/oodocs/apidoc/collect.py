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
import tomllib
from typing import Iterable, Sequence

from oodocs.apidoc.config import (
    ApiCollectConfig,
    ApiPublicPolicy,
    _project_source_roots,
    normalize_explicit_names,
)
from oodocs.apidoc.docstring import (
    ApiDocstringParser,
    ParsedDocstring,
    docstring_parser_import_paths,
    parse_docstring,
)
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
_IGNORED_SOURCE_PARTS = {
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


def collect_api(
    package: str | PathLike,
    *,
    config: ApiCollectConfig | None = None,
    collector: str | None = None,
    fallback_collector: str | None = None,
    public_policy: str | ApiPublicPolicy | None = None,
    explicit_names: Iterable[str] | None = None,
    docstring_style: str | ApiDocstringParser | None = None,
    docstring_parser_modules: Iterable[str] | None = None,
    include_private: bool | None = None,
    include_imported: bool | None = None,
    include_inherited: bool | None = None,
    include_attributes: bool | None = None,
    include_properties: bool | None = None,
    include_methods: bool | None = None,
    include_source_locations: bool | None = None,
    class_signature_from_init: bool | None = None,
    module_include_patterns: Iterable[str] | None = None,
    module_exclude_patterns: Iterable[str] | None = None,
    object_include_patterns: Iterable[str] | None = None,
    object_exclude_patterns: Iterable[str] | None = None,
) -> ApiPackage:
    """Collect a package or repository into an ``ApiPackage`` tree.

    Args:
        package: Importable package/module name, Python file, or package
            directory.
        config: Optional base collection config.
        collector: Collector backend name. ``"auto"``, ``"griffe"``, and
            ``"inspect"`` currently produce the same normalized schema, with
            source-based collection used when griffe is not installed.
        fallback_collector: Fallback backend used when griffe is unavailable
            or cannot load the target. Use ``"none"`` to surface a collection
            error instead of falling back.
        public_policy: Public API boundary policy name or reusable
            ``ApiPublicPolicy`` object.
        explicit_names: Names used with ``public_policy="explicit"``.
        docstring_style: Docstring parser style name or reusable
            ``ApiDocstringParser`` object.
        docstring_parser_modules: Importable modules that register custom
            parser styles before collection.
        include_private: Whether underscore-prefixed objects should be
            collected in addition to the configured public API boundary.
        include_imported: Whether imported public aliases should be included.
            Source collection records unresolved external imports as ``data``
            objects; griffe can resolve richer imported targets when available.
        include_inherited: Whether import-aware collectors should include
            inherited class members when available.
        include_attributes: Whether module data and class attributes should be
            included.
        include_properties: Whether class properties should be included.
        include_methods: Whether class methods should be included.
        include_source_locations: Whether source paths and line numbers should
            be retained in the returned API tree and diagnostics.
        class_signature_from_init: Whether class signatures use ``__init__``.
        module_include_patterns: Optional glob-style module names to include
            before collection.
        module_exclude_patterns: Optional glob-style module names to exclude
            before collection.
        object_include_patterns: Optional glob-style object name or qualname
            patterns to include after collection.
        object_exclude_patterns: Optional glob-style object name or qualname
            patterns to exclude after collection.

    Returns:
        Collected API package.

    Examples:
        Collect a normal Python repository and compose selected objects into an
        authored OODocs document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api

        api = collect_api(
            ".",
            public_policy="__all__",
            module_exclude_patterns=("mypkg.tests*",),
            object_exclude_patterns=("render_to_pdf", "render_to_html"),
        )
        classes = api.select(kind="class", module_prefix="mypkg")

        doc = Document(
            "Selected API",
            Chapter(
                "Public Classes",
                *[obj.to_section(level=2, profile="manual") for obj in classes[:3]],
            ),
        )
        ```

        Reuse a repository config and render a complete reference through the
        normal ``Document.save_all(...)`` pipeline:

        ```python
        from oodocs.apidoc import ApiCollectConfig, collect_api

        config = ApiCollectConfig.from_pyproject(".")
        api = collect_api(".", config=config)
        api.to_document(profile="reference").save_all(
            "artifacts/api",
            stem="mypkg-api",
        )
        ```
    """

    config_kwargs: dict[str, object | None] = {
        "collector": collector,
        "fallback_collector": fallback_collector,
        "public_policy": public_policy,
        "docstring_style": docstring_style,
        "docstring_parser_modules": tuple(docstring_parser_modules)
        if docstring_parser_modules is not None
        else None,
        "include_private": include_private,
        "include_imported": include_imported,
        "include_inherited": include_inherited,
        "include_attributes": include_attributes,
        "include_properties": include_properties,
        "include_methods": include_methods,
        "include_source_locations": include_source_locations,
        "class_signature_from_init": class_signature_from_init,
        "module_include_patterns": tuple(module_include_patterns)
        if module_include_patterns is not None
        else None,
        "module_exclude_patterns": tuple(module_exclude_patterns)
        if module_exclude_patterns is not None
        else None,
        "object_include_patterns": tuple(object_include_patterns)
        if object_include_patterns is not None
        else None,
        "object_exclude_patterns": tuple(object_exclude_patterns)
        if object_exclude_patterns is not None
        else None,
    }
    if explicit_names is not None:
        config_kwargs["explicit_names"] = normalize_explicit_names(explicit_names)
    with docstring_parser_import_paths(package):
        resolved = ApiCollectConfig.from_kwargs(config, **config_kwargs)
    if resolved.collector == "inspect":
        from oodocs.apidoc.collect_inspect import collect_package_inspect

        api = collect_package_inspect(package, config=resolved)
    elif resolved.collector == "griffe":
        from oodocs.apidoc.collect_griffe import collect_package_griffe

        api = collect_package_griffe(package, config=resolved)
    else:
        try:
            from oodocs.apidoc.collect_griffe import collect_package_griffe

            api = collect_package_griffe(package, config=resolved)
        except Exception as exc:  # pragma: no cover - fallback path is environment-sensitive.
            if resolved.fallback_collector == "none":
                api = _failed_collect_package(
                    package,
                    config=resolved,
                    code="collector-auto-fallback-disabled",
                    message=(
                        "Collector auto fallback is disabled and griffe "
                        f"collection failed: {exc}"
                    ),
                )
            else:
                fallback_config = replace(resolved, collector="inspect")
                api = _collect_package_source(package, config=fallback_config)
                api.issues.append(
                    ApiDocIssue(
                        "info",
                        "collector-auto-fallback",
                        f"Fell back to inspect-compatible source collection: {exc}",
                    )
                )
    api = _filter_collected_objects(api, config=resolved)
    if not resolved.include_source_locations:
        _strip_source_locations(api)
    return api


def collect_module_api(
    module: str | PathLike,
    *,
    target: str | PathLike | None = None,
    config: ApiCollectConfig | None = None,
    **kwargs: object,
) -> ApiModule:
    """Collect one module into an ``ApiModule``.

    Args:
        module: Importable module name, Python file, or module name to find
            inside ``target``.
        target: Optional package, Python file, package directory, or
            repository checkout to collect before selecting ``module``. Use
            this when the target checkout is not importable on ``PYTHONPATH``.
        config: Optional base config.
        **kwargs: Config overrides accepted by ``collect_api``.

    Returns:
        Collected module metadata.

    Raises:
        LookupError: If ``target`` is supplied and the named module is not in
            the collected target.
        ValueError: If the input expands to zero or more than one collected
            module when ``target`` is omitted.

    Examples:
        Collect one module from a repository checkout and render it as a
        standalone reference document:

        ```python
        from oodocs import Document
        from oodocs.apidoc import collect_module_api

        module = collect_module_api(
            "mypkg.adapters.http",
            target=".",
            public_policy="__all__",
        )
        Document("HTTP Adapter API", module.to_chapter(profile="manual")).save_html(
            "artifacts/http-adapter-api.html",
        )
        ```

        Collect a single module and embed it in a larger document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_module_api

        module = collect_module_api(
            "mypkg.renderers.pdf",
            public_policy="underscore",
        )
        doc = Document("Renderer Notes", Chapter("PDF API", *module.to_blocks()))
        ```
    """

    if target is not None:
        api = collect_api(target, config=config, **kwargs)
        found = api.find(str(module))
        if isinstance(found, ApiModule):
            return found
        raise LookupError(f"API module not found in target: {module}")

    api = collect_api(module, config=config, **kwargs)
    if len(api.modules) != 1:
        raise ValueError(f"Expected one module, collected {len(api.modules)} modules")
    return api.modules[0]


def collect_object_api(
    obj_or_qualname: object,
    *,
    target: str | PathLike | None = None,
    config: ApiCollectConfig | None = None,
    **kwargs: object,
) -> ApiObject:
    """Collect one object by fully qualified name or live Python object.

    Args:
        obj_or_qualname: Fully qualified object name or an importable Python
            class, function, method, or property object.
        target: Optional package, Python file, package directory, or
            repository checkout to collect before selecting the object. Use
            this for repository-local API references that should not depend on
            import path setup.
        config: Optional base config.
        **kwargs: Config overrides accepted by ``collect_api``.

    Returns:
        Matching API object.

    Raises:
        TypeError: If a live object does not expose importable module and
            qualname metadata.
        LookupError: If the object cannot be found in the selected module
            candidates or target.

    Examples:
        Collect one object from a repository checkout and insert it into an
        authored guide:

        ```python
        from oodocs import Chapter, Document, Paragraph
        from oodocs.apidoc import collect_object_api

        obj = collect_object_api(
            "mypkg.client.Client.connect",
            target=".",
            public_policy="__all__",
        )
        doc = Document(
            "Client Integration Guide",
            Chapter(
                "Connection API",
                Paragraph("The following section is generated from source."),
                obj.to_section(level=2, profile="manual"),
            ),
        )
        ```

        Collect one object when an API guide needs a focused reference panel:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_object_api

        obj = collect_object_api("mypkg.settings.DocumentSettings")
        doc = Document(
            "Settings API",
            Chapter("Document Settings", obj.to_compact_box(profile="manual")),
        )
        ```

        Pass a live object while developing an importable module:

        ```python
        from mypkg.settings import DocumentSettings
        from oodocs.apidoc import collect_object_api

        obj = collect_object_api(DocumentSettings, public_policy="underscore")
        section = obj.to_section(level=2, profile="manual")
        ```
    """

    qualname, preferred_module = _object_lookup_target(obj_or_qualname)
    if target is not None:
        api = collect_api(target, config=config, **kwargs)
        found = api.find(qualname)
        if isinstance(found, ApiObject):
            return found
        raise LookupError(f"API object not found in target: {qualname}")

    errors: list[Exception] = []
    module_candidates = _candidate_module_prefixes(qualname)
    if preferred_module is not None:
        module_candidates.insert(0, preferred_module)
    for module_name in list(dict.fromkeys(module_candidates)):
        try:
            api = collect_api(module_name, config=config, **kwargs)
        except Exception as exc:
            errors.append(exc)
            continue
        found = api.find(qualname)
        if isinstance(found, ApiObject):
            return found
    if errors:
        raise LookupError(f"API object not found: {qualname}") from errors[-1]
    raise LookupError(f"API object not found: {qualname}")


def _object_lookup_target(obj_or_qualname: object) -> tuple[str, str | None]:
    if isinstance(obj_or_qualname, str):
        return obj_or_qualname, None
    target = obj_or_qualname.fget if isinstance(obj_or_qualname, property) else obj_or_qualname
    target = getattr(target, "__func__", target)
    module = getattr(target, "__module__", None)
    qualname = getattr(target, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str) or not module or not qualname:
        raise TypeError("obj_or_qualname must be a fully qualified name or importable Python object")
    if "<locals>" in qualname:
        raise TypeError("local Python objects cannot be collected by collect_object_api")
    return f"{module}.{qualname}", module


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


def _failed_collect_package(
    package: str | PathLike,
    *,
    config: ApiCollectConfig,
    code: str,
    message: str,
) -> ApiPackage:
    try:
        root, package_name, files = _resolve_source_files(package)
    except Exception:
        root = Path.cwd()
        package_name = Path(str(package)).stem or str(package)
        files = []
    file_count = sum(
        1
        for file_path in files
        if _module_is_included(
            _module_name_for_file(file_path, root=root, package_name=package_name),
            config,
        )
    )
    return ApiPackage(
        package_name,
        version=_package_version(package_name),
        modules=[],
        issues=[ApiDocIssue("error", code, message)],
        metadata={
            "collector": config.collector,
            "fallback_collector": config.fallback_collector,
            "file_count": file_count,
            "public_policy": config.public_policy,
            "source_root": str(root),
        },
    )


def _filter_collected_objects(api: ApiPackage, *, config: ApiCollectConfig) -> ApiPackage:
    """Apply object include/exclude filters after collection."""

    if not config.object_include_patterns and not config.object_exclude_patterns:
        return api

    modules: list[ApiModule] = []
    selected_qualnames: set[str] = set()
    for module in api.modules:
        members = [
            filtered
            for member in module.members
            if (
                filtered := _filter_object_tree(
                    member,
                    config=config,
                    include_ancestor=False,
                )
            )
            is not None
        ]
        if not members:
            continue
        for member in members:
            selected_qualnames.add(member.qualname)
            selected_qualnames.update(child.qualname for child in member.iter_members(recursive=True))
        modules.append(
            ApiModule(
                name=module.name,
                members=members,
                summary=module.summary,
                description=module.description,
                notes=list(module.notes),
                warnings=list(module.warnings),
                renderer_notes=list(module.renderer_notes),
                source_path=module.source_path,
                line_number=module.line_number,
                end_line_number=module.end_line_number,
                metadata=dict(module.metadata),
            )
        )

    included_modules = {module.name for module in modules}
    metadata = dict(api.metadata)
    metadata["object_filters"] = {
        "include": list(config.object_include_patterns),
        "exclude": list(config.object_exclude_patterns),
    }
    return ApiPackage(
        api.name,
        version=api.version,
        modules=modules,
        issues=[
            issue
            for issue in api.issues
            if _issue_matches_object_filters(issue, selected_qualnames, included_modules)
        ],
        metadata=metadata,
    )


def _filter_object_tree(
    obj: ApiObject,
    *,
    config: ApiCollectConfig,
    include_ancestor: bool,
) -> ApiObject | None:
    if _matches_any_object_pattern(obj, config.object_exclude_patterns):
        return None

    include_match = (
        not config.object_include_patterns
        or _matches_any_object_pattern(obj, config.object_include_patterns)
    )
    include_descendants = include_ancestor or include_match
    members = [
        filtered
        for member in obj.members
        if (
            filtered := _filter_object_tree(
                member,
                config=config,
                include_ancestor=include_descendants,
            )
        )
        is not None
    ]
    if not include_descendants and not members:
        return None

    clone = ApiObject.from_dict(obj.to_dict())
    clone.members = members
    return clone


def _matches_any_object_pattern(obj: ApiObject, patterns: tuple[str, ...]) -> bool:
    return any(
        fnmatch.fnmatchcase(obj.qualname, pattern)
        or fnmatch.fnmatchcase(obj.name, pattern)
        for pattern in patterns
    )


def _object_kind_enabled(kind: str, config: ApiCollectConfig) -> bool:
    if kind in {"attribute", "data"}:
        return config.include_attributes
    if kind == "property":
        return config.include_properties
    if kind == "method":
        return config.include_methods
    return True


_SOURCE_LOCATION_METADATA_KEYS = {
    "end_line_number",
    "line_number",
    "path",
    "source_path",
    "source_root",
}


def _strip_source_locations(api: ApiPackage) -> None:
    _strip_source_location_metadata(api.metadata)
    for issue in api.issues:
        issue.path = None
        issue.line_number = None
    for module in api.modules:
        module.source_path = None
        module.line_number = None
        module.end_line_number = None
        _strip_source_location_metadata(module.metadata)
        for obj in module.iter_objects(recursive=True):
            obj.source_path = None
            obj.line_number = None
            obj.end_line_number = None
            _strip_source_location_metadata(obj.metadata)


def _strip_source_location_metadata(value: object) -> None:
    if isinstance(value, dict):
        for key in list(value):
            if key in _SOURCE_LOCATION_METADATA_KEYS:
                value.pop(key, None)
        for child in value.values():
            _strip_source_location_metadata(child)
    elif isinstance(value, list):
        for child in value:
            _strip_source_location_metadata(child)


def _issue_matches_object_filters(
    issue: ApiDocIssue,
    selected_qualnames: set[str],
    included_modules: set[str],
) -> bool:
    if issue.qualname:
        return issue.qualname in selected_qualnames
    if issue.module:
        return issue.module in included_modules
    return True


def _collect_module_from_file(
    path: Path,
    module_name: str,
    *,
    config: ApiCollectConfig,
) -> ApiModule:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    parsed_module = parse_docstring(
        ast.get_docstring(tree),
        style=config.docstring_style,
        module=module_name,
    )
    public_names = _module_all_names(tree)
    members: list[ApiObject] = []
    class_nodes = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }
    class_objects = {
        name: _class_object(node, module_name, path, config=config)
        for name, node in class_nodes.items()
    }
    module_overloads = _function_overloads(tree.body, module_name, path, config=config, parent=None)
    module = ApiModule(
        module_name,
        summary=parsed_module.summary,
        description=parsed_module.description,
        notes=parsed_module.notes,
        warnings=parsed_module.warnings,
        renderer_notes=parsed_module.renderer_notes,
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
            if _is_overload_function(node):
                continue
            if _is_public_name(node.name, f"{module_name}.{node.name}", public_names, config):
                members.append(
                    _function_object(
                        node,
                        module_name,
                        path,
                        config=config,
                        parent=None,
                        overloads=module_overloads.get(node.name, ()),
                    )
                )
        elif isinstance(node, ast.ClassDef):
            if _is_public_name(node.name, f"{module_name}.{node.name}", public_names, config):
                members.append(class_objects[node.name])
        elif config.include_attributes and isinstance(node, (ast.Assign, ast.AnnAssign)):
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
    if config.include_inherited:
        _add_source_inherited_members(
            members,
            class_nodes=class_nodes,
            class_objects=class_objects,
            config=config,
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
    if config.class_signature_from_init:
        if init_node is not None:
            signature_parameters = _parameters_from_function(init_node, drop_first=True)
        elif _is_dataclass_class(node):
            signature_parameters = _parameters_from_dataclass_fields(node, config=config, qualname=qualname)
    if signature_parameters:
        signature = f"{qualname}({_signature_parameter_text(signature_parameters)})"
    parameters, extra_issues = _merge_parameters(
        signature_parameters,
        _class_parameter_docs(signature_parameters, parsed, init_parsed),
        qualname=qualname,
        module=module_name,
        path=path,
        line_number=getattr(node, "lineno", None),
    )
    members: list[ApiObject] = []
    member_overloads = _function_overloads(node.body, module_name, path, config=config, parent=node.name)
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child.name == "__init__" or _is_overload_function(child):
                continue
            decorators = {_decorator_name(decorator) for decorator in child.decorator_list}
            if "property" in decorators:
                if not config.include_properties:
                    continue
            elif not config.include_methods:
                continue
            if _class_member_is_public(child.name, config, f"{qualname}.{child.name}"):
                members.append(
                    _function_object(
                        child,
                        module_name,
                        path,
                        config=config,
                        parent=node.name,
                        overloads=member_overloads.get(child.name, ()),
                    )
                )
        elif config.include_attributes and isinstance(child, (ast.Assign, ast.AnnAssign)):
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
    if config.include_attributes and init_node is not None:
        existing_names = {member.name for member in members}
        for name, annotation, default, line_number, end_line_number in _instance_attribute_targets(init_node):
            if name in existing_names or not _class_member_is_public(name, config, f"{qualname}.{name}"):
                continue
            metadata: dict[str, object] = {"instance_attribute": True}
            if default is not None:
                metadata["default"] = default
            members.append(
                ApiObject(
                    kind="attribute",
                    name=name,
                    qualname=f"{qualname}.{name}",
                    module=module_name,
                    visibility=_visibility_for(name),
                    signature=f"{name}: {annotation}" if annotation else name,
                    source_path=str(path),
                    line_number=line_number,
                    end_line_number=end_line_number,
                    metadata=metadata,
                )
            )
            existing_names.add(name)
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
        exceptions=parsed.exceptions,
        examples=parsed.examples,
        see_also=parsed.see_also,
        notes=parsed.notes,
        warnings=parsed.warnings,
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


def _add_source_inherited_members(
    members: list[ApiObject],
    *,
    class_nodes: dict[str, ast.ClassDef],
    class_objects: dict[str, ApiObject],
    config: ApiCollectConfig,
) -> None:
    for class_obj in members:
        if class_obj.kind != "class":
            continue
        node = class_nodes.get(class_obj.name)
        if node is None:
            continue
        existing = {member.name for member in class_obj.members}
        inherited: list[ApiObject] = []
        for member in _source_inherited_members(
            node,
            class_nodes=class_nodes,
            class_objects=class_objects,
            visited=set(),
        ):
            if member.name in existing or not _object_kind_enabled(member.kind, config):
                continue
            clone = _inherited_member_alias(member, class_obj.qualname)
            inherited.append(clone)
            existing.add(member.name)
        if inherited:
            class_obj.members = sorted(
                [*class_obj.members, *inherited],
                key=lambda item: (item.line_number or 0, item.name),
            )


def _source_inherited_members(
    node: ast.ClassDef,
    *,
    class_nodes: dict[str, ast.ClassDef],
    class_objects: dict[str, ApiObject],
    visited: set[str],
) -> Iterable[ApiObject]:
    for base_name in _source_base_names(node):
        if base_name in visited:
            continue
        visited.add(base_name)
        base_node = class_nodes.get(base_name)
        base_obj = class_objects.get(base_name)
        if base_node is None or base_obj is None:
            continue
        yield from base_obj.members
        yield from _source_inherited_members(
            base_node,
            class_nodes=class_nodes,
            class_objects=class_objects,
            visited=visited,
        )


def _source_base_names(node: ast.ClassDef) -> list[str]:
    names: list[str] = []
    for base in node.bases:
        name = _source_base_name(base)
        if name:
            names.append(name)
    return names


def _source_base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _instance_attribute_targets(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[str, str | None, str | None, int | None, int | None]]:
    attributes: dict[str, tuple[str, str | None, str | None, int | None, int | None]] = {}
    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                name = _self_attribute_name(target)
                if name and name not in attributes:
                    attributes[name] = (
                        name,
                        None,
                        _unparse(child.value),
                        getattr(child, "lineno", None),
                        getattr(child, "end_lineno", None),
                    )
        elif isinstance(child, ast.AnnAssign):
            name = _self_attribute_name(child.target)
            if name and name not in attributes:
                attributes[name] = (
                    name,
                    _unparse(child.annotation) if child.annotation else None,
                    _unparse(child.value) if child.value else None,
                    getattr(child, "lineno", None),
                    getattr(child, "end_lineno", None),
                )
    return list(attributes.values())


def _self_attribute_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id in {"self", "cls"}:
            return node.attr
    return None


def _inherited_member_alias(member: ApiObject, owner_qualname: str) -> ApiObject:
    clone = ApiObject.from_dict(copy.deepcopy(member.to_dict()))
    clone.qualname = f"{owner_qualname}.{member.name}"
    clone.metadata = dict(clone.metadata)
    clone.metadata["inherited_from"] = member.metadata.get("inherited_from") or member.qualname
    if clone.signature and clone.signature.startswith(member.qualname):
        clone.signature = clone.qualname + clone.signature[len(member.qualname) :]
    return clone


def _function_object(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_name: str,
    path: Path,
    *,
    config: ApiCollectConfig,
    parent: str | None,
    overloads: Sequence[dict[str, object]] = (),
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
    metadata: dict[str, object] = {
        "decorators": sorted(name for name in decorators if name),
        "docstring_style": parsed.style,
        "issues": [issue.to_dict() for issue in [*parsed.issues, *extra_issues]],
    }
    if overloads:
        metadata["overloads"] = list(overloads)
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
        exceptions=parsed.exceptions,
        examples=parsed.examples,
        see_also=parsed.see_also,
        notes=parsed.notes,
        warnings=parsed.warnings,
        renderer_notes=parsed.renderer_notes,
        source_path=str(path),
        line_number=getattr(node, "lineno", None),
        end_line_number=getattr(node, "end_lineno", None),
        deprecated=deprecated,
        deprecation_message=parsed.deprecation_message or warning_message,
        metadata=metadata,
    )


def _function_overloads(
    nodes: Iterable[ast.stmt],
    module_name: str,
    path: Path,
    *,
    config: ApiCollectConfig,
    parent: str | None,
) -> dict[str, list[dict[str, object]]]:
    overloads: dict[str, list[dict[str, object]]] = {}
    for node in nodes:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _is_overload_function(node):
            continue
        decorators = {_decorator_name(decorator) for decorator in node.decorator_list}
        if parent and "property" in decorators:
            continue
        drop_first = parent is not None and "staticmethod" not in decorators
        parameters = _parameters_from_function(node, drop_first=drop_first)
        qualname = f"{module_name}.{parent}.{node.name}" if parent else f"{module_name}.{node.name}"
        return_annotation = _unparse(node.returns) if node.returns is not None else None
        signature = f"{qualname}({_signature_parameter_text(parameters)})"
        if return_annotation:
            signature = f"{signature} -> {return_annotation}"
        overloads.setdefault(node.name, []).append(
            {
                "signature": signature,
                "parameters": [parameter.to_dict() for parameter in parameters],
                "returns": return_annotation,
                "source_path": str(path),
                "line_number": getattr(node, "lineno", None),
                "end_line_number": getattr(node, "end_lineno", None),
            }
        )
    return overloads


def _is_overload_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return "overload" in {_decorator_name(decorator) for decorator in node.decorator_list}


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


def _parameters_from_dataclass_fields(
    node: ast.ClassDef,
    *,
    config: ApiCollectConfig,
    qualname: str,
) -> list[ApiParameter]:
    parameters: list[ApiParameter] = []
    for child in node.body:
        if not isinstance(child, ast.AnnAssign):
            continue
        if not isinstance(child.target, ast.Name):
            continue
        name = child.target.id
        if not _class_member_is_public(name, config, f"{qualname}.{name}"):
            continue
        if _is_classvar_annotation(child.annotation):
            continue
        default = _dataclass_field_default(child.value)
        if default is _DATACLASS_FIELD_INIT_FALSE:
            continue
        parameters.append(
            ApiParameter(
                name=name,
                annotation=_unparse(child.annotation) if child.annotation else None,
                default=default,
                kind="positional",
                required=default is None,
                documented=False,
                source="dataclass-field",
            )
        )
    return parameters


_DATACLASS_FIELD_INIT_FALSE = object()


def _is_dataclass_class(node: ast.ClassDef) -> bool:
    return "dataclass" in {_decorator_name(decorator) for decorator in node.decorator_list}


def _is_classvar_annotation(node: ast.expr | None) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.Name):
        return node.id == "ClassVar"
    if isinstance(node, ast.Attribute):
        return node.attr == "ClassVar"
    if isinstance(node, ast.Subscript):
        return _is_classvar_annotation(node.value)
    return False


def _dataclass_field_default(node: ast.expr | None) -> str | None | object:
    if node is None:
        return None
    if not _is_dataclass_field_call(node):
        return _unparse(node)
    for keyword in node.keywords:
        if keyword.arg == "init" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
            return _DATACLASS_FIELD_INIT_FALSE
    for keyword in node.keywords:
        if keyword.arg == "default":
            return _unparse(keyword.value)
    for keyword in node.keywords:
        if keyword.arg == "default_factory":
            factory = _unparse(keyword.value)
            return f"{factory}()" if factory else None
    return None


def _is_dataclass_field_call(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id == "field"
    if isinstance(node.func, ast.Attribute):
        return node.func.attr == "field"
    return False


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


def _class_parameter_docs(
    signature_parameters: list[ApiParameter],
    parsed: ParsedDocstring,
    init_parsed: ParsedDocstring | None,
) -> list[ApiParameter]:
    """Return doc entries that can describe class constructor parameters."""

    primary = parsed.parameters or (init_parsed.parameters if init_parsed else [])
    by_name = {
        _normalize_param_name(parameter.name): parameter
        for parameter in primary
        if parameter.name
    }
    signature_names = {
        _normalize_param_name(parameter.name)
        for parameter in signature_parameters
        if parameter.name
    }
    for attribute in parsed.attributes:
        normalized = _normalize_param_name(attribute.name)
        if normalized in signature_names and normalized not in by_name:
            by_name[normalized] = attribute
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
        declared_target = _declared_import_source_files_from_pyproject(
            resolved,
            project_name=project_name,
        )
        if declared_target is not None:
            return declared_target
        flit_target = _flit_source_files_from_pyproject(
            resolved,
            project_name=project_name,
        )
        if flit_target is not None:
            return flit_target
        py_modules = _py_modules_from_pyproject(resolved)
        for source_root in _project_source_roots(resolved):
            if (source_root / "__init__.py").exists():
                files = _python_files_under(source_root)
                return source_root.parent, source_root.name, sorted(files)
            package_dirs = _package_dirs(source_root)
            namespace_dirs = _namespace_package_dirs(source_root)
            module_files = _module_files_for_source_root(
                source_root,
                py_modules=py_modules,
                include_implicit=not package_dirs and not namespace_dirs,
            )
            if package_dirs:
                files = [
                    file_path
                    for package_dir in package_dirs
                    for file_path in _python_files_under(package_dir)
                ]
                package_name = (
                    package_dirs[0].name
                    if len(package_dirs) == 1 and not module_files
                    else project_name
                )
                files.extend(module_files)
                return source_root, package_name, sorted(files)
            if namespace_dirs:
                files = [
                    file_path
                    for package_dir in namespace_dirs
                    for file_path in _python_files_under(package_dir)
                ]
                package_name = (
                    namespace_dirs[0].name
                    if len(namespace_dirs) == 1 and not module_files
                    else project_name
                )
                files.extend(module_files)
                return source_root, package_name, sorted(files)
            if module_files:
                package_name = module_files[0].stem if len(module_files) == 1 else project_name
                return source_root, package_name, sorted(module_files)

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
    package_parts = str(package).split(".")
    if len(package_parts) > 1 and len(source.parents) >= len(package_parts):
        return source.parents[len(package_parts) - 1], package_parts[0], [source]
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
    if len(parts) == 1 and path.parent.resolve() == root.resolve():
        return ".".join(parts)
    if parts and (root / parts[0] / "__init__.py").exists():
        return ".".join(parts)
    if parts and _is_namespace_source_dir(root / parts[0]):
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
    return sorted(
        path
        for path in directory.rglob("*.py")
        if not any(part in _IGNORED_SOURCE_PARTS for part in path.relative_to(directory).parts)
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


def _namespace_package_dirs(source_root: Path) -> list[Path]:
    return sorted(
        path
        for path in source_root.iterdir()
        if _is_namespace_source_dir(path)
    )


def _module_files_for_source_root(
    source_root: Path,
    *,
    py_modules: Sequence[str],
    include_implicit: bool,
) -> list[Path]:
    if py_modules:
        files: list[Path] = []
        for module in py_modules:
            module_path = source_root.joinpath(*module.split(".")).with_suffix(".py")
            if module_path.is_file():
                files.append(module_path)
        return sorted(files)
    if not include_implicit:
        return []
    return sorted(
        path
        for path in source_root.glob("*.py")
        if path.name != "__init__.py" and not path.name.startswith(".")
    )


def _is_namespace_source_dir(path: Path) -> bool:
    return (
        path.is_dir()
        and not path.name.startswith(".")
        and path.name not in _IGNORED_SOURCE_PARTS
        and not (path / "__init__.py").exists()
        and bool(_python_files_under(path))
    )


def _project_name_from_pyproject(directory: Path) -> str | None:
    data = _pyproject_data(directory)
    if not data:
        return None
    project = data.get("project")
    if isinstance(project, dict):
        name = project.get("name")
        if isinstance(name, str):
            return name.replace("-", "_") or None
    return None


def _flit_source_files_from_pyproject(
    directory: Path,
    *,
    project_name: str,
) -> tuple[Path, str, list[Path]] | None:
    data = _pyproject_data(directory)
    if not data or not _is_flit_pyproject(data):
        return None
    import_names = _flit_import_names(data, default_name=project_name)
    if not import_names:
        return None

    for source_root in _import_name_source_roots(directory):
        files: list[Path] = []
        for import_name in import_names:
            files.extend(_files_for_import_name(source_root, import_name))
        if files:
            package_name = import_names[0] if len(import_names) == 1 else project_name
            return source_root.resolve(), package_name, sorted(dict.fromkeys(files))
    return None


def _is_flit_pyproject(data: dict[str, object]) -> bool:
    build_system = data.get("build-system")
    build_backend = (
        build_system.get("build-backend")
        if isinstance(build_system, dict)
        else None
    )
    tool = data.get("tool")
    return (
        isinstance(build_backend, str)
        and "flit" in build_backend
    ) or (isinstance(tool, dict) and isinstance(tool.get("flit"), dict))


def _flit_import_names(
    data: dict[str, object],
    *,
    default_name: str,
) -> tuple[str, ...]:
    project = data.get("project")
    names: list[str] = []
    if isinstance(project, dict):
        names.extend(_flit_import_names_from_value(project.get("import-names")))
        names.extend(_flit_import_names_from_value(project.get("import-namespaces")))

    tool = data.get("tool")
    flit = tool.get("flit") if isinstance(tool, dict) else None
    module = flit.get("module") if isinstance(flit, dict) else None
    module_name = module.get("name") if isinstance(module, dict) else None
    if isinstance(module_name, str) and module_name.strip():
        names.append(module_name.strip())

    if not names and default_name:
        names.append(default_name)
    return tuple(dict.fromkeys(names))


def _declared_import_source_files_from_pyproject(
    directory: Path,
    *,
    project_name: str,
) -> tuple[Path, str, list[Path]] | None:
    data = _pyproject_data(directory)
    if not data:
        return None
    project = data.get("project")
    import_names = _declared_project_import_names(project)
    if import_names is None:
        return None
    if not import_names:
        return directory.resolve(), project_name, []

    for source_root in _import_name_source_roots(directory):
        files: list[Path] = []
        for import_name in import_names:
            files.extend(_files_for_import_name(source_root, import_name))
        if files:
            package_name = import_names[0] if len(import_names) == 1 else project_name
            return source_root.resolve(), package_name, sorted(dict.fromkeys(files))
    return directory.resolve(), project_name, []


def _declared_project_import_names(project: object) -> tuple[str, ...] | None:
    if not isinstance(project, dict):
        return None
    found = False
    names: list[str] = []
    for key in ("import-names", "import_names", "import-namespaces", "import_namespaces"):
        if key not in project:
            continue
        found = True
        names.extend(_flit_import_names_from_value(project.get(key)))
    if not found:
        return None
    return tuple(dict.fromkeys(names))


def _import_name_source_roots(directory: Path) -> list[Path]:
    roots = [
        *_project_source_roots(directory),
        directory / "src",
        directory,
    ]
    normalized: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved in seen or not resolved.is_dir():
            continue
        normalized.append(resolved)
        seen.add(resolved)
    return normalized


def _flit_import_names_from_value(value: object) -> list[str]:
    names = _module_names_from_value(value)
    return [
        name.split(";", 1)[0].strip()
        for name in names
        if name.split(";", 1)[0].strip()
    ]


def _files_for_import_name(source_root: Path, import_name: str) -> list[Path]:
    package_path = source_root.joinpath(*import_name.split("."))
    module_path = package_path.with_suffix(".py")
    if module_path.is_file():
        return [module_path.resolve()]
    if package_path.is_dir() and _python_files_under(package_path):
        return [path.resolve() for path in _python_files_under(package_path)]
    return []


def _py_modules_from_pyproject(directory: Path) -> tuple[str, ...]:
    data = _pyproject_data(directory)
    if not data:
        return ()
    tool = data.get("tool")
    modules: list[str] = []
    setuptools = tool.get("setuptools") if isinstance(tool, dict) else None
    if isinstance(setuptools, dict):
        value = setuptools.get("py-modules", setuptools.get("py_modules"))
        modules.extend(_module_names_from_value(value))
    modules.extend(_pdm_module_names_from_tool(tool))
    return tuple(dict.fromkeys(modules))


def _module_names_from_value(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _pdm_module_names_from_tool(tool: object) -> list[str]:
    if not isinstance(tool, dict):
        return []
    pdm = tool.get("pdm")
    build = pdm.get("build") if isinstance(pdm, dict) else None
    if not isinstance(build, dict):
        return []
    package_dir = build.get("package-dir", build.get("package_dir"))
    package_dir_parts = _path_parts(package_dir) if isinstance(package_dir, str) else ()
    modules: list[str] = []
    for include in _module_names_from_value(build.get("includes")):
        if not include.endswith(".py") or any(character in include for character in "*?["):
            continue
        path = Path(include).with_suffix("")
        parts = path.parts
        if parts and parts[-1] == "__init__":
            continue
        if package_dir_parts and parts[: len(package_dir_parts)] == package_dir_parts:
            parts = parts[len(package_dir_parts) :]
        if parts:
            modules.append(".".join(parts))
    return modules


def _path_parts(value: str) -> tuple[str, ...]:
    return tuple(part for part in Path(value.strip().rstrip("/\\")).parts if part)


def _pyproject_data(directory: Path) -> dict[str, object] | None:
    path = directory / "pyproject.toml"
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return data if isinstance(data, dict) else None


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
            for member in alias.iter_members(recursive=True):
                object_map[member.qualname] = member
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
    _remap_reexported_object(
        alias,
        old_prefix=target_qualname,
        new_prefix=f"{module_name}.{local_name}",
        module_name=module_name,
    )
    return alias


def _remap_reexported_object(
    obj: ApiObject,
    *,
    old_prefix: str,
    new_prefix: str,
    module_name: str,
) -> None:
    original_qualname = obj.qualname
    if obj.qualname == old_prefix:
        obj.qualname = new_prefix
    elif obj.qualname.startswith(f"{old_prefix}."):
        obj.qualname = f"{new_prefix}{obj.qualname[len(old_prefix):]}"
    obj.module = module_name
    if obj.signature and obj.signature.startswith(old_prefix):
        obj.signature = f"{new_prefix}{obj.signature[len(old_prefix):]}"
    obj.metadata = dict(obj.metadata)
    obj.metadata.setdefault("reexported_from", original_qualname)
    for member in obj.members:
        _remap_reexported_object(
            member,
            old_prefix=old_prefix,
            new_prefix=new_prefix,
            module_name=module_name,
        )


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
    if config.include_private and config.public_policy != "explicit" and name.startswith("_"):
        return True
    return config.public_api_policy().module_name_is_public(name, qualname, public_names)


def _class_member_is_public(
    name: str,
    config: ApiCollectConfig,
    qualname: str | None = None,
) -> bool:
    if config.include_private and config.public_policy != "explicit" and name.startswith("_"):
        return True
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
