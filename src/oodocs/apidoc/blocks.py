"""Convert normalized API documentation objects into OODocs blocks."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from oodocs.apidoc.model import ApiModule, ApiObject, ApiPackage, ApiSeeAlso
from oodocs.apidoc.profiles import ApiPresentationProfile, resolve_presentation_profile
from oodocs.components.base import Block
from oodocs.components.blocks import Box, CodeBlock, Paragraph, Section, section_for_level
from oodocs.components.inline import InlineChip, Text, bold, inline_code, comment, italic
from oodocs.styles import BorderStyle, InlineChipStyle
from oodocs.components.media import Table


def _unique_see_also_items(obj: ApiObject) -> Iterable[ApiSeeAlso]:
    seen: set[str] = set()
    for item in obj.see_also:
        key = item.target or item.label
        if key in seen:
            continue
        seen.add(key)
        yield item


def api_heading_text(obj: ApiObject) -> list[Text]:
    """Return inline heading fragments for an API object.

    Args:
        obj: API object to describe.

    Returns:
        Inline fragments suitable for an OODocs heading.

    Examples:
        Build the inline heading fragments used by ``api_object_to_section``:

        ```python
        from oodocs.apidoc import ApiObject
        from oodocs.apidoc.blocks import api_heading_text

        obj = ApiObject("function", "load", "mypkg.load", "mypkg")
        heading = api_heading_text(obj)
        ```
    """

    fragments: list[Text] = [Text(obj.heading_text())]
    if obj.deprecated:
        fragments.extend([Text(" "), api_deprecated_chip(obj)])
    return fragments


def api_kind_chip(obj: ApiObject) -> InlineChip:
    """Return a compact chip showing the API object kind.

    Args:
        obj: API object to label.

    Returns:
        Inline chip containing ``obj.kind``.

    Examples:
        Add an API kind badge to a custom summary paragraph:

        ```python
        from oodocs import Paragraph
        from oodocs.apidoc import ApiObject
        from oodocs.apidoc.blocks import api_kind_chip

        obj = ApiObject("class", "Client", "mypkg.Client", "mypkg")
        paragraph = Paragraph(api_kind_chip(obj), " ", obj.qualname)
        ```
    """

    return InlineChip(
        obj.kind,
        kind="badge",
        chip_style=InlineChipStyle(
            background_color="E0F2FE",
            text_color="075985",
            border=BorderStyle.solid("BAE6FD", width=0.5, radius=0.5, radius_unit="em"),
            uppercase=True,
        ),
    )


def api_visibility_chip(obj: ApiObject) -> InlineChip:
    """Return a compact chip showing the object visibility.

    Args:
        obj: API object to label.

    Returns:
        Inline chip containing ``obj.visibility``.

    Examples:
        Show public/private status in a custom API index row:

        ```python
        from oodocs.apidoc import ApiObject
        from oodocs.apidoc.blocks import api_visibility_chip

        obj = ApiObject("function", "load", "mypkg.load", "mypkg")
        chip = api_visibility_chip(obj)
        ```
    """

    style = InlineChipStyle(
        background_color="ECFDF3" if obj.visibility == "public" else "F3F4F6",
        text_color="166534" if obj.visibility == "public" else "374151",
        border=BorderStyle.solid(
            "BBF7D0" if obj.visibility == "public" else "D1D5DB",
            width=0.5,
            radius=0.5,
            radius_unit="em",
        ),
        uppercase=True,
    )
    return InlineChip(obj.visibility, kind="badge", chip_style=style)


def api_deprecated_chip(obj: ApiObject) -> InlineChip | None:
    """Return a deprecation chip for deprecated objects.

    Args:
        obj: API object.

    Returns:
        Deprecation chip, or ``None`` for active objects.

    Examples:
        Render a status chip only when an object is deprecated:

        ```python
        from oodocs.apidoc import ApiObject
        from oodocs.apidoc.blocks import api_deprecated_chip

        obj = ApiObject(
            "function",
            "old_load",
            "mypkg.old_load",
            "mypkg",
            deprecated=True,
        )
        chip = api_deprecated_chip(obj)
        ```
    """

    if not obj.deprecated:
        return None
    return InlineChip(
        "deprecated",
        kind="status",
        chip_style=InlineChipStyle(
            background_color="FEE2E2",
            text_color="991B1B",
            border=BorderStyle.solid("FECACA", width=0.5, radius=0.5, radius_unit="em"),
            uppercase=True,
        ),
    )


def api_object_summary_paragraph(obj: ApiObject) -> Paragraph:
    """Return a compact summary paragraph for an API object.

    Args:
        obj: API object to summarize.

    Returns:
        Paragraph containing object kind, display name, and summary.

    Examples:
        Insert a single parsed object summary into an authored chapter:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_object_summary_paragraph

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document(
            "API Notes",
            Chapter("Selected Object", api_object_summary_paragraph(obj)),
        )
        ```
    """

    pieces: list[object] = [
        api_kind_chip(obj),
        " ",
        inline_code(obj.heading_text()),
    ]
    summary = obj.summary_text()
    if summary:
        pieces.extend([": ", summary])
    return Paragraph(*pieces)


def api_signature_code_block(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> CodeBlock | None:
    """Return an API signature as a code block.

    Args:
        obj: API object.
        presentation: Presentation profile.

    Returns:
        Code block, or ``None`` when signatures are suppressed.

    Examples:
        Render a signature block in a custom API appendix:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_signature_code_block

        api = collect_api(".")
        obj = api.select_functions()[0]
        block = api_signature_code_block(obj, presentation="reference")
        doc = Document("API Appendix", Chapter("Signature", block))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_signature or not obj.signature:
        return None
    signature = _wrap_signature(
        obj.signature_text(),
        width=resolved.max_signature_width,
        indent=resolved.signature_wrap_indent,
    )
    signature = _truncate_lines(signature, resolved.max_signature_lines)
    return CodeBlock(signature, language="python")


def api_description_blocks(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> list[Block]:
    """Return summary and description blocks for an API object.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Paragraph or deprecation blocks for summary/description content.

    Examples:
        Use description blocks before adding custom guidance:

        ```python
        from oodocs import Chapter, Document, Paragraph
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_description_blocks

        api = collect_api(".")
        obj = api.select_classes()[0]
        doc = Document(
            "API Notes",
            Chapter("Class Notes", *api_description_blocks(obj), Paragraph("Review complete.")),
        )
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_description:
        return []
    blocks: list[Block] = []
    if obj.summary:
        blocks.append(Paragraph(obj.summary))
    if obj.description:
        description = _truncate(obj.description, resolved.max_description_chars)
        if description and description != obj.summary:
            blocks.append(Paragraph(description))
    if obj.deprecated and obj.deprecation_message:
        blocks.append(
            Box(
                Paragraph(obj.deprecation_message),
                title="Deprecated",
                border=BorderStyle.solid("FCA5A5", width=0.75),
                background_color="FEF2F2",
            )
        )
    return blocks


