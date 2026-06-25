"""Convert normalized API documentation objects into OODocs blocks."""

from __future__ import annotations

from typing import Iterable, Sequence

from oodocs.apidoc.model import ApiModule, ApiObject, ApiPackage
from oodocs.apidoc.styles import ApiDocProfile, resolve_profile
from oodocs.components.base import Block
from oodocs.components.blocks import Box, CodeBlock, Paragraph, Section, section_for_level
from oodocs.components.inline import InlineChip, InlineChipStyle, Text, bold, code, comment, italic
from oodocs.components.media import Table


def api_heading_text(obj: ApiObject) -> list[Text]:
    """Return inline heading fragments for an API object.

    Args:
        obj: API object to describe.

    Returns:
        Inline fragments suitable for an OODocs heading.
    """

    fragments: list[Text] = [Text(obj.display_name())]
    if obj.deprecated:
        fragments.extend([Text(" "), api_deprecated_chip(obj)])
    return fragments


def api_kind_chip(obj: ApiObject) -> InlineChip:
    """Return a compact chip showing the API object kind."""

    return InlineChip(
        obj.kind,
        kind="badge",
        chip_style=InlineChipStyle(
            background_color="E0F2FE",
            text_color="075985",
            border_color="BAE6FD",
            uppercase=True,
        ),
    )


def api_visibility_chip(obj: ApiObject) -> InlineChip:
    """Return a compact chip showing the object visibility."""

    style = InlineChipStyle(
        background_color="ECFDF3" if obj.visibility == "public" else "F3F4F6",
        text_color="166534" if obj.visibility == "public" else "374151",
        border_color="BBF7D0" if obj.visibility == "public" else "D1D5DB",
        uppercase=True,
    )
    return InlineChip(obj.visibility, kind="badge", chip_style=style)


def api_deprecated_chip(obj: ApiObject) -> InlineChip | None:
    """Return a deprecation chip for deprecated objects.

    Args:
        obj: API object.

    Returns:
        Deprecation chip, or ``None`` for active objects.
    """

    if not obj.deprecated:
        return None
    return InlineChip(
        "deprecated",
        kind="status",
        chip_style=InlineChipStyle(
            background_color="FEE2E2",
            text_color="991B1B",
            border_color="FECACA",
            uppercase=True,
        ),
    )


def api_object_summary_paragraph(obj: ApiObject) -> Paragraph:
    """Return a compact summary paragraph for an API object."""

    pieces: list[object] = [
        api_kind_chip(obj),
        " ",
        code(obj.display_name()),
    ]
    summary = obj.plain_summary()
    if summary:
        pieces.extend([": ", summary])
    return Paragraph(*pieces)


def api_signature_block(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> CodeBlock | None:
    """Return an API signature as a code block.

    Args:
        obj: API object.
        profile: Presentation profile.

    Returns:
        Code block, or ``None`` when signatures are suppressed.
    """

    resolved = resolve_profile(profile)
    if not resolved.include_signature or not obj.signature:
        return None
    signature = _wrap_signature(
        obj.display_signature(),
        width=resolved.max_signature_width,
        indent=resolved.signature_wrap_indent,
    )
    signature = _truncate_lines(signature, resolved.max_signature_lines)
    return CodeBlock(signature, language="python")


def api_description_blocks(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> list[Block]:
    """Return summary and description blocks for an API object."""

    resolved = resolve_profile(profile)
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
                border_color="FCA5A5",
                background_color="FEF2F2",
            )
        )
    return blocks


def api_parameter_table(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
    *,
    caption: str | None = None,
) -> Table | None:
    """Return a parameter table for an API object.

    Args:
        obj: API object.
        profile: Presentation profile.
        caption: Optional table caption.

    Returns:
        Parameter table, or ``None`` when no parameters should render.
    """

    resolved = resolve_profile(profile)
    if not resolved.include_parameters or not obj.parameters:
        return None
    columns = resolved.parameter_columns
    headers = [_column_header(column) for column in columns]
    rows = [parameter.to_table_cell_values(columns) for parameter in obj.parameters]
    return Table(headers, rows, caption=caption, split=True)


