"""Standalone usage guide example for oodocs.

The guide is written as a part- and chapter-based reference document. Each chapter
focuses on a specific authoring concern so a reader can jump directly to the page
that matches the question they have in mind without the document feeling like a FAQ
sheet.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import (
    Assumption,
    Author,
    AuthorLayout,
    BlockDefaults,
    BorderStyle,
    Box,
    BulletList,
    CaptionDefaults,
    Chapter,
    CitationLibrary,
    CitationSource,
    Comment,
    CommentList,
    CodeBlock,
    Definition,
    Divider,
    Document,
    DocumentSettings,
    Example,
    Figure,
    ListOfFigures,
    Footnote,
    GeneratedContentDefaults,
    ImageBox,
    Lemma,
    NumberedList,
    OutputBundle,
    PageNumberDefaults,
    PageLayout,
    PageMargins,
    PageSize,
    Padding,
    Paragraph,
    Part,
    Proof,
    ReferenceList,
    Remark,
    Section,
    Shape,
    StrokeStyle,
    SubFigure,
    SubFigureGroup,
    Subsection,
    SubSubsection,
    Table,
    ListOfTables,
    TableOfContents,
    Text,
    TextBox,
    Theme,
    Theorem,
    TitleMatterDefaults,
    TocLevelStyle,
    TypographyDefaults,
    VerticalSpace,
    badge,
    bold,
    inline_code,
    text_color,
    create_countable_block_type,
    highlight,
    link,
    line_break,
    keyboard,
    prescript,
    status,
    strikethrough,
    subscript,
    superscript,
    tag,
)
from oodocs.presets.components import CalloutBox, KeyValueTable, Nomenclature
from oodocs.presets.templates import JournalArticleTemplate, ManuscriptSection


OUTPUT_DIR = Path("artifacts") / "usage-guide"
EXAMPLE_DIR = Path(__file__).resolve().parent
ASSET_DIR = EXAMPLE_DIR / "assets"
LOGO_PATH = ASSET_DIR / "oodocs-logo.png"
PIPELINE_DIAGRAM_PATH = ASSET_DIR / "pipeline-diagram.png"
AUTHOR_LAYOUT_DIAGRAM_PATH = ASSET_DIR / "author-layout-diagram.png"
RENDERER_BEHAVIOR_DIAGRAM_PATH = ASSET_DIR / "renderer-behavior-diagram.png"
CLI_WORKFLOW_DIAGRAM_PATH = ASSET_DIR / "cli-workflow-diagram.png"

RELATED_WORK = CitationLibrary(
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
            "OODocs repository",
            key="repository",
            organization="Gonie-Gonie",
            publisher="GitHub repository",
            year="2026",
            url="https://github.com/Gonie-Gonie/oo-docs",
        ),
        CitationSource(
            "Elsevier Your Paper Your Way Guide for Authors",
            key="elsevier-your-paper-your-way",
            organization="Elsevier",
            publisher="Guide for authors",
            year="2026",
            url="https://www.elsevier.com/en-gb/subject/next/guide-for-authors",
        ),
        CitationSource(
            "Taylor & Francis manuscript layout guide",
            key="taylor-francis-layout-guide",
            organization="Taylor & Francis Author Services",
            publisher="Author Services",
            year="2026",
            url="https://authorservices.taylorandfrancis.com/publishing-your-research/writing-your-paper/journal-manuscript-layout-guide/",
        ),
        CitationSource(
            "Taylor & Francis instructions for authors overview",
            key="taylor-francis-instructions",
            organization="Taylor & Francis Author Services",
            publisher="Author Services",
            year="2026",
            url="https://authorservices.taylorandfrancis.com/publishing-your-research/making-your-submission/get-familiar-with-the-instructions-for-authors/",
        ),
    ]
)

QUICK_START_SNIPPET = """from oodocs import Chapter, Document, DocumentSettings, Paragraph, Section, bold

report = Document(
    "Hello oodocs",
    Chapter(
        "Getting Started",
        Section(
            "Overview",
            Paragraph("This document was defined with ", bold("Python objects"), "."),
        ),
    ),
    settings=DocumentSettings(metadata_author="OODocs"),
)

report.save("artifacts/hello.docx")
report.save("artifacts/hello.pdf")
report.save("artifacts/hello.html")

# Or create the normal DOCX/PDF/HTML bundle in one call:
report.save_all("artifacts", stem="hello")
"""

PART_STRUCTURE_SNIPPET = """from oodocs import Chapter, Document, Paragraph, Part, Section

handbook = Document(
    "Implementation Handbook",
    Part(
        "Foundations",
        Chapter("Getting Started", Section("Overview", Paragraph("Chapter 1."))),
    ),
    Part(
        "Reference",
        Chapter("Configuration", Section("Options", Paragraph("Chapter 2, not 1."))),
    ),
)
"""

AUTHOR_LAYOUT_SNIPPET = """from oodocs import Affiliation, Author, AuthorLayout, DocumentSettings

settings = DocumentSettings(
    authors=[
        Author(
            "Research Lead",
            affiliations=[Affiliation(organization="Example Lab")],
            corresponding=True,
            email="lead@example.org",
        ),
        Author(
            "Implementation Partner",
            affiliations=[Affiliation(organization="Open Source Team")],
            note="GitHub: @example",
        ),
    ],
    author_layout=AuthorLayout(mode="stacked"),
)
"""

LAYOUT_CONTROL_SNIPPET = """from oodocs import BlockDefaults, CaptionDefaults, DocumentSettings, GeneratedContentDefaults, PageLayout, PageMargins, PageSize, Theme

settings = DocumentSettings(
    unit="cm",
    page_layout=PageLayout(
        page_size=PageSize.a4(),
        page_margins=PageMargins.symmetric(vertical=2.0, horizontal=2.4, unit="cm"),
    ),
    theme=Theme(
        blocks=BlockDefaults(footnote_placement="document"),
        generated_content=GeneratedContentDefaults(generated_content_page_breaks=True),
        captions=CaptionDefaults(
            table_caption_position="above",
            figure_caption_position="below",
            table_reference_label="Tbl.",
            figure_reference_label="Fig.",
        ),
    ),
)
"""

APPENDIX_STRUCTURE_SNIPPET = """from oodocs import Appendix, Chapter, Document, Paragraph, Section

schema = Chapter(
    "Input Data Schema",
    Section("Fields", Paragraph("Field definitions.")),
)

report = Document(
    "Validation Report",
    Chapter("Results", Paragraph("Main body.")),
    Appendix(
        schema,
        Chapter("Validation Cases", Paragraph("Reference checks.")),
    ),
)

# The appendix chapters render as A, B; nested headings render as A.1, A.2, ...
"""

FIGURE_SIZING_SNIPPET = """from oodocs import DocumentSettings, Figure, PageMargins

settings = DocumentSettings(unit="cm", page_margins=PageMargins.all(2.0, unit="cm"))

figure = Figure(
    "assets/system-diagram.png",
    width=settings.get_text_width(0.75),
    height=8.0,
)
"""

SUBFIGURE_SNIPPET = """from oodocs import Paragraph, SubFigure, SubFigureGroup

before = SubFigure("assets/before.png", caption="Before calibration.", width=6.0, unit="cm")
after = SubFigure("assets/after.png", caption="After calibration.", width=6.0, unit="cm")

comparison = SubFigureGroup(
    before,
    after,
    caption="Calibration comparison.",
    columns=2,
)

Paragraph("The post-calibration case is shown in ", after.reference(), ".")
"""

POSITIONED_DRAWING_SNIPPET = """from oodocs import Document, DocumentSettings, ImageBox, Paragraph, Shape, StrokeStyle, TextBox

frame = Shape.rect(
    name="approval-frame",
    anchor="margin",
    x=0,
    y=0,
    width=6.0,
    height=1.0,
    stroke=StrokeStyle.solid("#476172", width=1.0),
)

document = Document(
    "Drawing placement",
    Paragraph(
        "Inline logo ",
        ImageBox("assets/oodocs-logo.png", width=0.28, height=0.28, placement="inline"),
        " stays in the sentence flow.",
    ),
    settings=DocumentSettings(
        page_items=[
            frame,
            TextBox("Approval area", anchor="approval-frame", x=0.25, y=0.25, width=2.0, height=0.3),
        ],
    ),
)
"""

REPORT_PANEL_SNIPPET = """from oodocs import BorderStyle, Box, Padding, Paragraph, Table

panel = Box(
    Paragraph("Editable report content can stay grouped with its evidence."),
    Table(
        headers=["Surface", "Word behavior", "Portable behavior"],
        rows=[
            ["Box", "Editable panel", "tcolorbox-like grouping"],
            ["Table", "Editable cells", "Shared structured layout"],
        ],
    ),
    title="Report panel",
    background_color="#FDFBF6",
    title_background_color="#1058A3",
    title_text_color="#FFFFFF",
    border=BorderStyle.solid("#B8C6D6", width=0.75),
    padding=Padding.symmetric(vertical=8, horizontal=12),
    width=18.0,
    unit="cm",
    block_alignment="center",
)
"""

CONTENTS_CONTROL_SNIPPET = """from oodocs import TableOfContents, TocLevelStyle

contents = TableOfContents(
    scope="document",
    show_page_numbers=True,
    leader=".",
    max_level=3,
    level_styles={
        1: TocLevelStyle(bold=True, space_before=12, space_after=7),
        2: TocLevelStyle(bold=False, space_before=3, space_after=3),
        3: TocLevelStyle(indent=0.48, font_size_delta=-0.2),
    },
)
"""

CONFIGURATION_OPTIONS_SNIPPET = """from oodocs import (
    BorderStyle,
    BlockDefaults, CaptionDefaults, DocumentSettings, PageNumberDefaults,
    HeadingStyle, Padding, Paragraph, Table, TextStyle, Theme, TypographyDefaults,
)

