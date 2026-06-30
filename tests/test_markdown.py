from __future__ import annotations

from oodocs import (
    BulletList,
    Chapter,
    CodeBlock,
    Box,
    Divider,
    Document,
    Figure,
    Paragraph,
    Section,
    Subsection,
    SubSubsection,
    Table,
    TableOfContents,
    shift_heading_levels,
)
from oodocs.components.inline import Hyperlink
from oodocs.components.markup import markup
from oodocs.importers import (
    from_markdown,
    from_markdown_file,
    parse_markdown,
    parse_markdown_file,
)
from oodocs.layout.indexing import build_render_index

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_parse_markdown_maps_commonmark_and_gfm_blocks() -> None:
    blocks = parse_markdown(
        """# Release Notes

Intro with **stable** text, ~~old behavior~~, [docs](https://example.com/docs), and https://example.com.

## Added
- [x] Markdown parser
- [ ] User guide updates

| Area | Status |
| :--- | ---: |
| API | `parse_markdown` |
| Docs | **updated** |

> Review note
> with a continuation line.

---

```python
print("ok")
```
"""
    ).blocks

    assert len(blocks) == 1
    chapter = blocks[0]
    assert isinstance(chapter, Chapter)
    assert chapter.plain_title() == "Release Notes"

    intro = chapter.children[0]
    assert isinstance(intro, Paragraph)
    assert any(fragment.value == "stable" and fragment.style.bold for fragment in intro.content)
    assert any(
        fragment.value == "old behavior" and fragment.style.strikethrough
        for fragment in intro.content
    )
    links = [fragment for fragment in intro.content if isinstance(fragment, Hyperlink)]
    assert [link.target for link in links] == [
        "https://example.com/docs",
        "https://example.com",
    ]

    added = chapter.children[1]
    assert isinstance(added, Section)
    assert added.plain_title() == "Added"

    task_list = added.children[0]
    assert isinstance(task_list, BulletList)
    assert task_list.style is not None
    assert task_list.style.marker.counter_format == "none"
    assert [item.plain_text() for item in task_list.items] == [
        "[x] Markdown parser",
        "[ ] User guide updates",
    ]

    table = added.children[1]
    assert isinstance(table, Table)
    assert [cell.content.plain_text() for cell in table.headers] == ["Area", "Status"]
    assert table.rows[0][1].content.plain_text() == "parse_markdown"
    assert table.column_styles[0].text_alignment == "left"
    assert table.column_styles[1].text_alignment == "right"

    assert isinstance(added.children[2], Box)
    assert isinstance(added.children[3], Divider)
    assert isinstance(added.children[4], CodeBlock)
    assert added.children[4].language == "python"


def test_from_markdown_uses_first_h1_as_document_title() -> None:
    document = from_markdown(
        """# Parsed Document

Lead paragraph.

## Details
Body paragraph.
"""
    )

    assert document.title == "Parsed Document"
    assert isinstance(document.body.children[0], Paragraph)
    assert isinstance(document.body.children[1], Section)
    assert document.body.children[1].plain_title() == "Details"

    explicit_title = Document.from_markdown("# Kept Heading\n\nBody.", title="Manual Title")
    assert explicit_title.title == "Manual Title"
    assert isinstance(explicit_title.body.children[0], Chapter)

    fallback_title = Document.from_markdown("Body only.")
    assert fallback_title.title == "Markdown Document"


