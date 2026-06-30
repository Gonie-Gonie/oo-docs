from __future__ import annotations

from oodocs.apidoc import (
    ApiCategory,
    ApiException,
    ApiExample,
    ApiModule,
    ApiObject,
    ApiPackage,
    ApiParameter,
    ApiPresentationProfile,
    ApiReturn,
    ApiSeeAlso,
    api_category_to_chapter,
    check_api_help_categories,
    collect_api,
    select_uncategorized_api_objects,
)


def _plain_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "".join(_plain_text(item) for item in value)
    return str(getattr(value, "value", value))


def _block_title(block: object) -> str:
    title = getattr(block, "title", "")
    return _plain_text(title)


def _chapter_titles(document) -> list[str]:
    return [
        _block_title(block)
        for block in document.body.children
        if _block_title(block)
    ]


def _all_titles(block: object) -> list[str]:
    titles = [_block_title(block)] if _block_title(block) else []
    for child in getattr(block, "children", ()):
        titles.extend(_all_titles(child))
    return titles


def _all_plain_text(block: object) -> str:
    plain_text = getattr(block, "plain_text", None)
    text = plain_text() if callable(plain_text) else ""
    code_text = getattr(block, "code", "")
    child_text = "".join(_all_plain_text(child) for child in getattr(block, "children", ()))
    rows = getattr(block, "rows", ())
    row_text = "".join(
        _all_plain_text(getattr(cell, "content", cell))
        for row in rows
        for cell in row
    )
    return text + str(code_text) + child_text + row_text


def _assert_text_order(text: str, *phrases: str) -> None:
    positions = [text.index(phrase) for phrase in phrases]
    assert positions == sorted(positions)


def test_help_book_starts_with_category_contents_not_coverage() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")
    document = api.to_help_book(
        presentation=ApiPresentationProfile.help(),
        include_coverage=True,
        max_heading_level=2,
    )

    titles = _chapter_titles(document)
    text = _all_plain_text(document.body)

    assert titles[0] == "API Contents"
    assert "API Documentation Coverage" == titles[-1]
    assert titles.index("Core Document Model") < titles.index("API Documentation Coverage")
    assert "Coverage evidence appears after the API chapters." in text