def api_parameter_table(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
    *,
    caption: str | None = None,
) -> Table | None:
    """Return a parameter table for an API object.

    Args:
        obj: API object.
        presentation: Presentation profile.
        caption: Optional table caption.

    Returns:
        Parameter table, or ``None`` when no parameters should render.

    Examples:
        Add only a parameter table to an evidence document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_parameter_table

        api = collect_api(".")
        obj = api.select_functions()[0]
        table = api_parameter_table(obj, presentation="review", caption="Parameters")
        doc = Document("API Review", Chapter("Parameter Review", table))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_parameters or not obj.parameters:
        return None
    columns = resolved.parameter_columns
    headers = [_column_header(column) for column in columns]
    rows = [parameter.as_table_cells(columns) for parameter in obj.parameters]
    return Table(headers, rows, caption=caption, split=True)


def api_returns_blocks(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> list[Block]:
    """Return blocks documenting return values.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Return documentation blocks, or an empty list.

    Examples:
        Append return docs to a custom function section:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_returns_blocks

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document("API Notes", Chapter("Returns", *api_returns_blocks(obj)))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_returns or obj.returns is None:
        return []
    parts: list[object] = []
    if obj.returns.annotation:
        parts.extend([inline_code(obj.returns.annotation), ": "])
    if obj.returns.description:
        parts.append(obj.returns.description)
    if not parts:
        return []
    return [Paragraph(*parts, title="Returns")]


