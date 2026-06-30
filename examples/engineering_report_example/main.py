"""Build an engineering method report with numbered algorithms."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import (
    Chapter,
    Document,
    DocumentMetadata,
    DocumentSettings,
    OutputBundle,
    Paragraph,
    Section,
    Table,
    TableOfContents,
    TitleMatter,
    inline_code,
)
from oodocs.engineering import Algorithm


OUTPUT_DIR = Path("artifacts") / "engineering-report-example"
OUTPUT_STEM = "engineering-method-report"


def requirement_rows() -> list[list[str]]:
    """Return sample engineering requirements for the report."""

    return [
        ["R-01", "Sample-rate drift", "Correct time-base drift before feature extraction."],
        ["R-02", "Noise floor", "Reject windows whose baseline noise exceeds threshold."],
        ["R-03", "Traceability", "Preserve every threshold in editable report tables."],
    ]


def verification_rows() -> list[list[str]]:
    """Return sample verification rows for the report."""

    return [
        ["Drift correction", "pass", "Median residual drift stayed below 0.3%."],
        ["Noise rejection", "pass", "Rejected 4 of 128 windows before aggregation."],
        ["Report traceability", "pass", "Thresholds appear in the method summary table."],
    ]


def build_quality_algorithm() -> Algorithm:
    """Build the numbered quality-gate algorithm used by the report."""

    return Algorithm(
        "Signal quality gate",
        inputs=["timestamped samples", "calibration profile", "noise threshold"],
        outputs=["accepted windows", "rejection reasons", "method audit rows"],
        steps=[
            "Normalize timestamps to the calibration profile.",
            "Split the signal into fixed-duration windows.",
            "Estimate baseline noise for each window.",
            "Reject windows above the configured threshold.",
            "Write accepted-window statistics into the report tables.",
        ],
        caption="Signal quality gate.",
    )


def build_document() -> Document:
    """Build the engineering report example document."""

    quality_algorithm = build_quality_algorithm()
    return Document(
        "Engineering Report Example",
        TableOfContents(max_level=2),
        Chapter(
            "Signal Processing Method",
            Paragraph(
                "This report keeps engineering logic in a focused example. ",
                "The numbered method is represented by ",
                inline_code("oodocs.engineering.Algorithm"),
                ", while requirements and verification evidence remain editable tables.",
            ),
            Section(
                "Requirements",
                Table(
                    ["ID", "Topic", "Requirement"],
                    requirement_rows(),
                    caption="Engineering requirements used by the method.",
                    split=True,
                ),
            ),
            Section(
                "Quality Gate Algorithm",
                Paragraph("The method is summarized in ", quality_algorithm.ref(), "."),
                quality_algorithm,
            ),
            Section(
                "Verification Summary",
                Table(
                    ["Check", "Status", "Evidence"],
                    verification_rows(),
                    caption="Verification evidence produced by the method run.",
                    split=True,
                ),
            ),
        ),
        settings=DocumentSettings(
            metadata=DocumentMetadata(
                author="OODocs Contributors",
                description="Engineering method report with a numbered algorithm and verification evidence.",
            ),
            title_matter=TitleMatter(
                subtitle="numbered pseudocode, requirements, and verification tables",
            ),
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the engineering report example."""

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
        description="Render the OODocs engineering report example.",
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
