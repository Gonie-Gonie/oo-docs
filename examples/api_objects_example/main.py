"""Build API help-book and composable API-object examples."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import (
    ApiHelpBookConfig,
    ApiCollectConfig,
    ApiCoverageResult,
    ApiDocstringParser,
    ApiPackage,
    ApiPresentationProfile,
    check_api_docs,
    collect_api,
)


ARTIFACT_DIR = Path("artifacts/api-objects-example")
HELP_BOOK_STEM = "oodocs-api-reference"
API_OBJECT_COMPOSITION_STEM = "oodocs-api-object-composition"
API_OBJECT_TREE_STEM = "oodocs-api-object-tree"
API_COVERAGE_STEM = "oodocs-api-coverage"


def _log(message: str, *, verbose: bool) -> None:
    if verbose:
        print(message, flush=True)


def collect_target_api(
    target: str | Path = "oodocs",
    *,
    config: ApiCollectConfig | None = None,
    public_policy: str | None = None,
    collector: str | None = None,
    docstring_style: str | ApiDocstringParser | None = None,
) -> ApiPackage:
    """Collect any Python package, module, file, or repository target.

    Args:
        target: Importable package/module name, Python file, package directory,
            or repository checkout to document.
        config: Optional collection config loaded from a repository config file.
        public_policy: Public boundary passed to ``collect_api``. Defaults to
            ``"__all__"`` when ``config`` is omitted.
        collector: Collector backend passed to ``collect_api``. Defaults to
            ``"auto"`` when ``config`` is omitted.
        docstring_style: Docstring parser style or reusable parser object.
            Defaults to ``ApiDocstringParser.auto()`` when ``config`` is
            omitted so mixed Google, NumPy, Sphinx, Markdown, and plain
            docstrings can be normalized together.

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
        document = api.to_help_book(presentation="help")
        ```

        Reuse a repository-local config so the example and release workflow
        render the same public boundary:

        ```python
        from examples.api_objects_example.main import collect_target_api
        from oodocs.apidoc import ApiHelpBookConfig

        build = ApiHelpBookConfig.from_pyproject(".")
        api = collect_target_api(".", config=build.collection)
        ```
    """

    effective_public_policy = public_policy
    effective_collector = collector
    effective_docstring_style: str | ApiDocstringParser | None = docstring_style
    if config is None:
        effective_public_policy = effective_public_policy or "__all__"
        effective_collector = effective_collector or "auto"
        effective_docstring_style = effective_docstring_style or ApiDocstringParser.auto()
    return collect_api(
        target,
        config=config,
        public_policy=effective_public_policy,
        collector=effective_collector,
        docstring_style=effective_docstring_style,
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
        help_book = api.to_help_book("OODocs API Reference")
        composable_classes = api.select_objects(
            kind="class",
            module_prefix="oodocs.components",
        )
        ```
    """

    return collect_target_api("oodocs", public_policy="__all__", collector="auto")


def build_help_book_document(
    api: ApiPackage | None = None,
    *,
    title: str | None = None,
    presentation: str | ApiPresentationProfile = "help",
    max_heading_level: int | None = None,
) -> Document:
    """Build a MATLAB-style API help-book document.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package is collected from the current environment.
        title: Optional document title. Defaults to ``"{api.name} API
            Reference"``.
        presentation: API presentation profile used for object help pages.
        max_heading_level: Optional deepest heading level to render.

    Returns:
        API help-book document built through ``ApiPackage.to_help_book``.

    Examples:
        Render the collected package as a user-facing API reference bundle:

        ```python
        from examples.api_objects_example.main import (
            build_help_book_document,
            collect_oodocs_api,
        )

        api = collect_oodocs_api()
        document = build_help_book_document(api, presentation="help", max_heading_level=3)
        document.save_all(
            "artifacts/api-objects-example",
            stem="oodocs-api-reference",
        )
        ```
    """

    api = api or collect_oodocs_api()
    return api.to_help_book(
        title=title or f"{api.name} API Reference",
        presentation=presentation,
        include_coverage=True,
        max_heading_level=max_heading_level,
    )


def build_composition_demo_document(
    api: ApiPackage | None = None,
    coverage: ApiCoverageResult | None = None,
) -> Document:
    """Build a document assembled from parsed API objects.

    Args:
        api: Optional pre-collected API package.
        coverage: Optional pre-computed coverage result for ``api``.

    Returns:
        OODocs document that combines selected API object sections, a focused
        module chapter, a function summary table, and coverage evidence.

    Examples:
        Build a composable document from the same parsed API object tree:

        ```python
        from examples.api_objects_example.main import (
            build_composition_demo_document,
            collect_oodocs_api,
        )
        from oodocs.apidoc import check_api_docs

        api = collect_oodocs_api()
        coverage = check_api_docs(api)
        document = build_composition_demo_document(api, coverage)
        document.save_all(
            "artifacts/api-objects-example",
            stem="oodocs-api-object-composition",
        )
        ```
    """

    api = api or collect_oodocs_api()
    coverage = coverage or check_api_docs(api)
    classes = api.select_objects(kind="class", module_prefix="oodocs.components")[:3]
    if not classes:
        classes = api.select_objects(kind="class")[:3]
    functions = api.select_objects(kind="function")[:10]
    focused_module = _focused_module_for_example(api)

    chapters = [
        Chapter(
            "Selected Classes",
            Paragraph("These sections are regular OODocs blocks created from ApiObject instances."),
            *[obj.to_section(level=2, presentation="compact") for obj in classes],
        ),
    ]
    if focused_module is not None:
        chapters.append(
            focused_module.to_chapter(
                title=f"Focused Module: {focused_module.name}",
                presentation="manual",
                max_heading_level=3,
            )
        )
    chapters.extend(
        [
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
        ]
    )
    return Document("OODocs API Object Composition", *chapters)


def _focused_module_for_example(api: ApiPackage):
    """Return a representative module for the composable example."""

    modules_with_objects = [module for module in api.modules if list(module.iter_objects())]
    if not modules_with_objects:
        return None
    return next(
        (
            module
            for module in modules_with_objects
            if module.name.endswith(".core") or module.name.endswith(".components")
        ),
        modules_with_objects[0],
    )


def save_sidecars(
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
        Mapping with ``api_object_tree_json``, ``api_coverage_json``, and
        ``api_coverage_csv`` output paths.

    Examples:
        Build a small evidence bundle beside rendered API documents:

        ```python
        from oodocs.apidoc import check_api_docs, collect_api
        from examples.api_objects_example.main import save_sidecars

        api = collect_api("oodocs", public_policy="__all__")
        coverage = check_api_docs(api, fail_under=0.90)
        sidecars = save_sidecars(api, coverage, "artifacts/api-objects-example")
        ```
    """

    sidecar_dir = Path(output_dir)
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    return {
        "api_object_tree_json": api.save_json(
            sidecar_dir / f"{API_OBJECT_TREE_STEM}.json"
        ),
        "api_coverage_json": coverage.save_json(
            sidecar_dir / f"{API_COVERAGE_STEM}.json"
        ),
        "api_coverage_csv": coverage.save_csv(
            sidecar_dir / f"{API_COVERAGE_STEM}.csv"
        ),
    }


