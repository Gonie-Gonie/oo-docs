"""Document validation helpers for authoring-time checks.

Attributes:
    ValidationSeverity: Literal severity labels emitted by document validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from textwrap import wrap
from typing import Iterable, Literal, Protocol, Sequence, TYPE_CHECKING

from oodocs.compatibility import (
    OUTPUT_FORMATS,
    OutputFormat,
    compatibility_note,
    format_output_formats,
    normalize_output_formats,
)
from oodocs.components.base import Block
from oodocs.components.blocks import (
    Appendix,
    Box,
    BulletList,
    CodeBlock,
    ColumnSpan,
    CountableBlock,
    Divider,
    Equation,
    MultiColumn,
    NumberedList,
    PageBreak,
    Paragraph,
    Part,
    Section,
    VerticalSpace,
)
from oodocs.components.generated import (
    ListOfComments,
    ListOfGlossaryTerms,
    ListOfAlgorithms,
    ListOfFigures,
    ListOfFootnotes,
    ListOfReferences,
    ListOfTables,
    TableOfContents,
)
from oodocs.components.inline import (
    BlockReference,
    Citation,
    Comment,
    Footnote,
    Hyperlink,
    InlineChip,
    MarginNote,
    ReferenceGroup,
    Text,
)
from oodocs.components.equations import unsupported_latex_commands
from oodocs.components.media import Figure, ImageData, PdfPages, SubFigure, SubFigureGroup, SubTable, SubTableGroup, Table
from oodocs.components.positioning import ImageBox, Shape, TextBox
from oodocs.components.references import CitationSource
from oodocs.core import OODocsError, PathLike, length_to_inches

if TYPE_CHECKING:
    from oodocs.document import Document
    from oodocs.layout.indexing import RenderIndex


ValidationSeverity = Literal["error", "warning"]
_URL_SOFT_BREAK = "\u200b"
_LONG_URL_TARGET_LENGTH = 96
_LONG_URL_UNBROKEN_SEGMENT_LENGTH = 64
_EXTERNAL_URL_PREFIXES = ("http://", "https://", "ftp://", "mailto:")


class ResultLike(Protocol):
    """Protocol for serializable result objects.

    Result objects expose status partitions, structured serialization,
    JSON sidecars, OODocs table conversion, and console text formatting.

    Examples:
        ```python
        from oodocs import ResultLike

        def print_summary(result: ResultLike) -> None:
            print(result.format_text())
        ```
    """

    @property
    def ok(self) -> bool:
        """Return whether the result has no error-level entries."""

    @property
    def errors(self) -> tuple[object, ...]:
        """Return error-level entries."""

    @property
    def warnings(self) -> tuple[object, ...]:
        """Return warning-level entries."""

    @property
    def infos(self) -> tuple[object, ...]:
        """Return informational entries."""

    def to_dict(self, *args: object, **kwargs: object) -> dict[str, object]:
        """Return a JSON-serializable mapping.

        Args:
            *args: Positional serialization options accepted by the concrete
                result type.
            **kwargs: Keyword serialization options accepted by the concrete
                result type.

        Returns:
            JSON-serializable result payload.
        """

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ResultLike:
        """Reconstruct a result from a JSON-serializable mapping.

        Args:
            data: Payload previously returned by ``to_dict``.

        Returns:
            Reconstructed result object.
        """

    def to_json(self, *args: object, **kwargs: object) -> str:
        """Serialize this result to JSON text.

        Args:
            *args: Positional serialization options accepted by the concrete
                result type.
            **kwargs: Keyword serialization options accepted by the concrete
                result type.

        Returns:
            JSON text for this result.
        """

    @classmethod
    def from_json(cls, text: str) -> ResultLike:
        """Deserialize a result from JSON text.

        Args:
            text: JSON text previously returned by ``to_json``.

        Returns:
            Reconstructed result object.
        """

    def save_json(self, path: PathLike, *args: object, **kwargs: object) -> Path:
        """Write this result to a JSON sidecar.

        Args:
            path: Output JSON sidecar path.
            *args: Positional serialization options accepted by the concrete
                result type.
            **kwargs: Keyword serialization options accepted by the concrete
                result type.

        Returns:
            Path that was written.
        """

    @classmethod
    def load_json(cls, path: PathLike) -> ResultLike:
        """Read a result from a JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            Reconstructed result object.
        """

    def to_table(self, *args: object, **kwargs: object) -> Table:
        """Return this result as an OODocs table.

        Args:
            *args: Positional table options accepted by the concrete result
                type.
            **kwargs: Keyword table options accepted by the concrete result
                type.

        Returns:
            OODocs table representation of this result.
        """

    def format_text(self, *args: object, **kwargs: object) -> str:
        """Format this result as human-readable console text.

        Args:
            *args: Positional formatting options accepted by the concrete
                result type.
            **kwargs: Keyword formatting options accepted by the concrete
                result type.

        Returns:
            Human-readable summary text.
        """


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    """Policy that decides which validation warnings block release gates.

    Attributes:
        allow_warnings: Warning codes accepted by the gate.
        deny_warnings: Warning codes that always block the gate.
        fail_on_unlisted_warnings: Whether warnings outside the allow list
            should block.

    Examples:
        ```python
        from oodocs.validation import ValidationPolicy

        policy = ValidationPolicy(
            allow_warnings={"html-toc-page-numbers"},
            deny_warnings={"wide-table"},
            fail_on_unlisted_warnings=True,
        )
        ```
    """

    allow_warnings: frozenset[str] = frozenset()
    deny_warnings: frozenset[str] = frozenset()
    fail_on_unlisted_warnings: bool = False

    def __post_init__(self) -> None:
        allow = _normalize_warning_codes(self.allow_warnings)
        deny = _normalize_warning_codes(self.deny_warnings)
        overlap = allow & deny
        if overlap:
            raise ValueError(
                "warning codes cannot be both allowed and denied: "
                + ", ".join(sorted(overlap))
            )
        object.__setattr__(self, "allow_warnings", frozenset(allow))
        object.__setattr__(self, "deny_warnings", frozenset(deny))
        object.__setattr__(
            self,
            "fail_on_unlisted_warnings",
            bool(self.fail_on_unlisted_warnings),
        )

    def blocks(self, issue: ValidationIssue) -> bool:
        """Return whether this policy blocks a warning issue."""

        if issue.severity != "warning":
            return False
        if issue.code in self.deny_warnings:
            return True
        if issue.code in self.allow_warnings:
            return False
        return self.fail_on_unlisted_warnings

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable policy mapping."""

        return {
            "allow_warnings": sorted(self.allow_warnings),
            "deny_warnings": sorted(self.deny_warnings),
            "fail_on_unlisted_warnings": self.fail_on_unlisted_warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ValidationPolicy:
        """Reconstruct a validation policy from serialized data."""

        return cls(
            allow_warnings=frozenset(_object_string_list(data.get("allow_warnings"))),
            deny_warnings=frozenset(_object_string_list(data.get("deny_warnings"))),
            fail_on_unlisted_warnings=bool(
                data.get("fail_on_unlisted_warnings", False)
            ),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize this policy to JSON text."""

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> ValidationPolicy:
        """Deserialize a validation policy from JSON text."""

        return cls.from_dict(json.loads(text))

    def save_json(self, path: PathLike, *, indent: int | None = 2) -> Path:
        """Write this policy to a JSON sidecar."""

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_json(indent=indent) + "\n", encoding="utf-8")
        return output_path

    @classmethod
    def load_json(cls, path: PathLike) -> ValidationPolicy:
        """Read a validation policy JSON sidecar."""

        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One authoring issue found in a document tree.

    Attributes:
        severity: Issue severity, either ``"error"`` or ``"warning"``.
        code: Stable machine-readable issue code.
        message: Human-readable explanation.
        source: Optional source label, such as a source file or adapter name.
        path: Dotted path to the document node that triggered the issue.
        line_number: Optional 1-based source line when the issue can be tied
            back to an imported source.
        formats: Output formats affected by this issue.

    Examples:
        ```python
        from oodocs.validation import ValidationIssue

        issue = ValidationIssue(
            "warning",
            "custom-warning",
            "Something should be reviewed.",
            path="document.body.children[0]",
            formats=("html",),
        )
        assert issue.applies_to(("html",))
        ```
    """

    severity: ValidationSeverity
    code: str
    message: str
    source: str | None = None
    path: str = "document"
    line_number: int | None = None
    formats: tuple[OutputFormat, ...] = OUTPUT_FORMATS

    def applies_to(self, formats: Iterable[str] | None = None) -> bool:
        """Return whether this issue applies to any requested format.

        Args:
            formats: Output formats to test. Defaults to all supported formats.

        Returns:
            ``True`` when this issue affects at least one requested format.
        """

        requested_formats = normalize_output_formats(formats)
        return bool(set(self.formats) & set(requested_formats))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of this issue.

        Returns:
            Dictionary containing severity, code, message, source, path, line
            number, and formats.
        """

        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "source": self.source,
            "path": self.path,
            "line_number": self.line_number,
            "formats": list(self.formats),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ValidationIssue:
        """Reconstruct a validation issue from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Validation issue object.
        """

        return cls(
            severity=str(data["severity"]),  # type: ignore[arg-type]
            code=str(data["code"]),
            message=str(data["message"]),
            source=_optional_str(data.get("source")),
            path=str(data.get("path", "document")),
            line_number=_optional_int(data.get("line_number")),
            formats=normalize_output_formats(data.get("formats")),  # type: ignore[arg-type]
        )

    def as_issue_row(self) -> list[object]:
        """Return this issue as a table row.

        Returns:
            ``[severity, formats, code, source, path, line_number, message]``.
        """

        return [
            self.severity,
            format_output_formats(self.formats),
            self.code,
            self.source or "",
            self.path,
            "" if self.line_number is None else str(self.line_number),
            self.message,
        ]

    def __str__(self) -> str:
        location = self.path
        if self.line_number is not None:
            location = f"{location}:{self.line_number}"
        source = f" in {self.source}" if self.source else ""
        return (
            f"{self.severity.upper()} {self.code} "
            f"[{format_output_formats(self.formats)}]{source} at {location}: "
            f"{self.message}"
        )


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validation issues plus display and filtering helpers.

    Attributes:
        issues: Validation issues in discovery order.

    Examples:
        Check whether a document can be rendered:

        ```python
        result = doc.validate(formats=("docx", "pdf"))
        if not result.ok:
            print(result.to_json(formats=("pdf",)))
        ```

        Filter warnings for a specific output format:

        ```python
        pdf_warnings = result.warnings_for(("pdf",))
        for issue in pdf_warnings:
            print(issue.message)
        ```

    Notes:
        ``ok`` only reflects error-level issues. Warnings remain available for
        display and format-specific filtering even when validation passes.

    See Also:
        ``Document.validate`` for producing validation results and
        ``DocumentValidationError`` for raising on error-level issues.
    """

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        """Return all error-level issues.

        Returns:
            Issues whose severity is ``"error"``.
        """

        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        """Return all warning-level issues.

        Returns:
            Issues whose severity is ``"warning"``.
        """

        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def infos(self) -> tuple[ValidationIssue, ...]:
        """Return informational issues.

        Returns:
            Empty tuple. Validation currently reports only errors and warnings.
        """

        return ()

    @property
    def ok(self) -> bool:
        """Return whether the result has no errors.

        Returns:
            ``True`` when no error-level issues exist.
        """

        return not self.errors

    def errors_for(
        self,
        formats: Iterable[str] | None = None,
    ) -> tuple[ValidationIssue, ...]:
        """Return error-level issues that affect requested formats.

        Args:
            formats: Output formats to filter for. Defaults to all formats.

        Returns:
            Matching error-level issues.
        """

        requested_formats = set(normalize_output_formats(formats))
        return tuple(
            issue
            for issue in self.errors
            if _issue_matches_formats(issue, requested_formats)
        )

    def warnings_for(
        self,
        formats: Iterable[str] | None = None,
    ) -> tuple[ValidationIssue, ...]:
        """Return warning-level issues that affect requested formats.

        Args:
            formats: Output formats to filter for. Defaults to all formats.

        Returns:
            Matching warning-level issues.
        """

        requested_formats = set(normalize_output_formats(formats))
        return tuple(
            issue
            for issue in self.warnings
            if _issue_matches_formats(issue, requested_formats)
        )

    def blocking_warnings(
        self,
        policy: ValidationPolicy,
        *,
        formats: Iterable[str] | None = None,
    ) -> tuple[ValidationIssue, ...]:
        """Return warning-level issues that block under a policy.

        Args:
            policy: Warning gate policy.
            formats: Output formats to filter for. Defaults to all formats.

        Returns:
            Warning issues that should block a release or CI gate.
        """

        return tuple(
            issue
            for issue in self.warnings_for(formats)
            if policy.blocks(issue)
        )

    def issues_for(
        self,
        formats: Iterable[str] | None = None,
    ) -> tuple[ValidationIssue, ...]:
        """Return issues that affect requested formats.

        Args:
            formats: Output formats to filter for. Defaults to all formats.

        Returns:
            Matching issues in discovery order.
        """

        requested_formats = set(normalize_output_formats(formats))
        return tuple(
            issue
            for issue in self.issues
            if _issue_matches_formats(issue, requested_formats)
        )

    def ok_for(self, formats: Iterable[str] | None = None) -> bool:
        """Return whether requested formats have no errors.

        Args:
            formats: Output formats to filter for. Defaults to all formats.

        Returns:
            ``True`` when no matching errors exist.
        """

        return not self.errors_for(formats)

    def for_formats(self, formats: Iterable[str] | None = None) -> ValidationResult:
        """Return a new result filtered to requested formats.

        Args:
            formats: Output formats to filter for. Defaults to all formats.

        Returns:
            A validation result containing only matching issues.
        """

        return ValidationResult(self.issues_for(formats))

    def to_dict(
        self,
        *,
        formats: Iterable[str] | None = None,
        policy: ValidationPolicy | None = None,
    ) -> dict[str, object]:
        """Return a JSON-serializable validation summary.

        Args:
            formats: Output formats to include. Defaults to all formats.
            policy: Optional warning policy used to report blocking warnings.

        Returns:
            Dictionary with status counts and issue dictionaries.
        """

        result = self.for_formats(formats)
        payload: dict[str, object] = {
            "ok": result.ok,
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "infos": len(result.infos),
            "issues": [issue.to_dict() for issue in result.issues],
        }
        if policy is not None:
            blocking = result.blocking_warnings(policy)
            payload["blocking_warnings"] = len(blocking)
            payload["warning_policy"] = policy.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ValidationResult:
        """Reconstruct a validation result from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Validation result object.
        """

        return cls(
            tuple(
                ValidationIssue.from_dict(issue)
                for issue in data.get("issues", [])  # type: ignore[union-attr]
            )
        )

    def to_json(
        self,
        *,
        formats: Iterable[str] | None = None,
        policy: ValidationPolicy | None = None,
        indent: int | None = 2,
    ) -> str:
        """Serialize this validation summary to JSON.

        Args:
            formats: Output formats to include. Defaults to all formats.
            policy: Optional warning policy used to report blocking warnings.
            indent: Indentation passed to ``json.dumps``.

        Returns:
            JSON string for the validation summary.
        """

        return json.dumps(
            self.to_dict(formats=formats, policy=policy),
            ensure_ascii=False,
            indent=indent,
        )

    @classmethod
    def from_json(cls, text: str) -> ValidationResult:
        """Deserialize a validation result from JSON text.

        Args:
            text: JSON text produced by ``to_json``.

        Returns:
            Validation result object.
        """

        return cls.from_dict(json.loads(text))

    def save_json(
        self,
        path: PathLike,
        *,
        formats: Iterable[str] | None = None,
        policy: ValidationPolicy | None = None,
        indent: int | None = 2,
    ) -> Path:
        """Write this validation result to a JSON sidecar.

        Args:
            path: Output JSON path.
            formats: Output formats to include. Defaults to all formats.
            policy: Optional warning policy used to report blocking warnings.
            indent: Indentation passed to ``json.dumps``.

        Returns:
            Written path.
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.to_json(formats=formats, policy=policy, indent=indent) + "\n",
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def load_json(cls, path: PathLike) -> ValidationResult:
        """Read a validation result JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            Validation result object.
        """

        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def to_table(
        self,
        *,
        formats: Iterable[str] | None = None,
        caption: str | None = "Validation issues",
    ) -> Table:
        """Return validation issues as an OODocs table.

        Args:
            formats: Output formats to include. Defaults to all formats.
            caption: Optional table caption.

        Returns:
            Table containing severity, formats, code, source, path, line number,
            and message.
        """

        rows = [issue.as_issue_row() for issue in self.issues_for(formats)]
        return Table(
            ["Severity", "Formats", "Code", "Source", "Path", "Line", "Message"],
            rows,
            caption=caption,
            split=True,
        )

    def format_text(
        self,
        *,
        formats: Iterable[str] | None = None,
        policy: ValidationPolicy | None = None,
    ) -> str:
        """Format validation issues as human-readable console text.

        Args:
            formats: Output formats to include. Defaults to all formats.
            policy: Optional warning policy used to mark blocking warnings.

        Returns:
            A human-readable text table, or a single status line when no
            issues match.
        """

        issues = self.issues_for(formats)
        errors = tuple(issue for issue in issues if issue.severity == "error")
        warnings = tuple(issue for issue in issues if issue.severity == "warning")
        blocking = (
            tuple(issue for issue in warnings if policy.blocks(issue))
            if policy is not None
            else ()
        )
        scope = format_output_formats(normalize_output_formats(formats))
        status = "ok" if not errors and not blocking else "failed"
        heading = (
            f"OODocs validation {status} for {scope}: "
            f"{len(errors)} error(s), {len(warnings)} warning(s)"
        )
        if policy is not None:
            heading += f", {len(blocking)} blocking warning(s)"
        if not issues:
            return heading

        blocking_ids = {id(issue) for issue in blocking}
        rows = [
            (
                "BLOCKING WARNING"
                if id(issue) in blocking_ids
                else str(issue.severity).upper(),
                format_output_formats(issue.formats),
                issue.code,
                issue.source or "",
                issue.path,
                "" if issue.line_number is None else str(issue.line_number),
                issue.message,
            )
            for issue in issues
        ]
        return "\n".join([heading, _format_issue_table(rows)])

    def __str__(self) -> str:
        return self.format_text()


class DocumentValidationError(OODocsError):
    """Raised when document validation blocks rendering.

    Args:
        result: Validation result or raw validation issues.
        formats: Output formats whose errors should block rendering.

    Examples:
        ```python
        from oodocs.validation import DocumentValidationError

        try:
            doc.validate(raise_on_error=True, formats=("pdf",))
        except DocumentValidationError as exc:
            print(exc.errors)
        ```
    """

    result: ValidationResult

    def __init__(
        self,
        result: ValidationResult | Sequence[ValidationIssue],
        *,
        formats: Iterable[str] | None = None,
        policy: ValidationPolicy | None = None,
    ) -> None:
        self.result = (
            result
            if isinstance(result, ValidationResult)
            else ValidationResult(tuple(result))
        )
        self.formats = normalize_output_formats(formats)
        self.policy = policy
        super().__init__(self.result.format_text(formats=self.formats, policy=policy))

    @property
    def issues(self) -> tuple[ValidationIssue, ...]:
        """Return issues associated with the blocked formats.

        Returns:
            Issues matching the formats that were validated for this error.
        """

        return self.result.issues_for(self.formats)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        """Return error-level issues associated with the blocked formats.

        Returns:
            Error-level issues matching the blocked formats.
        """

        return self.result.errors_for(self.formats)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        """Return warning-level issues associated with the blocked formats.

        Returns:
            Warning-level issues matching the blocked formats.
        """

        return self.result.warnings_for(self.formats)

    @property
    def blocking_warnings(self) -> tuple[ValidationIssue, ...]:
        """Return policy-blocked warnings associated with the blocked formats."""

        if self.policy is None:
            return ()
        return self.result.blocking_warnings(self.policy, formats=self.formats)


def validate_document(
    document: Document,
    *,
    raise_on_error: bool = False,
    formats: Iterable[str] | None = None,
    policy: ValidationPolicy | None = None,
) -> ValidationResult:
    """Validate a document tree.

    Args:
        document: Document to validate.
        raise_on_error: Whether to raise when blocking errors are present.
        formats: Output formats to validate for. Defaults to all formats.
        policy: Optional warning policy that can make warnings blocking when
            ``raise_on_error`` is true.

    Returns:
        A structured validation result.

    Raises:
        DocumentValidationError: If ``raise_on_error`` is true and the document
            has blocking errors for the requested formats.

    Examples:
        ```python
        from oodocs.validation import validate_document

        result = validate_document(doc, formats=("html",))
        print(result.format_text())
        ```
    """

    result = ValidationResult(tuple(_ValidationContext(document).validate()))
    if raise_on_error and (
        not result.ok_for(formats)
        or (policy is not None and result.blocking_warnings(policy, formats=formats))
    ):
        raise DocumentValidationError(result, formats=formats, policy=policy)
    return result


class _ValidationContext:
    def __init__(self, document: Document) -> None:
        self.document = document
        self.issues: list[ValidationIssue] = []
        self.block_paths: dict[int, str] = {}
        self.referenceable_paths: dict[int, str] = {}
        self.references: list[tuple[BlockReference, str]] = []
        self.reference_groups: list[tuple[ReferenceGroup, str]] = []
        self.citations: list[tuple[Citation, str]] = []
        self.hyperlinks: list[tuple[Hyperlink, str]] = []
        self.generated_content: list[tuple[object, str]] = []

    def validate(self) -> list[ValidationIssue]:
        """Collect validation issues for the configured document."""

        if not str(self.document.title).strip():
            self._add(
                "error",
                "blank-document-title",
                "Document title must not be empty.",
                "document.title",
            )

        self._collect_blocks(self.document.body.children, "document.body", parent_level=None)
        for index, item in enumerate(self.document.settings.overlays):
            self._collect_positioned_item(
                item,
                f"document.settings.overlays[{index}]",
            )
            if item.scope.kind != "all":
                self._add_compatibility_warning(
                    "page-item-scope-static-output",
                    f"document.settings.overlays[{index}].scope",
                )

        self._validate_citations()
        # Build the render index only after structural checks pass; downstream
        # reference and generated-page validation depends on stable numbering.
        render_index = self._build_render_index_if_possible()
        self._validate_references(render_index)
        self._validate_hyperlinks(render_index)
        if render_index is not None:
            self._validate_footnote_compatibility(render_index)
            self._validate_generated_content(render_index)
        return self.issues

    def _add(
        self,
        severity: ValidationSeverity,
        code: str,
        message: str,
        path: str,
        *,
        formats: Iterable[str] | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                severity=severity,
                code=code,
                message=message,
                path=path,
                formats=normalize_output_formats(formats),
            )
        )

    def _collect_blocks(
        self,
        blocks: Sequence[Block],
        path: str,
        *,
        parent_level: int | None,
    ) -> None:
        for index, block in enumerate(blocks):
            self._collect_block(
                block,
                f"{path}.children[{index}]",
                parent_level=parent_level,
            )

    def _collect_block(
        self,
        block: Block,
        path: str,
        *,
        parent_level: int | None,
    ) -> None:
        self._register_block(block, path)

        if isinstance(block, Paragraph):
            self._register_referenceable(block, path)
            self._validate_style_reference("paragraph", block.style, f"{path}.style")
            self._scan_inlines(block.content, f"{path}.content")
            return

        if isinstance(block, (BulletList, NumberedList)):
            self._validate_style_reference("list", block.style, f"{path}.style")
            if len(block.item_children) != len(block.items):
                self._add(
                    "error",
                    "list-children-mismatch",
                    "List item_children must match the number of list items.",
                    path,
                )
            for item_index, item in enumerate(block.items):
                item_path = f"{path}.items[{item_index}]"
                self._register_referenceable(item, item_path)
                self._validate_style_reference("paragraph", item.style, f"{item_path}.style")
                self._scan_inlines(item.content, f"{item_path}.content")
                child_lists = (
                    block.item_children[item_index]
                    if item_index < len(block.item_children)
                    else []
                )
                self._collect_blocks(
                    child_lists,
                    item_path,
                    parent_level=parent_level,
                )
            return

        if isinstance(block, (CodeBlock, Equation, Box)):
            self._register_referenceable(block, path)
            if isinstance(block, Box):
                self._validate_style_reference("box", block.style, f"{path}.style")
                self._validate_box_renderer_features(block, path)
            else:
                self._validate_style_reference("paragraph", block.style, f"{path}.style")
            if isinstance(block, Equation):
                self._validate_equation(block, path)
            if isinstance(block, Box):
                if block.title is not None:
                    self._scan_inlines(block.title, f"{path}.title")
                if block.icon is not None:
                    self._scan_inlines(block.icon, f"{path}.icon")
                self._collect_blocks(
                    block.children,
                    path,
                    parent_level=parent_level,
                )
            if isinstance(block, CodeBlock):
                if block.caption is not None:
                    self._scan_inlines(block.caption.content, f"{path}.caption")
                if block.identifier is not None and not block.identifier.strip():
                    self._add(
                        "error",
                        "blank-code-block-identifier",
                        "CodeBlock identifier must not be empty.",
                        f"{path}.identifier",
                    )
                if block.highlight_lines and max(block.highlight_lines) > len(block.normalized_lines()):
                    self._add(
                        "warning",
                        "missing-code-highlight-line",
                        "CodeBlock highlight_lines includes a line beyond the source length.",
                        f"{path}.highlight_lines",
                    )
            return

        if isinstance(block, CountableBlock):
            self._register_referenceable(block, path)
            if not str(block.kind).strip():
                self._add(
                    "error",
                    "blank-countable-kind",
                    "CountableBlock kind must not be empty.",
                    f"{path}.kind",
                )
            if block.numbered and not str(block.counter or "").strip():
                self._add(
                    "error",
                    "blank-countable-counter",
                    "Numbered CountableBlock objects require a non-empty counter.",
                    f"{path}.counter",
                )
            if block.title is not None:
                self._scan_inlines(block.title, f"{path}.title")
            if block.box_style is not None:
                self._validate_style_reference("box", block.box_style, f"{path}.box_style")
                self._validate_box_style_shadow(block.box_style, f"{path}.box_style")
            self._collect_blocks(
                block.children,
                path,
                parent_level=parent_level,
            )
            return

        if isinstance(block, (ColumnSpan, MultiColumn)):
            self._collect_blocks(
                block.children,
                path,
                parent_level=parent_level,
            )
            return

        if isinstance(block, Appendix):
            self._register_referenceable(block, path)
            if parent_level is not None:
                self._add(
                    "warning",
                    "nested-appendix",
                    "Appendix containers are intended for top-level document appendices.",
                    path,
                )
            self._validate_title(block.title, f"{path}.title", "Appendix title must not be empty.")
            self._scan_inlines(block.title, f"{path}.title")
            self._collect_blocks(
                block.children,
                path,
                parent_level=block.level,
            )
            return

        if isinstance(block, Part):
            self._register_referenceable(block, path)
            self._validate_title(block.title, f"{path}.title", "Part title must not be empty.")
            self._scan_inlines(block.title, f"{path}.title")
            self._collect_blocks(
                block.children,
                path,
                parent_level=block.level,
            )
            return

        if isinstance(block, Section):
            self._register_referenceable(block, path)
            self._validate_title(block.title, f"{path}.title", "Section title must not be empty.")
            self._scan_inlines(block.title, f"{path}.title")
            self._validate_heading_level(block, path, parent_level)
            if block.page_layout is not None:
                self._add_compatibility_warning(
                    "section-page-layout-html-degrade",
                    f"{path}.page_layout",
                )
            self._collect_blocks(
                block.children,
                path,
                parent_level=block.level,
            )
            return

        if isinstance(
            block,
            (
                ListOfTables,
                ListOfFigures,
                ListOfAlgorithms,
                ListOfGlossaryTerms,
                ListOfReferences,
                ListOfComments,
                ListOfFootnotes,
                TableOfContents,
            ),
        ):
            self.generated_content.append((block, path))
            if block.title is not None:
                self._scan_inlines(block.title, f"{path}.title")
            return

        if isinstance(block, Table):
            self._register_referenceable(block, path)
            self._validate_style_reference("table", block.style, f"{path}.style")
            self._validate_table(block, path)
            return

        if isinstance(block, PdfPages):
            self._validate_pdf_pages(block, path)
            return

        if isinstance(block, Figure):
            self._register_referenceable(block, path)
            self._validate_figure(block, path)
            return

        if isinstance(block, SubFigureGroup):
            self._register_referenceable(block, path)
            self._validate_subfigure_group(block, path)
            return

        if isinstance(block, SubTableGroup):
            self._register_referenceable(block, path)
            self._validate_subtable_group(block, path)
            return

        if isinstance(block, (TextBox, Shape, ImageBox)):
            self._collect_positioned_item(block, path)
            return

        if isinstance(block, (Divider, PageBreak, VerticalSpace)):
            return

        self._add(
            "error",
            "unsupported-block",
            f"Unsupported block object: {type(block)!r}.",
            path,
        )

    def _register_block(self, block: Block, path: str) -> None:
        block_id = id(block)
        existing_path = self.block_paths.get(block_id)
        if existing_path is not None:
            self._add(
                "error",
                "duplicate-block-instance",
                f"The same {type(block).__name__} object is inserted more than once "
                f"({existing_path} and {path}). Create a separate object for each location.",
                path,
            )
            return
        self.block_paths[block_id] = path

    def _register_referenceable(self, target: object, path: str) -> None:
        target_id = id(target)
        existing_path = self.referenceable_paths.get(target_id)
        if existing_path is not None and existing_path != path:
            self._add(
                "error",
                "duplicate-reference-target",
                f"The same {type(target).__name__} object is present at both "
                f"{existing_path} and {path}. References need a single document location.",
                path,
            )
            return
        self.referenceable_paths[target_id] = path

    def _scan_inlines(self, fragments: Sequence[Text], path: str) -> None:
        for index, fragment in enumerate(fragments):
            fragment_path = f"{path}[{index}]"
            if isinstance(fragment, InlineChip):
                self._validate_style_reference("chip", fragment.chip_style, f"{fragment_path}.chip_style")
                continue
            if isinstance(fragment, BlockReference):
                self.references.append((fragment, fragment_path))
                if fragment.reference_format.page:
                    self._add_page_reference_warning(fragment_path)
                if fragment.label is not None:
                    self._scan_inlines(fragment.label, f"{fragment_path}.label")
                continue
            if isinstance(fragment, ReferenceGroup):
                self.reference_groups.append((fragment, fragment_path))
                if fragment.reference_format.page:
                    self._add_page_reference_warning(fragment_path)
                continue
            if isinstance(fragment, Citation):
                self.citations.append((fragment, fragment_path))
                continue
            if isinstance(fragment, Hyperlink):
                self.hyperlinks.append((fragment, fragment_path))
                self._scan_inlines(fragment.label, f"{fragment_path}.label")
                continue
            if isinstance(fragment, Comment):
                if isinstance(fragment, MarginNote):
                    self._add_compatibility_warning(
                        "margin-note-renderer-fallback",
                        fragment_path,
                    )
                self._scan_inlines(fragment.comment, f"{fragment_path}.comment")
                continue
            if isinstance(fragment, Footnote):
                self._scan_inlines(fragment.note, f"{fragment_path}.note")
                continue
            if isinstance(fragment, (TextBox, Shape, ImageBox)):
                self._collect_positioned_item(fragment, fragment_path)

    def _validate_style_reference(self, category: str, value: object, path: str) -> None:
        if not isinstance(value, str):
            return
        stylesheet = self.document.settings.theme.stylesheet
        try:
            stylesheet.resolve(category, value)
        except KeyError:
            wrong_category = self._find_style_category(value, exclude=category)
            if wrong_category is not None:
                self._add(
                    "error",
                    "wrong-style-category",
                    f"Style {value!r} is registered as a {wrong_category.replace('_', ' ')} "
                    f"style, not a {category.replace('_', ' ')} style.",
                    path,
                )
                return
            self._add(
                "error",
                "unknown-style-name",
                f"Unknown {category.replace('_', ' ')} style: {value!r}.",
                path,
            )
        except TypeError as exc:
            self._add("error", "wrong-style-category", str(exc), path)

    def _validate_box_renderer_features(self, block: Box, path: str) -> None:
        try:
            box_style = self.document.settings.theme.stylesheet.resolve("box", block.style, None)
        except (KeyError, TypeError):
            return
        shadow = block.shadow if block.shadow is not None else getattr(box_style, "shadow", False)
        if shadow:
            self._add_box_shadow_warning(f"{path}.shadow")

    def _validate_box_style_shadow(self, value: object, path: str) -> None:
        try:
            box_style = self.document.settings.theme.stylesheet.resolve("box", value, None)
        except (KeyError, TypeError):
            return
        if getattr(box_style, "shadow", False):
            self._add_box_shadow_warning(path)

    def _add_box_shadow_warning(self, path: str) -> None:
        note = compatibility_note("box-shadow-html-only")
        self._add(
            "warning",
            note.code,
            note.message,
            path,
            formats=note.formats,
        )

    def _validate_equation(self, block: Equation, path: str) -> None:
        for source_index, source in enumerate(block.math_sources()):
            for command in unsupported_latex_commands(source):
                self._add(
                    "warning",
                    "unsupported-latex-command",
                    f"Equation source uses unsupported LaTeX command \\{command}. "
                    "It will be rendered as readable fallback text.",
                    f"{path}.expression[{source_index}]",
                )

    def _find_style_category(self, name: str, *, exclude: str) -> str | None:
        stylesheet = self.document.settings.theme.stylesheet
        normalized_name = name.strip()
        for category in (
            "text",
            "paragraph",
            "run_in_title",
            "list",
            "box",
            "table",
            "table_cell",
            "chip",
        ):
            if category == exclude:
                continue
            styles = getattr(stylesheet, category, None)
            if not isinstance(styles, dict):
                continue
            if normalized_name in styles:
                return category
            prefixed_name = normalized_name.removeprefix(f"{category}.")
            if prefixed_name in styles:
                return category
        return None

    def _validate_title(self, title: Sequence[Text], path: str, message: str) -> None:
        if not _plain_text(title).strip():
            self._add("error", "blank-heading-title", message, path)

    def _validate_heading_level(
        self,
        section: Section,
        path: str,
        parent_level: int | None,
    ) -> None:
        if parent_level is None:
            if section.numbered and section.level > 1:
                self._add(
                    "warning",
                    "top-level-heading-below-chapter",
                    "A numbered top-level section starts below chapter level. "
                    "Wrap it in a Chapter(...) or set numbered=False for front matter.",
                    path,
                )
            return

        if section.level > parent_level + 1:
            self._add(
                "warning",
                "skipped-heading-level",
                f"Heading level jumps from {parent_level} to {section.level}. "
                "Consider inserting the missing intermediate section level.",
                path,
            )

    def _validate_table(
        self,
        table: Table,
        path: str,
        *,
        warn_missing_caption: bool = True,
        scan_caption: bool = True,
    ) -> None:
        layout = table._layout()
        if layout.column_count < 1:
            self._add(
                "error",
                "empty-table",
                "Table must contain at least one rendered column.",
                path,
            )
        if table.column_widths is not None:
            for index, width in enumerate(table.column_widths):
                if width <= 0:
                    self._add(
                        "error",
                        "invalid-column-width",
                        "Table column widths must be greater than zero.",
                        f"{path}.column_widths[{index}]",
                    )
            self._validate_table_width(table, path)
        elif table.columns is not None:
            self._validate_table_width(table, path)
        elif layout.column_count >= 8 and table.overflow_policy.action == "warn":
            self._add(
                "warning",
                "many-table-columns",
                f"Table has {layout.column_count} columns. Wide tables may wrap poorly "
                "in fixed-page renderers; consider columns, column_widths, "
                "split=True, or a narrower table.",
                path,
                formats=("docx", "pdf"),
            )

        if table.caption is None and warn_missing_caption:
            self._add(
                "warning",
                "missing-table-caption",
                "Captionless tables cannot appear in generated table lists and cannot be "
                "referenced with an automatic table number.",
                f"{path}.caption",
            )

        for row_index, row in enumerate(table.header_rows):
            for cell_index, cell in enumerate(row):
                cell_path = f"{path}.header_rows[{row_index}][{cell_index}]"
                self._validate_style_reference("table_cell", cell.style, f"{cell_path}.style")
                self._validate_style_reference(
                    "paragraph",
                    cell.content.style,
                    f"{cell_path}.content.style",
                )
                self._scan_inlines(
                    cell.content.content,
                    f"{cell_path}.content",
                )
        for row_index, row in enumerate(table.rows):
            for cell_index, cell in enumerate(row):
                cell_path = f"{path}.rows[{row_index}][{cell_index}]"
                self._validate_style_reference("table_cell", cell.style, f"{cell_path}.style")
                self._validate_style_reference(
                    "paragraph",
                    cell.content.style,
                    f"{cell_path}.content.style",
                )
                self._scan_inlines(
                    cell.content.content,
                    f"{cell_path}.content",
                )
        for index, style in table.row_styles.items():
            self._validate_style_reference("table_cell", style, f"{path}.row_styles[{index}]")
        for index, style in table.column_styles.items():
            self._validate_style_reference("table_cell", style, f"{path}.column_styles[{index}]")
        if table.columns is not None:
            for index, column in enumerate(table.columns):
                self._validate_style_reference(
                    "table_cell",
                    column.style,
                    f"{path}.columns[{index}].style",
                )
        for index, style in table.header_row_styles.items():
            self._validate_style_reference(
                "table_cell",
                style,
                f"{path}.header_row_styles[{index}]",
            )
        if table.caption is not None and scan_caption:
            self._scan_inlines(table.caption.content, f"{path}.caption")

    def _validate_pdf_pages(self, block: PdfPages, path: str) -> None:
        if block.source.suffix.lower() != ".pdf":
            self._add(
                "error",
                "invalid-pdf-pages-source",
                f"PdfPages source must be a PDF file: {block.source}.",
                f"{path}.source",
            )
            return
        if not block.source.exists():
            self._add(
                "error",
                "missing-pdf-pages-source",
                f"PDF file does not exist: {block.source}.",
                f"{path}.source",
            )
            return
        if not block.source.is_file():
            self._add(
                "error",
                "invalid-pdf-pages-source",
                f"PDF source is not a file: {block.source}.",
                f"{path}.source",
            )
            return
        try:
            block.selected_page_indexes()
        except Exception as exc:
            self._add(
                "error",
                "invalid-pdf-pages-selection",
                str(exc),
                f"{path}.pages",
            )
        self._add(
            "warning",
            "pdf-pages-non-pdf-output",
            "PdfPages inserts actual pages in PDF output. DOCX and HTML output "
            "render a link-style placeholder instead.",
            path,
            formats=("docx", "html"),
        )

    def _validate_figure(
        self,
        figure: Figure | SubFigure,
        path: str,
        *,
        warn_missing_caption: bool = True,
    ) -> None:
        for field_name in ("width", "height"):
            value = getattr(figure, field_name)
            if value is not None and value <= 0:
                self._add(
                    "error",
                    "invalid-figure-size",
                    f"{type(figure).__name__}.{field_name} must be greater than "
                    "zero when supplied.",
                    f"{path}.{field_name}",
                )
        if not isinstance(figure.image_format, str) or not figure.image_format.strip():
            self._add(
                "error",
                "invalid-image-format",
                f"{type(figure).__name__}.image_format must not be empty.",
                f"{path}.image_format",
            )
        if figure.image_dpi is not None and figure.image_dpi <= 0:
            self._add(
                "error",
                "invalid-image-dpi",
                f"{type(figure).__name__}.image_dpi must be greater than zero.",
                f"{path}.image_dpi",
            )
        self._validate_figure_size(figure, path)
        self._validate_image_source(figure.image_source, path)
        if figure.caption is not None:
            self._scan_inlines(figure.caption.content, f"{path}.caption")
        elif warn_missing_caption:
            self._add(
                "warning",
                "missing-figure-caption",
                f"Captionless {type(figure).__name__} objects cannot appear in generated "
                "figure lists and cannot be referenced with an automatic figure number.",
                f"{path}.caption",
            )

    def _validate_subfigure_group(self, group: SubFigureGroup, path: str) -> None:
        for subfigure_index, subfigure in enumerate(group.subfigures):
            subfigure_path = f"{path}.subfigures[{subfigure_index}]"
            self._register_referenceable(subfigure, subfigure_path)
            self._validate_figure(
                subfigure,
                subfigure_path,
                warn_missing_caption=False,
            )
        if group.caption is not None:
            self._scan_inlines(group.caption.content, f"{path}.caption")
        else:
            self._add(
                "warning",
                "missing-figure-caption",
                "Captionless SubFigureGroup objects cannot appear in generated figure "
                "lists and cannot be referenced with an automatic figure number.",
                f"{path}.caption",
            )
        self._validate_subfigure_group_size(group, path)

    def _validate_subtable_group(self, group: SubTableGroup, path: str) -> None:
        for subtable_index, subtable in enumerate(group.subtables):
            subtable_path = f"{path}.subtables[{subtable_index}]"
            self._register_referenceable(subtable, subtable_path)
            self._validate_table(
                subtable.table,
                f"{subtable_path}.table",
                warn_missing_caption=False,
                scan_caption=False,
            )
            if subtable.caption is not None:
                self._scan_inlines(subtable.caption.content, f"{subtable_path}.caption")
        if group.caption is not None:
            self._scan_inlines(group.caption.content, f"{path}.caption")
        else:
            self._add(
                "warning",
                "missing-table-caption",
                "Captionless SubTableGroup objects cannot appear in generated table "
                "lists and cannot be referenced with an automatic table number.",
                f"{path}.caption",
            )
        self._validate_subtable_group_size(group, path)

    def _validate_image_source(self, source: object, path: str) -> None:
        if isinstance(source, ImageData):
            if not source.data:
                self._add(
                    "error",
                    "empty-image-data",
                    "ImageData must contain non-empty bytes.",
                    f"{path}.image_source",
                )
            return

        if isinstance(source, Path):
            if not source.exists():
                self._add(
                    "error",
                    "missing-image-file",
                    f"Image file does not exist: {source}.",
                    f"{path}.image_source",
                )
                return
            if not source.is_file():
                self._add(
                    "error",
                    "invalid-image-file",
                    f"Image source is not a file: {source}.",
                    f"{path}.image_source",
                )
            return

        if not hasattr(source, "savefig"):
            self._add(
                "error",
                "unsupported-image-source",
                "Image source must be a filesystem path, ImageData, or an object with "
                "savefig(...).",
                f"{path}.image_source",
            )

    def _collect_positioned_item(self, item: object, path: str) -> None:
        if isinstance(item, TextBox):
            self._scan_inlines(item.content, f"{path}.content")
            return
        if isinstance(item, ImageBox):
            if not isinstance(item.image_format, str) or not item.image_format.strip():
                self._add(
                    "error",
                    "invalid-image-format",
                    "ImageBox.image_format must not be empty.",
                    f"{path}.image_format",
                )
            if item.image_dpi is not None and item.image_dpi <= 0:
                self._add(
                    "error",
                    "invalid-image-dpi",
                    "ImageBox.image_dpi must be greater than zero.",
                    f"{path}.image_dpi",
                )
            self._validate_image_source(item.image_source, path)
            return
        if isinstance(item, Shape):
            return

        self._add(
            "error",
            "unsupported-positioned-item",
            f"Unsupported positioned item: {type(item)!r}.",
            path,
        )

    def _validate_citations(self) -> None:
        for citation, path in self.citations:
            target = citation.target
            if isinstance(target, CitationSource):
                continue
            if target not in self.document.citations.entries:
                self._add(
                    "error",
                    "unresolved-citation",
                    f"Citation key {target!r} is not present in the document citation library.",
                    path,
                )

    def _build_render_index_if_possible(self) -> RenderIndex | None:
        if any(issue.severity == "error" for issue in self.issues):
            return None

        from oodocs.layout.indexing import build_render_index

        try:
            return build_render_index(self.document)
        except OODocsError as exc:
            self._add(
                "error",
                "indexing-error",
                str(exc),
                "document",
            )
            return None

    def _validate_references(self, render_index: RenderIndex | None) -> None:
        for reference, path in self.references:
            self._validate_reference(reference, path, render_index)
        for group, path in self.reference_groups:
            for index, target in enumerate(group.targets):
                self._validate_reference(
                    BlockReference(target),
                    f"{path}.targets[{index}]",
                    render_index,
                )

    def _add_page_reference_warning(self, path: str) -> None:
        self._add(
            "warning",
            "page-aware-reference-degrades",
            "Page-aware references currently render as ordinary object references.",
            path,
            formats=("docx", "html", "pdf"),
        )

    def _validate_hyperlinks(self, render_index: RenderIndex | None) -> None:
        for hyperlink, path in self.hyperlinks:
            if not hyperlink.internal:
                self._validate_long_url_label(hyperlink, path)

        if render_index is None:
            return
        anchors = render_index.anchors()
        for hyperlink, path in self.hyperlinks:
            if not hyperlink.internal:
                continue
            target = hyperlink.target.lstrip("#")
            if not target or target in anchors:
                continue
            self._add(
                "error",
                "broken-internal-link",
                f"Internal hyperlink target {hyperlink.target!r} does not match a document anchor.",
                path,
                formats=("docx", "html", "pdf"),
            )

    def _validate_long_url_label(self, hyperlink: Hyperlink, path: str) -> None:
        target = hyperlink.target.strip()
        if not target.lower().startswith(_EXTERNAL_URL_PREFIXES):
            return
        if len(target) < _LONG_URL_TARGET_LENGTH:
            return
        visible_text = hyperlink.plain_text()
        if _URL_SOFT_BREAK in visible_text:
            return
        longest_segment = max((len(segment) for segment in visible_text.split()), default=0)
        if longest_segment < _LONG_URL_UNBROKEN_SEGMENT_LENGTH:
            return
        self._add(
            "warning",
            "overly-long-url",
            "Long URL labels may wrap poorly in fixed-page outputs. "
            "Use url(..., breakable=True) or provide a shorter label.",
            path,
            formats=("docx", "html", "pdf"),
        )

    def _validate_reference(
        self,
        reference: BlockReference,
        path: str,
        render_index: RenderIndex | None,
    ) -> None:
        target = reference.target
        target_path = self.referenceable_paths.get(id(target))
        if target_path is None:
            self._add(
                "error",
                "missing-reference-target",
                f"Referenced {type(target).__name__} is not included in this document body.",
                path,
            )
            return

        has_custom_label = reference.label is not None
        if isinstance(target, Table):
            if target.caption is None:
                self._add(
                    "error",
                    "uncaptioned-reference-target",
                    "Table references require the target table to have a caption.",
                    path,
                )
            return

        if isinstance(target, SubTableGroup):
            if target.caption is None:
                self._add(
                    "error",
                    "uncaptioned-reference-target",
                    "SubTableGroup references require the target to have a caption.",
                    path,
                )
            return

        if isinstance(target, SubTable):
            if render_index is not None and render_index.subtable_label(target) is None:
                self._add(
                    "error",
                    "unanchored-subtable-reference",
                    "SubTable references require the target to belong to a "
                    "captioned SubTableGroup.",
                    path,
                )
            return

        if isinstance(target, (Figure, SubFigureGroup)):
            if target.caption is None:
                self._add(
                    "error",
                    "uncaptioned-reference-target",
                    f"{type(target).__name__} references require the target to have a caption.",
                    path,
                )
            return

        if isinstance(target, SubFigure):
            if render_index is not None and render_index.subfigure_label(target) is None:
                self._add(
                    "error",
                    "unanchored-subfigure-reference",
                    "SubFigure references require the target to belong to a "
                    "captioned SubFigureGroup.",
                    path,
                )
            return

        if isinstance(target, (Part, Section)):
            if target.numbered:
                return
            if not has_custom_label:
                self._add(
                    "error",
                    "unnumbered-heading-reference",
                    f"{type(target).__name__} references without a custom label "
                    "require numbered=True.",
                    path,
                )
                return
            if render_index is not None and render_index.heading_anchor(target) is None:
                self._add(
                    "warning",
                    "unanchored-labeled-reference",
                    "This labeled heading reference has no internal anchor. "
                    "Set toc=True or numbered=True if it should link to the heading.",
                    path,
                )
            return

        if isinstance(target, CountableBlock):
            if target.numbered:
                return
            if not has_custom_label:
                self._add(
                    "error",
                    "unnumbered-countable-reference",
                    "Unnumbered CountableBlock references require a custom label.",
                    path,
                )
            return

        if isinstance(target, Equation):
            if target.numbered:
                return
            if not has_custom_label:
                self._add(
                    "error",
                    "unnumbered-equation-reference",
                    "Unnumbered Equation references require a custom label.",
                    path,
                )
            return

        if isinstance(target, (Paragraph, CodeBlock, Box)):
            return

        self._add(
            "error",
            "unsupported-reference-target",
            f"Unsupported reference target: {type(target)!r}.",
            path,
        )

    def _validate_generated_content(self, render_index: RenderIndex) -> None:
        for page, path in self.generated_content:
            if isinstance(page, TableOfContents):
                if page.show_page_numbers:
                    self._add_compatibility_warning("html-toc-page-numbers", path)
                if not render_index.scoped_headings(page):
                    self._add(
                        "warning",
                        "empty-table-of-contents",
                        "TableOfContents has no matching headings to display.",
                        path,
                    )
                continue
            if isinstance(page, ListOfTables):
                if page.show_page_numbers:
                    self._add_compatibility_warning("html-table-list-page-numbers", path)
                if not render_index.scoped_tables(page):
                    self._add(
                        "warning",
                        "empty-table-list",
                        "ListOfTables has no captioned tables to display.",
                        path,
                    )
                continue
            if isinstance(page, ListOfFigures):
                if page.show_page_numbers:
                    self._add_compatibility_warning("html-figure-list-page-numbers", path)
                if not render_index.scoped_figures(page):
                    self._add(
                        "warning",
                        "empty-figure-list",
                        "ListOfFigures has no captioned figures to display.",
                        path,
                    )
                continue
            if isinstance(page, ListOfAlgorithms):
                if page.show_page_numbers:
                    self._add_compatibility_warning("html-algorithm-list-page-numbers", path)
                if not render_index.scoped_algorithms(page):
                    self._add(
                        "warning",
                        "empty-algorithm-list",
                        "ListOfAlgorithms has no numbered algorithms to display.",
                        path,
                    )
                continue
            if isinstance(page, ListOfGlossaryTerms):
                duplicates = page.glossary.duplicate_keys()
                for key in sorted(duplicates):
                    self._add(
                        "error",
                        "duplicate-glossary-key",
                        f"Glossary key {key!r} is defined more than once.",
                        path,
                    )
                if not page.glossary.entries:
                    self._add(
                        "warning",
                        "empty-glossary-list",
                        "ListOfGlossaryTerms has no glossary entries to display.",
                        path,
                    )
                continue
            if (
                isinstance(page, ListOfReferences)
                and not render_index.reference_entries(
                    page,
                    reference_sort=self.document.settings.theme.citations.reference_sort,
                )
            ):
                self._add(
                    "warning",
                    "empty-references-page",
                    "ListOfReferences has no sources to display.",
                    path,
                )
                continue
            if isinstance(page, ListOfComments) and not render_index.comments:
                self._add(
                    "warning",
                    "empty-comments-page",
                    "ListOfComments has no comments to display.",
                    path,
                )
                continue
            if isinstance(page, ListOfFootnotes) and not render_index.footnotes:
                self._add(
                    "warning",
                    "empty-footnotes-page",
                    "ListOfFootnotes has no footnotes to display.",
                    path,
                )

    def _validate_footnote_compatibility(self, render_index: RenderIndex) -> None:
        theme = self.document.settings.theme
        if theme.blocks.footnote_placement != "page":
            return
        for entry in render_index.footnotes:
            if theme.footnotes.is_native_docx_compatible(entry.stream):
                continue
            self._add_compatibility_warning(
                "docx-footnote-stream-generated-list",
                "document.body",
            )
            return

    def _validate_table_width(self, table: Table, path: str) -> None:
        column_widths = table._column_widths_in_inches(
            self.document.settings.unit,
            available_width=self.document.settings.text_width_in_inches(),
        )
        if column_widths is None:
            return
        table_width = sum(column_widths)
        text_width = self.document.settings.text_width_in_inches()
        if table_width <= text_width:
            return
        if table.overflow_policy.action == "allow":
            return
        self._add(
            "warning",
            "wide-table",
            f"Table width is {table_width:.2f}in, wider than the document text "
            f"width of {text_width:.2f}in. Fixed-page renderers may wrap or clip "
            "it; consider ColumnSpec(flex=...), Table.excerpt(...), or "
            "Table.save_csv(...) for the full matrix sidecar.",
            path,
            formats=("docx", "pdf"),
        )

    def _validate_figure_size(self, figure: Figure | SubFigure, path: str) -> None:
        width = figure.width_in_inches(self.document.settings.unit)
        if width is None:
            return
        text_width = self.document.settings.text_width_in_inches()
        if width <= text_width:
            return
        self._add(
            "warning",
            "wide-figure",
            f"{type(figure).__name__} width is {width:.2f}in, wider than the "
            f"document text width of {text_width:.2f}in. Fixed-page renderers may scale "
            "or overflow it.",
            path,
            formats=("docx", "pdf"),
        )

    def _validate_subfigure_group_size(self, group: SubFigureGroup, path: str) -> None:
        first_row = group.subfigures[: group.columns]
        if not first_row:
            return
        widths = [
            subfigure.width_in_inches(self.document.settings.unit)
            for subfigure in first_row
        ]
        if any(width is None for width in widths):
            return
        group_width = sum(width for width in widths if width is not None)
        group_width += length_to_inches(
            group.column_gap,
            group.unit or self.document.settings.unit,
        ) * max(len(first_row) - 1, 0)
        text_width = self.document.settings.text_width_in_inches()
        if group_width <= text_width:
            return
        self._add(
            "warning",
            "wide-figure",
            f"SubFigureGroup first row is {group_width:.2f}in wide, wider than the "
            f"document text width of {text_width:.2f}in. Fixed-page renderers may "
            "scale or overflow it.",
            path,
            formats=("docx", "pdf"),
        )

    def _validate_subtable_group_size(self, group: SubTableGroup, path: str) -> None:
        first_row = group.subtables[: group.columns]
        if not first_row:
            return
        gap = length_to_inches(
            group.column_gap,
            group.unit or self.document.settings.unit,
        )
        available_width = max(
            (
                self.document.settings.text_width_in_inches()
                - gap * max(group.columns - 1, 0)
            )
            / group.columns,
            0,
        )
        widths = [
            subtable.width_in_inches(
                self.document.settings.unit,
                available_width=available_width,
            )
            for subtable in first_row
        ]
        if any(width is None for width in widths):
            return
        group_width = sum(width for width in widths if width is not None)
        group_width += gap * max(len(first_row) - 1, 0)
        text_width = self.document.settings.text_width_in_inches()
        if group_width <= text_width:
            return
        self._add(
            "warning",
            "wide-table",
            f"SubTableGroup first row is {group_width:.2f}in wide, wider than the "
            f"document text width of {text_width:.2f}in. Fixed-page renderers may "
            "wrap or overflow it.",
            path,
            formats=("docx", "pdf"),
        )

    def _add_compatibility_warning(self, code: str, path: str) -> None:
        note = compatibility_note(code)
        self._add(
            "warning",
            note.code,
            note.message,
            path,
            formats=note.formats,
        )


def _plain_text(fragments: Sequence[Text]) -> str:
    return "".join(fragment.plain_text() for fragment in fragments)


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_int(value: object) -> int | None:
    return int(value) if value is not None else None


def _normalize_warning_codes(values: Iterable[object]) -> set[str]:
    return {str(value).strip() for value in values if str(value).strip()}


def _object_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value]
    raise TypeError("warning code lists must be strings or iterables")


def _issue_matches_formats(
    issue: ValidationIssue,
    requested_formats: set[OutputFormat],
) -> bool:
    return any(output_format in requested_formats for output_format in issue.formats)


def _format_issue_table(rows: Sequence[tuple[str, str, str, str, str, str, str]]) -> str:
    headers = ("Severity", "Formats", "Code", "Source", "Path", "Line", "Message")
    max_widths = (16, 14, 30, 24, 38, 8, 72)
    widths = [
        min(
            max(len(headers[index]), *(len(row[index]) for row in rows)),
            max_widths[index],
        )
        for index in range(len(headers))
    ]
    border = _table_border(widths)
    lines = [
        border,
        _table_row(headers, widths),
        border,
    ]
    for row in rows:
        for wrapped_row in _wrap_row(row, widths):
            lines.append(_table_row(wrapped_row, widths))
        lines.append(border)
    return "\n".join(lines)


def _table_border(widths: Sequence[int]) -> str:
    return "+" + "+".join("-" * (width + 2) for width in widths) + "+"


def _table_row(values: Sequence[str], widths: Sequence[int]) -> str:
    cells = [
        f" {value:<{width}} "
        for value, width in zip(values, widths)
    ]
    return "|" + "|".join(cells) + "|"


def _wrap_row(values: Sequence[str], widths: Sequence[int]) -> list[tuple[str, ...]]:
    wrapped_cells = [
        wrap(value, width=width, break_long_words=True, break_on_hyphens=False)
        or [""]
        for value, width in zip(values, widths)
    ]
    row_count = max(len(cell) for cell in wrapped_cells)
    return [
        tuple(
            wrapped_cells[column][row_index]
            if row_index < len(wrapped_cells[column])
            else ""
            for column in range(len(values))
        )
        for row_index in range(row_count)
    ]


__all__ = [
    "DocumentValidationError",
    "ResultLike",
    "ValidationIssue",
    "ValidationPolicy",
    "ValidationResult",
    "ValidationSeverity",
    "validate_document",
]