def test_help_book_places_common_symbols_in_category_chapters() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")
    document = api.to_help_book(include_coverage=False, max_heading_level=2)
    titles = _chapter_titles(document)
    text = _all_plain_text(document.body)
    all_titles = [
        title
        for chapter in document.body.children
        for title in _all_titles(chapter)
    ]

    assert "Core Document Model" in titles
    assert "Tables and Figures" in titles
    assert "Layout and Theme" in titles
    assert "Imports" in titles
    assert "Automation API" in titles
    assert titles.index("Imports") < titles.index("Automation API")
    assert "oodocs.Document" in all_titles
    assert "oodocs.Paragraph" in all_titles
    assert "oodocs.Table" in all_titles
    assert "oodocs.TableCell" in all_titles
    assert "oodocs.TableCellStyle" in all_titles
    assert "oodocs.CodeBlock" in all_titles
    assert "oodocs.Box" in all_titles
    assert "oodocs.BoxStyle" in all_titles
    assert "oodocs.StyleSheet" in all_titles
    assert "oodocs.Figure" in all_titles
    assert "oodocs.equations.AlignedEquation" in all_titles
    assert "oodocs.equations.CasesEquation" in all_titles
    assert "oodocs.chemistry.ChemicalFormula" in all_titles
    assert "oodocs.chemistry.ReactionEquation" in all_titles
    assert "oodocs.chemistry.chemical_formula" in all_titles
    assert "oodocs.chemistry.ce" in all_titles
    assert "oodocs.CitationSource" in all_titles
    assert "oodocs.CitationLibrary" in all_titles
    assert "oodocs.CitationDefaults" in all_titles
    assert "oodocs.ListOfReferences" in all_titles
    assert "oodocs.DocumentMetadata" in all_titles
    assert "oodocs.link" in all_titles
    assert "oodocs.url" in all_titles
    assert "oodocs.LinkDefaults" in all_titles
    assert "oodocs.components.inline.Hyperlink" in all_titles
    assert "oodocs.BulletList" in all_titles
    assert "oodocs.NumberedList" in all_titles
    assert "oodocs.CounterStyle" in all_titles
    assert "oodocs.ListStyle" in all_titles
    assert "oodocs.glossary.Glossary" in all_titles
    assert "oodocs.glossary.Acronym" in all_titles
    assert "oodocs.glossary.GlossaryTerm" in all_titles
    assert "oodocs.glossary.ListOfGlossaryTerms" in all_titles
    assert "oodocs.presets.components.Nomenclature" in all_titles
    assert "oodocs.CaptionDefaults" in all_titles
    assert "oodocs.GeneratedContentDefaults" in all_titles
    assert "oodocs.LocaleDefaults" in all_titles
    assert "oodocs.HeaderFooterDefaults" in all_titles
    assert "oodocs.PageNumberDefaults" in all_titles
    assert "oodocs.refs" in all_titles
    assert "oodocs.ref_range" in all_titles
    assert "oodocs.references.ReferenceFormat" in all_titles
    assert "oodocs.references.bracket_ref" in all_titles
    assert "oodocs.references.paren_ref" in all_titles
    assert "oodocs.references.page_ref" in all_titles
    assert "oodocs.engineering.Algorithm" in all_titles
    assert "oodocs.SubFigure" in all_titles
    assert "oodocs.SubFigureGroup" in all_titles
    assert "oodocs.media.SubTable" in all_titles
    assert "oodocs.media.SubTableGroup" in all_titles
    assert "oodocs.pdf.PdfPages" in all_titles
    assert "oodocs.generated.ListOfAlgorithms" in all_titles
    assert "oodocs.generated.ListOfListings" in all_titles
    assert "oodocs.presets.components.CalloutBox" in all_titles
    assert "oodocs.TableOfContents" in all_titles
    assert "oodocs.ListOfTables" in all_titles
    assert "oodocs.ListOfFigures" in all_titles
    assert "oodocs.structure.Appendix" in all_titles
    assert "oodocs.media.ColumnSpec" in all_titles
    assert "oodocs.media.CropBox" in all_titles
    assert "oodocs.media.TableOverflowPolicy" in all_titles
    assert "oodocs.compatibility.OUTPUT_FORMATS" in all_titles
    assert "oodocs.components.blocks.MIN_SECTION_LEVEL" in all_titles
    assert "oodocs.Theme" in all_titles
    assert "oodocs.HeadingStyle" in all_titles
    assert "oodocs.HeadingNumbering" in all_titles
    assert "oodocs.ValidationResult" in all_titles
    assert "oodocs.document.Document" not in all_titles
    assert "oodocs.validation.ValidationResult" not in all_titles
    assert "oodocs.components.media.Table" not in all_titles
    assert "oodocs.settings.PageLayout" not in all_titles
    assert "oodocs.workflows.save_document_outputs" in all_titles
    assert "oodocs.workflows.build_source_outputs" in all_titles
    assert "oodocs.workflows.validate_source_document" in all_titles
    assert "oodocs.presets.components.CompactTable" in all_titles
    assert "oodocs.presets.templates.JournalArticleTemplate" in all_titles
    assert "oodocs.presets.CompactTable" not in all_titles
    assert "oodocs.presets.JournalArticleTemplate" not in all_titles
    assert check_api_help_categories(api) == ()
    assert "API Documentation Coverage" not in titles
    assert "Coverage evidence stays in sidecars unless explicitly requested." in text
    assert "Coverage evidence is appended at the end." not in text
    assert "Uncategorized API" not in titles
    assert "Renderer Extension API" not in titles
    assert "heading = HeadingStyle(" in text
    assert "heading_style=HeadingStyle(text_style=TextStyle(font_size=14))" in text
    assert "heading_styles: dict[int, HeadingStyle]" in text
    assert "toc = TableOfContents(" in text
    assert "scope=\"document\"" in text
    assert "level_styles={1: TableOfContentsLevelStyle(bold=True)}" in text
    assert "TableStyle.booktabs" in text
    assert "top_rule" in text
    assert "header_rule" in text
    assert "bottom_rule" in text
    assert "continuation_label" in text
    assert "continued_caption_template" in text
    assert "repeat_header_rows" in text
    assert "long_table_threshold" in text
    assert "Table.excerpt" in text
    assert "save_csv" in text
    assert "visible" in text
    assert "Table.grouped_headers" in text
    assert "colspan" in text
    assert "rowspan" in text
    assert "Figure.from_bytes" in text
    assert "Figure.from_buffer" in text
    assert "crop" in text
    assert "rotation" in text
    assert "alt_text" in text
    assert "label_format" in text
    assert "reference_label_format" in text
    assert "label_style" in text
    assert "selected_page_indexes" in text
    assert "page_label" in text
    assert "DOCX fallback" in text
    assert "HTML fallback" in text
    assert "CodeBlock.from_file" in text
    assert "line_numbers" in text
    assert "highlight_lines" in text
    assert "identifier" in text
    assert "inputs" in text
    assert "outputs" in text
    assert "body_style" in text
    assert "reference_label" in text
    assert "register_box" in text
    assert "title_position" in text
    assert "shadow" in text
    assert "box_style" in text
    assert "Equation.aligned" in text
    assert "Equation.cases" in text
    assert "Equation.from_sympy" in text
    assert "numbered" in text
    assert "ChemicalFormula" in text
    assert "ReactionEquation" in text
    assert "chemical_formula" in text
    assert "ce(" in text
    assert "CitationLibrary.from_bibtex_file" in text
    assert "CitationDefaults" in text
    assert "reference_sort" in text
    assert "include_uncited" in text
    assert "ListOfReferences" in text
    assert "DocumentMetadata" in text
    assert "LinkDefaults" in text
    assert "Hyperlink.internal_anchor" in text
    assert "url(" in text
    assert "link(" in text
    assert "breakable" in text
    assert "zero-width" in text
    assert "resume_from" in text
    assert "marker_gap" in text
    assert "item_spacing" in text
    assert "block_spacing" in text
    assert "item_children" in text
    assert "Glossary.use" in text
    assert "ListOfGlossaryTerms" in text
    assert "acronym" in text
    assert "Nomenclature" in text
    assert "Theme.from_locale" in text
    assert "LocaleDefaults.from_locale" in text
    assert "resolve_language_tag" in text
    assert "format_date" in text
    assert "pdf_font_fallback_guide" in text
    assert "ko-KR" in text
    assert "HeaderFooterDefaults" in text
    assert "header_left" in text
    assert "footer_center" in text
    assert "different_first_page" in text
    assert "different_odd_even_pages" in text
    assert "resolve_header_footer_template" in text
    assert "format_header_footer_text" in text
    assert "ReferenceFormat" in text
    assert "plural_label" in text
    assert "capitalized" in text
    assert "range_separator" in text
    assert "last_separator" in text
    assert "bracket_ref" in text
    assert "paren_ref" in text
    assert "page_ref" in text


