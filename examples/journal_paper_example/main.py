"""Standalone journal paper example for oodocs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from oodocs import (
    Affiliation,
    Author,
    BulletList,
    CitationDefaults,
    ColumnSpan,
    CitationLibrary,
    CitationSource,
    Document,
    DocumentSettings,
    Figure,
    MultiColumn,
    OutputBundle,
    PageNumberDefaults,
    Paragraph,
    ReferenceList,
    Section,
    Table,
    Theme,
    inline_code,
    italic,
)


OUTPUT_DIR = Path("artifacts") / "journal-paper"
EXAMPLE_DIR = Path(__file__).resolve().parent
ASSET_DIR = EXAMPLE_DIR / "assets"
RESULTS_CSV_PATH = ASSET_DIR / "benchmark_results.csv"
ABLATION_CSV_PATH = ASSET_DIR / "ablation_results.csv"
TRACEABILITY_DIAGRAM_PATH = ASSET_DIR / "traceability-diagram.png"


def build_quality_latency_figure(results_df: pd.DataFrame):
    """Plot the quality-latency frontier from the benchmark CSV."""

    figure, axis = plt.subplots(figsize=(3.6, 2.8))
    palette = ["#6C8DB0", "#4F8DA1", "#3F9D79", "#D07B42"]
    axis.scatter(results_df["Latency_ms"], results_df["Accuracy"], s=80, c=palette, edgecolors="#173042", linewidths=0.8)
    axis.plot(results_df["Latency_ms"], results_df["Accuracy"], color="#7B8E9E", linestyle="--", linewidth=1.1)
    labels = {
        "Baseline": "Base",
        "StructuredDoc": "Doc",
        "StructuredDoc+Review": "Review",
        "StructuredDoc+Review+Checks": "Checks",
    }
    offsets = {
        "Baseline": (8, 8),
        "StructuredDoc": (0, 9),
        "StructuredDoc+Review": (0, 9),
        "StructuredDoc+Review+Checks": (-8, 9),
    }
    for _, row in results_df.iterrows():
        offset = offsets[row["Model"]]
        axis.annotate(
            labels[row["Model"]],
            (row["Latency_ms"], row["Accuracy"]),
            textcoords="offset points",
            xytext=offset,
            ha="right" if offset[0] < 0 else "center",
            fontsize=7.0,
            color="#173042",
        )
    axis.set_xlabel("Latency (ms)", fontsize=7.5)
    axis.set_ylabel("Accuracy", fontsize=7.5)
    axis.set_xlim(40, 66)
    axis.set_ylim(0.865, 0.95)
    axis.set_title("Quality vs Latency", fontsize=8.5)
    axis.tick_params(labelsize=6.8)
    axis.grid(alpha=0.25, linestyle=":")
    figure.tight_layout()
    return figure


def build_revision_effort_figure():
    """Plot the expected synchronization effort during late revisions."""

    revision_rounds = [1, 2, 3, 4]
    manual_minutes = [36, 49, 63, 79]
    oodocs_minutes = [18, 21, 25, 29]

    figure, axis = plt.subplots(figsize=(3.4, 2.8))
    axis.plot(revision_rounds, manual_minutes, marker="o", linewidth=1.8, color="#D06A44", label="Manual")
    axis.plot(revision_rounds, oodocs_minutes, marker="o", linewidth=1.8, color="#3F8F6B", label="OODocs")
    axis.fill_between(revision_rounds, oodocs_minutes, manual_minutes, color="#F6D8CB", alpha=0.45)
    axis.set_xlabel("Late revision round", fontsize=7.5)
    axis.set_ylabel("Minutes per update", fontsize=7.5)
    axis.set_xticks(revision_rounds)
    axis.set_title("Cost of Late Revisions", fontsize=8.5)
    axis.legend(frameon=False, fontsize=6.8)
    axis.tick_params(labelsize=6.8)
    axis.grid(alpha=0.25, linestyle=":")
    figure.tight_layout()
    return figure


def build_journal_paper_document() -> Document:
    """Build an example journal-style manuscript."""

    results_df = pd.read_csv(RESULTS_CSV_PATH)
    ablation_df = pd.read_csv(ABLATION_CSV_PATH)
    dataset_df = pd.DataFrame(
        [
            ["Training", 18420, "system logs + editorial metadata"],
            ["Validation", 2400, "held-out internal documents"],
            ["Test", 2600, "blind review split"],
        ],
        columns=["Split", "Documents", "Source"],
    )

    manuscript_sources = CitationLibrary(
        [
            CitationSource(
                "Literate Programming",
                key="literate-programming",
                authors=("D. E. Knuth",),
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

    dataset_table = Table.from_dataframe(
        dataset_df,
        caption="Study corpus used to evaluate the manuscript workflow.",
        column_widths=[1.2, 1.2, 3.2],
        header_background_color="#E7EEF7",
        alternate_row_background_color="#FAFCFE",
    )
    benchmark_table = Table.from_dataframe(
        results_df[["Model", "Accuracy", "F1", "Latency_ms"]],
        caption="Benchmark results loaded directly from the experiment CSV file.",
        column_widths=[2.0, 1.0, 0.9, 1.3],
        header_background_color="#DCE8F4",
        alternate_row_background_color="#F7FAFD",
    )
    ablation_table = Table.from_dataframe(
        ablation_df,
        caption="Ablation results for the manuscript automation workflow.",
        column_widths=[2.9, 1.0, 1.2],
        header_background_color="#E3ECF6",
        alternate_row_background_color="#F8FBFD",
    )

    traceability_figure = Figure(
        TRACEABILITY_DIAGRAM_PATH,
        caption=Paragraph(
            "Traceability pipeline used in the study, linking evidence sources, authored structure, checks, and submission outputs."
        ),
        width=6.2,
    )
    quality_latency_figure = Figure(
        build_quality_latency_figure(results_df),
        caption=Paragraph(
            "Quality-latency frontier derived directly from the benchmark CSV used in the manuscript."
        ),
        width=2.7,
        placement="here",
    )
    revision_effort_figure = Figure(
        build_revision_effort_figure(),
        caption=Paragraph(
            "Estimated late-revision synchronization effort comparing manual workflows with an OODocs-based workflow."
        ),
        width=2.7,
        placement="here",
    )

    return Document(
        "OODocs Development Philosophy",
        Section(
            "Abstract",
            Paragraph(
                "This example models a journal submission workflow in which prose, tables, figures, and citations are assembled from ordinary Python code. Benchmark tables are loaded from CSV files with ",
                inline_code("pandas.read_csv"),
                ", benchmark figures are generated with ",
                inline_code("matplotlib"),
                ", and DOCX, PDF, and HTML outputs are rendered from the same source document. The workflow follows the reproducibility discipline discussed in ",
                manuscript_sources.cite("reproducible-research"),
                ".",
            ),
            Paragraph(
                "The paper argues for a practical authoring pattern rather than a new publishing format. The central claim is that keeping manuscript structure downstream of the evidence reduces synchronization mistakes during late revisions and makes document review easier to trust."
            ),
            Paragraph(
                italic("Keywords: "),
                "scientific reporting, document automation, reproducible workflows, Python",
            ),
            level=2,
            numbered=False,
        ),
        Section(
            "Highlights",
            BulletList(
                "Journal-style title matter can be authored from structured metadata without giving up customization paths.",
                "Tables and figures can be regenerated from the same Python inputs that support the manuscript claims.",
                "The strongest workflow benefit appears during late revisions, when synchronization cost usually rises fastest.",
            ),
            level=2,
            numbered=False,
        ),
        MultiColumn(
            Section(
                "Introduction",
                Paragraph(
                    "Research manuscripts often combine at least four moving parts: benchmark tables, static diagrams, generated plots, and conventional prose. In many teams those assets are edited in different tools, which creates avoidable synchronization work every time a metric, caption, or section ordering changes."
                ),
                Paragraph(
                    "The practical difficulty is not that any single asset is hard to regenerate. The difficulty is that small mismatches accumulate across captions, references, tables, review copies, and exported figures. A paper can therefore look polished while still hiding several manual edits that no longer correspond to the source evidence."
                ),
                Paragraph(
                    "The workflow studied here treats the manuscript itself as code. That does not eliminate editorial work, but it does move the document closer to the data that supports it, which is the operational direction already suggested by ",
                    manuscript_sources.cite("literate-programming"),
                    " and systems such as ",
                    manuscript_sources.cite("knitr"),
                    ".",
                ),
                Paragraph(
                    "This example focuses on the authoring layer rather than on a particular scientific domain. The same pattern could sit behind a methods note, a simulation study, or a benchmark report: load structured inputs, assemble explicit document blocks, and export the formats expected by collaborators and reviewers."
                ),
                level=1,
            ),
            Section("Workflow Design", level=1),
            Section(
                "Evidence Traceability",
                Paragraph(
                    "The study begins from a straightforward design requirement: every visible claim should remain traceable to either structured input data, a generated figure, or a cited source. ",
                    traceability_figure.reference(),
                    " summarizes the resulting workflow."
                ),
                Paragraph(
                    "The intent is not to force authors into a notebook-like page. Instead, the workflow preserves manuscript conventions such as abstract sections, captions, and editable review copies while keeping those conventions downstream of the evidence."
                ),
                Paragraph(
                    "Traceability is treated as a document property, not as a separate checklist. When a table number, figure caption, citation label, or exported file changes, the manuscript is regenerated from the same source graph. Reviewers can then inspect the visible prose while maintainers can inspect the code path that produced each referenced artifact."
                ),
                level=2,
            ),
            ColumnSpan(traceability_figure),
            Section(
                "Operational Rules",
                Paragraph(
                    "Three rules were enforced in the example manuscript. First, numeric tables must originate from structured data rather than hand-edited cells. Second, generated figures must be built from the same inputs that support the reported metric. Third, manuscript claims should cite a source or point to a table or figure wherever the argument depends on evidence."
                ),
                Paragraph(
                    "These rules are deliberately modest. They can be adopted in a small project without introducing a full experiment-tracking platform, yet they materially reduce the number of unreviewable document edits."
                ),
                Paragraph(
                    "The rules also keep the example close to ordinary writing practice. Authors still decide what claims matter, which caveats belong in the prose, and how much interpretation a figure needs. The automation only removes the repeated assembly steps that are easy to forget when a paper is revised under time pressure."
                ),
                Paragraph(
                    "A second constraint was readability of the source file. The document is written as a sequence of concrete blocks rather than through deeply nested helper functions, so a new contributor can scan the paper and understand where a paragraph, table, or figure enters the manuscript."
                ),
                level=2,
            ),
            Section("Study Assets", level=1),
            Paragraph(
                "The evaluation uses a small but realistic asset bundle: benchmark result CSV files, an ablation CSV, structured citation metadata, and an authored manuscript script. The corpus summary is shown in ",
                dataset_table.reference(),
                "."
            ),
            dataset_table,
            Paragraph(
                "The important point is not the corpus size by itself. The point is that the visible document objects and the supporting data remain connected through explicit code rather than through manual export steps."
            ),
            Paragraph(
                "The corpus table remains full-width because its descriptive source column benefits from horizontal space. Other evidence objects, especially compact plots, can sit inside a single manuscript column so the page feels like a real article instead of a sequence of full-width interruptions."
            ),
            Paragraph(
                "Input files are kept beside the example script so that the paper can be rebuilt without external services. That makes the example useful as a regression target: if a renderer changes table layout, image sizing, Citation styleting, or page flow, the generated paper exposes the change in every supported output format."
            ),
            Section("Results", level=1),
            Section(
                "Benchmark Frontier",
                Paragraph(
                    "The benchmark data in ",
                    benchmark_table.reference(),
                    " shows a steady quality gain as more structure is added to the workflow. The same CSV is also rendered into ",
                    quality_latency_figure.reference(),
                    ", which makes the trade-off between quality and latency easier to interpret during revision discussions."
                ),
                Paragraph(
                    "The relevant result is not merely the best final score. The more useful observation is that the quality improvement remains interpretable because the comparison table and the comparison plot are generated from the same underlying CSV."
                ),
                Paragraph(
                    "The full benchmark table is allowed to span both columns because the row labels and numeric columns benefit from horizontal space. The accompanying plot is smaller and can live inside one column, where it acts as a local visual summary rather than a page-level interruption."
                ),
                level=2,
            ),
            benchmark_table,
            quality_latency_figure,
            Section(
                "Ablation Signals",
                Paragraph(
                    "Ablation results are summarized in ",
                    ablation_table.reference(),
                    ". Removing table automation, citation checks, or asset reuse each weakens the final result, which supports the claim that the workflow benefit comes from coordinated authoring behavior rather than from any single isolated feature."
                ),
                Paragraph(
                    "The value of the ablation is conceptual as much as numeric: it demonstrates that manuscript reliability depends on several small pieces staying connected, including caption generation, citation handling, and predictable asset reuse."
                ),
                Paragraph(
                    "The ablation table stays full-width because its component labels are explanatory rather than symbolic. This gives the results section a more typical journal rhythm: prose, compact in-column plots, and occasional wide artifacts when the data genuinely needs the space."
                ),
                level=2,
            ),
            ablation_table,
            Section(
                "Late-Revision Cost",
                Paragraph(
                    "The workflow benefit becomes most visible late in the writing cycle. ",
                    revision_effort_figure.reference(),
                    " reports an estimated operational curve for repeated late updates. The estimate is intentionally approximate, but it captures a practical pattern: manual synchronization cost tends to rise more quickly than code-backed synchronization cost when the manuscript is revised several times close to submission."
                ),
                Paragraph(
                    "This type of figure matters because many workflow decisions are justified by revision logistics rather than by accuracy alone. Even when two pipelines can represent the same final content, the cheaper revision path is usually the one that survives into regular team use."
                ),
                Paragraph(
                    "The revision curve is not intended as a universal measurement. It is a compact model of a familiar editorial pattern: early changes are cheap, but late changes become expensive when authors must synchronize text, tables, captions, references, and exported files by hand."
                ),
                level=2,
            ),
            revision_effort_figure,
            Section(
                "Discussion",
                Paragraph(
                    "The example does not claim that every writing task should become a programming task. The stronger claim is narrower: when a project already depends on Python for data handling and figure generation, keeping the manuscript in the same environment improves traceability and usually reduces late-stage synchronization mistakes."
                ),
                Paragraph(
                    "There are still tradeoffs. A programmable manuscript requires some repository discipline, and teams unfamiliar with packaging or automated builds may need a small onboarding step. In return, they gain a workflow where visible manuscript changes can be reviewed with the same habits used for code changes."
                ),
                Paragraph(
                    "The multicolumn body is a useful stress test for this idea because article layout exposes awkward edges quickly. Figures that are too wide must escape the columns, compact evidence should remain near the relevant prose, and headings must keep their numbering even when the renderer changes the physical flow."
                ),
                Paragraph(
                    "For production use, a team would likely add project-specific checks around required statements, data availability language, and target journal preferences. Those checks can sit above the core block model without changing how paragraphs, figures, tables, and citations are assembled."
                ),
                level=1,
            ),
            Section(
                "Conclusion",
                Paragraph(
                    "This journal example shows OODocs at its most manuscript-oriented: structured authorship, data-backed tables, explanatory figures, and submission-ready exports are kept in one readable Python source. The result is not just reproducible output, but a document workflow that is easier to revise and easier to trust."
                ),
                Paragraph(
                    "The broader lesson is that document automation does not have to mean giving up familiar manuscript structure. It can instead make that structure cheaper to maintain, especially when the final paper must exist as DOCX, PDF, and HTML at the same time."
                ),
                level=1,
            ),
            columns=2,
            column_gap=0.28,
        ),
        Section(
            "Acknowledgements",
            Paragraph(
                "The authors thank the internal review group for feedback on figure clarity, manuscript structure, and release packaging decisions."
            ),
            level=2,
            numbered=False,
        ),
        ReferenceList(),
        settings=DocumentSettings(
            summary="Journal-style development philosophy paper",
            authors=[
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
                    corresponding=True,
                    email="gonie@example.org",
                    orcid="0009-0004-8821-275X",
                    note="GitHub: @Gonie-Gonie",
                ),
                Author(
                    "Codex",
                    affiliations=[Affiliation(organization="OpenAI")],
                    position="Coding Agent",
                    note="GitHub: openai/codex",
                ),
            ],
            theme=Theme(
                page_numbers=PageNumberDefaults(show_page_numbers=True, page_number_template="{page}"),
                citations=CitationDefaults(citation_style="apa", reference_style="apa"),
            ),
        ),
        citations=manuscript_sources,
    )


def build_journal_paper(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Build the journal paper example and export selected formats."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    document = build_journal_paper_document()
    formats = tuple(output_formats or ("docx", "pdf", "html"))
    return document.save_all(
        output_path,
        stem="oodocs-development-philosophy",
        formats=formats,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Build the paper from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs journal paper example.",
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

    outputs = build_journal_paper(
        args.output_dir,
        output_formats=args.output_formats,
        verbose=not args.quiet,
    )
    if not args.quiet:
        for output_format, path in outputs:
            print(f"Wrote {output_format}: {path}")


if __name__ == "__main__":
    main()
