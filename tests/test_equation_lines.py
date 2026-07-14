from __future__ import annotations

from io import BytesIO
import zipfile

from pypdf import PdfReader
import pytest

from oodocs import Chapter, CodeBlock, Document, DocumentSettings, Equation, Figure, Paragraph, Table, Theme
from oodocs.components.blocks import AlignedEquation, Theorem
from oodocs.components.equations import EquationLine, IndexableReference
from oodocs.layout.indexing import build_render_index, resolve_block_reference
from oodocs.styles.counter import CounterStyle
from oodocs.styles.numbering import CounterPolicy, NumberingDefaults


def _theme_with_numbering(numbering: NumberingDefaults) -> Theme:
    return Theme(numbering=numbering)


def test_equation_line_is_referenceable_without_becoming_a_block() -> None:
    line = EquationLine(
        r"E & = mc^2",
        reference_label="Eq.",
        identifier="energy-row",
    )

    assert isinstance(line, IndexableReference)
    assert line.alignment_parts() == ("E", "= mc^2")
    assert line.render_expression() == "E  = mc^2"
    assert line.plain_text() == "E  = mc2"
    assert line.anchor == "energy-row"
    assert line.ref().plain_text() == "Eq. ?"
    assert line.link("energy balance").plain_text() == "energy balance"

    with pytest.raises(ValueError, match="expression must not be empty"):
        EquationLine("  ")
    with pytest.raises(ValueError, match="reference_label must not be empty"):
        EquationLine("x=1", reference_label=" ")
    with pytest.raises(ValueError, match="identifier must not be empty"):
        EquationLine("x=1", identifier=" ")


def test_aligned_equation_coerces_strings_and_supports_all_numbering_modes() -> None:
    explicit = EquationLine(r"a &= b")
    group = AlignedEquation(explicit, r"b &= c")
    each = AlignedEquation(explicit, r"b &= c", numbering="each")
    none = AlignedEquation(r"a &= b", numbering="none")
    legacy_none = AlignedEquation(r"a &= b", numbered=False)

    assert group.numbering == "group"
    assert group.numbered is True
    assert group.lines[0] is explicit
    assert isinstance(group.lines[1], EquationLine)
    assert group.expression == r"a = b \\ b = c"
    assert each.numbering == "each"
    assert each.numbered is False
    assert len(each.numbered_lines()) == 2
    assert none.numbering == legacy_none.numbering == "none"
    assert none.numbered is legacy_none.numbered is False

    with pytest.raises(ValueError, match="must be 'group', 'each', or 'none'"):
        AlignedEquation("x=1", numbering="invalid")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="conflicts"):
        AlignedEquation("x=1", numbering="each", numbered=True)


def test_each_numbering_indexes_rows_in_shared_equation_sequence() -> None:
    first = Equation("x=1")
    primary = EquationLine(r"E & = mc^2", identifier="energy")
    note = EquationLine(r"m &> 0", numbered=False, identifier="mass-note")
    secondary = EquationLine(r"p & = mv")
    aligned = AlignedEquation(primary, note, secondary, numbering="each")
    last = Equation("z=3")
    document = Document(
        "Equation rows",
        Paragraph("See ", primary.ref(), " and ", note.link("the condition"), "."),
        first,
        aligned,
        last,
    )

    index = build_render_index(document)

    assert index.equation_number(first) == 1
    assert index.equation_number(aligned) is None
    assert index.equation_number(primary) == 2
    assert index.equation_number(note) is None
    assert index.equation_number(secondary) == 3
    assert index.equation_number(last) == 4
    assert index.anchor_for(primary) == "energy"
    assert index.anchor_for(note) == "mass-note"
    assert resolve_block_reference(primary, document.settings.theme, index).text() == "Equation 2"


def test_scoped_equation_numbers_restart_and_include_heading_number() -> None:
    numbering = NumberingDefaults(
        equation=CounterPolicy(
            scope="chapter",
            include_parent=True,
            template="{parent}.{value}",
        )
    )
    first = Equation("x=1")
    row_a = EquationLine(r"a &= b")
    row_b = EquationLine(r"b &= c")
    second = AlignedEquation(row_a, row_b, numbering="each")
    third = Equation("z=3")
    document = Document(
        "Scoped equations",
        Chapter("First", first, second),
        Chapter("Second", third),
        settings=DocumentSettings(theme=_theme_with_numbering(numbering)),
    )

    index = build_render_index(document)

    assert index.equation_number(first) == "1.1"
    assert index.equation_number(row_a) == "1.2"
    assert index.equation_number(row_b) == "1.3"
    assert index.equation_number(third) == "2.1"
    assert index.anchor_for(first) is not None


def test_counter_policies_apply_to_all_builtin_countable_families() -> None:
    chapter_policy = CounterPolicy(scope="chapter")
    numbering = NumberingDefaults(
        table=chapter_policy,
        figure=chapter_policy,
        equation=chapter_policy,
        listing=chapter_policy,
        countable=chapter_policy,
    )
    table = Table(["Value"], [["one"]], caption="Values")
    figure = Figure("not-read-during-indexing.png", caption="Diagram")
    equation = Equation("x=1")
    listing = CodeBlock("print('ok')", caption="Example")
    theorem = Theorem("The sequence restarts in each chapter.")
    document = Document(
        "Scoped counters",
        Chapter("One", table, figure, equation, listing, theorem),
        settings=DocumentSettings(theme=_theme_with_numbering(numbering)),
    )

    index = build_render_index(document)

    assert index.table_number(table) == "1"
    assert index.figure_number(figure) == "1"
    assert index.equation_number(equation) == "1"
    assert index.code_block_number(listing) == "1"
    assert index.countable_number(theorem) == "1"


