"""Standalone content-first JournalArticleTemplate example."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import (
    Affiliation,
    Author,
    CitationLibrary,
    CitationSource,
    CodeBlock,
    OutputBundle,
    Padding,
    Paragraph,
    Table,
    inline_code,
)
from oodocs.presets.templates import JournalArticleTemplate, ManuscriptSection


OUTPUT_DIR = Path("artifacts") / "template"
TITLE = "Content-First Journal Article Template"
SUBTITLE = "A ready manuscript draft from article metadata and body sections"
SUMMARY = "Content-first JournalArticleTemplate preset example"

AUTHORS = [
    Author(
        "Hyeong-Gon Jo",
        affiliations=[
            Affiliation(
                department="Example Laboratory",
                organization="Seoul National University",
                city="Seoul",
                country="Republic of Korea",
            )
        ],
        email="goniegonie@example.com",
        corresponding=True,
    ),
    Author(
        "Example Research Group",
        affiliations=["Open-source document tooling"],
    ),
]

CITATIONS = CitationLibrary(
    [
        CitationSource(
            "Literate Programming",
            key="literate-programming",
            authors=("Donald E. Knuth",),
            publisher="The Computer Journal",
            year="1984",
            url="https://doi.org/10.1093/comjnl/27.2.97",
        ),
        CitationSource(
            "Statistical Analyses and Reproducible Research",
            key="reproducible-research",
            authors=("Robert Gentleman", "Duncan Temple Lang"),
            publisher="Journal of Computational and Graphical Statistics",
            year="2007",
            url="https://doi.org/10.1198/106186007X178663",
        ),
        CitationSource(
            "knitr: A General-Purpose Package for Dynamic Report Generation in R",
            key="knitr",
            authors=("Yihui Xie",),
            publisher="Official project site",
            year="2026",
            url="https://yihui.org/knitr/",
        ),
    ]
)

ABSTRACT = (
    "This example demonstrates a journal article template that owns common manuscript "
    "formatting while the author supplies only title matter, abstract text, keywords, "
    "body sections, optional declarations, and citation data. The resulting document "
    "uses conventional article ordering without requiring the caller to assemble a "
    "table of contents, generated table lists, figure lists, page geometry, or title "
    "matter layout by hand."
)

KEYWORDS = [
    "journal article",
    "document automation",
    "reproducible authoring",
    "python",
]

ACKNOWLEDGEMENTS = (
    "The authors thank the oodocs maintainers and early readers for feedback on "
    "the manuscript preset API."
)

DATA_AVAILABILITY = (
    "All inputs needed to regenerate this example are contained in the template preset "
    "example scripts and the citation metadata defined alongside them."
)

INPUT_RESPONSIBILITY_TABLE = Table(
    headers=["Input", "Author responsibility", "Template responsibility"],
    rows=[
        [
            "Title matter",
            "Provide title, authors, abstract, and keywords.",
            "Render journal-style title matter and front content.",
        ],
        [
            "Body",
            "Write detailed manuscript sections with tables, figures, and citations.",
            "Preserve numbered section hierarchy and references.",
        ],
        [
            "Declarations",
            "Provide optional statements only when needed.",
            "Omit empty acknowledgement and data availability sections.",
        ],
        [
            "References",
            "Provide citation metadata or disable references explicitly.",
            "Render a generated references section by default.",
        ],
    ],
    caption="Content-first journal templates separate manuscript content from repeated document assembly.",
    header_background_color="#E7EEF7",
    alternate_row_background_color="#FAFCFE",
    cell_padding=Padding.all(4),
    repeat_header_rows=True,
)

TEMPLATE_CATALOG_TABLE = Table(
    headers=["Template", "Input object", "Output document", "When to use"],
    rows=[
        [
            "JournalArticleTemplate",
            "title, authors, abstract, sections",
            "manuscript draft",
            "Article-like reports with conventional title matter and declarations.",
        ],
        [
            "CoverPagePreset",
            "accented(...) or centered_logo(...)",
            "cover-page settings",
            "Generic caller-owned cover content and layout.",
        ],
        [
            "SoftwareManualTemplate",
            "title, overview, sections",
            "software manual",
            "User-facing procedures and command-oriented guides.",
        ],
        [
            "TechnicalReportTemplate",
            "title, executive_summary, sections, appendices",
            "technical report",
            "Validation reports, engineering memos, and audit evidence.",
        ],
        [
            "BookTemplate",
            "front_matter, parts, chapters, appendices, back_matter",
            "book or handbook",
            "Long-form documents with chapters, parts, and appendices.",
        ],
    ],
    caption="Template preset catalog for cover pages, articles, reports, manuals, and books.",
    header_background_color="#E8F2EC",
    alternate_row_background_color="#FAFCFA",
    cell_padding=Padding.all(4),
    repeat_header_rows=True,
)

INPUT_SCHEMA_TABLE = Table(
    headers=["Input", "Required", "Purpose"],
    rows=[
        ["title", "Yes", "Visible manuscript title and default artifact naming context."],
        ["subtitle", "No", "Optional secondary title line."],
        ["authors", "Yes", "Structured author and affiliation metadata."],
        ["abstract", "Yes", "Unnumbered front-matter abstract section."],
        ["keywords", "No", "Keyword line near the abstract."],
        ["sections", "Yes", "Ordered manuscript body sections."],
        ["acknowledgements", "No", "Optional declaration omitted when None."],
        ["data_availability", "No", "Optional declaration omitted when None."],
        ["citations", "No", "Citation library used by body content and references."],
        ["summary", "No", "Document metadata summary."],
    ],
    caption="JournalArticleTemplate.build(...) input schema.",
    header_background_color="#E7EEF7",
    alternate_row_background_color="#F8FBFD",
    cell_padding=Padding.all(4),
    repeat_header_rows=True,
)

DIRECT_ASSEMBLY_COMPARISON_TABLE = Table(
    headers=["Need", "template_presets", "journal_paper_example"],
    rows=[
        ["Fast article skeleton", "Best fit", "Manual setup required"],
        ["Full control over structure", "Partial", "Best fit"],
        ["Custom data and figure workflow", "Supported inside sections", "Best fit"],
        ["Optional declaration omission", "Built in", "Author-managed"],
    ],
    caption="Template-first authoring compared with direct manuscript assembly.",
    header_background_color="#F1E7D9",
    alternate_row_background_color="#FFFCF8",
    cell_padding=Padding.all(4),
    repeat_header_rows=True,
)

BODY_SECTIONS = [
    ManuscriptSection(
        "Introduction",
        [
            Paragraph(
                "Journal manuscripts are repetitive in structure even when their arguments are unique. A useful template should therefore ask for manuscript facts, not for renderer details: title, authors, abstract, keywords, body sections, optional declarations, and references."
            ),
            Paragraph(
                "The preset follows the traceability motivation behind literate programming ",
                CITATIONS.cite("literate-programming"),
                " and reproducible research ",
                CITATIONS.cite("reproducible-research"),
                ": the visible manuscript should remain downstream of structured inputs rather than hand-assembled formatting steps.",
            ),
            TEMPLATE_CATALOG_TABLE,
        ],
    ),
    ManuscriptSection(
        "Methods",
        [
            Paragraph(
                "The example builds the article with ",
                inline_code("JournalArticleTemplate.build(...)"),
                ". The caller supplies the content surface directly and lets the template decide ordinary journal defaults such as title matter placement, page numbering, caption alignment, declaration ordering, and reference placement.",
            ),
            INPUT_SCHEMA_TABLE,
            INPUT_RESPONSIBILITY_TABLE,
        ],
    ),
    ManuscriptSection(
        "Results",
        [
            Paragraph(
                "The body remains explicit because manuscript arguments are domain-specific. Authors can pass ",
                inline_code("ManuscriptSection"),
                " descriptors, existing ",
                inline_code("Section"),
                " blocks, or compact ",
                inline_code("(title, children)"),
                " tuples, while the preset handles generated article structure around those blocks.",
            ),
            Paragraph(
                "Optional acknowledgement and data availability statements behave like normal manuscript declarations: pass content to include the section, or pass ",
                inline_code("None"),
                " to omit it without leaving an empty heading.",
            ),
            CodeBlock(
                """minimal_doc = JournalArticleTemplate().build(
    "Minimal Article",
    authors=[author],
    abstract="...",
    sections=[ManuscriptSection("Body", [Paragraph("...")])],
    acknowledgements=None,
    data_availability=None,
)""",
                language="python",
            ),
            DIRECT_ASSEMBLY_COMPARISON_TABLE,
        ],
    ),
    ManuscriptSection(
        "Discussion",
        [
            Paragraph(
                "The template is intentionally generic rather than publisher-specific. It gives authors a complete article-shaped starting point, while still allowing project-specific overrides when a target journal has stricter instructions."
            ),
            Paragraph(
                "This is similar in spirit to tools such as ",
                CITATIONS.cite("knitr"),
                ": the authoring environment should make repeatable structure cheap without hiding the scientific content that needs review.",
            ),
        ],
    ),
    ManuscriptSection(
        "Conclusion",
        [
            Paragraph(
                "A content-first template lets authors fill in the manuscript fields that matter and receive a ready-to-render article draft without assembling theme, contents pages, generated lists, or declaration boilerplate by hand."
            ),
        ],
    ),
]


def build_minimal_document():
    """Build a minimal article that omits optional declaration sections."""

    return JournalArticleTemplate().build(
        "Minimal Article",
        authors=[AUTHORS[0]],
        abstract="A minimal article can omit optional declaration sections.",
        sections=[
            ManuscriptSection(
                "Body",
                [
                    Paragraph(
                        "This body section is present, while acknowledgements and data availability are omitted."
                    )
                ],
            )
        ],
        acknowledgements=None,
        data_availability=None,
        citations=None,
    )


def build_document():
    """Build a journal manuscript from content-oriented inputs."""

    return JournalArticleTemplate().build(
        TITLE,
        subtitle=SUBTITLE,
        authors=AUTHORS,
        abstract=ABSTRACT,
        keywords=KEYWORDS,
        sections=BODY_SECTIONS,
        acknowledgements=ACKNOWLEDGEMENTS,
        data_availability=DATA_AVAILABILITY,
        citations=CITATIONS,
        summary=SUMMARY,
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the example into the template artifact directory."""

    formats = tuple(output_formats or ("docx", "pdf", "html"))
    return build_document().save_all(
        output_dir,
        stem="journal-article-template",
        formats=formats,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Build the example from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs journal article template preset example.",
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
