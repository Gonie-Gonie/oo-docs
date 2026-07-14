from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from oodocs import Document
from oodocs.components.inline import Hyperlink
from oodocs.components.references import CitationLibrary, CitationSource
from oodocs.integrations.bibtex import (
    BibtexParseError,
    BibtexparserParser,
    BuiltinBibtexParser,
)


def test_bibtex_parser_preserves_named_and_unknown_fields_losslessly() -> None:
    library = CitationLibrary.from_bibtex(
        r"""
@article{kim2026,
  title = {한국어 {API} 문서화},
  author = {{Example Research and Development Organization}},
  journal = {Journal of Documentation},
  booktitle = {Collected Papers},
  volume = {12},
  number = {3},
  pages = {101--119},
  doi = {10.1234/example.2026.7},
  institution = {Example Institute},
  school = {Example University},
  edition = {2nd},
  chapter = {4},
  month = {July},
  address = {Seoul},
  version = {1.4},
  accessed = {2026-07-14},
  year = {2026},
  url = {https://example.org/paper},
  custom-field = {kept {verbatim}}
}
"""
    )

    source = library.resolve("kim2026")
    assert source.entry_type == "article"
    assert source.title == "한국어 API 문서화"
    assert source.authors == ("Example Research and Development Organization",)
    assert source.journal == "Journal of Documentation"
    assert source.booktitle == "Collected Papers"
    assert source.volume == "12"
    assert source.number == "3"
    assert source.pages == "101--119"
    assert source.doi == "10.1234/example.2026.7"
    assert source.institution == "Example Institute"
    assert source.school == "Example University"
    assert source.edition == "2nd"
    assert source.chapter == "4"
    assert source.month == "July"
    assert source.address == "Seoul"
    assert source.version == "1.4"
    assert source.accessed == "2026-07-14"
    assert source.fields["title"] == "한국어 {API} 문서화"
    assert source.fields["custom-field"] == "kept {verbatim}"

    record = source.as_bibtex_record()
    assert record["entry_type"] == "article"
    assert record["key"] == "kim2026"
    assert record["custom-field"] == "kept {verbatim}"
    assert set(source.fields) <= set(record)


@pytest.mark.parametrize(
    ("entry_type", "extra_fields", "expected"),
    [
        ("article", "journal={Journal A}, volume={4}, number={2}, pages={10--19}", "Journal A"),
        ("phdthesis", "school={Example University}", "Example University"),
        ("techreport", "institution={Example Institute}, number={TR-7}", "Example Institute"),
        ("standard", "organization={Standards Group}, number={STD-9}", "Standards Group"),
        ("manual", "organization={Tool Authors}, version={3.2}", "Version 3.2"),
        ("book", "publisher={Example Press}, edition={3rd}", "3rd ed"),
        ("misc", "howpublished={Online archive}, note={Dataset}", "Online archive"),
    ],
)
def test_entry_type_fixtures_feed_every_formatter(
    entry_type: str,
    extra_fields: str,
    expected: str,
) -> None:
    source = CitationLibrary.from_bibtex(
        f"""@{entry_type}{{sample,
  title={{A Generic Reference}},
  author={{Doe, Jane}},
  year={{2026}},
  doi={{10.5555/sample}},
  {extra_fields}
}}"""
    ).resolve("sample")

    for style in ("plain", "numbered", "apa", "mla", "chicago", "ieee"):
        formatted = source.format_reference(style)
        assert "A Generic Reference" in formatted
        assert expected in formatted
        assert "https://doi.org/10.5555/sample" in formatted


def test_supported_latex_accents_are_decoded_and_unknown_commands_are_diagnosed() -> None:
    source = CitationLibrary.from_bibtex(
        r"""@book{garcia,
  title = {Garc{\'i}a and \unknown{source}},
  author = {Garc{\'i}a, Ana},
  publisher = {Example Press}
}"""
    ).resolve("garcia")

    assert source.title.startswith("García")
    assert source.authors == ("García, Ana",)
    assert source.fields["title"] == r"Garc{\'i}a and \unknown{source}"
    assert len(source.diagnostics) == 1
    diagnostic = source.diagnostics[0]
    assert diagnostic.code == "unsupported-latex-command"
    assert diagnostic.entry_key == "garcia"
    assert diagnostic.field == "title"
    assert diagnostic.raw_value == source.fields["title"]
    assert diagnostic.line == 2


def test_parse_errors_include_entry_key_and_source_location() -> None:
    with pytest.raises(BibtexParseError) as exc_info:
        CitationLibrary.from_bibtex(
            "@article{broken,\n  title = {Valid},\n  year {2026}\n}\n"
        )

    message = str(exc_info.value)
    assert "broken" in message
    assert "line 3" in message
    assert "column" in message


def test_custom_parser_backend_can_supply_citation_sources() -> None:
    class Parser:
        def parse(self, source: str) -> tuple[CitationSource, ...]:
            assert source == "custom"
            return (CitationSource("Backend Result", key="backend", entry_type="misc"),)

    library = CitationLibrary.from_bibtex("custom", parser=Parser())
    assert library.resolve("backend").title == "Backend Result"


def test_optional_backend_reports_raw_field_loss_to_document_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = """@misc{sample,
  title = {Preserved title},
  custom-field = {must survive},
  year = {2026}
}"""
    fake_database = SimpleNamespace(
        entries=[
            {
                "ENTRYTYPE": "misc",
                "ID": "sample",
                "title": "Preserved title",
                "year": "2026",
            }
        ]
    )
    monkeypatch.setitem(
        sys.modules,
        "bibtexparser",
        SimpleNamespace(loads=lambda value: fake_database),
    )

    citation = BibtexparserParser().parse(source)[0]
    losses = [
        diagnostic
        for diagnostic in citation.diagnostics
        if diagnostic.code == "bibtex-field-loss"
    ]

    assert len(losses) == 1
    assert losses[0].entry_key == "sample"
    assert losses[0].field == "custom-field"
    assert losses[0].raw_value == "must survive"
    assert losses[0].line == 3
    assert citation.fields["custom-field"] == "must survive"

    errors = Document("Field loss", citations=[citation]).validate().errors
    matching = [issue for issue in errors if issue.code == "bibtex-field-loss"]
    assert len(matching) == 1
    assert matching[0].severity == "error"
    assert matching[0].path.endswith(".diagnostics[0]")


def test_doi_and_url_are_separate_hyperlink_fragments() -> None:
    source = CitationSource(
        "Linked Reference",
        key="linked",
        doi="10.1000/linked",
        url="https://example.org/supplement",
    )

    fragments = source.reference_fragments("plain")
    links = [fragment for fragment in fragments if isinstance(fragment, Hyperlink)]
    assert [(link.target, link.plain_text()) for link in links] == [
        ("https://doi.org/10.1000/linked", "https://doi.org/10.1000/linked"),
        ("https://example.org/supplement", "https://example.org/supplement"),
    ]


def test_importing_core_and_bibtex_integration_does_not_eager_import_optional_backend() -> None:
    command = (
        "import sys; import oodocs; import oodocs.integrations.bibtex; "
        "assert 'bibtexparser' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-c", command],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_builtin_parser_protocol_returns_sequence() -> None:
    parsed = BuiltinBibtexParser().parse("@misc{one, title={One}}")
    assert isinstance(parsed, tuple)
    assert parsed[0].key == "one"