def test_counter_policy_validates_scope_template_and_required_parent() -> None:
    with pytest.raises(ValueError, match="CounterPolicy.scope"):
        CounterPolicy(scope="page")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must contain"):
        CounterPolicy(template="{parent}")
    with pytest.raises(ValueError, match="supports only"):
        CounterPolicy(template="{value}-{unknown}")

    policy = CounterPolicy(
        scope="section",
        counter=CounterStyle(counter_format="upper-alpha"),
        include_parent=True,
        template="{parent}-{value}",
    )
    assert policy.format_value(2, parent="3.1") == "3.1-B"
    with pytest.raises(ValueError, match="requires a numbered parent"):
        policy.format_value(1)


def test_default_numbering_preserves_legacy_integer_values() -> None:
    equation = Equation("x=1")
    index = build_render_index(Document("Legacy numbering", equation))

    assert CounterPolicy().preserves_legacy_integer() is True
    assert index.equation_number(equation) == 1
    assert isinstance(index.equation_number(equation), int)


def test_equation_line_validation_covers_missing_numbers_targets_and_anchors() -> None:
    numbered = EquationLine("x &= 1", identifier="shared-row")
    unnumbered = EquationLine("y &= 2", numbered=False, identifier="shared-row")
    aligned = AlignedEquation(numbered, unnumbered, numbering="each")
    valid = Document(
        "Valid rows",
        Paragraph(
            "See ",
            numbered.ref(),
            ", ",
            unnumbered.ref("the second row"),
            ", and ",
            unnumbered.link("its anchor"),
            ".",
        ),
        aligned,
    )

    codes = {issue.code for issue in valid.validate().errors}
    assert "duplicate-anchor" in codes
    assert "equation-line-reference-missing" not in codes
    assert "missing-reference-target" not in codes

    missing_number = Document(
        "Unnumbered row",
        Paragraph("See ", unnumbered.ref(), "."),
        AlignedEquation(unnumbered, numbering="each"),
    )
    assert "equation-line-reference-missing" in {
        issue.code for issue in missing_number.validate().errors
    }

    detached = EquationLine("z=3")
    missing_target = Document("Missing row", Paragraph("See ", detached.ref(), "."))
    assert "missing-reference-target" in {
        issue.code for issue in missing_target.validate().errors
    }


def test_counter_scope_validation_requires_numbered_parent() -> None:
    numbering = NumberingDefaults(
        equation=CounterPolicy(scope="chapter", include_parent=True)
    )
    root_equation = Document(
        "No chapter",
        Equation("x=1"),
        settings=DocumentSettings(theme=Theme(numbering=numbering)),
    )
    unnumbered_chapter = Document(
        "Unnumbered chapter",
        Chapter("Body", Equation("x=1"), numbered=False),
        settings=DocumentSettings(theme=Theme(numbering=numbering)),
    )
    valid = Document(
        "Numbered chapter",
        Chapter("Body", Equation("x=1")),
        settings=DocumentSettings(theme=Theme(numbering=numbering)),
    )

    assert "counter-scope-parent-missing" in {
        issue.code for issue in root_equation.validate().errors
    }
    assert "counter-scope-parent-missing" in {
        issue.code for issue in unnumbered_chapter.validate().errors
    }
    assert "counter-scope-parent-missing" not in {
        issue.code for issue in valid.validate().errors
    }


def test_each_numbering_renders_alignment_row_anchors_and_links_in_all_formats(
    tmp_path,
) -> None:
    primary = EquationLine(r"E &= mc^2", identifier="energy-row")
    condition = EquationLine(
        r"m &> 0",
        numbered=False,
        identifier="mass-condition",
    )
    momentum = EquationLine(r"p &= mv", identifier="momentum-row")
    aligned = AlignedEquation(primary, condition, momentum, numbering="each")
    document = Document(
        "Aligned rows",
        Paragraph(
            "Use ",
            primary.ref(),
            "; assume ",
            condition.link("positive mass"),
            ".",
        ),
        aligned,
    )

    html_path = tmp_path / "aligned.html"
    docx_path = tmp_path / "aligned.docx"
    pdf_path = tmp_path / "aligned.pdf"
    document.save_html(html_path)
    document.save_docx(docx_path)
    document.save_pdf(pdf_path)

    html = html_path.read_text(encoding="utf-8")
    assert 'class="oodocs-equation oodocs-aligned-equation"' in html
    assert 'data-numbering="each"' in html
    assert 'id="energy-row"' in html
    assert 'id="mass-condition"' in html
    assert 'href="#energy-row"' in html
    assert 'href="#mass-condition"' in html
    assert html.count("oodocs-equation-number\">") == 2
    assert "(1)" in html and "(2)" in html

    with zipfile.ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert 'w:name="energy-row"' in document_xml
    assert 'w:name="mass-condition"' in document_xml
    assert "<w:tbl>" in document_xml
    assert "(1)" in document_xml and "(2)" in document_xml

    reader = PdfReader(BytesIO(pdf_path.read_bytes()))
    pdf_text = " ".join(
        (page.extract_text() or "").replace("\n", " ") for page in reader.pages
    )
    assert "E" in pdf_text and "mc2" in pdf_text
    assert "m" in pdf_text and "> 0" in pdf_text
    assert "p" in pdf_text and "mv" in pdf_text
    assert "(1)" in pdf_text and "(2)" in pdf_text