def render_apidoc_example_bundle(
    api: ApiPackage | None = None,
    coverage: ApiCoverageResult | None = None,
    output_dir: str | Path = ARTIFACT_DIR,
    *,
    target: str | Path = "oodocs",
    config: ApiHelpBookConfig | ApiCollectConfig | None = None,
    public_policy: str | None = None,
    collector: str | None = None,
    docstring_style: str | ApiDocstringParser | None = None,
    presentation: str | ApiPresentationProfile | None = None,
    max_heading_level: int | None = None,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> dict[str, Path]:
    """Render the API reference and object-composition example bundle.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package or ``target`` is collected from the current environment.
        coverage: Optional pre-computed coverage result for ``api``.
        output_dir: Directory that receives rendered documents and sidecars.
        target: Importable package/module name, Python file, package directory,
            or repository checkout collected when ``api`` is omitted.
        config: Optional build or collection config. Build configs provide the
            collection settings plus default formats and max level.
        public_policy: Public boundary used when collecting ``target``.
        collector: Collector backend used when collecting ``target``.
        docstring_style: Docstring parser style or reusable parser object used
            when collecting ``target``.
        presentation: Optional presentation profile for the API help book.
            Defaults to ``"help"``.
        max_heading_level: Optional deepest heading level to render in the API help
            book.
        output_formats: Optional subset of formats passed to
            ``Document.save_all``. Defaults to build config output formats or
            all supported formats.
        verbose: Whether to print major collection and rendering steps.

    Returns:
        Mapping containing DOCX/PDF/HTML paths for the API help book, DOCX/PDF
        /HTML paths for the composable API-object document, and API object tree
        JSON plus coverage JSON/CSV sidecar paths.

    Examples:
        Render the complete OODocs API reference and composable example bundle:

        ```python
        from examples.api_objects_example.main import render_apidoc_example_bundle
        from oodocs.apidoc import ApiHelpBookConfig

        outputs = render_apidoc_example_bundle(
            target=".",
            output_dir="artifacts/api-objects-example",
            config=ApiHelpBookConfig.from_pyproject("."),
            verbose=True,
        )
        help_book_html = outputs["help_book_html"]
        ```
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    build_config: ApiHelpBookConfig | None = None
    collect_config: ApiCollectConfig | None = None
    if isinstance(config, ApiHelpBookConfig):
        build_config = config
        collect_config = config.collection
    elif isinstance(config, ApiCollectConfig):
        collect_config = config

    effective_presentation = presentation or "help"
    if max_heading_level is not None:
        effective_max_heading_level = max_heading_level
    elif build_config is not None:
        effective_max_heading_level = build_config.max_heading_level
    else:
        effective_max_heading_level = None
    effective_formats = output_formats or (build_config.output_formats if build_config else None)

    if api is None:
        _log(f"Collecting API objects from {target!s}...", verbose=verbose)
        api = collect_target_api(
            target,
            config=collect_config,
            public_policy=public_policy,
            collector=collector,
            docstring_style=docstring_style,
        )
    if coverage is None:
        _log("Checking API documentation coverage...", verbose=verbose)
        coverage = check_api_docs(api)

    save_kwargs: dict[str, object] = {"verbose": verbose}
    if effective_formats is not None:
        save_kwargs["formats"] = tuple(effective_formats)

    _log("Building API help book...", verbose=verbose)
    help_book = build_help_book_document(
        api,
        presentation=effective_presentation,
        max_heading_level=effective_max_heading_level,
    )
    _log("Rendering API help book...", verbose=verbose)
    help_book_outputs = help_book.save_all(
        output_path,
        stem=HELP_BOOK_STEM,
        **save_kwargs,
    )

    _log("Building composable API-object document...", verbose=verbose)
    document = build_composition_demo_document(api, coverage)
    _log("Rendering composable API-object document...", verbose=verbose)
    composition_outputs = document.save_all(
        output_path,
        stem=API_OBJECT_COMPOSITION_STEM,
        **save_kwargs,
    )

    _log("Writing API and coverage sidecars...", verbose=verbose)
    outputs: dict[str, Path] = {
        f"help_book_{output_format}": path
        for output_format, path in help_book_outputs.items()
    }
    outputs.update(
        {
            f"object_composition_{output_format}": path
            for output_format, path in composition_outputs.items()
        }
    )
    outputs.update(save_sidecars(api, coverage, output_path))
    return outputs


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the API objects example."""

    parser = argparse.ArgumentParser(
        description=(
            "Render MATLAB-style API help pages and API object sidecars "
            "for a Python target."
        )
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
        "--config",
        help="Optional apidoc rendering config JSON, pyproject.toml, or project root.",
    )
    parser.add_argument(
        "--collector",
        help="Collector backend passed to collect_api, such as auto, griffe, or inspect.",
    )
    parser.add_argument(
        "--public-policy",
        help="Public API policy passed to collect_api.",
    )
    parser.add_argument(
        "--docstring-style",
        help="Docstring style or parser name passed to collect_api.",
    )
    parser.add_argument(
        "--outputs",
        action="append",
        dest="outputs",
        help="Output format to render. Repeat for multiple formats.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Render the API help-book example and sidecars.

    Args:
        argv: Optional argument list. Defaults to command-line arguments.

    Examples:
        Run the example for the current repository and render only HTML:

        ```python
        from examples.api_objects_example.main import main

        main([".", "--outputs", "html", "--out", "artifacts/api-objects-example"])
        ```
    """

    args = _parse_args(argv)
    build_config = (
        ApiHelpBookConfig.load_file(args.config, target=args.target)
        if args.config
        else None
    )
    outputs = render_apidoc_example_bundle(
        output_dir=args.out,
        target=args.target,
        config=build_config,
        public_policy=args.public_policy,
        collector=args.collector,
        docstring_style=args.docstring_style,
        output_formats=args.outputs,
        verbose=not args.quiet,
    )
    for path in outputs.values():
        print(f"Wrote {path}", flush=True)


if __name__ == "__main__":
    main()