def test_help_book_renders_uncategorized_api_appendix_from_category_gate() -> None:
    api = ApiPackage(
        "samplepkg",
        modules=[
            ApiModule(
                "samplepkg",
                [
                    ApiObject("function", "run", "samplepkg.run", "samplepkg"),
                    ApiObject("function", "save", "samplepkg.save", "samplepkg"),
                ],
            )
        ],
    )
    categories = [
        ApiCategory(
            id="core",
            title="Core API",
            summary="Primary sample API.",
            include=("samplepkg.run",),
            order=10,
        )
    ]

    uncategorized = select_uncategorized_api_objects(api, categories)
    issues = check_api_help_categories(api, categories)
    document = api.to_help_book(
        categories=categories,
        include_coverage=False,
        max_heading_level=1,
    )
    without_appendix = api.to_help_book(
        categories=categories,
        include_coverage=False,
        include_uncategorized_appendix=False,
        max_heading_level=1,
    )

    assert [obj.qualname for obj in uncategorized] == ["samplepkg.save"]
    assert [issue.qualname for issue in issues] == ["samplepkg.save"]
    assert issues[0].code == "uncategorized-api-object"
    assert "Uncategorized API" in _chapter_titles(document)
    assert "samplepkg.save" in _all_plain_text(document.body)
    assert "Uncategorized API" not in _chapter_titles(without_appendix)


