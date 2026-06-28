"""Build a CLI manual from an argparse parser."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Sequence

from oodocs import (
    Chapter,
    CodeBlock,
    Document,
    DocumentSettings,
    OutputBundle,
    Paragraph,
    Section,
    Table,
    TableOfContents,
    inline_code,
)


EXAMPLE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path("artifacts") / "cli-manual-example"
OUTPUT_STEM = "cli-manual"
SAMPLE_CLI_PATH = EXAMPLE_DIR / "sample_cli.py"


def load_sample_parser() -> argparse.ArgumentParser:
    """Load the sample parser from ``sample_cli.py``."""

    spec = importlib.util.spec_from_file_location("cli_manual_sample_cli", SAMPLE_CLI_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load sample CLI from {SAMPLE_CLI_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_parser()


def argparse_parser_to_section(
    parser: argparse.ArgumentParser,
    *,
    title: str = "Command Reference",
) -> Section:
    """Convert an ``argparse`` parser into an OODocs section."""

    commands = _subcommands(parser)
    return Section(
        title,
        Paragraph(
            "The manual is generated from the parser object, so option names, defaults, and command summaries stay downstream of the runnable CLI."
        ),
        CodeBlock(parser.format_usage().strip(), language="text"),
        _actions_table(parser, caption="Top-level command options."),
        _commands_table(commands),
        *[
            Section(
                f"{name} command",
                CodeBlock(command.format_usage().strip(), language="text"),
                _actions_table(command, caption=f"Options for docctl {name}."),
                level=2,
            )
            for name, command in commands
        ],
        toc=True,
    )


def _subcommands(
    parser: argparse.ArgumentParser,
) -> tuple[tuple[str, argparse.ArgumentParser], ...]:
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and choices:
            return tuple(
                (name, command)
                for name, command in choices.items()
                if isinstance(command, argparse.ArgumentParser)
            )
    return ()


def _actions_table(parser: argparse.ArgumentParser, *, caption: str) -> Table:
    rows = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if getattr(action, "choices", None) and _subcommands(parser):
            continue
        name = ", ".join(action.option_strings) if action.option_strings else action.dest
        default = "" if action.default in (None, argparse.SUPPRESS, False) else str(action.default)
        choices = ", ".join(str(choice) for choice in action.choices or ())
        rows.append(
            [
                name,
                action.metavar or "",
                default,
                choices,
                action.help or "",
            ]
        )
    if not rows:
        rows = [["(none)", "", "", "", "No options."]]
    return Table(
        ["Option", "Value", "Default", "Choices", "Description"],
        rows,
        caption=caption,
        split=True,
    )


def _commands_table(commands: Sequence[tuple[str, argparse.ArgumentParser]]) -> Table:
    rows = [
        [name, command.description or command.format_usage().strip(), command.format_usage().strip()]
        for name, command in commands
    ]
    return Table(
        ["Command", "Purpose", "Usage"],
        rows or [["(none)", "No subcommands.", ""]],
        caption="Subcommands discovered from argparse subparsers.",
        split=True,
    )


def build_document(parser: argparse.ArgumentParser | None = None) -> Document:
    """Build the CLI manual example document."""

    parser = parser or load_sample_parser()
    exit_code_table = Table(
        ["Exit code", "Meaning", "Policy"],
        [
            ["0", "Command completed successfully.", "Use for rendered or validated inputs."],
            ["1", "Validation failed.", "Use when errors or denied warnings remain."],
            ["2", "Argument parsing failed.", "argparse emits this before command execution."],
        ],
        caption="Exit code policy for the documented CLI.",
    )
    examples_table = Table(
        ["Task", "Command"],
        [
            ["Render HTML", "docctl render report.py --format html"],
            ["Render PDF and DOCX", "docctl render report.py --format pdf --format docx"],
            ["Validate with JSON diagnostics", "docctl validate report.py --json artifacts/validation.json"],
        ],
        caption="Copyable command examples generated for the manual.",
    )
    return Document(
        "CLI Manual Example",
        TableOfContents(max_level=2),
        Chapter(
            "Command Overview",
            Paragraph(
                "This example documents a Python argparse parser as an OODocs manual. It is intentionally local to the example so the pattern can mature before becoming core API."
            ),
            argparse_parser_to_section(parser),
        ),
        Chapter(
            "Exit Codes",
            exit_code_table,
        ),
        Chapter(
            "Examples",
            examples_table,
        ),
        settings=DocumentSettings(
            metadata_author="OODocs Contributors",
            subtitle="argparse command reference generated as DOCX, PDF, and HTML",
            summary="CLI manual generated from a sample argparse parser",
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the CLI manual example."""

    output_path = Path(output_dir)
    document = build_document()
    document.validate(raise_on_error=True)
    return document.save_all(
        output_path,
        stem=OUTPUT_STEM,
        formats=tuple(output_formats or ("docx", "pdf", "html")),
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Render the example from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs CLI manual example.",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        type=Path,
        help="Directory where rendered files are written.",
    )
    parser.add_argument(
        "--outputs",
        action="append",
        choices=("docx", "pdf", "html"),
        dest="output_formats",
        help="Output format to render. Repeat for multiple formats.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress and output-path messages.",
    )
    args = parser.parse_args(argv)

    outputs = build(
        args.output_dir,
        output_formats=args.output_formats,
        verbose=not args.quiet,
    )
    if not args.quiet:
        for output_format, path in outputs:
            print(f"Wrote {output_format}: {path}")


if __name__ == "__main__":
    main()
