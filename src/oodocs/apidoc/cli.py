"""Command line interface for API object collection workflows."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Sequence

from oodocs.apidoc.collect import collect_api
from oodocs.apidoc.config import ApiBuildConfig, ApiCollectConfig
from oodocs.apidoc.coverage import check_api_docs
from oodocs.apidoc.diff import ApiSnapshot, diff_api
from oodocs.apidoc.docstring import load_docstring_parser_modules
from oodocs.apidoc.model import ApiObject, ApiPackage
from oodocs.compatibility import normalize_output_formats
from oodocs.components.blocks import Chapter
from oodocs.document import Document


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``oodocs apidoc`` command.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.

    Examples:
        Invoke the CLI entrypoint from a Python automation script:

        ```python
        from oodocs.apidoc.cli import main

        exit_code = main([
            "build",
            ".",
            "--profile",
            "reference",
            "--out",
            "artifacts/api",
            "--to",
            "html",
            "--sidecars",
        ])
        assert exit_code == 0
        ```
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oodocs apidoc",
        description="Collect, check, snapshot, diff, and render Python API documentation objects.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create an apidoc config for a Python repository.")
    init.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project root, pyproject.toml path, or JSON config path.",
    )
    init.add_argument(
        "--format",
        choices=("auto", "pyproject", "json"),
        default="auto",
        help="Config file format. Defaults to pyproject for directories/TOML paths and JSON for .json paths.",
    )
    init.add_argument("--out-dir", default="artifacts/api", help="Default rendered API output directory.")
    init.add_argument("--to", default="docx,pdf,html", help="Default comma-separated output formats.")
    init.add_argument("--stem", help="Default output file stem.")
    init.add_argument("--profile", default="reference", help="Default presentation profile.")
    init.add_argument("--sidecars", action="store_true", default=True, help="Write sidecars by default.")
    init.add_argument("--no-sidecars", action="store_false", dest="sidecars", help="Disable sidecars by default.")
    init.add_argument("--max-level", type=int, help="Default deepest nested API heading level.")
    _add_filter_options(init)
    _add_collect_options(init, include_config=False)
    init.set_defaults(func=_run_init)

    collect = subparsers.add_parser("collect", help="Collect API objects to JSON.")
    collect.add_argument("package", help="Package/module name, Python file, or package directory.")
    collect.add_argument("--out", required=True, help="Output API object JSON path.")
    _add_collect_options(collect)
    collect.set_defaults(func=_run_collect)

    check = subparsers.add_parser("check", help="Check API documentation coverage.")
    check.add_argument("package", help="Package/module name, Python file, or package directory.")
    check.add_argument("--fail-under", type=float, help="Minimum documented-object ratio.")
    check.add_argument("--require-examples", action="store_true", help="Require examples for public API objects.")
    check.add_argument("--require-renderer-notes", action="store_true", help="Require renderer notes for public API objects.")
    check.add_argument("--out-json", help="Optional coverage result JSON path.")
    check.add_argument("--out-csv", help="Optional coverage issues CSV path.")
    _add_filter_options(check)
    _add_collect_options(check)
    check.set_defaults(func=_run_check)

    build = subparsers.add_parser("build", help="Build rendered API documentation.")
    build.add_argument("package", help="Package/module name, Python file, or package directory.")
    build.add_argument("--out", help="Output directory.")
    build.add_argument("--to", help="Comma-separated output formats.")
    build.add_argument("--stem", help="Output file stem.")
    build.add_argument("--profile", help="Presentation profile.")
    build.add_argument(
        "--sidecars",
        action="store_true",
        default=None,
        help="Write API JSON and coverage JSON/CSV sidecars beside rendered documents.",
    )
    build.add_argument(
        "--max-level",
        type=int,
        help="Deepest heading level to render for nested API sections.",
    )
    _add_filter_options(build)
    _add_collect_options(build)
    build.set_defaults(func=_run_build)

    snapshot = subparsers.add_parser("snapshot", help="Write a public API snapshot JSON.")
    snapshot.add_argument("package", help="Package/module name, Python file, or package directory.")
    snapshot.add_argument("--out", required=True, help="Output snapshot JSON path.")
    _add_filter_options(snapshot)
    _add_collect_options(snapshot)
    snapshot.set_defaults(func=_run_snapshot)

    diff = subparsers.add_parser("diff", help="Render differences between two API snapshots.")
    diff.add_argument("--base", required=True, help="Base snapshot JSON path.")
    diff.add_argument("--head", required=True, help="Head snapshot JSON path.")
    diff.add_argument("--out", required=True, help="Output directory.")
    diff.add_argument("--to", default="docx,pdf,html", help="Comma-separated output formats.")
    diff.add_argument("--stem", default="api-diff", help="Output file stem.")
    diff.set_defaults(func=_run_diff)
    return parser


def _add_collect_options(parser: argparse.ArgumentParser, *, include_config: bool = True) -> None:
    if include_config:
        parser.add_argument(
            "--config",
            help="Collection config JSON or pyproject.toml with [tool.oodocs.apidoc].",
        )
    parser.add_argument(
        "--collector",
        choices=("auto", "inspect", "griffe"),
        help="Collector backend.",
    )
    parser.add_argument(
        "--fallback-collector",
        choices=("inspect", "none"),
        help="Fallback backend when griffe is unavailable or cannot load the target.",
    )
    parser.add_argument(
        "--public-policy",
        choices=("__all__", "underscore", "all", "explicit"),
        help="Public API boundary policy.",
    )
    parser.add_argument(
        "--explicit-name",
        action="append",
        dest="explicit_names",
        help="Explicit public name for public-policy=explicit.",
    )
    parser.add_argument(
        "--docstring-style",
        help="Docstring parser style or registered custom parser name.",
    )
    parser.add_argument(
        "--docstring-parser-module",
        action="append",
        dest="docstring_parser_modules",
        help="Import a module that registers custom docstring parsers; may be repeated.",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        default=None,
        help="Include underscore-prefixed objects in addition to the public boundary.",
    )
    parser.add_argument(
        "--no-private",
        action="store_false",
        dest="include_private",
        default=None,
        help="Exclude underscore-prefixed objects.",
    )
    parser.add_argument(
        "--include-imported",
        action="store_true",
        default=None,
        help="Include public imported aliases when the collector can represent them.",
    )
    parser.add_argument(
        "--include-inherited",
        action="store_true",
        default=None,
        help="Include inherited class members when the collector can resolve them.",
    )
    parser.add_argument(
        "--include-attributes",
        action="store_true",
        default=None,
        help="Include module data and class attributes in the collected API tree.",
    )
    parser.add_argument(
        "--no-attributes",
        action="store_false",
        dest="include_attributes",
        default=None,
        help="Exclude module data and class attributes from the collected API tree.",
    )
    parser.add_argument(
        "--include-properties",
        action="store_true",
        default=None,
        help="Include class properties in the collected API tree.",
    )
    parser.add_argument(
        "--no-properties",
        action="store_false",
        dest="include_properties",
        default=None,
        help="Exclude class properties from the collected API tree.",
    )
    parser.add_argument(
        "--include-methods",
        action="store_true",
        default=None,
        help="Include class methods in the collected API tree.",
    )
    parser.add_argument(
        "--no-methods",
        action="store_false",
        dest="include_methods",
        default=None,
        help="Exclude class methods from the collected API tree.",
    )
    parser.add_argument(
        "--include-source-locations",
        action="store_true",
        default=None,
        help="Retain source paths and line numbers in API trees and diagnostics.",
    )
    parser.add_argument(
        "--no-source-locations",
        action="store_false",
        dest="include_source_locations",
        default=None,
        help="Remove source paths and line numbers from API trees and diagnostics.",
    )
    parser.add_argument(
        "--class-signature-from-init",
        action="store_true",
        default=None,
        help="Build class signatures from __init__ parameters.",
    )
    parser.add_argument(
        "--no-class-signature-from-init",
        action="store_false",
        dest="class_signature_from_init",
        help="Render class signatures without __init__ parameters.",
    )
    parser.add_argument(
        "--module-include",
        action="append",
        dest="module_include_patterns",
        help="Glob-style module name pattern to include during collection.",
    )
    parser.add_argument(
        "--module-exclude",
        action="append",
        dest="module_exclude_patterns",
        help="Glob-style module name pattern to exclude during collection.",
    )
    parser.add_argument(
        "--object-include",
        action="append",
        dest="object_include_patterns",
        help="Glob-style object name or qualname pattern to include after collection.",
    )
    parser.add_argument(
        "--object-exclude",
        action="append",
        dest="object_exclude_patterns",
        help="Glob-style object name or qualname pattern to exclude after collection.",
    )


def _add_filter_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", action="append", help="Filter object kind; may be repeated.")
    parser.add_argument("--module-prefix", help="Filter module prefix.")


def _run_init(args: argparse.Namespace) -> int:
    collection = ApiCollectConfig.from_kwargs(
        collector=args.collector,
        fallback_collector=args.fallback_collector,
        public_policy=args.public_policy,
        explicit_names=args.explicit_names,
        docstring_style=args.docstring_style,
        docstring_parser_modules=args.docstring_parser_modules,
        include_private=args.include_private,
        include_imported=args.include_imported,
        include_inherited=args.include_inherited,
        include_attributes=args.include_attributes,
        include_properties=args.include_properties,
        include_methods=args.include_methods,
        include_source_locations=args.include_source_locations,
        class_signature_from_init=args.class_signature_from_init,
        module_include_patterns=args.module_include_patterns,
        module_exclude_patterns=args.module_exclude_patterns,
        object_include_patterns=args.object_include_patterns,
        object_exclude_patterns=args.object_exclude_patterns,
    )
    config = ApiBuildConfig(
        collection=collection,
        profile=args.profile,
        output_formats=_split_csv(args.to),
        stem=args.stem,
        max_level=args.max_level,
        sidecars=args.sidecars,
        output_dir=args.out_dir,
        kind=tuple(args.kind) if args.kind else (),
        module_prefix=args.module_prefix,
    )
    output_format = _config_output_format(args.path, args.format)
    if output_format == "json":
        output_path = config.write_json(args.path)
    else:
        output_path = config.write_pyproject(args.path)
    print(f"Wrote apidoc-config: {output_path}")
    return 0


def _run_collect(args: argparse.Namespace) -> int:
    api = _collect_from_args(args)
    api.write_json(args.out)
    print(f"Wrote api-json: {Path(args.out)}")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    build_config = _build_config_from_args(args)
    kind, module_prefix = _filter_options_from_args(args, build_config)
    api = _filter_api(
        _collect_from_args(args, config=build_config.collection),
        kind=kind,
        module_prefix=module_prefix,
    )
    result = check_api_docs(
        api,
        fail_under=args.fail_under,
        require_examples=args.require_examples,
        require_renderer_notes=args.require_renderer_notes,
    )
    print(
        f"{api.name}: {result.documented_object_count}/{result.public_object_count} "
        f"public objects documented ({result.object_coverage:.1%})"
    )
    if args.out_json:
        result.write_json(args.out_json)
        print(f"Wrote coverage-json: {args.out_json}")
    if args.out_csv:
        result.write_csv(args.out_csv)
        print(f"Wrote coverage-csv: {args.out_csv}")
    if result.issues:
        for issue in result.issues[:20]:
            print(f"- {issue.severity.upper()} {issue.code}: {issue.qualname or issue.module or api.name} - {issue.message}")
        if len(result.issues) > 20:
            print(f"... {len(result.issues) - 20} more issue(s)")
    return 1 if any(issue.severity == "error" for issue in result.issues) else 0


def _run_build(args: argparse.Namespace) -> int:
    build_config = _build_config_from_args(args)
    api = _collect_from_args(args, config=build_config.collection)
    kind, module_prefix = _filter_options_from_args(args, build_config)
    rendered_api = _filter_api(api, kind=kind, module_prefix=module_prefix)
    profile = args.profile or build_config.profile
    formats = normalize_output_formats(_split_csv(args.to) if args.to else build_config.output_formats)
    stem = args.stem or build_config.stem or f"{api.name.replace('.', '-')}-api"
    max_level = args.max_level if args.max_level is not None else build_config.max_level
    output_dir = args.out or build_config.output_dir
    if output_dir is None:
        raise SystemExit("oodocs apidoc build requires --out or output-dir in config")
    if _has_filter_values(kind, module_prefix):
        selected = _top_level_objects(rendered_api)
        document = Document(
            f"{api.name} API Reference",
            Chapter(
                "Selected API",
                rendered_api.to_summary_table(
                    selected,
                    caption="Selected public API objects",
                    profile=profile,
                ),
                *[
                    obj.to_section(
                        level=2,
                        profile=profile,
                        max_level=max_level,
                    )
                    for obj in selected
                ],
            ),
        )
    else:
        document = rendered_api.to_document(profile=profile, max_level=max_level)
    outputs = document.save_all(
        output_dir,
        stem=stem,
        formats=formats,
    )
    _print_outputs(outputs)
    sidecars = args.sidecars if args.sidecars is not None else build_config.sidecars
    if sidecars:
        _write_build_sidecars(rendered_api, output_dir, stem)
    return 0


def _run_snapshot(args: argparse.Namespace) -> int:
    build_config = _build_config_from_args(args)
    kind, module_prefix = _filter_options_from_args(args, build_config)
    api = _filter_api(
        _collect_from_args(args, config=build_config.collection),
        kind=kind,
        module_prefix=module_prefix,
    )
    ApiSnapshot.from_package(api).write_json(args.out)
    print(f"Wrote api-snapshot: {Path(args.out)}")
    return 0


def _run_diff(args: argparse.Namespace) -> int:
    base = ApiSnapshot.read_json(args.base)
    head = ApiSnapshot.read_json(args.head)
    result = diff_api(base, head)
    document = result.to_document()
    outputs = document.save_all(
        args.out,
        stem=args.stem,
        formats=normalize_output_formats(_split_csv(args.to)),
    )
    result.write_json(Path(args.out) / f"{args.stem}.json")
    _print_outputs(outputs)
    return 0


def _collect_from_args(
    args: argparse.Namespace,
    *,
    config: ApiCollectConfig | None = None,
):
    _load_docstring_parser_modules_from_args(args)
    if config is None and args.config:
        config = ApiCollectConfig.read_file(args.config)
    return collect_api(
        args.package,
        config=config,
        collector=args.collector,
        fallback_collector=args.fallback_collector,
        public_policy=args.public_policy,
        explicit_names=args.explicit_names,
        docstring_style=args.docstring_style,
        docstring_parser_modules=args.docstring_parser_modules,
        include_private=args.include_private,
        include_imported=args.include_imported,
        include_inherited=args.include_inherited,
        include_attributes=args.include_attributes,
        include_properties=args.include_properties,
        include_methods=args.include_methods,
        include_source_locations=args.include_source_locations,
        class_signature_from_init=args.class_signature_from_init,
        module_include_patterns=args.module_include_patterns,
        module_exclude_patterns=args.module_exclude_patterns,
        object_include_patterns=args.object_include_patterns,
        object_exclude_patterns=args.object_exclude_patterns,
    )


def _build_config_from_args(args: argparse.Namespace) -> ApiBuildConfig:
    _load_docstring_parser_modules_from_args(args)
    return ApiBuildConfig.read_file(args.config) if args.config else ApiBuildConfig()


def _filter_options_from_args(
    args: argparse.Namespace,
    build_config: ApiBuildConfig,
) -> tuple[tuple[str, ...] | None, str | None]:
    kind = tuple(args.kind) if args.kind else build_config.kind or None
    module_prefix = args.module_prefix or build_config.module_prefix
    return kind, module_prefix


def _load_docstring_parser_modules_from_args(args: argparse.Namespace) -> None:
    modules = getattr(args, "docstring_parser_modules", None)
    if modules:
        with _docstring_parser_import_paths(args):
            load_docstring_parser_modules(modules)


@contextmanager
def _docstring_parser_import_paths(args: argparse.Namespace):
    target = getattr(args, "package", None) or getattr(args, "path", None)
    roots = _candidate_import_roots(target)
    added: list[str] = []
    for root in reversed([str(path) for path in roots]):
        if root not in sys.path:
            sys.path.insert(0, root)
            added.append(root)
    try:
        yield
    finally:
        for root in added:
            try:
                sys.path.remove(root)
            except ValueError:  # pragma: no cover - defensive against user mutation.
                pass


def _candidate_import_roots(target: object) -> list[Path]:
    if target is None:
        return []
    path = Path(str(target))
    if not path.exists():
        return []
    resolved = path.resolve()
    if resolved.is_file():
        return [resolved.parent]

    roots = [resolved]
    src_root = resolved / "src"
    if src_root.is_dir():
        roots.append(src_root.resolve())
    parent = resolved.parent
    if parent != resolved:
        roots.append(parent)

    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return unique


def _filter_api(
    api: ApiPackage,
    *,
    kind: tuple[str, ...] | None = None,
    module_prefix: str | None = None,
) -> ApiPackage:
    if not _has_filter_values(kind, module_prefix):
        return api
    return api.filtered(
        kind=kind,
        module_prefix=module_prefix,
    )


def _has_filters(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "kind", None) or getattr(args, "module_prefix", None))


def _has_filter_values(kind: tuple[str, ...] | None, module_prefix: str | None) -> bool:
    return bool(kind or module_prefix)


def _top_level_objects(api: ApiPackage) -> list[ApiObject]:
    return [member for module in api.modules for member in module.members]


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(piece.strip() for piece in value.split(",") if piece.strip())


def _config_output_format(path: str | Path, requested: str) -> str:
    if requested != "auto":
        return requested
    target = Path(path)
    return "json" if target.suffix.lower() == ".json" else "pyproject"


def _print_outputs(outputs: dict[object, Path]) -> None:
    for output_format, path in outputs.items():
        print(f"Wrote {output_format}: {path}")


def _write_build_sidecars(api: ApiPackage, output_dir: str | Path, stem: str) -> None:
    directory = Path(output_dir)
    api_path = api.write_json(directory / f"{stem}.json")
    coverage = check_api_docs(api)
    coverage_json_path = coverage.write_json(directory / f"{stem}-coverage.json")
    coverage_csv_path = coverage.write_csv(directory / f"{stem}-coverage.csv")
    print(f"Wrote api-json: {api_path}")
    print(f"Wrote coverage-json: {coverage_json_path}")
    print(f"Wrote coverage-csv: {coverage_csv_path}")


if __name__ == "__main__":
    raise SystemExit(main())
