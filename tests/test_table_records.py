from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import pytest

from oodocs import Figure, ImageData, Table, TableCell, TableStyle
from oodocs.media import ColumnSpec

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass
class MetricRow:
    metric: str
    value: float


def _cell_text(table: Table, row: int, column: int) -> str:
    return table.rows[row][column].content.plain_text()


def test_table_from_records_supports_mappings_dataclasses_and_formatters() -> None:
    table = Table.from_records(
        [
            {"metric": "speed", "value": 0.8123, "note": None},
            MetricRow("quality", 0.945),
        ],
        columns=["metric", "value", "note"],
        headers=["Metric", "Value", "Note"],
        formatters={"value": ".2f"},
        missing="n/a",
        caption="Run metrics.",
        style=TableStyle.evidence(),
    )

    assert [cell.content.plain_text() for cell in table.headers] == [
        "Metric",
        "Value",
        "Note",
    ]
    assert _cell_text(table, 0, 1) == "0.81"
    assert _cell_text(table, 0, 2) == ""
    assert _cell_text(table, 1, 2) == "n/a"
    assert table.style.repeat_header_rows is True


def test_table_from_records_supports_sequence_records() -> None:
    table = Table.from_records(
        [("docx", 1), ("pdf", 2)],
        headers=["Format", "Count"],
    )

    assert _cell_text(table, 0, 0) == "docx"
    assert _cell_text(table, 1, 1) == "2"

    with pytest.raises(ValueError, match="columns or headers"):
        Table.from_records([("docx", 1)])

    with pytest.raises(ValueError, match="missing column"):
        Table.from_records([{"a": 1}], columns=["a", "b"], fail_on_missing=True)


def test_table_from_dataframe_preserves_multiindex_spans_and_formatters() -> None:
    pandas = pytest.importorskip("pandas")
    dataframe = pandas.DataFrame(
        [
            [1.234, 4.567, 10.0],
            [2.345, 5.678, 20.0],
            [3.456, 6.789, 30.0],
        ],
        columns=pandas.MultiIndex.from_tuples(
            [
                ("Metrics", "Mean"),
                ("Metrics", "Peak"),
                ("Limits", ""),
            ],
            names=("Group", "Measure"),
        ),
        index=pandas.MultiIndex.from_tuples(
            [("North", "A"), ("North", "B"), ("South", "A")],
            names=("Region", "Case"),
        ),
    )

    table = Table.from_dataframe(
        dataframe,
        include_index=True,
        formatters={
            "Metrics": ".1f",
            "Peak": ".2f",
            "Limits": lambda value: f"{value:.0f} ms",
        },
    )
    shortcut = Table(dataframe, include_index=True)

    assert [cell.content.plain_text() for cell in table.header_rows[0]] == [
        "Region",
        "Case",
        "Metrics",
        "Limits",
    ]
    assert table.header_rows[0][0].rowspan == 2
    assert table.header_rows[0][1].rowspan == 2
    assert table.header_rows[0][2].colspan == 2
    assert table.header_rows[0][3].rowspan == 2
    assert [cell.content.plain_text() for cell in table.rows[0]] == [
        "North",
        "A",
        "1.2",
        "4.57",
        "10 ms",
    ]
    assert [cell.content.plain_text() for cell in table.rows[1]] == [
        "B",
        "2.3",
        "5.68",
        "20 ms",
    ]
    assert table.rows[0][0].rowspan == 2
    assert table._layout().column_count == 5
    assert shortcut.header_rows[0][2].colspan == 2
    assert shortcut.rows[0][2].content.plain_text() == "1.234"


def test_table_rejects_mismatched_expanded_group_headers() -> None:
    with pytest.raises(ValueError, match="grouped header colspans"):
        Table(
            headers=[
                [TableCell("Only one group")],
                [TableCell("A"), TableCell("B")],
            ],
            rows=[["a", "b"]],
        )

    with pytest.raises(ValueError, match="column_widths"):
        Table.grouped_headers(
            groups=[("Group", 2)],
            columns=["A", "B"],
            rows=[["a", "b"]],
            column_widths=[2.0],
        )


