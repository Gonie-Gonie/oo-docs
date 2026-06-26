"""Build composable API-object documentation examples."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import (
    ApiBuildConfig,
    ApiCollectConfig,
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
        document = api.to_document(profile="compact")
        ```

        Reuse a repository-local config so the example and release workflow
        render the same public boundary:

        ```python
        from examples.api_objects_example.main import collect_target_api
        from oodocs.apidoc import ApiBuildConfig

        build = ApiBuildConfig.from_pyproject(".")
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
        full_reference = api.to_document("OODocs Full API Reference")
        composable_classes = api.select_objects(kind="class", module_prefix="oodocs.components")
        ```
    """

    return collect_target_api("oodocs", public_policy="__all__", collector="auto")


def build_full_package_document(
    api: ApiPackage | None = None,
    *,
    title: str | None = None,
    profile: str = "compact",
    max_level: int | None = None,
) -> Document:
    """Build a full package API reference document.

    Args:
        api: Optional pre-collected API package. When omitted, the OODocs
            package is collected from the current environment.
        title: Optional document title. Defaults to ``"{api.name} API
            Reference"``.
        profile: API presentation profile used for object sections.
        max_level: Optional deepest heading level to render.

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
        document = build_full_package_document(api, profile="compact", max_level=3)
        document.save_all(
            "artifacts/api-objects-example",
            stem="oodocs-full-api-reference",
        )
        ```
    """

    api = api or collect_oodocs_api()
    return api.to_document(
        title=title or f"{api.name} API Reference",
        profile=profile,
        include_coverage=True,
        include_modules=True,
        max_level=max_level,
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
        OODocs document that combines selected API object sections, a focused
        module chapter, a function summary table, and coverage evidence.

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
    classes = api.select_objects(kind="class", module_prefix="oodocs.components")[:3]
    if not classes:
        classes = api.select_objects(kind="class")[:3]
    functions = api.select_objects(kind="function")[:10]
    focused_module = _focused_module_for_example(api)

    chapters = [
        Chapter(
            "Selected Classes",
            Paragraph("These sections are regular OODocs blocks created from ApiObject instances."),
            *[obj.to_section(level=2, profile="compact") for obj in classes],
        ),
    ]
    if focused_module is not None:
        chapters.append(
            focused_module.to_chapter(
                title=f"Focused Module: {focused_module.name}",
                profile="manual",
                max_level=3,
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
        Mapping with ``api_json``, ``coverage_json``, and ``coverage_csv``
        output paths.

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
        "api_json": api.save_json(sidecar_dir / f"{COMPOSITION_STEM}.json"),
        "coverage_json": coverage.save_json(sidecar_dir / f"{COVERAGE_STEM}.json"),
        "coverage_csv": coverage.save_csv(sidecar_dir / f"{COVERAGE_STEM}.csv"),
    }


def render_api_objects_example(
    api: ApiPackage | None = None,
    coverage: ApiCoverageResult | None = None,
    output_dir: str | Path = ARTIFACT_DIR,
    *,
    target: str | Path = "oodocs",
    config: ApiBuildConfig | ApiCollectConfig | None = None,
    public_policy: str | None = None,
    collector: str | None = None,
    docstring_style: str | ApiDocstringParser | None = None,
    profile: str | None = None,
    max_level: int | None = None,
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
        config: Optional build or collection config. Build configs provide the
            collection settings plus default profile, formats, and max level.
        public_policy: Public boundary used when collecting ``target``.
        collector: Collector backend used when collecting ``target``.
        docstring_style: Docstring parser style or reusable parser object used
            when collecting ``target``.
        profile: Optional presentation profile for the full package reference.
            Defaults to the build config profile or ``"compact"``.
        max_level: Optional deepest heading level to render in the full package
            reference.
        formats: Optional subset of formats passed to ``Document.save_all``.
            Defaults to build config formats or all supported formats.
        verbose: Whether to print major collection and rendering steps.

    Returns:
        Mapping containing DOCX/PDF/HTML paths for the full package reference,
        DOCX/PDF/HTML paths for the composable API-object document, and API
        JSON plus coverage JSON/CSV sidecar paths.

    Examples:
        Render the complete OODocs API reference and composable example bundle:

        ```python
        from examples.api_objects_example.main import render_api_objects_example
        from oodocs.apidoc import ApiBuildConfig

        outputs = render_api_objects_example(
            target=".",
            output_dir="artifacts/api-objects-example",
            config=ApiBuildConfig.from_pyproject("."),
            verbose=True,
        )
        full_reference_html = outputs["full_reference_html"]
        ```
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    build_config: ApiBuildConfig | None = None
    collect_config: ApiCollectConfig | None = None
    if isinstance(config, ApiBuildConfig):
        build_config = config
        collect_config = config.collection
    elif isinstance(config, ApiCollectConfig):
        collect_config = config

    effective_profile = profile or (build_config.profile if build_config else "compact")
    if max_level is not None:
        effective_max_level = max_level
    elif build_config is not None:
        effective_max_level = build_config.max_level
    else:
        effective_max_level = None
    effective_formats = formats or (build_config.output_formats if build_config else None)

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

    _log("Building full package API reference...", verbose=verbose)
    full_reference = build_full_package_document(
        api,
        profile=effective_profile,
        max_level=effective_max_level,
    )
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
    outputs.update(save_sidecars(api, coverage, output_path))
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
        "--config",
        help="Optional apidoc build config JSON, pyproject.toml, or project root.",
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
    """Render the API object example and sidecars.

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
        ApiBuildConfig.load_file(args.config, target=args.target)
        if args.config
        else None
    )
    outputs = render_api_objects_example(
        output_dir=args.out,
        target=args.target,
        config=build_config,
        public_policy=args.public_policy,
        collector=args.collector,
        docstring_style=args.docstring_style,
        formats=args.outputs,
        verbose=not args.quiet,
    )
    for path in outputs.values():
        print(f"Wrote {path}", flush=True)


if __name__ == "__main__":
    main()