def api_exceptions_table(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
    *,
    caption: str | None = None,
) -> Table | None:
    """Return an exception table for an API object.

    Args:
        obj: API object to render.
        presentation: Presentation profile.
        caption: Optional table caption.

    Returns:
        Exception table, or ``None`` when no exceptions should render.

    Examples:
        Render documented exceptions in a review appendix:

        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_exceptions_table

        api = collect_api(".")
        obj = api.select_functions()[0]
        table = api_exceptions_table(obj, caption="Raises")
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_exceptions or not obj.exceptions:
        return None
    return Table(
        ["Exception", "Description"],
        [item.as_exception_row() for item in obj.exceptions],
        caption=caption,
        split=True,
    )


def api_examples_blocks(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> list[Block]:
    """Return example blocks for an API object.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Example caption paragraphs and code blocks.

    Examples:
        Insert parsed examples into a tutorial chapter:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_examples_blocks

        api = collect_api(".")
        obj = api.select_functions()[0]
        tutorial = Document("Tutorial", Chapter("Examples", *api_examples_blocks(obj)))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_examples or not obj.examples:
        return []
    examples = obj.examples
    max_code_lines: int | None = None
    if resolved.name == "help":
        basic_examples = [example for example in examples if example.role == "basic"]
        examples = basic_examples or examples[:1]
        max_code_lines = 20
    if resolved.max_examples is not None:
        examples = examples[: resolved.max_examples]
    blocks: list[Block] = []
    for index, example in enumerate(examples, start=1):
        if example.caption:
            blocks.append(Paragraph(example.caption, title=f"Example {index}"))
        elif len(examples) > 1:
            blocks.append(Paragraph(f"Example {index}"))
        blocks.append(example.to_code_block(max_lines=max_code_lines))
    return blocks


