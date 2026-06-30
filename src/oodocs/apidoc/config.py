"""Configuration objects for API collection.

Attributes:
    ApiCollectorName: Literal collector backend names.
    ApiFallbackCollectorName: Literal collector fallback policy names.
    ApiPublicPolicyName: Literal public API boundary policy names.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import tomllib
from typing import TYPE_CHECKING, Iterable, Literal, Mapping, Sequence

from oodocs.compatibility import normalize_output_formats
from oodocs.core import PathLike

if TYPE_CHECKING:
    from oodocs.apidoc.coverage import ApiCoverageResult
    from oodocs.apidoc.diff import ApiSnapshot
    from oodocs.apidoc.model import ApiPackage
    from oodocs.document import Document

ApiCollectorName = Literal["auto", "inspect", "griffe"]
ApiFallbackCollectorName = Literal["inspect", "none"]
ApiPublicPolicyName = Literal["__all__", "underscore", "all", "explicit"]

_COLLECT_CONFIG_KEYS = {
    "class_signature_from_init",
    "collector",
    "docstring_parser_modules",
    "docstring_style",
    "explicit_names",
    "fallback_collector",
    "fallback_parser",
    "include_attributes",
    "include_imported",
    "include_inherited",
    "include_methods",
    "include_private",
    "include_properties",
    "include_source_locations",
    "module_exclude_patterns",
    "module_include_patterns",
    "object_exclude_patterns",
    "object_include_patterns",
    "public_api_policy",
    "public_policy",
}
_BUILD_CONFIG_KEYS = {
    "include_coverage",
    "include_uncategorized_appendix",
    "kind",
    "max_heading_level",
    "module_prefix",
    "output_dir",
    "output_formats",
    "presentation",
    "sidecars",
    "stem",
}


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

        Examples:
            Normalize a value accepted by ``collect_api(...)`` before sharing
            it across multiple collections:

            ```python
            from oodocs.apidoc import ApiPublicPolicy, collect_api

            policy = ApiPublicPolicy.from_value(
                {"name": "explicit", "explicit_names": ["mypkg.load"]},
            )
            api = collect_api(".", public_policy=policy)
            ```
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

        Examples:
            Collect only a curated public surface from a repository:

            ```python
            from oodocs.apidoc import ApiPublicPolicy, collect_api

            policy = ApiPublicPolicy.explicit("mypkg.Client", "mypkg.connect")
            api = collect_api(".", public_policy=policy)
            ```
        """

        return cls("explicit", normalize_explicit_names(names))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ApiPublicPolicy:
        """Reconstruct a policy from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Public policy object.

        Examples:
            Rehydrate a policy stored in a JSON config sidecar:

            ```python
            from oodocs.apidoc import ApiPublicPolicy

            policy = ApiPublicPolicy.from_dict({
                "name": "__all__",
                "explicit_names": [],
            })
            ```
        """

        data = _normalize_config_mapping(data)
        return cls(
            str(data.get("name", "__all__")),  # type: ignore[arg-type]
            normalize_explicit_names(data.get("explicit_names", ())),  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized policy data.

        Returns:
            JSON-serializable public policy mapping.

        Examples:
            Store a public policy beside a custom API sidecar:

            ```python
            from oodocs.apidoc import ApiPublicPolicy

            payload = ApiPublicPolicy.explicit("mypkg.Client").to_dict()
            ```
        """

        return {
            "name": self.name,
            "explicit_names": list(self.explicit_names),
        }

    def validate(self) -> None:
        """Validate the policy.

        Raises:
            ValueError: If the strategy or explicit names are invalid.

        Examples:
            Validate a user-provided policy before collection:

            ```python
            from oodocs.apidoc import ApiPublicPolicy

            policy = ApiPublicPolicy("__all__")
            policy.validate()
            ```
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

        Examples:
            Apply ``__all__`` semantics while inspecting module members:

            ```python
            from oodocs.apidoc import ApiPublicPolicy

            policy = ApiPublicPolicy("__all__")
            assert policy.module_name_is_public(
                "Client",
                "mypkg.Client",
                {"Client"},
            )
            ```
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

        Examples:
            Check whether a class method belongs in generated API docs:

            ```python
            from oodocs.apidoc import ApiPublicPolicy

            policy = ApiPublicPolicy("underscore")
            assert policy.member_name_is_public("render")
            assert not policy.member_name_is_public("_render_internal")
            ```
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
        fallback_collector: Fallback backend used when griffe is unavailable or
            cannot load the target. Use ``"none"`` for strict CI runs.
        public_policy: Public API boundary policy.
        explicit_names: Names included when ``public_policy="explicit"``.
        docstring_style: Docstring parser style.
        docstring_parser_modules: Importable modules that register custom
            docstring parsers before style validation and collection.
        include_private: Whether underscore-prefixed objects should be included
            in addition to the configured public API boundary.
        include_imported: Whether imported public aliases may be included.
            Source collection records unresolved external imports as ``data``
            objects, while griffe may resolve richer imported targets.
        include_inherited: Whether inherited class members may be included by
            collectors that can resolve them.
        include_attributes: Whether module data and class attributes are
            included in collected API trees.
        include_properties: Whether class properties are included in collected
            API trees.
        include_methods: Whether class methods are included in collected API
            trees.
        include_source_locations: Whether source paths and line numbers are
            retained in collected API trees and diagnostics.
        class_signature_from_init: Whether class signatures use ``__init__``.
        module_include_patterns: Optional glob-style module names to include.
        module_exclude_patterns: Optional glob-style module names to exclude.
        object_include_patterns: Optional glob-style object name or qualname
            patterns to include after collection.
        object_exclude_patterns: Optional glob-style object name or qualname
            patterns to exclude after collection.

    Examples:
        ```python
        from oodocs.apidoc import ApiCollectConfig, collect_api

        config = ApiCollectConfig(
            public_policy="__all__",
            docstring_style="auto",
            object_exclude_patterns=("*.experimental",),
        )
        api = collect_api("oodocs", config=config)
        ```
    """

    collector: ApiCollectorName = "auto"
    fallback_collector: ApiFallbackCollectorName = "inspect"
    public_policy: ApiPublicPolicyName | ApiPublicPolicy | Mapping[str, object] = "__all__"
    explicit_names: tuple[str, ...] = field(default_factory=tuple)
    docstring_style: str = "auto"
    docstring_parser_modules: tuple[str, ...] = field(default_factory=tuple)
    include_private: bool = False
    include_imported: bool = False
    include_inherited: bool = False
    include_attributes: bool = True
    include_properties: bool = True
    include_methods: bool = True
    include_source_locations: bool = True
    class_signature_from_init: bool = True
    module_include_patterns: tuple[str, ...] = field(default_factory=tuple)
    module_exclude_patterns: tuple[str, ...] = field(default_factory=tuple)
    object_include_patterns: tuple[str, ...] = field(default_factory=tuple)
    object_exclude_patterns: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        policy = ApiPublicPolicy.from_value(
            self.public_policy,
            explicit_names=self.explicit_names or None,
        )
        object.__setattr__(self, "public_policy", policy.name)
        object.__setattr__(self, "explicit_names", policy.explicit_names)
        object.__setattr__(self, "fallback_collector", str(self.fallback_collector).strip().lower())
        if isinstance(self.docstring_style, Mapping) or _is_docstring_parser(self.docstring_style):
            from oodocs.apidoc.docstring import ApiDocstringParser

            parser = ApiDocstringParser.from_value(self.docstring_style)  # type: ignore[arg-type]
            object.__setattr__(self, "docstring_style", parser.style)
        else:
            object.__setattr__(self, "docstring_style", str(self.docstring_style).strip().lower())
        object.__setattr__(self, "docstring_parser_modules", _string_tuple(self.docstring_parser_modules))
        if self.docstring_parser_modules:
            from oodocs.apidoc.docstring import load_docstring_parser_modules

            load_docstring_parser_modules(self.docstring_parser_modules)
        self.validate()

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

        Examples:
            Start from repository defaults and override a small part for one
            CI job:

            ```python
            from oodocs.apidoc import ApiCollectConfig, collect_api

            base = ApiCollectConfig.from_pyproject(".")
            config = ApiCollectConfig.from_kwargs(
                base,
                module_exclude_patterns=("mypkg.tests*", "mypkg.experimental*"),
            )
            api = collect_api(".", config=config)
            ```
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
        if isinstance(values.get("docstring_style"), Mapping) or _is_docstring_parser(values.get("docstring_style")):
            from oodocs.apidoc.docstring import ApiDocstringParser

            values["docstring_style"] = ApiDocstringParser.from_value(
                values["docstring_style"],  # type: ignore[arg-type]
            ).style
        for field_name in (
            "explicit_names",
            "docstring_parser_modules",
            "module_include_patterns",
            "module_exclude_patterns",
            "object_include_patterns",
            "object_exclude_patterns",
        ):
            if field_name in values and not isinstance(values[field_name], tuple):
                values[field_name] = tuple(values[field_name])  # type: ignore[arg-type]
        resolved = cls(**values)  # type: ignore[arg-type]
        resolved.validate()
        return resolved

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ApiCollectConfig:
        """Reconstruct a config from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Validated collection configuration.

        Examples:
            Reuse configuration loaded from a deployment manifest:

            ```python
            from oodocs.apidoc import ApiCollectConfig, collect_api

            config = ApiCollectConfig.from_dict({
                "collector": "griffe",
                "public_policy": "__all__",
                "docstring_style": "auto",
            })
            api = collect_api(".", config=config)
            ```
        """

        normalized = _normalize_config_mapping(data)
        _validate_known_config_keys(normalized)
        return cls.from_kwargs(
            **{
                key: value
                for key, value in normalized.items()
                if key in _COLLECT_CONFIG_KEYS
            }
        )

    @classmethod
    def from_pyproject(
        cls,
        path: PathLike = "pyproject.toml",
        *,
        target: object | None = None,
    ) -> ApiCollectConfig:
        """Read apidoc collection config from ``pyproject.toml``.

        Args:
            path: Project root directory or ``pyproject.toml`` path.
            target: Optional target repository, package directory, Python
                file, or importable name whose local parser modules should be
                importable while the config validates.

        Returns:
            Validated collection configuration from ``[tool.oodocs.apidoc]``.

        Raises:
            FileNotFoundError: If the pyproject file does not exist.
            KeyError: If ``[tool.oodocs.apidoc]`` is missing.
            tomllib.TOMLDecodeError: If the pyproject file is invalid TOML.

        Examples:
            Store apidoc settings in a repository ``pyproject.toml`` and use
            them for collection:

            ```python
            from oodocs.apidoc import ApiCollectConfig, collect_api

            config = ApiCollectConfig.from_pyproject(".")
            api = collect_api(".", config=config)
            ```
        """

        pyproject_path = _pyproject_path(path)
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8-sig"))
        try:
            section = data["tool"]["oodocs"]["apidoc"]  # type: ignore[index]
        except KeyError as exc:
            raise KeyError("pyproject.toml must contain [tool.oodocs.apidoc]") from exc
        if not isinstance(section, Mapping):
            raise TypeError("[tool.oodocs.apidoc] must be a table")
        with _config_and_target_import_paths(pyproject_path, target):
            return cls.from_dict(section)

    def validate(self) -> None:
        """Validate config values.

        Raises:
            ValueError: If an option is unsupported or incomplete.

        Examples:
            Validate config assembled from a UI or script before collecting:

            ```python
            from oodocs.apidoc import ApiCollectConfig

            config = ApiCollectConfig(
                public_policy="__all__",
                docstring_style="auto",
            )
            config.validate()
            ```
        """

        if self.collector not in {"auto", "inspect", "griffe"}:
            raise ValueError("collector must be 'auto', 'inspect', or 'griffe'")
        if self.fallback_collector not in {"inspect", "none"}:
            raise ValueError("fallback_collector must be 'inspect' or 'none'")
        if self.public_policy not in {"__all__", "underscore", "all", "explicit"}:
            raise ValueError("public_policy must be '__all__', 'underscore', 'all', or 'explicit'")
        if self.public_policy == "explicit" and not self.explicit_names:
            raise ValueError("explicit_names is required when public_policy='explicit'")
        from oodocs.apidoc.docstring import is_docstring_style_supported

        if not is_docstring_style_supported(self.docstring_style):
            raise ValueError("docstring_style is not supported")

    def docstring_parser(self):
        """Return this config's reusable docstring parser object.

        Returns:
            ``ApiDocstringParser`` configured from ``docstring_style``.

        Examples:
            Reuse the same parser for a quick standalone parse:

            ```python
            from oodocs.apidoc import ApiCollectConfig

            config = ApiCollectConfig(docstring_style="google")
            parsed = config.docstring_parser().parse(
                "Load data.\\n\\nArgs:\\n    path: Input path.",
            )
            ```
        """

        from oodocs.apidoc.docstring import ApiDocstringParser

        return ApiDocstringParser(self.docstring_style)

    def public_api_policy(self) -> ApiPublicPolicy:
        """Return this config's reusable public API policy object.

        Returns:
            ``ApiPublicPolicy`` built from ``public_policy`` and
            ``explicit_names``.

        Examples:
            Inspect the resolved public boundary used by collection:

            ```python
            from oodocs.apidoc import ApiCollectConfig

            config = ApiCollectConfig(
                public_policy="explicit",
                explicit_names=("mypkg.run",),
            )
            policy = config.public_api_policy()
            assert policy.module_name_is_public("run", "mypkg.run", None)
            ```
        """

        return ApiPublicPolicy(self.public_policy, self.explicit_names)

    def to_dict(self) -> dict[str, object]:
        """Return this config as JSON-serializable data.

        Returns:
            Deterministic mapping suitable for JSON sidecars or
            ``ApiCollectConfig.from_dict(...)``.

        Examples:
            Store a collection policy in a custom project manifest:

            ```python
            from oodocs.apidoc import ApiCollectConfig

            payload = ApiCollectConfig(
                collector="griffe",
                public_policy="__all__",
                docstring_style="auto",
            ).to_dict()
            ```
        """

        return {
            "collector": self.collector,
            "fallback_collector": self.fallback_collector,
            "public_policy": self.public_policy,
            "explicit_names": list(self.explicit_names),
            "docstring_style": self.docstring_style,
            "docstring_parser_modules": list(self.docstring_parser_modules),
            "include_private": self.include_private,
            "include_imported": self.include_imported,
            "include_inherited": self.include_inherited,
            "include_attributes": self.include_attributes,
            "include_properties": self.include_properties,
            "include_methods": self.include_methods,
            "include_source_locations": self.include_source_locations,
            "class_signature_from_init": self.class_signature_from_init,
            "module_include_patterns": list(self.module_include_patterns),
            "module_exclude_patterns": list(self.module_exclude_patterns),
            "object_include_patterns": list(self.object_include_patterns),
            "object_exclude_patterns": list(self.object_exclude_patterns),
        }

    def save_json(self, path: PathLike) -> Path:
        """Write this collection config as deterministic JSON.

        Args:
            path: Output JSON path.

        Returns:
            Written path.

        Examples:
            Persist one repository policy for local scripts and CLI commands:

            ```python
            from oodocs.apidoc import ApiCollectConfig

            config = ApiCollectConfig(
                collector="griffe",
                public_policy="__all__",
                module_exclude_patterns=("mypkg.tests*",),
            )
            config.save_json("apidoc-config.json")
            ```
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def load_json(
        cls,
        path: PathLike,
        *,
        target: object | None = None,
    ) -> ApiCollectConfig:
        """Read a collection config JSON sidecar.

        Args:
            path: JSON sidecar path.
            target: Optional target repository, package directory, Python
                file, or importable name whose local parser modules should be
                importable while the config validates.

        Returns:
            Validated collection configuration.

        Examples:
            Load the same collection policy that the CLI uses with
            ``--config``:

            ```python
            from oodocs.apidoc import ApiCollectConfig, collect_api

            config = ApiCollectConfig.load_json("apidoc-config.json", target=".")
            api = collect_api(".", config=config)
            ```
        """

        config_path = Path(path)
        with _config_and_target_import_paths(config_path, target):
            return cls.from_dict(json.loads(config_path.read_text(encoding="utf-8")))

    @classmethod
    def load_file(
        cls,
        path: PathLike,
        *,
        target: object | None = None,
    ) -> ApiCollectConfig:
        """Load a collection config from JSON or ``pyproject.toml``.

        Args:
            path: JSON sidecar, project root directory, or TOML file path.
            target: Optional target repository, package directory, Python
                file, or importable name whose local parser modules should be
                importable while the config validates.

        Returns:
            Validated collection configuration.

        Examples:
            ```python
            from oodocs.apidoc import ApiCollectConfig

            config = ApiCollectConfig.load_file("pyproject.toml", target=".")
            ```
        """

        config_path = Path(path)
        if config_path.is_dir() or config_path.suffix.lower() == ".toml":
            return cls.from_pyproject(config_path, target=target)
        return cls.load_json(config_path, target=target)


@dataclass(frozen=True, slots=True)
class ApiHelpBookConfig:
    """Reusable API help-book rendering configuration.

    Attributes:
        collection: Collection settings used before rendering.
        presentation: Presentation profile name.
        output_formats: Output formats passed to ``Document.save_all``.
        stem: Optional output file stem.
        max_heading_level: Optional deepest nested API heading level.
        include_coverage: Whether rendered help books include coverage
            evidence as the final appendix.
        include_uncategorized_appendix: Whether rendered help books include
            public API objects not assigned to curated categories.
        sidecars: Whether ``save_all(...)`` writes API and coverage sidecars.
        output_dir: Optional default output directory.
        kind: Optional object kinds to render after collection.
        module_prefix: Optional module prefix filter after collection.

    Examples:
        Store repository-local build defaults in ``pyproject.toml`` and use
        them from Python or the CLI:

        ```python
        from oodocs.apidoc import ApiHelpBookConfig

        build = ApiHelpBookConfig.from_pyproject(".")
        outputs = build.save_all(".", output_dir="artifacts/api")
        ```
    """

    collection: ApiCollectConfig = field(default_factory=ApiCollectConfig)
    presentation: str = "help"
    output_formats: tuple[str, ...] = ("docx", "pdf", "html")
    stem: str | None = None
    max_heading_level: int | None = None
    include_coverage: bool = True
    include_uncategorized_appendix: bool = True
    sidecars: bool = False
    output_dir: str | None = None
    kind: tuple[str, ...] = field(default_factory=tuple)
    module_prefix: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "collection",
            self.collection
            if isinstance(self.collection, ApiCollectConfig)
            else ApiCollectConfig.from_dict(self.collection),  # type: ignore[arg-type]
        )
        object.__setattr__(self, "presentation", self.presentation.strip().lower())
        object.__setattr__(self, "output_formats", normalize_output_formats(self.output_formats))
        object.__setattr__(self, "kind", _string_tuple(self.kind))
        if self.module_prefix is not None:
            if _is_sequence_or_mapping(self.module_prefix):
                raise TypeError("module_prefix must be a string")
            object.__setattr__(self, "module_prefix", str(self.module_prefix).strip() or None)
        if self.output_dir is not None:
            object.__setattr__(self, "output_dir", str(self.output_dir))
        if self.stem is not None:
            object.__setattr__(self, "stem", str(self.stem).strip() or None)
        self.validate()

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ApiHelpBookConfig:
        """Reconstruct build config from serialized data.

        Args:
            data: Mapping from JSON or ``[tool.oodocs.apidoc]``.

        Returns:
            Validated build configuration.

        Examples:
            Build a config object from a deployment manifest and use it to
            render a package help book:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.from_dict({
                "collector": "griffe",
                "public_policy": "__all__",
                "presentation": "reference",
                "output_formats": ["docx", "html"],
                "output_dir": "artifacts/api",
            })
            outputs = build.save_all(".")
            ```
        """

        normalized = _normalize_config_mapping(data)
        _validate_known_config_keys(normalized)
        output_formats = normalized.get("output_formats", ("docx", "pdf", "html"))
        output_dir = normalized.get("output_dir")
        return cls(
            collection=ApiCollectConfig.from_dict(normalized),
            presentation=str(normalized.get("presentation", "help")),
            output_formats=_format_tuple(output_formats),
            stem=_optional_str(normalized.get("stem")),
            max_heading_level=_optional_int(normalized.get("max_heading_level")),
            include_coverage=bool(normalized.get("include_coverage", True)),
            include_uncategorized_appendix=bool(
                normalized.get("include_uncategorized_appendix", True)
            ),
            sidecars=bool(normalized.get("sidecars", False)),
            output_dir=_optional_str(output_dir),
            kind=_string_tuple(normalized.get("kind", ())),
            module_prefix=_optional_config_str("module_prefix", normalized.get("module_prefix")),
        )

    @classmethod
    def from_pyproject(
        cls,
        path: PathLike = "pyproject.toml",
        *,
        target: object | None = None,
    ) -> ApiHelpBookConfig:
        """Read build config from ``pyproject.toml``.

        Args:
            path: Project root directory or ``pyproject.toml`` path.
            target: Optional target repository, package directory, Python
                file, or importable name whose local parser modules should be
                importable while the config validates.

        Returns:
            Build configuration from ``[tool.oodocs.apidoc]``.

        Raises:
            FileNotFoundError: If the pyproject file does not exist.
            KeyError: If ``[tool.oodocs.apidoc]`` is missing.
            tomllib.TOMLDecodeError: If the pyproject file is invalid TOML.

        Examples:
            Reuse the same build defaults stored in ``[tool.oodocs.apidoc]``:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.from_pyproject(".")
            outputs = build.save_all(".", output_dir="artifacts/api")
            ```
        """

        pyproject_path = _pyproject_path(path)
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8-sig"))
        try:
            section = data["tool"]["oodocs"]["apidoc"]  # type: ignore[index]
        except KeyError as exc:
            raise KeyError("pyproject.toml must contain [tool.oodocs.apidoc]") from exc
        if not isinstance(section, Mapping):
            raise TypeError("[tool.oodocs.apidoc] must be a table")
        with _config_and_target_import_paths(pyproject_path, target):
            return cls.from_dict(section)

    @classmethod
    def load_json(
        cls,
        path: PathLike,
        *,
        target: object | None = None,
    ) -> ApiHelpBookConfig:
        """Read a build config JSON sidecar.

        Args:
            path: JSON sidecar path.
            target: Optional target repository, package directory, Python
                file, or importable name whose local parser modules should be
                importable while the config validates.

        Returns:
            Validated build configuration.

        Examples:
            Load a build config written by ``ApiHelpBookConfig.save_json(...)``:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.load_json("apidoc-build.json", target=".")
            outputs = build.save_all(".", output_dir="artifacts/api")
            ```
        """

        config_path = Path(path)
        with _config_and_target_import_paths(config_path, target):
            return cls.from_dict(json.loads(config_path.read_text(encoding="utf-8")))

    @classmethod
    def load_file(
        cls,
        path: PathLike,
        *,
        target: object | None = None,
    ) -> ApiHelpBookConfig:
        """Load a build config from JSON or ``pyproject.toml``.

        Args:
            path: JSON sidecar, project root directory, or TOML file path.
            target: Optional target repository, package directory, Python
                file, or importable name whose local parser modules should be
                importable while the config validates.

        Returns:
            Validated build configuration.

        Examples:
            Let scripts accept either ``pyproject.toml`` or JSON config paths:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.load_file("pyproject.toml", target=".")
            document = build.to_help_book(".")
            ```
        """

        config_path = Path(path)
        if config_path.is_dir() or config_path.suffix.lower() == ".toml":
            return cls.from_pyproject(config_path, target=target)
        return cls.load_json(config_path, target=target)

    def validate(self) -> None:
        """Validate build settings.

        Raises:
            ValueError: If presentation, formats, or heading depth are invalid.

        Examples:
            Validate build defaults before writing them into a repository:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig(
                presentation="website",
                output_formats=("html",),
            )
            build.validate()
            ```
        """

        from oodocs.apidoc.profiles import resolve_presentation_profile

        resolve_presentation_profile(self.presentation)
        if self.max_heading_level is not None and self.max_heading_level < 1:
            raise ValueError("max_heading_level must be >= 1")
        if not self.output_formats:
            raise ValueError("output_formats must include at least one format")

    def collect(self, target: str | PathLike) -> ApiPackage:
        """Collect and filter a target with this build configuration.

        Args:
            target: Importable package/module name, Python file, package
                directory, or repository root.

        Returns:
            ``ApiPackage`` collected with ``collection`` settings and filtered
            by this build config's ``kind`` and ``module_prefix`` options.

        Examples:
            Load an external build config, then collect a normal Python
            repository with the configured parser object and object filters:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.load_file("apidoc-build.json", target=".")
            api = build.collect(".")
            assert api.modules
            ```
        """

        from oodocs.apidoc.collect import collect_api

        api = collect_api(target, config=self.collection)
        return _filter_api_for_build(
            api,
            kind=self.kind or None,
            module_prefix=self.module_prefix,
        )

    def to_help_book(
        self,
        target: str | PathLike,
        title: str | None = None,
        *,
        settings: object | None = None,
        citations: object | None = None,
    ) -> Document:
        """Collect a target and return a rendered API help-book document.

        Args:
            target: Importable package/module name, Python file, package
                directory, or repository root.
            title: Optional document title. Defaults to
                ``"{api.name} API Reference"``.
            settings: Optional ``DocumentSettings`` passed to ``Document``.
            citations: Optional citation library passed to ``Document``.

        Returns:
            OODocs ``Document`` ready for ``save_docx``, ``save_pdf``,
            ``save_html``, or ``save_all``.

        Examples:
            Build a complete help-book reference from a repository config:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.from_pyproject(".")
            document = build.to_help_book(".")
            document.save_all("artifacts/api", stem="mypkg-api")
            ```
        """

        return _help_book_for_build(
            self.collect(target),
            self,
            title=title,
            settings=settings,
            citations=citations,
        )

    def check_docs(
        self,
        target: str | PathLike,
        *,
        fail_under: float | None = None,
        require_examples: bool = False,
        require_renderer_notes: bool = False,
        doctest_namespace: Mapping[str, object] | None = None,
    ) -> ApiCoverageResult:
        """Collect a target and check API documentation coverage.

        Args:
            target: Importable package/module name, Python file, package
                directory, or repository root.
            fail_under: Optional minimum documented-object ratio. When the
                coverage is below this value, the result contains an error
                issue.
            require_examples: Whether public API objects must include examples.
            require_renderer_notes: Whether public API objects must include
                renderer notes.
            doctest_namespace: Optional trusted namespace used to execute
                doctest-style examples.

        Returns:
            ``ApiCoverageResult`` for the collected and build-filtered API
            package.

        Examples:
            Run the same filtered coverage check that the CLI uses, but from a
            release script:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.from_pyproject(".")
            coverage = build.check_docs(".", fail_under=0.90)
            coverage.save_json("artifacts/api/coverage.json")
            ```
        """

        from oodocs.apidoc.coverage import check_api_docs

        return check_api_docs(
            self.collect(target),
            fail_under=fail_under,
            require_examples=require_examples,
            require_renderer_notes=require_renderer_notes,
            doctest_namespace=doctest_namespace,
        )

    def snapshot(self, target: str | PathLike) -> ApiSnapshot:
        """Collect a target and return a public API snapshot.

        Args:
            target: Importable package/module name, Python file, package
                directory, or repository root.

        Returns:
            Deterministic ``ApiSnapshot`` built from the collected and
            build-filtered API package.

        Examples:
            Create a filtered snapshot using the same config as API reference
            builds:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig, diff_api

            build = ApiHelpBookConfig.from_pyproject(".")
            base = build.snapshot(".")
            head = build.snapshot(".")
            diff = diff_api(base, head)
            ```
        """

        from oodocs.apidoc.diff import ApiSnapshot

        return ApiSnapshot.from_package(self.collect(target))

    def save_snapshot(self, target: str | PathLike, path: PathLike) -> Path:
        """Collect a target and save a public API snapshot sidecar.

        Args:
            target: Importable package/module name, Python file, package
                directory, or repository root.
            path: Output snapshot JSON path.

        Returns:
            Written snapshot path.

        Examples:
            Persist a release snapshot for later diffing:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig.from_pyproject(".")
            snapshot_path = build.save_snapshot(".", "artifacts/api-head.json")
            ```
        """

        return self.snapshot(target).save_json(path)

    def save_all(
        self,
        target: str | PathLike,
        output_dir: PathLike | None = None,
        *,
        stem: str | None = None,
        output_formats: Sequence[str] | None = None,
        sidecars: bool | None = None,
        title: str | None = None,
        settings: object | None = None,
        citations: object | None = None,
    ) -> dict[object, Path]:
        """Collect a target and write rendered API reference outputs.

        Args:
            target: Importable package/module name, Python file, package
                directory, or repository root.
            output_dir: Optional output directory. Defaults to this config's
                ``output_dir``.
            stem: Optional output filename stem. Defaults to this config's
                ``stem`` or ``"{api.name}-api"``.
            output_formats: Optional output formats. Defaults to this config's
                ``output_formats``.
            sidecars: Whether to write API JSON and coverage JSON/CSV sidecars.
                Defaults to this config's ``sidecars``.
            title: Optional document title.
            settings: Optional ``DocumentSettings`` passed to ``Document``.
            citations: Optional citation library passed to ``Document``.

        Returns:
            Mapping of rendered output names to written paths. When sidecars
            are enabled, the mapping also includes
            ``"api_object_tree_json"``, ``"api_coverage_json"``, and
            ``"api_coverage_csv"``.

        Raises:
            ValueError: If no output directory is supplied by the call or
                stored config.

        Examples:
            Render a full API bundle for a different Python repository using
            an external JSON config. Repository-local custom parser modules are
            loaded when ``load_file(..., target=repo)`` validates the config:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            repo = r"C:\\work\\mypkg"
            build = ApiHelpBookConfig.load_file(r"C:\\configs\\mypkg-apidoc.json", target=repo)
            outputs = build.save_all(repo)
            assert outputs["html"].exists()
            assert outputs["api_object_tree_json"].exists()
            ```
        """

        api = self.collect(target)
        resolved_output_dir = output_dir if output_dir is not None else self.output_dir
        if resolved_output_dir is None:
            raise ValueError("ApiHelpBookConfig.save_all requires output_dir or config output_dir")
        resolved_stem = stem or self.stem or f"{api.name.replace('.', '-')}-api"
        resolved_formats = normalize_output_formats(
            tuple(output_formats) if output_formats is not None else self.output_formats
        )
        document = _help_book_for_build(
            api,
            self,
            title=title,
            settings=settings,
            citations=citations,
        )
        rendered_outputs = document.save_all(
            resolved_output_dir,
            stem=resolved_stem,
            formats=resolved_formats,
        )
        outputs: dict[object, Path] = dict(rendered_outputs.items())
        save_sidecars = self.sidecars if sidecars is None else sidecars
        if save_sidecars:
            outputs.update(_write_build_sidecars(api, resolved_output_dir, resolved_stem))
        return outputs

    def to_dict(self) -> dict[str, object]:
        """Return this build config as JSON-serializable data.

        Returns:
            Deterministic mapping containing both collection and build options.

        Examples:
            Generate config data for a custom repository setup wizard:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            payload = ApiHelpBookConfig(
                presentation="website",
                output_formats=("html",),
                output_dir="artifacts/api",
            ).to_dict()
            ```
        """

        values = self.collection.to_dict()
        values.update(
            {
                "presentation": self.presentation,
                "output_formats": list(self.output_formats),
                "stem": self.stem,
                "max_heading_level": self.max_heading_level,
                "include_coverage": self.include_coverage,
                "include_uncategorized_appendix": self.include_uncategorized_appendix,
                "sidecars": self.sidecars,
                "output_dir": self.output_dir,
                "kind": list(self.kind),
                "module_prefix": self.module_prefix,
            }
        )
        return values

    def save_json(self, path: PathLike) -> Path:
        """Write this build config as deterministic JSON.

        Args:
            path: Output JSON path.

        Returns:
            Written path.

        Examples:
            Write build defaults for a repository-local automation script:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            build = ApiHelpBookConfig(
                presentation="reference",
                output_dir="artifacts/api",
                sidecars=True,
            )
            build.save_json("apidoc-build.json")
            ```
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path

    def to_toml_section(self) -> str:
        """Return this build config as a ``[tool.oodocs.apidoc]`` TOML section.

        Returns:
            TOML text containing collection and build options.

        Examples:
            Generate a repository-local config block:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            text = ApiHelpBookConfig(presentation="website", output_formats=("html",)).to_toml_section()
            ```
        """

        lines = ["[tool.oodocs.apidoc]"]
        for key, value in self.to_dict().items():
            if value is None or value == []:
                continue
            lines.append(f"{key.replace('_', '-')} = {_toml_value(value)}")
        return "\n".join(lines) + "\n"

    def save_pyproject(self, path: PathLike = "pyproject.toml") -> Path:
        """Save this config into a ``pyproject.toml`` file.

        Args:
            path: Project root directory or ``pyproject.toml`` path.

        Returns:
            Written ``pyproject.toml`` path.

        Raises:
            ValueError: If the file already contains ``[tool.oodocs.apidoc]``.

        Examples:
            Initialize a Python repository so CLI and Python calls share the
            same defaults:

            ```python
            from oodocs.apidoc import ApiHelpBookConfig

            ApiHelpBookConfig(
                presentation="website",
                output_formats=("html",),
                output_dir="artifacts/api",
                sidecars=True,
            ).save_pyproject(".")
            ```
        """

        pyproject_path = _pyproject_path(path)
        pyproject_path.parent.mkdir(parents=True, exist_ok=True)
        if pyproject_path.exists():
            existing = pyproject_path.read_text(encoding="utf-8-sig")
            if _has_apidoc_section(existing):
                raise ValueError("pyproject.toml already contains [tool.oodocs.apidoc]")
            separator = "\n\n" if existing.strip() else ""
            pyproject_path.write_text(
                existing.rstrip() + separator + self.to_toml_section(),
                encoding="utf-8",
            )
        else:
            pyproject_path.write_text(self.to_toml_section(), encoding="utf-8")
        return pyproject_path


def _filter_api_for_build(
    api: ApiPackage,
    *,
    kind: tuple[str, ...] | None,
    module_prefix: str | None,
) -> ApiPackage:
    if not _has_build_filters(kind, module_prefix):
        return api
    return api.subset(kind=kind, module_prefix=module_prefix)


def _help_book_for_build(
    api: ApiPackage,
    config: ApiHelpBookConfig,
    *,
    title: str | None = None,
    settings: object | None = None,
    citations: object | None = None,
) -> Document:
    if _has_build_filters(config.kind or None, config.module_prefix):
        from oodocs.components.blocks import Chapter
        from oodocs.document import Document

        selected = _top_level_objects(api)
        return Document(
            title or f"{api.name} API Reference",
            Chapter(
                "Selected API",
                api.to_summary_table(
                    selected,
                    caption="Selected public API objects",
                    presentation=config.presentation,
                ),
                *[
                    obj.to_section(
                        level=2,
                        presentation=config.presentation,
                        max_heading_level=config.max_heading_level,
                    )
                    for obj in selected
                ],
            ),
            settings=settings,  # type: ignore[arg-type]
            citations=citations,  # type: ignore[arg-type]
        )
    return api.to_help_book(
        title=title,
        presentation=config.presentation,
        settings=settings,
        citations=citations,
        include_coverage=config.include_coverage,
        include_uncategorized_appendix=config.include_uncategorized_appendix,
        max_heading_level=config.max_heading_level,
    )


def _write_build_sidecars(
    api: ApiPackage,
    output_dir: PathLike,
    stem: str,
) -> dict[object, Path]:
    from oodocs.apidoc.coverage import check_api_docs

    directory = Path(output_dir)
    coverage = check_api_docs(api)
    return {
        "api_object_tree_json": api.save_json(directory / f"{stem}-object-tree.json"),
        "api_coverage_json": coverage.save_json(directory / f"{stem}-coverage.json"),
        "api_coverage_csv": coverage.save_csv(directory / f"{stem}-coverage.csv"),
    }


def _has_build_filters(kind: tuple[str, ...] | None, module_prefix: str | None) -> bool:
    return bool(kind or module_prefix)


def _top_level_objects(api: ApiPackage) -> list[object]:
    return [member for module in api.modules for member in module.members]


def normalize_explicit_names(names: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize explicit public API names.

    Args:
        names: Optional input names.

    Returns:
        Deduplicated tuple preserving sorted deterministic order.

    Examples:
        Normalize explicit names before creating a public policy:

        ```python
        from oodocs.apidoc.config import normalize_explicit_names

        names = normalize_explicit_names([
            "mypkg.Client",
            "mypkg.Client",
            " run ",
        ])
        assert names == ("mypkg.Client", "run")
        ```
    """

    return tuple(sorted({name.strip() for name in names or () if name.strip()}))


def _is_docstring_parser(value: object) -> bool:
    return type(value).__name__ == "ApiDocstringParser"


def _normalize_config_mapping(data: Mapping[str, object]) -> dict[str, object]:
    normalized = {str(key).replace("-", "_"): value for key, value in data.items()}
    if "fallback_parser" in normalized and "fallback_collector" not in normalized:
        normalized["fallback_collector"] = normalized["fallback_parser"]
    normalized.pop("fallback_parser", None)
    return normalized


def _validate_known_config_keys(data: Mapping[str, object]) -> None:
    unknown = sorted(set(data) - _COLLECT_CONFIG_KEYS - _BUILD_CONFIG_KEYS)
    if unknown:
        raise TypeError(f"Unsupported apidoc config key(s): {', '.join(unknown)}")


def _format_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(piece.strip() for piece in value.split(",") if piece.strip())
    return _string_tuple(value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    return tuple(str(item).strip() for item in value if str(item).strip())  # type: ignore[union-attr]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_config_str(name: str, value: object) -> str | None:
    if value is None:
        return None
    if _is_sequence_or_mapping(value):
        raise TypeError(f"{name} must be a string")
    return _optional_str(value)


def _is_sequence_or_mapping(value: object) -> bool:
    return isinstance(value, Mapping) or (
        isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _project_source_roots(directory: Path) -> list[Path]:
    """Return existing source roots declared by a project directory.

    Args:
        directory: Project root that may contain ``pyproject.toml``.

    Returns:
        Existing source roots from setuptools ``package-dir`` mappings,
        ``packages.find.where`` settings, hatch wheel package settings, Poetry
        package entries, PDM build settings, ``[project] import-names``, Flit
        import-name source roots, and the conventional ``src/`` layout.
    """

    roots: list[Path] = []
    data = _project_pyproject_data(directory)
    if data:
        tool = data.get("tool")
        setuptools = tool.get("setuptools") if isinstance(tool, Mapping) else None
        if isinstance(setuptools, Mapping):
            package_dir = setuptools.get("package-dir")
            if isinstance(package_dir, Mapping):
                default_root = package_dir.get("")
                if isinstance(default_root, str):
                    roots.append(directory / default_root)
                for value in package_dir.values():
                    if isinstance(value, str):
                        roots.append(directory / value)

            packages = setuptools.get("packages")
            find = packages.get("find") if isinstance(packages, Mapping) else None
            where = find.get("where") if isinstance(find, Mapping) else None
            if isinstance(where, str):
                roots.append(directory / where)
            elif isinstance(where, Sequence) and not isinstance(where, (str, bytes, bytearray)):
                roots.extend(directory / item for item in where if isinstance(item, str))
        roots.extend(_hatch_source_roots(directory, tool))
        roots.extend(_poetry_source_roots(directory, tool))
        roots.extend(_pdm_source_roots(directory, tool))
        roots.extend(_declared_import_source_roots(directory, data))
        roots.extend(_flit_source_roots(directory, data))

    roots.append(directory / "src")
    return _existing_unique_paths(roots)


def _project_import_roots(directory: Path) -> list[Path]:
    """Return import roots for project-local extension modules.

    Args:
        directory: Project root or config directory.

    Returns:
        Existing directories that should be temporarily added to ``sys.path``
        while loading repository-local docstring parser modules.
    """

    roots: list[Path] = [directory]
    for source_root in _project_source_roots(directory):
        roots.append(source_root)
        if (source_root / "__init__.py").exists():
            roots.append(source_root.parent)
    return _existing_unique_paths(roots)


def _project_pyproject_data(directory: Path) -> dict[str, object] | None:
    path = directory / "pyproject.toml"
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _hatch_source_roots(directory: Path, tool: object) -> list[Path]:
    if not isinstance(tool, Mapping):
        return []
    hatch = tool.get("hatch")
    build = hatch.get("build") if isinstance(hatch, Mapping) else None
    targets = build.get("targets") if isinstance(build, Mapping) else None
    wheel = targets.get("wheel") if isinstance(targets, Mapping) else None
    if not isinstance(wheel, Mapping):
        return []
    roots: list[Path] = []
    roots.extend((directory / value).parent for value in _path_strings(wheel.get("packages")))
    for key in ("only-include", "sources"):
        roots.extend(directory / value for value in _path_strings(wheel.get(key)))
    return roots


def _poetry_source_roots(directory: Path, tool: object) -> list[Path]:
    if not isinstance(tool, Mapping):
        return []
    poetry = tool.get("poetry")
    packages = poetry.get("packages") if isinstance(poetry, Mapping) else None
    if not isinstance(packages, Sequence) or isinstance(packages, (str, bytes, bytearray)):
        return []
    roots: list[Path] = []
    for package in packages:
        if not isinstance(package, Mapping):
            continue
        from_root = package.get("from")
        include = package.get("include")
        if isinstance(from_root, str) and from_root.strip():
            roots.append(directory / from_root)
        elif isinstance(include, str) and include.strip() and "*" not in include:
            roots.append(directory / include)
    return roots


def _pdm_source_roots(directory: Path, tool: object) -> list[Path]:
    if not isinstance(tool, Mapping):
        return []
    pdm = tool.get("pdm")
    build = pdm.get("build") if isinstance(pdm, Mapping) else None
    if not isinstance(build, Mapping):
        return []
    roots: list[Path] = []
    package_dir = build.get("package-dir", build.get("package_dir"))
    if isinstance(package_dir, str) and package_dir.strip():
        roots.append(directory / package_dir)
    roots.extend(
        root
        for include in _path_strings(build.get("includes"))
        if (root := _pdm_include_source_root(directory, include)) is not None
    )
    return roots


def _pdm_include_source_root(directory: Path, include: str) -> Path | None:
    normalized = include.strip().rstrip("/\\")
    if not normalized or any(character in normalized for character in "*?["):
        return None
    path = directory / normalized
    if path.suffix == ".py":
        if path.name == "__init__.py":
            return path.parent.parent
        return path.parent
    if path.name in {"src", "lib"}:
        return path
    if (path / "__init__.py").exists():
        return path.parent
    if path.is_dir() and any(child.name == "__init__.py" for child in path.rglob("__init__.py")):
        return path.parent
    return path


def _flit_source_roots(directory: Path, data: Mapping[str, object]) -> list[Path]:
    if not _is_flit_project(data):
        return []
    roots: list[Path] = []
    for source_root in (directory / "src", directory):
        for import_name in _flit_import_names(data):
            source = source_root.joinpath(*import_name.split("."))
            if source.with_suffix(".py").is_file() or source.is_dir():
                roots.append(source_root)
    return roots


def _declared_import_source_roots(
    directory: Path,
    data: Mapping[str, object],
) -> list[Path]:
    project = data.get("project")
    import_names = _declared_project_import_names(project)
    if import_names is None:
        return []
    roots: list[Path] = []
    for source_root in (directory / "src", directory):
        for import_name in import_names:
            source = source_root.joinpath(*import_name.split("."))
            if source.with_suffix(".py").is_file() or source.is_dir():
                roots.append(source_root)
    return roots


def _declared_project_import_names(project: object) -> tuple[str, ...] | None:
    if not isinstance(project, Mapping):
        return None
    found = False
    names: list[str] = []
    for key in ("import-names", "import_names", "import-namespaces", "import_namespaces"):
        if key not in project:
            continue
        found = True
        names.extend(_flit_import_names_from_value(project.get(key)))
    if not found:
        return None
    return tuple(dict.fromkeys(names))


def _is_flit_project(data: Mapping[str, object]) -> bool:
    build_system = data.get("build-system")
    build_backend = (
        build_system.get("build-backend")
        if isinstance(build_system, Mapping)
        else None
    )
    tool = data.get("tool")
    return (
        isinstance(build_backend, str)
        and "flit" in build_backend
    ) or (isinstance(tool, Mapping) and isinstance(tool.get("flit"), Mapping))


def _flit_import_names(data: Mapping[str, object]) -> tuple[str, ...]:
    names: list[str] = []
    project = data.get("project")
    if isinstance(project, Mapping):
        names.extend(_flit_import_names_from_value(project.get("import-names")))
        names.extend(_flit_import_names_from_value(project.get("import-namespaces")))
    tool = data.get("tool")
    flit = tool.get("flit") if isinstance(tool, Mapping) else None
    module = flit.get("module") if isinstance(flit, Mapping) else None
    module_name = module.get("name") if isinstance(module, Mapping) else None
    if isinstance(module_name, str) and module_name.strip():
        names.append(module_name.strip())
    if not names and isinstance(project, Mapping):
        project_name = project.get("name")
        if isinstance(project_name, str) and project_name.strip():
            names.append(project_name.replace("-", "_").strip())
    return tuple(dict.fromkeys(names))


def _flit_import_names_from_value(value: object) -> list[str]:
    return [
        name.split(";", 1)[0].strip()
        for name in _path_strings(value)
        if name.split(";", 1)[0].strip()
    ]


def _path_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, Mapping):
        return tuple(str(item).strip() for item in value.values() if str(item).strip())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _existing_unique_paths(paths: Iterable[Path]) -> list[Path]:
    normalized: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not resolved.is_dir():
            continue
        normalized.append(resolved)
        seen.add(resolved)
    return normalized


@contextmanager
def _config_import_paths(path: Path):
    base = path.parent.resolve()
    roots = _project_import_roots(base)

    added: list[str] = []
    for root in reversed([str(item) for item in roots]):
        if root not in sys.path:
            sys.path.insert(0, root)
            added.append(root)
    try:
        yield
    finally:
        for root in added:
            try:
                sys.path.remove(root)
            except ValueError:  # pragma: no cover - defensive against user mutation.
                pass


@contextmanager
def _config_and_target_import_paths(path: Path, target: object | None):
    with _config_import_paths(path):
        if target is None:
            yield
            return
        from oodocs.apidoc.docstring import docstring_parser_import_paths

        with docstring_parser_import_paths(target):
            yield


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))


def _has_apidoc_section(text: str) -> bool:
    return any(
        line.strip() == "[tool.oodocs.apidoc]"
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _pyproject_path(path: PathLike) -> Path:
    source_path = Path(path)
    if source_path.is_dir():
        return source_path / "pyproject.toml"
    return source_path


__all__ = [
    "ApiHelpBookConfig",
    "ApiCollectConfig",
    "ApiCollectorName",
    "ApiFallbackCollectorName",
    "ApiPublicPolicy",
    "ApiPublicPolicyName",
    "normalize_explicit_names",
]
