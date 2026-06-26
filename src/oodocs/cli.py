"""Command line interface for OODocs workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import traceback
from typing import Sequence

from oodocs.compatibility import normalize_output_formats
from oodocs.core import OODocsError
from oodocs.importers.results import ImportResult
from oodocs.validation import DocumentValidationError
from oodocs.workflows import build_source_outputs, validate_source_document


def main(argv: Sequence[str] | None = None) -> int:
    """Run the OODocs CLI.

    Args:
        argv: Optional argument sequence. ``None`` reads arguments from
            ``sys.argv``.

    Returns:
        Process exit code. Validation failures return ``1`` and operational
        errors return ``2``.
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except DocumentValidationError as exc:
        if getattr(args, "traceback", False):
            traceback.print_exception(exc, file=sys.stderr)
        else:
            print(exc, file=sys.stderr)
        return 1
    except OODocsError as exc:
        if getattr(args, "traceback", False):
            traceback.print_exception(exc, file=sys.stderr)
        else:
            print(f"oodocs: {exc}", file=sys.stderr)
        return 2
    except (AttributeError, FileNotFoundError, ImportError, TypeError, ValueError) as exc:
        if getattr(args, "traceback", False):
            traceback.print_exception(exc, file=sys.stderr)
        else:
            print(f"oodocs: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oodocs",
        description="Build and validate OODocs documents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        help="Build a Python, Markdown, or notebook OODocs source.",
    )
    build.add_argument("source", help="Python, Markdown, or notebook source file.")
    _add_render_options(build, default_out=".")
    build.add_argument(
        "--source-type",
        choices=("python", "markdown", "notebook"),
        help="Override source type inference.",
    )
    build.add_argument("--title", help="Override imported Markdown/notebook title.")
    build.add_argument(
        "--document-factory",
        help="Document variable or zero-argument function to use from the Python source.",
    )
    build.add_argument(
        "--no-chdir",
        action="store_true",
        help="Do not run the Python source with its directory as the working directory.",
    )
    build.add_argument(
        "--show-import-warnings",
        action="store_true",
        help="Print lossy Markdown/notebook import warnings before rendering.",
    )
    build.add_argument(
        "--fail-on-import-warning",
        dest="fail_on_import_warning",
        action="store_true",
        help="Fail when Markdown/notebook import reports lossy or unsupported content.",
    )
    build.set_defaults(func=_run_build)

    validate = subparsers.add_parser(
        "validate",
        help="Validate a Python, Markdown, or notebook source document.",
    )
    validate.add_argument("source", help="Source file to validate.")
    validate.add_argument(
        "--outputs",
        default="docx,pdf,html",
        help="Comma-separated output formats to validate for. Defaults to docx,pdf,html.",
    )
    validate.add_argument(
        "--source-type",
        choices=("python", "markdown", "notebook"),
        help="Override source type inference.",
    )
    validate.add_argument("--title", help="Override imported Markdown/notebook title.")
    validate.add_argument(
        "--document-factory",
        help="Document variable or zero-argument function for Python sources.",
    )
    validate.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return a non-zero exit code when warnings are present.",
    )
    validate.add_argument(
        "--report-format",
        choices=("text", "json"),
        default="text",
        help="Validation output format. Defaults to text.",
    )
    validate.add_argument(
        "--no-chdir",
        action="store_true",
        help="Do not run Python sources with their directory as the working directory.",
    )
    _add_traceback_option(validate)
    validate.set_defaults(func=_run_validate)

    apidoc = subparsers.add_parser(
        "apidoc",
        help="Collect, check, snapshot, diff, and render Python API documentation.",
    )
    apidoc.add_argument("apidoc_args", nargs=argparse.REMAINDER)
    apidoc.set_defaults(func=_run_apidoc)

    return parser


def _add_render_options(
    parser: argparse.ArgumentParser,
    *,
    default_out: str | None,
) -> None:
    parser.add_argument(
        "--out",
        default=default_out,
        help=(
            "Output directory. Defaults to the current directory for build."
        ),
    )
    parser.add_argument(
        "--outputs",
        default="docx,pdf,html",
        help="Comma-separated output formats. Defaults to docx,pdf,html.",
    )
    parser.add_argument("--stem", help="Output filename stem.")
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation before rendering.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print slow major build steps.",
    )
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Print validation warnings even when rendering succeeds.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return a non-zero exit code when validation warnings are present.",
    )
    _add_traceback_option(parser)


