"""Presentation profiles for API documentation objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from oodocs.apidoc.model import ApiPresentationProfileName


@dataclass(frozen=True, slots=True)
class ApiDocProfile:
    """Block-composition policy for API object rendering.

    A profile does not target a specific output format. It controls how much of
    a normalized API object is expanded into renderer-neutral OODocs blocks.

    Attributes:
        name: Stable profile name.
        include_signature: Whether to include a signature code block.
        include_description: Whether to include summary and description text.
        include_parameters: Whether to include a parameter table.
        include_returns: Whether to include returns/yields documentation.
        include_raises: Whether to include an exception table.
        include_examples: Whether to include examples.
        include_see_also: Whether to include related API references.
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
            prose in review-style output.

    Examples:
        Use a compact profile when embedding API notes into a larger document:

        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.styles import ApiDocProfile

        api = collect_api("oodocs", collector="auto")
        section = api.find("oodocs.Document").to_section(
            profile=ApiDocProfile.compact()
        )
        ```
    """

    name: ApiPresentationProfileName
    include_signature: bool = True
    include_description: bool = True
    include_parameters: bool = True
    include_returns: bool = True
    include_raises: bool = True
    include_examples: bool = True
    include_see_also: bool = True
    include_renderer_notes: bool = True
    include_source: bool = True
    include_member_summary: bool = True
    include_member_sections: bool = True
    parameter_columns: tuple[str, ...] = ("name", "type", "default", "description")
    max_description_chars: int | None = None
    max_examples: int | None = None
    prefer_editable_tables: bool = True

    @classmethod
    def reference(cls) -> ApiDocProfile:
        """Return the full API reference profile.

        Returns:
            Profile that renders full signatures, details, examples, member
            summaries, and nested member sections.

        Examples:
            ```python
            profile = ApiDocProfile.reference()
            ```
        """

        return cls(name="reference")

    @classmethod
    def compact(cls) -> ApiDocProfile:
        """Return a compact profile for summaries and indexes.

        Returns:
            Profile that truncates long descriptions, renders at most one
            example, and skips nested member detail sections.
        """

        return cls(
            name="compact",
            include_member_sections=False,
            max_description_chars=180,
            max_examples=1,
            parameter_columns=("name", "type", "description"),
        )

    @classmethod
    def manual(cls) -> ApiDocProfile:
        """Return a profile tuned for manual-style authored documents.

        Returns:
            Profile that keeps examples and see-also content prominent while
            remaining suitable for insertion into an existing chapter.
        """

        return cls(name="manual", include_source=False)

    @classmethod
    def evidence(cls) -> ApiDocProfile:
        """Return a profile for release evidence and coverage appendices.

        Returns:
            Profile that emphasizes source locations and summary tables while
            suppressing long prose and examples.
        """

        return cls(
            name="evidence",
            include_description=True,
            include_examples=False,
            include_see_also=False,
            include_renderer_notes=True,
            include_member_sections=False,
            max_description_chars=120,
            parameter_columns=("name", "type", "description"),
        )

    @classmethod
    def review(cls) -> ApiDocProfile:
        """Return a profile optimized for DOCX review copies.

        Returns:
            Profile that prefers editable tables and plain block structure.
        """

        return cls(name="review", prefer_editable_tables=True)

    @classmethod
    def website(cls) -> ApiDocProfile:
        """Return a profile optimized for HTML API pages.

        Returns:
            Profile that preserves headings, anchors, source locations, and
            navigation-friendly member summaries.
        """

        return cls(name="website")

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-serializable mapping.

        Returns:
            Dictionary containing every profile option.
        """

        return {
            "name": self.name,
            "include_signature": self.include_signature,
            "include_description": self.include_description,
            "include_parameters": self.include_parameters,
            "include_returns": self.include_returns,
            "include_raises": self.include_raises,
            "include_examples": self.include_examples,
            "include_see_also": self.include_see_also,
            "include_renderer_notes": self.include_renderer_notes,
            "include_source": self.include_source,
            "include_member_summary": self.include_member_summary,
            "include_member_sections": self.include_member_sections,
            "parameter_columns": list(self.parameter_columns),
            "max_description_chars": self.max_description_chars,
            "max_examples": self.max_examples,
            "prefer_editable_tables": self.prefer_editable_tables,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ApiDocProfile:
        """Build a profile from serialized data.

        Args:
            data: Mapping produced by ``to_dict``.

        Returns:
            Reconstructed profile object.
        """

        values = dict(data)
        if "parameter_columns" in values:
            values["parameter_columns"] = tuple(values["parameter_columns"])  # type: ignore[arg-type]
        return cls(**values)  # type: ignore[arg-type]


_PROFILES: dict[str, ApiDocProfile] = {
    "reference": ApiDocProfile.reference(),
    "compact": ApiDocProfile.compact(),
    "manual": ApiDocProfile.manual(),
    "evidence": ApiDocProfile.evidence(),
    "review": ApiDocProfile.review(),
    "website": ApiDocProfile.website(),
}


def register_profile(name: str, profile: ApiDocProfile) -> None:
    """Register a custom API documentation profile.

    Args:
        name: Profile name used by ``resolve_profile``.
        profile: Profile object to register.

    Raises:
        ValueError: If the name is empty or already registered.

    Examples:
        ```python
        from oodocs.apidoc.styles import ApiDocProfile, register_profile

        register_profile("brief", ApiDocProfile.compact())
        ```
    """

    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("profile name must not be empty")
    if normalized in _PROFILES:
        raise ValueError(f"API documentation profile already registered: {name!r}")
    _PROFILES[normalized] = profile


def resolve_profile(profile: str | ApiDocProfile = "reference") -> ApiDocProfile:
    """Resolve a profile name or object.

    Args:
        profile: Profile name or already-constructed profile.

    Returns:
        Resolved profile.

    Raises:
        ValueError: If a profile name is unknown.
    """

    if isinstance(profile, ApiDocProfile):
        return profile
    normalized = profile.strip().lower()
    try:
        return _PROFILES[normalized]
    except KeyError as exc:
        available = ", ".join(sorted(_PROFILES))
        raise ValueError(f"Unknown API documentation profile {profile!r}. Available: {available}") from exc


def profile_names() -> tuple[str, ...]:
    """Return registered profile names.

    Returns:
        Sorted profile name tuple.
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
    """

    allowed = {"name", "type", "default", "required", "description", "source"}
    normalized = tuple(column.strip().lower() for column in columns)
    invalid = [column for column in normalized if column not in allowed]
    if invalid:
        raise ValueError(f"Unsupported API parameter columns: {', '.join(invalid)}")
    return normalized


__all__ = [
    "ApiDocProfile",
    "normalize_parameter_columns",
    "profile_names",
    "register_profile",
    "resolve_profile",
]
