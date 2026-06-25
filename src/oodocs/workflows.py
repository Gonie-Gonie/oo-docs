"""High-level document loading, validation, and rendering workflows."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Iterable, Iterator

from oodocs.compatibility import OutputFormat, normalize_output_formats
from oodocs.document import Document
from oodocs.validation import ValidationResult


PYTHON_DOCUMENT_NAMES = ("document", "doc", "report")
PYTHON_FACTORY_NAMES = ("build_document", "build_report", "build")


@dataclass(frozen=True, slots=True)
class RenderedOutputs:
    """Paths written by a document rendering workflow.

    Attributes:
        outputs: Mapping from normalized output format to written file path.
    """

    outputs: dict[OutputFormat, Path]

    def __iter__(self) -> Iterator[tuple[OutputFormat, Path]]:
        """Iterate over rendered output pairs.

        Yields:
            ``(format, path)`` pairs in the underlying mapping order.
        """

        return iter(self.outputs.items())

    def __getitem__(self, output_format: str) -> Path:
        """Return the rendered path for an output format.

        Args:
            output_format: Output format name or extension.

        Returns:
            The path rendered for that format.

        Raises:
            KeyError: If the format was not rendered.
            ValueError: If the format is not supported.
        """

        normalized = normalize_output_formats((output_format,))
        return self.outputs[normalized[0]]


def load_document(
    source: str | Path,
    *,
    source_type: str | None = None,
    title: str | None = None,
    factory: str | None = None,
    chdir: bool = True,
) -> Document:
    """Load a document from Python, Markdown, or notebook source.

    Args:
        source: Source file path.
        source_type: Optional explicit type: ``"python"``, ``"markdown"``, or
            ``"notebook"``.
        title: Optional title override for imported Markdown or notebooks.
        factory: Optional factory name for Python document sources.
        chdir: Whether Python sources should execute with their directory as
            the current working directory.

    Returns:
        The loaded document.

    Raises:
        ValueError: If the source type is unsupported or the source does not
            expose a document.
    """

    source_path = Path(source)
    resolved_type = _resolve_source_type(source_path, source_type)
    if factory is not None and resolved_type != "python":
        raise ValueError("--factory is only supported for Python document sources")
    if resolved_type == "python":
        return load_python_document(source_path, factory=factory, chdir=chdir)
    if resolved_type == "markdown":
        from oodocs.importers.markdown import from_markdown_file

        return from_markdown_file(source_path, title=title)
    if resolved_type == "notebook":
        from oodocs.importers.notebook import from_ipynb

        return from_ipynb(source_path, title=title)
    raise ValueError(f"Unsupported document source type: {resolved_type!r}")


def load_python_document(
    source: str | Path,
    *,
    factory: str | None = None,
    chdir: bool = True,
) -> Document:
    """Load a document object from a Python file.

    Args:
        source: Python file path.
        factory: Optional function or variable name to read from the module.
        chdir: Whether to execute the module from its containing directory.

    Returns:
        The document exposed by the Python source.

    Raises:
        FileNotFoundError: If ``source`` does not exist.
        ValueError: If no document is exposed by the module.
        AttributeError: If an explicit factory name is missing.
        TypeError: If the selected candidate is not a document.
    """

    source_path = Path(source).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Python document source not found: {source_path}")

    with _optional_chdir(source_path.parent, enabled=chdir):
        module = _load_python_module(source_path)

    document = _document_from_module(module, factory=factory)
    if document is None:
        candidates = ", ".join(PYTHON_DOCUMENT_NAMES + PYTHON_FACTORY_NAMES)
        raise ValueError(
            f"{source_path} did not expose a Document. Define one of: {candidates}; "
            "or pass --factory NAME."
        )
    return document


def render_document(
    document: Document,
    output_dir: str | Path,
    *,
    stem: str,
    formats: Iterable[str] | None = None,
    validate: bool = True,
    verbose: bool = False,
) -> RenderedOutputs:
    """Render a document to one or more output formats.

    Args:
        document: Document to render.
        output_dir: Directory where rendered files are written.
        stem: Base output filename without extension.
        formats: Output formats to render. Defaults to all supported formats.
        validate: Whether to validate before rendering.
        verbose: Whether to print slow major rendering steps.

    Returns:
        Paths written by the render workflow.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    normalized_formats = normalize_output_formats(formats)
    outputs = document.save_all(
        output_path,
        stem=stem,
        formats=normalized_formats,
        validate=validate,
        verbose=verbose,
    )
    return RenderedOutputs(outputs)


def build_python_document(
    source: str | Path,
    output_dir: str | Path,
    *,
    formats: Iterable[str] | None = None,
    stem: str | None = None,
    factory: str | None = None,
    validate: bool = True,
    chdir: bool = True,
    verbose: bool = False,
) -> RenderedOutputs:
    """Load a Python-authored document and render it.

    Args:
        source: Python source file path.
        output_dir: Directory where rendered files are written.
        formats: Output formats to render. Defaults to all supported formats.
        stem: Base output filename without extension. Defaults to the source
            file stem.
        factory: Optional function or variable name to read from the module.
        validate: Whether to validate before rendering.
        chdir: Whether to execute the source from its containing directory.
        verbose: Whether to print slow major rendering steps.

    Returns:
        Paths written by the build workflow.
    """

    source_path = Path(source).resolve()
    output_path = Path(output_dir).resolve()
    with _optional_chdir(source_path.parent, enabled=chdir):
        document = load_python_document(source_path, factory=factory, chdir=False)
        return render_document(
            document,
            output_path,
            stem=stem or source_path.stem,
            formats=formats,
            validate=validate,
            verbose=verbose,
        )


