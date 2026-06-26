"""MATLAB-style API help-book composition helpers."""

from __future__ import annotations

from typing import Sequence

from oodocs.apidoc.builtin_categories import OODocs_API_CATEGORIES
from oodocs.apidoc.categories import ApiCategory, select_uncategorized_api_objects
from oodocs.apidoc.coverage import check_api_docs
from oodocs.apidoc.model import ApiObject, ApiPackage, ApiParameter
from oodocs.apidoc.profiles import ApiPresentationProfile, resolve_presentation_profile
from oodocs.components.base import Block
from oodocs.components.blocks import Chapter, CodeBlock, Paragraph, Section, section_for_level
from oodocs.components.generated import TableOfContents
from oodocs.components.inline import bold
from oodocs.components.media import Table
from oodocs.document import Document


def api_object_to_help_section(
    obj: ApiObject,
    *,
    level: int = 2,
    presentation: str | ApiPresentationProfile = "help",
    max_level: int | None = None,
) -> Section:
    """Return one public symbol as a help-page section.

    Args:
        obj: Collected API object to render.
        level: Heading level for the returned section.
        presentation: Presentation profile name or object. The default
            ``"help"`` profile keeps a single symbol page concise.
        max_level: Optional deepest heading level for nested member sections.

    Returns:
        Section containing the symbol signature, summary, parameters, examples,
        see-also links, and source metadata allowed by the presentation profile.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.apidoc import collect_api, api_object_to_help_section

        api = collect_api("oodocs", public_policy="__all__")
        paragraph = api.find_object("oodocs.Paragraph")
        section = api_object_to_help_section(paragraph, level=2)
        document = Document("Selected API", section)
        ```
    """

    profile = resolve_presentation_profile(presentation)
    if profile.name == "help":
        return section_for_level(
            obj.heading_text(),
            *_api_object_help_blocks(obj, presentation=profile),
            level=level,
            anchor=obj.anchor_name(),
        )
    return obj.to_section(level=level, presentation=profile, max_level=max_level)


