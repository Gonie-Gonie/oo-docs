"""Configuration objects for API collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping, Sequence

from oodocs.apidoc.model import ApiDocstringStyleName


ApiCollectorName = Literal["auto", "inspect", "griffe"]
ApiPublicPolicyName = Literal["__all__", "underscore", "all", "explicit"]


@dataclass(frozen=True, slots=True)
class ApiPublicPolicy:
    """Reusable public API boundary policy.

    Attributes:
        name: Boundary strategy. ``"__all__"`` honors module ``__all__`` when
            present and otherwise falls back to underscore filtering.
        explicit_names: Public names or qualnames used by the ``"explicit"``
            strategy.

    Examples:
        Reuse one policy across multiple repository collections:

        ```python
        from oodocs.apidoc import ApiPublicPolicy, collect_api

        policy = ApiPublicPolicy.explicit("pkg.Widget", "pkg.make_widget")
        api = collect_api(".", public_policy=policy, collector="griffe")
        ```
    """

    name: ApiPublicPolicyName = "__all__"
    explicit_names: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "explicit_names", normalize_explicit_names(self.explicit_names))
        self.validate()

    @classmethod
    def from_value(
        cls,
        value: ApiPublicPolicy | ApiPublicPolicyName | Mapping[str, object] | None = None,
        *,
        explicit_names: Sequence[str] | None = None,
    ) -> ApiPublicPolicy:
        """Return a policy object from a string, mapping, or existing policy.

        Args:
            value: Policy name, serialized mapping, policy object, or ``None``.
            explicit_names: Optional explicit names overriding names from
                ``value``.

        Returns:
            Normalized public policy object.
        """

        if isinstance(value, cls):
            if explicit_names is None:
                return value
            return cls(value.name, normalize_explicit_names(explicit_names))
        if isinstance(value, Mapping):
            policy = cls.from_dict(value)
            if explicit_names is not None:
                return cls(policy.name, normalize_explicit_names(explicit_names))
            return policy
        return cls(
            "__all__" if value is None else value,
            normalize_explicit_names(explicit_names),
        )

    @classmethod
    def explicit(cls, *names: str) -> ApiPublicPolicy:
        """Return an explicit-name public API policy.

        Args:
            *names: Local names or fully qualified names to include.

        Returns:
            Explicit public policy.
        """

        return cls("explicit", normalize_explicit_names(names))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ApiPublicPolicy:
        """Reconstruct a policy from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Public policy object.
        """

        return cls(
            str(data.get("name", "__all__")),  # type: ignore[arg-type]
            normalize_explicit_names(data.get("explicit_names", ())),  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized policy data."""

        return {
            "name": self.name,
            "explicit_names": list(self.explicit_names),
        }

    def validate(self) -> None:
        """Validate the policy.

        Raises:
            ValueError: If the strategy or explicit names are invalid.
        """

        if self.name not in {"__all__", "underscore", "all", "explicit"}:
            raise ValueError("public policy must be '__all__', 'underscore', 'all', or 'explicit'")
        if self.name == "explicit" and not self.explicit_names:
            raise ValueError("explicit_names is required when public policy is 'explicit'")

    def module_name_is_public(
        self,
        name: str,
        qualname: str,
        public_names: set[str] | None,
    ) -> bool:
        """Return whether a module-level object is public.

        Args:
            name: Local object name.
            qualname: Fully qualified object name.
            public_names: Names from module ``__all__``, or ``None`` when the
                module does not define ``__all__``.

        Returns:
            Whether the object is part of the public API boundary.
        """

        if self.name == "all":
            return True
        if self.name == "explicit":
            return name in self.explicit_names or qualname in self.explicit_names
        if self.name == "__all__" and public_names is not None:
            return name in public_names or qualname in public_names
        return not name.startswith("_")

    def member_name_is_public(self, name: str, qualname: str | None = None) -> bool:
        """Return whether a class member is public.

        Args:
            name: Local member name.
            qualname: Optional fully qualified member name.

        Returns:
            Whether the member should be collected as public.
        """

        if self.name == "all":
            return True
        if self.name == "explicit":
            return name in self.explicit_names or bool(qualname and qualname in self.explicit_names)
        return not name.startswith("_")


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
        values.pop("public_api_policy", None)
        explicit_override = "explicit_names" in kwargs and kwargs["explicit_names"] is not None
        values.update({key: value for key, value in kwargs.items() if value is not None})
        if isinstance(values.get("public_policy"), (ApiPublicPolicy, Mapping)):
            policy = ApiPublicPolicy.from_value(
                values["public_policy"],  # type: ignore[arg-type]
                explicit_names=values.get("explicit_names") if explicit_override else None,  # type: ignore[arg-type]
            )
            values["public_policy"] = policy.name
            values["explicit_names"] = policy.explicit_names
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

    def public_api_policy(self) -> ApiPublicPolicy:
        """Return this config's reusable public API policy object."""

        return ApiPublicPolicy(self.public_policy, self.explicit_names)

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
    "ApiPublicPolicy",
    "ApiPublicPolicyName",
    "normalize_explicit_names",
]
