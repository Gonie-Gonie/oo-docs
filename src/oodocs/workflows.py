"""High-level document loading, validation, and rendering workflows.

Attributes:
    PYTHON_DOCUMENT_NAMES: Candidate variable names for Python document modules.
    PYTHON_FACTORY_NAMES: Candidate factory function names for Python document
        modules.
"""

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
class OutputBundle:
    """Paths written by a document rendering workflow.

    Attributes:
        outputs: Mapping from normalized output format to written file path.

    Examples:
        Render Markdown to one format and index the result by format:

        ```python
        rendered = build_source_outputs("notes.md", "dist", outputs=("pdf",))
        print(rendered["pdf"])
        ```

        Iterate over every rendered output:

        ```python
        for output_format, path in rendered:
            print(output_format, path)
        ```

    Notes:
        Output format keys are normalized, so callers can use names or
        extensions such as ``"pdf"`` or ``".pdf"`` when indexing the result.

    See Also:
        ``save_document_outputs`` for rendering an existing ``Document`` and
        ``build_source_outputs`` for Python, Markdown, or notebook sources.
    """

    outputs: dict[OutputFormat, Path]

    @property
    def formats(self) -> tuple[OutputFormat, ...]:
        """Return normalized output formats in bundle order."""

        return tuple(self.outputs)

    @property
    def paths(self) -> tuple[Path, ...]:
        """Return rendered output paths in bundle order."""

        return tuple(self.outputs.values())

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

    def by_format(self, output_format: str) -> Path:
        """Return the rendered path for an output format.

        Args:
            output_format: Output format name or extension.

        Returns:
            The path rendered for that format.
        """

        return self[output_format]


def load_source_document(
    source: str | Path,
    *,
    source_type: str | None = None,
    title: str | None = None,
    document_factory: str | None = None,
    chdir: bool = True,
) -> Document:
    """Load a document from Python, Markdown, or notebook source.

    Args:
        source: Source file path.
        source_type: Optional explicit type: ``"python"``, ``"markdown"``, or
            ``"notebook"``.
        title: Optional title override for imported Markdown or notebooks.
        document_factory: Optional factory name for Python document sources.
        chdir: Whether Python sources should execute with their directory as
            the current working directory.

    Returns:
        The loaded document.

    Raises:
        ValueError: If the source type is unsupported or the source does not
            expose a document.

    Examples:
        ```python
        from oodocs.workflows import load_source_document

        doc = load_source_document("report.md", title="Imported Report")
        ```
    """

    source_path = Path(source)
    resolved_type = _resolve_source_type(source_path, source_type)
    if document_factory is not None and resolved_type != "python":
        raise ValueError("--document-factory is only supported for Python sources")
    if resolved_type == "python":
        return load_document_from_python(
            source_path,
            document_factory=document_factory,
            chdir=chdir,
        )
    if resolved_type == "markdown":
        from oodocs.importers.markdown import from_markdown_file

        return from_markdown_file(source_path, title=title)
    if resolved_type == "notebook":
        from oodocs.importers.notebook import from_notebook

        return from_notebook(source_path, title=title)
    raise ValueError(f"Unsupported document source type: {resolved_type!r}")


def load_document_from_python(
    source: str | Path,
    *,
    document_factory: str | None = None,
    chdir: bool = True,
) -> Document:
    """Load a document object from a Python file.

    Args:
        source: Python file path.
        document_factory: Optional function or variable name to read from the
            module.
        chdir: Whether to execute the module from its containing directory.

    Returns:
        The document exposed by the Python source.

    Raises:
        FileNotFoundError: If ``source`` does not exist.
        ValueError: If no document is exposed by the module.
        AttributeError: If an explicit factory name is missing.
        TypeError: If the selected candidate is not a document.

    Examples:
        Load a module-level ``document`` variable or explicit factory:

        ```python
        from oodocs.workflows import load_document_from_python

        doc = load_document_from_python(
            "reports/monthly.py",
            document_factory="build",
        )
        ```
    """

    source_path = Path(source).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Python document source not found: {source_path}")

    with _optional_chdir(source_path.parent, enabled=chdir):
        module = _load_python_module(source_path)

    document = _document_from_module(module, document_factory=document_factory)
    if document is None:
        candidates = ", ".join(PYTHON_DOCUMENT_NAMES + PYTHON_FACTORY_NAMES)
        raise ValueError(
            f"{source_path} did not expose a Document. Define one of: {candidates}; "
            "or pass --document-factory NAME."
        )
    return document


