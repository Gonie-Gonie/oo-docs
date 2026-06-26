from __future__ import annotations

from oodocs.apidoc import (
    ApiCategory,
    ApiModule,
    ApiObject,
    ApiPackage,
    ApiPresentationProfile,
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
    child_text = "".join(_all_plain_text(child) for child in getattr(block, "children", ()))
    rows = getattr(block, "rows", ())
    row_text = "".join(
        _all_plain_text(getattr(cell, "content", cell))
        for row in rows
        for cell in row
    )
    return text + child_text + row_text


def test_help_book_starts_with_category_contents_not_coverage() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")
    document = api.to_help_book(
        presentation=ApiPresentationProfile.help(),
        include_coverage=True,
        max_level=2,
    )

    titles = _chapter_titles(document)

    assert titles[0] == "API Contents"
    assert "API Documentation Coverage" == titles[-1]
    assert titles.index("Core Document Model") < titles.index("API Documentation Coverage")


def test_help_book_places_common_symbols_in_category_chapters() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")
    document = api.to_help_book(include_coverage=False, max_level=2)
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
    assert "oodocs.Theme" in all_titles
    assert "oodocs.ValidationResult" in all_titles
    assert "API Documentation Coverage" not in titles


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
        max_level=1,
    )
    without_appendix = api.to_help_book(
        categories=categories,
        include_coverage=False,
        include_uncategorized_appendix=False,
        max_level=1,
    )

    assert [obj.qualname for obj in uncategorized] == ["samplepkg.save"]
    assert [issue.qualname for issue in issues] == ["samplepkg.save"]
    assert issues[0].code == "uncategorized-api-object"
    assert "Uncategorized API" in _chapter_titles(document)
    assert "samplepkg.save" in _all_plain_text(document.body)
    assert "Uncategorized API" not in _chapter_titles(without_appendix)
