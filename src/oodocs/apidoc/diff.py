"""API snapshot and diff helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from oodocs.apidoc.coverage import check_api_docs
from oodocs.apidoc.model import ApiObject, ApiPackage
from oodocs.components.blocks import Chapter, Paragraph
from oodocs.components.media import Table
from oodocs.core import PathLike
from oodocs.document import Document


@dataclass(slots=True)
class ApiSnapshot:
    """Deterministic snapshot of public API objects.

    Attributes:
        name: Snapshot package name.
        version: Optional package version.
        objects: Public objects keyed by qualname.

    Examples:
        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.diff import ApiSnapshot

        snapshot = ApiSnapshot.from_package(collect_api("oodocs"))
        snapshot.save_json("api-snapshot.json")
        ```
    """

    name: str
    version: str | None = None
    objects: dict[str, dict[str, object]] = field(default_factory=dict)

    @classmethod
    def from_package(cls, api: ApiPackage) -> ApiSnapshot:
        """Create a snapshot from a package object.

        Args:
            api: Collected API package.

        Returns:
            Snapshot containing deterministic serialized public objects keyed
            by fully qualified name.

        Examples:
            Persist a baseline snapshot during a release job:

            ```python
            from oodocs.apidoc import ApiSnapshot, collect_api

            api = collect_api(".", public_policy="__all__")
            ApiSnapshot.from_package(api).save_json("artifacts/api-base.json")
            ```
        """

        return cls(
            api.name,
            version=api.version,
            objects={obj.qualname: obj.to_dict() for obj in api.select_public_objects()},
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable snapshot mapping.

        Examples:
            Serialize a snapshot before writing it through custom storage:

            ```python
            from oodocs.apidoc import ApiSnapshot, collect_api

            snapshot = ApiSnapshot.from_package(collect_api("."))
            payload = snapshot.to_dict()
            ```
        """

        return {"name": self.name, "version": self.version, "objects": self.objects}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiSnapshot:
        """Reconstruct a snapshot from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Snapshot object.

        Examples:
            Rehydrate a snapshot payload before computing a diff:

            ```python
            from oodocs.apidoc import ApiSnapshot

            snapshot = ApiSnapshot.from_dict({
                "name": "mypkg",
                "version": None,
                "objects": {},
            })
            ```
        """

        return cls(
            name=str(data["name"]),
            version=data.get("version"),  # type: ignore[arg-type]
            objects=dict(data.get("objects", {})),  # type: ignore[arg-type]
        )

    def save_json(self, path: PathLike) -> Path:
        """Write snapshot JSON.

        Args:
            path: Output JSON path.

        Returns:
            Written path.

        Examples:
            Write a release baseline snapshot:

            ```python
            from oodocs.apidoc import ApiSnapshot, collect_api

            api = collect_api(".")
            ApiSnapshot.from_package(api).save_json("artifacts/api-base.json")
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
    def load_json(cls, path: PathLike) -> ApiSnapshot:
        """Read snapshot JSON.

        Args:
            path: Snapshot JSON path.

        Returns:
            Snapshot object.

        Raises:
            FileNotFoundError: If the snapshot path does not exist.
            json.JSONDecodeError: If the snapshot is not valid JSON.

        Examples:
            Load two snapshots and render an API diff document:

            ```python
            from oodocs.apidoc import ApiSnapshot, diff_api

            base = ApiSnapshot.load_json("artifacts/api-base.json")
            head = ApiSnapshot.load_json("artifacts/api-head.json")
            diff = diff_api(base, head)
            document = diff.to_document()
            ```
        """

        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(slots=True)
