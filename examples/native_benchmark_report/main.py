"""Native Python benchmark report example for oodocs."""

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import platform
from pathlib import Path
from statistics import median
import sys
from time import perf_counter_ns
from typing import Iterator, Sequence

from oodocs import (
    Chapter,
    CodeBlock,
    Document,
    DocumentMetadata,
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
    TitleMatter,
    bold,
    inline_code,
)


OUTPUT_DIR = Path("artifacts") / "native-benchmark-report"
OUTPUT_STEM = "native-python-benchmark"
DEFAULT_PAYLOAD_COUNT = 1200
DEFAULT_REPEAT = 7
DEFAULT_INNER_ITERATIONS = 20
TRANSLATION_TABLE = str.maketrans({"-": " ", "_": " "})


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Measured result for one normalization implementation."""

    name: str
    median_ms: float
    best_ms: float
    checksum: str

    def as_table_row(self, rank: int, best_ms: float) -> list[str]:
        """Convert the result into a rendered benchmark table row."""

        return [
            str(rank),
            self.name,
            f"{self.median_ms:.3f}",
            f"{self.best_ms:.3f}",
            f"{self.median_ms / best_ms:.2f}x",
            self.checksum,
        ]


@dataclass(frozen=True, slots=True)
class BenchmarkReportBundle:
    """Rendered benchmark report outputs plus the machine-readable sidecar."""

    rendered: OutputBundle
    results_json: Path

    def __iter__(self) -> Iterator[tuple[str, Path]]:
        """Iterate over rendered document outputs."""

        return iter(self.rendered)

    def __getitem__(self, output_format: str) -> Path:
        """Return the rendered path for an output format."""

        return self.rendered[output_format]

    def keys(self) -> tuple[str, ...]:
        """Return rendered output format keys."""

        return self.rendered.keys()

    def values(self) -> tuple[Path, ...]:
        """Return rendered output paths."""

        return self.rendered.values()

    def items(self) -> tuple[tuple[str, Path], ...]:
        """Return rendered output pairs."""

        return self.rendered.items()


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


def generate_payload(count: int = DEFAULT_PAYLOAD_COUNT) -> list[str]:
    owners = ("Alpha Team", "Beta Squad", "Core Platform", "Release Desk")
    verbs = ("Prepare", "Review", "Normalize", "Publish")
    objects = ("User Guide", "Benchmark Report", "Release Note", "API Draft")
    return [
        f"{verbs[index % 4]}-{objects[(index * 5) % 4]}_{owners[(index * 3) % 4]} item {index:04d}"
        for index in range(count)
    ]


def benchmark_normalizers(
    payload: list[str],
    repeat: int = DEFAULT_REPEAT,
    inner_iterations: int = DEFAULT_INNER_ITERATIONS,
) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []

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
            BenchmarkResult(
                name=name,
                median_ms=median(durations_ms),
                best_ms=min(durations_ms),
                checksum=checksum,
            )
        )

    return sorted(results, key=lambda result: result.median_ms)


def validate_benchmark_results(results: Sequence[BenchmarkResult]) -> None:
    """Validate benchmark results before documenting them."""

    if len(results) < 2:
        raise ValueError("At least two benchmark results are required.")
    checksums = {result.checksum for result in results}
    if len(checksums) != 1:
        raise ValueError("Benchmark implementations produced different checksums.")
    if any(result.median_ms <= 0 for result in results):
        raise ValueError("Benchmark median times must be positive.")


def benchmark_results_to_table(results: Sequence[BenchmarkResult]) -> Table:
    """Convert benchmark results into a rendered OODocs table."""

    validate_benchmark_results(results)
    best = results[0]
    benchmark_rows = [
        result.as_table_row(index, best.median_ms)
        for index, result in enumerate(results, start=1)
    ]
    return Table(
        headers=["Rank", "Implementation", "Median batch ms", "Best batch ms", "Vs best", "Checksum"],
        rows=benchmark_rows,
        caption="Native Python benchmark results converted directly from measured data.",
        column_widths=[1.1, 3.2, 2.4, 2.2, 1.8, 3.0],
        unit="cm",
        header_background_color="#E4EDF7",
        alternate_row_background_color="#F8FBFE",
    )


def benchmark_environment_rows(
    payload_count: int,
    repeat: int,
    inner_iterations: int,
) -> list[list[str]]:
    """Return execution metadata rows for the benchmark report."""

    return [
        ["Python version", sys.version.split()[0]],
        ["Platform", platform.platform()],
        ["Repeat count", str(repeat)],
        ["Inner iterations", str(inner_iterations)],
        ["Payload size", str(payload_count)],
        ["Hash algorithm", "SHA-256 truncated to 12 hex characters"],
    ]


def write_benchmark_sidecar(
    output_dir: str | Path,
    results: Sequence[BenchmarkResult],
    *,
    payload_count: int,
    repeat: int,
    inner_iterations: int,
) -> Path:
    """Write benchmark results and environment metadata as JSON."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sidecar_path = output_path / f"{OUTPUT_STEM}.json"
    payload = {
        "payload_count": payload_count,
        "repeat": repeat,
        "inner_iterations": inner_iterations,
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "hash_algorithm": "sha256",
        },
        "results": [asdict(result) for result in results],
    }
    sidecar_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return sidecar_path


