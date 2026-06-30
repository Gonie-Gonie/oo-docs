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

    assert titles[0] == "API Contents"
    assert "API Documentation Coverage" == titles[-1]
    assert titles.index("Core Document Model") < titles.index("API Documentation Coverage")


def test_help_book_places_common_symbols_in_category_chapters() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")
    document = api.to_help_book(include_coverage=False, max_heading_level=2)
    titles = _chapter_titles(document)
    all_titles = [
        title
        for chapter in document.body.children
        for title in _all_titles(chapter)
    ]

    assert "Core Document Model" in titles
    assert "Tables and Figures" in titles
    assert "Layout and Theme" in titles
    assert "oodocs.Document" in all_titles
    assert "oodocs.Paragraph" in all_titles
    assert "oodocs.Table" in all_titles
    assert "oodocs.Figure" in all_titles
    assert "oodocs.compatibility.OUTPUT_FORMATS" in all_titles
    assert "oodocs.components.blocks.MIN_SECTION_LEVEL" in all_titles
    assert "oodocs.Theme" in all_titles
    assert "oodocs.ValidationResult" in all_titles
    assert "oodocs.document.Document" not in all_titles
    assert "oodocs.validation.ValidationResult" not in all_titles
    assert "oodocs.components.media.Table" not in all_titles
    assert "oodocs.settings.PageLayout" not in all_titles
    assert "oodocs.presets.components.CompactTable" in all_titles
    assert "oodocs.presets.templates.JournalArticleTemplate" in all_titles
    assert "oodocs.presets.CompactTable" not in all_titles
    assert "oodocs.presets.JournalArticleTemplate" not in all_titles
    assert check_api_help_categories(api) == ()
    assert "API Documentation Coverage" not in titles
    assert "Uncategorized API" not in titles
    assert "Renderer Extension API" not in titles


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
