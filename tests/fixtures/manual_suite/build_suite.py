"""Build the compact, generic manual suite used by acceptance tests.

The fixture intentionally exercises one instance of each cross-cutting manual
feature.  It is not an example application and owns no domain-specific
vocabulary, schema, branding, or release recipe.
"""

from __future__ import annotations

from pathlib import Path

from oodocs import (
    Author,
    Chapter,
    CitationLibrary,
    Document,
    ListOfFigures,
    ListOfReferences,
    ListOfTables,
    PageLayout,
    Paragraph,
    Part,
    Section,
    SubFigure,
    SubFigureGroup,
    Table,
    TableOfContents,
    Theme,
    cite,
)
from oodocs.clidoc import CliApplication, CliCommand, CliOption
from oodocs.components.blocks import AlignedEquation, Appendix
from oodocs.components.descriptions import DescriptionList
from oodocs.components.equations import EquationLine
from oodocs.components.matter import BackMatter, FrontMatter, MainMatter
from oodocs.engineering import NumberFormat, Quantity
from oodocs.presets.templates import CoverPagePreset
from oodocs.schema import FieldSpec, SchemaCatalog, SchemaSpec
from oodocs.suite import AssetResolver, DocumentSuite, DocumentSuiteContext


FIXTURE_ROOT = Path(__file__).resolve().parent
ASSET_NAMES = ("logo.png", "diagram-a.png", "diagram-b.png")
MANUAL_NAME = "Acceptance manual"
LONG_TABLE_ROW_COUNT = 42


def build_cli_application() -> CliApplication:
    """Return the generic CLI model embedded in the manual."""

    return CliApplication(
        "doc-tool",
        "Render a portable documentation bundle.",
        root_command=CliCommand(
            "doc-tool",
            usage="doc-tool [OPTIONS] SOURCE",
            options=(
                CliOption(("source",), value_name="SOURCE", required=True,
                          description="Input document definition."),
                CliOption(("-f", "--format"), value_name="FORMAT", default="html",
                          choices=("html", "docx", "pdf"),
                          description="Output format."),
                CliOption(("--strict",), description="Fail on validation warnings."),
            ),
            subcommands=(
                CliCommand("inspect", "Inspect the normalized document model."),
            ),
        ),
    )


def build_schema_catalog() -> SchemaCatalog:
    """Return two small schemas with circular cross-links."""

    root = SchemaSpec(
        "manual-root",
        "Manual root schema",
        (
            FieldSpec(
                "child",
                "object",
                requirement="required",
                target_schema="manual-child",
                description="Nested child configuration.",
            ),
            FieldSpec(
                "threshold",
                "float",
                requirement="optional",
                default=2.5,
                constraints=("greater than zero",),
                unit=Quantity(1, "m"),
                description="Generic numeric threshold.",
            ),
        ),
    )
    child = SchemaSpec(
        "manual-child",
        "Manual child schema",
        (
            FieldSpec(
                "parent",
                "object",
                requirement="optional",
                target_schema="manual-root",
                description="Optional link back to the root schema.",
            ),
        ),
    )
    return SchemaCatalog((root, child))


def _grouped_header_table() -> Table:
    return Table.grouped_headers(
        groups=(("Measured range", 2), ("Review", 1)),
        columns=("Minimum", "Maximum", "Status"),
        rows=(("1.0", "4.0", "Ready"), ("2.0", "6.0", "Review")),
        caption="Grouped-header acceptance table",
        identifier="grouped-header-table",
    )


def _long_table() -> Table:
    rows = tuple(
        (f"row-{index:03d}", f"value-{index:03d}", "accepted")
        for index in range(1, LONG_TABLE_ROW_COUNT + 1)
    )
    return Table(
        ("Long Table Header", "Value", "State"),
        rows,
        caption="Long table acceptance matrix",
        identifier="long-table",
        split=True,
        repeat_header_rows=True,
        continuation_label="continued",
    )


def _wide_table() -> Table:
    headers = tuple(f"Metric {index}" for index in range(1, 9))
    rows = tuple(
        tuple(f"{row}.{column}" for column in range(1, 9))
        for row in range(1, 4)
    )
    return Table(
        headers,
        rows,
        caption="Landscape wide table",
        identifier="wide-table",
        overflow_policy="allow",
    )


