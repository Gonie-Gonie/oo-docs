"""Shared scoped-numbering policies for countable document objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from string import Formatter
from typing import Literal

from oodocs.styles.counter import CounterStyle


CounterScope = Literal["document", "part", "chapter", "section"]
COUNTER_SCOPES: frozenset[str] = frozenset(
    {"document", "part", "chapter", "section"}
)


@dataclass(frozen=True, slots=True)
class CounterPolicy:
    """Formatting and reset policy for one family of block counters.

    Args:
        scope: Ancestor boundary at which the counter restarts.
        counter: Style used to format the local counter value.
        include_parent: Whether a numbered parent heading is required.
        template: Output template supporting ``{parent}`` and ``{value}``.

    Examples:
        Number equations per chapter as ``2.1``, ``2.2``, and so on:

        ```python
        CounterPolicy(
            scope="chapter",
            include_parent=True,
            template="{parent}.{value}",
        )
        ```
    """

    scope: CounterScope = "document"
    counter: CounterStyle = field(default_factory=CounterStyle)
    include_parent: bool = False
    template: str = "{value}"

    def __post_init__(self) -> None:
        if self.scope not in COUNTER_SCOPES:
            raise ValueError(
                "CounterPolicy.scope must be 'document', 'part', 'chapter', or 'section'"
            )
        if not isinstance(self.counter, CounterStyle):
            raise TypeError("CounterPolicy.counter must be a CounterStyle")
        object.__setattr__(self, "include_parent", bool(self.include_parent))
        if not isinstance(self.template, str) or "{value}" not in self.template:
            raise ValueError("CounterPolicy.template must contain '{value}'")
        fields = {
            field_name
            for _, field_name, _, _ in Formatter().parse(self.template)
            if field_name is not None
        }
        if not fields <= {"parent", "value"}:
            raise ValueError(
                "CounterPolicy.template supports only '{parent}' and '{value}'"
            )
        try:
            self.template.format(parent="1", value="1")
        except (KeyError, ValueError) as exc:
            raise ValueError("CounterPolicy.template is not a valid counter template") from exc

    def format_value(self, value: int, *, parent: str | None = None) -> str:
        """Format one local counter value, optionally with its parent label.

        Raises:
            ValueError: If ``include_parent`` is enabled but no parent heading
                number is available.
        """

        if self.include_parent and parent is None:
            raise ValueError(
                f"CounterPolicy(scope={self.scope!r}) requires a numbered parent heading"
            )
        local_value = self.counter.format_value(value)
        return self.template.format(parent=parent or "", value=local_value)

    def preserves_legacy_integer(self) -> bool:
        """Return whether this policy has the legacy document-wide format."""

        return (
            self.scope == "document"
            and not self.include_parent
            and self.template == "{value}"
            and self.counter == CounterStyle()
        )


@dataclass(slots=True)
class NumberingDefaults:
    """Document-wide policies for built-in countable block families.

    Defaults preserve OODocs' historical document-wide integer numbering.
    ``countable`` applies to theorem-like blocks while their named counter
    namespaces continue to determine which block kinds share a sequence.
    """

    table: CounterPolicy = field(default_factory=CounterPolicy)
    figure: CounterPolicy = field(default_factory=CounterPolicy)
    equation: CounterPolicy = field(default_factory=CounterPolicy)
    listing: CounterPolicy = field(default_factory=CounterPolicy)
    countable: CounterPolicy = field(default_factory=CounterPolicy)

    def __post_init__(self) -> None:
        for field_name in ("table", "figure", "equation", "listing", "countable"):
            if not isinstance(getattr(self, field_name), CounterPolicy):
                raise TypeError(f"NumberingDefaults.{field_name} must be a CounterPolicy")

    def policy_for(self, kind: str) -> CounterPolicy:
        """Return a policy by its built-in counter family name."""

        if kind not in {"table", "figure", "equation", "listing", "countable"}:
            raise ValueError(f"Unsupported numbering policy kind: {kind!r}")
        return getattr(self, kind)


__all__ = [
    "COUNTER_SCOPES",
    "CounterPolicy",
    "CounterScope",
    "NumberingDefaults",
]
