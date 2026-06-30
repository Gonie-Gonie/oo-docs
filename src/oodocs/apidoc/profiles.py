"""Presentation profiles for API documentation objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from oodocs.apidoc.model import ApiPresentationProfileName


_ALLOWED_PARAMETER_COLUMNS = {
    "name",
    "type",
    "default",
    "required",
    "description",
    "source",
}


@dataclass(frozen=True, slots=True)
class ApiPresentationProfile:
    """Block-composition policy for API object rendering.

    A profile does not target a specific output format. It controls how much of
    a normalized API object is expanded into renderer-neutral OODocs blocks.

    Attributes:
        name: Stable profile name.
        include_signature: Whether to include a signature code block.
        include_description: Whether to include summary and description text.
        include_parameters: Whether to include a parameter table.
        include_returns: Whether to include returns/yields documentation.
        include_exceptions: Whether to include an exception table.
        include_examples: Whether to include examples.
        include_see_also: Whether to include related API references.
        include_notes: Whether to include general docstring notes.
        include_warnings: Whether to include warning notes.
        include_renderer_notes: Whether to include renderer-specific notes.
        include_source: Whether to include source file and line information.
        include_member_summary: Whether class/module members get a summary
            table.
        include_member_sections: Whether class/module members get nested
            sections.
        parameter_columns: Columns used for parameter tables.
        max_description_chars: Optional truncation limit for long descriptions.
        max_examples: Optional maximum number of examples to render.
        prefer_editable_tables: Whether tables should be favored over compact
            prose in review output.
        include_review_notes: Whether to add reviewer note blocks beside API
            objects.
        review_note_text: Optional reviewer note body used when review notes
            are enabled.
        review_note_author: Optional author label for generated inline
            comments.
        review_note_initials: Optional initials for generated inline comments.
        max_signature_width: Optional maximum line width for rendered
            signature code blocks.
        max_signature_lines: Optional maximum number of rendered signature
            lines. Long signatures are truncated with an ellipsis after
            wrapping.
        signature_wrap_indent: Indentation used for wrapped signature
            parameters.

    Examples:
        Use a compact profile when embedding API notes into a larger document:

        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.profiles import ApiPresentationProfile

        api = collect_api("oodocs", collector="auto")
        section = api.find_object("oodocs.Document").to_section(
            presentation=ApiPresentationProfile.compact()
        )
        ```
    """

    name: ApiPresentationProfileName
    include_signature: bool = True
    include_description: bool = True
    include_parameters: bool = True
    include_returns: bool = True
    include_exceptions: bool = True
    include_examples: bool = True
    include_see_also: bool = True
    include_notes: bool = True
    include_warnings: bool = True
    include_renderer_notes: bool = True
    include_source: bool = True
    include_member_summary: bool = True
    include_member_sections: bool = True
    parameter_columns: tuple[str, ...] = ("name", "type", "default", "description")
    max_description_chars: int | None = None
    max_examples: int | None = None
    prefer_editable_tables: bool = True
    include_review_notes: bool = False
    review_note_text: str | None = None
    review_note_author: str | None = None
    review_note_initials: str | None = None
    max_signature_width: int | None = None
    max_signature_lines: int | None = None
    signature_wrap_indent: str = "    "

    def __post_init__(self) -> None:
        """Normalize and validate profile options."""

        normalized_columns = tuple(
            str(column).strip().lower() for column in self.parameter_columns
        )
        invalid = [
            column
            for column in normalized_columns
            if column not in _ALLOWED_PARAMETER_COLUMNS
        ]
        if invalid:
            raise ValueError(
                f"Unsupported API parameter columns: {', '.join(invalid)}"
            )
        object.__setattr__(self, "parameter_columns", normalized_columns)

    @classmethod
    def reference(cls) -> ApiPresentationProfile:
        """Return the full API reference profile.

        Returns:
            Profile that renders full signatures, details, examples, member
            summaries, and nested member sections.

        Examples:
            ```python
            profile = ApiPresentationProfile.reference()
            ```
        """

        return cls(name="reference")

    @classmethod
    def help(cls) -> ApiPresentationProfile:
        """Return the per-symbol API help page profile.

        Returns:
            Profile that favors compact MATLAB-style help pages with one
            runnable example, concise parameter tables, and source metadata as
            supporting information.

        Examples:
            ```python
            from oodocs.apidoc import ApiPresentationProfile, collect_api

            api = collect_api("oodocs", public_policy="__all__")
            doc = api.to_help_book(presentation=ApiPresentationProfile.help())
            ```
        """

        return cls(
            name="help",
            include_description=True,
            include_examples=True,
            include_see_also=True,
            include_notes=False,
            include_warnings=True,
            include_renderer_notes=False,
            include_source=True,
            include_member_summary=True,
            include_member_sections=False,
            parameter_columns=("name", "type", "default", "description"),
            max_description_chars=360,
            max_examples=1,
            max_signature_width=88,
            max_signature_lines=16,
        )

    @classmethod
    def compact(cls) -> ApiPresentationProfile:
        """Return a compact profile for summaries and indexes.

        Returns:
            Profile that truncates long descriptions, renders at most one
            example, and skips nested member detail sections.

        Examples:
            Use compact rendering for a release evidence appendix:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api
            from oodocs.apidoc.profiles import ApiPresentationProfile

            api = collect_api(".")
            functions = api.select_functions()
            doc = Document(
                "Release Evidence",
                Chapter(
                    "Function Summary",
                    api.to_summary_table(
                        functions,
                        presentation=ApiPresentationProfile.compact(),
                    ),
                ),
            )
            ```
        """

        return cls(
            name="compact",
            include_member_sections=False,
            include_notes=False,
            max_signature_width=88,
            max_signature_lines=24,
            max_description_chars=180,
            max_examples=1,
            parameter_columns=("name", "type", "description"),
        )

    @classmethod
    def manual(cls) -> ApiPresentationProfile:
        """Return a profile tuned for manual authored documents.

        Returns:
            Profile that keeps examples and see-also content prominent while
            remaining suitable for insertion into an existing chapter.

        Examples:
            Insert selected API objects into a hand-authored guide:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api
            from oodocs.apidoc.profiles import ApiPresentationProfile

            api = collect_api(".")
            classes = api.select_objects(kind="class", module_prefix="mypkg.widgets")
            doc = Document(
                "Widget Guide",
                Chapter(
                    "Reference Notes",
                    *[
                        item.to_section(level=2, presentation=ApiPresentationProfile.manual())
                        for item in classes
                    ],
                ),
            )
            ```
        """

        return cls(name="manual", include_source=False)

    @classmethod
    def evidence(cls) -> ApiPresentationProfile:
        """Return a profile for release evidence and coverage appendices.

        Returns:
            Profile that emphasizes source locations and summary tables while
            suppressing long prose and examples.

        Examples:
            Render a concise API appendix for release review:

            ```python
            from oodocs import Chapter, Document
            from oodocs.apidoc import collect_api
            from oodocs.apidoc.profiles import ApiPresentationProfile

            api = collect_api(".")
            doc = Document(
                "API Evidence",
                Chapter(
                    "Public API",
                    *api.to_sections(
                        presentation=ApiPresentationProfile.evidence(),
                        max_heading_level=2,
                    ),
                ),
            )
            ```
        """

        return cls(
            name="evidence",
            include_description=True,
            include_examples=False,
            include_see_also=False,
            include_notes=False,
            include_warnings=True,
            include_renderer_notes=True,
            include_member_sections=False,
            max_signature_width=88,
            max_signature_lines=20,
            max_description_chars=120,
            parameter_columns=("name", "type", "description"),
        )

    @classmethod
    def review(cls) -> ApiPresentationProfile:
        """Return a profile optimized for DOCX review copies.

        Returns:
            Profile that prefers editable tables and plain block structure.

        Examples:
            Build a DOCX-oriented API review copy:

            ```python
            from oodocs.apidoc import collect_api
            from oodocs.apidoc.profiles import ApiPresentationProfile

            api = collect_api(".")
            document = api.to_help_book(presentation=ApiPresentationProfile.review())
            document.save_docx("artifacts/api-review.docx")
            ```
        """

        return cls(
            name="review",
            prefer_editable_tables=True,
            include_review_notes=True,
            review_note_text=(
                "Check this API object's summary, parameters, returns, "
                "examples, renderer notes, and source location before publishing."
            ),
            review_note_author="OODocs",
            review_note_initials="API",
            max_signature_width=88,
        )

    @classmethod
    def website(cls) -> ApiPresentationProfile:
        """Return a profile optimized for HTML API pages.

        Returns:
            Profile that preserves headings, anchors, source locations, and
            navigation-friendly member summaries.

        Examples:
            Render a reference tree with stable HTML anchors:

            ```python
            from oodocs.apidoc import collect_api
            from oodocs.apidoc.profiles import ApiPresentationProfile

            api = collect_api(".")
            document = api.to_help_book(presentation=ApiPresentationProfile.website())
            document.save_html("artifacts/api/index.html")
            ```
        """

        return cls(name="website")

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-serializable mapping.

        Returns:
            Dictionary containing every profile option.

        Examples:
            Store a custom profile beside an API sidecar:

            ```python
            from oodocs.apidoc.profiles import ApiPresentationProfile

            payload = ApiPresentationProfile.compact().to_dict()
            ```
        """

        return {
            "name": self.name,
            "include_signature": self.include_signature,
            "include_description": self.include_description,
            "include_parameters": self.include_parameters,
            "include_returns": self.include_returns,
            "include_exceptions": self.include_exceptions,
            "include_examples": self.include_examples,
            "include_see_also": self.include_see_also,
            "include_notes": self.include_notes,
            "include_warnings": self.include_warnings,
            "include_renderer_notes": self.include_renderer_notes,
            "include_source": self.include_source,
            "include_member_summary": self.include_member_summary,
            "include_member_sections": self.include_member_sections,
            "parameter_columns": list(self.parameter_columns),
            "max_description_chars": self.max_description_chars,
            "max_examples": self.max_examples,
            "prefer_editable_tables": self.prefer_editable_tables,
            "include_review_notes": self.include_review_notes,
            "review_note_text": self.review_note_text,
            "review_note_author": self.review_note_author,
            "review_note_initials": self.review_note_initials,
            "max_signature_width": self.max_signature_width,
            "max_signature_lines": self.max_signature_lines,
            "signature_wrap_indent": self.signature_wrap_indent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiPresentationProfile:
        """Build a profile from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Reconstructed profile object.

        Examples:
            Reuse a profile loaded from repository-local settings:

            ```python
            from oodocs.apidoc.profiles import ApiPresentationProfile

            profile = ApiPresentationProfile.from_dict({
                "name": "compact",
                "include_member_sections": False,
                "parameter_columns": ["name", "type", "description"],
            })
            ```
        """

        values = dict(data)
        if "parameter_columns" in values:
            values["parameter_columns"] = tuple(values["parameter_columns"])  # type: ignore[arg-type]
        return cls(**values)  # type: ignore[arg-type]


_PROFILES: dict[str, ApiPresentationProfile] = {
    "reference": ApiPresentationProfile.reference(),
    "help": ApiPresentationProfile.help(),
    "compact": ApiPresentationProfile.compact(),
    "manual": ApiPresentationProfile.manual(),
    "evidence": ApiPresentationProfile.evidence(),
    "review": ApiPresentationProfile.review(),
    "website": ApiPresentationProfile.website(),
}


def register_presentation_profile(name: str, profile: ApiPresentationProfile) -> None:
    """Register a custom API documentation profile.

    Args:
        name: Profile name used by ``resolve_presentation_profile``.
        profile: Profile object to register.

    Raises:
        ValueError: If the name is empty or already registered.

    Examples:
        ```python
        from oodocs.apidoc.profiles import ApiPresentationProfile, register_presentation_profile

        register_presentation_profile("brief", ApiPresentationProfile.compact())
        ```
    """

    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("profile name must not be empty")
    if normalized in _PROFILES:
        raise ValueError(f"API documentation profile already registered: {name!r}")
    _PROFILES[normalized] = profile


def resolve_presentation_profile(presentation: str | ApiPresentationProfile = "reference") -> ApiPresentationProfile:
    """Resolve a profile name or object.

    Args:
        presentation: Profile name or already-constructed profile.

    Returns:
        Resolved profile.

    Raises:
        ValueError: If a profile name is unknown.

    Examples:
        Normalize user input before passing a profile into rendering helpers:

        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.profiles import resolve_presentation_profile

        api = collect_api(".")
        profile = resolve_presentation_profile("compact")
        table = api.to_summary_table(presentation=profile)
        ```
    """

    if isinstance(presentation, ApiPresentationProfile):
        return presentation
    normalized = presentation.strip().lower()
    try:
        return _PROFILES[normalized]
    except KeyError as exc:
        available = ", ".join(sorted(_PROFILES))
        raise ValueError(
            f"Unknown API documentation profile {presentation!r}. Available: {available}"
        ) from exc


def presentation_profile_names() -> tuple[str, ...]:
    """Return registered profile names.

    Returns:
        Sorted profile name tuple.

    Examples:
        Check whether a plugin registered a custom profile:

        ```python
        from oodocs.apidoc.profiles import presentation_profile_names

        assert "reference" in presentation_profile_names()
        ```
    """

    return tuple(sorted(_PROFILES))


def normalize_parameter_columns(columns: Sequence[str]) -> tuple[str, ...]:
    """Validate and normalize parameter table columns.

    Args:
        columns: Requested column names.

    Returns:
        Tuple of supported column names.

    Raises:
        ValueError: If an unsupported column is requested.

    Examples:
        Validate columns before building a custom profile:

        ```python
        from oodocs.apidoc.profiles import ApiPresentationProfile

        profile = ApiPresentationProfile(
            name="compact",
            parameter_columns=("name", "type", "description"),
        )
        ```
    """

    normalized = tuple(column.strip().lower() for column in columns)
    invalid = [
        column for column in normalized if column not in _ALLOWED_PARAMETER_COLUMNS
    ]
    if invalid:
        raise ValueError(f"Unsupported API parameter columns: {', '.join(invalid)}")
    return normalized


__all__ = [
    "ApiPresentationProfile",
    "presentation_profile_names",
    "register_presentation_profile",
    "resolve_presentation_profile",
]
