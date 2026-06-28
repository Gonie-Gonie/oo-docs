from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import (
    BlockDefaults,
    Box,
    BoxStyle,
    CaptionDefaults,
    Chapter,
    Document,
    DocumentSettings,
    InlineChip,
    InlineChipStyle,
    OutputBundle,
    Padding,
    Paragraph,
    ParagraphStyle,
    StyleSheet,
    Table,
    TableStyle,
    Theme,
    TypographyDefaults,
)


OUTPUT_DIR = Path("artifacts/style-cleanup-smoke")
OUTPUT_STEM = "style-cleanup-smoke"


def create_stylesheet() -> StyleSheet:
    """Create the named styles used by the smoke document.

    Returns:
        Stylesheet containing paragraph, table, box, and chip styles.
    """

    styles = StyleSheet.default()
    styles.register(
        "paragraph",
        "body.compact",
        ParagraphStyle(text_alignment="left", space_after=6),
    )
    styles.register(
        "table",
        "schema",
        TableStyle(
            header_background_color="E7EEF7",
            alternate_row_background_color="F8FBFD",
            cell_padding=Padding.all(3),
            repeat_header_rows=True,
        ),
    )
    styles.register(
        "box",
        "scope",
        BoxStyle(background_color="F4F8FB", padding=Padding.all(8)),
    )
    styles.register(
        "chip",
        "req.required",
        InlineChipStyle(background_color="2563EB", text_color="FFFFFF"),
    )
    return styles


def build_document() -> Document:
    """Build the style cleanup smoke document.

    Returns:
        Renderable document using named styles through ``Theme.stylesheet``.
    """

    styles = create_stylesheet()
    return Document(
        "Style Cleanup Smoke Test",
        Chapter(
            "Named Styles",
            Paragraph("This paragraph uses a named style.", style="body.compact"),
            Paragraph("Requirement: ", InlineChip("R", chip_style="req.required")),
            Box("Scope text", title="Scope", style="scope"),
            Table(
                ["Field", "Value"],
                [["name", "example"], ["status", "pass"]],
                caption="Schema-style table.",
                style="schema",
            ),
        ),
        settings=DocumentSettings(
            theme=Theme(
                typography=TypographyDefaults(body_font_name="Segoe UI"),
                captions=CaptionDefaults(table_caption_position="above"),
                blocks=BlockDefaults(paragraph_text_alignment="left"),
                stylesheet=styles,
            )
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the smoke document.

    Args:
        output_dir: Directory where rendered files should be written.
        output_formats: Output formats to render. Defaults to DOCX, PDF, and
            HTML when omitted.
        verbose: Print slow render steps.

    Returns:
        Rendered output bundle keyed by normalized output format.
    """

    document = build_document()
    document.validate(raise_on_error=True)
    formats = tuple(output_formats or ("docx", "pdf", "html"))
    return document.save_all(
        output_dir,
        stem=OUTPUT_STEM,
        formats=formats,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Render the example from the command line.

    Args:
        argv: Optional argument sequence. When omitted, arguments are read from
            ``sys.argv``.
    """

    parser = argparse.ArgumentParser(
        description="Render the OODocs named style smoke example.",
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
