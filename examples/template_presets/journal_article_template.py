"""Standalone content-first JournalArticleTemplate example."""

from __future__ import annotations

from pathlib import Path

from oodocs import (
    Affiliation,
    Author,
    CitationLibrary,
    CitationSource,
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
                department="Building Simulation LAB",
                organization="Seoul National University",
                city="Seoul",
                country="Republic of Korea",
            )
        ],
        email="goniegonie@example.com",
        corresponding=True,
    ),
    Author(
        "OODocs Contributors",
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
    verbose: bool = False,
) -> OutputBundle:
    """Render the example into the template artifact directory."""

    return build_document().save_all(
        output_dir,
        stem="journal-article-template",
        verbose=verbose,
    )


def main() -> None:
    """Build the example from the command line."""

    for path in build(verbose=True).values():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