def api_returns_blocks(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> list[Block]:
    """Return blocks documenting return values."""

    resolved = resolve_profile(profile)
    if not resolved.include_returns or obj.returns is None:
        return []
    parts: list[object] = []
    if obj.returns.annotation:
        parts.extend([code(obj.returns.annotation), ": "])
    if obj.returns.description:
        parts.append(obj.returns.description)
    if not parts:
        return []
    return [Paragraph(*parts, title="Returns")]


def api_raises_table(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
    *,
    caption: str | None = None,
) -> Table | None:
    """Return an exception table for an API object."""

    resolved = resolve_profile(profile)
    if not resolved.include_raises or not obj.raises:
        return None
    return Table(
        ["Exception", "Description"],
        [[item.exception, item.description or ""] for item in obj.raises],
        caption=caption,
        split=True,
    )


def api_examples_blocks(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> list[Block]:
    """Return example blocks for an API object."""

    resolved = resolve_profile(profile)
    if not resolved.include_examples or not obj.examples:
        return []
    examples = obj.examples
    if resolved.max_examples is not None:
        examples = examples[: resolved.max_examples]
    blocks: list[Block] = []
    for index, example in enumerate(examples, start=1):
        if example.caption:
            blocks.append(Paragraph(example.caption, title=f"Example {index}"))
        elif len(examples) > 1:
            blocks.append(Paragraph(f"Example {index}"))
        blocks.append(example.to_block())
    return blocks


def api_see_also_blocks(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> list[Block]:
    """Return see-also blocks for an API object."""

    resolved = resolve_profile(profile)
    if not resolved.include_see_also or not obj.see_also:
        return []
    rows = [
        [item.label, item.target or "", item.kind or "", item.description or ""]
        for item in obj.see_also
    ]
    return [
        Table(
            ["Label", "Target", "Kind", "Description"],
            rows,
            caption="See also",
            split=True,
        )
    ]


def api_notes_blocks(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> list[Block]:
    """Return parsed general notes as OODocs blocks."""

    resolved = resolve_profile(profile)
    if not resolved.include_notes or not obj.notes:
        return []
    return [
        Paragraph(note, title="Notes" if index == 0 else None)
        for index, note in enumerate(obj.notes)
    ]


def api_warnings_blocks(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> list[Block]:
    """Return parsed warning notes as OODocs blocks."""

    resolved = resolve_profile(profile)
    if not resolved.include_warnings or not obj.warnings:
        return []
    warning_text = "\n\n".join(obj.warnings)
    return [
        Box(
            Paragraph(warning_text),
            title="Warnings",
            border_color="F59E0B",
            background_color="FFFBEB",
        )
    ]


def api_renderer_notes_table(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
    *,
    caption: str | None = "Renderer notes",
) -> Table | None:
    """Return renderer-specific notes as a table."""

    resolved = resolve_profile(profile)
    if not resolved.include_renderer_notes or not obj.renderer_notes:
        return None
    notes = obj.renderer_notes
    if resolved.name == "compact":
        notes = [note for note in notes if note.severity == "warning"]
    if not notes:
        return None
    return Table(
        ["Format", "Severity", "Message"],
        [[note.format or "all", note.severity, note.message] for note in notes],
        caption=caption,
        split=True,
    )


def api_renderer_notes_blocks(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> list[Block]:
    """Return renderer notes table as a block list."""

    table = api_renderer_notes_table(obj, profile)
    return [table] if table is not None else []


def api_source_location_paragraph(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> Paragraph | None:
    """Return source location as a paragraph when enabled."""

    resolved = resolve_profile(profile)
    if not resolved.include_source or not obj.source_path:
        return None
    location = obj.source_path
    if obj.line_number is not None:
        location = f"{location}:{obj.line_number}"
    return Paragraph(location, title="Source")


def api_review_note_paragraph(
    obj: ApiObject,
    profile: str | ApiDocProfile = "reference",
) -> Paragraph | None:
    """Return a reviewer note paragraph when enabled by the profile.

    Args:
        obj: API object being rendered.
        profile: Presentation profile.

    Returns:
        Paragraph containing an inline comment, or ``None`` when review notes
        are disabled.
    """

    resolved = resolve_profile(profile)
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
    profile: str | ApiDocProfile = "reference",
) -> Table | None:
    """Return a member summary table for class-like objects."""

    resolved = resolve_profile(profile)
    if not resolved.include_member_summary or not obj.members:
        return None
    return api_objects_to_summary_table(obj.members, caption="Members", profile=resolved)


def api_object_to_blocks(
    obj: ApiObject,
    *,
    profile: str | ApiDocProfile = "reference",
    level: int = 2,
) -> list[Block]:
    """Convert one API object into renderer-neutral blocks."""

    resolved = resolve_profile(profile)
    blocks: list[Block] = []

    if signature := api_signature_block(obj, resolved):
        blocks.append(signature)
    blocks.extend(api_description_blocks(obj, resolved))
    if parameter_table := api_parameter_table(obj, resolved, caption="Parameters"):
        blocks.append(parameter_table)
    blocks.extend(api_returns_blocks(obj, resolved))
    if raises_table := api_raises_table(obj, resolved, caption="Raises"):
        blocks.append(raises_table)
    blocks.extend(api_notes_blocks(obj, resolved))
    blocks.extend(api_warnings_blocks(obj, resolved))
    blocks.extend(api_examples_blocks(obj, resolved))
    blocks.extend(api_see_also_blocks(obj, resolved))
    blocks.extend(api_renderer_notes_blocks(obj, resolved))
    if member_summary := api_member_summary_table(obj, resolved):
        blocks.append(member_summary)
    if source := api_source_location_paragraph(obj, resolved):
        blocks.append(source)
    if review_note := api_review_note_paragraph(obj, resolved):
        blocks.append(review_note)

    if resolved.include_member_sections:
        child_level = min(level + 1, 6)
        for member in obj.members:
            blocks.append(member.to_section(level=child_level, profile=resolved))
    return blocks


def api_object_to_section(
    obj: ApiObject,
    *,
    profile: str | ApiDocProfile = "reference",
    level: int = 2,
    title: str | None = None,
) -> Section:
    """Convert one API object into an OODocs section."""

    heading = title or obj.display_name()
    section = section_for_level(
        heading,
        *api_object_to_blocks(obj, profile=profile, level=level),
        level=level,
        anchor=obj.anchor_id(),
    )
    return section


def api_object_to_compact_box(
    obj: ApiObject,
    *,
    profile: str | ApiDocProfile = "compact",
) -> Box:
    """Return an API object as a compact boxed summary."""

    blocks: list[Block] = [api_object_summary_paragraph(obj)]
    if signature := api_signature_block(obj, profile):
        blocks.append(signature)
    return Box(*blocks, title=obj.display_name())


def api_objects_to_summary_table(
    objects: Sequence[ApiObject],
    *,
    profile: str | ApiDocProfile = "compact",
    caption: str | None = None,
    include_module: bool = True,
) -> Table:
    """Return a summary table for API objects.

    The website profile links object names to the stable section anchors
    produced by ``ApiObject.to_section(...)``.
    """

    resolved = resolve_profile(profile)
    headers = ["Kind", "Module", "Name", "Summary"] if include_module else ["Kind", "Name", "Summary"]
    rows = [
        obj.to_summary_row(include_module=include_module, link_name=resolved.name == "website")
        for obj in objects
    ]
    return Table(headers, rows, caption=caption, split=True)


def api_module_to_blocks(
    module: ApiModule,
    *,
    profile: str | ApiDocProfile = "reference",
    level: int = 2,
) -> list[Block]:
    """Convert a module into renderer-neutral blocks."""

    resolved = resolve_profile(profile)
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
                border_color="F59E0B",
                background_color="FFFBEB",
            )
        )
    if resolved.include_renderer_notes and module.renderer_notes:
        blocks.append(
            Table(
                ["Format", "Severity", "Message"],
                [
                    [note.format or "all", note.severity, note.message]
                    for note in module.renderer_notes
                ],
                caption="Renderer notes",
                split=True,
            )
        )
    if module.members:
        blocks.append(module.to_summary_table(caption="Module API", profile=resolved))
    blocks.extend(module.to_sections(profile=resolved, level=level))
    return blocks


def api_module_to_chapter(
    module: ApiModule,
    *,
    profile: str | ApiDocProfile = "reference",
    title: str | None = None,
):
    """Convert a module into an OODocs chapter."""

    from oodocs.components.blocks import Chapter

    return Chapter(
        title or module.name,
        *api_module_to_blocks(module, profile=profile, level=2),
    )



def api_package_to_chapters(
    package: ApiPackage,
    *,
    profile: str | ApiDocProfile = "reference",
) -> list[object]:
    """Convert package modules into OODocs chapters."""

    return [module.to_chapter(profile=profile) for module in package.modules]


def api_objects_to_chapter(
    title: str,
    objects: Iterable[ApiObject],
    *,
    profile: str | ApiDocProfile = "manual",
    level: int = 2,
):
    """Build a chapter from selected API objects."""

    from oodocs.components.blocks import Chapter

    return Chapter(title, *[obj.to_section(level=level, profile=profile) for obj in objects])


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
    "api_object_to_compact_box",
    "api_object_to_section",
    "api_objects_to_chapter",
    "api_objects_to_summary_table",
    "api_package_to_chapters",
    "api_parameter_table",
    "api_raises_table",
    "api_review_note_paragraph",
    "api_renderer_notes_blocks",
    "api_renderer_notes_table",
    "api_returns_blocks",
    "api_see_also_blocks",
    "api_signature_block",
    "api_source_location_paragraph",
    "api_visibility_chip",
    "api_warnings_blocks",
]
