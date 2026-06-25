"""Build composable API-object documentation examples."""

from __future__ import annotations

from pathlib import Path

from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import check_api_docs, collect_api


ARTIFACT_DIR = Path("artifacts/api-objects-example")


def build_document() -> Document:
    """Build a document assembled from parsed API objects.

    Returns:
        OODocs document that combines selected API object sections, a function
        summary table, and coverage evidence.
    """

    api = collect_api("oodocs", public_policy="__all__", collector="auto")
    coverage = check_api_docs(api)
    classes = api.select(kind="class", module_prefix="oodocs.components")[:3]
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
    api = collect_api("oodocs", public_policy="__all__", collector="auto")
    coverage = check_api_docs(api)
    document = build_document()

    document.save_all(ARTIFACT_DIR, stem="oodocs-api-objects")
    api.write_json(ARTIFACT_DIR / "oodocs-api-objects.json")
    coverage.write_csv(ARTIFACT_DIR / "oodocs-api-coverage.csv")


if __name__ == "__main__":
    main()
