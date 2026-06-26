from __future__ import annotations

from textwrap import dedent

import pytest

from apidoc_samples import write_undocumented_package
from oodocs.apidoc import (
    ApiExample,
    ApiModule,
    ApiObject,
    ApiPackage,
    ApiParameter,
    ApiReturn,
    collect_api,
)
from oodocs.apidoc.coverage import ApiCoverageResult, check_api_docs
from oodocs.components.media import Table


def test_apidoc_coverage_detects_missing_docs_and_serializes(tmp_path) -> None:
    package_dir = write_undocumented_package(tmp_path)
    api = collect_api(package_dir, collector="inspect", public_policy="underscore")
    coverage = check_api_docs(api)

    assert coverage.undocumented_object_count >= 1
    assert any(issue.code == "missing-docstring" for issue in coverage.issues)
    assert coverage.ok
    assert coverage.errors == ()
    assert coverage.warnings
    assert ApiCoverageResult.from_dict(coverage.to_dict()).package == "undocpkg"
    assert ApiCoverageResult.from_json(coverage.to_json()).package == "undocpkg"
    assert "undocpkg:" in coverage.format_text()
    assert isinstance(coverage.to_table(), Table)


def test_apidoc_coverage_uses_dataclass_attribute_docs_for_constructor_parameters(
    tmp_path,
) -> None:
    pytest.importorskip("griffe")
    package_dir = tmp_path / "datapkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            from dataclasses import dataclass

            __all__ = ["Settings"]

            @dataclass(slots=True)
            class Settings:
                """Runtime settings.

                Attributes:
                    path: Output path.
                    retries: Retry count.
                """

                path: str
                retries: int = 3
            '''
        ),
        encoding="utf-8",
    )

    api = collect_api(package_dir, collector="griffe", public_policy="__all__")
    settings = api.find_object("datapkg.Settings")
    coverage = check_api_docs(api)

    assert settings is not None
    assert {parameter.name for parameter in settings.parameters} >= {"path", "retries"}
    assert all(parameter.documented for parameter in settings.parameters)
    assert not [
        issue
        for issue in coverage.issues
        if issue.qualname == "datapkg.Settings"
        and issue.code == "missing-parameter-doc"
    ]


def test_apidoc_coverage_reports_quality_gate_issues(tmp_path) -> None:
    api = ApiPackage(
        "qualitypkg",
        modules=[
            ApiModule(
                "qualitypkg",
                members=[
                    ApiObject(
                        kind="function",
                        name="bad_example",
                        qualname="qualitypkg.bad_example",
                        module="qualitypkg",
                        summary="Run a bad example.",
                        signature="(value: str) -> str",
                        parameters=[ApiParameter("value", "str")],
                        returns=ApiReturn("str"),
                        examples=[
                            ApiExample("if True print('bad')", language="python"),
                            ApiExample(">>>print('bad')", language="pycon"),
                        ],
                        deprecated=True,
                    ),
                    ApiObject(
                        kind="function",
                        name="without_example",
                        qualname="qualitypkg.without_example",
                        module="qualitypkg",
                        summary="Run without an example.",
                    ),
                ],
            )
        ],
    )

    coverage = check_api_docs(
        api,
        fail_under=1.0,
        require_examples=True,
        require_renderer_notes=True,
    )
    issue_codes = {issue.code for issue in coverage.issues}

    assert coverage.public_object_count == 2
    assert coverage.documented_object_count == 2
    assert coverage.parameter_count == 1
    assert coverage.missing_parameter_doc_count == 1
    assert coverage.return_annotation_count == 1
    assert coverage.documented_return_count == 0
    assert coverage.example_count == 2
    assert coverage.syntax_checked_example_count == 2
    assert coverage.syntax_ok_example_count == 1
    assert coverage.doctest_checked_example_count == 1
    assert coverage.doctest_ok_example_count == 0
    assert {
        "doctest-failed",
        "example-syntax-error",
        "missing-deprecation-guidance",
        "missing-examples",
        "missing-parameter-doc",
        "missing-renderer-notes",
        "missing-return-doc",
    } <= issue_codes

    csv_path = coverage.save_csv(tmp_path / "coverage.csv")
    csv_text = csv_path.read_text(encoding="utf-8")

    assert "doctest-failed" in csv_text
    assert "missing-renderer-notes" in csv_text


def test_apidoc_coverage_can_execute_doctest_examples() -> None:
    def echo(value: str) -> str:
        return value

    api = ApiPackage(
        "doctestexecpkg",
        modules=[
            ApiModule(
                "doctestexecpkg",
                members=[
                    ApiObject(
                        kind="function",
                        name="good",
                        qualname="doctestexecpkg.good",
                        module="doctestexecpkg",
                        summary="Run a passing doctest.",
                        examples=[ApiExample(">>> echo('ok')\n'ok'", language="pycon")],
                    ),
                    ApiObject(
                        kind="function",
                        name="bad",
                        qualname="doctestexecpkg.bad",
                        module="doctestexecpkg",
                        summary="Run a failing doctest.",
                        examples=[ApiExample(">>> echo('bad')\n'ok'", language="pycon")],
                    ),
                ],
            )
        ],
    )

    coverage = check_api_docs(api, doctest_namespace={"echo": echo})
    issue_codes = {issue.code for issue in coverage.issues}
    good = api.find_object("doctestexecpkg.good")
    bad = api.find_object("doctestexecpkg.bad")

    assert coverage.example_count == 2
    assert coverage.syntax_checked_example_count == 2
    assert coverage.syntax_ok_example_count == 2
    assert coverage.doctest_checked_example_count == 2
    assert coverage.doctest_ok_example_count == 1
    assert "doctest-failed" in issue_codes
    assert good is not None
    assert good.examples[0].doctest_ok is True
    assert bad is not None
    assert bad.examples[0].doctest_ok is False
