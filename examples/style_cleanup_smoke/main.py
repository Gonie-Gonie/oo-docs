from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from oodocs import (
    BlockDefaults,
    Box,
    BoxStyle,
    CaptionDefaults,
    Chapter,
    CodeBlock,
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
STYLESHEET_JSON = "style-cleanup-smoke-stylesheet.json"


class StyleExampleBundle:
    """Rendered custom-style example outputs plus stylesheet sidecar."""

    def __init__(self, rendered: OutputBundle, stylesheet_json: Path) -> None:
        self.rendered = rendered
        self.stylesheet_json = stylesheet_json

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


def create_stylesheet() -> StyleSheet:
    """Create the named styles used by the custom styles document.

    Returns:
        Stylesheet containing paragraph, table, box, and chip styles.
    """

    styles = StyleSheet.default()
    styles.register_paragraph(
        "body.compact",
        ParagraphStyle(text_alignment="left", space_after=6),
    )
    styles.register_table(
        "schema",
        TableStyle(
            header_background_color="E7EEF7",
            alternate_row_background_color="F8FBFD",
            cell_padding=Padding.all(3),
            repeat_header_rows=True,
        ),
    )
    styles.register_box(
        "scope",
        BoxStyle(background_color="F4F8FB", padding=Padding.all(8)),
    )
    styles.register_chip(
        "req.required",
        InlineChipStyle(background_color="2563EB", text_color="FFFFFF"),
    )
    return styles


def write_stylesheet_sidecar(
    output_dir: str | Path,
    stylesheet: StyleSheet,
) -> Path:
    """Write the stylesheet as a reusable JSON sidecar."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sidecar_path = output_path / STYLESHEET_JSON
    sidecar_path.write_text(
        json.dumps(stylesheet.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return sidecar_path


def load_stylesheet_sidecar(path: str | Path) -> StyleSheet:
    """Load a stylesheet sidecar written by this example."""

    return StyleSheet.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def category_mismatch_validation_codes(
    stylesheet: StyleSheet | None = None,
) -> tuple[str, ...]:
    """Return validation codes for a named-style category mismatch probe.

    Args:
        stylesheet: Stylesheet used to resolve the probe document. Defaults to
            the stylesheet created by this example.

    Returns:
        Validation issue codes produced when a box style is used as a table
        style.
    """

    styles = stylesheet or create_stylesheet()
    probe = Document(
        "Named Style Category Probe",
        Table(["Field"], [["status"]], style="warning"),
        settings=DocumentSettings(theme=Theme(stylesheet=styles)),
    )
    return tuple(issue.code for issue in probe.validate().issues)


def build_document(stylesheet: StyleSheet | None = None) -> Document:
    """Build the custom styles example document.

    Returns:
        Renderable document using named styles through ``Theme.stylesheet``.
    """

    styles = stylesheet or create_stylesheet()
    comparison_table = Table(
        ["Concern", "Without named style", "With StyleSheet"],
        [
            ["Paragraph rhythm", "Repeated spacing kwargs", "style='body.compact'"],
            ["Schema tables", "Repeated table colors and padding", "style='schema'"],
            ["Scope callouts", "Repeated BoxStyle values", "style='scope'"],
            ["Requirement chips", "Repeated chip colors", "chip_style='req.required'"],
        ],
        caption="Named styles replace repeated visual kwargs with reusable style identifiers.",
        style="schema",
    )
    validation_table = Table(
        ["Probe", "Expected validation code", "Reason"],
        [
            [
                "Table(..., style='warning')",
                "wrong-style-category",
                "'warning' is registered as a box style, not a table style.",
            ]
        ],
        caption="Named style validation catches category mismatches before rendering.",
        style="schema",
    )
    return Document(
        "Custom Styles Example",
        Chapter(
            "Named Styles",
            Paragraph("This paragraph uses a named style.", style="body.compact"),
            Paragraph("Requirement: ", InlineChip("R", chip_style="req.required")),
            Box("Scope text", title="Scope", style="scope"),
            comparison_table,
            Table(
                ["Field", "Value"],
                [["name", "example"], ["status", "pass"]],
                caption="Schema-style table.",
                style="schema",
            ),
            Paragraph(
                "Use named styles from the category that matches the component. "
                "A table style name is resolved from the table registry, while "
                "a box style name is resolved from the box registry."
            ),
            CodeBlock("Table(['A'], [['B']], style='warning')", language="python"),
            validation_table,
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
) -> StyleExampleBundle:
    """Render the custom styles document.

    Args:
        output_dir: Directory where rendered files should be written.
        output_formats: Output formats to render. Defaults to DOCX, PDF, and
            HTML when omitted.
        verbose: Print slow render steps.

    Returns:
        Rendered output bundle plus the stylesheet JSON sidecar.
    """

    stylesheet = create_stylesheet()
    stylesheet_json = write_stylesheet_sidecar(output_dir, stylesheet)
    document = build_document(load_stylesheet_sidecar(stylesheet_json))
    document.validate(raise_on_error=True)
    formats = tuple(output_formats or ("docx", "pdf", "html"))
    rendered = document.save_all(
        output_dir,
        stem=OUTPUT_STEM,
        formats=formats,
        verbose=verbose,
    )
    return StyleExampleBundle(rendered, stylesheet_json)


def main(argv: Sequence[str] | None = None) -> None:
    """Render the example from the command line.

    Args:
        argv: Optional argument sequence. When omitted, arguments are read from
            ``sys.argv``.
    """

    parser = argparse.ArgumentParser(
        description="Render the OODocs custom styles example.",
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
        print(f"Wrote stylesheet: {outputs.stylesheet_json}")


if __name__ == "__main__":
    main()
