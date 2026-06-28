"""Sample argparse CLI used by the CLI manual example."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build a small multi-command parser for documentation."""

    parser = argparse.ArgumentParser(
        prog="docctl",
        description="Render and validate documentation artifacts.",
    )
    parser.add_argument(
        "--config",
        default="pyproject.toml",
        help="Project configuration file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress messages.",
    )

    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    render = commands.add_parser("render", help="Render one source document.")
    render.add_argument("source", help="Python, Markdown, or notebook source file.")
    render.add_argument(
        "--output-dir",
        default="artifacts/docs",
        help="Directory for rendered artifacts.",
    )
    render.add_argument(
        "--format",
        action="append",
        choices=("docx", "pdf", "html"),
        dest="formats",
        help="Output format to render. Repeat for multiple formats.",
    )

    validate = commands.add_parser("validate", help="Validate one source document.")
    validate.add_argument("source", help="Source file to validate.")
    validate.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Treat validation warnings as command failures.",
    )
    validate.add_argument(
        "--json",
        dest="json_path",
        help="Write validation diagnostics to this JSON path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments for the sample command."""

    build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