def test_api_category_prefix_include_matches_rendering_and_gate() -> None:
    api = ApiPackage(
        "samplepkg",
        modules=[
            ApiModule(
                "samplepkg.core",
                [
                    ApiObject("class", "Client", "samplepkg.core.Client", "samplepkg.core"),
                    ApiObject("function", "connect", "samplepkg.core.connect", "samplepkg.core"),
                ],
            ),
            ApiModule(
                "samplepkg.extras",
                [
                    ApiObject("function", "debug", "samplepkg.extras.debug", "samplepkg.extras"),
                ],
            ),
        ],
    )
    categories = [
        ApiCategory(
            id="core",
            title="Core API",
            summary="Primary sample API.",
            include=("samplepkg.core.*",),
            order=10,
        )
    ]

    chapter = api_category_to_chapter(categories[0], api, max_heading_level=1)
    uncategorized = select_uncategorized_api_objects(api, categories)

    text = _all_plain_text(chapter)
    assert "Client" in text
    assert "connect" in text
    assert "samplepkg.extras.debug" not in text
    assert [obj.qualname for obj in uncategorized] == ["samplepkg.extras.debug"]


def test_help_book_uses_canonical_reexport_path_once() -> None:
    api = ApiPackage(
        "oodocs",
        modules=[
            ApiModule(
                "oodocs",
                [
                    ApiObject(
                        "class",
                        "Widget",
                        "oodocs.Widget",
                        "oodocs",
                        metadata={"reexported_from": "oodocs.core.Widget"},
                    )
                ],
            ),
            ApiModule(
                "oodocs.core",
                [
                    ApiObject(
                        "class",
                        "Widget",
                        "oodocs.core.Widget",
                        "oodocs.core",
                    )
                ],
            ),
        ],
    )
    categories = [
        ApiCategory(
            id="core",
            title="Core API",
            summary="Primary sample API.",
            include=("oodocs.Widget", "oodocs.core.*"),
            order=10,
        )
    ]

    chapter = api_category_to_chapter(categories[0], api, max_heading_level=2)
    uncategorized = select_uncategorized_api_objects(api, categories)
    issues = check_api_help_categories(api, categories)
    all_titles = _all_titles(chapter)

    assert "oodocs.Widget" in all_titles
    assert "oodocs.core.Widget" not in all_titles
    assert uncategorized == []
    assert issues == ()


def test_help_function_section_uses_matlab_style_argument_layout() -> None:
    obj = ApiObject(
        "function",
        "make_widget",
        "samplepkg.make_widget",
        "samplepkg",
        signature="make_widget(name: str, *, enabled: bool = True) -> Widget",
        summary="Create a widget.",
        description="Use this helper when a widget instance is needed.",
        parameters=[
            ApiParameter("name", "str", description="Widget name."),
            ApiParameter(
                "enabled",
                "bool",
                default="True",
                kind="keyword-only",
                description="Whether the widget starts enabled.",
                required=False,
            ),
        ],
        returns=ApiReturn("Widget", "Created widget.", documented=True),
        exceptions=[ApiException("ValueError", "If the name is blank.")],
        examples=[ApiExample('make_widget("demo")')],
        see_also=[ApiSeeAlso("Widget", target="samplepkg.Widget")],
    )

    section = obj.to_help_section(level=2)
    text = _all_plain_text(section)

    _assert_text_order(
        text,
        "Create a widget.",
        "Syntax",
        "Description",
        "Input Arguments",
        "Name-Value Arguments",
        "Output Arguments",
        "Examples",
        "Errors",
        "See also",
    )
    assert "result = make_widget" in text
    assert "enabled" in text
    assert "Created widget." in text
    assert "ValueError" in text


