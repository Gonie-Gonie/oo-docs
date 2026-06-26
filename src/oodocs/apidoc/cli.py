"""Command line interface for API object collection workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs.apidoc.collect import collect_api
from oodocs.apidoc.config import ApiBuildConfig, ApiCollectConfig
from oodocs.apidoc.coverage import check_api_docs
from oodocs.apidoc.diff import ApiSnapshot, diff_api
from oodocs.apidoc.docstring import (
    docstring_parser_import_paths,
    load_docstring_parser_modules,
)


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
            "collect",
            ".",
            "--public-policy",
            "__all__",
            "--save-json",
            "artifacts/api.json",
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
        description="Collect, check, snapshot, and diff Python API documentation objects.",
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
        "--config-format",
        dest="config_format",
        choices=("auto", "pyproject", "json"),
        default="auto",
        help="Config file format. Defaults to pyproject for directories/TOML paths and JSON for .json paths.",
    )
    init.add_argument("--out-dir", default="artifacts/api", help="Default rendered API output directory.")
    init.add_argument("--outputs", default="docx,pdf,html", help="Default comma-separated output formats.")
    init.add_argument("--stem", help="Default output file stem.")
    init.add_argument(
        "--presentation-profile",
        default="reference",
        help="Default presentation profile.",
    )
    init.add_argument("--sidecars", action="store_true", default=True, help="Write sidecars by default.")
    init.add_argument("--no-sidecars", action="store_false", dest="sidecars", help="Disable sidecars by default.")
    init.add_argument("--max-level", type=int, help="Default deepest nested API heading level.")
    _add_filter_options(init)
    _add_collect_options(init, include_config=False)
    init.set_defaults(func=_run_init)

    collect = subparsers.add_parser("collect", help="Collect API objects to JSON.")
    collect.add_argument("package", help="Package/module name, Python file, or package directory.")
    collect.add_argument("--save-json", required=True, help="Output API object JSON path.")
    _add_collect_options(collect)
    collect.set_defaults(func=_run_collect)

    check = subparsers.add_parser("check", help="Check API documentation coverage.")
    check.add_argument("package", help="Package/module name, Python file, or package directory.")
    check.add_argument("--fail-under", type=float, help="Minimum documented-object ratio.")
    check.add_argument("--require-examples", action="store_true", help="Require examples for public API objects.")
    check.add_argument("--require-renderer-notes", action="store_true", help="Require renderer notes for public API objects.")
    check.add_argument("--report-format", choices=("text", "json"), default="text", help="Coverage report format.")
    check.add_argument("--save-json", help="Optional coverage result JSON path.")
    check.add_argument("--save-csv", help="Optional coverage issues CSV path.")
    _add_filter_options(check)
    _add_collect_options(check)
    check.set_defaults(func=_run_check)

    snapshot = subparsers.add_parser("snapshot", help="Write a public API snapshot JSON.")
    snapshot.add_argument("package", help="Package/module name, Python file, or package directory.")
    snapshot.add_argument("--save-json", required=True, help="Output snapshot JSON path.")
    _add_filter_options(snapshot)
    _add_collect_options(snapshot)
    snapshot.set_defaults(func=_run_snapshot)

    diff = subparsers.add_parser("diff", help="Write differences between two API snapshots.")
    diff.add_argument("base", help="Base snapshot JSON path.")
    diff.add_argument("head", help="Head snapshot JSON path.")
    diff.add_argument("--save-json", required=True, help="Output diff JSON path.")
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
    with docstring_parser_import_paths(_init_import_target(args.path)):
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
        profile=args.presentation_profile,
        output_formats=_split_outputs(args.outputs),
        stem=args.stem,
        max_level=args.max_level,
        sidecars=args.sidecars,
        output_dir=args.out_dir,
        kind=tuple(args.kind) if args.kind else (),
        module_prefix=args.module_prefix,
    )
    output_format = _config_output_format(args.path, args.config_format)
    if output_format == "json":
        output_path = config.save_json(args.path)
    else:
        output_path = config.save_pyproject(args.path)
    print(f"Wrote apidoc-config: {output_path}")
    return 0


def _run_collect(args: argparse.Namespace) -> int:
    api = _collect_from_args(args)
    api.save_json(args.save_json)
    print(f"Wrote api-json: {Path(args.save_json)}")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    build_config = _effective_build_config_from_args(args)
    result = build_config.check_docs(
        args.package,
        fail_under=args.fail_under,
        require_examples=args.require_examples,
        require_renderer_notes=args.require_renderer_notes,
    )
    if args.save_json:
        result.save_json(args.save_json)
    if args.save_csv:
        result.save_csv(args.save_csv)
    if args.report_format == "json":
        print(result.to_json(indent=2))
    else:
        print(result.format_text())
        if args.save_json:
            print(f"Wrote coverage-json: {args.save_json}")
        if args.save_csv:
            print(f"Wrote coverage-csv: {args.save_csv}")
    return 0 if result.ok else 1


def _run_snapshot(args: argparse.Namespace) -> int:
    build_config = _effective_build_config_from_args(args)
    build_config.save_snapshot(args.package, args.save_json)
    print(f"Wrote api-snapshot: {Path(args.save_json)}")
    return 0


def _run_diff(args: argparse.Namespace) -> int:
    base = ApiSnapshot.load_json(args.base)
    head = ApiSnapshot.load_json(args.head)
    result = diff_api(base, head)
    result.save_json(args.save_json)
    print(f"Wrote api-diff: {Path(args.save_json)}")
    return 0


def _collect_from_args(
    args: argparse.Namespace,
    *,
    config: ApiCollectConfig | None = None,
):
    _load_docstring_parser_modules_from_args(args)
    if config is None and args.config:
        config = ApiCollectConfig.load_file(
            args.config,
            target=_target_from_args(args),
        )
    return collect_api(args.package, config=_collect_config_from_args(args, config))


def _build_config_from_args(args: argparse.Namespace) -> ApiBuildConfig:
    _load_docstring_parser_modules_from_args(args)
    if not args.config:
        return ApiBuildConfig()
    return ApiBuildConfig.load_file(args.config, target=_target_from_args(args))


def _effective_build_config_from_args(
    args: argparse.Namespace,
) -> ApiBuildConfig:
    base = _build_config_from_args(args)
    return ApiBuildConfig(
        collection=_collect_config_from_args(args, base.collection),
        profile=base.profile,
        output_formats=base.output_formats,
        stem=base.stem,
        max_level=base.max_level,
        sidecars=base.sidecars,
        output_dir=base.output_dir,
        kind=tuple(args.kind) if args.kind else base.kind,
        module_prefix=args.module_prefix or base.module_prefix,
    )


def _collect_config_from_args(
    args: argparse.Namespace,
    config: ApiCollectConfig | None = None,
) -> ApiCollectConfig:
    return ApiCollectConfig.from_kwargs(
        config,
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


def _load_docstring_parser_modules_from_args(args: argparse.Namespace) -> None:
    modules = getattr(args, "docstring_parser_modules", None)
    if modules:
        with docstring_parser_import_paths(_target_from_args(args)):
            load_docstring_parser_modules(modules)


def _target_from_args(args: argparse.Namespace) -> object:
    return getattr(args, "package", None) or getattr(args, "path", None)


def _init_import_target(path: str | Path) -> Path:
    target = Path(path)
    if target.is_dir():
        return target
    return target.parent if target.suffix else target


def _split_outputs(value: str) -> tuple[str, ...]:
    return tuple(piece.strip() for piece in value.split(",") if piece.strip())


def _config_output_format(path: str | Path, requested: str) -> str:
    if requested != "auto":
        return requested
    target = Path(path)
    return "json" if target.suffix.lower() == ".json" else "pyproject"




if __name__ == "__main__":
    raise SystemExit(main())
