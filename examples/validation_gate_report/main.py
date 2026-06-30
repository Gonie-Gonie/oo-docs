"""Build a validation gate report from ``Document.validate()`` output."""

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
from oodocs.validation import ValidationPolicy, ValidationResult


OUTPUT_DIR = Path("artifacts") / "validation-gate-report"
OUTPUT_STEM = "validation-gate-report"
VALIDATION_JSON = "validation-result.json"
ALLOWED_WARNINGS = ("html-toc-page-numbers", "wide-table")
VALIDATION_POLICY = ValidationPolicy(
    allow_warnings=frozenset(ALLOWED_WARNINGS),
    fail_on_unlisted_warnings=True,
)


class ValidationGateBundle:
    """Rendered validation gate report outputs plus validation JSON sidecar."""

    def __init__(self, rendered: OutputBundle, validation_json: Path) -> None:
        self.rendered = rendered
        self.validation_json = validation_json

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


def build_candidate_document() -> Document:
    """Build a document with intentional validation warnings."""

    wide_table = Table(
        ["Case", "Owner", "Expected", "Actual"],
        [
            ["layout-001", "release", "fixed-page renderers keep the policy excerpt visible", "pass"],
            ["layout-002", "release", "wide evidence moves to sidecar in production", "review"],
        ],
        caption="Intentionally wide table used to demonstrate the validation gate.",
        column_widths=[2.5, 2.5, 5.0, 5.0],
        unit="in",
    )
    return Document(
        "Validation Candidate",
        TableOfContents(show_page_numbers=True),
        Chapter(
            "Evidence",
            Paragraph("The candidate document intentionally creates validation warnings."),
            wide_table,
        ),
    )


def evaluate_gate(
    result: ValidationResult,
    *,
    policy: ValidationPolicy = VALIDATION_POLICY,
) -> tuple[bool, tuple[str, ...]]:
    """Return whether validation issues pass the configured release gate."""

    denied = tuple(issue.code for issue in result.blocking_warnings(policy))
    return not result.errors and not denied, denied


def build_document(
    validation_result: ValidationResult | None = None,
    *,
    policy: ValidationPolicy = VALIDATION_POLICY,
) -> Document:
    """Build the validation gate report document."""

    result = validation_result or build_candidate_document().validate()
    passed, denied = evaluate_gate(result, policy=policy)
    policy_table = Table(
        ["Policy item", "Decision"],
        [
            ["Allowed warnings", ", ".join(sorted(policy.allow_warnings))],
            ["Denied warnings", ", ".join(sorted(policy.deny_warnings)) or "(none)"],
            ["Fail on unlisted warnings", str(policy.fail_on_unlisted_warnings)],
            ["Denied warning codes", ", ".join(denied) if denied else "(none)"],
            ["Blocking errors", str(len(result.errors))],
            ["Gate decision", "pass" if passed else "fail"],
        ],
        caption="Validation gate policy used by this example.",
    )
    stale_artifact_table = Table(
        ["Step", "Release-safe behavior"],
        [
            ["1", "Write rendered outputs and validation JSON into a temporary directory."],
            ["2", "Inspect ValidationResult errors and denied warnings."],
            ["3", "Move the temporary directory into place only when the gate passes."],
        ],
        caption="Temporary write pattern for avoiding stale release artifacts.",
    )
    return Document(
        "Validation Gate Report",
        TableOfContents(max_level=2),
        Chapter(
            "Validation Policy",
            Paragraph(
                "This example treats ",
                inline_code("Document.validate()"),
                " as a release gate. The candidate document is validated before artifacts are promoted.",
            ),
            policy_table,
        ),
        Chapter(
            "Validation Result Table",
            result.to_table(caption="Validation result issues captured from the candidate document."),
        ),
        Chapter(
            "Release Gate Pattern",
            Section(
                "JSON sidecar",
                Paragraph(
                    "The same ",
                    inline_code("ValidationResult"),
                    " is written to ",
                    inline_code(VALIDATION_JSON),
                    " for CI and release evidence.",
                ),
            ),
            stale_artifact_table,
        ),
        settings=DocumentSettings(
            metadata=DocumentMetadata(
                author="OODocs Contributors",
                description="Validation gate report with JSON diagnostics sidecar",
            ),
            title_matter=TitleMatter(subtitle="Document.validate() as a release gate"),
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> ValidationGateBundle:
    """Render the validation gate report and write validation JSON."""

    output_path = Path(output_dir)
    candidate = build_candidate_document()
    validation_result = candidate.validate()
    validation_json = validation_result.save_json(
        output_path / VALIDATION_JSON,
        policy=VALIDATION_POLICY,
    )
    report = build_document(validation_result, policy=VALIDATION_POLICY)
    report.validate(raise_on_error=True)
    rendered = report.save_all(
        output_path,
        stem=OUTPUT_STEM,
        formats=tuple(output_formats or ("docx", "pdf", "html")),
        verbose=verbose,
    )
    return ValidationGateBundle(rendered, validation_json)


def main(argv: Sequence[str] | None = None) -> None:
    """Render the example from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs validation gate report example.",
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
        print(f"Wrote validation: {outputs.validation_json}")


if __name__ == "__main__":
    main()
