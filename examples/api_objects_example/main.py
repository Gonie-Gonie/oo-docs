"""Build composable API-object documentation examples."""

from __future__ import annotations

from pathlib import Path

from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import ApiCoverageResult, ApiPackage, check_api_docs, collect_api


ARTIFACT_DIR = Path("artifacts/api-objects-example")
FULL_REFERENCE_STEM = "oodocs-full-api-reference"
COMPOSITION_STEM = "oodocs-api-objects"
COVERAGE_STEM = "oodocs-api-coverage"


def _log(message: str, *, verbose: bool) -> None:
    if verbose:
        print(message, flush=True)


def collect_oodocs_api() -> ApiPackage:
    """Collect the OODocs public API object tree.

    Returns:
        Collected API package using the release workflow's public boundary.

    Examples:
        Collect the package once and reuse it for multiple rendered documents:

        ```python
        from examples.api_objects_example.main import collect_oodocs_api

        api = collect_oodocs_api()
        full_reference = api.to_document("OODocs Full API Reference")
        composable_classes = api.select(kind="class", module_prefix="oodocs.components")
        ```
    """

    return collect_api("oodocs", public_policy="__all__", collector="auto")


def build_full_package_document(api: ApiPackage | None = None) -> Document:
    """Build a full package API reference document.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package is collected from the current environment.

    Returns:
        Full package reference document built through ``ApiPackage.to_document``.

    Examples:
        Render the whole collected package as a reusable API reference bundle:

        ```python
        from examples.api_objects_example.main import (
            build_full_package_document,
            collect_oodocs_api,
        )

        api = collect_oodocs_api()
        document = build_full_package_document(api)
        document.save_all(
            "artifacts/api-objects-example",
            stem="oodocs-full-api-reference",
        )
        ```
    """

    api = api or collect_oodocs_api()
    return api.to_document(
        title="OODocs Full API Reference",
        profile="compact",
        include_coverage=True,
        include_modules=True,
    )


def build_document(
    api: ApiPackage | None = None,
    coverage: ApiCoverageResult | None = None,
) -> Document:
    """Build a document assembled from parsed API objects.

    Args:
        api: Optional pre-collected API package.
        coverage: Optional pre-computed coverage result for ``api``.

    Returns:
        OODocs document that combines selected API object sections, a function
        summary table, and coverage evidence.

    Examples:
        Build a composable document from the same parsed API object tree:

        ```python
        from examples.api_objects_example.main import build_document, collect_oodocs_api
        from oodocs.apidoc import check_api_docs

        api = collect_oodocs_api()
        coverage = check_api_docs(api)
        document = build_document(api, coverage)
        document.save_all("artifacts/api-objects-example", stem="oodocs-api-objects")
        ```
    """

    api = api or collect_oodocs_api()
    coverage = coverage or check_api_docs(api)
    classes = api.select(kind="class", module_prefix="oodocs.components")[:3]
    if not classes:
        classes = api.select(kind="class")[:3]
    functions = api.select(kind="function")[:10]

    return Document(
        "OODocs API Object Composition",
        Chapter(
            "Selected Classes",
            Paragraph("These sections are regular OODocs blocks created from ApiObject instances."),
            *[obj.to_section(level=2, profile="compact") for obj in classes],
        ),
        Chapter(
            "Function Summary",
            Paragraph("The summary table can be inserted into release notes or evidence documents."),
            api.to_summary_table(functions, caption="Selected public functions."),
        ),
        Chapter(
            "Coverage Summary",
            Paragraph("Detailed coverage issues are written to the CSV sidecar."),
            coverage.to_table(),
        ),
    )


def write_sidecars(
    api: ApiPackage,
    coverage: ApiCoverageResult,
    output_dir: str | Path = ARTIFACT_DIR,
) -> dict[str, Path]:
    """Write API object and coverage sidecars for release evidence.

    Args:
        api: API package object tree to serialize.
        coverage: Coverage result for the same API tree.
        output_dir: Directory that receives the sidecar files.

    Returns:
        Mapping with ``api_json``, ``coverage_json``, and ``coverage_csv``
        output paths.

    Examples:
        Build a small evidence bundle beside rendered API documents:

        ```python
        from oodocs.apidoc import check_api_docs, collect_api
        from examples.api_objects_example.main import write_sidecars

        api = collect_api("oodocs", public_policy="__all__")
        coverage = check_api_docs(api, fail_under=0.90)
        sidecars = write_sidecars(api, coverage, "artifacts/api-objects-example")
        ```
    """

    sidecar_dir = Path(output_dir)
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    return {
        "api_json": api.write_json(sidecar_dir / f"{COMPOSITION_STEM}.json"),
        "coverage_json": coverage.write_json(sidecar_dir / f"{COVERAGE_STEM}.json"),
        "coverage_csv": coverage.write_csv(sidecar_dir / f"{COVERAGE_STEM}.csv"),
    }


def render_api_objects_example(
    api: ApiPackage | None = None,
    coverage: ApiCoverageResult | None = None,
    output_dir: str | Path = ARTIFACT_DIR,
    *,
    verbose: bool = False,
) -> dict[str, Path]:
    """Render the full API-object example bundle.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package is collected from the current environment.
        coverage: Optional pre-computed coverage result for ``api``.
        output_dir: Directory that receives rendered documents and sidecars.
        verbose: Whether to print major collection and rendering steps.

    Returns:
        Mapping containing DOCX/PDF/HTML paths for the full package reference,
        DOCX/PDF/HTML paths for the composable API-object document, and API
        JSON plus coverage JSON/CSV sidecar paths.

    Examples:
        Render the complete OODocs API reference and composable example bundle:

        ```python
        from examples.api_objects_example.main import render_api_objects_example

        outputs = render_api_objects_example(
            output_dir="artifacts/api-objects-example",
            verbose=True,
        )
        full_reference_html = outputs["full_reference_html"]
        ```
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if api is None:
        _log("Collecting OODocs API objects...", verbose=verbose)
        api = collect_oodocs_api()
    if coverage is None:
        _log("Checking API documentation coverage...", verbose=verbose)
        coverage = check_api_docs(api)

    _log("Building full package API reference...", verbose=verbose)
    full_reference = build_full_package_document(api)
    _log("Rendering full package API reference...", verbose=verbose)
    full_outputs = full_reference.save_all(
        output_path,
        stem=FULL_REFERENCE_STEM,
        verbose=verbose,
    )

    _log("Building composable API-object document...", verbose=verbose)
    document = build_document(api, coverage)
    _log("Rendering composable API-object document...", verbose=verbose)
    composition_outputs = document.save_all(
        output_path,
        stem=COMPOSITION_STEM,
        verbose=verbose,
    )

    _log("Writing API and coverage sidecars...", verbose=verbose)
    outputs: dict[str, Path] = {
        f"full_reference_{output_format}": path
        for output_format, path in full_outputs.items()
    }
    outputs.update(
        {
            f"composition_{output_format}": path
            for output_format, path in composition_outputs.items()
        }
    )
    outputs.update(write_sidecars(api, coverage, output_path))
    return outputs


def main() -> None:
    """Render the API object example and sidecars.

    Examples:
        Run the example from the repository root:

        ```python
        from examples.api_objects_example.main import main

        main()
        ```
    """

    outputs = render_api_objects_example(verbose=True)
    for path in outputs.values():
        print(f"Wrote {path}", flush=True)


if __name__ == "__main__":
    main()