def _add_traceback_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--traceback",
        action="store_true",
        help="Print a full traceback for debugging instead of the compact CLI error.",
    )


def _run_build(args: argparse.Namespace) -> int:
    formats = _parse_outputs(args.outputs)
    import_exit = _run_import_warning_policy(args)
    if import_exit != 0:
        return import_exit
    validation_exit = _run_render_warning_policy(
        args,
        formats=formats,
        source_type=args.source_type,
        title=args.title,
        document_factory=args.document_factory,
        chdir=not args.no_chdir,
    )
    if validation_exit != 0:
        return validation_exit
    outputs = build_source_outputs(
        args.source,
        args.out,
        source_type=args.source_type,
        title=args.title,
        outputs=formats,
        stem=args.stem,
        document_factory=args.document_factory,
        validate=not args.no_validate,
        chdir=not args.no_chdir,
        verbose=args.verbose,
    )
    _print_outputs(outputs.outputs)
    return 0


def _run_validate(args: argparse.Namespace) -> int:
    formats = _parse_outputs(args.outputs)
    result = validate_source_document(
        args.source,
        source_type=args.source_type,
        title=args.title,
        document_factory=args.document_factory,
        outputs=formats,
        chdir=not args.no_chdir,
    )
    if args.report_format == "json":
        print(result.to_json(formats=formats))
    else:
        print(result.format_text(formats=formats))
    if result.errors_for(formats):
        return 1
    if args.fail_on_warning and result.warnings_for(formats):
        return 1
    return 0


def _run_apidoc(args: argparse.Namespace) -> int:
    from oodocs.apidoc.cli import main as apidoc_main

    return apidoc_main(args.apidoc_args)


def _run_import_warning_policy(args: argparse.Namespace) -> int:
    if not (args.show_import_warnings or args.fail_on_import_warning):
        return 0

    source_path = Path(args.source)
    policy = "fail-on-lossy" if args.fail_on_import_warning else "record-lossy"
    suffix = source_path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        from oodocs.importers.markdown import parse_markdown_file

        result = parse_markdown_file(
            source_path,
            import_policy=policy,
        )
    elif suffix == ".ipynb":
        from oodocs.importers.notebook import parse_notebook

        result = parse_notebook(
            source_path,
            import_policy=policy,
        )
    else:
        raise ValueError(
            f"Cannot infer document source type from {source_path}. "
            "Use a Markdown or notebook source."
        )

    assert isinstance(result, ImportResult)
    if args.show_import_warnings and result.issues:
        print(result.format_text())
    return 0


def _run_render_warning_policy(
    args: argparse.Namespace,
    *,
    formats: tuple[str, ...],
    source_type: str | None = None,
    title: str | None = None,
    document_factory: str | None = None,
    chdir: bool = True,
) -> int:
    if args.no_validate or not (args.show_warnings or args.fail_on_warning):
        return 0

    result = validate_source_document(
        args.source,
        source_type=source_type,
        title=title,
        document_factory=document_factory,
        outputs=formats,
        chdir=chdir,
    )
    errors = result.errors_for(formats)
    warnings = result.warnings_for(formats)
    if args.show_warnings and warnings:
        print(result.format_text(formats=formats))
    if errors:
        print(result.format_text(formats=formats), file=sys.stderr)
        return 1
    if args.fail_on_warning and warnings:
        if not args.show_warnings:
            print(result.format_text(formats=formats), file=sys.stderr)
        return 1
    return 0


def _parse_outputs(value: str) -> tuple[str, ...]:
    pieces = tuple(piece.strip() for piece in value.split(",") if piece.strip())
    if not pieces:
        raise ValueError("--outputs must include at least one output format")
    return normalize_output_formats(pieces)


def _print_outputs(outputs: dict[object, Path]) -> None:
    for output_format, path in outputs.items():
        print(f"Wrote {output_format}: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
