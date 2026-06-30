"""Build a review-notes workflow document."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import (
    Chapter,
    Comment,
    Document,
    DocumentMetadata,
    DocumentSettings,
    Footnote,
    NumberedList,
    OutputBundle,
    Paragraph,
    Section,
    Table,
    TitleMatter,
    comment,
    footnote,
    inline_code,
)
from oodocs.generated import ListOfComments, ListOfFootnotes, TableOfContents
from oodocs.review import MarginNote, Todo, margin_note, todo


OUTPUT_DIR = Path("artifacts") / "review-notes-example"
OUTPUT_STEM = "review-notes"


def review_queue_rows() -> list[list[str]]:
    """Return sample review queue rows used in the example document."""

    return [
        ["copy", "open", "Confirm release date and product wording."],
        ["data", "review", "Re-run benchmark table before final PDF export."],
        ["legal", "blocked", "Verify redistribution note before publication."],
    ]


def build_review_section() -> Section:
    """Build the section that demonstrates review annotations."""

    return Section(
        "Inline Review Notes",
        Paragraph(
            "Core comments stay attached to source prose: ",
            comment(
                "release date",
                "Confirm the final release date before sending the review copy.",
                author="QA",
                initials="QA",
            ),
            ".",
        ),
        Paragraph(
            "Class-based comments work when the caller wants an explicit object: ",
            Comment.annotated(
                "approval threshold",
                "Check this threshold against the launch checklist.",
                author="Data",
                initials="DS",
            ),
            ".",
        ),
        Paragraph(
            "Review-only helpers are imported from ",
            inline_code("oodocs.review"),
            ": ",
            todo("Verify benchmark fixture names.", owner="QA", status="open"),
            " and ",
            margin_note(
                "Keep this side note next to the source claim while reviewing.",
                side="right",
            ),
            ".",
        ),
        Paragraph(
            "The class forms support explicit visible anchors: ",
            Todo(
                "Capture a named owner before release.",
                owner="PM",
                status="blocked",
                value="owner needed",
            ),
            " ",
            MarginNote(
                "Move this note with the risk paragraph.",
                side="left",
                value="risk note",
            ),
            ".",
        ),
    )


def build_source_notes_section() -> Section:
    """Build the section that demonstrates core footnotes."""

    return Section(
        "Source Notes",
        Paragraph(
            "Footnotes stay in the core inline API for source explanation: ",
            footnote(
                "SLA",
                "Service-level agreement used for the review scenario.",
            ),
            ".",
        ),
        Paragraph(
            "The class constructor is useful when factories are not convenient: ",
            Footnote.annotated(
                "fallback behavior",
                "DOCX can use native page footnotes for the default stream; PDF and HTML keep portable generated notes.",
            ),
            ".",
        ),
        Table(
            ["Reviewer", "Status", "Next action"],
            review_queue_rows(),
            caption="Review queue represented as editable document data.",
            split=True,
        ),
    )


def build_document() -> Document:
    """Build the review notes example document."""

    return Document(
        "Review Notes Example",
        TableOfContents(max_level=2),
        Chapter(
            "Review Workflow",
            Paragraph(
                "This example keeps editorial notes, TODOs, side notes, and source footnotes in normal document objects so DOCX review copies and HTML/PDF previews come from the same source."
            ),
            NumberedList(
                "Write source prose with core comments and footnotes.",
                "Use oodocs.review for TODOs and margin notes.",
                "Place generated list pages at the end when reviewers need a consolidated queue.",
            ),
            build_review_section(),
            build_source_notes_section(),
        ),
        Chapter(
            "Generated Review Pages",
            Paragraph(
                "Generated pages summarize inline annotations without moving the authored notes away from the paragraphs they review."
            ),
            ListOfComments("Collected Review Notes"),
            ListOfFootnotes("Collected Footnotes"),
        ),
        settings=DocumentSettings(
            metadata=DocumentMetadata(
                author="OODocs Contributors",
                description="Review notes workflow with comments, TODOs, margin notes, and footnotes.",
            ),
            title_matter=TitleMatter(
                subtitle="comments, TODOs, margin notes, and generated review pages",
            ),
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the review notes example."""

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
        description="Render the OODocs review notes example.",
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
