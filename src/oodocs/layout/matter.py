"""Shared document-matter partitioning used by every renderer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from oodocs.components.matter import BackMatter, DocumentMatter, FrontMatter, MainMatter


@dataclass(frozen=True, slots=True)
class MatterRegion:
    """Resolved children and page-break policy for one matter region."""

    children: tuple[object, ...] = ()
    page_break_before: bool = False


@dataclass(frozen=True, slots=True)
class MatterLayout:
    """Renderer-neutral front/main/back partition for a document."""

    front: MatterRegion
    main: MatterRegion
    back: MatterRegion
    explicit: bool = False


def partition_document_matter(children: Sequence[object]) -> MatterLayout:
    """Resolve explicit matter, or apply the compatibility heuristic once.

    The presence of any explicit matter container disables inference. Ordinary
    top-level blocks that accompany explicit containers are treated as main
    matter, which keeps mixed documents renderable while validation can report
    structural mistakes.
    """

    explicit = any(isinstance(child, DocumentMatter) for child in children)
    if explicit:
        regions: dict[str, list[object]] = {"front": [], "main": [], "back": []}
        breaks = {"front": False, "main": False, "back": False}
        for child in children:
            if isinstance(child, DocumentMatter):
                regions[child.kind].extend(child.children)
                breaks[child.kind] = breaks[child.kind] or child.requires_page_break
            else:
                regions["main"].append(child)
        return MatterLayout(
            front=MatterRegion(tuple(regions["front"]), breaks["front"]),
            main=MatterRegion(tuple(regions["main"]), breaks["main"]),
            back=MatterRegion(tuple(regions["back"]), breaks["back"]),
            explicit=True,
        )

    for index, child in enumerate(children):
        level = getattr(child, "level", None)
        numbered = getattr(child, "numbered", False)
        if level in {0, 1} and numbered:
            return MatterLayout(
                front=MatterRegion(tuple(children[:index])),
                main=MatterRegion(tuple(children[index:])),
                back=MatterRegion(),
            )

    # A simple document is one continuous main-matter flow. This avoids
    # assigning roman page numbers merely because it contains no chapter.
    return MatterLayout(
        front=MatterRegion(),
        main=MatterRegion(tuple(children)),
        back=MatterRegion(),
    )


__all__ = ["MatterLayout", "MatterRegion", "partition_document_matter"]
