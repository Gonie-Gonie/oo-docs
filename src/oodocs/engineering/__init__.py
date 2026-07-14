"""Engineering-oriented authoring primitives.

The namespace intentionally contains presentation objects only.  Unit-system
adapters and symbolic-math adapters live under :mod:`oodocs.integrations`.
"""

from __future__ import annotations

from oodocs.components.blocks import Algorithm
from oodocs.engineering.quantity import NumberFormat, Quantity

__all__ = [
    "Algorithm",
    "NumberFormat",
    "Quantity",
]