def test_table_from_records_accepts_column_specs_and_sidecar_helpers(
    tmp_path,
) -> None:
    table = Table.from_records(
        [
            {
                "case": "case-001",
                "status": "pass",
                "notes": "stable",
                "raw_trace": "debug-only",
            },
            {
                "case": "case-002",
                "status": "review",
                "notes": "needs follow-up",
                "raw_trace": "debug-only",
            },
        ],
        columns=[
            ColumnSpec(key="case", header="Case", width=0.9, unit="in", wrap=False),
            {"key": "status", "header": "Status", "width": 0.8, "unit": "in"},
            ColumnSpec(key="notes", header="Notes", flex=1, text_alignment="left"),
            ColumnSpec(key="raw_trace", visible=False),
        ],
        caption="Matrix.",
    )

    assert [cell.content.plain_text() for cell in table.headers] == [
        "Case",
        "Status",
        "Notes",
    ]
    assert _cell_text(table, 0, 0) == "case-001"
    assert _cell_text(table, 0, 2) == "stable"
    assert len(table.columns or []) == 3
    assert table.columns is not None
    assert table.columns[0].wrap is False
    assert table._column_widths_in_inches("in", available_width=4.7) == [
        0.9,
        0.8,
        3.0,
    ]

    excerpt = table.excerpt(max_rows=1, max_columns=2, caption="Excerpt.")
    assert [cell.content.plain_text() for cell in excerpt.headers] == [
        "Case",
        "Status",
    ]
    assert len(excerpt.rows) == 1
    assert _cell_text(excerpt, 0, 0) == "case-001"
    assert excerpt.caption is not None
    assert excerpt.caption.plain_text() == "Excerpt."

    csv_path = table.save_csv(tmp_path / "full-matrix.csv")
    assert csv_path.read_text(encoding="utf-8").splitlines() == [
        "Case,Status,Notes",
        "case-001,pass,stable",
        "case-002,review,needs follow-up",
    ]

    with pytest.raises(ValueError, match="ColumnSpec.key"):
        Table.from_records([{"case": "case-001"}], columns=[ColumnSpec(width=1.0)])


def test_table_from_mapping_stringifies_nested_values() -> None:
    table = Table.from_mapping(
        {"name": "oodocs", "meta": {"python": ">=3.11"}},
        key_header="Field",
        value_header="Value",
    )

    assert [cell.content.plain_text() for cell in table.headers] == ["Field", "Value"]
    assert _cell_text(table, 1, 1) == '{"python": ">=3.11"}'

    with pytest.raises(ValueError, match="must not be empty"):
        Table.from_mapping({})


def test_table_from_csv_and_tsv(tmp_path) -> None:
    csv_path = tmp_path / "results.csv"
    csv_path.write_text("metric,value\nspeed,0.81\nquality,0.94\n", encoding="utf-8")
    tsv_path = tmp_path / "results.tsv"
    tsv_path.write_text("metric\tvalue\nspeed\t0.81\n", encoding="utf-8")

    csv_table = Table.from_csv(
        csv_path,
        columns=[
            ColumnSpec(width=0.8, unit="in", wrap=False),
            ColumnSpec(flex=1, text_alignment="right"),
        ],
        caption="CSV results.",
        style="compact",
        split=True,
    )
    tsv_table = Table.from_tsv(
        tsv_path,
        columns=[ColumnSpec(flex=1), ColumnSpec(flex=2)],
    )
    no_header = Table.from_csv(csv_path, headers=False)

    assert [cell.content.plain_text() for cell in csv_table.headers] == ["metric", "value"]
    assert _cell_text(csv_table, 1, 1) == "0.94"
    assert csv_table.caption is not None
    assert csv_table.caption.plain_text() == "CSV results."
    assert csv_table.split is True
    assert csv_table.columns is not None
    assert csv_table.columns[0].wrap is False
    assert csv_table._column_widths_in_inches("in", available_width=3.0) == [
        0.8,
        2.2,
    ]
    assert _cell_text(tsv_table, 0, 0) == "speed"
    assert tsv_table._column_widths_in_inches("in", available_width=3.0) == [1.0, 2.0]
    assert [cell.content.plain_text() for cell in no_header.headers] == [
        "Column 1",
        "Column 2",
    ]


def test_figure_from_bytes_and_buffer_use_image_data() -> None:
    from_bytes = Figure.from_bytes(_TINY_PNG, image_format="png", caption="Pixel.")
    from_buffer = Figure.from_buffer(BytesIO(_TINY_PNG), image_format="png", caption="Pixel.")

    assert isinstance(from_bytes.image_source, ImageData)
    assert from_bytes.image_source.data == _TINY_PNG
    assert isinstance(from_buffer.image_source, ImageData)
    assert from_buffer.image_source.data == _TINY_PNG

    with pytest.raises(ValueError, match="non-empty"):
        Figure.from_bytes(b"", image_format="png")