def _api_object_help_blocks(
    obj: ApiObject,
    *,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    if obj.kind == "class":
        return _class_help_blocks(obj, presentation=presentation)
    if obj.kind in {"function", "method"}:
        return _function_help_blocks(obj, presentation=presentation)
    return _value_help_blocks(obj, presentation=presentation)


def _function_help_blocks(
    obj: ApiObject,
    *,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    blocks: list[Block] = []
    if presentation.include_description:
        blocks.extend(_summary_blocks(obj))
    if presentation.include_signature and (syntax := _syntax_block(obj)):
        blocks.extend([_subheading("Syntax"), syntax])
    if presentation.include_description:
        blocks.extend(_description_section(obj))
    if presentation.include_parameters:
        blocks.extend(_argument_sections(obj, input_title="Input Arguments"))
    if presentation.include_returns:
        blocks.extend(_returns_section(obj))
    blocks.extend(_examples_section(obj, presentation))
    blocks.extend(_exceptions_section(obj, presentation))
    blocks.extend(_see_also_section(obj, presentation))
    blocks.extend(_source_section(obj, presentation))
    return blocks


def _class_help_blocks(
    obj: ApiObject,
    *,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    blocks: list[Block] = []
    if presentation.include_description:
        blocks.extend(_summary_blocks(obj))
    if presentation.include_signature and (creation := _creation_block(obj)):
        blocks.extend([_subheading("Creation"), creation])
    if presentation.include_description:
        blocks.extend(_description_section(obj))
    if presentation.include_parameters:
        blocks.extend(_argument_sections(obj, input_title="Constructor Arguments"))
    if presentation.include_member_summary:
        if properties := _properties_table(obj):
            blocks.extend([_subheading("Properties"), properties])
        if methods := _methods_table(obj):
            blocks.extend([_subheading("Common Methods"), methods])
    blocks.extend(_examples_section(obj, presentation))
    blocks.extend(_exceptions_section(obj, presentation))
    blocks.extend(_see_also_section(obj, presentation))
    blocks.extend(_source_section(obj, presentation))
    return blocks


def _value_help_blocks(
    obj: ApiObject,
    *,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    blocks: list[Block] = []
    if presentation.include_description:
        blocks.extend(_summary_blocks(obj))
    if definition := _value_definition_table(obj):
        blocks.extend([_subheading("Definition"), definition])
    if presentation.include_description:
        blocks.extend(_description_section(obj))
    blocks.extend(_examples_section(obj, presentation))
    blocks.extend(_see_also_section(obj, presentation))
    blocks.extend(_source_section(obj, presentation))
    return blocks


def _summary_blocks(obj: ApiObject) -> list[Block]:
    return [Paragraph(obj.summary)] if obj.summary else []


def _description_section(obj: ApiObject) -> list[Block]:
    if not obj.description or obj.description == obj.summary:
        return []
    return [_subheading("Description"), Paragraph(obj.description)]


def _argument_sections(obj: ApiObject, *, input_title: str) -> list[Block]:
    positional, keyword_only = _split_help_parameters(obj.parameters)
    blocks: list[Block] = []
    if positional:
        blocks.extend([_subheading(input_title), _parameter_table(positional)])
    if keyword_only:
        blocks.extend([_subheading("Name-Value Arguments"), _parameter_table(keyword_only)])
    return blocks


def _returns_section(obj: ApiObject) -> list[Block]:
    if obj.returns is None:
        return []
    annotation = obj.returns.annotation or ""
    description = obj.returns.description or ""
    if not annotation and not description:
        return []
    return [
        _subheading("Output Arguments"),
        Table(["Type", "Description"], [[annotation, description]], caption=None, split=True),
    ]


def _examples_section(
    obj: ApiObject,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    from oodocs.apidoc.blocks import api_examples_blocks

    examples = api_examples_blocks(obj, presentation)
    if not examples:
        return []
    return [_subheading("Examples"), *examples]


def _exceptions_section(
    obj: ApiObject,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    from oodocs.apidoc.blocks import api_exceptions_table

    table = api_exceptions_table(obj, presentation, caption=None)
    return [_subheading("Errors"), table] if table is not None else []


def _see_also_section(
    obj: ApiObject,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    from oodocs.apidoc.blocks import api_see_also_blocks

    return api_see_also_blocks(obj, presentation)


def _source_section(
    obj: ApiObject,
    presentation: ApiPresentationProfile,
) -> list[Block]:
    from oodocs.apidoc.blocks import api_source_location_paragraph

    paragraph = api_source_location_paragraph(obj, presentation)
    return [paragraph] if paragraph is not None else []


def _subheading(text: str) -> Paragraph:
    return Paragraph(bold(text))


def _syntax_block(obj: ApiObject) -> CodeBlock | None:
    if not obj.signature:
        return None
    syntax = obj.signature_text()
    if obj.kind in {"function", "method"} and obj.returns and obj.returns.annotation:
        syntax = f"result = {syntax}"
    return CodeBlock(syntax, language="python")


def _creation_block(obj: ApiObject) -> CodeBlock | None:
    if obj.kind != "class":
        return _syntax_block(obj)
    if obj.signature:
        signature = obj.signature_text()
        if "(" in signature and ")" in signature:
            arguments = signature.split("(", 1)[1].rsplit(")", 1)[0]
            syntax = f"obj = {obj.name}({arguments})"
        else:
            syntax = f"obj = {obj.name}()"
    else:
        syntax = f"obj = {obj.name}()"
    return CodeBlock(syntax, language="python")


def _split_help_parameters(
    parameters: Sequence[ApiParameter],
) -> tuple[list[ApiParameter], list[ApiParameter]]:
    positional: list[ApiParameter] = []
    keyword_only: list[ApiParameter] = []
    for parameter in parameters:
        if parameter.name in {"self", "cls"}:
            continue
        if parameter.kind == "keyword-only":
            keyword_only.append(parameter)
        else:
            positional.append(parameter)
    return positional, keyword_only


def _parameter_table(parameters: Sequence[ApiParameter]) -> Table:
    return Table(
        ["Name", "Type", "Default", "Description"],
        [
            [
                parameter.name,
                parameter.annotation_text(),
                _parameter_default_text(parameter),
                parameter.description or "",
            ]
            for parameter in parameters
        ],
        caption=None,
        split=True,
    )


def _parameter_default_text(parameter: ApiParameter) -> str:
    if parameter.default:
        return parameter.default_text()
    return "Required" if parameter.required else ""


def _properties_table(obj: ApiObject) -> Table | None:
    properties = [
        member
        for member in obj.members
        if member.kind in {"property", "attribute"} and member.visibility == "public"
    ]
    if not properties:
        return None
    return Table(
        ["Property", "Type", "Description"],
        [
            [
                member.name,
                _value_type_text(member),
                member.summary_text(),
            ]
            for member in properties
        ],
        caption=None,
        split=True,
    )


def _methods_table(obj: ApiObject) -> Table | None:
    methods = [
        member
        for member in obj.members
        if member.kind == "method"
        and member.visibility == "public"
        and not member.name.startswith("render_to_")
    ]
    if not methods:
        return None
    return Table(
        ["Method", "Syntax", "Purpose"],
        [
            [
                member.name,
                member.signature_text(),
                member.summary_text(),
            ]
            for member in methods
        ],
        caption=None,
        split=True,
    )


def api_category_to_chapter(
    category: ApiCategory,
    api: ApiPackage,
    *,
    presentation: str | ApiPresentationProfile = "help",
    max_level: int | None = None,
) -> Chapter:
    """Return a category landing page and its symbol help sections.

    Args:
        category: Category definition that names the public symbols to include.
        api: Collected package API containing the category symbols.
        presentation: Presentation profile name or object used for each symbol
            section.
        max_level: Optional deepest heading level. Values below ``2`` render
            the category landing page and index without per-symbol sections.

    Returns:
        Chapter containing the category summary, related guide links, category
        index table, and matching symbol help sections.

    Examples:
        ```python
        from oodocs import Document
        from oodocs.apidoc import ApiCategory, api_category_to_chapter, collect_api

        api = collect_api("oodocs", public_policy="__all__")
        category = ApiCategory(
            id="tables",
            title="Tables and Figures",
            summary="Table and figure building blocks.",
            include=("oodocs.Table", "oodocs.Figure"),
            order=10,
        )
        chapter = api_category_to_chapter(category, api)
        document = Document("Selected API", chapter)
        ```
    """

    objects = _objects_for_category(api, category)
    blocks: list[object] = [Paragraph(category.summary)]
    if category.guide_links:
        blocks.append(Paragraph(bold("Related User Guide pages")))
        blocks.extend(link.to_paragraph() for link in category.guide_links)
    blocks.append(_category_index_table(category, objects))
    if constants := _constants_table(objects):
        blocks.extend([Paragraph(bold("Constants")), constants])
    blocks.extend(
        api_object_to_help_section(
            obj,
            level=2,
            presentation=presentation,
            max_level=max_level,
        )
        for obj in objects
        if max_level is None or max_level >= 2
    )
    return Chapter(category.title, *blocks)


def api_package_to_help_book(
    api: ApiPackage,
    *,
    title: str | None = None,
    categories: Sequence[ApiCategory] | None = None,
    presentation: str | ApiPresentationProfile = "help",
    settings: object | None = None,
    citations: object | None = None,
    include_coverage: bool = True,
    include_uncategorized_appendix: bool = True,
    max_level: int | None = None,
) -> Document:
    """Build a category-based API reference help book.

    Args:
        api: Collected package API.
        title: Optional document title. Defaults to
            ``"{api.name} API Reference"``.
        categories: Optional category definitions. Defaults to curated OODocs
            categories for the ``oodocs`` package, or a generated ``Public API``
            category for other packages.
        presentation: Presentation profile name or object used for symbol
            pages.
        settings: Optional document settings passed to ``Document``.
        citations: Optional citation library passed to ``Document``.
        include_coverage: Whether to append API documentation coverage evidence
            after category pages.
        include_uncategorized_appendix: Whether to append public API objects
            not assigned to a category before coverage evidence.
        max_level: Optional deepest heading level for the table of contents and
            generated symbol sections.

    Returns:
        Document containing the API contents page, category chapters, per-symbol
        help pages, and optional coverage appendix.

    Raises:
        ValueError: If ``max_level`` is less than ``1``.

    Examples:
        ```python
        from pathlib import Path
        from oodocs import DocumentSettings
        from oodocs.apidoc import collect_api, api_package_to_help_book

        api = collect_api("oodocs", public_policy="__all__")
        reference = api_package_to_help_book(
            api,
            title="OODocs API Reference",
            settings=DocumentSettings(cover_page=True),
        )
        reference.save(Path("build/oodocs-api-reference.html"))
        ```
    """

    if max_level is not None and max_level < 1:
        raise ValueError("max_level must be >= 1")
    category_list = tuple(categories) if categories is not None else _default_categories(api)
    visible_categories = tuple(
        sorted(
            (category for category in category_list if category.show_in_help_book),
            key=lambda category: category.order,
        )
    )
    uncategorized = tuple(select_uncategorized_api_objects(api, category_list))
    rendered_uncategorized = uncategorized if include_uncategorized_appendix else ()
    children: list[object] = [
        TableOfContents(title="API Contents", max_level=max_level),
        _contents_chapter(api, visible_categories, rendered_uncategorized),
    ]
    children.extend(
        api_category_to_chapter(
            category,
            api,
            presentation=presentation,
            max_level=max_level,
        )
        for category in visible_categories
    )
    if rendered_uncategorized:
        children.append(
            _uncategorized_chapter(
                rendered_uncategorized,
                presentation=presentation,
                max_level=max_level,
            )
        )
    if include_coverage:
        children.append(check_api_docs(api).to_section())
    return Document(
        title or f"{api.name} API Reference",
        *children,
        settings=settings,  # type: ignore[arg-type]
        citations=citations,  # type: ignore[arg-type]
    )


def _contents_chapter(
    api: ApiPackage,
    categories: Sequence[ApiCategory],
    uncategorized: Sequence[ApiObject] = (),
) -> Chapter:
    rows = []
    for category in categories:
        objects = _objects_for_category(api, category)
        rows.append(
            [
                category.title,
                category.summary,
                str(len(objects)),
            ]
        )
    if uncategorized:
        rows.append(
            [
                "Uncategorized API",
                "Public API symbols not yet assigned to a curated category.",
                str(len(uncategorized)),
            ]
        )
    return Chapter(
        "API Contents",
        Paragraph("Find public symbols by category. Coverage evidence is appended at the end."),
        Table(
            ["Category", "Purpose", "Symbols"],
            rows,
            caption=None,
            split=True,
        ),
    )


def _uncategorized_chapter(
    objects: Sequence[ApiObject],
    *,
    presentation: str | ApiPresentationProfile = "help",
    max_level: int | None = None,
) -> Chapter:
    from oodocs.apidoc.blocks import api_objects_to_summary_table

    blocks: list[object] = [
        Paragraph(
            "Public API symbols not yet assigned to a curated category. "
            "Move these objects into explicit categories before treating the "
            "help book as complete."
        ),
        api_objects_to_summary_table(
            objects,
            caption=None,
            presentation=presentation,
        ),
    ]
    if max_level is None or max_level >= 2:
        blocks.extend(
            api_object_to_help_section(
                obj,
                level=2,
                presentation=presentation,
                max_level=max_level,
            )
            for obj in objects
        )
    return Chapter("Uncategorized API", *blocks)


def _default_categories(api: ApiPackage) -> tuple[ApiCategory, ...]:
    if api.name == "oodocs":
        return OODocs_API_CATEGORIES
    public_objects = api.select_objects(
        kind=("class", "function", "data", "attribute"),
        visibility="public",
        recursive=False,
    )
    return (
        ApiCategory(
            id="public-api",
            title="Public API",
            summary=f"Public API symbols exported by {api.name}.",
            include=tuple(obj.qualname for obj in public_objects),
            order=10,
        ),
    )


def _category_index_table(category: ApiCategory, objects: Sequence[ApiObject]) -> Table:
    rows = [
        [
            obj.name,
            obj.summary_text(),
            _common_use(obj),
            f"{category.title} > {obj.name}",
        ]
        for obj in objects
    ]
    return Table(
        ["Object", "Purpose", "Common use", "Page"],
        rows,
        caption=None,
        split=True,
    )


def _constants_table(objects: Sequence[ApiObject]) -> Table | None:
    constants = [obj for obj in objects if obj.kind in {"data", "attribute"}]
    if not constants:
        return None
    return Table(
        ["Name", "Value / Type", "Meaning"],
        [
            [
                obj.name,
                _value_summary_text(obj),
                obj.summary_text(),
            ]
            for obj in constants
        ],
        caption=None,
        split=True,
    )


def _objects_for_category(api: ApiPackage, category: ApiCategory) -> tuple[ApiObject, ...]:
    found: list[ApiObject] = []
    seen: set[str] = set()
    public_objects: tuple[ApiObject, ...] | None = None
    for name in category.include:
        if name.endswith(".*"):
            prefix = name[:-1]
            if public_objects is None:
                public_objects = tuple(
                    api.select_objects(
                        kind=("class", "function", "data", "attribute"),
                        visibility="public",
                        recursive=False,
                    )
                )
            for obj in public_objects:
                if obj.qualname.startswith(prefix) and obj.qualname not in seen:
                    found.append(obj)
                    seen.add(obj.qualname)
            continue
        obj = api.find_object(name)
        if obj is None:
            obj = api.find_object(name.rsplit(".", 1)[-1])
        if obj is None or obj.qualname in seen:
            continue
        found.append(obj)
        seen.add(obj.qualname)
    return tuple(found)


def _common_use(obj: ApiObject) -> str:
    if obj.kind == "class":
        return "Create or configure this object directly."
    if obj.kind in {"function", "method"}:
        return "Call this helper from Python code."
    if obj.kind in {"attribute", "data"}:
        return "Use as a constant or configuration value."
    return "Use from the documented API surface."


def _value_definition_table(obj: ApiObject) -> Table | None:
    type_text = _value_type_text(obj)
    value_text = _value_default_text(obj)
    if not type_text and not value_text and obj.kind not in {"data", "attribute", "property"}:
        return None
    return Table(
        ["Name", "Type", "Value"],
        [[obj.name, type_text, value_text]],
        caption=None,
        split=True,
    )


def _value_summary_text(obj: ApiObject) -> str:
    value_text = _value_default_text(obj)
    type_text = _value_type_text(obj)
    if value_text and type_text:
        return f"{value_text} / {type_text}"
    return value_text or type_text


def _value_type_text(obj: ApiObject) -> str:
    if obj.returns and obj.returns.annotation:
        return obj.returns.annotation
    annotation = obj.metadata.get("annotation")
    if annotation:
        return str(annotation)
    signature = obj.signature_text()
    if ":" not in signature:
        return ""
    annotation_text = signature.split(":", 1)[1].strip()
    if "=" in annotation_text:
        annotation_text = annotation_text.split("=", 1)[0].strip()
    return annotation_text


def _value_default_text(obj: ApiObject) -> str:
    if "default" not in obj.metadata:
        return ""
    return _preview_text(obj.metadata["default"], max_chars=120)


def _preview_text(value: object, *, max_chars: int) -> str:
    text = " ".join(str(value).split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


__all__ = [
    "api_category_to_chapter",
    "api_object_to_help_section",
    "api_package_to_help_book",
]
