"""Command line interface for API object collection workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs.apidoc.collect import collect_api
from oodocs.apidoc.config import ApiBuildConfig, ApiCollectConfig
from oodocs.apidoc.coverage import check_api_docs
from oodocs.apidoc.diff import ApiSnapshot, diff_api
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


def _add_collect_options(parser: argparse.ArgumentParser) -> None:
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
        choices=("auto", "google", "numpy", "sphinx", "markdown", "plain"),
        help="Docstring parser style.",
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


def _add_filter_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", action="append", help="Filter object kind; may be repeated.")
    parser.add_argument("--module-prefix", help="Filter module prefix.")


def _run_collect(args: argparse.Namespace) -> int:
    api = _collect_from_args(args)
    api.write_json(args.out)
    print(f"Wrote api-json: {Path(args.out)}")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    api = _filter_from_args(_collect_from_args(args), args)
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
    if result.issues:
        for issue in result.issues[:20]:
            print(f"- {issue.severity.upper()} {issue.code}: {issue.qualname or issue.module or api.name} - {issue.message}")
        if len(result.issues) > 20:
            print(f"... {len(result.issues) - 20} more issue(s)")
    return 1 if any(issue.severity == "error" for issue in result.issues) else 0


def _run_build(args: argparse.Namespace) -> int:
    build_config = ApiBuildConfig.read_file(args.config) if args.config else ApiBuildConfig()
    api = _collect_from_args(args, config=build_config.collection)
    kind = tuple(args.kind) if args.kind else build_config.kind or None
    module_prefix = args.module_prefix or build_config.module_prefix
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
    api = _filter_from_args(_collect_from_args(args), args)
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
    if config is None and args.config:
        config = ApiCollectConfig.read_file(args.config)
    return collect_api(
        args.package,
        config=config,
        collector=args.collector,
        public_policy=args.public_policy,
        explicit_names=args.explicit_names,
        docstring_style=args.docstring_style,
        include_imported=args.include_imported,
        include_inherited=args.include_inherited,
        module_include_patterns=args.module_include_patterns,
        module_exclude_patterns=args.module_exclude_patterns,
    )


def _filter_from_args(api: ApiPackage, args: argparse.Namespace) -> ApiPackage:
    return _filter_api(
        api,
        kind=tuple(args.kind) if args.kind else None,
        module_prefix=args.module_prefix,
    )


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
