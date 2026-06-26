"""Shared import diagnostics for Markdown and notebook importers.

Attributes:
    ImportSeverity: Literal severity labels for import diagnostics.
    ImportPolicy: Literal policies for handling lossy imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

from oodocs.components.base import Block
from oodocs.core import OODocsError


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

    def to_dict(self) -> dict[str, object]:
        """Return the issue as a JSON-serializable mapping.

        Returns:
            Dictionary containing severity, code, message, line number, and source.
        """

        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "line_number": self.line_number,
            "source": self.source,
        }


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

        result = parse_markdown("# Title", diagnostics=True)
        if result.warnings():
            print(result.format_text())
        ```

        Reuse imported blocks in a document:

        ```python
        from oodocs import Document, parse_markdown

        result = parse_markdown("# Title", diagnostics=True)
        document = Document("Imported", result.blocks)
        ```

    Notes:
        Importers return this object only when ``diagnostics=True``. Otherwise
        they return plain block lists or documents, depending on the importer.

    See Also:
        ``ImportIssue`` for individual diagnostics, ``ImportPolicyError`` for
        fail-on-lossy policy failures, and ``parse_markdown``/``parse_notebook`` for
        diagnostics-producing importers.
    """

    blocks: tuple[Block, ...]
    issues: tuple[ImportIssue, ...] = ()

    def warnings(self) -> tuple[ImportIssue, ...]:
        """Return warning diagnostics.

        Returns:
            Tuple of issues whose severity is ``"warning"``.
        """

        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def errors(self) -> tuple[ImportIssue, ...]:
        """Return error diagnostics.

        Returns:
            Tuple of issues whose severity is ``"error"``.
        """

        return tuple(issue for issue in self.issues if issue.severity == "error")

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
    diagnostics: bool,
    import_policy: str,
) -> list[Block] | ImportResult:
    """Apply importer diagnostics policy and choose the return shape.

    Args:
        blocks: Imported block objects.
        issues: Diagnostics collected during import.
        diagnostics: Whether to return an ``ImportResult`` instead of blocks.
        import_policy: Import policy controlling lossy conversions.

    Returns:
        A list of blocks when ``diagnostics`` is false, otherwise an
        ``ImportResult`` containing blocks and diagnostics.

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
            diagnostics=True,
            import_policy="record-lossy",
        )
        ```
    """

    normalized_policy = normalize_import_policy(import_policy)
    normalized_blocks = tuple(blocks)
    normalized_issues = tuple(issues)
    if normalized_policy == "fail-on-lossy" and normalized_issues:
        raise ImportPolicyError(normalized_issues)
    if diagnostics:
        return ImportResult(normalized_blocks, normalized_issues)
    return list(normalized_blocks)


__all__ = [
    "ImportIssue",
    "ImportPolicy",
    "ImportPolicyError",
    "ImportResult",
    "ImportSeverity",
    "normalize_import_policy",
    "resolve_import_result",
]
