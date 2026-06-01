"""Document root object and renderer entry points."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, TYPE_CHECKING

from docscriptor.compatibility import normalize_output_format, normalize_output_formats
from docscriptor.components.base import BlockInput, Body
from docscriptor.components.inline import Text
from docscriptor.components.people import Author, AuthorInput, coerce_authors
from docscriptor.components.positioning import PositionedItem, coerce_positioned_items
from docscriptor.components.references import CitationLibrary, CitationSource, coerce_citation_library
from docscriptor.core import PathLike
from docscriptor.layout.theme import Theme
from docscriptor.settings import DocumentSettings

if TYPE_CHECKING:
    from docscriptor.validation import ValidationResult


@dataclass(slots=True, init=False)
class Document:
    """Top-level renderable document.

    Args:
        title: Document title rendered at the top of the output.
        *children: Top-level blocks. Mutually exclusive with ``body=...``.
        body: Optional pre-built ``Body`` container.
        page_items: Optional page-positioned drawing items rendered independently
            of the text flow.
        settings: Optional grouped document metadata and rendering settings.
        citations: Bibliography metadata supplied as a library, a sequence of
            ``CitationSource`` objects, or BibTeX text.
    """

    title: str
    body: Body
    settings: DocumentSettings
    citations: CitationLibrary

    def __init__(
        self,
        title: str,
        *children: BlockInput,
        body: Body | None = None,
        page_items: Sequence[PositionedItem] | None = None,
        settings: DocumentSettings | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
    ) -> None:
        if body is not None and children:
            raise ValueError("Pass either body=... or positional blocks, not both")

        self.title = title
        self.body = body if body is not None else Body(*children)
        self.settings = settings or DocumentSettings()
        if page_items is not None:
            self.settings.page_items = coerce_positioned_items(page_items)
        self.citations = coerce_citation_library(citations)

    @classmethod
    def from_markdown(
        cls,
        source: str,
        *,
        title: str | None = None,
        settings: DocumentSettings | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        numbered: bool = True,
        toc: bool | None = None,
        heading_level_shift: int = 0,
    ) -> Document:
        """Create a document from Markdown text."""

        from docscriptor.importers.markdown import from_markdown

        return from_markdown(
            source,
            title=title,
            settings=settings,
            citations=citations,
            numbered=numbered,
            toc=toc,
            heading_level_shift=heading_level_shift,
        )

    @classmethod
    def from_ipynb(
        cls,
        source: object,
        *,
        title: str | None = None,
        settings: DocumentSettings | None = None,
        citations: CitationLibrary | Sequence[CitationSource] | str | None = None,
        include_outputs: bool = True,
        include_code: bool = True,
        include_markdown: bool = True,
        include_raw: bool = True,
        code_language: str | None = None,
    ) -> Document:
        """Create a document from a Jupyter notebook."""

        from docscriptor.importers.notebook import from_ipynb

        return from_ipynb(
            source,
            title=title,
            settings=settings,
            citations=citations,
            include_outputs=include_outputs,
            include_code=include_code,
            include_markdown=include_markdown,
            include_raw=include_raw,
            code_language=code_language,
        )

    @property
    def author(self) -> str | None:
        return self.settings.resolved_author()

    @author.setter
    def author(self, value: str | None) -> None:
        self.settings.author = value

    @property
    def summary(self) -> str | None:
        return self.settings.summary

    @summary.setter
    def summary(self, value: str | None) -> None:
        self.settings.summary = value

    @property
    def subtitle(self) -> list[Text] | None:
        return self.settings.subtitle

    @subtitle.setter
    def subtitle(self, value: list[Text] | None) -> None:
        self.settings.subtitle = value

    @property
    def authors(self) -> tuple[Author, ...]:
        return self.settings.authors

    @authors.setter
    def authors(self, value: Sequence[AuthorInput]) -> None:
        self.settings.authors = coerce_authors(value)

    @property
    def cover_page(self) -> bool:
        return self.settings.cover_page

    @cover_page.setter
    def cover_page(self, value: bool) -> None:
        self.settings.cover_page = value

    @property
    def unit(self) -> str:
        return self.settings.unit

    @unit.setter
    def unit(self, value: str) -> None:
        from docscriptor.core import normalize_length_unit

        self.settings.unit = normalize_length_unit(value)

    def get_page_width(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        return self.settings.get_page_width(scale, unit=unit)

    def get_page_height(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        return self.settings.get_page_height(scale, unit=unit)

    def get_text_width(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        return self.settings.get_text_width(scale, unit=unit)

    def get_text_height(self, scale: float = 1.0, *, unit: str | None = None) -> float:
        return self.settings.get_text_height(scale, unit=unit)

    @property
    def theme(self) -> Theme:
        return self.settings.theme

    @theme.setter
    def theme(self, value: Theme) -> None:
        self.settings.theme = value

    def split_top_level_children(self) -> tuple[list[object], list[object]]:
        """Split top-level blocks into front matter and main matter.

        Front matter is defined as every top-level block that appears before the
        first numbered part or level-1 heading.
        """

        for index, child in enumerate(self.body.children):
            level = getattr(child, "level", None)
            numbered = getattr(child, "numbered", False)
            if level in {0, 1} and numbered:
                return self.body.children[:index], self.body.children[index:]
        return list(self.body.children), []

    def validate(
        self,
        *,
        raise_on_error: bool = False,
        formats: Iterable[str] | None = None,
    ) -> ValidationResult:
        """Validate the document tree and return a structured result."""

        from docscriptor.validation import validate_document

        return validate_document(
            self,
            raise_on_error=raise_on_error,
            formats=formats,
        )

    def _ensure_valid(self, formats: Iterable[str]) -> None:
        from docscriptor.validation import DocumentValidationError

        result = self.validate(formats=formats)
        if not result.ok_for(formats):
            raise DocumentValidationError(result, formats=formats)

    def save_docx(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document to DOCX and return the output path."""

        if validate:
            self._ensure_valid(("docx",))

        from docscriptor.renderers.docx import DocxRenderer

        return DocxRenderer().render(self, path)

    def save_pdf(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document to PDF and return the output path."""

        if validate:
            self._ensure_valid(("pdf",))

        from docscriptor.renderers.pdf import PdfRenderer

        return PdfRenderer().render(self, path)

    def save_html(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document to HTML and return the output path."""

        if validate:
            self._ensure_valid(("html",))

        from docscriptor.renderers.html import HtmlRenderer

        return HtmlRenderer().render(self, path)

    def save(self, path: PathLike, *, validate: bool = True) -> Path:
        """Render the document using the output path extension.

        Supported extensions are ``.docx``, ``.pdf``, and ``.html``. The
        format-specific methods remain available when code wants to be explicit,
        but this helper keeps first scripts small and readable.
        """

        output_format = normalize_output_format(Path(path).suffix)
        if output_format == "docx":
            return self.save_docx(path, validate=validate)
        if output_format == "pdf":
            return self.save_pdf(path, validate=validate)
        return self.save_html(path, validate=validate)

    def save_all(
        self,
        output_dir: PathLike,
        *,
        stem: str | None = None,
        formats: Sequence[str] = ("docx", "pdf", "html"),
        validate: bool = True,
    ) -> dict[str, Path]:
        """Render the document to multiple output formats.

        Args:
            output_dir: Directory where rendered files should be written.
            stem: Base filename without extension. Defaults to a filename-safe
                version of the document title.
            formats: Iterable of output formats. Supported values are
                ``"docx"``, ``"pdf"``, and ``"html"`` with or without a
                leading dot.

        Returns:
            A mapping from normalized format name to the written path.
        """

        directory = Path(output_dir)
        output_stem = stem or self._default_output_stem()
        normalized_formats = normalize_output_formats(formats)
        if validate:
            self._ensure_valid(normalized_formats)

        outputs: dict[str, Path] = {}
        for output_format in normalized_formats:
            outputs[output_format] = self.save(
                directory / f"{output_stem}.{output_format}",
                validate=False,
            )
        return outputs

    def _default_output_stem(self) -> str:
        pieces: list[str] = []
        previous_was_separator = False
        for character in self.title.strip().lower():
            if character.isalnum():
                pieces.append(character)
                previous_was_separator = False
            elif not previous_was_separator:
                pieces.append("-")
                previous_was_separator = True
        stem = "".join(pieces).strip("-")
        return stem or "document"
