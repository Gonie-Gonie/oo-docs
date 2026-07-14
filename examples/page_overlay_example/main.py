"""Build a page overlay and positioned drawing example."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import (
    Chapter,
    CoverPage,
    Document,
    DocumentMetadata,
    DocumentSettings,
    OutputBundle,
    PageLayout,
    PageSize,
    Paragraph,
    Section,
    Table,
    TableOfContents,
    Theme,
    TitleMatter,
    inline_code,
)
from oodocs.positioning import ImageBox, PageItemScope, Shape, TextBox
from oodocs.styles import PageNumberDefaults, StrokeStyle


OUTPUT_DIR = Path("artifacts") / "page-overlay-example"
OUTPUT_STEM = "page-overlay"

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def overlay_summary_rows() -> list[list[str]]:
    """Return the overlay rules demonstrated by the example."""

    return [
        ["Named frame", "Shape.rect(name='approval-frame')", "Creates an anchor for child boxes."],
        ["Cover badge", "PageItemScope.cover()", "Shows cover-only decoration."],
        ["Main watermark", "PageItemScope.main()", "Keeps document body pages marked."],
        ["Page range", "PageItemScope.pages(2)", "Targets a physical page number."],
    ]


def build_overlays() -> list[object]:
    """Build page-positioned overlay items for the example document."""

    return [
        Shape.rect(
            name="approval-frame",
            x=0.45,
            y=0.45,
            width=7.4,
            height=9.8,
            stroke=StrokeStyle.solid("334155", width=1.2),
            fill_color="F8FAFC",
            z_index=0,
        ),
        TextBox(
            "APPROVAL AREA",
            anchor="approval-frame",
            x=0.35,
            y=0.3,
            width=2.4,
            height=0.35,
            font_size=10,
            text_alignment="center",
            vertical_alignment="middle",
            z_index=2,
        ),
        ImageBox(
            _TINY_PNG,
            anchor="approval-frame",
            x=6.45,
            y=0.28,
            width=0.32,
            height=0.32,
            z_index=2,
            scope=PageItemScope.cover(),
        ),
        TextBox(
            "COVER BADGE",
            x=5.35,
            y=0.55,
            width=1.6,
            height=0.3,
            font_size=8,
            scope=PageItemScope.cover(),
        ),
        TextBox(
            "MAIN WATERMARK",
            x=5.0,
            y=10.25,
            width=2.3,
            height=0.3,
            font_size=8,
            text_alignment="right",
            scope=PageItemScope.main(),
        ),
        TextBox(
            "PAGE 2 CHECK",
            x=0.65,
            y=10.25,
            width=2.2,
            height=0.3,
            font_size=8,
            scope=PageItemScope.pages(2),
        ),
    ]


def build_document() -> Document:
    """Build the page overlay example document."""

    inline_logo = ImageBox(_TINY_PNG, width=0.2, height=0.2, placement="inline")
    return Document(
        "Page Overlay Example",
        TableOfContents(max_level=2),
        Chapter(
            "Overlay Workflow",
            Paragraph(
                "This example keeps page-positioned decoration in ",
                inline_code("DocumentSettings(overlays=...)"),
                " so body content remains a normal document tree.",
            ),
            Section(
                "Overlay Rules",
                Table(
                    ["Rule", "API", "Purpose"],
                    overlay_summary_rows(),
                    caption="Page overlay rules represented as data.",
                    split=True,
                ),
            ),
            Section(
                "Inline Placement",
                Paragraph(
                    "Positioning objects can also move with prose when ",
                    inline_code("placement='inline'"),
                    " is used: ",
                    inline_logo,
                    " inline marker.",
                ),
            ),
            Section(
                "Body Flow",
                Paragraph(
                    "The overlay frame, badges, and watermarks are drawn outside this body flow. "
                    "The paragraphs and tables keep their normal layout in DOCX, PDF, and HTML."
                ),
            ),
        ),
        settings=DocumentSettings(
            page_layout=PageLayout(PageSize.letter()),
            title_matter=TitleMatter(
                cover=CoverPage(eyebrow="POSITIONED CONTENT EXAMPLE"),
                subtitle="page-positioned overlays and inline drawing placement",
            ),
            overlays=build_overlays(),
            metadata=DocumentMetadata(
                author="Example Documentation Team",
                description="Page overlay example with scoped positioned items.",
            ),
            theme=Theme(page_numbers=PageNumberDefaults(show_page_numbers=True)),
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the page overlay example."""

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
        description="Render the OODocs page overlay example.",
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
