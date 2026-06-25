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
from typing import Literal, Mapping, Sequence

from oodocs.compatibility import normalize_output_formats
from oodocs.core import PathLike

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
    "formats",
    "kind",
    "max_level",
    "module_prefix",
    "out",
    "output_dir",
    "output_formats",
    "profile",
    "sidecars",
    "stem",
    "to",
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
            object_exclude_patterns=("render_to_pdf", "render_to_html"),
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
    def from_pyproject(cls, path: PathLike = "pyproject.toml") -> ApiCollectConfig:
        """Read apidoc collection config from ``pyproject.toml``.

        Args:
            path: Project root directory or ``pyproject.toml`` path.

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
        with _config_import_paths(pyproject_path):
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

    def write_json(self, path: PathLike) -> Path:
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
            config.write_json("apidoc-config.json")
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
    def read_json(cls, path: PathLike) -> ApiCollectConfig:
        """Read a collection config JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            Validated collection configuration.

        Examples:
            Load the same collection policy that the CLI uses with
            ``--config``:

            ```python
            from oodocs.apidoc import ApiCollectConfig, collect_api

            config = ApiCollectConfig.read_json("apidoc-config.json")
            api = collect_api(".", config=config)
            ```
        """

        config_path = Path(path)
        with _config_import_paths(config_path):
            return cls.from_dict(json.loads(config_path.read_text(encoding="utf-8")))

    @classmethod
    def read_file(cls, path: PathLike) -> ApiCollectConfig:
        """Read a collection config from JSON or ``pyproject.toml``.

        Args:
            path: JSON sidecar, project root directory, or TOML file path.

        Returns:
            Validated collection configuration.

        Examples:
            ```python
            from oodocs.apidoc import ApiCollectConfig

            config = ApiCollectConfig.read_file("pyproject.toml")
            ```
        """

        config_path = Path(path)
        if config_path.is_dir() or config_path.suffix.lower() == ".toml":
            return cls.from_pyproject(config_path)
        return cls.read_json(config_path)


@dataclass(frozen=True, slots=True)
class ApiBuildConfig:
    """Reusable API reference rendering configuration.

    Attributes:
        collection: Collection settings used before rendering.
        profile: Presentation profile name.
        output_formats: Output formats passed to ``Document.save_all``.
        stem: Optional output file stem.
        max_level: Optional deepest nested API heading level.
        sidecars: Whether build commands write API and coverage sidecars.
        output_dir: Optional default output directory.
        kind: Optional object kinds to render after collection.
        module_prefix: Optional module prefix filter after collection.

    Examples:
        Store repository-local build defaults in ``pyproject.toml`` and use
        them from Python or the CLI:

        ```python
        from oodocs.apidoc import ApiBuildConfig, collect_api

        build = ApiBuildConfig.from_pyproject(".")
        api = collect_api(".", config=build.collection)
        api.to_document(profile=build.profile).save_all(
            build.output_dir or "artifacts/api",
            formats=build.output_formats,
        )
        ```
    """

    collection: ApiCollectConfig = field(default_factory=ApiCollectConfig)
    profile: str = "reference"
    output_formats: tuple[str, ...] = ("docx", "pdf", "html")
    stem: str | None = None
    max_level: int | None = None
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
        object.__setattr__(self, "profile", self.profile.strip().lower())
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
    def from_dict(cls, data: Mapping[str, object]) -> ApiBuildConfig:
        """Reconstruct build config from serialized data.

        Args:
            data: Mapping from JSON or ``[tool.oodocs.apidoc]``.

        Returns:
            Validated build configuration.

        Examples:
            Build a config object from a deployment manifest and use it to
            render a package reference:

            ```python
            from oodocs.apidoc import ApiBuildConfig, collect_api

            build = ApiBuildConfig.from_dict({
                "collector": "griffe",
                "public_policy": "__all__",
                "profile": "reference",
                "formats": ["docx", "html"],
                "out": "artifacts/api",
            })
            api = collect_api(".", config=build.collection)
            api.to_document(profile=build.profile).save_all(
                build.output_dir or "artifacts/api",
                formats=build.output_formats,
            )
            ```
        """

        normalized = _normalize_config_mapping(data)
        _validate_known_config_keys(normalized)
        output_formats = normalized.get(
            "output_formats",
            normalized.get("formats", normalized.get("to", ("docx", "pdf", "html"))),
        )
        output_dir = normalized.get("output_dir", normalized.get("out"))
        return cls(
            collection=ApiCollectConfig.from_dict(normalized),
            profile=str(normalized.get("profile", "reference")),
            output_formats=_format_tuple(output_formats),
            stem=_optional_str(normalized.get("stem")),
            max_level=_optional_int(normalized.get("max_level")),
            sidecars=bool(normalized.get("sidecars", False)),
            output_dir=_optional_str(output_dir),
            kind=_string_tuple(normalized.get("kind", ())),
            module_prefix=_optional_config_str("module_prefix", normalized.get("module_prefix")),
        )

    @classmethod
    def from_pyproject(cls, path: PathLike = "pyproject.toml") -> ApiBuildConfig:
        """Read build config from ``pyproject.toml``.

        Args:
            path: Project root directory or ``pyproject.toml`` path.

        Returns:
            Build configuration from ``[tool.oodocs.apidoc]``.

        Raises:
            FileNotFoundError: If the pyproject file does not exist.
            KeyError: If ``[tool.oodocs.apidoc]`` is missing.
            tomllib.TOMLDecodeError: If the pyproject file is invalid TOML.

        Examples:
            Reuse the same build defaults that ``oodocs apidoc build`` reads:

            ```python
            from oodocs.apidoc import ApiBuildConfig, collect_api

            build = ApiBuildConfig.from_pyproject(".")
            api = collect_api(".", config=build.collection)
            api.to_document(profile=build.profile).save_all(
                build.output_dir or "artifacts/api",
                stem=build.stem,
                formats=build.output_formats,
            )
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
        with _config_import_paths(pyproject_path):
            return cls.from_dict(section)

    @classmethod
    def read_json(cls, path: PathLike) -> ApiBuildConfig:
        """Read a build config JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            Validated build configuration.

        Examples:
            Load a build config written by ``ApiBuildConfig.write_json(...)``:

            ```python
            from oodocs.apidoc import ApiBuildConfig

            build = ApiBuildConfig.read_json("apidoc-build.json")
            ```
        """

        config_path = Path(path)
        with _config_import_paths(config_path):
            return cls.from_dict(json.loads(config_path.read_text(encoding="utf-8")))

    @classmethod
    def read_file(cls, path: PathLike) -> ApiBuildConfig:
        """Read a build config from JSON or ``pyproject.toml``.

        Args:
            path: JSON sidecar, project root directory, or TOML file path.

        Returns:
            Validated build configuration.

        Examples:
            Let scripts accept either ``pyproject.toml`` or JSON config paths:

            ```python
            from oodocs.apidoc import ApiBuildConfig

            build = ApiBuildConfig.read_file("pyproject.toml")
            ```
        """

        config_path = Path(path)
        if config_path.is_dir() or config_path.suffix.lower() == ".toml":
            return cls.from_pyproject(config_path)
        return cls.read_json(config_path)

    def validate(self) -> None:
        """Validate build settings.

        Raises:
            ValueError: If profile, formats, or heading depth are invalid.

        Examples:
            Validate build defaults before writing them into a repository:

            ```python
            from oodocs.apidoc import ApiBuildConfig

            build = ApiBuildConfig(
                profile="website",
                output_formats=("html",),
            )
            build.validate()
            ```
        """

        from oodocs.apidoc.styles import resolve_profile

        resolve_profile(self.profile)
        if self.max_level is not None and self.max_level < 1:
            raise ValueError("max_level must be >= 1")
        if not self.output_formats:
            raise ValueError("output_formats must include at least one format")

    def to_dict(self) -> dict[str, object]:
        """Return this build config as JSON-serializable data.

        Returns:
            Deterministic mapping containing both collection and build options.

        Examples:
            Generate config data for a custom repository setup wizard:

            ```python
            from oodocs.apidoc import ApiBuildConfig

            payload = ApiBuildConfig(
                profile="website",
                output_formats=("html",),
                output_dir="artifacts/api",
            ).to_dict()
            ```
        """

        values = self.collection.to_dict()
        values.update(
            {
                "profile": self.profile,
                "output_formats": list(self.output_formats),
                "stem": self.stem,
                "max_level": self.max_level,
                "sidecars": self.sidecars,
                "output_dir": self.output_dir,
                "kind": list(self.kind),
                "module_prefix": self.module_prefix,
            }
        )
        return values

    def write_json(self, path: PathLike) -> Path:
        """Write this build config as deterministic JSON.

        Args:
            path: Output JSON path.

        Returns:
            Written path.

        Examples:
            Write build defaults for a repository-local automation script:

            ```python
            from oodocs.apidoc import ApiBuildConfig

            build = ApiBuildConfig(
                profile="reference",
                output_dir="artifacts/api",
                sidecars=True,
            )
            build.write_json("apidoc-build.json")
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
            from oodocs.apidoc import ApiBuildConfig

            text = ApiBuildConfig(profile="website", output_formats=("html",)).to_toml_section()
            ```
        """

        lines = ["[tool.oodocs.apidoc]"]
        for key, value in self.to_dict().items():
            if value is None or value == []:
                continue
            lines.append(f"{key.replace('_', '-')} = {_toml_value(value)}")
        return "\n".join(lines) + "\n"

    def write_pyproject(self, path: PathLike = "pyproject.toml") -> Path:
        """Append this config to a ``pyproject.toml`` file.

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
            from oodocs.apidoc import ApiBuildConfig

            ApiBuildConfig(
                profile="website",
                output_formats=("html",),
                output_dir="artifacts/api",
                sidecars=True,
            ).write_pyproject(".")
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


@contextmanager
def _config_import_paths(path: Path):
    base = path.parent.resolve()
    roots = [base]
    src_root = base / "src"
    if src_root.is_dir():
        roots.append(src_root.resolve())

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
    "ApiBuildConfig",
    "ApiCollectConfig",
    "ApiCollectorName",
    "ApiFallbackCollectorName",
    "ApiPublicPolicy",
    "ApiPublicPolicyName",
    "normalize_explicit_names",
]