settings = DocumentSettings(
    unit="cm",
    theme=Theme(
        typography=TypographyDefaults(body_font_name="Arial", body_font_size=10.5),
        captions=CaptionDefaults(figure_label="Fig."),
        page_numbers=PageNumberDefaults(show_page_numbers=True, page_number_template="p. {page}"),
        blocks=BlockDefaults(
            paragraph_text_alignment="left",
            heading_styles={
                1: HeadingStyle(text_style=TextStyle(font_size=18), space_after=8),
            },
        ),
    ),
)

paragraph = Paragraph("Right-aligned note.", text_alignment="right", space_after=6)
kept_paragraph = Paragraph(
    "Keep this paragraph with the following evidence table.",
    space_before=6,
    keep_with_next=True,
)
table = Table(
    headers=["Metric", "Value"],
    rows=[["Latency", "14 ms"]],
    header_background_color="#E8EDF5",
    cell_text_alignment="center",
    border=BorderStyle.solid("#CBD5E1", width=0.4),
    cell_padding=Padding.symmetric(vertical=3, horizontal=5),
    repeat_header_rows=True,
)
"""

COUNTABLE_BLOCK_SNIPPET = """from oodocs import Definition, Lemma, Paragraph, Proof, Theorem, create_countable_block_type

Exercise = create_countable_block_type("Exercise", counter="exercise")

bounded = Definition("A block with an explicit label and document-wide number.")
setup = Lemma("Shared theorem-like blocks advance the same counter.")
main = Theorem("The numbered statement can be referenced later.", title="Main result")
exercise = Exercise("Custom countable kinds can keep a separate sequence.")

paragraph = Paragraph("Use ", main.reference(), " before the proof.")
proof = Proof("Proofs are unnumbered by default, so reference them with a custom label.")
"""

PROJECT_LAYOUT_SNIPPET = """my-report/
  main.py
  assets/
    logo.png
    architecture.png
  data/
    benchmark.csv
    ablation.csv
  artifacts/
    report.docx
    report.pdf
    report.html
"""

CLI_WORKFLOW_SNIPPET = """# Build a Python-authored document that exposes build_document(), document, doc, or report.
oodocs build report.py --out artifacts --outputs docx,pdf,html

# Build imported sources through the same import APIs used in Python.
oodocs build README.md --outputs docx,pdf,html --out artifacts
oodocs build notebook.ipynb --outputs pdf --out artifacts

# Validate without writing outputs; use --fail-on-warning when warnings should fail CI.
oodocs validate report.py
oodocs validate report.py --outputs pdf --fail-on-warning
"""

PYTHON_BUILD_SOURCE_SNIPPET = """from oodocs import Chapter, Document, Paragraph, Section

def build_document() -> Document:
    return Document(
        "Operational Report",
        Chapter(
            "Status",
            Section("Summary", Paragraph("Everything needed for the report is here.")),
        ),
    )
"""

VALIDATION_SNIPPET = """document = build_document()
result = document.validate(formats=("docx", "pdf", "html"))

if not result.ok:
    print(result)
    raise SystemExit(1)

document.save_all("artifacts", stem="operational-report")
"""

MARKDOWN_RELEASE_NOTES_SNIPPET = """from oodocs import Document, Section, Table, parse_markdown

release_notes = {
    "v0.8.0": "# v0.8.0\\n\\n## Added\\n- [x] Markdown import\\n- [x] Release digest",
    "v0.7.0": "# v0.7.0\\n\\n## Changed\\n- ~~Old notes~~ are archived",
}

parsed_notes = [
    Document.from_markdown(markdown_text)
    for markdown_text in release_notes.values()
]

summary = Table(
    headers=["Release", "Imported blocks"],
    rows=[
        [note.title, str(len(note.body.children))]
        for note in parsed_notes
    ],
)

digest = Document(
    "Release note digest",
    summary,
    *[
        Section(note.title, note.body.children, numbered=False)
        for note in parsed_notes
    ],
)

ad_hoc_blocks = parse_markdown("## Follow-up\\n\\n- Publish DOCX\\n- Publish PDF").blocks
digest.body.children.extend(ad_hoc_blocks)
"""

NOTEBOOK_IMPORT_SNIPPET = """from oodocs import Document, Section, parse_notebook

analysis = Document.from_notebook(
    "analysis.ipynb",
    include_outputs=True,
)

appendix_blocks = parse_notebook(
    "exploration.ipynb",
    include_outputs=False,
).blocks

report = Document(
    "Notebook-backed report",
    Section("Curated analysis", analysis.body.children, numbered=False),
    Section("Exploration appendix", appendix_blocks, numbered=False),
)

report.save_all("artifacts/notebook-report", stem="analysis")
"""

LATEX_COMPARISON_SNIPPET = """from oodocs import Box, Divider, Figure, Paragraph, Table, VerticalSpace, bold, inline_code

summary = Box(
    Paragraph(bold("Takeaway. "), "The result table and figure are normal document blocks."),
    Table(
        headers=["Method", "Score"],
        rows=[["Baseline", "0.81"], ["OODocs workflow", "0.88"]],
        caption="Benchmark summary generated from Python data.",
    ),
    VerticalSpace(6),
    Divider(space_before=2, space_after=6),
    Figure("assets/system-diagram.png", caption="Pipeline diagram.", width=12, unit="cm"),
    title="Report-ready evidence",
    width=16,
    unit="cm",
    block_alignment="center",
)

Paragraph("See ", summary.reference(), " for the editable evidence package.")
"""

INLINE_WORD_FEATURES_SNIPPET = """from oodocs import Paragraph, Text, highlight, line_break, prescript, strikethrough, subscript, superscript

Paragraph(
    "Keep ",
    highlight("review focus", "#FFF2CC"),
    ", remove ",
    strikethrough("old value"),
    line_break(),
    "Continue with ",
    Text.styled("small caps", small_caps=True),
    ", ",
    Text.styled("uppercase", uppercase=True),
    ", H",
    Text.styled("2", subscript=True),
    "O, and x",
    Text.styled("2", superscript=True),
    ". Front scripts work in prose too: ",
    prescript("14", "6", "C"),
    " and index ",
    subscript("i"),
    superscript("j"),
    ".",
)
"""

INLINE_CHIPS_SNIPPET = """from oodocs import Paragraph, badge, keyboard, status, tag

Paragraph(
    "Route ",
    tag("api"),
    " work with ",
    status("ready", state="success"),
    ", show ",
    badge("3 notes"),
    ", and name ",
    keyboard("Ctrl+Enter"),
    " without leaving the inline flow.",
)
"""

JAVASCRIPT_SNIPPET = """export function summarize(rows) {
  return rows
    .filter((row) => row.ready)
    .map((row) => `${row.name}: ${row.score.toFixed(2)}`);
}
"""

SQL_SNIPPET = """SELECT project, AVG(score) AS mean_score
FROM benchmark_runs
WHERE status = 'accepted'
GROUP BY project
ORDER BY mean_score DESC;
"""

YAML_SNIPPET = """report:
  title: OODocs User Guide
  outputs:
    - docx
    - pdf
    - html
"""

PARAGRAPH_INDENT_SNIPPET = """from oodocs import BlockDefaults, DocumentSettings, Paragraph, Theme

settings = DocumentSettings(
    theme=Theme(blocks=BlockDefaults(paragraph_text_alignment="left"))
)

Paragraph(
    "This paragraph inherits the document-wide left alignment."
)

Paragraph(
    "This one overrides the document-wide default.",
    text_alignment="right",
)

Paragraph(
    "First-line indents work like a normal word processor paragraph.",
    left_indent=1.0,
    first_line_indent=0.6,
    unit="cm",
)

Paragraph(
    "Hanging indents are useful for references, definitions, and glossary-like entries.",
    left_indent=1.2,
    first_line_indent=-0.6,
    unit="cm",
)
"""

TABLE_ALIGNMENT_SNIPPET = """from oodocs import Table, TableCell

Table(
    headers=[["Metric", "Value"]],
    rows=[
        [
            "Latency",
            TableCell(
                "14 ms",
                background_color="#FFE699",
                text_color="#7F1D1D",
                bold=True,
                text_alignment="right",
                vertical_alignment="middle",
            ),
        ],
        ["Quality", "Stable"],
    ],
    row_styles={1: {"background_color": "#E2F0D9", "italic": True}},
    column_styles={0: {"text_color": "#1F4E79", "bold": True}},
    header_row_styles={0: {"background_color": "#1F4E79", "text_color": "#FFFFFF"}},
    header_text_alignment="center",
    cell_vertical_alignment="middle",
)
"""

BOOKTABS_TABLE_SNIPPET = """from oodocs import Table

Table(
    headers=["Metric", "Value"],
    rows=[["Accuracy", "0.91"], ["F1", "0.88"]],
    caption="Publication-style metrics.",
    style="booktabs",
)
"""

TABLE_PLACEMENT_SNIPPET = """from oodocs import Figure, Table

audit_log = Table(
    headers=["Step", "Result"],
    rows=[[f"Step {index}", "ok"] for index in range(40)],
    caption="Long audit log.",
    split=False,      # Prefer one block, but auto-split when it is too long.
    placement="tbp",  # Advanced float-like placement preference.
)

runbook = Table(
    headers=["Check", "Owner"],
    rows=[["Preflight", "Release lead"], ["Smoke test", "QA"]],
    caption="Runbook checks.",
    split=True,       # Always render here and allow page breaks.
)

diagram = Figure(
    "assets/system-diagram.png",
    caption="Pipeline diagram.",
    placement="top", # Advanced placement hint for the renderer.
)
"""

COMPONENT_PRESETS_SNIPPET = """from oodocs import Paragraph
from oodocs.presets.components import CalloutBox, KeyValueTable, Nomenclature

