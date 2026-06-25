from __future__ import annotations

from apidoc_samples import write_mixed_docstring_repo
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import (
    ApiBuildConfig,
    ApiCoverageResult,
    ApiDocstringParser,
    ApiPackage,
    check_api_docs,
    collect_api,
)
from oodocs.apidoc.cli import main


def test_general_repo_auto_parser_objects_compose_into_document(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    parser = ApiDocstringParser.auto()

    api = collect_api(
        repo,
        collector="inspect",
        public_policy="__all__",
        docstring_style=parser,
    )
    client = api.find("mixedpkg.Client")
    method = api.find("mixedpkg.Client.connect")
    function = api.find("mixedpkg.connect")
    coverage = check_api_docs(api, fail_under=1.0)

    assert api.name == "mixedpkg"
    assert client is not None
    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"
    assert method.parameters[0].description == "Timeout in seconds."
    assert method.returns is not None
    assert method.returns.description == "Whether the connection succeeded."
    assert function is not None
    assert function.metadata["docstring_style"] == "google"
    assert coverage.object_coverage == 1.0

    document = Document(
        "Mixed Package API Notes",
        Chapter(
            "Selected API",
            Paragraph("These sections are composed from a normal Python repository."),
            client.to_section(level=2, profile="manual"),
        ),
        Chapter(
            "Function Index",
            api.to_summary_table(api.functions(), profile="compact"),
        ),
        Chapter("Coverage", coverage.to_table()),
    )

    outputs = document.save_all(
        tmp_path / "rendered",
        stem="mixed-api",
        formats=("html",),
    )

    html = outputs["html"].read_text(encoding="utf-8")
    assert "mixedpkg.Client" in html
    assert "Timeout in seconds." in html
    assert "Object coverage" in html


def test_general_repo_pyproject_auto_parser_builds_cli_bundle(tmp_path) -> None:
    repo = write_mixed_docstring_repo(tmp_path)
    build_config = ApiBuildConfig.from_pyproject(repo)
    parser = build_config.collection.docstring_parser()
    output_dir = tmp_path / "bundle"

    assert parser == ApiDocstringParser.auto()
    assert parser.detect("Parameters\n----------\ntimeout : float\n    Timeout.") == "numpy"
    assert build_config.module_prefix == "mixedpkg"

    api = collect_api(repo, config=build_config.collection)
    method = api.find("mixedpkg.Client.connect")
    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"

    assert (
        main(
            [
                "build",
                str(repo),
                "--config",
                str(repo / "pyproject.toml"),
                "--out",
                str(output_dir),
            ]
        )
        == 0
    )

    html_path = output_dir / "mixedpkg-api.html"
    api_path = output_dir / "mixedpkg-api.json"
    coverage_path = output_dir / "mixedpkg-api-coverage.json"
    assert html_path.exists()
    assert api_path.exists()
    assert coverage_path.exists()
    assert (output_dir / "mixedpkg-api-coverage.csv").exists()

    html = html_path.read_text(encoding="utf-8")
    assert "mixedpkg.Client" in html
    assert "Timeout in seconds." in html

    rendered_api = ApiPackage.read_json(api_path)
    rendered_method = rendered_api.find("mixedpkg.Client.connect")
    assert rendered_method is not None
    assert rendered_method.metadata["docstring_style"] == "numpy"
    assert ApiCoverageResult.read_json(coverage_path).object_coverage == 1.0
