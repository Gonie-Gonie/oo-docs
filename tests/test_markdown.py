from __future__ import annotations

from docscriptor import (
    BulletList,
    Chapter,
    CodeBlock,
    Box,
    Divider,
    Document,
    Paragraph,
    Section,
    Table,
    from_markdown,
    parse_markdown,
)
from docscriptor.components.inline import Hyperlink
from docscriptor.components.markup import markup


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
    )

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
    assert task_list.style.marker_format == "none"
    assert [item.plain_text() for item in task_list.items] == [
        "[x] Markdown parser",
        "[ ] User guide updates",
    ]

    table = added.children[1]
    assert isinstance(table, Table)
    assert [cell.content.plain_text() for cell in table.headers] == ["Area", "Status"]
    assert table.rows[0][1].content.plain_text() == "parse_markdown"
    assert table.column_styles[0].horizontal_alignment == "left"
    assert table.column_styles[1].horizontal_alignment == "right"

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
