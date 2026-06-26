"""Public style objects and theme configuration."""

from oodocs.styles.blocks import (
    BoxStyle,
    ParagraphStyle,
    RunInTitleStyle,
    box_style_with_overrides,
    paragraph_style_with_overrides,
)
from oodocs.styles.counter import (
    HeadingNumbering,
    ListStyle,
    list_style_with_overrides,
)
from oodocs.styles.tables import TableStyle, table_style_with_overrides
from oodocs.styles.text import TextStyle
from oodocs.styles.theme import (
    BlockDefaults,
    CaptionDefaults,
    CitationDefaults,
    GeneratedContentDefaults,
    PageNumberDefaults,
    Theme,
    TitleMatterDefaults,
    TypographyDefaults,
)

__all__ = [
    "BlockDefaults",
    "BoxStyle",
    "CaptionDefaults",
    "CitationDefaults",
    "GeneratedContentDefaults",
    "HeadingNumbering",
    "ListStyle",
    "PageNumberDefaults",
    "ParagraphStyle",
    "RunInTitleStyle",
    "TableStyle",
    "TextStyle",
    "Theme",
    "TitleMatterDefaults",
    "TypographyDefaults",
    "box_style_with_overrides",
    "list_style_with_overrides",
    "paragraph_style_with_overrides",
    "table_style_with_overrides",
]
