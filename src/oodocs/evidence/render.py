"""Rendering helpers for evidence items."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from oodocs._paths import display_path
from oodocs.components.blocks import CodeBlock, Paragraph, Section
from oodocs.components.inline import inline_code
from oodocs.components.media import Table
from oodocs.styles import TableStyle

if TYPE_CHECKING:
    from oodocs.evidence.model import EvidenceItem


def render_evidence_item(item: EvidenceItem) -> Section:
    """Render one existing evidence item to an OODocs section."""

    title = item.title or item.path.stem.replace("-", " ").replace("_", " ").title()
    children: list[object] = [
        Paragraph("Read from ", inline_code(display_path(item.path)), ".")
    ]
    if item.description:
        children.append(Paragraph(item.description))

    kind = item.resolved_kind()
    if kind == "csv":
        children.append(
            Table.from_csv(
                item.path,
                caption=f"Rows from {item.path.name}.",
                style=TableStyle.evidence(),
            )
        )
    elif kind == "json":
        payload = json.loads(item.path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            children.append(
                Table.from_mapping(
                    payload,
                    caption=f"Values from {item.path.name}.",
                    style=TableStyle.evidence(),
                )
            )
        elif isinstance(payload, list) and all(isinstance(row, dict) for row in payload):
            children.append(
                Table.from_records(
                    payload,
                    caption=f"Rows from {item.path.name}.",
                    style=TableStyle.evidence(),
                )
            )
        else:
            children.append(
                CodeBlock(json.dumps(payload, indent=2, ensure_ascii=False), language="json")
            )
    else:
        children.append(
            CodeBlock(
                item.path.read_text(encoding="utf-8", errors="replace").rstrip(),
                language="text",
            )
        )
    return Section(title or "Evidence item", children, numbered=False, toc=True)


__all__ = ["render_evidence_item"]
