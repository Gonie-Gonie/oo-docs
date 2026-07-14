"""Build a CLI manual from an argparse parser."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Sequence

from oodocs import (
    Chapter,
    Document,
    DocumentMetadata,
    DocumentSettings,
    OutputBundle,
    Paragraph,
    Table,
    TableOfContents,
    TitleMatter,
)
from oodocs.clidoc import CliApplication
from oodocs.integrations.argparse import collect_argparse_cli


EXAMPLE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path("artifacts") / "cli-manual-example"
OUTPUT_STEM = "cli-manual"
SAMPLE_CLI_PATH = EXAMPLE_DIR / "sample_cli.py"


def load_sample_parser() -> argparse.ArgumentParser:
    """Load the side-effect-free parser builder from ``sample_cli.py``.

    Importing a module executes its top-level code. The sample module therefore
    keeps argument parsing and command execution behind its ``__main__`` guard.
    """

    spec = importlib.util.spec_from_file_location("cli_manual_sample_cli", SAMPLE_CLI_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load sample CLI from {SAMPLE_CLI_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_parser()


def build_document(parser: argparse.ArgumentParser | None = None) -> Document:
    """Build the CLI manual example document."""

    parser = parser or load_sample_parser()
    application: CliApplication = collect_argparse_cli(parser)
    exit_code_table = Table(
        ["Exit code", "Meaning", "Policy"],
        [
            ["0", "Command completed successfully.", "Use for rendered or validated inputs."],
            ["1", "Validation failed.", "Use when errors or denied warnings remain."],
            ["2", "Argument parsing failed.", "argparse emits this before command execution."],
        ],
        caption="Exit code policy for the documented CLI.",
    )
    environment_table = Table(
        ["Variable", "Required", "Behavior"],
        [
            [
                "(none)",
                "No",
                "This sample CLI does not read configuration from environment variables.",
            ]
        ],
        caption="Environment-variable policy supplied by the manual author.",
    )
    executable = application.root_command.name
    examples_table = Table(
        ["Task", "Command"],
        [
            ["Render HTML", f"{executable} render report.py --format html"],
            [
                "Render PDF and DOCX",
                f"{executable} render report.py --format pdf --format docx",
            ],
            [
                "Validate with JSON diagnostics",
                f"{executable} validate report.py --json artifacts/validation.json",
            ],
        ],
        caption="Copyable command examples generated for the manual.",
    )
    return Document(
        "CLI Manual Example",
        TableOfContents(max_level=2),
        Chapter(
            "Command Overview",
            Paragraph(
                "This manual is generated from a neutral CLI model collected "
                "from a Python argparse parser."
            ),
            application.to_section(title="Command Reference"),
        ),
        Chapter(
            "Exit Codes",
            exit_code_table,
            environment_table,
        ),
        Chapter(
            "Examples",
            examples_table,
        ),
        settings=DocumentSettings(
            metadata=DocumentMetadata(
                author="Example Documentation Team",
                description="CLI manual generated from a sample argparse parser",
            ),
            title_matter=TitleMatter(
                subtitle="argparse command reference generated as DOCX, PDF, and HTML",
            ),
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
