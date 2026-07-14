"""Build, validate, and render related documents with shared context.

``DocumentSuite`` deliberately keeps templating in Python.  Factories receive a
single context containing ordinary variables, a citation library, and an asset
resolver whose paths are independent of the process working directory.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from oodocs.compatibility import OutputFormat, normalize_output_formats
from oodocs.components.base import Block, Component
from oodocs.components.cover import CoverPage
from oodocs.components.descriptions import DescriptionList
from oodocs.components.media import Figure, SubFigureGroup
from oodocs.components.references import CitationLibrary
from oodocs.core import OODocsError, PathLike
from oodocs.document import Document
from oodocs.validation import (
    ValidationIssue,
    ValidationPolicy,
    ValidationResult,
)
from oodocs.workflows import OutputBundle

if TYPE_CHECKING:
    from typing import TypeAlias

    DocumentFactory: TypeAlias = Callable[["DocumentSuiteContext"], Document]
else:
    DocumentFactory = Callable[["DocumentSuiteContext"], Document]


class AmbiguousAssetError(ValueError):
    """Raised when a relative asset exists in more than one registered root."""

    def __init__(self, path: PathLike, candidates: Sequence[Path]) -> None:
        self.path = Path(path)
        self.candidates = tuple(candidates)
        rendered = ", ".join(str(candidate) for candidate in self.candidates)
        super().__init__(f"Asset {self.path!s} is ambiguous; found: {rendered}")


@dataclass(frozen=True, slots=True)
class AssetResolver:
    """Resolve assets against a suite root and then registered search roots.

    Relative registered roots are interpreted relative to the suite root after
    a resolver is placed in ``DocumentSuiteContext``.  A standalone resolver
    anchors them to the directory in which it was constructed, so a later
    ``chdir`` cannot change resolution.
    """

    roots: tuple[Path, ...] = ()
    _suite_root: Path | None = field(default=None, init=False, repr=False, compare=False)
    _construction_root: Path = field(
        default_factory=lambda: Path.cwd().resolve(strict=False),
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "roots", tuple(Path(root).expanduser() for root in self.roots))

    def bound_to(self, root: PathLike) -> AssetResolver:
        """Return a resolver whose relative roots are anchored to ``root``."""

        suite_root = _absolute_path(root)
        registered = tuple(
            _absolute_path(candidate, base=suite_root) for candidate in self.roots
        )
        bound = AssetResolver(registered)
        object.__setattr__(bound, "_suite_root", suite_root)
        return bound

    def resolve(self, path: PathLike) -> Path | None:
        """Return one existing path or ``None`` when the asset is missing.

        Search order is absolute path, suite-root-relative path, then registered
        roots.  The suite-root candidate wins by design.  Multiple matches
        among registered roots are an error instead of an order-dependent pick.
        """

        requested = Path(path).expanduser()
        if requested.is_absolute():
            candidate = requested.resolve(strict=False)
            return candidate if candidate.is_file() else None

        if self._suite_root is not None:
            suite_candidate = (self._suite_root / requested).resolve(strict=False)
            if suite_candidate.is_file():
                return suite_candidate

        base = self._suite_root or self._construction_root
        matches: list[Path] = []
        seen: set[Path] = set()
        for root in self.roots:
            registered_root = _absolute_path(root, base=base)
            candidate = (registered_root / requested).resolve(strict=False)
            if candidate.is_file() and candidate not in seen:
                matches.append(candidate)
                seen.add(candidate)

        if len(matches) > 1:
            matches.sort(key=lambda candidate: candidate.as_posix().casefold())
            raise AmbiguousAssetError(requested, matches)
        return matches[0] if matches else None

    def require(self, path: PathLike) -> Path:
        """Resolve ``path`` or raise ``FileNotFoundError`` immediately."""

        resolved = self.resolve(path)
        if resolved is None:
            raise FileNotFoundError(f"Suite asset does not exist: {Path(path)}")
        return resolved


@dataclass(frozen=True, slots=True)
class DocumentSuiteContext:
    """Shared, renderer-neutral inputs passed to every suite factory."""

    root: Path
    output_dir: Path
    variables: Mapping[str, object] = field(default_factory=dict)
    assets: AssetResolver = field(default_factory=AssetResolver)
    citations: CitationLibrary = field(default_factory=CitationLibrary)

    def __post_init__(self) -> None:
        root = _absolute_path(self.root)
        output_dir = _absolute_path(self.output_dir, base=root)
        if not isinstance(self.assets, AssetResolver):
            raise TypeError("DocumentSuiteContext.assets must be an AssetResolver")
        if not isinstance(self.citations, CitationLibrary):
            raise TypeError("DocumentSuiteContext.citations must be a CitationLibrary")
        if not isinstance(self.variables, Mapping):
            raise TypeError("DocumentSuiteContext.variables must be a mapping")

        object.__setattr__(self, "root", root)
        object.__setattr__(self, "output_dir", output_dir)
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))
        object.__setattr__(self, "assets", self.assets.bound_to(root))


@dataclass(frozen=True, slots=True)
class DocumentSuiteItem:
    """One named document factory and its output policy."""

    name: str
    stem: str
    factory: DocumentFactory
    formats: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        name = _nonblank(self.name, label="Document suite item name")
        stem = _validate_stem(self.stem)
        if not callable(self.factory):
            raise TypeError("DocumentSuiteItem.factory must be callable")
        normalized_formats: tuple[OutputFormat, ...] | None = None
        if self.formats is not None:
            normalized_formats = normalize_output_formats(self.formats)
            if not normalized_formats:
                raise ValueError("DocumentSuiteItem.formats must not be empty")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "stem", stem)
        object.__setattr__(self, "formats", normalized_formats)


@dataclass(frozen=True, slots=True)
class DocumentSuiteBundle:
    """Rendered ``OutputBundle`` objects indexed by suite document name."""

    name: str
    output_dir: Path
    outputs: Mapping[str, OutputBundle]
    variables: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _nonblank(self.name, label="Suite name"))
        object.__setattr__(self, "output_dir", _absolute_path(self.output_dir))
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))

    def __getitem__(self, name: str) -> OutputBundle:
        return self.outputs[name]

    def __iter__(self) -> Iterator[tuple[str, OutputBundle]]:
        return iter(self.outputs.items())

    def __len__(self) -> int:
        return len(self.outputs)

    def as_manifest(self) -> dict[str, object]:
        """Return a deterministic, JSON-compatible suite manifest mapping."""

        outputs: dict[str, dict[str, str]] = {}
        for document_name, bundle in self.outputs.items():
            outputs[document_name] = {
                output_format: _manifest_path(path, base=self.output_dir)
                for output_format, path in bundle
            }
        return {
            "suite": self.name,
            "variables": _serializable_mapping(self.variables),
            "outputs": outputs,
        }

    def save_manifest(
        self,
        path: PathLike | None = None,
        *,
        indent: int | None = 2,
    ) -> Path:
        """Write ``as_manifest()`` as UTF-8 JSON and return its path."""

        destination = (
            self.output_dir / "suite-manifest.json"
            if path is None
            else _absolute_path(path, base=self.output_dir)
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(
                self.as_manifest(),
                ensure_ascii=False,
                indent=indent,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return destination


class DocumentSuiteValidationError(OODocsError):
    """Raised when any suite document has blocking validation issues."""

    def __init__(
        self,
        results: Mapping[str, ValidationResult],
        *,
        formats: Mapping[str, tuple[OutputFormat, ...]],
        policy: ValidationPolicy | None = None,
    ) -> None:
        self.results = MappingProxyType(dict(results))
        self.formats = MappingProxyType(dict(formats))
        self.policy = policy
        failed = [
            name
            for name, result in self.results.items()
            if not result.ok_for(self.formats[name])
            or (
                policy is not None
                and result.blocking_warnings(policy, formats=self.formats[name])
            )
        ]
        super().__init__(
            "Document suite validation failed for: " + ", ".join(failed)
        )


@dataclass(slots=True)
class DocumentSuite:
    """Manage related documents built from one explicit shared context."""

    name: str
    context: DocumentSuiteContext
    items: list[DocumentSuiteItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = _nonblank(self.name, label="Suite name")
        if not isinstance(self.context, DocumentSuiteContext):
            raise TypeError("DocumentSuite.context must be a DocumentSuiteContext")
        self.items = list(self.items)
        seen: set[str] = set()
        for item in self.items:
            if not isinstance(item, DocumentSuiteItem):
                raise TypeError("DocumentSuite.items must contain DocumentSuiteItem objects")
            if item.name in seen:
                raise ValueError(f"Duplicate document suite item name: {item.name!r}")
            seen.add(item.name)

    def add(
        self,
        name: str,
        factory: DocumentFactory,
        stem: str | None = None,
        formats: Iterable[str] | None = None,
    ) -> DocumentSuite:
        """Register one document factory and return this suite."""

        normalized_name = _nonblank(name, label="Document suite item name")
        if any(item.name == normalized_name for item in self.items):
            raise ValueError(f"Duplicate document suite item name: {normalized_name!r}")
        item = DocumentSuiteItem(
            name=normalized_name,
            stem=stem if stem is not None else _default_stem(normalized_name),
            factory=factory,
            formats=tuple(formats) if formats is not None else None,
        )
        self.items.append(item)
        return self

    def build(self, name: str) -> Document:
        """Build one document and require every suite-managed asset."""

        item = self._item(name)
        document = self._build_item(item)
        _resolve_document_assets(document, self.context.assets, require=True)
        return document

    def validate_all(
        self,
        *,
        formats: Iterable[str] | None = None,
        policy: ValidationPolicy | None = None,
        raise_on_error: bool = False,
    ) -> Mapping[str, ValidationResult]:
        """Build and validate every document, including all suite assets."""

        requested = tuple(formats) if formats is not None else None
        results: dict[str, ValidationResult] = {}
        formats_by_name: dict[str, tuple[OutputFormat, ...]] = {}
        for item in self.items:
            item_formats = _formats_for(item, requested)
            document = self._build_item(item)
            asset_issues = _resolve_document_assets(
                document,
                self.context.assets,
                require=False,
                formats=item_formats,
            )
            document_result = document.validate(formats=item_formats, policy=policy)
            results[item.name] = ValidationResult(
                (*asset_issues, *_without_duplicate_asset_issues(document_result, asset_issues))
            )
            formats_by_name[item.name] = item_formats

        frozen_results: Mapping[str, ValidationResult] = MappingProxyType(results)
        if raise_on_error and _has_blocking_results(
            frozen_results,
            formats_by_name,
            policy=policy,
        ):
            raise DocumentSuiteValidationError(
                frozen_results,
                formats=formats_by_name,
                policy=policy,
            )
        return frozen_results

    def save_all(
        self,
        output_dir: PathLike | None = None,
        *,
        formats: Iterable[str] | None = None,
        validate: bool = True,
        policy: ValidationPolicy | None = None,
        verbose: bool = False,
    ) -> DocumentSuiteBundle:
        """Build all documents, validate before writing, and render outputs.

        Returns:
            The rendered suite bundle, including per-document outputs and
            shared context variables.
        """

        destination = (
            self.context.output_dir
            if output_dir is None
            else _absolute_path(output_dir, base=self.context.root)
        )
        requested = tuple(formats) if formats is not None else None
        documents: dict[str, Document] = {}
        results: dict[str, ValidationResult] = {}
        formats_by_name: dict[str, tuple[OutputFormat, ...]] = {}

        # Complete every build and validation before creating any output so a
        # late failing document cannot leave a partially rendered suite.
        for item in self.items:
            item_formats = _formats_for(item, requested)
            document = self._build_item(item)
            formats_by_name[item.name] = item_formats
            if validate:
                asset_issues = _resolve_document_assets(
                    document,
                    self.context.assets,
                    require=False,
                    formats=item_formats,
                )
                document_result = document.validate(formats=item_formats, policy=policy)
                results[item.name] = ValidationResult(
                    (
                        *asset_issues,
                        *_without_duplicate_asset_issues(document_result, asset_issues),
                    )
                )
            else:
                _resolve_document_assets(document, self.context.assets, require=True)
            documents[item.name] = document

        if validate and _has_blocking_results(
            results,
            formats_by_name,
            policy=policy,
        ):
            raise DocumentSuiteValidationError(
                results,
                formats=formats_by_name,
                policy=policy,
            )

        bundles: dict[str, OutputBundle] = {}
        for item in self.items:
            bundles[item.name] = documents[item.name].save_all(
                destination,
                stem=item.stem,
                formats=formats_by_name[item.name],
                validate=False,
                verbose=verbose,
            )
        return DocumentSuiteBundle(
            name=self.name,
            output_dir=destination,
            outputs=bundles,
            variables=self.context.variables,
        )

    def _item(self, name: str) -> DocumentSuiteItem:
        for item in self.items:
            if item.name == name:
                return item
        raise KeyError(f"Unknown document suite item: {name!r}")

    def _build_item(self, item: DocumentSuiteItem) -> Document:
        document = item.factory(self.context)
        if not isinstance(document, Document):
            raise TypeError(
                f"Factory for {item.name!r} returned {type(document)!r}, not Document"
            )
        # Citation ownership stays with the factory.  In particular, this code
        # never replaces a document's existing library with the shared one.
        return document


def _resolve_document_assets(
    document: Document,
    resolver: AssetResolver,
    *,
    require: bool,
    formats: tuple[OutputFormat, ...] | None = None,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    def resolve(owner: object, attribute: str, path: str) -> None:
        source = getattr(owner, attribute)
        if not isinstance(source, (str, Path)):
            return
        try:
            resolved = resolver.resolve(source)
        except AmbiguousAssetError as exc:
            if require:
                raise
            issues.append(
                ValidationIssue(
                    "error",
                    "asset-ambiguous",
                    str(exc),
                    path=path,
                    formats=formats or normalize_output_formats(),
                )
            )
            return
        if resolved is None:
            if require:
                resolver.require(source)
            issues.append(
                ValidationIssue(
                    "error",
                    "missing-suite-asset",
                    f"Suite asset does not exist: {source}.",
                    path=path,
                    formats=formats or normalize_output_formats(),
                )
            )
            return
        setattr(owner, attribute, resolved)

    cover = document.settings.title_matter.cover
    if cover is not None:
        resolve(cover, "logo", "document.settings.title_matter.cover.logo")
        for group_name, blocks in (
            ("note", cover.note),
            ("extra_top", cover.extra_top),
            ("extra_bottom", cover.extra_bottom),
        ):
            _walk_asset_blocks(
                blocks,
                f"document.settings.title_matter.cover.{group_name}",
                resolve,
            )
    _walk_asset_blocks(document.body.children, "document.body", resolve)
    return tuple(issues)


def _walk_asset_blocks(
    blocks: Sequence[Block],
    path: str,
    resolve: Callable[[object, str, str], None],
    *,
    _seen: set[int] | None = None,
) -> None:
    seen = _seen if _seen is not None else set()
    for index, block in enumerate(blocks):
        block_id = id(block)
        if block_id in seen:
            continue
        seen.add(block_id)
        block_path = f"{path}.children[{index}]"
        if isinstance(block, Figure):
            resolve(block, "image_source", f"{block_path}.image_source")
            continue
        if isinstance(block, SubFigureGroup):
            for child_index, child in enumerate(block.subfigures):
                resolve(
                    child,
                    "image_source",
                    f"{block_path}.subfigures[{child_index}].image_source",
                )
            continue
        if isinstance(block, Component):
            _walk_asset_blocks(
                block.composed_blocks(),
                f"{block_path}.composed_blocks",
                resolve,
                _seen=seen,
            )
            continue
        if isinstance(block, DescriptionList):
            for item_index, item in enumerate(block.items):
                _walk_asset_blocks(
                    item.children,
                    f"{block_path}.items[{item_index}]",
                    resolve,
                    _seen=seen,
                )
            continue

        children = getattr(block, "children", None)
        if isinstance(children, (list, tuple)) and all(
            isinstance(child, Block) for child in children
        ):
            _walk_asset_blocks(
                children,
                block_path,
                resolve,
                _seen=seen,
            )
        item_children = getattr(block, "item_children", None)
        if isinstance(item_children, (list, tuple)):
            for item_index, nested in enumerate(item_children):
                if isinstance(nested, (list, tuple)) and all(
                    isinstance(child, Block) for child in nested
                ):
                    _walk_asset_blocks(
                        nested,
                        f"{block_path}.items[{item_index}]",
                        resolve,
                        _seen=seen,
                    )


def _formats_for(
    item: DocumentSuiteItem,
    requested: tuple[str, ...] | None,
) -> tuple[OutputFormat, ...]:
    if item.formats is not None:
        return normalize_output_formats(item.formats)
    normalized = normalize_output_formats(requested)
    if not normalized:
        raise ValueError("Document suite output formats must not be empty")
    return normalized


def _without_duplicate_asset_issues(
    result: ValidationResult,
    suite_issues: Sequence[ValidationIssue],
) -> tuple[ValidationIssue, ...]:
    suite_paths = {issue.path for issue in suite_issues}
    return tuple(
        issue
        for issue in result.issues
        if not (
            issue.code in {"missing-image-file", "invalid-image-file"}
            and issue.path in suite_paths
        )
    )


def _has_blocking_results(
    results: Mapping[str, ValidationResult],
    formats: Mapping[str, tuple[OutputFormat, ...]],
    *,
    policy: ValidationPolicy | None,
) -> bool:
    return any(
        not result.ok_for(formats[name])
        or (
            policy is not None
            and bool(result.blocking_warnings(policy, formats=formats[name]))
        )
        for name, result in results.items()
    )


def _absolute_path(path: PathLike, *, base: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = (base if base is not None else Path.cwd()) / candidate
    return candidate.resolve(strict=False)


def _nonblank(value: str, *, label: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _default_stem(value: str) -> str:
    pieces: list[str] = []
    previous_was_separator = False
    for character in value.strip().lower():
        if character.isalnum() or character in {"-", "_"}:
            pieces.append(character)
            previous_was_separator = False
        elif not previous_was_separator:
            pieces.append("-")
            previous_was_separator = True
    return "".join(pieces).strip("-_") or "document"


def _validate_stem(value: str) -> str:
    stem = _nonblank(value, label="Document suite item stem")
    if stem in {".", ".."} or Path(stem).name != stem or "/" in stem or "\\" in stem:
        raise ValueError("Document suite item stem must be a filename, not a path")
    return stem


_UNSERIALIZABLE = object()


def _serializable_mapping(values: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            continue
        converted = _serializable_value(value)
        if converted is not _UNSERIALIZABLE:
            result[key] = converted
    return result


def _serializable_value(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else _UNSERIALIZABLE
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return _serializable_mapping(value)
    if isinstance(value, (list, tuple)):
        converted = [_serializable_value(item) for item in value]
        return [item for item in converted if item is not _UNSERIALIZABLE]
    return _UNSERIALIZABLE


def _manifest_path(path: Path, *, base: Path) -> str:
    absolute = _absolute_path(path, base=base)
    try:
        return absolute.relative_to(base).as_posix()
    except ValueError:
        return absolute.as_posix()


__all__ = [
    "AmbiguousAssetError",
    "AssetResolver",
    "DocumentSuite",
    "DocumentSuiteBundle",
    "DocumentSuiteContext",
    "DocumentSuiteItem",
    "DocumentSuiteValidationError",
]