def convert_source(
    source: str | Path,
    output_dir: str | Path | None = None,
    *,
    formats: Iterable[str] | None = None,
    stem: str | None = None,
    title: str | None = None,
    validate: bool = True,
    verbose: bool = False,
) -> RenderedOutputs:
    """Convert Markdown or notebook source into rendered document outputs.

    Args:
        source: Markdown or notebook source path.
        output_dir: Directory where rendered files are written. Defaults to the
            source file directory.
        formats: Output formats to render. Defaults to all supported formats.
        stem: Base output filename without extension. Defaults to the source
            file stem.
        title: Optional document title override.
        validate: Whether to validate before rendering.
        verbose: Whether to print slow major rendering steps.

    Returns:
        Paths written by the conversion workflow.
    """

    source_path = Path(source)
    document = load_document(source_path, title=title)
    return render_document(
        document,
        output_dir or source_path.parent,
        stem=stem or source_path.stem,
        formats=formats,
        validate=validate,
        verbose=verbose,
    )


def validate_source(
    source: str | Path,
    *,
    source_type: str | None = None,
    title: str | None = None,
    factory: str | None = None,
    formats: Iterable[str] | None = None,
    chdir: bool = True,
) -> ValidationResult:
    """Load a source document and return its validation result.

    Args:
        source: Source file path.
        source_type: Optional explicit type: ``"python"``, ``"markdown"``, or
            ``"notebook"``.
        title: Optional title override for imported Markdown or notebooks.
        factory: Optional factory name for Python document sources.
        formats: Output formats to validate for. Defaults to all formats.
        chdir: Whether Python sources should execute with their directory as
            the current working directory.

    Returns:
        Validation issues for the loaded source document.
    """

    source_path = Path(source)
    resolved_type = _resolve_source_type(source_path, source_type)
    if factory is not None and resolved_type != "python":
        raise ValueError("--factory is only supported for Python document sources")
    if resolved_type == "python":
        resolved_source = source_path.resolve()
        with _optional_chdir(resolved_source.parent, enabled=chdir):
            document = load_python_document(
                resolved_source,
                factory=factory,
                chdir=False,
            )
            return document.validate(formats=formats)

    document = load_document(
        source_path,
        source_type=resolved_type,
        title=title,
        factory=None,
        chdir=chdir,
    )
    return document.validate(formats=formats)


def _resolve_source_type(source_path: Path, source_type: str | None) -> str:
    if source_type is not None:
        normalized = source_type.lower().strip()
        aliases = {
            "py": "python",
            "python": "python",
            "md": "markdown",
            "markdown": "markdown",
            "ipynb": "notebook",
            "notebook": "notebook",
        }
        if normalized in aliases:
            return aliases[normalized]
        raise ValueError(f"Unsupported source type: {source_type!r}")

    suffix = source_path.suffix.lower()
    # Inference intentionally stays extension-based so CLI behavior is stable
    # and does not require opening large notebooks just to choose a loader.
    if suffix == ".py":
        return "python"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".ipynb":
        return "notebook"
    raise ValueError(
        f"Cannot infer document source type from {source_path}. "
        "Use --type python, markdown, or notebook."
    )


def _load_python_module(source_path: Path) -> ModuleType:
    module_name = f"_oodocs_cli_{source_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load Python document source: {source_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def _document_from_module(module: ModuleType, *, factory: str | None) -> Document | None:
    if factory is not None:
        value = getattr(module, factory, None)
        if value is None:
            raise AttributeError(f"Python document source has no factory named {factory!r}")
        return _coerce_document_candidate(value, name=factory)

    for name in PYTHON_DOCUMENT_NAMES:
        if hasattr(module, name):
            document = _coerce_document_candidate(getattr(module, name), name=name)
            if document is not None:
                return document
    for name in PYTHON_FACTORY_NAMES:
        if hasattr(module, name):
            document = _coerce_document_candidate(getattr(module, name), name=name)
            if document is not None:
                return document
    return None


def _coerce_document_candidate(value: object, *, name: str) -> Document | None:
    candidate = value() if callable(value) else value
    if isinstance(candidate, Document):
        return candidate
    if candidate is None:
        return None
    raise TypeError(f"{name} must be an oodocs.Document or return one")


@contextmanager
def _optional_chdir(directory: Path, *, enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    import os

    previous = Path.cwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(previous)


__all__ = [
    "PYTHON_DOCUMENT_NAMES",
    "PYTHON_FACTORY_NAMES",
    "RenderedOutputs",
    "build_python_document",
    "convert_source",
    "load_document",
    "load_python_document",
    "render_document",
    "validate_source",
]
