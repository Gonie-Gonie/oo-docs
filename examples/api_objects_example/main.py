"""Build composable API-object documentation examples."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import (
    ApiCoverageResult,
    ApiDocstringParser,
    ApiPackage,
    check_api_docs,
    collect_api,
)


ARTIFACT_DIR = Path("artifacts/api-objects-example")
FULL_REFERENCE_STEM = "oodocs-full-api-reference"
COMPOSITION_STEM = "oodocs-api-objects"
COVERAGE_STEM = "oodocs-api-coverage"


def _log(message: str, *, verbose: bool) -> None:
    if verbose:
        print(message, flush=True)


def collect_target_api(
    target: str | Path = "oodocs",
    *,
    public_policy: str = "__all__",
    collector: str = "auto",
    docstring_style: str | ApiDocstringParser | None = None,
) -> ApiPackage:
    """Collect any Python package, module, file, or repository target.

    Args:
        target: Importable package/module name, Python file, package directory,
            or repository checkout to document.
        public_policy: Public boundary passed to ``collect_api``.
        collector: Collector backend passed to ``collect_api``.
        docstring_style: Docstring parser style or reusable parser object.
            Defaults to ``ApiDocstringParser.auto()`` so mixed Google, NumPy,
            Sphinx, Markdown, and plain docstrings can be normalized together.

    Returns:
        Collected API package object tree that can be queried, serialized, or
        converted to OODocs blocks.

    Examples:
        Collect a normal ``src/`` layout repository with a reusable auto parser:

        ```python
        from examples.api_objects_example.main import collect_target_api
        from oodocs.apidoc import ApiDocstringParser

        api = collect_target_api(
            ".",
            public_policy="__all__",
            docstring_style=ApiDocstringParser.auto(),
        )
        document = api.to_document(profile="compact")
        ```
    """

    parser = docstring_style or ApiDocstringParser.auto()
    return collect_api(
        target,
        public_policy=public_policy,
        collector=collector,
        docstring_style=parser,
    )


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

    return collect_target_api("oodocs", public_policy="__all__", collector="auto")


def build_full_package_document(
    api: ApiPackage | None = None,
    *,
    title: str | None = None,
) -> Document:
    """Build a full package API reference document.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package is collected from the current environment.
        title: Optional document title. Defaults to ``"{api.name} API
            Reference"``.

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
        title=title or f"{api.name} API Reference",
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
    target: str | Path = "oodocs",
    public_policy: str = "__all__",
    collector: str = "auto",
    docstring_style: str | ApiDocstringParser | None = None,
    formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> dict[str, Path]:
    """Render the full API-object example bundle.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package or ``target`` is collected from the current environment.
        coverage: Optional pre-computed coverage result for ``api``.
        output_dir: Directory that receives rendered documents and sidecars.
        target: Importable package/module name, Python file, package directory,
            or repository checkout collected when ``api`` is omitted.
        public_policy: Public boundary used when collecting ``target``.
        collector: Collector backend used when collecting ``target``.
        docstring_style: Docstring parser style or reusable parser object used
            when collecting ``target``.
        formats: Optional subset of formats passed to ``Document.save_all``.
            Defaults to all supported formats.
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
            target=".",
            output_dir="artifacts/api-objects-example",
            docstring_style="auto",
            verbose=True,
        )
        full_reference_html = outputs["full_reference_html"]
        ```
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if api is None:
        _log(f"Collecting API objects from {target!s}...", verbose=verbose)
        api = collect_target_api(
            target,
            public_policy=public_policy,
            collector=collector,
            docstring_style=docstring_style,
        )
    if coverage is None:
        _log("Checking API documentation coverage...", verbose=verbose)
        coverage = check_api_docs(api)

    save_kwargs: dict[str, object] = {"verbose": verbose}
    if formats is not None:
        save_kwargs["formats"] = tuple(formats)

    _log("Building full package API reference...", verbose=verbose)
    full_reference = build_full_package_document(api)
    _log("Rendering full package API reference...", verbose=verbose)
    full_outputs = full_reference.save_all(
        output_path,
        stem=FULL_REFERENCE_STEM,
        **save_kwargs,
    )

    _log("Building composable API-object document...", verbose=verbose)
    document = build_document(api, coverage)
    _log("Rendering composable API-object document...", verbose=verbose)
    composition_outputs = document.save_all(
        output_path,
        stem=COMPOSITION_STEM,
        **save_kwargs,
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


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the API objects example."""

    parser = argparse.ArgumentParser(
        description="Render composable API-object documents for a Python target."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="oodocs",
        help="Importable module/package, Python file, package directory, or repo path.",
    )
    parser.add_argument(
        "--out",
        default=str(ARTIFACT_DIR),
        help="Output directory for rendered documents and sidecars.",
    )
    parser.add_argument(
        "--collector",
        default="auto",
        help="Collector backend passed to collect_api, such as auto, griffe, or inspect.",
    )
    parser.add_argument(
        "--public-policy",
        default="__all__",
        help="Public API policy passed to collect_api.",
    )
    parser.add_argument(
        "--docstring-style",
        default="auto",
        help="Docstring style or parser name passed to collect_api.",
    )
    parser.add_argument(
        "--to",
        action="append",
        dest="formats",
        help="Output format to render. Repeat for multiple formats.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Render the API object example and sidecars.

    Args:
        argv: Optional argument list. Defaults to command-line arguments.

    Examples:
        Run the example for the current repository and render only HTML:

        ```python
        from examples.api_objects_example.main import main

        main([".", "--to", "html", "--out", "artifacts/api-objects-example"])
        ```
    """

    args = _parse_args(argv)
    outputs = render_api_objects_example(
        output_dir=args.out,
        target=args.target,
        public_policy=args.public_policy,
        collector=args.collector,
        docstring_style=args.docstring_style,
        formats=args.formats,
        verbose=not args.quiet,
    )
    for path in outputs.values():
        print(f"Wrote {path}", flush=True)


if __name__ == "__main__":
    main()