def save_document_outputs(
    document: Document,
    output_dir: str | Path,
    *,
    stem: str,
    outputs: Iterable[str] | None = None,
    validate: bool = True,
    verbose: bool = False,
) -> OutputBundle:
    """Render a document to one or more output formats.

    Args:
        document: Document to render.
        output_dir: Directory where rendered files are written.
        stem: Base output filename without extension.
        outputs: Output formats to render. Defaults to all supported formats.
        validate: Whether to validate before rendering.
        verbose: Whether to print slow major rendering steps.

    Returns:
        Paths written by the render workflow.

    Examples:
        ```python
        from oodocs import Document, Paragraph
        from oodocs.workflows import save_document_outputs

        rendered = save_document_outputs(
            Document("Memo", Paragraph("Ready.")),
            "dist",
            stem="memo",
            outputs=("html",),
        )
        ```
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    normalized_outputs = normalize_output_formats(outputs)
    rendered = document.save_all(
        output_path,
        stem=stem,
        formats=normalized_outputs,
        validate=validate,
        verbose=verbose,
    )
    return OutputBundle(rendered)


def build_source_outputs(
    source: str | Path,
    output_dir: str | Path,
    *,
    source_type: str | None = None,
    title: str | None = None,
    document_factory: str | None = None,
    outputs: Iterable[str] | None = None,
    stem: str | None = None,
    validate: bool = True,
    chdir: bool = True,
    verbose: bool = False,
) -> OutputBundle:
    """Load a source document and render it.

    Args:
        source: Python, Markdown, or notebook source file path.
        output_dir: Directory where rendered files are written.
        source_type: Optional explicit type: ``"python"``, ``"markdown"``, or
            ``"notebook"``.
        title: Optional title override for imported Markdown or notebooks.
        document_factory: Optional function or variable name for Python
            sources.
        outputs: Output formats to render. Defaults to all supported formats.
        stem: Base output filename without extension. Defaults to the source
            file stem.
        validate: Whether to validate before rendering.
        chdir: Whether to execute the source from its containing directory.
        verbose: Whether to print slow major rendering steps.

    Returns:
        Paths written by the build workflow.

    Examples:
        ```python
        from oodocs.workflows import build_source_outputs

        outputs = build_source_outputs(
            "reports/monthly.py",
            "dist",
            outputs=("pdf",),
        )
        ```
    """

    source_path = Path(source).resolve()
    output_path = Path(output_dir).resolve()
    resolved_type = _resolve_source_type(source_path, source_type)
    if resolved_type == "python":
        with _optional_chdir(source_path.parent, enabled=chdir):
            document = load_document_from_python(
                source_path,
                document_factory=document_factory,
                chdir=False,
            )
            return save_document_outputs(
                document,
                output_path,
                stem=stem or source_path.stem,
                outputs=outputs,
                validate=validate,
                verbose=verbose,
            )

    if document_factory is not None:
        raise ValueError("--document-factory is only supported for Python sources")
    document = load_source_document(source_path, source_type=resolved_type, title=title)
    return save_document_outputs(
        document,
        output_path,
        stem=stem or source_path.stem,
        outputs=outputs,
        validate=validate,
        verbose=verbose,
    )


def validate_source_document(
    source: str | Path,
    *,
    source_type: str | None = None,
    title: str | None = None,
    document_factory: str | None = None,
    outputs: Iterable[str] | None = None,
    chdir: bool = True,
) -> ValidationResult:
    """Load a source document and return its validation result.

    Args:
        source: Source file path.
        source_type: Optional explicit type: ``"python"``, ``"markdown"``, or
            ``"notebook"``.
        title: Optional title override for imported Markdown or notebooks.
        document_factory: Optional factory name for Python document sources.
        outputs: Output formats to validate for. Defaults to all formats.
        chdir: Whether Python sources should execute with their directory as
            the current working directory.

    Returns:
        Validation issues for the loaded source document.

    Examples:
        ```python
        from oodocs.workflows import validate_source_document

        result = validate_source_document("notes.md", outputs=("pdf",))
        assert result.ok_for(("pdf",))
        ```
    """

    source_path = Path(source)
    resolved_type = _resolve_source_type(source_path, source_type)
    if document_factory is not None and resolved_type != "python":
        raise ValueError("--document-factory is only supported for Python sources")
    if resolved_type == "python":
        resolved_source = source_path.resolve()
        with _optional_chdir(resolved_source.parent, enabled=chdir):
            document = load_document_from_python(
                resolved_source,
                document_factory=document_factory,
                chdir=False,
            )
            return document.validate(formats=outputs)

    document = load_source_document(
        source_path,
        source_type=resolved_type,
        title=title,
        document_factory=None,
        chdir=chdir,
    )
    return document.validate(formats=outputs)


def _resolve_source_type(source_path: Path, source_type: str | None) -> str:
    if source_type is not None:
        normalized = source_type.lower().strip()
        aliases = {
            "py": "python",
            "python": "python",
            "md": "markdown",
            "markdown": "markdown",
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
        "Use --source-type python, markdown, or notebook."
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


def _document_from_module(
    module: ModuleType,
    *,
    document_factory: str | None,
) -> Document | None:
    if document_factory is not None:
        value = getattr(module, document_factory, None)
        if value is None:
            raise AttributeError(
                f"Python document source has no document factory named {document_factory!r}"
            )
        return _coerce_document_candidate(value, name=document_factory)

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
    "OutputBundle",
    "PYTHON_DOCUMENT_NAMES",
    "PYTHON_FACTORY_NAMES",
    "build_source_outputs",
    "load_document_from_python",
    "load_source_document",
    "save_document_outputs",
    "validate_source_document",
]
