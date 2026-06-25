"""Layout, indexing, and theme support for renderers."""

from __future__ import annotations

from importlib import import_module


_EXPORTS = {
    "BoxStyle": "oodocs.layout.theme",
    "CaptionEntry": "oodocs.layout.indexing",
    "CitationOptions": "oodocs.layout.theme",
    "CitationReferenceEntry": "oodocs.layout.indexing",
    "CommentReferenceEntry": "oodocs.layout.indexing",
    "FootnoteReferenceEntry": "oodocs.layout.indexing",
    "HeadingEntry": "oodocs.layout.indexing",
    "HeadingNumbering": "oodocs.layout.theme",
    "ListStyle": "oodocs.layout.theme",
    "ParagraphStyle": "oodocs.layout.theme",
    "ParagraphTitleStyle": "oodocs.layout.theme",
    "RenderIndex": "oodocs.layout.indexing",
    "TableStyle": "oodocs.layout.theme",
    "TextStyle": "oodocs.layout.theme",
    "Theme": "oodocs.layout.theme",
    "build_render_index": "oodocs.layout.indexing",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> object:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
