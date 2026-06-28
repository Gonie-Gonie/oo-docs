"""Common entry point for template preset examples."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence

from oodocs import Document, OutputBundle

EXAMPLE_DIR = Path(__file__).resolve().parent
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))

import build_all as _build_all
import journal_article_template


OUTPUT_DIR = _build_all.OUTPUT_DIR


def build_document() -> Document:
    """Return the primary template preset example document."""

    return journal_article_template.build_document()


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> dict[str, OutputBundle]:
    """Render all template preset examples through the common interface."""

    return _build_all.build_all(
        output_dir,
        output_formats=output_formats,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Render all template preset examples from the command line."""

    _build_all.main(argv)


if __name__ == "__main__":
    main()
