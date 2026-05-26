"""Top-level package for docscriptor."""

from importlib.metadata import PackageNotFoundError, version as package_version

from docscriptor.core import DocscriptorError
from docscriptor.components.blocks import (
    Box,
    BulletList,
    Chapter,
    CodeBlock,
    ColumnSpan,
    Divider,
    Equation,
    MultiColumn,
    NumberedList,
    PageBreak,
    Paragraph,
    Part,
    Section,
    Subsection,
    Subsubsection,
    VerticalSpace,
)
from docscriptor.components.generated import CommentsPage, FigureList, ReferencesPage, TableList, TableOfContents, TocLevelStyle
from docscriptor.components.media import Figure, SubFigure, SubFigureGroup, Table, TableCell, TableCellStyle
from docscriptor.components.markup import markup
from docscriptor.components.people import Affiliation, Author, AuthorLayout
from docscriptor.components.references import CitationLibrary, CitationSource
from docscriptor.components.positioning import ImageBox, Shape, TextBox
from docscriptor.document import Document
from docscriptor.importers.markdown import from_markdown, parse_markdown
from docscriptor.components.inline import (
    Comment,
    Footnote,
    InlineChip,
    InlineChipStyle,
    LineBreak,
    Math,
    Text,
    badge,
    bold,
    code,
    color,
    cite,
    comment,
    footnote,
    highlight,
    italic,
    keyboard,
    link,
    line_break,
    math,
    prescript,
    reference,
    status,
    strike,
    strikethrough,
    styled,
    subscript,
    superscript,
    tag,
)
from docscriptor.settings import (
    BlockOptions,
    BoxStyle,
    CaptionOptions,
    CitationOptions,
    DocumentSettings,
    GeneratedPageOptions,
    HeadingNumbering,
    ListStyle,
    PageNumberOptions,
    PageMargins,
    PageSize,
    ParagraphStyle,
    TableStyle,
    TextStyle,
    TitleMatterOptions,
    TypographyOptions,
    Theme,
)


def _resolve_version() -> str:
    try:
        return package_version("docscriptor")
    except PackageNotFoundError:
        try:
            from setuptools_scm import get_version
        except ImportError:
            return "0.7.0"
        return get_version(
            root="../..",
            relative_to=__file__,
            fallback_version="0.7.0",
            tag_regex=r"^v(?P<version>\d+\.\d+\.\d+)$",
        )


__version__ = _resolve_version()

__all__ = [
    "Affiliation",
    "Author",
    "AuthorLayout",
    "BlockOptions",
    "Box",
    "BoxStyle",
    "BulletList",
    "CaptionOptions",
    "CitationOptions",
    "CitationLibrary",
    "CitationSource",
    "Chapter",
    "Comment",
    "CommentsPage",
    "CodeBlock",
    "ColumnSpan",
    "Document",
    "DocumentSettings",
    "DocscriptorError",
    "Divider",
    "Equation",
    "Figure",
    "FigureList",
    "Footnote",
    "GeneratedPageOptions",
    "HeadingNumbering",
    "ImageBox",
    "InlineChip",
    "InlineChipStyle",
    "LineBreak",
    "ListStyle",
    "Math",
    "MultiColumn",
    "NumberedList",
    "PageNumberOptions",
    "PageMargins",
    "PageSize",
    "PageBreak",
    "Paragraph",
    "Part",
    "ParagraphStyle",
    "ReferencesPage",
    "Section",
    "Shape",
    "SubFigure",
    "SubFigureGroup",
    "Subsection",
    "Subsubsection",
    "Table",
    "TableCell",
    "TableCellStyle",
    "TableStyle",
    "TableOfContents",
    "TableList",
    "Text",
    "TextBox",
    "TextStyle",
    "TitleMatterOptions",
    "Theme",
    "TocLevelStyle",
    "TypographyOptions",
    "VerticalSpace",
    "__version__",
    "badge",
    "bold",
    "code",
    "color",
    "cite",
    "comment",
    "footnote",
    "from_markdown",
    "highlight",
    "italic",
    "keyboard",
    "link",
    "line_break",
    "math",
    "prescript",
    "reference",
    "status",
    "strike",
    "strikethrough",
    "markup",
    "styled",
    "parse_markdown",
    "subscript",
    "superscript",
    "tag",
]

for _module_name in ("components", "core", "document", "layout", "settings"):
    globals().pop(_module_name, None)

del _resolve_version
del _module_name
