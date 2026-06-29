"""Public style objects and theme configuration."""

from oodocs.styles.blocks import (
    BoxStyle,
    ParagraphStyle,
    RunInTitleStyle,
    box_style_with_overrides,
    paragraph_style_with_overrides,
)
from oodocs.styles.border import BorderStyle, StrokeStyle
from oodocs.styles.chips import InlineChipStyle
from oodocs.styles.counter import (
    CounterStyle,
    HeadingNumbering,
    ListStyle,
    list_style_with_overrides,
)
from oodocs.styles.sheet import StyleSheet
from oodocs.styles.tables import (
    TableCellStyle,
    TableCellStyleInput,
    TableStyle,
    coerce_table_cell_style,
    table_style_with_overrides,
)
from oodocs.styles.spacing import Padding
from oodocs.styles.text import TextStyle
from oodocs.styles.theme import (
    BlockDefaults,
    CaptionDefaults,
    CitationDefaults,
    FootnoteDefaults,
    FootnoteStyle,
    GeneratedContentDefaults,
    HeaderFooterDefaults,
    HeadingStyle,
    LinkDefaults,
    LocaleDefaults,
    PageNumberDefaults,
    Theme,
    TitleMatterDefaults,
    TypographyDefaults,
)

__all__ = [
    "BlockDefaults",
    "BorderStyle",
    "BoxStyle",
    "CaptionDefaults",
    "CitationDefaults",
    "CounterStyle",
    "FootnoteDefaults",
    "FootnoteStyle",
    "GeneratedContentDefaults",
    "HeaderFooterDefaults",
    "HeadingStyle",
    "HeadingNumbering",
    "LinkDefaults",
    "LocaleDefaults",
    "InlineChipStyle",
    "ListStyle",
    "PageNumberDefaults",
    "Padding",
    "ParagraphStyle",
    "RunInTitleStyle",
    "StrokeStyle",
    "StyleSheet",
    "TableCellStyle",
    "TableCellStyleInput",
    "TableStyle",
    "TextStyle",
    "Theme",
    "TitleMatterDefaults",
    "TypographyDefaults",
    "box_style_with_overrides",
    "coerce_table_cell_style",
    "list_style_with_overrides",
    "paragraph_style_with_overrides",
    "table_style_with_overrides",
]
