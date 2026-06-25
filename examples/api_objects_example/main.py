"""Build composable API-object documentation examples."""

from __future__ import annotations

from pathlib import Path

from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import ApiCoverageResult, ApiPackage, check_api_docs, collect_api


ARTIFACT_DIR = Path("artifacts/api-objects-example")
FULL_REFERENCE_STEM = "oodocs-full-api-reference"
COMPOSITION_STEM = "oodocs-api-objects"


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


def main() -> None:
    """Render the API object example and sidecars."""

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    api = collect_oodocs_api()
    coverage = check_api_docs(api)
    full_reference = build_full_package_document(api)
    document = build_document(api, coverage)

    full_reference.save_all(ARTIFACT_DIR, stem=FULL_REFERENCE_STEM)
    document.save_all(ARTIFACT_DIR, stem=COMPOSITION_STEM)
    api.write_json(ARTIFACT_DIR / f"{COMPOSITION_STEM}.json")
    coverage.write_csv(ARTIFACT_DIR / "oodocs-api-coverage.csv")


if __name__ == "__main__":
    main()
