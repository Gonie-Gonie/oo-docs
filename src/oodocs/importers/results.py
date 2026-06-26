"""Shared import diagnostics for Markdown and notebook importers.

Attributes:
    ImportSeverity: Literal severity labels for import diagnostics.
    ImportPolicy: Literal policies for handling lossy imports.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Literal, Sequence

from oodocs.components.base import Block
from oodocs.components.media import Table
from oodocs.core import OODocsError, PathLike


ImportSeverity = Literal["info", "warning", "error"]
ImportPolicy = Literal["allow-lossy", "record-lossy", "fail-on-lossy"]


@dataclass(frozen=True, slots=True)
class ImportIssue:
    """Issue reported while importing a lossy external source.

    Attributes:
        severity: Diagnostic severity for the issue.
        code: Stable machine-readable issue code.
        message: Human-readable diagnostic message.
        line_number: Optional 1-based source line where the issue occurred.
        source: Optional source label, such as a file path or notebook cell.
        path: Optional filesystem path associated with the imported source.

    Examples:
        ```python
        issue = ImportIssue(
            "warning",
            "raw-html-unsupported",
            "Raw HTML was imported as plain text.",
            line_number=4,
        )
        ```
    """

    severity: ImportSeverity
    code: str
    message: str
    line_number: int | None = None
    source: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the issue as a JSON-serializable mapping.

        Returns:
            Dictionary containing severity, code, message, source, path, and
            line number.
        """

        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "line_number": self.line_number,
            "source": self.source,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ImportIssue:
        """Reconstruct an import issue from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Import issue object.

        Examples:
            ```python
            issue = ImportIssue.from_dict({
                "severity": "warning",
                "code": "raw-html-unsupported",
                "message": "Raw HTML was imported as plain text.",
            })
            ```
        """

        line_number = data.get("line_number")
        return cls(
            severity=str(data["severity"]),  # type: ignore[arg-type]
            code=str(data["code"]),
            message=str(data["message"]),
            line_number=int(line_number) if line_number is not None else None,
            source=_optional_str(data.get("source")),
            path=_optional_str(data.get("path")),
        )


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Imported blocks plus optional diagnostics.

    Attributes:
        blocks: Imported OODocs block objects.
        issues: Diagnostics collected while importing the source.

    Examples:
        Inspect diagnostics returned by an importer:

        ```python
        from oodocs import parse_markdown

        result = parse_markdown("# Title")
        if result.warnings:
            print(result.format_text())
        ```

        Reuse imported blocks in a document:

        ```python
        from oodocs import Document, parse_markdown

        result = parse_markdown("# Title")
        document = Document("Imported", result.blocks)
        ```

    Notes:
        Parser functions return this object. Document factory functions such as
        ``from_markdown`` and ``from_notebook`` return ``Document`` objects.

    See Also:
        ``ImportIssue`` for individual diagnostics, ``ImportPolicyError`` for
        fail-on-lossy policy failures, and ``parse_markdown``/``parse_notebook`` for
        diagnostics-producing importers.
    """

    blocks: tuple[Block, ...]
    issues: tuple[ImportIssue, ...] = ()

    @property
    def errors(self) -> tuple[ImportIssue, ...]:
        """Return error diagnostics.

        Returns:
            Tuple of issues whose severity is ``"error"``.
        """

        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ImportIssue, ...]:
        """Return warning diagnostics.

        Returns:
            Tuple of issues whose severity is ``"warning"``.
        """

        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def infos(self) -> tuple[ImportIssue, ...]:
        """Return informational diagnostics.

        Returns:
            Tuple of issues whose severity is ``"info"``.
        """

        return tuple(issue for issue in self.issues if issue.severity == "info")

    @property
    def ok(self) -> bool:
        """Return whether the import completed without error diagnostics.

        Returns:
            ``True`` when no issue has severity ``"error"``.
        """

        return not self.errors

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable import summary.

        Returns:
            Dictionary containing status counts, imported block count, and
            issue dictionaries. Blocks themselves are not serialized because
            imported OODocs block objects are not a stable JSON format.

        Examples:
            ```python
            from oodocs import parse_markdown

            result = parse_markdown("# Title")
            payload = result.to_dict()
            ```
        """

        return {
            "ok": self.ok,
            "block_count": len(self.blocks),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "infos": len(self.infos),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ImportResult:
        """Reconstruct an import summary from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Import result with deserialized issues and an empty block tuple.

        Examples:
            ```python
            restored = ImportResult.from_dict(saved_import_summary)
            if not restored.ok:
                print(restored.format_text())
            ```
        """

        return cls(
            (),
            tuple(
                ImportIssue.from_dict(issue)
                for issue in data.get("issues", [])  # type: ignore[union-attr]
            ),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize this import summary to JSON.

        Args:
            indent: Indentation passed to ``json.dumps``.

        Returns:
            JSON string for the import summary.
        """

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> ImportResult:
        """Deserialize an import summary from JSON text.

        Args:
            text: JSON text produced by ``to_json``.

        Returns:
            Import result with deserialized issues and no blocks.
        """

        return cls.from_dict(json.loads(text))

    def save_json(self, path: PathLike) -> Path:
        """Write this import summary to a JSON sidecar.

        Args:
            path: Output JSON path.

        Returns:
            Written path.
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_json(indent=2) + "\n", encoding="utf-8")
        return output_path

    @classmethod
    def load_json(cls, path: PathLike) -> ImportResult:
        """Read an import summary JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            Import result with deserialized issues and no blocks.
        """

        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def to_table(self, *, caption: str | None = "Import diagnostics") -> Table:
        """Return import diagnostics as an OODocs table.

        Args:
            caption: Optional table caption.

        Returns:
            Table containing severity, code, source, line number, and message.
        """

        rows = [
            [
                issue.severity,
                issue.code,
                issue.source or issue.path or "",
                "" if issue.line_number is None else str(issue.line_number),
                issue.message,
            ]
            for issue in self.issues
        ]
        return Table(
            ["Severity", "Code", "Source", "Line", "Message"],
            rows,
            caption=caption,
            split=True,
        )

    def format_text(self) -> str:
        """Format diagnostics as human-readable console text.

        Returns:
            Multi-line summary of all import diagnostics.
        """

        if not self.issues:
            return "OODocs import completed with 0 issue(s)."
        lines = [f"OODocs import completed with {len(self.issues)} issue(s):"]
        for issue in self.issues:
            location = (
                f" line {issue.line_number}" if issue.line_number is not None else ""
            )
            source = f" in {issue.source}" if issue.source else ""
            lines.append(
                f"- {issue.severity.upper()} {issue.code}{source}{location}: "
                f"{issue.message}"
            )
        return "\n".join(lines)


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


class ImportPolicyError(OODocsError):
    """Raised when fail-on-lossy import policy rejects a lossy conversion.

    Attributes:
        issues: Diagnostics that caused the fail-on-lossy import to fail.

    Examples:
        ```python
        from oodocs import ImportIssue, ImportPolicyError

        issue = ImportIssue("error", "unsupported-html", "Raw HTML is not supported.")
        raise ImportPolicyError([issue])
        ```
    """

    def __init__(self, issues: Sequence[ImportIssue]) -> None:
        """Initialize the policy error from rejected diagnostics.

        Args:
            issues: Import diagnostics that should block lossy conversion.

        Examples:
            ```python
            error = ImportPolicyError([ImportIssue("error", "unsupported", "Blocked.")])
            ```
        """

        self.issues = tuple(issues)
        super().__init__(ImportResult((), self.issues).format_text())


def normalize_import_policy(value: str) -> ImportPolicy:
    """Normalize and validate an import policy string.

    Args:
        value: User-supplied policy value.

    Returns:
        Normalized import policy literal.

    Raises:
        ValueError: If ``value`` is not one of ``"allow-lossy"``,
            ``"record-lossy"``, or ``"fail-on-lossy"``.

    Examples:
        ```python
        normalize_import_policy(" FAIL-ON-LOSSY ")
        # "fail-on-lossy"
        ```
    """

    normalized = value.strip().lower()
    valid_policies = {"allow-lossy", "record-lossy", "fail-on-lossy"}
    if normalized not in valid_policies:
        raise ValueError(
            "import_policy must be 'allow-lossy', 'record-lossy', or 'fail-on-lossy'"
        )
    return normalized  # type: ignore[return-value]


def resolve_import_result(
    blocks: Iterable[Block],
    issues: Iterable[ImportIssue],
    *,
    import_policy: str,
) -> ImportResult:
    """Apply importer diagnostics policy and return imported blocks with issues.

    Args:
        blocks: Imported block objects.
        issues: Diagnostics collected during import.
        import_policy: Import policy controlling lossy conversions.

    Returns:
        Import result containing imported blocks and diagnostics.

    Raises:
        ImportPolicyError: If ``import_policy`` is ``"fail-on-lossy"`` and any
            issue was collected.
        ValueError: If ``import_policy`` is not supported.

    Examples:
        ```python
        from oodocs import Paragraph

        result = resolve_import_result(
            [Paragraph("Imported")],
            [],
            import_policy="record-lossy",
        )
        ```
    """

    normalized_policy = normalize_import_policy(import_policy)
    normalized_blocks = tuple(blocks)
    normalized_issues = tuple(issues)
    if normalized_policy == "fail-on-lossy" and normalized_issues:
        raise ImportPolicyError(normalized_issues)
    return ImportResult(normalized_blocks, normalized_issues)


__all__ = [
    "ImportIssue",
    "ImportPolicy",
    "ImportPolicyError",
    "ImportResult",
    "ImportSeverity",
    "normalize_import_policy",
    "resolve_import_result",
]