class ApiDiffResult:
    """Difference between two API snapshots.

    Attributes:
        base_name: Base snapshot name.
        head_name: Head snapshot name.
        added: Public objects added in head.
        removed: Public objects removed from head.
        changed_signatures: Pairs whose signatures changed.
        changed_defaults: Pairs whose parameter defaults changed.
        changed_parameter_annotations: Pairs whose parameter annotations
            changed.
        changed_return_annotations: Pairs whose return annotations changed.
        changed_docstrings: Pairs whose summary/description changed.
        deprecated: Public objects newly or currently marked deprecated.
        coverage_delta: Documentation coverage delta summary.

    Examples:
        Compare two snapshots and place the generated diff sections in an
        OODocs document:

        ```python
        from oodocs.apidoc import ApiSnapshot, diff_api

        base = ApiSnapshot.load_json("artifacts/api-base.json")
        head = ApiSnapshot.load_json("artifacts/api-head.json")
        diff = diff_api(base, head)
        diff.to_document(title="Public API Changes").save_all("artifacts/api-diff")
        ```
    """

    base_name: str
    head_name: str
    added: list[ApiObject]
    removed: list[ApiObject]
    changed_signatures: list[tuple[ApiObject, ApiObject]]
    changed_defaults: list[tuple[ApiObject, ApiObject]]
    changed_parameter_annotations: list[tuple[ApiObject, ApiObject]]
    changed_return_annotations: list[tuple[ApiObject, ApiObject]]
    changed_docstrings: list[tuple[ApiObject, ApiObject]]
    deprecated: list[ApiObject]
    coverage_delta: dict[str, object]

    def to_summary_table(self) -> Table:
        """Return a compact diff summary table.

        Returns:
            OODocs table with counts for added, removed, changed, deprecated,
            and coverage-delta categories.

        Examples:
            Insert a high-level API change summary into release notes:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiSnapshot, diff_api

            base = ApiSnapshot.load_json("artifacts/api-base.json")
            head = ApiSnapshot.load_json("artifacts/api-head.json")
            diff = diff_api(base, head)
            doc = Document("Release Notes", Chapter("API Changes", diff.to_summary_table()))
            ```
        """

        rows = [
            ["Added", str(len(self.added))],
            ["Removed", str(len(self.removed))],
            ["Changed signatures", str(len(self.changed_signatures))],
            ["Changed defaults", str(len(self.changed_defaults))],
            ["Changed parameter annotations", str(len(self.changed_parameter_annotations))],
            ["Changed return annotations", str(len(self.changed_return_annotations))],
            ["Changed docstrings", str(len(self.changed_docstrings))],
            ["Deprecated", str(len(self.deprecated))],
            ["Coverage delta", str(self.coverage_delta.get("object_coverage_delta", ""))],
        ]
        return Table(["Metric", "Count"], rows, caption="API diff summary", split=True)

    def to_coverage_delta_table(self) -> Table:
        """Return coverage delta details as an OODocs table.

        Returns:
            Table containing base/head public object counts, documented object
            counts, coverage ratios, and coverage delta.

        Examples:
            Add coverage movement to a release review document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiSnapshot, diff_api

            base = ApiSnapshot.load_json("artifacts/api-base.json")
            head = ApiSnapshot.load_json("artifacts/api-head.json")
            diff = diff_api(base, head)
            doc = Document(
                "API Review",
                Chapter("Coverage Movement", diff.to_coverage_delta_table()),
            )
            ```
        """

        rows = [
            ["Base public objects", _format_delta_value(self.coverage_delta.get("base_public_object_count"))],
            ["Head public objects", _format_delta_value(self.coverage_delta.get("head_public_object_count"))],
            [
                "Base documented objects",
                _format_delta_value(self.coverage_delta.get("base_documented_object_count")),
            ],
            [
                "Head documented objects",
                _format_delta_value(self.coverage_delta.get("head_documented_object_count")),
            ],
            ["Base object coverage", _format_delta_value(self.coverage_delta.get("base_object_coverage"))],
            ["Head object coverage", _format_delta_value(self.coverage_delta.get("head_object_coverage"))],
            ["Object coverage delta", _format_delta_value(self.coverage_delta.get("object_coverage_delta"))],
        ]
        return Table(["Metric", "Value"], rows, caption="API coverage delta", split=True)

    def to_sections(self) -> list[Chapter]:
        """Return detailed diff sections.

        Returns:
            Chapters for coverage movement and each non-empty change category.
            The result can be appended to a larger OODocs document.

        Examples:
            Insert API change details into a release report:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiSnapshot, diff_api

            base = ApiSnapshot.load_json("artifacts/api-base.json")
            head = ApiSnapshot.load_json("artifacts/api-head.json")
            diff = diff_api(base, head)
            doc = Document(
                "Release Report",
                Chapter("API Changes", *diff.to_sections()),
            )
            ```
        """

        sections: list[Chapter] = [Chapter("Coverage Delta", self.to_coverage_delta_table())]
        for title, objects in (
            ("Added API", self.added),
            ("Removed API", self.removed),
            ("Deprecated API", self.deprecated),
        ):
            if objects:
                sections.append(Chapter(title, _objects_table(objects)))
        if self.changed_signatures:
            sections.append(Chapter("Changed Signatures", _pairs_table(self.changed_signatures, "Signature")))
        if self.changed_defaults:
            sections.append(Chapter("Changed Defaults", _pairs_table(self.changed_defaults, "Defaults")))
        if self.changed_parameter_annotations:
            sections.append(
                Chapter(
                    "Changed Parameter Annotations",
                    _pairs_table(self.changed_parameter_annotations, "Parameter annotations"),
                )
            )
        if self.changed_return_annotations:
            sections.append(
                Chapter(
                    "Changed Return Annotations",
                    _pairs_table(self.changed_return_annotations, "Return annotation"),
                )
            )
        if self.changed_docstrings:
            sections.append(Chapter("Changed Docstrings", _pairs_table(self.changed_docstrings, "Summary")))
        return sections

    def to_document(self, *, title: str | None = None) -> Document:
        """Return this diff as an OODocs document.

        Args:
            title: Optional document title. Defaults to ``"API Diff"``.

        Returns:
            Renderable OODocs document containing a summary chapter plus the
            detailed diff sections.

        Examples:
            Render a standalone API change bundle:

            ```python
            from oodocs.apidoc import ApiSnapshot, diff_api

            base = ApiSnapshot.load_json("artifacts/api-base.json")
            head = ApiSnapshot.load_json("artifacts/api-head.json")
            diff = diff_api(base, head)
            diff.to_document(title="Public API Changes").save_all(
                "artifacts/api-diff",
                stem="api-diff",
            )
            ```
        """

        return Document(
            title or "API Diff",
            Chapter(
                "Summary",
                Paragraph(f"{self.base_name} -> {self.head_name}"),
                self.to_summary_table(),
            ),
            *self.to_sections(),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized data.

        Returns:
            JSON-serializable diff mapping containing changed objects and
            coverage deltas.

        Examples:
            Store a machine-readable API diff next to rendered documents:

            ```python
            import json
            from pathlib import Path

            from oodocs.apidoc import ApiSnapshot, diff_api

            base = ApiSnapshot.load_json("artifacts/api-base.json")
            head = ApiSnapshot.load_json("artifacts/api-head.json")
            diff = diff_api(base, head)
            Path("artifacts/api-diff.json").write_text(
                json.dumps(diff.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            ```
        """

        return {
            "base_name": self.base_name,
            "head_name": self.head_name,
            "added": [obj.to_dict() for obj in self.added],
            "removed": [obj.to_dict() for obj in self.removed],
            "changed_signatures": [[base.to_dict(), head.to_dict()] for base, head in self.changed_signatures],
            "changed_defaults": [[base.to_dict(), head.to_dict()] for base, head in self.changed_defaults],
            "changed_parameter_annotations": [
                [base.to_dict(), head.to_dict()] for base, head in self.changed_parameter_annotations
            ],
            "changed_return_annotations": [
                [base.to_dict(), head.to_dict()] for base, head in self.changed_return_annotations
            ],
            "changed_docstrings": [[base.to_dict(), head.to_dict()] for base, head in self.changed_docstrings],
            "deprecated": [obj.to_dict() for obj in self.deprecated],
            "coverage_delta": self.coverage_delta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiDiffResult:
        """Reconstruct a diff result from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Diff result that can be rendered into OODocs blocks.

        Raises:
            KeyError: If the serialized data is missing required snapshot
                names.
            ValueError: If a serialized changed-object pair does not contain
                exactly two API objects.

        Examples:
            Restore a diff sidecar payload and append its summary table to a
            document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiDiffResult

            diff = ApiDiffResult.from_dict(saved_diff)
            doc = Document("API Review", Chapter("Summary", diff.to_summary_table()))
            ```
        """

        return cls(
            base_name=str(data["base_name"]),
            head_name=str(data["head_name"]),
            added=[
                ApiObject.from_dict(item)
                for item in data.get("added", [])  # type: ignore[union-attr]
            ],
            removed=[
                ApiObject.from_dict(item)
                for item in data.get("removed", [])  # type: ignore[union-attr]
            ],
            changed_signatures=[
                _object_pair_from_dict(item)
                for item in data.get("changed_signatures", [])  # type: ignore[union-attr]
            ],
            changed_defaults=[
                _object_pair_from_dict(item)
                for item in data.get("changed_defaults", [])  # type: ignore[union-attr]
            ],
            changed_parameter_annotations=[
                _object_pair_from_dict(item)
                for item in data.get("changed_parameter_annotations", [])  # type: ignore[union-attr]
            ],
            changed_return_annotations=[
                _object_pair_from_dict(item)
                for item in data.get("changed_return_annotations", [])  # type: ignore[union-attr]
            ],
            changed_docstrings=[
                _object_pair_from_dict(item)
                for item in data.get("changed_docstrings", [])  # type: ignore[union-attr]
            ],
            deprecated=[
                ApiObject.from_dict(item)
                for item in data.get("deprecated", [])  # type: ignore[union-attr]
            ],
            coverage_delta=dict(data.get("coverage_delta", {})),  # type: ignore[arg-type]
        )

    def save_json(self, path: PathLike) -> Path:
        """Write diff sidecar JSON.

        Args:
            path: Output JSON path.

        Returns:
            Written path.

        Examples:
            Store a diff sidecar beside rendered outputs:

            ```python
            from oodocs.apidoc import ApiSnapshot, diff_api

            base = ApiSnapshot.load_json("artifacts/api-base.json")
            head = ApiSnapshot.load_json("artifacts/api-head.json")
            diff = diff_api(base, head)
            diff.save_json("artifacts/api-diff/api-diff.json")
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
    def load_json(cls, path: PathLike) -> ApiDiffResult:
        """Read a diff result JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            Diff result object.

        Raises:
            FileNotFoundError: If the sidecar path does not exist.
            json.JSONDecodeError: If the sidecar is not valid JSON.
            ValueError: If a serialized changed-object pair is malformed.

        Examples:
            Render a diff produced by an earlier CI job:

            ```python
            from oodocs.apidoc import ApiDiffResult

            diff = ApiDiffResult.load_json("artifacts/api-diff/api-diff.json")
            diff.to_document(title="Public API Changes").save_all("artifacts/api-diff")
            ```
        """

        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def diff_api(
    base: ApiPackage | ApiSnapshot,
    head: ApiPackage | ApiSnapshot,
) -> ApiDiffResult:
    """Compare two API packages or snapshots.

    Args:
        base: Base API package or persisted snapshot.
        head: Head API package or persisted snapshot.

    Returns:
        API diff result containing added/removed objects, signature/default
        changes, annotation changes, docstring changes, deprecated objects, and
        coverage deltas.

    Examples:
        Compare two live package collections and render the result:

        ```python
        from oodocs.apidoc import collect_api, diff_api

        base = collect_api("path/to/base/src/mypkg")
        head = collect_api("path/to/head/src/mypkg")
        diff = diff_api(base, head)
        diff.to_document().save_all("artifacts/api-diff")
        ```

        Compare persisted snapshots when the target package should not be
        imported during the reporting job:

        ```python
        from oodocs.apidoc import ApiSnapshot, diff_api

        diff = diff_api(
            ApiSnapshot.load_json("artifacts/api-base.json"),
            ApiSnapshot.load_json("artifacts/api-head.json"),
        )
        ```
    """

    base_snapshot = ApiSnapshot.from_package(base) if isinstance(base, ApiPackage) else base
    head_snapshot = ApiSnapshot.from_package(head) if isinstance(head, ApiPackage) else head
    base_objects = {name: ApiObject.from_dict(data) for name, data in base_snapshot.objects.items()}
    head_objects = {name: ApiObject.from_dict(data) for name, data in head_snapshot.objects.items()}
    base_names = set(base_objects)
    head_names = set(head_objects)
    added = [head_objects[name] for name in sorted(head_names - base_names)]
    removed = [base_objects[name] for name in sorted(base_names - head_names)]
    changed_signatures: list[tuple[ApiObject, ApiObject]] = []
    changed_defaults: list[tuple[ApiObject, ApiObject]] = []
    changed_parameter_annotations: list[tuple[ApiObject, ApiObject]] = []
    changed_return_annotations: list[tuple[ApiObject, ApiObject]] = []
    changed_docstrings: list[tuple[ApiObject, ApiObject]] = []
    for name in sorted(base_names & head_names):
        base_obj = base_objects[name]
        head_obj = head_objects[name]
        if base_obj.signature != head_obj.signature:
            changed_signatures.append((base_obj, head_obj))
        if _defaults(base_obj) != _defaults(head_obj):
            changed_defaults.append((base_obj, head_obj))
        if _parameter_annotations(base_obj) != _parameter_annotations(head_obj):
            changed_parameter_annotations.append((base_obj, head_obj))
        if _return_annotation(base_obj) != _return_annotation(head_obj):
            changed_return_annotations.append((base_obj, head_obj))
        if (base_obj.summary, base_obj.description) != (head_obj.summary, head_obj.description):
            changed_docstrings.append((base_obj, head_obj))
    deprecated = [obj for obj in head_objects.values() if obj.deprecated]
    coverage_delta = _coverage_delta(base, head)
    return ApiDiffResult(
        base_name=base_snapshot.name,
        head_name=head_snapshot.name,
        added=added,
        removed=removed,
        changed_signatures=changed_signatures,
        changed_defaults=changed_defaults,
        changed_parameter_annotations=changed_parameter_annotations,
        changed_return_annotations=changed_return_annotations,
        changed_docstrings=changed_docstrings,
        deprecated=sorted(deprecated, key=lambda obj: obj.qualname),
        coverage_delta=coverage_delta,
    )


def _coverage_delta(base: ApiPackage | ApiSnapshot, head: ApiPackage | ApiSnapshot) -> dict[str, object]:
    base_count, base_documented, base_object_coverage = _coverage_stats(base)
    head_count, head_documented, head_object_coverage = _coverage_stats(head)
    return {
        "base_public_object_count": base_count,
        "head_public_object_count": head_count,
        "base_documented_object_count": base_documented,
        "head_documented_object_count": head_documented,
        "base_object_coverage": base_object_coverage,
        "head_object_coverage": head_object_coverage,
        "object_coverage_delta": head_object_coverage - base_object_coverage,
    }


def _coverage_stats(source: ApiPackage | ApiSnapshot) -> tuple[int, int, float]:
    if isinstance(source, ApiPackage):
        coverage = check_api_docs(source)
        return (
            coverage.public_object_count,
            coverage.documented_object_count,
            coverage.object_coverage,
        )
    objects = [ApiObject.from_dict(data) for data in source.objects.values()]
    public_object_count = len(objects)
    documented_object_count = sum(1 for obj in objects if obj.documented)
    object_coverage = documented_object_count / public_object_count if public_object_count else 1.0
    return public_object_count, documented_object_count, object_coverage


def _defaults(obj: ApiObject) -> tuple[tuple[str, str | None], ...]:
    return tuple((parameter.name, parameter.default) for parameter in obj.parameters)


def _parameter_annotations(obj: ApiObject) -> tuple[tuple[str, str | None], ...]:
    return tuple((parameter.name, parameter.annotation) for parameter in obj.parameters)


def _return_annotation(obj: ApiObject) -> str | None:
    return obj.returns.annotation if obj.returns else None


def _object_pair_from_dict(data: object) -> tuple[ApiObject, ApiObject]:
    if not isinstance(data, (list, tuple)) or len(data) != 2:
        raise ValueError("Serialized API object pair must contain exactly two objects")
    return ApiObject.from_dict(data[0]), ApiObject.from_dict(data[1])


def _objects_table(objects: list[ApiObject]) -> Table:
    return Table(
        ["Kind", "Name", "Summary"],
        [[obj.kind, obj.qualname, obj.summary_text()] for obj in objects],
        split=True,
    )


def _pairs_table(pairs: list[tuple[ApiObject, ApiObject]], field_name: str) -> Table:
    return Table(
        ["Object", f"Base {field_name}", f"Head {field_name}"],
        [[base.qualname, _field(base, field_name), _field(head, field_name)] for base, head in pairs],
        split=True,
    )


def _format_delta_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.1%}"
    if value is None:
        return ""
    return str(value)


def _field(obj: ApiObject, field_name: str) -> str:
    if field_name == "Signature":
        return obj.signature or ""
    if field_name == "Defaults":
        return ", ".join(f"{name}={default}" for name, default in _defaults(obj) if default is not None)
    if field_name == "Parameter annotations":
        return ", ".join(
            f"{name}: {annotation}" if annotation else name
            for name, annotation in _parameter_annotations(obj)
        )
    if field_name == "Return annotation":
        return _return_annotation(obj) or ""
    return obj.summary_text()


__all__ = [
    "ApiDiffResult",
    "ApiSnapshot",
    "diff_api",
]
