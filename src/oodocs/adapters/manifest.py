"""Adapters for JSON release or reproducibility manifests."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from oodocs.components.blocks import Paragraph, Section
from oodocs.components.inline import inline_code
from oodocs.components.media import Table
from oodocs.core import PathLike
from oodocs.styles import TableStyle


@dataclass(frozen=True, slots=True)
class ReleaseManifestSummary:
    """JSON release or reproducibility manifest summary.

    Attributes:
        source_path: JSON manifest file used as the metadata source.
        data: Parsed JSON manifest payload.

    Examples:
        Add a reproducibility manifest to a release report:

        ```python
        from oodocs import Document
        from oodocs.adapters import ReleaseManifestSummary

        manifest = ReleaseManifestSummary.from_file(
            "artifacts/evidence/reproducibility-manifest.json"
        )
        doc = Document("Build Manifest", manifest.to_section())
        ```
    """

    source_path: Path
    data: object

    @classmethod
    def from_file(cls, path: PathLike) -> ReleaseManifestSummary:
        """Read a JSON release or reproducibility manifest.

        Args:
            path: JSON manifest file to read.

        Returns:
            Parsed manifest summary.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """

        source_path = Path(path)
        return cls(
            source_path=source_path,
            data=json.loads(source_path.read_text(encoding="utf-8")),
        )

    def to_table(self, *, caption: str | None = None) -> Table:
        """Convert manifest data into an OODocs table.

        Args:
            caption: Optional table caption. A manifest-specific caption is
                used when omitted.

        Returns:
            Table preserving the manifest shape where possible.
        """

        if isinstance(self.data, dict):
            return Table.from_mapping(
                self.data,
                caption=caption or f"Manifest values from {self.source_path.name}.",
                style=TableStyle.evidence(),
            )
        if isinstance(self.data, list):
            return Table.from_records(
                self.data,
                caption=caption or f"Manifest rows from {self.source_path.name}.",
                style=TableStyle.evidence(),
            )
        return Table(
            ["Value"],
            [[json.dumps(self.data, ensure_ascii=False)]],
            caption=caption or f"Manifest value from {self.source_path.name}.",
            style=TableStyle.evidence(),
        )

    def to_section(self) -> Section:
        """Convert manifest data into an OODocs section.

        Returns:
            Section containing a source note and manifest table.
        """

        return Section(
            "Reproducibility manifest",
            Paragraph("Read from ", inline_code(self.source_path.as_posix()), "."),
            self.to_table(),
            numbered=False,
            toc=True,
        )


__all__ = ["ReleaseManifestSummary"]
