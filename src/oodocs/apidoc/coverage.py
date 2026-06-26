"""API documentation coverage checks."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Mapping

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
        doctest_checked_example_count: Doctest-style examples checked for
            parse validity.
        doctest_ok_example_count: Doctest-style examples with valid doctest
            syntax.
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
    doctest_checked_example_count: int = 0
    doctest_ok_example_count: int = 0
    issues: list[ApiDocIssue] = field(default_factory=list)

    @property
    def object_coverage(self) -> float:
        """Return the documented public object ratio.

        Returns:
            Fraction between ``0.0`` and ``1.0``. Packages with no public
            objects report ``1.0`` so empty internal packages do not fail
            coverage gates by default.

        Examples:
            Use the ratio as a CI gate before rendering release evidence:

            ```python
            from oodocs.apidoc import collect_api
            from oodocs.apidoc.coverage import check_api_docs

            api = collect_api(".")
            coverage = check_api_docs(api)
            assert coverage.object_coverage >= 0.9
            ```
        """

        if self.public_object_count == 0:
            return 1.0
        return self.documented_object_count / self.public_object_count

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serialized coverage data.

        Returns:
            JSON-serializable mapping containing the coverage counters,
            computed object coverage, and issue rows.

        Examples:
            Persist coverage evidence in a custom automation pipeline:

            ```python
            import json
            from pathlib import Path

            from oodocs.apidoc import collect_api
            from oodocs.apidoc.coverage import check_api_docs

            api = collect_api(".")
            coverage = check_api_docs(api)
            Path("artifacts/api-coverage.json").write_text(
                json.dumps(coverage.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            ```
        """

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
            "doctest_checked_example_count": self.doctest_checked_example_count,
            "doctest_ok_example_count": self.doctest_ok_example_count,
            "object_coverage": self.object_coverage,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiCoverageResult:
        """Reconstruct coverage data from serialized JSON data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Coverage result that can be inserted into an OODocs document.

        Raises:
            KeyError: If the serialized data is missing the required package
                name.

        Examples:
            Rehydrate coverage data loaded by another process and insert the
            table into an evidence document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiCoverageResult

            coverage = ApiCoverageResult.from_dict(saved_coverage)
            doc = Document("API Evidence", Chapter("Coverage", coverage.to_table()))
            ```
        """

        return cls(
            package=str(data["package"]),
            public_object_count=int(data.get("public_object_count", 0)),
            documented_object_count=int(data.get("documented_object_count", 0)),
            undocumented_object_count=int(data.get("undocumented_object_count", 0)),
            parameter_count=int(data.get("parameter_count", 0)),
            documented_parameter_count=int(data.get("documented_parameter_count", 0)),
            missing_parameter_doc_count=int(data.get("missing_parameter_doc_count", 0)),
            extra_parameter_doc_count=int(data.get("extra_parameter_doc_count", 0)),
            return_annotation_count=int(data.get("return_annotation_count", 0)),
            documented_return_count=int(data.get("documented_return_count", 0)),
            example_count=int(data.get("example_count", 0)),
            syntax_checked_example_count=int(data.get("syntax_checked_example_count", 0)),
            syntax_ok_example_count=int(data.get("syntax_ok_example_count", 0)),
            doctest_checked_example_count=int(data.get("doctest_checked_example_count", 0)),
            doctest_ok_example_count=int(data.get("doctest_ok_example_count", 0)),
            issues=[
                ApiDocIssue.from_dict(issue)
                for issue in data.get("issues", [])  # type: ignore[union-attr]
            ],
        )

    def to_table(self, *, caption: str | None = "API documentation coverage") -> Table:
        """Return coverage metrics as an OODocs table.

        Args:
            caption: Optional table caption.

        Returns:
            Two-column metrics table ready to insert into a ``Chapter`` or
            ``Section``.

        Examples:
            Render coverage metrics beside release notes:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import check_api_docs, collect_api

            api = collect_api("mypkg")
            coverage = check_api_docs(api)
            doc = Document("Release Evidence", Chapter("API Coverage", coverage.to_table()))
            ```
        """

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
            ["Doctest-checked examples", str(self.doctest_checked_example_count)],
            ["Doctest-valid examples", str(self.doctest_ok_example_count)],
            ["Issues", str(len(self.issues))],
        ]
        return Table(["Metric", "Value"], rows, caption=caption, split=True)

    def to_section(self) -> Chapter:
        """Return coverage metrics and issue rows as an OODocs chapter.

        Returns:
            Chapter titled ``"API Documentation Coverage"``. The chapter
            contains the metric table and either an issue table or a short
            success paragraph.

        Examples:
            Add complete coverage evidence to a rendered API reference:

            ```python
            from oodocs import Document
            from oodocs.apidoc import check_api_docs, collect_api

            api = collect_api(".", collector="griffe")
            coverage = check_api_docs(api, fail_under=0.90)
            Document("API Evidence", coverage.to_section()).save_all("artifacts/api-evidence")
            ```
        """

        blocks: list[object] = [self.to_table()]
        if self.issues:
            blocks.append(
                Table(
                    ["Severity", "Code", "Object", "Module", "Location", "Message"],
                    [issue.as_issue_row() for issue in self.issues],
                    caption="API documentation issues",
                    split=True,
                )
            )
        else:
            blocks.append(Paragraph("No API documentation issues were found."))
        return Chapter("API Documentation Coverage", *blocks)

    def write_json(self, path: PathLike) -> Path:
        """Write coverage sidecar JSON.

        Args:
            path: Output JSON path.

        Returns:
            Written path.

        Examples:
            Persist CI coverage data for a later rendering job:

            ```python
            from oodocs.apidoc import check_api_docs, collect_api

            api = collect_api(".", collector="griffe")
            coverage = check_api_docs(api)
            coverage.write_json("artifacts/api-coverage.json")
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
    def read_json(cls, path: PathLike) -> ApiCoverageResult:
        """Read a coverage JSON sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            Coverage result object.

        Raises:
            FileNotFoundError: If the sidecar path does not exist.
            json.JSONDecodeError: If the sidecar is not valid JSON.

        Examples:
            Read coverage generated by CI and render it as part of a release
            evidence document:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import ApiCoverageResult

            coverage = ApiCoverageResult.read_json("artifacts/api-coverage.json")
            doc = Document("Release Evidence", Chapter("Coverage", coverage.to_table()))
            ```
        """

        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def write_csv(self, path: PathLike) -> Path:
        """Write coverage issues as CSV.

        Args:
            path: Output CSV path.

        Returns:
            Written path.

        Examples:
            Attach coverage issue rows to release evidence:

            ```python
            from oodocs.apidoc import check_api_docs, collect_api

            api = collect_api(".", collector="griffe")
            coverage = check_api_docs(api)
            coverage.write_csv("artifacts/api-coverage.csv")
            ```
        """

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
    doctest_namespace: Mapping[str, object] | None = None,
) -> ApiCoverageResult:
    """Check API documentation coverage.

    Args:
        api: Collected API package to inspect.
        fail_under: Optional minimum documented-public-object ratio. When the
            result falls below this value, an ``error`` issue with code
            ``"coverage-fail-under"`` is appended.
        require_examples: Whether every public object should include parsed
            examples.
        require_renderer_notes: Whether every public object should include
            renderer notes.
        doctest_namespace: Optional trusted namespace used to execute
            doctest-style examples. When omitted, doctest examples are parsed
            but not executed.

    Returns:
        Coverage result with counters and issue rows. The result can be
        rendered with ``to_table()`` or ``to_section()``, serialized with
        ``write_json()``, or exported as CSV with ``write_csv()``.

    Examples:
        Gate public API docs and render the evidence:

        ```python
        from oodocs import Document
        from oodocs.apidoc import check_api_docs, collect_api

        api = collect_api(".", public_policy="__all__", collector="griffe")
        coverage = check_api_docs(
            api,
            fail_under=0.90,
            require_examples=True,
        )
        coverage.write_json("artifacts/api-coverage.json")
        coverage.write_csv("artifacts/api-coverage.csv")
        Document("API Coverage", coverage.to_section()).save_docx(
            "artifacts/api-coverage.docx"
        )
        ```
    """

    objects = api.select_public_objects()
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
    doctest_checked_example_count = 0
    doctest_ok_example_count = 0

    for obj in objects:
        if obj.documented:
            documented_objects += 1
        else:
            issues.append(_issue(obj, "warning", "missing-docstring", "Public API object has no docstring summary."))
        if not obj.summary_text():
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
        issues.extend(check_doctest_examples(obj, globs=doctest_namespace))
        for example in obj.examples:
            if example.doctest_ok is None:
                continue
            doctest_checked_example_count += 1
            if example.doctest_ok:
                doctest_ok_example_count += 1

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
        doctest_checked_example_count=doctest_checked_example_count,
        doctest_ok_example_count=doctest_ok_example_count,
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
