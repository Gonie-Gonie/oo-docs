# List Support Reference

OODocs covers common `enumitem` list authoring needs with explicit list blocks
and reusable marker styles.

## Authoring Objects

| Need | Use | Notes |
|---|---|---|
| Bullet list | `BulletList(...)` | Uses bullet markers by default and accepts strings, paragraphs, and nested item children. |
| Numbered list | `NumberedList(...)` | Uses decimal numbering by default. Pass `start=...` for a custom first number. |
| Resume numbering | `NumberedList(..., resume_from=previous)` | Continues after the previous numbered list. `start` and `resume_from` are mutually exclusive. |
| Marker format | `CounterStyle(counter_format=..., prefix=..., suffix=..., bullet=...)` | Controls decimal, roman, alpha, bullet, and wrapper text. |
| List spacing and indent | `ListStyle(indent=..., marker_gap=..., item_spacing=..., block_spacing=...)` | Applies renderer-independent spacing values to DOCX, PDF, and HTML. |
| Named list style | `StyleSheet.register_list(name, ListStyle(...))` | Lets several lists share one style by passing `style=name`. |
| Nested list | `item_children=[[BulletList(...), NumberedList(...)]]` | Attaches child lists to individual list items while preserving document structure. |

## Policies

`NumberedList(start=...)` sets the first marker directly. `NumberedList(
resume_from=previous)` computes the next start value from the previous list's
item count, so resumed lists stay stable when items are inserted earlier.

Nested lists inherit the surrounding renderer context and may override marker,
spacing, and indent with their own direct kwargs or `ListStyle`. Prefer a named
style when several nested lists should use the same `enumitem`-like setup.
