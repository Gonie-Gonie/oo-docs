"""Build every template preset example."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import journal_article_template
from oodocs import OutputBundle


OUTPUT_DIR = Path("artifacts") / "template"


def build_all(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> dict[str, OutputBundle]:
    """Render all template preset examples into one artifact directory."""

    return {
        "journal_article_template": journal_article_template.build(
            output_dir,
            output_formats=output_formats,
            verbose=verbose,
        ),
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Build all template examples from the command line."""

    parser = argparse.ArgumentParser(
        description="Render all OODocs template preset examples.",
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

    bundles = build_all(
        args.output_dir,
        output_formats=args.output_formats,
        verbose=not args.quiet,
    )
    if not args.quiet:
        for name, outputs in bundles.items():
            for output_format, path in outputs:
                print(f"Wrote {name} {output_format}: {path}")


if __name__ == "__main__":
    main()
