"""Build composable API-object documentation examples."""

from __future__ import annotations

from pathlib import Path

from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import ApiCoverageResult, ApiPackage, check_api_docs, collect_api


ARTIFACT_DIR = Path("artifacts/api-objects-example")
FULL_REFERENCE_STEM = "oodocs-full-api-reference"
COMPOSITION_STEM = "oodocs-api-objects"
COVERAGE_STEM = "oodocs-api-coverage"


def collect_oodocs_api() -> ApiPackage:
    """Collect the OODocs public API object tree.

    Returns:
        Collected API package using the release workflow's public boundary.
    """

    return collect_api("oodocs", public_policy="__all__", collector="auto")


def build_full_package_document(api: ApiPackage | None = None) -> Document:
    """Build a full package API reference document.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package is collected from the current environment.

    Returns:
        Full package reference document built through ``ApiPackage.to_document``.
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


def main() -> None:
    """Render the API object example and sidecars."""

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    api = collect_oodocs_api()
    coverage = check_api_docs(api)
    full_reference = build_full_package_document(api)
    document = build_document(api, coverage)

    full_reference.save_all(ARTIFACT_DIR, stem=FULL_REFERENCE_STEM)
    document.save_all(ARTIFACT_DIR, stem=COMPOSITION_STEM)
    write_sidecars(api, coverage, ARTIFACT_DIR)


if __name__ == "__main__":
    main()
