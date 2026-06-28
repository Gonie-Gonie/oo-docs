"""Native Python benchmark report example for oodocs."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Sequence

from oodocs import (
    Chapter,
    CodeBlock,
    Document,
    DocumentSettings,
    NumberedList,
    OutputBundle,
    PageNumberDefaults,
    Paragraph,
    Section,
    Table,
    ListOfTables,
    TableOfContents,
    Theme,
    bold,
    inline_code,
)


OUTPUT_DIR = Path("artifacts") / "native-benchmark-report"
TRANSLATION_TABLE = str.maketrans({"-": " ", "_": " "})


def normalize_with_loop(text: str) -> str:
    pieces: list[str] = []
    previous_separator = True
    for character in text.casefold():
        if character.isalnum():
            pieces.append(character)
            previous_separator = False
        elif not previous_separator:
            pieces.append("_")
            previous_separator = True
    return "".join(pieces).strip("_")


def normalize_with_replace(text: str) -> str:
    return "_".join(text.casefold().replace("-", " ").replace("_", " ").split())


def normalize_with_translate(text: str) -> str:
    return "_".join(text.casefold().translate(TRANSLATION_TABLE).split())


NORMALIZERS = (
    ("character loop", normalize_with_loop),
    ("replace + split", normalize_with_replace),
    ("translate + split", normalize_with_translate),
)


def generate_payload(count: int = 1200) -> list[str]:
    owners = ("Alpha Team", "Beta Squad", "Core Platform", "Release Desk")
    verbs = ("Prepare", "Review", "Normalize", "Publish")
    objects = ("User Guide", "Benchmark Report", "Release Note", "API Draft")
    return [
        f"{verbs[index % 4]}-{objects[(index * 5) % 4]}_{owners[(index * 3) % 4]} item {index:04d}"
        for index in range(count)
    ]


def benchmark_normalizers(
    payload: list[str],
    repeat: int = 7,
    inner_iterations: int = 20,
) -> list[dict[str, float | str]]:
    results: list[dict[str, float | str]] = []

    for name, normalizer in NORMALIZERS:
        durations_ms: list[float] = []
        normalized = []

        for _ in range(repeat):
            start = perf_counter_ns()
            for _ in range(inner_iterations):
                normalized = [normalizer(value) for value in payload]
            durations_ms.append((perf_counter_ns() - start) / 1_000_000)

        checksum = sha256("\n".join(normalized).encode("utf-8")).hexdigest()[:12]
        results.append(
            {
                "name": name,
                "median_ms": median(durations_ms),
                "best_ms": min(durations_ms),
                "checksum": checksum,
            }
        )

    return sorted(results, key=lambda result: float(result["median_ms"]))


def build_benchmark_document() -> Document:
    payload = generate_payload()
    results = benchmark_normalizers(payload)
    best = results[0]
    slowest = results[-1]
    speedup = float(slowest["median_ms"]) / float(best["median_ms"])

    sample_rows = [
        [str(index + 1), value, normalize_with_translate(value)]
        for index, value in enumerate(payload[:5])
    ]
    benchmark_rows = [
        [
            str(index),
            str(result["name"]),
            f"{float(result['median_ms']):.3f}",
            f"{float(result['best_ms']):.3f}",
            f"{float(result['median_ms']) / float(best['median_ms']):.2f}x",
            str(result["checksum"]),
        ]
        for index, result in enumerate(results, start=1)
    ]

    pipeline_table = Table(
        headers=["Step", "Python value", "Document use"],
        rows=[
            ["1", "payload: list[str]", "Generated in memory by normal Python code."],
            ["2", "NORMALIZERS", "Three callables are benchmarked with the same loop."],
            ["3", "results: list[dict]", "Median time, best time, and checksum are kept as data."],
            ["4", "benchmark_rows", "The measured data becomes table rows."],
            ["5", "Document", "The report is exported to DOCX, PDF, and HTML."],
        ],
        caption="Serialized Python-to-document flow used by this example.",
        column_widths=[1.0, 3.8, 8.8],
        unit="cm",
        header_background_color="#E8F2EC",
        alternate_row_background_color="#FAFCFA",
    )
    sample_table = Table(
        headers=["#", "Input", "Normalized output"],
        rows=sample_rows,
        caption="Sample rows from the generated native Python workload.",
        column_widths=[0.8, 6.2, 6.8],
        unit="cm",
        header_background_color="#F1E7D9",
        alternate_row_background_color="#FFFCF8",
    )
    result_table = Table(
        headers=["Rank", "Implementation", "Median batch ms", "Best batch ms", "Vs best", "Checksum"],
        rows=benchmark_rows,
        caption="Native Python benchmark results converted directly from measured data.",
        column_widths=[1.1, 3.2, 2.4, 2.2, 1.8, 3.0],
        unit="cm",
        header_background_color="#E4EDF7",
        alternate_row_background_color="#F8FBFE",
    )

    return Document(
        "Native Python Benchmark Report",
        TableOfContents(max_level=2),
        ListOfTables(),
        Chapter(
            "Benchmark as a Document Workflow",
            Paragraph(
                "This example starts as ordinary Python work: generate input strings, run a few functions, "
                "measure them, and keep the results as normal Python data. The document is assembled after "
                "those values exist."
            ),
            pipeline_table,
            Section(
                "The serialized flow",
                NumberedList(
                    "Generate a deterministic in-memory payload.",
                    "Run each implementation over the same workload.",
                    "Keep timing and checksum values in dictionaries.",
                    "Turn those dictionaries into oodocs table rows and prose.",
                    "Render the same source document to DOCX, PDF, and HTML.",
                ),
            ),
        ),
        Chapter(
            "Workload",
            Paragraph(
                "The workload is intentionally small: text labels that are normalized into stable "
                "identifiers. In a real project this could be any Python-native task whose result should "
                "be reviewed as a report."
            ),
            sample_table,
            Section(
                "Implementation candidates",
                Paragraph(
                    "The candidates are ordinary functions. They are listed once in ",
                    inline_code("NORMALIZERS"),
                    ", then used by both the benchmark and the document narrative."
                ),
                CodeBlock(
                    "NORMALIZERS = (\n"
                    "    ('character loop', normalize_with_loop),\n"
                    "    ('replace + split', normalize_with_replace),\n"
                    "    ('translate + split', normalize_with_translate),\n"
                    ")",
                    language="python",
                ),
            ),
        ),
        Chapter(
            "Results",
            Paragraph(
                "The fastest candidate in this run was ",
                bold(str(best["name"])),
                " at ",
                inline_code(f"{float(best['median_ms']):.3f}"),
                " ms per measured batch. The slowest candidate took about ",
                inline_code(f"{speedup:.2f}x"),
                " as long on the same payload."
            ),
            result_table,
            Section(
                "Why the checksum is included",
                Paragraph(
                    "The checksum is a quick signal that the implementations produced the same normalized "
                    "batch. It is not a new abstraction; it is just another Python value carried into the "
                    "document."
                ),
            ),
        ),
        Chapter(
            "Reusing the Pattern",
            Paragraph(
                "The important part is the order of work. Do the Python task first, keep the measured or "
                "derived values in ordinary variables, then assemble the document from those values."
            ),
            CodeBlock(
                "payload = generate_payload()\n"
                "results = benchmark_normalizers(payload)\n"
                "document = build_benchmark_document()\n"
                "document.save_all('artifacts/native-benchmark-report', stem='native-python-benchmark')",
                language="python",
            ),
        ),
        settings=DocumentSettings(
            metadata_author="OODocs Contributors",
            subtitle="Documenting measured Python work without leaving Python",
            summary="Example report generated from native Python benchmark data",
            theme=Theme(
                page_numbers=PageNumberDefaults(
                    show_page_numbers=True,
                    page_number_template="{page}",
                )
            ),
        ),
    )


def build_native_benchmark_report(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Build the benchmark report example and export selected formats."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    formats = tuple(output_formats or ("docx", "pdf", "html"))
    return build_benchmark_document().save_all(
        output_path,
        stem="native-python-benchmark",
        formats=formats,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Build the benchmark report from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs native benchmark report example.",
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

    outputs = build_native_benchmark_report(
        args.output_dir,
        output_formats=args.output_formats,
        verbose=not args.quiet,
    )
    if not args.quiet:
        for output_format, path in outputs:
            print(f"Wrote {output_format}: {path}")


if __name__ == "__main__":
    main()
