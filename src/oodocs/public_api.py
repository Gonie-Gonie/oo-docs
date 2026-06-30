"""Public API tier policy for the top-level :mod:`oodocs` namespace."""

from __future__ import annotations

from typing import Literal


PublicApiTier = Literal["core", "domain", "internal"]

TOP_LEVEL_EXPORT_LIMIT = 116

CORE_TOP_LEVEL_EXPORTS = frozenset(
    {
        "Affiliation",
        "Author",
        "AuthorLayout",
        "BlockDefaults",
        "BorderStyle",
        "Box",
        "BoxStyle",
        "BulletList",
        "CaptionDefaults",
        "CitationDefaults",
        "CitationLibrary",
        "CitationSource",
        "Chapter",
        "CodeBlock",
        "ColumnSpan",
        "Comment",
        "CounterStyle",
        "Document",
        "DocumentMetadata",
        "DocumentSettings",
        "DocumentValidationError",
        "Divider",
        "Equation",
        "Figure",
        "Footnote",
        "ImageData",
        "ImportIssue",
        "ImportPolicyError",
        "ImportResult",
        "InlineChip",
        "InlineChipStyle",
        "LineBreak",
        "ListOfFigures",
        "ListOfTables",
        "Math",
        "MultiColumn",
        "NumberedList",
        "OODocsError",
        "OutputBundle",
        "Padding",
        "PageBreak",
        "PageLayout",
        "PageMargins",
        "PageNumberDefaults",
        "PageSize",
        "Paragraph",
        "ParagraphStyle",
        "Part",
        "ReferenceList",
        "Section",
        "StrokeStyle",
        "StyleSheet",
        "SubFigure",
        "SubFigureGroup",
        "SubSubsection",
        "Subsection",
        "Table",
        "TableCell",
        "TableCellStyle",
        "TableOfContents",
        "TableStyle",
        "Text",
        "TextStyle",
        "Theme",
        "TitleMatterDefaults",
        "TypographyDefaults",
        "ValidationIssue",
        "ValidationResult",
        "VerticalSpace",
        "__version__",
        "badge",
        "bold",
        "cite",
        "comment",
        "footnote",
        "highlight",
        "inline_code",
        "italic",
        "keyboard",
        "line_break",
        "link",
        "math",
        "prescript",
        "ref",
        "ref_range",
        "refs",
        "status",
        "strikethrough",
        "subscript",
        "superscript",
        "tag",
        "text_color",
        "url",
    }
)

DOMAIN_TOP_LEVEL_EXPORTS = frozenset(
    {
        "CommentList",
        "FootnoteDefaults",
        "FootnoteList",
        "FootnoteStyle",
        "GeneratedContentDefaults",
        "HeaderFooterDefaults",
        "HeadingNumbering",
        "HeadingStyle",
        "LinkDefaults",
        "ListStyle",
        "LocaleDefaults",
        "OUTPUT_FORMATS",
        "OutputFormat",
        "ResultLike",
        "RunInTitleStyle",
        "TocLevelStyle",
        "markup",
        "styled",
    }
)

INTERNAL_TOP_LEVEL_EXPORTS = frozenset(
    {
        "MAX_SECTION_LEVEL",
        "MIN_SECTION_LEVEL",
        "section_for_level",
        "shift_heading_level",
        "shift_heading_levels",
    }
)

FORBIDDEN_TOP_LEVEL_NAME_PATTERNS = (
    "coerce",
    "normalize",
    "render_to_",
    "build_table_layout",
    "resolve_positioned_boxes",
)

TOP_LEVEL_SYMBOL_TIERS: dict[str, PublicApiTier] = {
    **{name: "core" for name in CORE_TOP_LEVEL_EXPORTS},
    **{name: "domain" for name in DOMAIN_TOP_LEVEL_EXPORTS},
    **{name: "internal" for name in INTERNAL_TOP_LEVEL_EXPORTS},
}

__all__ = [
    "CORE_TOP_LEVEL_EXPORTS",
    "DOMAIN_TOP_LEVEL_EXPORTS",
    "FORBIDDEN_TOP_LEVEL_NAME_PATTERNS",
    "INTERNAL_TOP_LEVEL_EXPORTS",
    "PublicApiTier",
    "TOP_LEVEL_EXPORT_LIMIT",
    "TOP_LEVEL_SYMBOL_TIERS",
]