def build_manual(context: DocumentSuiteContext) -> Document:
    """Build the complete manual from shared suite context."""

    logo = context.assets.require("logo.png")
    diagram_a = context.assets.require("diagram-a.png")
    diagram_b = context.assets.require("diagram-b.png")
    organization = str(context.variables["organization"])
    version = str(context.variables["version"])
    publication_date = str(context.variables["date"])

    cover_preset = CoverPagePreset.centered_logo(
        logo,
        eyebrow=f"Version {version}",
        organization=organization,
        date=publication_date,
        footer="Generic documentation acceptance fixture",
    )
    settings = cover_preset.settings(
        subtitle="Small cross-renderer manual",
        authors=(Author("Example Maintainer"),),
        theme=Theme.from_locale("ko-KR"),
    )

    overview = Section(
        "Overview",
        anchor="manual-overview",
    )
    navigation = Section(
        "Navigation target",
        anchor="manual-navigation",
    )
    overview.add(
        Paragraph(
            "Object link forward: ",
            navigation.link("open the navigation target"),
            ". Typed reference: ",
            navigation.ref(),
            ".",
        )
    )
    navigation.add(
        Paragraph(
            "Object link back: ",
            overview.link("return to the overview"),
            ".",
        )
    )

    first_line = EquationLine(
        r"Q_{total} &= Q_{base} + Q_{adjustment}",
        identifier="equation-total-line",
    )
    second_line = EquationLine(
        r"R &= Q_{total} / A",
        identifier="equation-rate-line",
    )
    derivation = AlignedEquation(first_line, second_line, numbering="each")
    symbol_descriptions = DescriptionList(style="description.symbols")
    symbol_descriptions.add(
        "Q_total",
        Paragraph(
            "Total quantity; example value ",
            Quantity(
                1234.5,
                "kWh",
                NumberFormat(decimals=1, thousands_separator=True),
            ),
            ".",
        ),
    )
    symbol_descriptions.add("A", "Reference area used by the rate equation.")

    figures = SubFigureGroup(
        SubFigure(diagram_a, caption="Input flow", alt_text="Generic input flow diagram"),
        SubFigure(diagram_b, caption="Output flow", alt_text="Generic output flow diagram"),
        caption="Two-part process diagram",
        identifier="process-diagrams",
    )

    tables_chapter = Chapter(
        "Tables and figures",
        _grouped_header_table(),
        _long_table(),
        Section(
            "Wide matrix",
            _wide_table(),
            page_layout=PageLayout.landscape(),
        ),
        figures,
    )
    concepts_chapter = Chapter(
        "Concepts",
        overview,
        navigation,
        Section(
            "Equation semantics",
            Paragraph("Per-line references: ", first_line.ref(), " and ", second_line.ref(), "."),
            derivation,
            symbol_descriptions,
            Paragraph(
                "Reference sources: ",
                cite("article2026"),
                ", ",
                cite("thesis2024"),
                ", ",
                cite("manual2025"),
                ", and ",
                cite("standard2023"),
                ".",
            ),
        ),
        build_cli_application().to_section(title="CLI model", level=2),
    )
    schema_chapter = build_schema_catalog().to_chapter(
        "Schema catalog",
        validate=True,
    )

    front = FrontMatter(
        Chapter(
            "머리말",
            Paragraph("이 문서는 렌더러 의미론을 검증하는 작은 공용 픽스처입니다."),
            numbered=False,
            toc=True,
            anchor="manual-preface",
        ),
        TableOfContents(),
        ListOfFigures(),
        ListOfTables(),
    )
    main = MainMatter(
        Part("Portable manual", concepts_chapter, tables_chapter),
        schema_chapter,
        start_on_new_page=True,
    )
    back = BackMatter(
        Appendix(
            Chapter(
                "Acceptance notes",
                Paragraph("Back-matter appendix marker."),
            )
        ),
        ListOfReferences(include_uncited=True),
        start_on_new_page=True,
    )
    return Document(
        "공용 기술 설명서",
        front,
        main,
        back,
        settings=settings,
        citations=context.citations,
    )


def build_suite(output_dir: Path | str | None = None) -> DocumentSuite:
    """Return the acceptance suite with one compact manual item."""

    destination = Path(output_dir) if output_dir is not None else FIXTURE_ROOT / "generated"
    context = DocumentSuiteContext(
        root=FIXTURE_ROOT,
        output_dir=destination,
        variables={
            "organization": "Example Documentation Cooperative",
            "version": "2.0",
            "date": "2026-07-14",
        },
        assets=AssetResolver((Path("assets"),)),
        citations=CitationLibrary.from_bibtex_file(FIXTURE_ROOT / "references.bib"),
    )
    return DocumentSuite("Generic manual suite", context).add(
        MANUAL_NAME,
        build_manual,
        stem="acceptance-manual",
        formats=("html", "docx", "pdf"),
    )


if __name__ == "__main__":
    build_suite().save_all(verbose=True)
