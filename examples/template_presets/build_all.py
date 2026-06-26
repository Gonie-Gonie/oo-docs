"""Build every template preset example."""

from __future__ import annotations

from pathlib import Path

import journal_article_template
from oodocs import OutputBundle


OUTPUT_DIR = Path("artifacts") / "template"


def build_all(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    verbose: bool = False,
) -> dict[str, OutputBundle]:
    """Render all template preset examples into one artifact directory."""

    return {
        "journal_article_template": journal_article_template.build(
            output_dir,
            verbose=verbose,
        ),
    }


def main() -> None:
    """Build all template examples from the command line."""

    for outputs in build_all(verbose=True).values():
        for path in outputs.values():
            print(f"Wrote {path}")


if __name__ == "__main__":
    main()