def test_help_class_section_separates_creation_properties_and_methods() -> None:
    obj = ApiObject(
        "class",
        "Widget",
        "samplepkg.Widget",
        "samplepkg",
        signature="Widget(name: str)",
        summary="Runtime widget.",
        description="Wraps rendered widget state.",
        parameters=[ApiParameter("name", "str", description="Widget name.")],
        members=[
            ApiObject(
                "attribute",
                "label",
                "samplepkg.Widget.label",
                "samplepkg",
                signature="label: LabelText",
                summary="User-facing label.",
            ),
            ApiObject(
                "property",
                "title",
                "samplepkg.Widget.title",
                "samplepkg",
                summary="Display title.",
                returns=ApiReturn("str", "Title text.", documented=True),
            ),
            ApiObject(
                "method",
                "render",
                "samplepkg.Widget.render",
                "samplepkg",
                signature="render(path: str) -> str",
                summary="Render the widget.",
            ),
            ApiObject(
                "method",
                "render_to_html",
                "samplepkg.Widget.render_to_html",
                "samplepkg",
                signature="render_to_html(context)",
                summary="Renderer hook.",
            ),
        ],
    )

    section = obj.to_help_section(level=2)
    text = _all_plain_text(section)

    _assert_text_order(
        text,
        "Runtime widget.",
        "Creation",
        "Description",
        "Constructor Arguments",
        "Properties",
        "Common Methods",
    )
    assert "obj = Widget(name: str)" in text
    assert "label" in text
    assert "LabelText" in text
    assert "title" in text
    assert "render(path: str) -> str" in text
    assert "render_to_html" not in text


def test_help_value_section_uses_compact_definition_layout() -> None:
    obj = ApiObject(
        "data",
        "OUTPUT_FORMATS",
        "samplepkg.OUTPUT_FORMATS",
        "samplepkg",
        signature="OUTPUT_FORMATS: tuple[str, ...]",
        summary="Supported output formats.",
        description="Used by save helpers when no explicit output set is provided.",
        metadata={"default": "('docx', 'pdf', 'html')"},
    )

    section = obj.to_help_section(level=2)
    text = _all_plain_text(section)

    _assert_text_order(
        text,
        "Supported output formats.",
        "Definition",
        "OUTPUT_FORMATS",
        "tuple[str, ...]",
        "('docx', 'pdf', 'html')",
        "Description",
    )
    assert "Syntax" not in text
    assert "Input Arguments" not in text


def test_category_landing_page_summarizes_constants() -> None:
    api = ApiPackage(
        "samplepkg",
        modules=[
            ApiModule(
                "samplepkg",
                [
                    ApiObject(
                        "data",
                        "OUTPUT_FORMATS",
                        "samplepkg.OUTPUT_FORMATS",
                        "samplepkg",
                        signature="OUTPUT_FORMATS: tuple[str, ...]",
                        summary="Supported output formats.",
                        metadata={"default": "('docx', 'pdf')"},
                    ),
                    ApiObject(
                        "function",
                        "save",
                        "samplepkg.save",
                        "samplepkg",
                        signature="save(path: str) -> None",
                        summary="Save outputs.",
                    ),
                ],
            )
        ],
    )
    category = ApiCategory(
        id="outputs",
        title="Output API",
        summary="Save documents and inspect supported outputs.",
        include=("samplepkg.OUTPUT_FORMATS", "samplepkg.save"),
        order=10,
    )

    chapter = api_category_to_chapter(category, api, max_heading_level=1)
    text = _all_plain_text(chapter)

    assert "Constants" in text
    assert "OUTPUT_FORMATS" in text
    assert "('docx', 'pdf') / tuple[str, ...]" in text
    assert "Supported output formats." in text


def test_help_examples_use_basic_role_and_preview_long_code() -> None:
    long_basic = "\n".join(f"line_{index}()" for index in range(25))
    obj = ApiObject(
        "function",
        "run",
        "samplepkg.run",
        "samplepkg",
        signature="run() -> None",
        summary="Run the sample.",
        examples=[
            ApiExample("advanced_run()", role="advanced"),
            ApiExample(long_basic, role="basic"),
            ApiExample("guide_run()", role="guide"),
        ],
    )

    section = obj.to_help_section(level=2)
    text = _all_plain_text(section)

    assert "line_0()" in text
    assert "line_19()" in text
    assert "line_20()" not in text
    assert "..." in text
    assert "advanced_run()" not in text
    assert "guide_run()" not in text
