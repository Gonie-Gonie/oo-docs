"""Layout and indexing support for renderers."""

from __future__ import annotations

from importlib import import_module


_EXPORTS = {
    "CaptionEntry": "oodocs.layout.indexing",
    "CitationReferenceEntry": "oodocs.layout.indexing",
    "CommentReferenceEntry": "oodocs.layout.indexing",
    "FootnoteReferenceEntry": "oodocs.layout.indexing",
    "HeadingEntry": "oodocs.layout.indexing",
    "RenderIndex": "oodocs.layout.indexing",
    "build_render_index": "oodocs.layout.indexing",
    "MatterLayout": "oodocs.layout.matter",
    "MatterRegion": "oodocs.layout.matter",
    "partition_document_matter": "oodocs.layout.matter",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> object:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
