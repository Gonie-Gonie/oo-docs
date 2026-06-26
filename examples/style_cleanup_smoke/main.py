from __future__ import annotations

from pathlib import Path

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
    verbose: bool = False,
) -> dict[str, Path]:
    """Render the smoke document to DOCX, PDF, and HTML.

    Args:
        output_dir: Directory where rendered files should be written.
        verbose: Print slow render steps.

    Returns:
        Mapping from output format to rendered file path.
    """

    document = build_document()
    document.validate(raise_on_error=True)
    return document.save_all(
        output_dir,
        stem=OUTPUT_STEM,
        formats=("docx", "pdf", "html"),
        verbose=verbose,
    )


if __name__ == "__main__":
    for path in build(verbose=True).values():
        print(path)
