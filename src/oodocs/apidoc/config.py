"""Configuration objects for API collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

from oodocs.apidoc.model import ApiDocstringStyleName


ApiCollectorName = Literal["auto", "inspect", "griffe"]
ApiPublicPolicyName = Literal["__all__", "underscore", "all", "explicit"]


@dataclass(frozen=True, slots=True)
class ApiCollectConfig:
    """Configuration for API collection.

    Attributes:
        collector: Collector backend. ``"auto"`` prefers griffe-compatible
            source collection and falls back to inspect-compatible collection.
        public_policy: Public API boundary policy.
        explicit_names: Names included when ``public_policy="explicit"``.
        docstring_style: Docstring parser style.
        include_imported: Whether imported objects may be included.
        include_inherited: Whether inherited class members may be included.
        class_signature_from_init: Whether class signatures use ``__init__``.

    Examples:
        ```python
        from oodocs.apidoc import ApiCollectConfig, collect_api

        config = ApiCollectConfig(public_policy="__all__", docstring_style="auto")
        api = collect_api("oodocs", config=config)
        ```
    """

    collector: ApiCollectorName = "auto"
    public_policy: ApiPublicPolicyName = "__all__"
    explicit_names: tuple[str, ...] = field(default_factory=tuple)
    docstring_style: ApiDocstringStyleName = "auto"
    include_imported: bool = False
    include_inherited: bool = False
    class_signature_from_init: bool = True

    @classmethod
    def from_kwargs(
        cls,
        config: ApiCollectConfig | None = None,
        **kwargs: object,
    ) -> ApiCollectConfig:
        """Create a config object from explicit keyword overrides.

        Args:
            config: Optional base config.
            **kwargs: Field overrides.

        Returns:
            Validated configuration.
        """

        values = config.to_dict() if config is not None else {}
        values.update({key: value for key, value in kwargs.items() if value is not None})
        if "explicit_names" in values and not isinstance(values["explicit_names"], tuple):
            values["explicit_names"] = tuple(values["explicit_names"])  # type: ignore[arg-type]
        resolved = cls(**values)  # type: ignore[arg-type]
        resolved.validate()
        return resolved

    def validate(self) -> None:
        """Validate config values.

        Raises:
            ValueError: If an option is unsupported or incomplete.
        """

        if self.collector not in {"auto", "inspect", "griffe"}:
            raise ValueError("collector must be 'auto', 'inspect', or 'griffe'")
        if self.public_policy not in {"__all__", "underscore", "all", "explicit"}:
            raise ValueError("public_policy must be '__all__', 'underscore', 'all', or 'explicit'")
        if self.public_policy == "explicit" and not self.explicit_names:
            raise ValueError("explicit_names is required when public_policy='explicit'")
        if self.docstring_style not in {"auto", "google", "numpy", "sphinx", "markdown", "plain"}:
            raise ValueError("docstring_style is not supported")

    def to_dict(self) -> dict[str, object]:
        """Return this config as JSON-serializable data."""

        return {
            "collector": self.collector,
            "public_policy": self.public_policy,
            "explicit_names": list(self.explicit_names),
            "docstring_style": self.docstring_style,
            "include_imported": self.include_imported,
            "include_inherited": self.include_inherited,
            "class_signature_from_init": self.class_signature_from_init,
        }


def normalize_explicit_names(names: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize explicit public API names.

    Args:
        names: Optional input names.

    Returns:
        Deduplicated tuple preserving sorted deterministic order.
    """

    return tuple(sorted({name.strip() for name in names or () if name.strip()}))


__all__ = [
    "ApiCollectConfig",
    "ApiCollectorName",
    "ApiPublicPolicyName",
    "normalize_explicit_names",
]
