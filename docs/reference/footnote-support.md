# Footnote Support Reference

OODocs covers common `footmisc` and `manyfoot` authoring needs with inline
footnote objects, document-wide marker styles, and renderer-aware placement
fallbacks.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Inline footnote | `footnote("term", "note")` | Creates visible inline text with an attached note body. |
| Explicit class form | `Footnote.annotated("term", "note")` | Equivalent to the helper when code needs the concrete fragment type. |
| Independent stream | `footnote("term", "note", stream="symbols")` | Streams are numbered independently, similar to manyfoot-style note series. |
| Stream marker defaults | `Theme(footnotes=FootnoteDefaults(...))` | Keeps footnote stream policy in the document theme. |
| Symbol markers | `FootnoteStyle.symbol()` | Uses the default symbol cycle, or pass a custom symbol sequence. |
| Custom numeric markers | `FootnoteStyle(CounterStyle(prefix="R"))` | Supports decimal, alphabetic, roman, prefixed, and suffixed markers through `CounterStyle`. |
| Generated footnote list | `ListOfFootnotes()` from `oodocs.generated` | Places the generated notes page at an explicit point in the document. |
| Document-end placement | `Theme(blocks=BlockDefaults(footnote_placement="document"))` | Collects notes into the generated list instead of requesting page-bottom output. |

## Stream And Marker Policy

The default stream is named `default` and uses plain decimal markers. Custom
streams such as `symbols` or `review` have independent counters. Configure
their marker style with `FootnoteDefaults(stream_styles={...})`; streams not
listed there use `default_style`.

`FootnoteStyle.symbol(("*", "#"))` repeats symbols when a stream has more
notes than symbols: the first cycle is `*`, `#`, and the next cycle is `**`,
`##`.

## Renderer Mapping

DOCX uses native page-bottom Word footnotes only for the default stream with
plain decimal markers. Custom streams or symbol markers render through the
generated footnote list and emit the
`docx-footnote-stream-generated-list` compatibility note.

PDF and HTML render generated markers and collected notes from the same
stream-local index. Page-bottom placement remains renderer-dependent, so use
document-end placement when exact cross-format positioning matters more than
native Word footnote behavior.
