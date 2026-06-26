from __future__ import annotations

from oodocs.apidoc import ApiPresentationProfile, collect_api


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
