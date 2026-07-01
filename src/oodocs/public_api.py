"""Public API tier policy for the top-level :mod:`oodocs` namespace.

Attributes:
    PublicApiTier: Stability tier assigned to a top-level public symbol.
    TOP_LEVEL_EXPORT_LIMIT: Maximum allowed number of top-level exports.
    CORE_TOP_LEVEL_EXPORTS: User-facing symbols expected at the top level.
    DOMAIN_TOP_LEVEL_EXPORTS: Domain-specific symbols allowed at the top level.
    INTERNAL_TOP_LEVEL_EXPORTS: Internal symbols intentionally exposed at the top level.
    FORBIDDEN_TOP_LEVEL_NAME_PATTERNS: Name fragments blocked from top-level export.
    TOP_LEVEL_SYMBOL_TIERS: Mapping from top-level public symbol name to tier.
"""

from __future__ import annotations

from typing import Literal


PublicApiTier = Literal["core", "domain", "internal"]

TOP_LEVEL_EXPORT_LIMIT = 90

CORE_TOP_LEVEL_EXPORTS = frozenset(
    {
        "Affiliation",
        "Author",
        "AuthorLayout",
        "Box",
        "BoxStyle",
        "BulletList",
        "CitationLibrary",
        "CitationSource",
        "Chapter",
        "CodeBlock",
        "ColumnSpan",
        "Comment",
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
        "PageSize",
        "Paragraph",
        "ParagraphStyle",
        "Part",
        "ListOfReferences",
        "Section",
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
        "TitleMatter",
        "Theme",
        "ValidationIssue",
        "ValidationPolicy",
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
        "inline_math",
        "italic",
        "keyboard",
        "line_break",
        "link",
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
        "ResultLike",
    }
)

INTERNAL_TOP_LEVEL_EXPORTS = frozenset()

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