def api_see_also_blocks(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> list[Block]:
    """Return see-also blocks for an API object.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Compact related API paragraphs, guide-style box blocks, or an empty
        list.

    Examples:
        Add related API references to a custom section:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_see_also_blocks

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document("API Notes", Chapter("Related API", *api_see_also_blocks(obj)))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_see_also or not obj.see_also:
        return []
    items = list(_unique_see_also_items(obj))
    if not items:
        return []
    if resolved.name == "manual":
        return [
            Box(
                *(item.to_paragraph() for item in items),
                title="See also",
                border=BorderStyle.solid("93C5FD", width=0.75),
                background_color="EFF6FF",
            )
        ]
    return [Paragraph(bold("See also")), *(item.to_paragraph() for item in items)]


def api_notes_blocks(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> list[Block]:
    """Return parsed general notes as OODocs blocks.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Note paragraphs, or an empty list.

    Examples:
        Place parsed ``Notes:`` content in a review document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_notes_blocks

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document("API Review", Chapter("Notes", *api_notes_blocks(obj)))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_notes or not obj.notes:
        return []
    return [
        Paragraph(note, title="Notes" if index == 0 else None)
        for index, note in enumerate(obj.notes)
    ]


def api_warnings_blocks(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> list[Block]:
    """Return parsed warning notes as OODocs blocks.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Warning box blocks, or an empty list.

    Examples:
        Surface parsed ``Warnings:`` content in release evidence:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_warnings_blocks

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document("API Evidence", Chapter("Warnings", *api_warnings_blocks(obj)))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_warnings or not obj.warnings:
        return []
    warning_text = "\n\n".join(obj.warnings)
    return [
        Box(
            Paragraph(warning_text),
            title="Warnings",
            border=BorderStyle.solid("F59E0B", width=0.75),
            background_color="FFFBEB",
        )
    ]


def api_output_notes_table(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
    *,
    caption: str | None = "Renderer notes",
) -> Table | None:
    """Return renderer-specific notes as a table.

    Args:
        obj: API object to render.
        presentation: Presentation profile.
        caption: Optional table caption.

    Returns:
        Renderer notes table, or ``None`` when no notes should render.

    Examples:
        Add renderer-specific notes to a compatibility report:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_output_notes_table

        api = collect_api(".")
        obj = api.select_functions()[0]
        table = api_output_notes_table(obj, presentation="reference")
        doc = Document("Renderer Notes", Chapter("API", table))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_renderer_notes or not obj.renderer_notes:
        return None
    notes = obj.renderer_notes
    if resolved.name == "compact":
        notes = [note for note in notes if note.severity == "warning"]
    if not notes:
        return None
    return Table(
        ["Output format", "Severity", "Message"],
        [note.as_output_note_row() for note in notes],
        caption=caption,
        split=True,
    )


def api_output_notes_blocks(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> list[Block]:
    """Return renderer notes table as a block list.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        One-item table block list, or an empty list.

    Examples:
        Compose renderer notes with other custom blocks:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_output_notes_blocks

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document(
            "Renderer Evidence",
            Chapter("Notes", *api_output_notes_blocks(obj)),
        )
        ```
    """

    table = api_output_notes_table(obj, presentation)
    return [table] if table is not None else []


def api_source_location_paragraph(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> Paragraph | None:
    """Return source location as a paragraph when enabled.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Source location paragraph, or ``None`` when disabled or unavailable.

    Examples:
        Show source locations in an evidence appendix:

        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_source_location_paragraph

        api = collect_api(".")
        obj = api.select_functions()[0]
        source = api_source_location_paragraph(obj, presentation="evidence")
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_source or not obj.source_path:
        return None
    source_root = obj.metadata.get("source_root")
    location = _source_location_text(
        obj.source_path,
        obj.line_number,
        source_root=source_root if isinstance(source_root, str) else None,
    )
    return Paragraph(location, title="Source")


def api_review_note_paragraph(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
) -> Paragraph | None:
    """Return a reviewer note paragraph when enabled by the profile.

    Args:
        obj: API object being rendered.
        presentation: Presentation profile.

    Returns:
        Paragraph containing an inline comment, or ``None`` when review notes
        are disabled.

    Examples:
        Generate review-note comments for a DOCX review profile:

        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_review_note_paragraph

        api = collect_api(".")
        obj = api.select_functions()[0]
        note = api_review_note_paragraph(obj, presentation="review")
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_review_notes:
        return None
    note_text = resolved.review_note_text or "Review this API object's docstring before publishing."
    note_text = f"{note_text} Object: {obj.qualname}."
    return Paragraph(
        comment(
            "Review note",
            note_text,
            author=resolved.review_note_author,
            initials=resolved.review_note_initials,
        ),
        title="API review",
    )


def api_member_summary_table(
    obj: ApiObject,
    presentation: str | ApiPresentationProfile = "reference",
    *,
    level: int = 2,
    max_level: int | None = None,
) -> Table | None:
    """Return a member summary table for class-like objects.

    Args:
        obj: API object whose members should be summarized.
        presentation: Presentation profile.
        level: Heading level of ``obj`` when the table is rendered.
        max_level: Optional deepest heading level. Website links are emitted
            only when member sections will also be rendered.

    Returns:
        Member summary table, or ``None`` when there are no members.

    Examples:
        Summarize class methods before rendering detailed member sections:

        ```python
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_member_summary_table

        api = collect_api(".")
        cls = api.select_classes()[0]
        table = api_member_summary_table(cls, presentation="reference")
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    if not resolved.include_member_summary or not obj.members:
        return None
    link_names = (
        resolved.name == "website"
        and resolved.include_member_sections
        and _can_render_child_sections(level, _normalize_max_level(max_level))
    )
    return api_objects_to_summary_table(
        obj.members,
        caption=None,
        presentation=resolved,
        link_names=link_names,
    )


def api_object_to_blocks(
    obj: ApiObject,
    *,
    presentation: str | ApiPresentationProfile = "reference",
    level: int = 2,
    max_level: int | None = None,
) -> list[Block]:
    """Convert one API object into renderer-neutral blocks.

    Args:
        obj: API object to render.
        presentation: Presentation profile.
        level: Current heading level, used for nested member sections.
        max_level: Optional deepest heading level to expand.

    Returns:
        Renderer-neutral OODocs blocks for the object.

    Examples:
        Insert one parsed object into an authored chapter without a new
        heading:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_object_to_blocks

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document("API Notes", Chapter("load", *api_object_to_blocks(obj)))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    max_level = _normalize_max_level(max_level)
    blocks: list[Block] = []

    if signature := api_signature_code_block(obj, resolved):
        blocks.append(signature)
    blocks.extend(api_description_blocks(obj, resolved))
    if parameter_table := api_parameter_table(obj, resolved):
        blocks.append(Paragraph(bold("Parameters")))
        blocks.append(parameter_table)
    blocks.extend(api_returns_blocks(obj, resolved))
    if exceptions_table := api_exceptions_table(obj, resolved):
        blocks.append(Paragraph(bold("Raises")))
        blocks.append(exceptions_table)
    blocks.extend(api_notes_blocks(obj, resolved))
    blocks.extend(api_warnings_blocks(obj, resolved))
    blocks.extend(api_examples_blocks(obj, resolved))
    blocks.extend(api_see_also_blocks(obj, resolved))
    blocks.extend(api_output_notes_blocks(obj, resolved))
    if member_summary := api_member_summary_table(
        obj,
        resolved,
        level=level,
        max_level=max_level,
    ):
        blocks.append(Paragraph(bold("Members")))
        blocks.append(member_summary)
    if source := api_source_location_paragraph(obj, resolved):
        blocks.append(source)
    if review_note := api_review_note_paragraph(obj, resolved):
        blocks.append(review_note)

    if resolved.include_member_sections and _can_render_child_sections(level, max_level):
        child_level = min(level + 1, 6)
        for member in obj.members:
            blocks.append(
                member.to_section(
                    level=child_level,
                    presentation=resolved,
                    max_level=max_level,
                )
            )
    return blocks


def api_object_to_section(
    obj: ApiObject,
    *,
    presentation: str | ApiPresentationProfile = "reference",
    level: int = 2,
    title: str | None = None,
    max_level: int | None = None,
) -> Section:
    """Convert one API object into an OODocs section.

    Args:
        obj: API object to render.
        presentation: Presentation profile.
        level: Heading level for the resulting section.
        title: Optional heading override.
        max_level: Optional deepest heading level to expand.

    Returns:
        OODocs section with stable API anchor.

    Examples:
        Build a section from a selected API object:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_object_to_section

        api = collect_api(".")
        obj = api.select_classes()[0]
        doc = Document("API", Chapter("Classes", api_object_to_section(obj)))
        ```
    """

    heading = title or obj.heading_text()
    section = section_for_level(
        heading,
        *api_object_to_blocks(
            obj,
            presentation=presentation,
            level=level,
            max_level=max_level,
        ),
        level=level,
        anchor=obj.anchor_name(),
    )
    return section


def api_object_to_box(
    obj: ApiObject,
    *,
    presentation: str | ApiPresentationProfile = "compact",
) -> Box:
    """Return an API object as a compact boxed summary.

    Args:
        obj: API object to render.
        presentation: Presentation profile.

    Returns:
        Box containing a compact object summary and optional signature.

    Examples:
        Add a compact API callout to a guide:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_object_to_box

        api = collect_api(".")
        obj = api.select_functions()[0]
        doc = Document("Guide", Chapter("Related API", api_object_to_box(obj)))
        ```
    """

    blocks: list[Block] = [api_object_summary_paragraph(obj)]
    if signature := api_signature_code_block(obj, presentation):
        blocks.append(signature)
    return Box(*blocks, title=obj.heading_text())


def api_objects_to_summary_table(
    objects: Sequence[ApiObject],
    *,
    presentation: str | ApiPresentationProfile = "compact",
    caption: str | None = None,
    include_module: bool = True,
    link_names: bool | None = None,
) -> Table:
    """Return a summary table for API objects.

    The website profile links object names to the stable section anchors
    produced by ``ApiObject.to_section(...)``.

    Args:
        objects: API objects to summarize.
        presentation: Presentation profile.
        caption: Optional table caption.
        include_module: Whether to include the module column.
        link_names: Optional override for whether object names should link to
            object anchors. Defaults to ``True`` for the website profile and
            ``False`` otherwise.

    Returns:
        OODocs table containing kind, module/name, and summary columns.

    Examples:
        Build a function index for an authored document:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_objects_to_summary_table

        api = collect_api(".")
        table = api_objects_to_summary_table(
            api.select_functions(),
            presentation="compact",
            caption="Public functions",
        )
        doc = Document("API Index", Chapter("Functions", table))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    headers = ["Kind", "Module", "Name", "Summary"] if include_module else ["Kind", "Name", "Summary"]
    resolved_link_names = resolved.name == "website" if link_names is None else link_names
    rows = [
        obj.as_summary_row(include_module=include_module, link_name=resolved_link_names)
        for obj in objects
    ]
    return Table(headers, rows, caption=caption, split=True)


def api_module_to_blocks(
    module: ApiModule,
    *,
    presentation: str | ApiPresentationProfile = "reference",
    level: int = 2,
    max_level: int | None = None,
) -> list[Block]:
    """Convert a module into renderer-neutral blocks.

    Args:
        module: API module to render.
        presentation: Presentation profile.
        level: Heading level for contained object sections.
        max_level: Optional deepest heading level to expand.

    Returns:
        Renderer-neutral blocks for module prose, summaries, and objects.

    Examples:
        Embed a module reference inside a larger guide:

        ```python
        from oodocs import Chapter, Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_module_to_blocks

        api = collect_api(".")
        module = next(iter(api))
        doc = Document("Module Guide", Chapter(module.name, *api_module_to_blocks(module)))
        ```
    """

    resolved = resolve_presentation_profile(presentation)
    max_level = _normalize_max_level(max_level)
    blocks: list[Block] = []
    if module.summary:
        blocks.append(Paragraph(module.summary))
    if module.description:
        blocks.append(Paragraph(module.description))
    if resolved.include_notes:
        blocks.extend(
            Paragraph(note, title="Notes" if index == 0 else None)
            for index, note in enumerate(module.notes)
        )
    if resolved.include_warnings and module.warnings:
        blocks.append(
            Box(
                Paragraph("\n\n".join(module.warnings)),
                title="Warnings",
                border=BorderStyle.solid("F59E0B", width=0.75),
                background_color="FFFBEB",
            )
        )
    if resolved.include_renderer_notes and module.renderer_notes:
        blocks.append(
            Table(
                ["Format", "Severity", "Message"],
                [note.as_output_note_row() for note in module.renderer_notes],
                caption="Renderer notes",
                split=True,
            )
        )
    render_member_sections = max_level is None or level <= max_level
    if module.members:
        blocks.append(
            api_objects_to_summary_table(
                module.members,
                caption="Module API",
                presentation=resolved,
                link_names=resolved.name == "website" and render_member_sections,
            )
        )
    if render_member_sections:
        blocks.extend(
            module.to_sections(
                presentation=resolved,
                level=level,
                max_level=max_level,
            )
        )
    return blocks


def api_module_to_chapter(
    module: ApiModule,
    *,
    presentation: str | ApiPresentationProfile = "reference",
    title: str | None = None,
    max_level: int | None = None,
):
    """Convert a module into an OODocs chapter.

    Args:
        module: API module to render.
        presentation: Presentation profile.
        title: Optional chapter title override.
        max_level: Optional deepest heading level to expand.

    Returns:
        OODocs chapter for the module.

    Examples:
        Render one module as a document chapter:

        ```python
        from oodocs import Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_module_to_chapter

        api = collect_api(".")
        module = next(iter(api))
        doc = Document("Module API", api_module_to_chapter(module))
        ```
    """

    from oodocs.components.blocks import Chapter

    return Chapter(
        title or module.name,
        *api_module_to_blocks(
            module,
            presentation=presentation,
            level=2,
            max_level=max_level,
        ),
    )


def api_package_to_chapters(
    package: ApiPackage,
    *,
    presentation: str | ApiPresentationProfile = "reference",
    max_level: int | None = None,
) -> list[object]:
    """Convert package modules into OODocs chapters.

    Args:
        package: API package to render.
        presentation: Presentation profile.
        max_level: Optional deepest heading level to expand.

    Returns:
        Chapter list, one per collected module.

    Examples:
        Build a complete package reference document:

        ```python
        from oodocs import Document
        from oodocs.apidoc import collect_api
        from oodocs.apidoc.blocks import api_package_to_chapters

        api = collect_api(".")
        doc = Document("Package API", *api_package_to_chapters(api))
        ```
    """

    return [
        module.to_chapter(presentation=presentation, max_level=max_level)
        for module in package.modules
    ]


def api_objects_to_chapter(
    title: str,
    objects: Iterable[ApiObject],
    *,
    presentation: str | ApiPresentationProfile = "manual",
    level: int = 2,
    max_level: int | None = None,
):
    """Build a chapter from selected API objects.

    Args:
        title: Chapter title.
        objects: API objects to render as child sections.
        presentation: Presentation profile name or ``ApiPresentationProfile``.
        level: Heading level used for each object section.
        max_level: Optional deepest heading level for nested member sections.

    Returns:
        OODocs chapter containing one section per selected API object.

    Examples:
        Insert selected classes into a larger hand-authored guide:

        ```python
        from oodocs import Document, Paragraph
        from oodocs.apidoc import collect_api, api_objects_to_chapter

        api = collect_api("mypkg")
        chapter = api_objects_to_chapter(
            "Widget API",
            api.select_objects(kind="class", module_prefix="mypkg.widgets"),
            presentation="manual",
            max_level=3,
        )
        guide = Document("Widget Guide", Paragraph("Overview text."), chapter)
        ```
    """

    from oodocs.components.blocks import Chapter

    return Chapter(
        title,
        *[
            obj.to_section(
                level=level,
                presentation=presentation,
                max_level=max_level,
            )
            for obj in objects
        ],
    )


def _normalize_max_level(max_level: int | None) -> int | None:
    if max_level is None:
        return None
    max_level = int(max_level)
    if max_level < 1:
        raise ValueError("max_level must be >= 1")
    return max_level


def _source_location_text(
    source_path: str,
    line_number: int | None,
    *,
    source_root: str | None = None,
) -> str:
    display_path = source_path
    if source_root:
        try:
            display_path = (
                Path(source_path)
                .resolve(strict=False)
                .relative_to(Path(source_root).resolve(strict=False))
                .as_posix()
            )
        except (OSError, ValueError):
            display_path = source_path
    if line_number is not None:
        return f"{display_path}:{line_number}"
    return display_path


def _can_render_child_sections(level: int, max_level: int | None) -> bool:
    return max_level is None or level < max_level


def _column_header(column: str) -> str:
    return {
        "name": "Name",
        "type": "Type",
        "default": "Default",
        "required": "Required",
        "description": "Description",
        "source": "Source",
    }.get(column, column.title())


def _truncate(value: str, limit: int | None) -> str:
    if limit is None or len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _truncate_lines(value: str, limit: int | None) -> str:
    if limit is None:
        return value
    lines = value.splitlines()
    if len(lines) <= limit:
        return value
    return "\n".join([*lines[: max(0, limit - 1)], "..."])


def _wrap_signature(signature: str, *, width: int | None, indent: str) -> str:
    if width is None or width <= 0:
        return signature
    return "\n".join(
        _wrap_signature_line(line, width=width, indent=indent)
        for line in signature.splitlines()
    )


def _wrap_signature_line(line: str, *, width: int, indent: str) -> str:
    if len(line) <= width:
        return line
    leading = line[: len(line) - len(line.lstrip())]
    body = line[len(leading) :]
    open_index = body.find("(")
    close_index = body.rfind(")")
    if open_index < 0 or close_index <= open_index:
        return line

    prefix = body[: open_index + 1]
    inner = body[open_index + 1 : close_index]
    suffix = body[close_index:]
    parts = _split_signature_parameters(inner)
    if len(parts) <= 1:
        return line

    wrapped = [f"{leading}{prefix}"]
    for index, part in enumerate(parts):
        comma = "," if index < len(parts) - 1 else ""
        wrapped.append(f"{leading}{indent}{part.strip()}{comma}")
    wrapped.append(f"{leading}{suffix}")
    return "\n".join(wrapped)


def _split_signature_parameters(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escape = False
    for index, char in enumerate(value):
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return [part for part in parts if part.strip()]


__all__ = [
    "api_description_blocks",
    "api_deprecated_chip",
    "api_examples_blocks",
    "api_heading_text",
    "api_kind_chip",
    "api_member_summary_table",
    "api_module_to_blocks",
    "api_module_to_chapter",
    "api_notes_blocks",
    "api_object_summary_paragraph",
    "api_object_to_blocks",
    "api_object_to_box",
    "api_object_to_section",
    "api_objects_to_chapter",
    "api_objects_to_summary_table",
    "api_package_to_chapters",
    "api_parameter_table",
    "api_exceptions_table",
    "api_review_note_paragraph",
    "api_output_notes_blocks",
    "api_output_notes_table",
    "api_returns_blocks",
    "api_see_also_blocks",
    "api_signature_code_block",
    "api_source_location_paragraph",
    "api_visibility_chip",
    "api_warnings_blocks",
]
