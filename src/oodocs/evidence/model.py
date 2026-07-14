"""Generic evidence report models."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
from typing import Literal, TYPE_CHECKING

from oodocs.components.blocks import Chapter, Paragraph, Section
from oodocs.document import Document
from oodocs.evidence.render import render_evidence_item
from oodocs.settings import DocumentMetadata, DocumentSettings, TitleMatter
from oodocs.styles import Theme
from oodocs.workflows import OutputBundle

if TYPE_CHECKING:
    from collections.abc import Sequence


EvidenceKind = Literal["auto", "csv", "json", "text", "checksums"]
MissingInputPolicy = Literal["error", "warn"]


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One caller-selected evidence source."""

    path: Path
    title: str | None = None
    kind: EvidenceKind = "auto"
    required: bool = True
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        if self.kind not in {"auto", "csv", "json", "text", "checksums"}:
            raise ValueError(
                "EvidenceItem.kind must be auto, csv, json, text, or checksums"
            )

    def resolved_kind(self) -> EvidenceKind:
        """Return the explicit kind or an extension-based kind."""

        if self.kind != "auto":
            return self.kind
        suffix = self.path.suffix.casefold()
        if suffix == ".csv":
            return "csv"
        if suffix == ".json":
            return "json"
        if suffix in {".sha256", ".sha512"} or "checksum" in self.path.name.casefold():
            return "checksums"
        return "text"


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Files written for a generic evidence report."""

    output_dir: Path
    outputs: OutputBundle
    included_source_files: tuple[Path, ...]
    checksum_file: Path


@dataclass(slots=True)
class EvidenceReport:
    """A caller-configured collection of evidence items."""

    title: str
    items: tuple[EvidenceItem, ...]
    metadata: DocumentMetadata | None = None
    title_matter: TitleMatter | None = None
    theme: Theme | None = None

    def __post_init__(self) -> None:
        self.items = tuple(
            item if isinstance(item, EvidenceItem) else EvidenceItem(Path(item))
            for item in self.items
        )

    def to_document(
        self,
        *,
        missing_input_policy: MissingInputPolicy = "error",
    ) -> Document:
        """Convert existing evidence inputs to a generic document."""

        policy = _normalize_missing_policy(missing_input_policy)
        sections: list[Section] = []
        missing: list[EvidenceItem] = []
        for item in self.items:
            if item.path.exists():
                sections.append(render_evidence_item(item))
            elif item.required:
                missing.append(item)
            elif policy == "warn":
                sections.append(_missing_item_section(item))

        if missing and policy == "error":
            names = ", ".join(item.path.as_posix() for item in missing)
            raise FileNotFoundError(f"Missing required evidence item(s): {names}")
        if missing:
            sections[:0] = [_missing_item_section(item) for item in missing]

        body: list[object] = []
        if sections:
            body.append(Chapter("Evidence", sections))
        else:
            body.append(Paragraph("No evidence items were supplied."))
        return Document(
            self.title,
            body,
            settings=DocumentSettings(
                metadata=self.metadata,
                title_matter=self.title_matter,
                theme=self.theme,
            ),
        )

    def save_bundle(
        self,
        output_dir: str | Path,
        *,
        stem: str,
        formats: Sequence[str] = ("docx", "pdf", "html"),
        missing_input_policy: MissingInputPolicy = "error",
        validate: bool = True,
    ) -> EvidenceBundle:
        """Copy explicit inputs, render outputs, and write their checksums."""

        if not stem or Path(stem).name != stem:
            raise ValueError("stem must be a non-empty filename stem")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        document = self.to_document(missing_input_policy=missing_input_policy)
        outputs = document.save_all(
            output_path,
            stem=stem,
            formats=formats,
            validate=validate,
        )
        included = _copy_explicit_sources(self.items, output_path)
        checksum_file = _write_checksums(output_path, (*included, *outputs.paths))
        return EvidenceBundle(
            output_dir=output_path,
            outputs=outputs,
            included_source_files=included,
            checksum_file=checksum_file,
        )


def _normalize_missing_policy(value: str) -> MissingInputPolicy:
    if value not in {"error", "warn"}:
        raise ValueError("missing_input_policy must be 'error' or 'warn'")
    return value  # type: ignore[return-value]


def _missing_item_section(item: EvidenceItem) -> Section:
    title = item.title or item.path.stem.replace("-", " ").replace("_", " ").title()
    return Section(
        title or "Missing evidence item",
        Paragraph(f"Evidence item is missing: {item.path.name}"),
        numbered=False,
        toc=True,
    )


def _copy_explicit_sources(
    items: tuple[EvidenceItem, ...],
    output_dir: Path,
) -> tuple[Path, ...]:
    existing = [item.path for item in items if item.path.is_file()]
    if not existing:
        return ()
    source_dir = output_dir / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    included: list[Path] = []
    names: set[str] = set()
    for source in existing:
        if source.name in names:
            raise ValueError(f"Evidence item filenames must be unique: {source.name}")
        names.add(source.name)
        destination = source_dir / source.name
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        included.append(destination)
    return tuple(included)


def _write_checksums(output_dir: Path, paths: tuple[Path, ...]) -> Path:
    checksum_path = output_dir / "checksums.sha256"
    rows: list[str] = []
    for path in sorted(paths, key=lambda value: value.as_posix()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            display_name = path.resolve().relative_to(output_dir.resolve()).as_posix()
        except ValueError:
            display_name = path.name
        rows.append(f"{digest}  {display_name}")
    checksum_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return checksum_path


__all__ = ["EvidenceBundle", "EvidenceItem", "EvidenceReport"]