def build_benchmark_document(
    payload: Sequence[str] | None = None,
    results: Sequence[BenchmarkResult] | None = None,
    *,
    repeat: int = DEFAULT_REPEAT,
    inner_iterations: int = DEFAULT_INNER_ITERATIONS,
) -> Document:
    payload_values = list(payload) if payload is not None else generate_payload(DEFAULT_PAYLOAD_COUNT)
    result_values = list(results) if results is not None else benchmark_normalizers(
        payload_values,
        repeat=repeat,
        inner_iterations=inner_iterations,
    )
    validate_benchmark_results(result_values)
    best = result_values[0]
    slowest = result_values[-1]
    speedup = slowest.median_ms / best.median_ms

    sample_rows = [
        [str(index + 1), value, normalize_with_translate(value)]
        for index, value in enumerate(payload_values[:5])
    ]

    pipeline_table = Table(
        headers=["Step", "Python value", "Document use"],
        rows=[
            ["1", "payload: list[str]", "Generated in memory by normal Python code."],
            ["2", "NORMALIZERS", "Three callables are benchmarked with the same loop."],
            ["3", "results: list[BenchmarkResult]", "Median time, best time, and checksum are kept as typed data."],
            ["4", "benchmark_results_to_table(...)", "The measured data becomes table rows."],
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
    environment_table = Table(
        headers=["Metadata", "Value"],
        rows=benchmark_environment_rows(
            len(payload_values),
            repeat,
            inner_iterations,
        ),
        caption="Benchmark environment metadata recorded with the result sidecar.",
        column_widths=[3.4, 10.2],
        unit="cm",
        header_background_color="#E7EEF7",
        alternate_row_background_color="#F8FBFD",
    )
    result_table = benchmark_results_to_table(result_values)

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
                    "Keep timing and checksum values in BenchmarkResult objects.",
                    "Turn those result objects into oodocs table rows and prose.",
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
                "Benchmark environment",
                Paragraph(
                    "Timing results are only useful when the run context is visible. This example records the core execution metadata in the document and in the JSON sidecar."
                ),
                environment_table,
            ),
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
                bold(best.name),
                " at ",
                inline_code(f"{best.median_ms:.3f}"),
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
                "validate_benchmark_results(results)\n"
                "table = benchmark_results_to_table(results)\n"
                "document = build_benchmark_document(payload, results)\n"
                "bundle = document.save_all('artifacts/native-benchmark-report', stem='native-python-benchmark')",
                language="python",
            ),
        ),
        settings=DocumentSettings(
            metadata=DocumentMetadata(
                author="Example Documentation Team",
                description="Example report generated from native Python benchmark data",
            ),
            title_matter=TitleMatter(
                subtitle="Documenting measured Python work without leaving Python",
            ),
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
) -> BenchmarkReportBundle:
    """Build the benchmark report example and export selected formats."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    payload = generate_payload(DEFAULT_PAYLOAD_COUNT)
    results = benchmark_normalizers(
        payload,
        repeat=DEFAULT_REPEAT,
        inner_iterations=DEFAULT_INNER_ITERATIONS,
    )
    validate_benchmark_results(results)
    sidecar_path = write_benchmark_sidecar(
        output_path,
        results,
        payload_count=len(payload),
        repeat=DEFAULT_REPEAT,
        inner_iterations=DEFAULT_INNER_ITERATIONS,
    )
    document = build_benchmark_document(
        payload,
        results,
        repeat=DEFAULT_REPEAT,
        inner_iterations=DEFAULT_INNER_ITERATIONS,
    )
    formats = tuple(output_formats or ("docx", "pdf", "html"))
    rendered = document.save_all(
        output_path,
        stem=OUTPUT_STEM,
        formats=formats,
        verbose=verbose,
    )
    return BenchmarkReportBundle(rendered=rendered, results_json=sidecar_path)


def build_document() -> Document:
    """Return the renderable benchmark report document."""

    return build_benchmark_document()


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> BenchmarkReportBundle:
    """Render the benchmark report through the common example interface."""

    return build_native_benchmark_report(
        output_dir,
        output_formats=output_formats,
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
        print(f"Wrote json: {outputs.results_json}")


if __name__ == "__main__":
    main()
