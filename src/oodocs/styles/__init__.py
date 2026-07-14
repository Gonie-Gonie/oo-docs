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
from oodocs.styles.cover import CoverAlignment, CoverPageStyle, CoverVerticalAlignment
from oodocs.styles.counter import (
    CounterStyle,
    HeadingNumbering,
    ListStyle,
    list_style_with_overrides,
)
from oodocs.styles.descriptions import (
    DescriptionListLayout,
    DescriptionListStyle,
    description_list_style_with_overrides,
)
from oodocs.styles.numbering import (
    COUNTER_SCOPES,
    CounterPolicy,
    CounterScope,
    NumberingDefaults,
)
from oodocs.styles.references import REFERENCE_KINDS, ReferenceDefaults, ReferenceTemplate
from oodocs.styles.sheet import StyleCategory, StyleSheet
from oodocs.styles.tables import (
    TableCellStyle,
    TableCellStyleInput,
    TableStyle,
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
    "CounterPolicy",
    "CounterScope",
    "COUNTER_SCOPES",
    "CoverAlignment",
    "CoverPageStyle",
    "CoverVerticalAlignment",
    "DescriptionListLayout",
    "DescriptionListStyle",
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
    "NumberingDefaults",
    "PageNumberDefaults",
    "Padding",
    "ParagraphStyle",
    "RunInTitleStyle",
    "ReferenceDefaults",
    "ReferenceTemplate",
    "REFERENCE_KINDS",
    "StrokeStyle",
    "StyleSheet",
    "StyleCategory",
    "TableCellStyle",
    "TableCellStyleInput",
    "TableStyle",
    "TextStyle",
    "Theme",
    "TitleMatterDefaults",
    "TypographyDefaults",
    "box_style_with_overrides",
    "description_list_style_with_overrides",
    "list_style_with_overrides",
    "paragraph_style_with_overrides",
    "table_style_with_overrides",
]