review_note = CalloutBox(
    Paragraph("Check terminology before external review."),
    title="Review focus",
    style="warning",
)

metadata = KeyValueTable(
    {
        "Manuscript type": "Research article",
        "Output bundle": "DOCX, PDF, HTML",
    },
    caption="Submission metadata.",
)

nomenclature = Nomenclature(
    [
        ("A", "Floor area", "m2"),
        ("E", "Annual energy use", "kWh"),
        ("q", "Heat flux", "W/m2"),
        ("T", "Air temperature", "degC"),
    ],
    double_column=True,
)
"""

TEMPLATE_PRESETS_SNIPPET = """from oodocs import Author, Paragraph
from oodocs.presets.templates import JournalArticleTemplate, ManuscriptSection

document = JournalArticleTemplate().build(
    "Readable manuscript generation",
    authors=[Author("Research Lead", affiliations=["Example Lab"], corresponding=True)],
    abstract="A concise abstract paragraph.",
    keywords=["document generation", "python"],
    sections=[
        ManuscriptSection("Introduction", [Paragraph("Problem and contribution.")]),
        ManuscriptSection("Methods", [Paragraph("Data, model, and validation.")]),
    ],
    acknowledgements="The authors thank the internal review group.",
    data_availability=None,
)

document.save_all("artifacts/manuscript", stem="article-draft")
"""


def build_usage_guide_document() -> Document:
    """Build a detailed reference-style usage guide."""

    logo_figure = Figure(LOGO_PATH, width=1.8, placement="here")
    pipeline_figure = Figure(
        PIPELINE_DIAGRAM_PATH,
        caption=Paragraph(
            "Core authoring pipeline from project inputs to synchronized DOCX, PDF, and HTML outputs."
        ),
        width=6.5,
    )
    author_layout_figure = Figure(
        AUTHOR_LAYOUT_DIAGRAM_PATH,
        caption=Paragraph(
            "Three practical author-display strategies: journal-style default, stacked guide profiles, and fully manual front matter."
        ),
        width=6.5,
    )
    renderer_behavior_figure = Figure(
        RENDERER_BEHAVIOR_DIAGRAM_PATH,
        caption=Paragraph(
            "Renderer-specific behavior for notes, review workflows, and cross-reference stability."
        ),
        width=6.5,
    )
    cli_workflow_figure = Figure(
        CLI_WORKFLOW_DIAGRAM_PATH,
        caption=Paragraph(
            "Command-line builds and validation all call the same high-level workflow API."
        ),
        width=6.5,
    )

    navigation_table = Table(
        headers=["Need", "Recommended chapter", "What you will find there"],
        rows=[
            ["First successful export", "1. Overview", "The minimal document shape, the save methods, and the default rendering model."],
            ["Switching from LaTeX", "1. Overview", "A concrete mapping from familiar LaTeX concepts to OODocs objects."],
            ["Author metadata and covers", "2. Metadata and Title Matter", "Structured authors, journal-style defaults, stacked profiles, and cover conventions."],
            ["Tables, figures, and references", "4. Tables, Figures, and Cross-References", "Caption numbering, block references, and data-backed media objects."],
            ["Notes and citations", "5. Notes, Comments, and References", "Footnotes, generated comments pages, citation libraries, and bibliography output."],
            ["Pagination and output differences", "6. Layout and Pagination", "Contents styling, caption cohesion, and renderer-specific note behavior."],
            ["Reusable document shapes", "8. Component Presets", "Ready-made callouts, option tables, nomenclature boxes, and journal template entry points."],
        ],
        caption="A reading map for the guide.",
        column_widths=[2.0, 2.0, 2.6],
    )
    example_catalog_table = Table(
        headers=["Task", "Example", "Use it when"],
        rows=[
            ["Learn OODocs concepts", "usage_guide_example", "Start here for the object model, renderer behavior, imports, validation, presets, and CLI workflow."],
            ["Write a manuscript from data and figures", "journal_paper_example", "Assemble CSV-backed tables, matplotlib figures, citations, and article-style sections."],
            ["Document Python computation results", "native_benchmark_report", "Turn benchmark data and structured Python results into a compact technical report."],
            ["Reuse release-note Markdown", "release_notes_digest", "Import versioned Markdown release notes into a synchronized DOCX, PDF, and HTML digest."],
            ["Document Python API objects", "api_objects_example", "Collect docstrings into API objects, help-book pages, composable reference sections, and sidecars."],
            ["Create reusable named styles", "style_cleanup_smoke", "Exercise document-wide StyleSheet entries for paragraphs, tables, boxes, and chips."],
            ["Start from a template", "template_presets", "Build a complete document from content-oriented preset inputs."],
        ],
        caption="Purpose-based entry points for the bundled examples.",
        column_widths=[2.0, 1.8, 3.2],
    )
    document_credits_table = Table(
        headers=["Label", "Value", "Role in this document"],
        rows=[
            [
                "Author",
                "OODocs Contributors",
                "Maintainers and release editors for the public documentation workflow.",
            ],
            [
                "Author",
                "Hyeong-Gon Jo",
                "Repository steward and maintainer of the example documentation.",
            ],
            [
                "Affiliation",
                "Building Simulation LAB, Seoul National University",
                "Structured affiliation metadata used by repository stewardship examples.",
            ],
        ],
        caption="Document credits separate names, affiliations, and document roles.",
        column_widths=[1.6, 2.7, 3.2],
    )
    latex_transition_table = Table(
        headers=["If you reach for this in LaTeX", "Use this in oodocs", "Why it is easier here"],
        rows=[
            ["\\part", "Part(...)", "Parts render on their own separator pages and do not reset chapter numbering, matching the usual LaTeX book/report behavior."],
            ["\\appendix", "Appendix(Chapter(...), ...)", "Appendix child chapters use A, B, C numbering, and references to those chapters use the same generated labels."],
            ["\\section, \\subsection", "Chapter, Section, Subsection", "The Python object tree is also the document outline, so headings, contents, and anchors stay synchronized."],
            ["\\textbf, \\emph, \\texttt", "bold(...), italic(...), inline_code(...)", "Inline styling stays attached to the words being styled and works in DOCX, PDF, and HTML."],
            ["\\includegraphics", "Figure(path_or_matplotlib_figure, caption=...)", "Static images and Python-generated figures use the same captioning and referencing model."],
            ["\\vspace{...}, \\hrule", "VerticalSpace(...), Divider()", "Vertical spacing and separators remain explicit document blocks, including a Notion-like divider for lightweight visual breaks."],
            ["tabular or booktabs", "Table(...), Table.from_dataframe(...), style=\"booktabs\"", "Tables can be created directly from Python data instead of being copied into markup."],
            ["\\label and \\ref", "Call reference(figure_obj) or figure_obj.reference() inside Paragraph(...)", "References follow the indexed document order without hand-maintained labels."],
            ["tcolorbox", "Box(..., background_color=..., padding=...)", "Report panels remain editable in Word while keeping a similar grouped visual shape in PDF and HTML."],
            ["BibTeX plus \\cite", "CitationLibrary and CitationSource.cite(...)", "Citations are authored inline, and only cited sources appear on ReferenceList()."],
        ],
        caption="LaTeX habits translated into oodocs's Python-first authoring model.",
        column_widths=[1.9, 2.1, 2.8],
    )
    author_options_table = Table(
        headers=["Approach", "When it fits best", "Configuration pattern"],
        rows=[
            ["Structured journal default", "Manuscripts and technical reports with compact title matter.", "DocumentSettings(authors=[...])"],
            ["Structured stacked profiles", "Guides, internal reports, and project documentation.", "DocumentSettings(authors=[...], author_layout=AuthorLayout(mode='stacked'))"],
            ["Simple metadata string", "Short exports where file properties matter more than visible title blocks.", "DocumentSettings(metadata_author='Team Name')"],
            ["Manual front matter section", "Branded covers or institution-specific title pages.", "Keep metadata simple and author the visible cover with unnumbered sections."],
        ],
        caption="Author-display options from most automated to most manual.",
        column_widths=[1.8, 2.5, 2.3],
    )
    generated_content_table = Table(
        headers=["Generated object", "Why it exists", "What triggers it"],
        rows=[
            ["TableOfContents()", "Creates a navigable outline from authored headings.", "Place the block where the contents page should appear."],
            ["ListOfTables() / ListOfFigures()", "Collects numbered captions in a stable order with page labels in DOCX and PDF.", "Use captioned tables or figures earlier in the document; pass show_page_numbers=False for a link-only list."],
            ["CommentList()", "Exports reviewer comments without disturbing reading flow.", Comment.annotated("Place review remarks inline", "CommentList() collects these review notes onto a dedicated generated page.")],
            ["ReferenceList()", "Renders only the bibliography entries that were cited.", "Cite items from CitationLibrary or CitationSource."],
        ],
        caption="Generated pages that help a long document stay navigable.",
        column_widths=[1.8, 2.3, 2.5],
    )
    media_workflow_table = Table(
        headers=["Task", "Preferred object", "Why the object matters"],
        rows=[
            ["Insert a benchmark table from code", "Table.from_dataframe(...)", "The rendered table stays attached to the data-processing step that created it."],
            ["Insert an architecture figure from disk", "Figure('assets/diagram.png')", "Static diagrams can stay under version control without manual copy-paste."],
            ["Refer to a caption from prose", "Paragraph('See ', figure_obj.reference(), '.')", "Block references update automatically when figure order changes."],
            ["Keep a note near evidence", Footnote.annotated("page-footnote default", "DOCX uses page footnotes by default. PDF and HTML keep a generated notes page because their layout engines do not share Word's native footnote model."), "Footnotes stay authored inline instead of being managed in a separate editor pane."],
        ],
        caption="Working patterns for media objects and references.",
        column_widths=[1.9, 2.0, 2.7],
    )
    media_placement_table = Table(
        headers=["Option", "Default use", "Renderer effect"],
        rows=[
            ["Table(split=False)", "Prefer an uncut floating table.", "Short tables stay together and may move after nearby prose; very long tables become split tables with repeated headers."],
            ["Table(split=True)", "Treat the table like LaTeX here placement.", "The table is rendered in source order and can break across pages."],
            ["placement='tbp'", "Advanced float-like preference.", "Renderers keep the object together when possible and may move it to a better page position."],
            ["placement='top' or 'page'", "Advanced forced placement.", "Renderers add page-break hints around the table or figure."],
        ],
        caption="Advanced table and figure placement controls.",
        column_widths=[1.7, 2.5, 2.6],
    )
    renderer_rules_table = Table(
        headers=["Concern", "Shared behavior", "Important renderer detail"],
        rows=[
            ["Heading numbering", "Document structure drives numbering in all outputs.", "Part entries use independent Roman labels; appendix child chapters switch to A, B, C labels."],
            ["Captions", "Tables and figures receive automatic numbers and can be referenced inline.", "Captions are kept visually closer to their table or figure to avoid page-break confusion."],
            ["Footnotes", "Footnotes are authored with the same inline API everywhere.", "DOCX uses native page footnotes; PDF and HTML fall back to generated note pages."],
            ["Hyperlinks", "External links and block anchors remain visible in all outputs.", "HTML makes them directly clickable while DOCX and PDF preserve them in exported files."],
        ],
        caption="Behavior that stays stable across renderers and the places where format details still matter.",
        column_widths=[1.5, 2.7, 2.4],
    )
    page_layout_table = Table(
        headers=["Need", "API", "Effect"],
        rows=[
            ["Work in metric units", "DocumentSettings(unit='cm')", "Numeric lengths are interpreted as centimeters unless an object overrides unit."],
            ["Set page layout", "PageLayout(page_size=PageSize.a4(), page_margins=...)", "DOCX, PDF, and HTML use the same page box."],
            ["Set orientation", "PageLayout.landscape(PageSize.a4(), PageMargins.all(...))", "Landscape swaps the page box before text width helpers and renderers use it."],
            ["Set printable margins", "PageMargins.all(...) or PageMargins.symmetric(...)", "The text area and HTML @page margins stay aligned."],
            ["Add local vertical spacing", "VerticalSpace(8)", "A small block-level spacer gives the flow breathing room without inserting dummy prose."],
            ["Insert a visual separator", "Divider()", "A Notion-like horizontal rule separates nearby blocks while staying renderer-neutral."],
            ["Force a new page", "PageBreak()", "The break is explicit in the document tree and renders across DOCX, PDF, and HTML."],
            ["Size a figure from text width", "settings.get_text_width(0.75)", "Figures can follow the document text block instead of hard-coded page assumptions."],
        ],
        caption="Page layout controls shared across renderers.",
        column_widths=[1.7, 2.6, 2.6],
    )
    contents_style_table = Table(
        headers=["Concern", "Default", "Customization path"],
        rows=[
            ["Part entries", "Shown above chapters when authored.", "Use Part(...) for book-like divisions; set level_styles={0: TocLevelStyle(...)} to tune the part line."],
            ["Appendix entries", "Shown as an unnumbered separator followed by A/B/C child chapters.", "Use Appendix(Chapter(...), ...) when end matter needs appendix numbering and contents entries."],
            ["Page numbers", "Shown by default for contents, table lists, and figure lists in paginated DOCX and PDF output.", "HTML keeps clean link-only generated lists because browsers do not provide stable page labels."],
            ["Leader dots", "Dotted leaders connect the heading text to the page number in paginated output.", "Set leader='' for no leader or another short string for a different visual cue."],
            ["Scoped lists", "Generated lists cover the whole document.", "Set scope='part', scope='chapter', or scope='section' for local mini contents, table lists, or figure lists."],
            ["Heading depth", "All numbered headings are included.", "Set max_level=2 or max_level=3 for shorter contents pages."],
            ["Hierarchy styling", "Top-level entries are bold; lower levels use normal weight by default.", "Pass level_styles={level: TocLevelStyle(...)} for per-level spacing, indentation, and emphasis."],
        ],
        caption="Table-of-contents defaults and customization options.",
        column_widths=[1.6, 2.7, 2.7],
    )
    settings_options_table = Table(
        headers=["Object", "Options", "Scope"],
        rows=[
            ["DocumentSettings", "metadata_author, summary, subtitle, authors, author_layout, cover_page", "Document metadata and title matter."],
            ["DocumentSettings", "unit, page_layout, page_items", "Page geometry and page-positioned overlays."],
            ["DocumentSettings", "theme", "Document-wide renderer defaults shared by DOCX, PDF, and HTML."],
            ["PageLayout", "page_size, page_margins, orientation; portrait(...); landscape(...)", "Grouped page geometry comparable to LaTeX geometry options."],
            ["PageSize", "width, height, unit", "Physical page box."],
            ["PageMargins", "top, right, bottom, left, unit; all(...); symmetric(...)", "Printable area around document content."],
            ["AuthorLayout", "mode, name_separator, show_affiliations, show_details", "How structured author metadata is displayed."],
        ],
        caption="Document-level configuration options.",
        column_widths=[1.6, 3.2, 2.3],
    )
    theme_options_table = Table(
        headers=["Theme group", "Options", "Use it for"],
        rows=[
            ["TypographyDefaults", "body_font_name, monospace_font_name, title_font_size, body_font_size, heading_sizes, caption_font_size", "Fonts and type scale."],
            ["CaptionDefaults", "caption_text_alignment, table_caption_position, figure_caption_position, table_label, figure_label, caption/reference labels", "Caption placement and localized labels."],
            ["CitationDefaults", "citation_style, reference_style", "Inline citation labels and generated reference entry style."],
            ["GeneratedContentDefaults", "contents/list/comments/footnotes/references titles, generated_heading_level, generated_content_page_breaks", "Generated content titles and heading level."],
            ["PageNumberDefaults", "show_page_numbers, page_number_alignment, page_number_template, front/main matter counters, page_number_font_size", "Footer page labels."],
            ["TitleMatterDefaults", "title_text_alignment, subtitle_text_alignment, author_text_alignment, affiliation_text_alignment, author_detail_text_alignment", "Title-page and metadata alignment."],
            ["BlockDefaults", "page_background_color, paragraph_text_alignment, table/figure/box block alignment, footnote_placement, list styles, heading_styles, heading_numbering", "Document-wide defaults that individual blocks can override."],
        ],
        caption="Grouped Theme defaults are passed as keyword groups to Theme(...).",
        column_widths=[1.7, 3.7, 1.8],
    )
    block_options_table = Table(
        headers=["Block", "Direct kwargs", "Style object when needed"],
        rows=[
            ["Text and styled(...)", "font_name, font_size, text_color, highlight_color, bold, italic, underline, strikethrough, small_caps, uppercase, subscript, superscript", "Use TextStyle only when a reusable inline style needs a name."],
            ["Paragraph, CodeBlock, Equation", "text_alignment, space_before, space_after, leading, left_indent, right_indent, first_line_indent, keep_together, keep_with_next, page_break_before, widow_control, unit", "Use ParagraphStyle only for shared paragraph rhythm."],
            ["Section, Chapter, Subsection", "level, numbered, toc, anchor, run_in_title_style, heading_style", "Use HeadingStyle for per-level theme defaults or one-off heading overrides."],
            ["Part, Appendix", "title, toc; Part also accepts numbered", "Use Appendix when child chapters should switch to A/B/C numbering."],
            ["BulletList, NumberedList", "marker=CounterStyle(...), indent, marker_gap", "Use ListStyle only for repeated list conventions."],
            ["Box", "border, background_color, title colors, padding, space_after, width, unit, block_alignment", "Use BoxStyle only for named callout or report-panel designs."],
            ["Table", "header/body/alternate colors, border, top_rule, header_rule, bottom_rule, alignment, cell_padding, repeat_header_rows", "Use style=\"booktabs\" for publication-style horizontal rules without vertical grid lines."],
            ["TableCell", "colspan, rowspan, background_color, text_color, bold, italic, text_alignment, vertical_alignment", "Use TableCellStyle only for reusable row, column, or cell styling."],
            ["TableOfContents, ListOfTables, ListOfFigures", "scope, show_page_numbers, leader; TableOfContents also accepts max_level and level_styles", "Use scope for document, part, chapter, or section-local generated lists."],
            ["Figure, SubFigure, SubFigureGroup", "width, height, unit, placement, image_dpi, columns, column_gap, label_format", "Use caption Paragraphs when caption text needs inline styling."],
        ],
        caption="Block-level option scope from quick kwargs to reusable style objects.",
        column_widths=[1.8, 3.6, 2.0],
    )
    component_presets_table = Table(
        headers=["Preset", "What it builds", "Common customizations"],
        rows=[
            ["CalloutBox", "A styled Box using named styles such as info, note, success, or warning.", "style, title, and normal Box options when using a concrete BoxStyle."],
            ["KeyValueTable", "A compact two-column Table for metadata and option lists.", "headers, caption, style, column widths."],
            ["Nomenclature", "A heavy-outlined Box containing a symbol, meaning, and optional unit table with no internal rules.", "double_column, headers, padding, border, title."],
            ["CompactTable", "A table preset using the compact named table style.", "Any normal Table kwarg, with style objects still available for reusable designs."],
        ],
        caption="Component presets wrap ordinary blocks and still accept the same block/style options.",
        column_widths=[1.5, 3.0, 2.6],
    )
    template_presets_table = Table(
        headers=["Template", "Accepted structure", "Best first use"],
        rows=[
            ["JournalArticleTemplate", "title, authors, abstract, keywords, body sections, optional declarations, citations.", "A content-first manuscript builder where the caller fills article fields and the preset owns routine article assembly."],
            ["ManuscriptSection", "title, children, level, numbered.", "A small descriptor when users prefer data-like section lists over nested Section objects."],
            ["Advanced overrides", "theme, page_layout, author_layout, contents/references flags.", "Use these only when a lab or target journal has explicit layout requirements."],
        ],
        caption="Template presets build full Document objects from manuscript-shaped inputs.",
        column_widths=[1.7, 3.4, 2.3],
    )
    figure_sizing_table = Table(
        headers=["Figure intent", "Pattern", "Renderer behavior"],
        rows=[
            ["Constrain by width", "Figure(path, width=12, unit='cm')", "The image keeps its aspect ratio while fitting the requested width."],
            ["Constrain by height", "Figure(path, height=8, unit='cm')", "The image keeps its aspect ratio while fitting the requested height."],
            ["Force a box", "Figure(path, width=12, height=8, unit='cm')", "Both dimensions are honored, similar to explicit LaTeX graphic sizing."],
            ["Follow text width", "Figure(path, width=settings.get_text_width(0.8))", "The width is computed from page size minus margins."],
        ],
        caption="Figure sizing patterns for width, height, and document-relative sizing.",
        column_widths=[1.8, 2.9, 2.3],
    )
    drawing_placement_table = Table(
        headers=["Placement", "Use it for", "Anchor behavior"],
        rows=[
            ["DocumentSettings.page_items", "Watermarks, trim guides, fixed approval areas, and form decoration.", "Coordinates start from page, margin/content, or a named Shape."],
            ["placement='inline'", "Small logos, seals, badges, and simple shapes that should move with nearby prose.", "The object sits in the authored flow like directly inserted Word media."],
        ],
        caption="Coordinate-based drawings can be page overlays or inline flow objects.",
        column_widths=[1.6, 3.0, 2.2],
    )
    scaling_table = Table(
        headers=["Project stage", "Suggested structure", "Reasoning"],
        rows=[
            ["Single script", "Keep document assembly in one main.py file.", "The document tree stays visible while the project is still changing rapidly."],
            ["Growing assets", "Split reusable chart builders or citation helpers into local modules.", "Move code only when repeated logic starts to hide the document structure."],
            ["Team workflow", "Keep data, assets, and document outputs in sibling folders.", "It becomes easier to review analysis changes and document changes together."],
            ["Release workflow", "Render artifacts in CI and attach them to GitHub releases.", "The exported files and the package version can move together."],
        ],
        caption="How the source layout can grow without losing readability.",
        column_widths=[1.4, 2.3, 2.9],
    )
    cli_command_table = Table(
        headers=["Command", "Input expectation", "Use it when"],
        rows=[
            ["oodocs build report.py --out artifacts", "A Python file exposing document, doc, report, or build_document().", "The source of record is a Python-authored Document."],
            ["oodocs build README.md --outputs docx,pdf,html --out artifacts", "Markdown source imported with the same parser used by Document.from_markdown(...).", "A README, changelog, release note, or generated Markdown file should become a rendered bundle."],
            ["oodocs build notebook.ipynb --outputs pdf --out artifacts", "A notebook imported with the same parser used by Document.from_notebook(...).", "A notebook-backed analysis needs a quick PDF export or an appendix source."],
            ["oodocs validate report.py", "Any Python, Markdown, or notebook source that can be loaded as a Document.", "CI should fail before rendering when authoring mistakes are present."],
        ],
        caption="CLI commands and the source shapes they expect.",
        column_widths=[2.5, 2.4, 2.5],
    )
    validation_table = Table(
        headers=["Validation issue", "Why it matters", "Typical fix"],
        rows=[
            ["Missing image file", "DOCX, PDF, and HTML cannot render media that is not present.", "Keep assets under version control or pass an existing Path."],
            ["Uncaptioned table or figure reference", "Automatic references need a numbered target.", "Add a caption or provide an explicit custom reference label."],
            ["Unnumbered heading or countable reference", "The default label cannot be resolved without a number.", "Set numbered=True, set toc=True for heading anchors, or write reference(obj, 'custom label')."],
            ["Top-level heading below chapter", "A report can look like it skipped its first chapter.", "Wrap imported blocks in Chapter(...) or import with heading_level_shift."],
            ["HTML generated-list page numbers", "Browsers do not have stable rendered page numbers.", "Accept the warning for HTML or set show_page_numbers=False on TableOfContents, ListOfTables, or ListOfFigures."],
        ],
        caption="Validation results are structured objects, but they print as a compact table for terminal and CI logs.",
        column_widths=[2.0, 2.7, 2.7],
    )
    Exercise = create_countable_block_type("Exercise", counter="exercise")
    counted_definition = Definition(
        "A countable block is a document block with a visible kind label and an index-assigned number."
    )
    counted_theorem = Theorem(
        "The same source object can be referenced from prose after the render index assigns its number.",
        title="Stable references",
    )
    counted_assumption = Assumption(
        "Assumptions, lemmas, theorems, examples, and remarks share the same theorem-like counter by default."
    )
    counted_exercise = Exercise(
        "Custom countable kinds can use their own counter, or join the theorem counter by passing counter='theorem'."
    )
    preset_callout = CalloutBox(
        Paragraph(
            "Presets are ordinary oodocs components with carefully chosen defaults. Use direct kwargs for quick local changes and reserve style objects for repeated house styles that need a name."
        ),
        title="Preset rule",
        style="info",
    )
    preset_metadata_table = KeyValueTable(
        {
            "Preset namespace": "oodocs.presets.components",
            "Customization surface": "Same direct kwargs as core components",
            "Output formats": "DOCX, PDF, HTML",
        },
        caption="A KeyValueTable preset used as a live component example.",
        column_widths=[2.4, 4.4],
    )
    preset_nomenclature = Nomenclature(
        [
            ("A", "conditioned floor area", "m2"),
            ("E", "annual energy use", "kWh"),
            ("q", "heat flux", "W/m2"),
            ("T", "air temperature", "degC"),
        ],
        double_column=True,
        title="Nomenclature",
        width=15.0,
        unit="cm",
    )

    cover_callout = Box(
        Paragraph(
            "This guide stays intentionally close to the authored source. The point is not only to document the API, but also to let a new user read the script and see how the Python tree maps to the final pages."
        ),
        BulletList(
            "Keep title matter, metadata, and theme choices near DocumentSettings(...).",
            "Keep block structure explicit so chapters and sections remain visible in code review.",
            "Treat figures, tables, and notes as authored objects rather than pasted export artifacts.",
        ),
        title="Reading Principle",
        border=BorderStyle.solid("#6E8497", width=0.75),
        background_color="#F6F9FC",
        title_background_color="#DCE8F4",
    )
    contributor_certificate = Box(
        Paragraph(
            "Awarded for keeping document structure readable across DOCX, PDF, and HTML.",
            text_alignment="center",
            space_after=8,
        ),
        Table(
            headers=["Authoring surface", "Word behavior", "Portable behavior"],
            rows=[
                ["Box", "Editable table-backed panel", "Stable tcolorbox-like grouping"],
                ["Table", "Editable cells", "Shared data-backed layout"],
                ["Figure", "Reviewable inserted media", "Same asset in every output"],
            ],
            column_widths=[3.6, 5.2, 6.2],
            unit="cm",
            header_background_color="#E7EEF7",
            border=BorderStyle.solid("#B8C6D6", width=0.5),
            cell_padding=Padding.all(4),
        ),
        Figure(LOGO_PATH, width=3.2, unit="cm"),
        Paragraph(
            "Generated from the same Python document tree as this guide.",
            text_alignment="center",
            space_after=0,
        ),
        title="OODocs Contributor Certificate",
        border=BorderStyle.solid("#D4B56A", width=1.0),
        background_color="#FDFBF6",
        title_background_color="#1058A3",
        title_text_color="#FFFFFF",
        padding=Padding.symmetric(vertical=8, horizontal=12),
        width=18.0,
        unit="cm",
        block_alignment="center",
    )

    return Document(
        "OODocs User Guide",
        logo_figure,
        Section(
            "Guide Cover",
            document_credits_table,
            Paragraph(
                bold("License. "),
                "MIT. The package metadata, source code, and example release workflow all live in the same repository so the rendered outputs can be attached to a tagged release."
            ),
            Paragraph(
                bold("Repository. "),
                link("https://github.com/Gonie-Gonie/oo-docs", "github.com/Gonie-Gonie/oo-docs"),
                ".",
            ),
            Paragraph(
                bold("Positioning. "),
                "OODocs is for situations where document content already lives near Python data, figures, scripts, and review workflows."
            ),
            cover_callout,
            level=2,
            numbered=False,
        ),
        TableOfContents(),
        ListOfTables(),
        ListOfFigures(),
        Part(
            "Getting Oriented",
            Chapter(
                "Overview",
            Section(
                "What oodocs is trying to solve",
                Paragraph(
                    "OODocs is a Python-first document authoring toolkit. It lets you define a document with ordinary Python objects, render the same source to DOCX, PDF, and HTML, and keep data-backed tables and figures close to the code that generated them."
                ),
                Paragraph(
                    "The central motivation is the one described in ",
                    RELATED_WORK.cite("literate-programming"),
                    ": authorship becomes easier to trust when prose, evidence, and automation live in one readable source."
                ),
                pipeline_figure,
                Paragraph(
                    "The pipeline shown in ",
                    pipeline_figure.reference(),
                    " is the real payoff of the package. Data files, static assets, title metadata, generated pages, and renderer output all remain downstream of one explicit document tree."
                ),
                navigation_table,
            ),
            Section(
                "Example catalog",
                Paragraph(
                    "The usage guide explains the core concepts. The other bundled examples are workflow entry points, so choose them by the task you are trying to automate."
                ),
                example_catalog_table,
            ),
            Section(
                "The smallest working document",
                Paragraph(
                    "A first document only needs a title, a chapter, a section, a paragraph, and one save call per output format. The quick-start example below intentionally uses ",
                    inline_code("bold(...)"),
                    " rather than older method-style emphasis so the current preferred inline API stays visible."
                ),
                CodeBlock(QUICK_START_SNIPPET, language="python"),
                Paragraph(
                    "For the common case where you want all three outputs together, call ",
                    inline_code("document.save_all('artifacts')"),
                    ". It uses a filename-safe version of the document title by default, or you can pass ",
                    inline_code("stem='my-report'"),
                    " to choose the base filename."
                ),
                NumberedList(
                    "Author the structure with Document, Part, Chapter, and Section objects.",
                    "Write prose with Paragraph plus explicit inline helpers such as bold(...), inline_code(...), and links.",
                    "Call document.save(...) with a .docx, .pdf, or .html path; use the explicit save_docx(...), save_pdf(...), and save_html(...) methods when that reads better.",
                ),
            ),
            Section(
                "For authors coming from LaTeX",
                Paragraph(
                    "If you already know LaTeX, the important shift is that oodocs treats document structure as Python objects rather than commands in a markup stream. You still get numbered headings, captions, cross-references, equations, citations, and tcolorbox-like panels, but the same source can also produce an editable DOCX review copy."
                ),
                latex_transition_table,
                Divider(space_before=2, space_after=8),
                Paragraph(
                    "The practical advantage is strongest when the document depends on Python outputs. A table can come from a dataframe, a figure can come from matplotlib, and the caption reference can be written directly in prose without copying values between tools."
                ),
                CodeBlock(LATEX_COMPARISON_SNIPPET, language="python"),
            ),
        ),
        Chapter(
            "Metadata and Title Matter",
            Section(
                "Structured authors as the default path",
                Paragraph(
                    "The default structured-author path is now journal-friendly without forcing every document to look like a journal submission. If you provide ",
                    inline_code("Author(...)"),
                    " objects, oodocs groups names, affiliations, and correspondence information into a compact title block by default."
                ),
                Paragraph(
                    "That default fits papers well, but guides often read better with stacked author profiles. This guide therefore uses ",
                    inline_code("AuthorLayout(mode='stacked')"),
                    " while the journal example relies on the default journal-style arrangement."
                ),
                author_layout_figure,
                author_options_table,
            ),
            Section(
                "When to customize the author display",
                Paragraph(
                    "The practical decision is simple: use the journal default when the visible priority is compact authorship, use stacked profiles when the document benefits from role context, and fall back to a simple metadata author string when visible title matter is mostly manual."
                ),
                CodeBlock(AUTHOR_LAYOUT_SNIPPET, language="python"),
                Paragraph(
                    "If even the stacked layout is still too opinionated, keep ",
                    inline_code("DocumentSettings(metadata_author='Team Name')"),
                    " for metadata and author the visible cover with ordinary unnumbered sections instead. That preserves a clean file property string while leaving the page design fully under document control."
                ),
            ),
        ),
        Chapter(
            "Document Model",
            Section(
                "Blocks define the visible structure",
                Paragraph(
                    "A good rule is: use classes for visible structure and helpers for inline emphasis. Blocks such as ",
                    inline_code("Part"),
                    ", ",
                    inline_code("Chapter"),
                    ", ",
                    inline_code("Section"),
                    ", ",
                    inline_code("Table"),
                    ", and ",
                    inline_code("Figure"),
                    " make the document outline obvious when reading the source."
                ),
                Paragraph(
                    "That explicitness matters most in large edits. During review, a collaborator can skim the object tree and understand where a figure belongs or where a generated page is inserted without first running the script."
                ),
                Paragraph(
                    inline_code("Part"),
                    " is for book-like divisions above chapters. It gets its own separator page and a Roman label such as ",
                    inline_code("Part I"),
                    ", while chapter numbering continues as 1, 2, 3 across later parts."
                ),
                CodeBlock(PART_STRUCTURE_SNIPPET, language="python"),
                Paragraph(
                    inline_code("Appendix"),
                    " is for end matter that needs LaTeX-style appendix numbering. The appendix separator is unnumbered by default, while child chapters render as A, B, C and can be referenced with those labels."
                ),
                CodeBlock(APPENDIX_STRUCTURE_SNIPPET, language="python"),
                generated_content_table,
            ),
            Section(
                "Numbered statements, proofs, and custom counters",
                Paragraph(
                    "Research notes, specifications, and technical manuals often need blocks such as definitions, lemmas, theorems, examples, remarks, and assumptions. These are not headings because they should usually stay inside the current section, but they still need document-wide numbering and cross-references."
                ),
                Paragraph(
                    "OODocs handles those cases with ",
                    inline_code("CountableBlock"),
                    " and the factory ",
                    inline_code("create_countable_block_type(...)"),
                    ". The built-in theorem-like classes share the ",
                    inline_code("theorem"),
                    " counter, while ",
                    inline_code("Proof(...)"),
                    " is unnumbered by default. If an unnumbered block needs a reference, give the reference an explicit label."
                ),
                counted_definition,
                Lemma("A theorem-like block can appear between ordinary paragraphs without becoming a section heading."),
                counted_theorem,
                Proof(
                    "Proofs are intentionally unnumbered by default, but they remain normal blocks and can contain paragraphs, lists, equations, tables, or figures when needed."
                ),
                Example("Examples continue the theorem-like counter, so they can be cited consistently in prose."),
                Remark("Remarks use the same numbering surface when a document wants one shared mathematical sequence."),
                counted_assumption,
                counted_exercise,
                Paragraph(
                    "For example, ",
                    counted_theorem.reference(),
                    " can be cited after the block is inserted, while the exercise above uses a separate custom sequence."
                ),
                CodeBlock(COUNTABLE_BLOCK_SNIPPET, language="python"),
            ),
            Section(
                "Inline annotations stay local to the prose",
                Paragraph(
                    "Inline helpers are deliberately direct. Use ",
                    inline_code("bold(...)"),
                    ", ",
                    inline_code("inline_code(...)"),
                    ", hyperlinks, comments such as ",
                    Comment.annotated("reviewable phrases", "This note will show up again on the generated comments page."),
                    ", and notes such as ",
                    Footnote.annotated(
                        "portable footnotes",
                        "Portable footnotes are authored inline so the prose remains readable in Python. The visible placement depends on renderer capabilities.",
                    ),
                    " exactly where the text appears."
                ),
                Paragraph(
                    "Word-style direct formatting is available without leaving the document tree. Use ",
                    inline_code("highlight(...)"),
                    " for reviewer focus, ",
                    inline_code("strikethrough(...)"),
                    " for deleted or superseded language, and ",
                    inline_code("line_break()"),
                    " for a Shift+Enter-style break inside the same paragraph. ",
                    inline_code("Text.styled(...)"),
                    " also accepts Word-native inline features such as ",
                    inline_code("small_caps"),
                    ", ",
                    inline_code("uppercase"),
                    ", ",
                    inline_code("subscript"),
                    ", and ",
                    inline_code("superscript"),
                    ". For front scripts in ordinary prose, use ",
                    inline_code("prescript(...)"),
                    " instead of wrapping the sentence in math."
                ),
                Paragraph(
                    "Inline text can carry ordinary scripts such as H",
                    subscript("2"),
                    "O and x",
                    superscript("2"),
                    ", plus front scripts like ",
                    prescript("14", "6", "C"),
                    ".",
                ),
                CodeBlock(INLINE_WORD_FEATURES_SNIPPET, language="python"),
                Paragraph(
                    "Compact inline chips cover categories, counts, states, and keys: ",
                    tag("api"),
                    " ",
                    badge("3 notes"),
                    " ",
                    status("ready", state="success"),
                    " ",
                    keyboard("Ctrl+Enter"),
                    ". DOCX renders each chip as a small inline image while PDF and HTML keep text in styled spans."
                ),
                CodeBlock(INLINE_CHIPS_SNIPPET, language="python"),
                Paragraph(
                    "Code blocks use Pygments highlighting, so the same renderer path can handle Python, JavaScript, SQL, YAML, shell snippets, and many other languages without adding language-specific document objects."
                ),
                CodeBlock(JAVASCRIPT_SNIPPET, language="javascript"),
                CodeBlock(SQL_SNIPPET, language="sql"),
                CodeBlock(YAML_SNIPPET, language="yaml"),
                Paragraph(
                    "Paragraph-level Word features are also part of the authored source. ",
                    inline_code("Paragraph(...)"),
                    " accepts explicit alignment, spacing before and after, left and right indents, first-line indents, hanging indents, and keep/page-break controls for reference-like blocks that should not be simulated with spaces. Use ",
                    inline_code("Theme(blocks=BlockDefaults(...))"),
                    " for the document-wide default and direct kwargs such as ",
                    inline_code("text_alignment='right'"),
                    " only where one paragraph should diverge."
                ),
                CodeBlock(PARAGRAPH_INDENT_SNIPPET, language="python"),
                Paragraph(
                    "Table cells can use the same sort of explicit alignment that authors expect from Word. Put one-off alignment on ",
                    inline_code("TableCell"),
                    ", or use ",
                    inline_code("Table(...)"),
                    " kwargs to set table-wide body and header defaults including borders, per-side cell padding, repeated headers, and alignment. For row, header-row, or column formatting, pass small dictionaries to ",
                    inline_code("row_styles"),
                    ", ",
                    inline_code("header_row_styles"),
                    ", or ",
                    inline_code("column_styles"),
                    "."
                ),
                CodeBlock(TABLE_ALIGNMENT_SNIPPET, language="python"),
                Paragraph(
                    "For publication-style tables comparable to LaTeX ",
                    inline_code("booktabs"),
                    ", use the built-in ",
                    inline_code('style="booktabs"'),
                    " preset, or build a custom ",
                    inline_code("TableStyle"),
                    " with ",
                    inline_code("top_rule"),
                    ", ",
                    inline_code("header_rule"),
                    ", and ",
                    inline_code("bottom_rule"),
                    "."
                ),
                CodeBlock(BOOKTABS_TABLE_SNIPPET, language="python"),
                Paragraph(
                    "That local authorship pattern is also why the guide can stay detailed without becoming confusing. The content reads like a normal reference document, but the source remains inspectable because the formatting instructions are still attached to the words they affect."
                ),
            ),
        ),
        ),
        Part(
            "Authoring Reference",
            Chapter(
                "Tables, Figures, and Cross-References",
            Section(
                "Media objects should stay attached to evidence",
                Paragraph(
                    "Tables and figures become much easier to trust when they are declared as document objects instead of exported manually. A captioned block can also be referenced from prose by inserting the block object itself inside a paragraph."
                ),
                media_workflow_table,
                Paragraph(
                    "That block-reference behavior is especially helpful in late revisions. When the order of figures or tables changes, the text stays synchronized because references resolve against the indexed caption numbers rather than a hard-coded label."
                ),
                Paragraph(
                    "Document-wide labels are configurable separately for captions and prose references. For example, a document can caption blocks as ",
                    inline_code("Figure"),
                    " while referring to them as ",
                    inline_code("Fig."),
                    ", or use localized labels such as ",
                    inline_code("그림"),
                    "."
                ),
                Paragraph(
                    "When several related images should share one figure number, use ",
                    inline_code("SubFigure"),
                    " children inside a ",
                    inline_code("SubFigureGroup"),
                    ". Each child receives an automatic ",
                    inline_code("(a)"),
                    ", ",
                    inline_code("(b)"),
                    " label and can be referenced from prose."
                ),
                CodeBlock(SUBFIGURE_SNIPPET, language="python"),
            ),
            Section(
                "Use figures to explain the authoring model, not just decorate it",
                Paragraph(
                    "The diagrams in this guide are intentionally explanatory. ",
                    pipeline_figure.reference(),
                    " captures the project-level data flow, while ",
                    author_layout_figure.reference(),
                    " explains how the same metadata can support multiple presentation styles."
                ),
                renderer_behavior_figure,
                Paragraph(
                    "Likewise, ",
                    renderer_behavior_figure.reference(),
                    " is not decorative. It surfaces the concrete behavior differences a user needs to know before choosing which output to send to collaborators."
                ),
            ),
            Section(
                "Advanced placement and long tables",
                Paragraph(
                    "Authors normally decide whether a table may be split, not whether it is a normal table or a long table. With ",
                    inline_code("Table(split=False)"),
                    ", oodocs keeps a short table together and lets PDF place following prose before the table when that avoids an awkward blank page. Very long tables automatically switch to repeated-header split rendering. With ",
                    inline_code("Table(split=True)"),
                    ", the table behaves like a here-placed object that can break in source order."
                ),
                Paragraph(
                    "Tables and figures also accept advanced ",
                    inline_code("placement"),
                    " hints such as ",
                    inline_code("'tbp'"),
                    ", ",
                    inline_code("'top'"),
                    ", and ",
                    inline_code("'page'"),
                    " for users who need more direct control over renderer placement."
                ),
                media_placement_table,
                CodeBlock(TABLE_PLACEMENT_SNIPPET, language="python"),
            ),
        ),
        Chapter(
            "Notes, Comments, and References",
            Section(
                "Footnotes and comments",
                Paragraph(
                    "Footnotes are meant for reader-facing context, while comments are for review-facing discussion. The two features are authored in the same inline style but flow to different places in the rendered outputs."
                ),
                Paragraph(
                    "The most important recent behavior change is that page-footnote placement is the default target when the renderer can support it. In practice that means DOCX uses native footnotes, while PDF and HTML fall back to a generated notes page because they do not share Word's native footnote mechanism."
                ),
                Paragraph(
                    "If you want the explicit collected-notes behavior everywhere, set ",
                    inline_code("Theme(blocks=BlockDefaults(footnote_placement='document'))"),
                    ".",
                ),
                CodeBlock(LAYOUT_CONTROL_SNIPPET, language="python"),
            ),
            Section(
                "Citations and bibliography output",
                Paragraph(
                    "Citations work the same way as table and figure references: keep them attached to the prose. The repository itself can be cited as ",
                    RELATED_WORK.cite("repository"),
                    ", which is useful when a guide or report needs to point back to the implementation source directly."
                ),
                Paragraph(
                    "Only cited sources are rendered on the final references page. That keeps the bibliography stable even when a project carries a larger citation library than any single document uses."
                ),
                Paragraph(
                    "The visible style is configured on the theme: ",
                    inline_code('Theme(citations=CitationDefaults(...))'),
                    " switches inline citations to author-year labels and formats the generated references entries in APA-style order."
                ),
            ),
        ),
        Chapter(
            "Layout and Pagination",
            Section(
                "What the theme controls",
                Paragraph(
                    "Theme is where renderer-neutral layout defaults live: heading numbering, list markers, page numbers, caption positions, caption/reference labels, author alignment, and footnote placement strategy. The goal is to keep document-wide choices together so a document does not accumulate hidden style decisions."
                ),
                Paragraph(
                    "The common override path is intentionally shallow: pass a direct keyword argument to the block when the choice is local, use a reusable style object when the same visual treatment repeats, and use a grouped ",
                    inline_code("Theme"),
                    " option object when the default should apply across the whole document."
                ),
                renderer_rules_table,
            ),
            Section(
                "Configuration option reference",
                Paragraph(
                    "Most author-facing options are available as ordinary keyword arguments. Style objects remain available for reusable patterns, and grouped ",
                    inline_code("Theme"),
                    " defaults objects keep document-wide settings readable when many values change together. Pass those defaults objects positionally to ",
                    inline_code("Theme"),
                    ", and use direct ",
                    inline_code("Theme(...)"),
                    " keyword arguments for one-off overrides."
                ),
                settings_options_table,
                theme_options_table,
                block_options_table,
                CodeBlock(CONFIGURATION_OPTIONS_SNIPPET, language="python"),
            ),
            Section(
                "Page size, margins, and explicit breaks",
                Paragraph(
                    "Page geometry belongs in ",
                    inline_code("DocumentSettings"),
                    " rather than in individual renderer calls. Use ",
                    inline_code("PageSize"),
                    " for the physical page, ",
                    inline_code("PageMargins"),
                    " for the printable area, and ",
                    inline_code("unit"),
                    " to make numeric dimensions read naturally for the document."
                ),
                page_layout_table,
                Paragraph(
                    "Explicit pagination is a block-level decision. Insert ",
                    inline_code("PageBreak()"),
                    " where the authored flow should move to the next page; generated pages can still use ",
                    inline_code("Theme(generated_content=GeneratedContentDefaults(...))"),
                    " for automatic separation."
                ),
                CodeBlock(LAYOUT_CONTROL_SNIPPET, language="python"),
            ),
            Section(
                "Contents hierarchy and page labels",
                Paragraph(
                    "The generated contents, table-list, and figure-list pages use hierarchy-aware or caption-aware spacing by default. In paginated DOCX and PDF output they also render page labels with dotted leaders, which is the common book/report convention where the entry text sits on the left and the page number aligns on the right. HTML keeps the same information as clean link-only navigation because browsers do not expose stable rendered page labels."
                ),
                Paragraph(
                    "Use ",
                    inline_code("TableOfContents"),
                    ", ",
                    inline_code("ListOfTables"),
                    ", and ",
                    inline_code("ListOfFigures"),
                    " options when the document needs a shorter outline, no page numbers, or a different per-level visual rhythm."
                ),
                contents_style_table,
                CodeBlock(CONTENTS_CONTROL_SNIPPET, language="python"),
                Subsection(
                    "Subsection entries",
                    Paragraph(
                        "This subsection is included as a live example of a third-level heading. It should appear in the contents below the section with normal font weight and a deeper indent."
                    ),
                    SubSubsection(
                        "Fourth-level section entries",
                        Paragraph(
                            "This fourth-level heading gives the contents page one more depth to render, which makes hierarchy checks easier in examples and tests."
                        ),
                    ),
                ),
            ),
            Section(
                "Figure sizing from document geometry",
                Paragraph(
                    "Figures accept ",
                    inline_code("width"),
                    ", ",
                    inline_code("height"),
                    ", or both. If only one dimension is set, renderers preserve the image aspect ratio. If both are set, the figure is placed into the explicit box."
                ),
                Paragraph(
                    "For LaTeX-like sizing relative to the text block, compute the length before constructing the figure. The common pattern is ",
                    inline_code("width=settings.get_text_width(0.75)"),
                    ", which reads as '75 percent of the current text width' while still producing a plain numeric width."
                ),
                figure_sizing_table,
                CodeBlock(FIGURE_SIZING_SNIPPET, language="python"),
            ),
            Section(
                "Positioned and inline drawing objects",
                Paragraph(
                    "Use ",
                    inline_code("DocumentSettings(page_items=...)"),
                    " for page-positioned shapes, text boxes, and image boxes that should not push body text around. Use ",
                    inline_code("placement='inline'"),
                    " when the same object should behave more like directly inserted Word media."
                ),
                Paragraph(
                    "Inline image example: ",
                    ImageBox(LOGO_PATH, width=0.28, height=0.28, placement="inline"),
                    " stays in the sentence flow, while page items stay independent of the paragraph layout."
                ),
                drawing_placement_table,
                CodeBlock(POSITIONED_DRAWING_SNIPPET, language="python"),
            ),
            Section(
                "Report panels for structured forms",
                Paragraph(
                    "Most report layouts should remain editable document structure. For tcolorbox-like panels, callouts, and form sections, use ",
                    inline_code("Box"),
                    " with explicit width, padding, colors, and alignment before reaching for fixed-position page graphics. That keeps Word output reviewable while PDF and HTML keep the same grouping intent."
                ),
                contributor_certificate,
                CodeBlock(REPORT_PANEL_SNIPPET, language="python"),
            ),
            Section(
                "What changed in the default document feel",
                Paragraph(
                    "The generated contents page now separates top-level chapters more clearly so readers can distinguish chapters, sections, and deeper levels at a glance. Captions are also kept visually closer to their table or figure so page breaks are less likely to strand a label away from the object it describes."
                ),
                Paragraph(
                    "Those changes matter because oodocs is not trying to imitate a notebook export. It should read like an intentionally typeset document even when the source stays fully programmable."
                ),
            ),
        ),
        Chapter(
            "Project Structure and Scaling Up",
            Section(
                "When to split a single file",
                Paragraph(
                    "Start with one file and only split when real repetition appears. The object tree is the most valuable teaching tool in a new project, so it should remain visible until helper functions provide a clear readability gain."
                ),
                scaling_table,
            ),
            Section(
                "Repository layout that stays review-friendly",
                Paragraph(
                    "A healthy document repository keeps authored source, reusable assets, structured data, and generated artifacts separate. That keeps commits readable and makes it easier to review whether a table changed because the data changed or because the document layout changed."
                ),
                CodeBlock(PROJECT_LAYOUT_SNIPPET, language="text", show_language=False),
                Paragraph(
                    "The journal example at ",
                    inline_code("examples/journal_paper_example/main.py"),
                    " follows the same pattern with CSV-backed tables, generated figures, and a manuscript body authored from one readable script."
                ),
            ),
            Section(
                "Build and validate from the CLI",
                Paragraph(
                    "The command-line interface is for the point where a document becomes part of a release process, CI job, or repeatable local workflow. It deliberately stays thin over the same workflow API that Python callers can import, so command behavior and library behavior do not drift apart."
                ),
                cli_workflow_figure,
                Paragraph(
                    "Use ",
                    inline_code("oodocs build"),
                    " when the source file is Python and exposes a ",
                    inline_code("Document"),
                    " as ",
                    inline_code("document"),
                    ", ",
                    inline_code("doc"),
                    ", ",
                    inline_code("report"),
                    ", or a zero-argument factory such as ",
                    inline_code("build_document()"),
                    ". The same ",
                    inline_code("oodocs build"),
                    " command also imports Markdown and notebooks. Use ",
                    inline_code("oodocs validate"),
                    " when CI should stop before any renderer writes files."
                ),
                cli_command_table,
                CodeBlock(CLI_WORKFLOW_SNIPPET, language="powershell"),
                Paragraph(
                    "A Python source file for ",
                    inline_code("oodocs build"),
                    " should keep construction and rendering separate. That makes the same source easy to import from tests, validate in CI, or render locally."
                ),
                CodeBlock(PYTHON_BUILD_SOURCE_SNIPPET, language="python"),
                validation_table,
                Paragraph(
                    "Validation returns a structured result object. Printing it produces a table for humans, while code can still branch on ",
                    inline_code("result.ok"),
                    ", ",
                    inline_code("result.errors_for(('pdf',))"),
                    ", or ",
                    inline_code("result.warnings_for(('html',))"),
                    ". Rendering methods call validation by default and stop before writing outputs when errors apply to the requested formats."
                ),
                CodeBlock(VALIDATION_SNIPPET, language="python"),
            ),
            Section(
                "Import Markdown when it is already the source of record",
                Paragraph(
                    "Markdown import is meant for handoff points: release notes, README fragments, generated changelog sections, and issue summaries that already exist as Markdown. Use ",
                    inline_code("Document.from_markdown(...)"),
                    " when the Markdown should become a document, and ",
                    inline_code("parse_markdown(...)"),
                    " when the imported blocks should be rearranged inside a larger Python-authored report."
                ),
                Paragraph(
                    "Because parsed Markdown becomes normal OODocs objects, several release-note bodies can be collected, counted, wrapped in ",
                    inline_code("Section"),
                    " objects, combined with a summary ",
                    inline_code("Table"),
                    ", and exported with the same DOCX, PDF, and HTML renderers as hand-authored content."
                ),
                CodeBlock(MARKDOWN_RELEASE_NOTES_SNIPPET, language="python"),
            ),
            Section(
                "Import notebooks without turning them into screenshots",
                Paragraph(
                    "Jupyter notebooks can enter the same workflow through ",
                    inline_code("Document.from_notebook(...)"),
                    " or ",
                    inline_code("parse_notebook(...)"),
                    ". Markdown cells become normal document structure, code cells become ",
                    inline_code("CodeBlock"),
                    " objects, and textual outputs can be included for audit trails or omitted when the report should only carry the authored code."
                ),
                Paragraph(
                    "The useful pattern is to keep exploratory notebooks as inputs, then wrap selected imported notebook sections in a report that also contains narrative, tables, figures, references, and generated pages."
                ),
                CodeBlock(NOTEBOOK_IMPORT_SNIPPET, language="python"),
            ),
        ),
        ),
        Part(
            "Presets and Templates",
            Chapter(
                "Component Presets",
                Section(
                    "Reusable components keep the core API visible",
                    Paragraph(
                        "Component presets live under ",
                        inline_code("oodocs.presets.components"),
                        ". They are intentionally thin wrappers around ordinary blocks, so a user can start with ",
                        inline_code("CalloutBox"),
                        ", ",
                        inline_code("KeyValueTable"),
                        ", or ",
                        inline_code("Nomenclature"),
                        " and still pass familiar kwargs such as ",
                        inline_code("padding"),
                        ", ",
                        inline_code("cell_padding"),
                        ", ",
                        inline_code("border"),
                        ", and ",
                        inline_code("column_widths"),
                        ".",
                    ),
                    component_presets_table,
                    preset_callout,
                    preset_metadata_table,
                    preset_nomenclature,
                    CodeBlock(COMPONENT_PRESETS_SNIPPET, language="python"),
                ),
            ),
            Chapter(
                "Template Presets",
                Section(
                    "Templates build complete documents from manuscript-shaped input",
                    Paragraph(
                        "Template presets live under ",
                        inline_code("oodocs.presets.templates"),
                        ". The generic journal template owns the routine article scaffolding so callers usually fill content fields rather than theme details. The build input stays small: title, authors, abstract, keywords, body sections, optional acknowledgement and data availability statements, and citation data. Publisher-specific presets are intentionally not included because broad public guidance is not the same thing as a journal-specific template. The included example uses common manuscript elements that appear in Elsevier's general Your Paper Your Way guidance ",
                        RELATED_WORK.cite("elsevier-your-paper-your-way"),
                        " and Taylor & Francis Author Services guidance ",
                        RELATED_WORK.cite("taylor-francis-layout-guide"),
                        ", while still treating the target journal's Instructions for Authors as authoritative ",
                        RELATED_WORK.cite("taylor-francis-instructions"),
                        "."
                    ),
                    Paragraph(
                        inline_code("JournalArticleTemplate"),
                        " accepts existing ",
                        inline_code("Section"),
                        " blocks, compact ",
                        inline_code("ManuscriptSection"),
                        " descriptors, or simple ",
                        inline_code("(title, children)"),
                        " tuples for the body."
                    ),
                    template_presets_table,
                    CodeBlock(TEMPLATE_PRESETS_SNIPPET, language="python"),
                ),
            ),
        ),
        CommentList(),
        ReferenceList(),
        settings=DocumentSettings(
            metadata_author="OODocs Contributors",
            summary="Detailed usage guide and API walkthrough",
            subtitle="Reference-style guide for structured Python document authoring",
            authors=[
                Author("OODocs Contributors"),
                Author("Hyeong-Gon Jo"),
            ],
            author_layout=AuthorLayout(
                mode="stacked",
                show_affiliations=False,
                show_details=False,
            ),
            page_margins=PageMargins.symmetric(vertical=2.0, horizontal=2.2, unit="cm"),
            theme=Theme(
                page_numbers=PageNumberDefaults(
                    show_page_numbers=True,
                    page_number_template="{page}",
                ),
                blocks=BlockDefaults(footnote_placement="page"),
            ),
        ),
        citations=RELATED_WORK,
    )


def build_usage_guide(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Build the usage guide example and export selected formats."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    document = build_usage_guide_document()
    formats = tuple(output_formats or ("docx", "pdf", "html"))
    return document.save_all(
        output_path,
        stem="oodocs-user-guide",
        formats=formats,
        verbose=verbose,
    )


def build_document() -> Document:
    """Return the renderable usage guide document."""

    return build_usage_guide_document()


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the usage guide through the common example interface."""

    return build_usage_guide(
        output_dir,
        output_formats=output_formats,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Build the guide from the command line."""

    parser = argparse.ArgumentParser(description="Render the OODocs usage guide example.")
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

    outputs = build_usage_guide(
        args.output_dir,
        output_formats=args.output_formats,
        verbose=not args.quiet,
    )
    if not args.quiet:
        for output_format, path in outputs:
            print(f"Wrote {output_format}: {path}")


if __name__ == "__main__":
    main()
