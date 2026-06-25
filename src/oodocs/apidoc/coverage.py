"""API documentation coverage checks."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import json
from pathlib import Path

from oodocs.apidoc.examples import check_doctest_examples, check_example_syntax
from oodocs.apidoc.model import ApiDocIssue, ApiObject, ApiPackage
from oodocs.components.blocks import Chapter, Paragraph
from oodocs.components.media import Table
from oodocs.core import PathLike


@dataclass(slots=True)
class ApiCoverageResult:
    """Documentation coverage summary for an API package.

    Attributes:
        package: Package name.
        public_object_count: Number of public API objects.
        documented_object_count: Public objects with summary or description.
        undocumented_object_count: Public objects without docs.
        parameter_count: Signature parameter count.
        documented_parameter_count: Parameters documented in docstrings.
        missing_parameter_doc_count: Signature parameters missing doc text.
        extra_parameter_doc_count: Docstring parameters absent from signatures.
        return_annotation_count: Objects with return annotations.
        documented_return_count: Objects with documented returns.
        example_count: Parsed example count.
        syntax_checked_example_count: Python examples checked for syntax.
        syntax_ok_example_count: Syntax-valid Python examples.
        issues: Coverage issues.

    Examples:
        Insert coverage evidence into a release document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.coverage import check_api_docs

        api = collect_api("oodocs")
        coverage = check_api_docs(api)
        doc = Document("Release Evidence", Chapter("Coverage", coverage.to_table()))
        ```
    """

    package: str
    public_object_count: int
    documented_object_count: int
    undocumented_object_count: int
    parameter_count: int
    documented_parameter_count: int
    missing_parameter_doc_count: int
    extra_parameter_doc_count: int
    return_annotation_count: int
    documented_return_count: int
    example_count: int
    syntax_checked_example_count: int
    syntax_ok_example_count: int
    issues: list[ApiDocIssue] = field(default_factory=list)

    @property
    def object_coverage(self) -> float:
        """Return documented object ratio."""

        if self.public_object_count == 0:
            return 1.0
        return self.documented_object_count / self.public_object_count

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized coverage data."""

        return {
            "package": self.package,
            "public_object_count": self.public_object_count,
            "documented_object_count": self.documented_object_count,
            "undocumented_object_count": self.undocumented_object_count,
            "parameter_count": self.parameter_count,
            "documented_parameter_count": self.documented_parameter_count,
            "missing_parameter_doc_count": self.missing_parameter_doc_count,
            "extra_parameter_doc_count": self.extra_parameter_doc_count,
            "return_annotation_count": self.return_annotation_count,
            "documented_return_count": self.documented_return_count,
            "example_count": self.example_count,
            "syntax_checked_example_count": self.syntax_checked_example_count,
            "syntax_ok_example_count": self.syntax_ok_example_count,
            "object_coverage": self.object_coverage,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_table(self, *, caption: str | None = "API documentation coverage") -> Table:
        """Return coverage metrics as an OODocs table."""

        rows = [
            ["Public objects", str(self.public_object_count)],
            ["Documented objects", str(self.documented_object_count)],
            ["Undocumented objects", str(self.undocumented_object_count)],
            ["Object coverage", f"{self.object_coverage:.1%}"],
            ["Parameters", str(self.parameter_count)],
            ["Documented parameters", str(self.documented_parameter_count)],
            ["Missing parameter docs", str(self.missing_parameter_doc_count)],
            ["Extra parameter docs", str(self.extra_parameter_doc_count)],
            ["Examples", str(self.example_count)],
            ["Syntax-checked examples", str(self.syntax_checked_example_count)],
            ["Syntax-valid examples", str(self.syntax_ok_example_count)],
            ["Issues", str(len(self.issues))],
        ]
        return Table(["Metric", "Value"], rows, caption=caption)

    def to_section(self) -> Chapter:
        """Return coverage as an OODocs chapter."""

        blocks: list[object] = [self.to_table()]
        if self.issues:
            blocks.append(
                Table(
                    ["Severity", "Code", "Object", "Module", "Location", "Message"],
                    [issue.to_row() for issue in self.issues],
                    caption="API documentation issues",
                )
            )
        else:
            blocks.append(Paragraph("No API documentation issues were found."))
        return Chapter("API Documentation Coverage", *blocks)

    def write_json(self, path: PathLike) -> Path:
        """Write coverage sidecar JSON."""

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path

    def write_csv(self, path: PathLike) -> Path:
        """Write coverage issues as CSV."""

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["severity", "code", "qualname", "module", "path", "line_number", "message"])
            for issue in self.issues:
                writer.writerow(
                    [
                        issue.severity,
                        issue.code,
                        issue.qualname or "",
                        issue.module or "",
                        issue.path or "",
                        issue.line_number or "",
                        issue.message,
                    ]
                )
        return output_path


def check_api_docs(
    api: ApiPackage,
    *,
    fail_under: float | None = None,
    require_examples: bool = False,
    require_renderer_notes: bool = False,
) -> ApiCoverageResult:
    """Check API documentation coverage.

    Args:
        api: Collected API package.
        fail_under: Optional minimum object coverage ratio.
        require_examples: Whether every public object should include examples.
        require_renderer_notes: Whether every public object should include
            renderer notes.

    Returns:
        Coverage result with issues.
    """

    objects = api.public_objects()
    issues: list[ApiDocIssue] = list(api.issues)
    documented_objects = 0
    parameter_count = 0
    documented_parameter_count = 0
    missing_parameter_doc_count = 0
    extra_parameter_doc_count = 0
    return_annotation_count = 0
    documented_return_count = 0
    example_count = 0
    syntax_checked_example_count = 0
    syntax_ok_example_count = 0

    for obj in objects:
        if obj.documented:
            documented_objects += 1
        else:
            issues.append(_issue(obj, "warning", "missing-docstring", "Public API object has no docstring summary."))
        if not obj.plain_summary():
            issues.append(_issue(obj, "warning", "missing-summary", "Public API object has no summary."))
        for parameter in obj.parameters:
            if parameter.source == "docstring":
                extra_parameter_doc_count += 1
                continue
            parameter_count += 1
            if parameter.documented:
                documented_parameter_count += 1
            elif parameter.name not in {"self", "cls"}:
                missing_parameter_doc_count += 1
                issues.append(
                    _issue(
                        obj,
                        "warning",
                        "missing-parameter-doc",
                        f"Parameter {parameter.name!r} is not documented.",
                    )
                )
        if obj.returns and obj.returns.annotation:
            return_annotation_count += 1
            if obj.returns.documented:
                documented_return_count += 1
            else:
                issues.append(_issue(obj, "warning", "missing-return-doc", "Return annotation is not documented."))
        if require_examples and not obj.examples:
            issues.append(_issue(obj, "warning", "missing-examples", "Public API object has no examples."))
        if require_renderer_notes and not obj.renderer_notes:
            issues.append(_issue(obj, "info", "missing-renderer-notes", "Object has no renderer notes."))
        if obj.deprecated and not obj.deprecation_message:
            issues.append(_issue(obj, "warning", "missing-deprecation-guidance", "Deprecated API has no guidance."))
        example_count += len(obj.examples)
        for example in obj.examples:
            if example.language.lower() in {"python", "py", "pycon"}:
                syntax_checked_example_count += 1
                if check_example_syntax(example):
                    syntax_ok_example_count += 1
                else:
                    issues.append(_issue(obj, "warning", "example-syntax-error", "Example contains invalid Python syntax."))
        issues.extend(check_doctest_examples(obj))

    result = ApiCoverageResult(
        package=api.name,
        public_object_count=len(objects),
        documented_object_count=documented_objects,
        undocumented_object_count=len(objects) - documented_objects,
        parameter_count=parameter_count,
        documented_parameter_count=documented_parameter_count,
        missing_parameter_doc_count=missing_parameter_doc_count,
        extra_parameter_doc_count=extra_parameter_doc_count,
        return_annotation_count=return_annotation_count,
        documented_return_count=documented_return_count,
        example_count=example_count,
        syntax_checked_example_count=syntax_checked_example_count,
        syntax_ok_example_count=syntax_ok_example_count,
        issues=issues,
    )
    if fail_under is not None and result.object_coverage < fail_under:
        result.issues.append(
            ApiDocIssue(
                "error",
                "coverage-fail-under",
                f"Object documentation coverage {result.object_coverage:.1%} is below {fail_under:.1%}.",
            )
        )
    return result


def _issue(obj: ApiObject, severity: str, code: str, message: str) -> ApiDocIssue:
    return ApiDocIssue(
        severity,  # type: ignore[arg-type]
        code,
        message,
        qualname=obj.qualname,
        module=obj.module,
        path=obj.source_path,
        line_number=obj.line_number,
    )


__all__ = [
    "ApiCoverageResult",
    "check_api_docs",
]
