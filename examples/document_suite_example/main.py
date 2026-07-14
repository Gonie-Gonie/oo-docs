"""Build two neutral documents from one explicit suite context."""

from pathlib import Path
from typing import Sequence

from oodocs.components.blocks import Paragraph
from oodocs.components.references import CitationLibrary
from oodocs.document import Document
from oodocs.suite import (
    AssetResolver,
    DocumentSuite,
    DocumentSuiteBundle,
    DocumentSuiteContext,
)


ROOT = Path(__file__).resolve().parent
CONTEXT = DocumentSuiteContext(
    root=ROOT,
    output_dir=ROOT / "dist" / "document-suite",
    variables={"project": "Example Project", "version": "1.0"},
    assets=AssetResolver((ROOT / "assets",)),
    citations=CitationLibrary(),
)


def overview(context: DocumentSuiteContext) -> Document:
    return Document(
        f"{context.variables['project']} Overview",
        Paragraph(f"Current version: {context.variables['version']}"),
        citations=context.citations,
    )


def release_note(context: DocumentSuiteContext) -> Document:
    return Document(
        f"{context.variables['project']} Release Note",
        Paragraph("This document was built from the same explicit context."),
        citations=context.citations,
    )


def build_document() -> Document:
    """Build the first suite document for the common example interface."""

    return overview(CONTEXT)


def build(
    output_dir: str | Path = CONTEXT.output_dir,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> DocumentSuiteBundle:
    """Build and render both documents, returning their shared bundle."""

    formats = tuple(output_formats or ("html",))
    suite = DocumentSuite("example-release", CONTEXT)
    suite.add("overview", overview, formats=formats)
    suite.add("release-note", release_note, formats=formats)
    bundle = suite.save_all(output_dir, verbose=verbose)
    bundle.save_manifest()
    return bundle


def main() -> None:
    """Render the example suite."""

    build()


if __name__ == "__main__":
    main()
