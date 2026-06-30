"""Build a conformance matrix report with a full-matrix sidecar."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Sequence

from oodocs import (
    Chapter,
    Document,
    DocumentMetadata,
    DocumentSettings,
    NumberedList,
    OutputBundle,
    Paragraph,
    Section,
    Table,
    TableOfContents,
    TitleMatter,
    inline_code,
)


EXAMPLE_DIR = Path(__file__).resolve().parent
DATA_PATH = EXAMPLE_DIR / "data" / "conformance-results.csv"
OUTPUT_DIR = Path("artifacts") / "conformance-matrix-report"
OUTPUT_STEM = "conformance-matrix-report"
FULL_MATRIX_JSON = "conformance-matrix-full.json"


class ConformanceMatrixBundle:
    """Rendered conformance report outputs plus full-matrix JSON sidecar."""

    def __init__(self, rendered: OutputBundle, full_matrix_json: Path) -> None:
        self.rendered = rendered
        self.full_matrix_json = full_matrix_json

    def __iter__(self):
        """Iterate over rendered document outputs."""

        return iter(self.rendered)

    def __getitem__(self, output_format: str) -> Path:
        """Return the rendered path for an output format."""

        return self.rendered[output_format]

    def keys(self):
        """Return rendered output format keys."""

        return self.rendered.keys()

    def values(self):
        """Return rendered output paths."""

        return self.rendered.values()

    def items(self):
        """Return rendered output pairs."""

        return self.rendered.items()


def load_results(path: str | Path = DATA_PATH) -> list[dict[str, str]]:
    """Load conformance result records from CSV."""

    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_full_matrix(
    records: Sequence[dict[str, str]],
    output_dir: str | Path,
) -> Path:
    """Write the full conformance matrix as JSON sidecar."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sidecar = output_path / FULL_MATRIX_JSON
    payload = {
        "record_count": len(records),
        "columns": list(records[0]) if records else [],
        "records": list(records),
    }
    sidecar.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return sidecar


def status_counts(records: Sequence[dict[str, str]]) -> dict[str, int]:
    """Return count by conformance status."""

    counts: dict[str, int] = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    return counts


def build_document(records: Sequence[dict[str, str]] | None = None) -> Document:
    """Build the conformance matrix report document."""

    records = list(records or load_results())
    counts = status_counts(records)
    excerpt_records = [
        {
            "case": record["case"],
            "status": record["status"],
            "max_error": record["max_error"],
        }
        for record in records
    ]
    failed_or_review = [
        record for record in records if record["status"] in {"fail", "review"}
    ]
    summary_table = Table(
        ["Status", "Count"],
        [[status, str(count)] for status, count in sorted(counts.items())],
        caption="Conformance status summary.",
    )
    excerpt_table = Table.from_records(
        excerpt_records,
        columns=["case", "status", "max_error"],
        headers=["Case", "Status", "Max error"],
        caption="PDF excerpt matrix; full matrix is written to the JSON sidecar.",
    )
    failure_table = Table.from_records(
        failed_or_review,
        columns=["case", "status", "max_error", "notes"],
        headers=["Case", "Status", "Max error", "Notes"],
        caption="Failure and review detail appendix.",
        split=True,
    )
    sidecar_policy_table = Table(
        ["Artifact", "Purpose"],
        [
            [FULL_MATRIX_JSON, "Complete wide matrix for machine review and HTML-side inspection."],
            [f"{OUTPUT_STEM}.pdf", "Readable claim boundary, summary, excerpt, and failure appendix."],
        ],
        caption="Wide matrix reporting policy.",
    )

    return Document(
        "Conformance Matrix Report",
        TableOfContents(max_level=2),
        Chapter(
            "Claim Boundary",
            Paragraph(
                "This example reports conformance results without forcing every wide matrix column into the PDF body. The complete matrix remains available as ",
                inline_code(FULL_MATRIX_JSON),
                ".",
            ),
            NumberedList(
                "Use the document body for review decisions.",
                "Use the sidecar for complete evidence and automation.",
                "Keep failure details visible in an appendix.",
            ),
            sidecar_policy_table,
        ),
        Chapter(
            "Summary",
            summary_table,
            excerpt_table,
        ),
        Chapter(
            "Failure Detail Appendix",
            failure_table,
        ),
        settings=DocumentSettings(
            metadata=DocumentMetadata(
                author="OODocs Contributors",
                description="Conformance matrix report with wide evidence sidecar",
            ),
            title_matter=TitleMatter(subtitle="PDF excerpt plus full matrix sidecar"),
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> ConformanceMatrixBundle:
    """Render the conformance report and write full matrix JSON."""

    output_path = Path(output_dir)
    records = load_results()
    full_matrix_json = save_full_matrix(records, output_path)
    document = build_document(records)
    document.validate(raise_on_error=True)
    rendered = document.save_all(
        output_path,
        stem=OUTPUT_STEM,
        formats=tuple(output_formats or ("docx", "pdf", "html")),
        verbose=verbose,
    )
    return ConformanceMatrixBundle(rendered, full_matrix_json)


def main(argv: Sequence[str] | None = None) -> None:
    """Render the example from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs conformance matrix report example.",
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
        print(f"Wrote full matrix: {outputs.full_matrix_json}")


if __name__ == "__main__":
    main()