def test_markdown_file_import_resolves_local_images_as_editable_figures(tmp_path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    image_path = assets_dir / "plot.png"
    image_path.write_bytes(_TINY_PNG)
    markdown_path = tmp_path / "report.md"
    markdown_path.write_text(
        "# Imported Report\n\n![Result chart](assets/plot.png)\n",
        encoding="utf-8",
    )

    blocks = parse_markdown_file(markdown_path).blocks
    document = from_markdown_file(markdown_path)

    assert document.title == "Imported Report"
    assert len(blocks) == 1
    chapter = blocks[0]
    assert isinstance(chapter, Chapter)
    figure = chapter.children[0]
    assert isinstance(figure, Figure)
    assert figure.image_source == image_path
    assert figure.caption is not None
    assert figure.caption.plain_text() == "Result chart"
    assert document.validate().ok


def test_markdown_import_can_keep_headings_unnumbered() -> None:
    document = Document.from_markdown(
        """# Release v1.2.3

## Highlights
Body paragraph.
""",
        numbered=False,
    )

    assert document.title == "Release v1.2.3"
    section = document.body.children[0]
    assert isinstance(section, Section)
    assert section.plain_title() == "Highlights"
    assert section.numbered is False
    assert section.toc is False

    toc_document = Document.from_markdown(
        """# Release v1.2.3

## Highlights
Body paragraph.
""",
        numbered=False,
        toc=True,
    )
    toc_section = toc_document.body.children[0]
    assert isinstance(toc_section, Section)
    assert toc_section.numbered is False
    assert toc_section.toc is True

    render_index = build_render_index(Document("Digest", TableOfContents(), toc_section))
    assert render_index.heading_number(toc_section) is None
    assert render_index.heading_anchor(toc_section) is not None
    assert [entry.number for entry in render_index.headings] == [None]


def test_markdown_import_can_shift_heading_levels() -> None:
    blocks = parse_markdown(
        """## Release

### Highlights
Body paragraph.
""",
        heading_level_shift=1,
    ).blocks

    release = blocks[0]
    assert isinstance(release, Subsection)
    assert release.level == 3
    highlights = release.children[0]
    assert isinstance(highlights, SubSubsection)
    assert highlights.level == 4

    promoted = parse_markdown(
        """## Release
Body paragraph.
""",
        heading_level_shift=-1,
    ).blocks
    assert isinstance(promoted[0], Chapter)

    try:
        parse_markdown("# Too high", heading_level_shift=-1)
    except ValueError as exc:
        assert "cannot be shifted" in str(exc)
    else:
        raise AssertionError("Expected heading_level_shift below the top level to fail")

    try:
        parse_markdown("###### Too low", heading_level_shift=1)
    except ValueError as exc:
        assert "cannot be shifted" in str(exc)
    else:
        raise AssertionError("Expected heading_level_shift below the bottom level to fail")


def test_section_objects_can_shift_heading_levels() -> None:
    paragraph = Paragraph("Body paragraph.")
    blocks = [
        Chapter("Release", Section("Highlights", paragraph)),
        Paragraph("Keep me as a paragraph."),
    ]

    shifted = shift_heading_levels(blocks, 1)
    assert isinstance(shifted[0], Section)
    assert shifted[0].level == 2
    assert isinstance(shifted[0].children[0], Subsection)
    assert shifted[0].children[0].level == 3
    assert shifted[0].children[0].children[0] is paragraph
    assert shifted[1] is blocks[1]

    try:
        shift_heading_levels([Chapter("Release")], -1)
    except ValueError as exc:
        assert "outside the supported range" in str(exc)
    else:
        raise AssertionError("Expected shifting above the top section level to fail")


def test_parse_markdown_preserves_nested_lists() -> None:
    blocks = parse_markdown(
        """## Highlights
- Added page-positioned drawing items:
  - `Shape(...)`
  - `TextBox(...)`
- Added inline drawing placement.
"""
    ).blocks

    assert len(blocks) == 1
    section = blocks[0]
    assert isinstance(section, Section)
    list_block = section.children[0]
    assert isinstance(list_block, BulletList)
    assert [item.plain_text() for item in list_block.items] == [
        "Added page-positioned drawing items:",
        "Added inline drawing placement.",
    ]
    assert len(list_block.item_children[0]) == 1
    nested_list = list_block.item_children[0][0]
    assert isinstance(nested_list, BulletList)
    assert [item.plain_text() for item in nested_list.items] == [
        "Shape(...)",
        "TextBox(...)",
    ]
    assert list_block.item_children[1] == []


def test_markup_resolves_reference_links_and_gfm_inline_styles() -> None:
    fragments = markup(
        "Use [the docs][docs], ~~remove this~~, and <support@example.com>.",
        references={"docs": "https://example.com/docs"},
    )

    link_fragments = [fragment for fragment in fragments if isinstance(fragment, Hyperlink)]
    assert [fragment.target for fragment in link_fragments] == [
        "https://example.com/docs",
        "mailto:support@example.com",
    ]
    assert any(fragment.style.strikethrough for fragment in fragments)
