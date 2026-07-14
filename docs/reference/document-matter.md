# Document Matter Reference

Use explicit matter containers when a report, book, or manual needs a stable
front/main/back boundary. Each container is a direct child of `Document` and
accepts the same block inputs as the document body.

```python
from oodocs import (
    BackMatter,
    Chapter,
    Document,
    FrontMatter,
    ListOfFigures,
    ListOfReferences,
    ListOfTables,
    MainMatter,
    Paragraph,
    TableOfContents,
)

document = Document(
    "Operations Manual",
    FrontMatter(
        TableOfContents(),
        ListOfFigures(),
        ListOfTables(),
    ),
    MainMatter(
        Chapter("Overview", Paragraph("Primary document content.")),
        start_on_new_page=True,
    ),
    BackMatter(
        ListOfReferences(),
        page_break_before=True,
    ),
)
```

`FrontMatter`, `MainMatter`, and `BackMatter` support `add()` and `extend()` for
incremental construction. `page_break_before=True` and
`start_on_new_page=True` both request a new physical page before that region;
the two names let callers express either document structure or layout intent.

## Structure and validation

Matter containers must remain top-level, appear in front/main/back order, and
occur at most once per kind. Validation reports stable error codes:

| Condition | Code |
| --- | --- |
| A matter container inside another matter container | `nested-matter` |
| More than one container of the same kind | `duplicate-matter` |
| Front, main, and back containers in the wrong order | `matter-order` |

The presence of any explicit container disables the legacy numbered-chapter
heuristic for the whole document. Explicit children populate their declared
region; ordinary top-level blocks alongside them are treated as main matter.
When no explicit container exists, compatibility behavior is retained: blocks
before the first numbered part or level-1 chapter are inferred as front matter.
A simple document without such a heading stays one continuous main-matter flow.

`Document.matter_layout()` returns the shared renderer-neutral partition.
`split_top_level_children()` remains available for compatibility and returns
front matter plus combined main/back content.

## Page numbering

The default policy is equivalent to:

```python
from oodocs.styles import CounterStyle, PageNumberDefaults

page_numbers = PageNumberDefaults(
    show_page_numbers=True,
    front_matter_counter=CounterStyle(counter_format="lower-roman"),
    main_matter_counter=CounterStyle(counter_format="decimal"),
    back_matter_counter=None,
    restart_main_matter=True,
    restart_back_matter=False,
)
```

Front matter therefore uses lower-case Roman labels, main matter restarts at
decimal 1, and back matter continues the main-matter style and sequence. Set a
`back_matter_counter` and `restart_back_matter=True` when a separate back-matter
sequence is required. A cover page remains part of the physical page count but
does not display a page number.

HTML emits `oodocs-front-matter`, `oodocs-main-matter`, and
`oodocs-back-matter` section classes. Regions that begin on a new page also get
`oodocs-page-break-before`, whose print CSS uses `break-before: page` with the
legacy `page-break-before` fallback. DOCX and PDF use the same shared matter
partition for section/page transitions and counter changes.
