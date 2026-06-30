from __future__ import annotations

from dataclasses import fields
import importlib
import inspect

import pytest

import oodocs
import oodocs.adapters as adapters
import oodocs.apidoc as apidoc
import oodocs.chemistry as chemistry
import oodocs.components as components
import oodocs.components.base as base_components
import oodocs.components.blocks as block_components
import oodocs.components.inline as inline_components
import oodocs.components.markup as markup_components
import oodocs.components.media as media_components
import oodocs.components.people as people_components
import oodocs.components.positioning as positioning_components
import oodocs.components.references as references
import oodocs.engineering as engineering
import oodocs.equations as equations
import oodocs.generated as generated
import oodocs.glossary as glossary
import oodocs.importers as importers
import oodocs.media as media
import oodocs.pdf as pdf
import oodocs.positioning as positioning
import oodocs.presets as presets
import oodocs.presets.components as preset_components
import oodocs.presets.templates as preset_templates
import oodocs.public_api as public_api
import oodocs.references as reference_helpers
import oodocs.review as review
import oodocs.structure as structure
import oodocs.styles.generated as generated_styles
import oodocs.workflows as workflows
from oodocs.apidoc.cli import _build_parser as _build_apidoc_parser
from oodocs.cli import _build_parser as _build_oodocs_parser
from oodocs.importers.results import normalize_import_policy


_PUBLIC_API_MODULE_NAMES = (
    "oodocs",
    "oodocs.chemistry",
    "oodocs.equations",
    "oodocs.apidoc",
    "oodocs.adapters",
    "oodocs.importers.markdown",
    "oodocs.importers.notebook",
    "oodocs.pdf",
    "oodocs.styles",
    "oodocs.styles.generated",
    "oodocs.validation",
    "oodocs.workflows",
    "oodocs.presets",
)


def _public_members(cls: type[object]) -> set[str]:
    return {name for name, _ in inspect.getmembers(cls) if not name.startswith("_")}


def _public_api_exports():
    for module_name in _PUBLIC_API_MODULE_NAMES:
        module = importlib.import_module(module_name)
        for export_name in getattr(module, "__all__", ()):
            if hasattr(module, export_name):
                yield module_name, export_name, getattr(module, export_name)


def _subcommand_help(parser, args: list[str], capsys) -> str:
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([*args, "--help"])
    assert exc_info.value.code == 0
    return capsys.readouterr().out


def test_top_level_public_api_has_tier_policy_and_export_cap() -> None:
    export_names = set(oodocs.__all__)
    tier_names = set(public_api.TOP_LEVEL_SYMBOL_TIERS)
    allowed_tiers = {"core", "domain", "internal"}

    assert len(oodocs.__all__) <= public_api.TOP_LEVEL_EXPORT_LIMIT
    assert export_names == tier_names
    assert set(public_api.TOP_LEVEL_SYMBOL_TIERS.values()) <= allowed_tiers
    assert public_api.CORE_TOP_LEVEL_EXPORTS
    assert public_api.DOMAIN_TOP_LEVEL_EXPORTS
    assert not public_api.INTERNAL_TOP_LEVEL_EXPORTS
    assert (
        public_api.CORE_TOP_LEVEL_EXPORTS
        | public_api.DOMAIN_TOP_LEVEL_EXPORTS
        | public_api.INTERNAL_TOP_LEVEL_EXPORTS
    ) == tier_names
    assert not (
        public_api.CORE_TOP_LEVEL_EXPORTS
        & public_api.DOMAIN_TOP_LEVEL_EXPORTS
        | public_api.CORE_TOP_LEVEL_EXPORTS
        & public_api.INTERNAL_TOP_LEVEL_EXPORTS
        | public_api.DOMAIN_TOP_LEVEL_EXPORTS
        & public_api.INTERNAL_TOP_LEVEL_EXPORTS
    )


def test_top_level_public_api_excludes_internal_helper_patterns() -> None:
    leaked_names = {
        name
        for name in oodocs.__all__
        for pattern in public_api.FORBIDDEN_TOP_LEVEL_NAME_PATTERNS
        if pattern in name
    }

    assert leaked_names == set()


def test_recommended_user_import_experience_keeps_domains_explicit() -> None:
    table = oodocs.Table.from_records(
        [
            {"case": "A", "status": "pass"},
            {"case": "B", "status": "fail"},
        ],
        caption="Validation cases.",
    )
    document = oodocs.Document(
        "Validation Report",
        oodocs.Chapter(
            "Results",
            oodocs.Paragraph("Summary is shown in ", oodocs.ref(table), "."),
            table,
        ),
    )

    assert document.validate().ok
    assert not hasattr(oodocs, "Algorithm")
    assert not hasattr(oodocs, "Shape")
    assert not hasattr(oodocs, "Todo")
    assert engineering.Algorithm.__name__ == "Algorithm"
    assert positioning.Shape.__name__ == "Shape"
    assert positioning.TextBox.__name__ == "TextBox"
    assert review.MarginNote.__name__ == "MarginNote"
    assert review.Todo.__name__ == "Todo"
    assert callable(apidoc.collect_api)


def test_leaf_component_modules_hide_internal_helpers_from_all() -> None:
    forbidden_by_module = {
        base_components: {"coerce_blocks"},
        block_components: {
            "coerce_cell",
            "coerce_list_item",
        },
        inline_components: {
            "coerce_inlines",
            "MarginNote",
            "Todo",
            "margin_note",
            "todo",
        },
        media_components: {
            "build_table_layout",
            "coerce_column_spec",
            "coerce_crop_box",
            "coerce_image_source",
            "coerce_table_cell",
            "image_source_to_buffer",
            "image_source_to_bytes",
            "normalize_media_placement",
            "normalize_table_split",
            "TableLayout",
            "TablePlacement",
        },
        positioning_components: {
            "coerce_page_item_scope",
            "coerce_positioned_items",
            "resolve_positioned_boxes",
        },
        people_components: {
            "coerce_author_layout",
            "coerce_authors",
        },
        references: {
            "coerce_citation_library",
            "normalize_citation_style",
            "normalize_reference_style",
            "normalize_reference_sort",
        },
    }

    for module, forbidden_names in forbidden_by_module.items():
        assert forbidden_names.isdisjoint(module.__all__), module.__name__
        for name in forbidden_names:
            assert hasattr(module, name), f"{module.__name__}.{name}"


def test_tier_two_namespaces_export_domain_symbols() -> None:
    expected_exports = {
        chemistry: {
            "ChemicalFormula",
            "ReactionEquation",
            "ce",
            "chemical_formula",
        },
        review: {"MarginNote", "Todo", "margin_note", "todo"},
        glossary: {"Acronym", "Glossary", "ListOfGlossaryTerms", "GlossaryTerm"},
        importers: {
            "ImportIssue",
            "ImportPolicyError",
            "ImportResult",
            "NotebookImportOptions",
            "from_markdown",
            "from_markdown_file",
            "from_notebook",
            "parse_markdown",
            "parse_markdown_file",
            "parse_notebook",
        },
        media: {
            "ColumnSpec",
            "CropBox",
            "SubTable",
            "SubTableGroup",
            "TableOverflowPolicy",
        },
        pdf: {"PdfPages"},
        positioning: {"ImageBox", "PageItemScope", "Shape", "TextBox"},
        reference_helpers: {
            "ReferenceFormat",
            "page_ref",
            "paren_ref",
            "ref",
            "ref_range",
            "refs",
        },
        workflows: {
            "OutputBundle",
            "PYTHON_DOCUMENT_NAMES",
            "PYTHON_FACTORY_NAMES",
            "build_source_outputs",
            "load_document_from_python",
            "load_source_document",
            "save_document_outputs",
            "validate_source_document",
        },
        structure: {
            "Appendix",
            "Assumption",
            "Axiom",
            "Claim",
            "Conjecture",
            "CountableBlock",
            "Corollary",
            "Definition",
            "Example",
            "Lemma",
            "Proof",
            "Proposition",
            "Remark",
            "Theorem",
            "create_countable_block_type",
        },
        generated: {
            "ListOfComments",
            "ListOfFootnotes",
            "ListOfGlossaryTerms",
            "ListOfAlgorithms",
            "ListOfFigures",
            "ListOfTables",
            "ListOfReferences",
            "TableOfContents",
        },
        generated_styles: {
            "TableOfContentsLevelStyle",
        },
        engineering: {
            "Algorithm",
        },
        equations: {
            "AlignedEquation",
            "CasesEquation",
        },
    }

    for name in ("MarginNote", "Todo", "margin_note", "todo"):
        assert not hasattr(components, name)

    for module, names in expected_exports.items():
        assert names == set(module.__all__)
        for name in names:
            assert hasattr(module, name)
            if hasattr(oodocs, name):
                assert getattr(module, name) is getattr(oodocs, name)


def test_preset_namespaces_keep_component_and_template_boundaries() -> None:
    component_preset_names = {
        "CalloutBox",
        "CompactTable",
        "info_box",
        "KeyValueTable",
        "Nomenclature",
        "note_box",
        "option_table",
        "success_box",
        "warning_box",
    }
    template_preset_names = {
        "BookTemplate",
        "CoverPagePreset",
        "JournalArticleTemplate",
        "ManuscriptSection",
        "SoftwareManualTemplate",
        "TechnicalReportTemplate",
    }
    all_preset_names = component_preset_names | template_preset_names

    assert set(preset_components.__all__) == component_preset_names
    assert set(preset_templates.__all__) == template_preset_names
    assert set(presets.__all__) == all_preset_names
    assert all_preset_names.isdisjoint(oodocs.__all__)

    for name in component_preset_names:
        assert getattr(presets, name) is getattr(preset_components, name)
    for name in template_preset_names:
        assert getattr(presets, name) is getattr(preset_templates, name)

    cover = preset_templates.CoverPagePreset.eplus_simple()
    settings_parameters = set(inspect.signature(cover.settings).parameters)

    assert "overlays" in settings_parameters
    assert "page_items" not in settings_parameters
    assert hasattr(cover, "overlays")
    assert not hasattr(cover, "page_items")


def test_top_level_public_api_uses_completed_canonical_names() -> None:
    forbidden = {
        "Algorithm",
        "AlignedEquation",
        "Appendix",
        "Assumption",
        "Axiom",
        "CasesEquation",
        "ChemicalFormula",
        "chemical_formula",
        "Claim",
        "ColumnSpec",
        "Conjecture",
        "CountableBlock",
        "Corollary",
        "create_countable_block_type",
        "CropBox",
        "Definition",
        "Example",
        "strike",
        "code",
        "color",
        "countable_kind",
        "from_ipynb",
        "from_markdown",
        "from_markdown_file",
        "from_notebook",
        "parse_ipynb",
        "parse_markdown",
        "parse_markdown_file",
        "parse_notebook",
        "RenderedOutputs",
        "build_source_outputs",
        "build_python_document",
        "CommentsPage",
        "convert_source",
        "FigureList",
        "FootnotesPage",
        "GeneratedPageDefaults",
        "Acronym",
        "Glossary",
        "GlossaryList",
        "ListOfGlossaryTerms",
        "GlossaryTerm",
        "ImageBox",
        "ListOfAlgorithms",
        "MarginNote",
        "Lemma",
        "load_document",
        "load_document_from_python",
        "load_python_document",
        "load_source_document",
        "margin_note",
        "math",
        "markup",
        "MAX_SECTION_LEVEL",
        "MIN_SECTION_LEVEL",
        "NotebookImportOptions",
        "OUTPUT_FORMATS",
        "OutputFormat",
        "ReferencesPage",
        "ReactionEquation",
        "CommentList",
        "FootnoteList",
        "ReferenceList",
        "ReferenceFormat",
        "render_document",
        "Ref",
        "reference",
        "ListOfComments",
        "ListOfFootnotes",
        "Subsubsection",
        "TableList",
        "Todo",
        "todo",
        "BlockOptions",
        "CaptionOptions",
        "CitationOptions",
        "GeneratedPageOptions",
        "PageNumberOptions",
        "PageItemScope",
        "page_ref",
        "paren_ref",
        "PdfPages",
        "ParagraphTitleStyle",
        "Proof",
        "Proposition",
        "Shape",
        "Remark",
        "SubTable",
        "SubTableGroup",
        "TableOverflowPolicy",
        "save_document_outputs",
        "section_for_level",
        "styled",
        "TitleMatterOptions",
        "TextBox",
        "Theorem",
        "TableOfContentsLevelStyle",
        "TypographyOptions",
        "shift_heading_level",
        "shift_heading_levels",
        "validate_source",
        "validate_source_document",
    }
    expected = {
        "strikethrough",
        "inline_code",
        "inline_math",
        "text_color",
        "OutputBundle",
        "FootnoteDefaults",
        "FootnoteStyle",
        "ListOfFigures",
        "ListOfTables",
        "BlockDefaults",
        "CaptionDefaults",
        "CitationDefaults",
        "GeneratedContentDefaults",
        "HeaderFooterDefaults",
        "LocaleDefaults",
        "PageNumberDefaults",
        "RunInTitleStyle",
        "ListOfReferences",
        "ResultLike",
        "SubSubsection",
        "TitleMatterDefaults",
        "TypographyDefaults",
    }

    assert forbidden.isdisjoint(oodocs.__all__)
    assert not any(hasattr(oodocs, name) for name in forbidden)
    assert expected <= set(oodocs.__all__)
    assert hasattr(block_components, "section_for_level")
    assert hasattr(block_components, "shift_heading_level")
    assert hasattr(block_components, "shift_heading_levels")
    assert hasattr(markup_components, "markup")
    assert hasattr(inline_components, "styled")


def test_apidoc_namespace_uses_canonical_exports() -> None:
    forbidden = {
        "ApiDocProfile",
        "ApiRaises",
        "api_package_to_document",
        "api_coverage_to_chapter",
        "api_diff_to_chapter",
        "api_objects_to_summary_table",
        "api_object_to_help_section",
        "profile_names",
        "register_profile",
        "resolve_profile",
        "api_package_to_help_book",
    }
    expected = {
        "ApiPresentationProfile",
        "ApiException",
        "presentation_profile_names",
        "register_presentation_profile",
        "resolve_presentation_profile",
    }

    assert forbidden.isdisjoint(apidoc.__all__)
    assert not any(hasattr(apidoc, name) for name in forbidden)
    assert expected <= set(apidoc.__all__)


def test_text_style_uses_canonical_field_names() -> None:
    field_names = {field.name for field in fields(oodocs.TextStyle)}

    assert {"color", "all_caps"}.isdisjoint(field_names)
    assert {"text_color", "uppercase"} <= field_names


def test_highlight_helpers_use_highlight_color_parameter_name() -> None:
    for callable_obj in (
        inline_components.Highlight,
        oodocs.highlight,
    ):
        parameters = set(inspect.signature(callable_obj).parameters)

        assert "color" not in parameters
        assert "highlight_color" in parameters


def test_text_class_keeps_only_canonical_classmethod_helpers() -> None:
    members = _public_members(oodocs.Text)
    forbidden = {
        "bold",
        "italic",
        "inline_code",
        "text_color",
        "highlight",
        "strikethrough",
        "superscript",
        "subscript",
    }

    assert forbidden.isdisjoint(members)
    assert {"styled", "from_markup"} <= members


def test_citation_defaults_use_style_field_names() -> None:
    citation_fields = {field.name for field in fields(oodocs.CitationDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}

    assert {"citation_format", "reference_format"}.isdisjoint(citation_fields)
    assert {"citation_style", "reference_style", "reference_sort"} <= citation_fields
    assert {"citation_format", "reference_format"}.isdisjoint(theme_fields)
    assert {"citation_style", "reference_style"}.isdisjoint(theme_fields)
    assert "citation_options" not in theme_fields
    assert "citations" in theme_fields
    assert "normalize_citation_format" not in references.__all__
    assert "normalize_reference_format" not in references.__all__
    assert "normalize_citation_style" not in references.__all__
    assert "normalize_reference_style" not in references.__all__
    assert "normalize_reference_sort" not in references.__all__


def test_list_style_uses_counter_style_marker_field() -> None:
    field_names = {field.name for field in fields(oodocs.ListStyle)}

    assert {"marker_format", "marker_counter_format", "bullet", "prefix", "suffix"}.isdisjoint(
        field_names
    )
    assert "marker" in field_names
    assert isinstance(oodocs.ListStyle().marker, oodocs.CounterStyle)


def test_heading_numbering_uses_counter_style_level_fields() -> None:
    field_names = {field.name for field in fields(oodocs.HeadingNumbering)}

    assert {"formats", "level_counter_formats"}.isdisjoint(field_names)
    assert "level_styles" in field_names
    assert all(isinstance(style, oodocs.CounterStyle) for style in oodocs.HeadingNumbering().level_styles)


def test_page_and_part_numbering_use_template_and_counter_field_names() -> None:
    page_number_fields = {field.name for field in fields(oodocs.PageNumberDefaults)}
    block_fields = {field.name for field in fields(oodocs.BlockDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}

    forbidden_page_fields = {
        "page_number_format",
        "front_matter_page_number_format",
        "main_matter_page_number_format",
        "front_matter_counter_format",
        "main_matter_counter_format",
    }
    expected_page_fields = {
        "page_number_template",
        "front_matter_counter",
        "main_matter_counter",
    }

    assert forbidden_page_fields.isdisjoint(page_number_fields)
    assert expected_page_fields <= page_number_fields
    assert {"part_number_format", "part_counter_format"}.isdisjoint(block_fields)
    assert "part_counter" in block_fields
    assert forbidden_page_fields.isdisjoint(theme_fields)
    assert expected_page_fields.isdisjoint(theme_fields)
    assert "part_number_format" not in theme_fields
    assert "part_counter_format" not in theme_fields
    assert isinstance(oodocs.PageNumberDefaults().front_matter_counter, oodocs.CounterStyle)
    assert isinstance(oodocs.BlockDefaults().part_counter, oodocs.CounterStyle)


def test_generated_content_defaults_use_document_language_field_names() -> None:
    generated_fields = {field.name for field in fields(oodocs.GeneratedContentDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}
    forbidden_fields = {
        "comments_title",
        "footnotes_title",
        "glossary_list_title",
        "references_title",
        "contents_title",
        "generated_section_level",
        "generated_page_breaks",
    }
    expected_fields = {
        "list_of_comments_title",
        "list_of_footnotes_title",
        "list_of_references_title",
        "list_of_glossary_terms_title",
        "table_of_contents_title",
        "generated_heading_level",
        "generated_content_page_breaks",
    }

    assert forbidden_fields.isdisjoint(generated_fields)
    assert expected_fields <= generated_fields
    assert forbidden_fields.isdisjoint(theme_fields)
    assert expected_fields.isdisjoint(theme_fields)
    assert "generated_pages" not in theme_fields
    assert "generated_content" in theme_fields


def test_run_in_title_style_uses_canonical_names() -> None:
    block_fields = {field.name for field in fields(oodocs.BlockDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}

    assert "paragraph_title_style" not in block_fields
    assert "run_in_title_style" in block_fields
    assert "paragraph_title_style" not in theme_fields
    assert "run_in_title_style" not in theme_fields


def test_theme_constructor_uses_grouped_defaults_only() -> None:
    theme_parameters = set(inspect.signature(oodocs.Theme).parameters)
    grouped_parameters = {
        "typography",
        "captions",
        "citations",
        "generated_content",
        "locale",
        "page_numbers",
        "header_footer",
        "title_matter",
        "blocks",
    }
    direct_parameters = {
        "page_background_color",
        "body_font_name",
        "paragraph_text_alignment",
        "run_in_title_style",
        "caption_text_alignment",
        "table_block_alignment",
        "citation_style",
        "reference_style",
        "show_page_numbers",
        "page_number_template",
        "title_text_alignment",
    }

    assert grouped_parameters <= theme_parameters
    assert direct_parameters.isdisjoint(theme_parameters)


def test_document_settings_use_overlays_for_page_positioned_items() -> None:
    parameters = set(inspect.signature(oodocs.DocumentSettings).parameters)
    overlay = positioning.TextBox("DRAFT", width=1.0, height=0.2)
    forbidden = {
        "metadata_author",
        "summary",
        "page_size",
        "page_margins",
        "subtitle",
        "authors",
        "author_layout",
        "cover_page",
    }

    assert forbidden.isdisjoint(parameters)
    assert {"metadata", "title_matter", "page_layout"} <= parameters
    assert "overlays" in parameters
    assert "page_items" not in parameters
    settings = oodocs.DocumentSettings(overlays=[overlay])
    for name in forbidden:
        assert not hasattr(settings, name)
    assert isinstance(settings.title_matter, oodocs.TitleMatter)
    assert settings.overlays == (overlay,)
    assert not hasattr(settings, "page_items")


def test_title_matter_owns_visible_title_fields() -> None:
    parameters = set(inspect.signature(oodocs.TitleMatter).parameters)
    field_names = {field.name for field in fields(oodocs.TitleMatter)}
    expected = {"subtitle", "authors", "author_layout", "cover_page"}

    assert expected <= parameters
    assert expected == field_names
    title_matter = oodocs.TitleMatter(
        subtitle="Visible subtitle",
        authors=[oodocs.Author("Jane Doe")],
        cover_page=True,
    )
    assert title_matter.subtitle is not None
    assert title_matter.subtitle[0].plain_text() == "Visible subtitle"
    assert title_matter.authors[0].name == "Jane Doe"
    assert title_matter.cover_page is True


def test_theme_resolver_methods_use_explicit_resolve_names() -> None:
    members = _public_members(oodocs.Theme)
    forbidden = {
        "heading_size",
        "heading_emphasis",
        "heading_alignment",
        "table_caption_label_text",
        "figure_caption_label_text",
        "table_reference_label_text",
        "figure_reference_label_text",
    }
    expected = {
        "resolve_body_font",
        "resolve_monospace_font",
        "resolve_heading_style",
        "resolve_heading_size",
        "resolve_heading_emphasis",
        "resolve_heading_text_alignment",
        "resolve_paragraph_text_alignment",
        "resolve_caption_label",
        "resolve_generated_page_title",
        "resolve_header_footer_template",
        "resolve_language_tag",
        "resolve_run_in_title_style",
    }

    assert forbidden.isdisjoint(members)
    assert expected <= members


def test_paragraph_style_uses_text_alignment_names() -> None:
    paragraph_style_fields = {field.name for field in fields(oodocs.ParagraphStyle)}
    block_fields = {field.name for field in fields(oodocs.BlockDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}

    assert "alignment" not in paragraph_style_fields
    assert "text_alignment" in paragraph_style_fields
    assert "paragraph_alignment" not in block_fields
    assert "paragraph_text_alignment" in block_fields
    assert "paragraph_alignment" not in theme_fields
    assert "paragraph_text_alignment" not in theme_fields

    for cls in (oodocs.Paragraph, oodocs.CodeBlock, oodocs.Equation):
        parameters = set(inspect.signature(cls).parameters)
        assert "alignment" not in parameters, cls.__name__
        assert "text_alignment" in parameters, cls.__name__


def test_theme_caption_and_title_matter_use_text_alignment_names() -> None:
    caption_fields = {field.name for field in fields(oodocs.CaptionDefaults)}
    title_matter_fields = {field.name for field in fields(oodocs.TitleMatterDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}
    theme_parameters = set(inspect.signature(oodocs.Theme).parameters)

    assert "caption_alignment" not in caption_fields
    assert "caption_text_alignment" in caption_fields
    assert "caption_alignment" not in theme_fields
    assert "caption_text_alignment" not in theme_fields
    assert "caption_alignment" not in theme_parameters
    assert "caption_text_alignment" not in theme_parameters

    forbidden = {
        "title_alignment",
        "subtitle_alignment",
        "author_alignment",
        "affiliation_alignment",
        "author_detail_alignment",
    }
    expected = {
        "title_text_alignment",
        "subtitle_text_alignment",
        "author_text_alignment",
        "affiliation_text_alignment",
        "author_detail_text_alignment",
    }

    assert forbidden.isdisjoint(title_matter_fields)
    assert expected <= title_matter_fields
    assert forbidden.isdisjoint(theme_fields)
    assert expected.isdisjoint(theme_fields)
    assert forbidden.isdisjoint(theme_parameters)
    assert expected.isdisjoint(theme_parameters)


def test_image_components_use_image_format_field_name() -> None:
    for cls in (
        oodocs.ImageData,
        oodocs.Figure,
        oodocs.SubFigure,
        positioning.ImageBox,
    ):
        field_names = {field.name for field in fields(cls)}
        assert "format" not in field_names, cls.__name__
        assert "image_format" in field_names, cls.__name__


def test_image_public_signatures_use_image_format_parameter_name() -> None:
    for callable_obj in (
        oodocs.ImageData,
        oodocs.ImageData.savefig,
        oodocs.Figure,
        oodocs.Figure.from_bytes,
        oodocs.Figure.from_buffer,
        oodocs.SubFigure,
        positioning.ImageBox,
    ):
        parameters = set(inspect.signature(callable_obj).parameters)

        assert "format" not in parameters, callable_obj
        if callable_obj is not oodocs.ImageData.savefig:
            assert "image_format" in parameters, callable_obj


def test_image_components_use_image_dpi_field_name() -> None:
    for cls in (oodocs.Figure, oodocs.SubFigure, positioning.ImageBox):
        field_names = {field.name for field in fields(cls)}
        assert "dpi" not in field_names, cls.__name__
        assert "image_dpi" in field_names, cls.__name__


def test_image_public_signatures_use_image_dpi_parameter_name() -> None:
    for callable_obj in (
        oodocs.Figure,
        oodocs.SubFigure,
        positioning.ImageBox,
    ):
        parameters = set(inspect.signature(callable_obj).parameters)

        assert "dpi" not in parameters, callable_obj
        assert "image_dpi" in parameters, callable_obj


def test_table_public_api_hides_renderer_helper_methods() -> None:
    members = _public_members(oodocs.Table)
    from_records_parameters = set(inspect.signature(oodocs.Table.from_records).parameters)

    forbidden = {
        "layout",
        "row_count",
        "resolved_split",
        "resolved_placement",
        "effective_cell_style",
        "column_widths_in_inches",
    }
    expected = {
        "total_row_count",
        "from_csv",
        "from_dataframe",
        "from_records",
        "from_tsv",
        "grouped_headers",
        "excerpt",
        "save_csv",
    }

    assert forbidden.isdisjoint(members)
    assert expected <= members
    assert "strict" not in from_records_parameters
    assert "fail_on_missing" in from_records_parameters


def test_adapter_public_api_uses_canonical_missing_input_policy_names() -> None:
    forbidden_exports = {
        "EvidenceBundle",
        "build_release_evidence_bundle",
        "build_release_evidence_document",
        "section_from_github_workflow",
        "section_from_manifest",
        "section_from_pyproject",
        "table_from_csv",
        "table_from_records",
        "table_from_tsv",
    }
    expected_exports = {
        "GithubWorkflowSummary",
        "ProjectMetadata",
        "ReleaseEvidence",
        "ReleaseEvidenceBundle",
        "ReleaseManifestSummary",
    }

    assert forbidden_exports.isdisjoint(adapters.__all__)
    assert not any(hasattr(adapters, name) for name in forbidden_exports)
    assert expected_exports <= set(adapters.__all__)

    for method in (adapters.ReleaseEvidence.to_document, adapters.ReleaseEvidence.save_bundle):
        parameters = set(inspect.signature(method).parameters)

        assert "strict" not in parameters, method.__name__
        assert "fail_on_missing_input" not in parameters, method.__name__
        assert "missing_input_policy" in parameters, method.__name__

    for method_name in ("create_skeleton", "ensure_inputs"):
        assert hasattr(adapters.ReleaseEvidence, method_name)


def test_table_cell_alignment_fields_use_text_alignment_names() -> None:
    cell_style_fields = {field.name for field in fields(oodocs.TableCellStyle)}
    cell_fields = {field.name for field in fields(oodocs.TableCell)}
    table_style_fields = {field.name for field in fields(oodocs.TableStyle)}
    table_parameters = set(inspect.signature(oodocs.Table).parameters)
    table_cell_parameters = set(inspect.signature(oodocs.TableCell).parameters)
    dataframe_parameters = set(inspect.signature(oodocs.Table.from_dataframe).parameters)

    assert "horizontal_alignment" not in cell_style_fields
    assert "text_alignment" in cell_style_fields
    assert "horizontal_alignment" not in cell_fields
    assert "text_alignment" in cell_fields
    assert "horizontal_alignment" not in table_cell_parameters
    assert "text_alignment" in table_cell_parameters

    forbidden_table_names = {"cell_horizontal_alignment", "header_horizontal_alignment"}
    expected_table_names = {"cell_text_alignment", "header_text_alignment"}

    assert forbidden_table_names.isdisjoint(table_style_fields)
    assert expected_table_names <= table_style_fields
    assert forbidden_table_names.isdisjoint(table_parameters)
    assert expected_table_names <= table_parameters
    assert forbidden_table_names.isdisjoint(dataframe_parameters)
    assert expected_table_names <= dataframe_parameters


def test_block_alignment_fields_use_block_alignment_names() -> None:
    box_style_fields = {field.name for field in fields(oodocs.BoxStyle)}
    block_fields = {field.name for field in fields(oodocs.BlockDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}
    box_parameters = set(inspect.signature(oodocs.Box).parameters)
    theme_parameters = set(inspect.signature(oodocs.Theme).parameters)

    assert "alignment" not in box_style_fields
    assert "block_alignment" in box_style_fields
    assert "alignment" not in box_parameters
    assert "block_alignment" in box_parameters

    forbidden = {"table_alignment", "figure_alignment", "box_alignment"}
    expected = {
        "table_block_alignment",
        "figure_block_alignment",
        "box_block_alignment",
    }

    assert forbidden.isdisjoint(block_fields)
    assert expected <= block_fields
    assert forbidden.isdisjoint(theme_fields)
    assert expected.isdisjoint(theme_fields)
    assert forbidden.isdisjoint(theme_parameters)
    assert expected.isdisjoint(theme_parameters)


def test_textbox_uses_explicit_alignment_field_names() -> None:
    field_names = {field.name for field in fields(positioning.TextBox)}
    parameter_names = set(inspect.signature(positioning.TextBox).parameters)

    assert {"align", "valign"}.isdisjoint(field_names)
    assert {"text_alignment", "vertical_alignment"} <= field_names
    assert {"align", "valign"}.isdisjoint(parameter_names)
    assert {"text_alignment", "vertical_alignment"} <= parameter_names


def test_api_renderer_note_uses_output_format_field_name() -> None:
    field_names = {field.name for field in fields(apidoc.ApiRendererNote)}

    assert "format" not in field_names
    assert "output_format" in field_names


def test_result_objects_share_resultlike_api_names() -> None:
    assert "ResultLike" in oodocs.__all__
    required_members = {
        "ok",
        "errors",
        "warnings",
        "infos",
        "to_dict",
        "from_dict",
        "to_json",
        "from_json",
        "save_json",
        "load_json",
        "to_table",
        "format_text",
    }
    forbidden_members = {
        "write_json",
        "read_json",
        "write_csv",
        "format_table",
        "format_issues",
    }

    for result_type in (
        oodocs.ValidationResult,
        oodocs.ImportResult,
        apidoc.ApiCoverageResult,
        apidoc.ApiDiffResult,
    ):
        members = _public_members(result_type)
        row_helpers = {
            name
            for name in members
            if name == "to_row"
            or (name.startswith("to_") and name.endswith("_row"))
            or (name.startswith("as_") and name.endswith("_row"))
        }

        assert required_members <= members, result_type.__name__
        assert forbidden_members.isdisjoint(members), result_type.__name__
        assert not row_helpers, result_type.__name__


def test_import_issue_uses_line_number_field_name() -> None:
    field_names = {field.name for field in fields(oodocs.ImportIssue)}
    issue = oodocs.ImportIssue(
        "warning",
        "raw-html-unsupported",
        "Raw HTML was imported as plain text.",
        line_number=4,
    )

    assert "line" not in field_names
    assert "line_number" in field_names
    assert "line" not in issue.to_dict()
    assert issue.to_dict()["line_number"] == 4


def test_issue_objects_share_common_location_fields() -> None:
    expected_fields = {"severity", "code", "message", "source", "path", "line_number"}

    for issue_type in (
        oodocs.ValidationIssue,
        oodocs.ImportIssue,
        apidoc.ApiDocIssue,
    ):
        field_names = {field.name for field in fields(issue_type)}
        assert expected_fields <= field_names
        assert "as_issue_row" in _public_members(issue_type)

    validation_issue = oodocs.ValidationIssue(
        "warning",
        "custom-warning",
        "Review this imported block.",
        source="notes.md",
        path="document.body.children[0]",
        line_number=12,
        formats=("html",),
    )
    api_issue = apidoc.ApiDocIssue(
        "warning",
        "missing-docstring",
        "No docstring.",
        source="griffe",
        qualname="pkg.Widget",
    )

    assert validation_issue.to_dict()["source"] == "notes.md"
    assert validation_issue.to_dict()["line_number"] == 12
    assert api_issue.to_dict()["source"] == "griffe"
    assert validation_issue.as_issue_row()[3] == "notes.md"
    assert api_issue.as_issue_row()[4] == "griffe"


def test_import_policy_names_describe_lossy_behavior() -> None:
    assert normalize_import_policy(" ALLOW-LOSSY ") == "allow-lossy"
    assert normalize_import_policy("record-lossy") == "record-lossy"
    assert normalize_import_policy("fail-on-lossy") == "fail-on-lossy"

    for old_policy in ("lossy", "warn", "strict"):
        with pytest.raises(ValueError):
            normalize_import_policy(old_policy)


def test_parse_importers_return_import_result_without_diagnostics_switch() -> None:
    for callable_obj in (
        importers.parse_markdown,
        importers.parse_markdown_file,
        importers.parse_notebook,
    ):
        assert "diagnostics" not in inspect.signature(callable_obj).parameters

    markdown_result = importers.parse_markdown("# Title")
    notebook_result = importers.parse_notebook(
        {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {},
            "cells": [],
        }
    )

    assert isinstance(markdown_result, oodocs.ImportResult)
    assert isinstance(notebook_result, oodocs.ImportResult)


def test_notebook_import_options_use_explicit_field_names() -> None:
    option_fields = {field.name for field in fields(importers.NotebookImportOptions)}
    forbidden = {"include_raw", "code_language", "image_caption"}
    expected = {"include_raw_cells", "default_code_language", "output_image_caption"}

    assert forbidden.isdisjoint(option_fields)
    assert expected <= option_fields

    for callable_obj in (
        importers.parse_notebook,
        importers.from_notebook,
        oodocs.Document.from_notebook,
    ):
        parameters = set(inspect.signature(callable_obj).parameters)
        assert forbidden.isdisjoint(parameters)
        assert {"include_raw_cells", "default_code_language"} <= parameters


def test_workflow_api_uses_formats_parameter_name() -> None:
    for callable_obj in (
        workflows.save_document_outputs,
        workflows.build_source_outputs,
        workflows.validate_source_document,
    ):
        parameters = inspect.signature(callable_obj).parameters

        assert "formats" in parameters
        assert "outputs" not in parameters


def test_block_renderer_hooks_are_private() -> None:
    forbidden = {"render_to_docx", "render_to_pdf", "render_to_html"}
    expected_private = {"_render_to_docx", "_render_to_pdf", "_render_to_html"}

    for cls in (
        base_components.Block,
        base_components.Body,
        oodocs.Paragraph,
        oodocs.Table,
        oodocs.Figure,
        oodocs.TableOfContents,
    ):
        public_members = _public_members(cls)
        all_members = {name for name, _ in inspect.getmembers(cls)}

        assert forbidden.isdisjoint(public_members), cls.__name__
        assert expected_private <= all_members, cls.__name__


def test_reference_targets_use_ref_method_name() -> None:
    for cls in (
        base_components.Block,
        oodocs.Paragraph,
        oodocs.Table,
        oodocs.Figure,
        oodocs.SubFigure,
        media.SubTable,
        media.SubTableGroup,
    ):
        members = _public_members(cls)

        assert "ref" in members, cls.__name__
        assert "reference" not in members, cls.__name__


def test_raw_value_helpers_use_as_prefix() -> None:
    forbidden_by_class = {
        oodocs.ValidationIssue: {"to_row", "to_issue_row"},
        oodocs.ImportIssue: {"to_row", "to_issue_row"},
        apidoc.ApiParameter: {"to_row", "to_table_cell_values"},
        apidoc.ApiReturn: {"to_row"},
        apidoc.ApiException: {"to_row"},
        apidoc.ApiExample: {"to_row", "to_block"},
        apidoc.ApiSeeAlso: {"to_row"},
        apidoc.ApiRendererNote: {"to_row"},
        apidoc.ApiDocIssue: {"to_row"},
        apidoc.ApiObject: {
            "to_summary_row",
            "to_index_row",
            "to_doc_issue_rows",
            "to_issue_rows",
        },
    }

    expected_by_class = {
        oodocs.ValidationIssue: {"as_issue_row"},
        oodocs.ImportIssue: {"as_issue_row"},
        apidoc.ApiParameter: {"as_table_cells", "as_parameter_row"},
        apidoc.ApiReturn: {"as_return_row"},
        apidoc.ApiException: {"as_exception_row"},
        apidoc.ApiExample: {"as_example_row", "to_code_block"},
        apidoc.ApiSeeAlso: {"as_record", "as_see_also_row"},
        apidoc.ApiRendererNote: {"as_output_note_row"},
        apidoc.ApiDocIssue: {"as_issue_row"},
        apidoc.ApiObject: {"as_summary_row", "as_index_row", "as_issue_rows"},
    }

    for cls, forbidden in forbidden_by_class.items():
        members = _public_members(cls)
        assert forbidden.isdisjoint(members), cls.__name__
        assert expected_by_class[cls] <= members, cls.__name__

        for member_name in expected_by_class[cls]:
            if member_name.startswith("as_") and (
                member_name.endswith("_row") or member_name.endswith("_cells")
            ):
                signature = inspect.signature(getattr(cls, member_name))
                assert signature.return_annotation == "list[object]", member_name


def test_public_api_uses_global_conversion_io_prefix_rules() -> None:
    forbidden_exact_names = {
        "write_json",
        "read_json",
        "write_csv",
        "format_table",
        "format_issues",
    }
    forbidden_prefixes = ("write_", "read_")

    for module_name, export_name, obj in _public_api_exports():
        assert export_name not in forbidden_exact_names, f"{module_name}.{export_name}"
        assert not export_name.startswith(forbidden_prefixes), f"{module_name}.{export_name}"

        if not inspect.isclass(obj):
            continue

        members = _public_members(obj)
        forbidden_members = {
            name
            for name in members
            if name in forbidden_exact_names or name.startswith(forbidden_prefixes)
        }
        to_row_helpers = {
            name
            for name in members
            if name == "to_row" or (name.startswith("to_") and name.endswith("_row"))
        }

        assert not forbidden_members, (
            f"{module_name}.{export_name}: {sorted(forbidden_members)}"
        )
        assert not to_row_helpers, f"{module_name}.{export_name}: {sorted(to_row_helpers)}"


def test_apidoc_raw_text_helpers_stay_model_scoped() -> None:
    raw_text_helpers = {
        "annotation_text",
        "default_text",
        "signature_text",
        "summary_text",
    }
    expected_owners = {
        "oodocs.apidoc:ApiParameter.annotation_text",
        "oodocs.apidoc:ApiParameter.default_text",
        "oodocs.apidoc:ApiObject.signature_text",
        "oodocs.apidoc:ApiObject.summary_text",
    }
    owners: set[str] = set()

    for module_name, export_name, obj in _public_api_exports():
        if not inspect.isclass(obj):
            continue
        for member_name in raw_text_helpers & _public_members(obj):
            owners.add(f"{module_name}:{export_name}.{member_name}")

    assert owners == expected_owners


def test_apidoc_selection_and_json_api_use_canonical_names() -> None:
    forbidden_by_class = {
        apidoc.ApiObject: {"select", "find"},
        apidoc.ApiModule: {"select", "find", "classes", "functions", "attributes", "properties"},
        apidoc.ApiPackage: {
            "select",
            "filtered",
            "find",
            "modules_by_name",
            "classes",
            "functions",
            "methods",
            "attributes",
            "properties",
            "public_objects",
            "private_objects",
            "undocumented_public_objects",
            "to_document",
            "write_json",
            "read_json",
        },
        apidoc.ApiSnapshot: {"write_json", "read_json"},
        apidoc.ApiDiffResult: {"write_json", "read_json"},
        apidoc.ApiCoverageResult: {"write_json", "read_json", "write_csv"},
        apidoc.ApiCollectConfig: {"write_json", "read_json", "read_file"},
        apidoc.ApiHelpBookConfig: {
            "write_json",
            "read_json",
            "read_file",
            "write_pyproject",
            "write_snapshot",
        },
    }

    expected_by_class = {
        apidoc.ApiObject: {"select_members", "find_member"},
        apidoc.ApiModule: {
            "select_objects",
            "find_object",
            "select_classes",
            "select_functions",
            "select_attributes",
            "select_properties",
        },
        apidoc.ApiPackage: {
            "select_objects",
            "subset",
            "find_module",
            "find_object",
            "require_module",
            "require_object",
            "module_map",
            "select_classes",
            "select_functions",
            "select_methods",
            "select_attributes",
            "select_properties",
            "select_public_objects",
            "select_private_objects",
            "select_undocumented_public_objects",
            "to_help_book",
            "save_json",
            "load_json",
        },
        apidoc.ApiSnapshot: {"save_json", "load_json"},
        apidoc.ApiDiffResult: {"save_json", "load_json"},
        apidoc.ApiCoverageResult: {"save_json", "load_json", "save_csv"},
        apidoc.ApiCollectConfig: {"save_json", "load_json", "load_file"},
        apidoc.ApiHelpBookConfig: {
            "save_json",
            "load_json",
            "load_file",
            "save_pyproject",
            "save_snapshot",
        },
    }

    for cls, forbidden in forbidden_by_class.items():
        members = _public_members(cls)
        assert forbidden.isdisjoint(members), cls.__name__
        assert expected_by_class[cls] <= members, cls.__name__


def test_apidoc_heading_depth_uses_explicit_parameter_name() -> None:
    config_fields = {field.name for field in fields(apidoc.ApiHelpBookConfig)}
    assert "max_level" not in config_fields
    assert "max_heading_level" in config_fields

    callables = (
        apidoc.ApiObject.to_blocks,
        apidoc.ApiObject.to_section,
        apidoc.ApiModule.to_sections,
        apidoc.ApiModule.to_chapter,
        apidoc.ApiModule.to_blocks,
        apidoc.ApiPackage.to_sections,
        apidoc.ApiPackage.to_chapters,
        apidoc.ApiPackage.to_blocks,
        apidoc.ApiPackage.to_help_book,
        apidoc.ApiObject.to_help_section,
        apidoc.api_category_to_chapter,
    )

    for callable_obj in callables:
        parameters = set(inspect.signature(callable_obj).parameters)
        assert "max_level" not in parameters, callable_obj
        assert "max_heading_level" in parameters, callable_obj


def test_cli_help_uses_canonical_option_names(capsys) -> None:
    oodocs_parser = _build_oodocs_parser()
    oodocs_build_help = _subcommand_help(oodocs_parser, ["build"], capsys)
    oodocs_validate_help = _subcommand_help(oodocs_parser, ["validate"], capsys)

    assert "--outputs" in oodocs_build_help
    assert "--source-type" in oodocs_build_help
    assert "--document-factory" in oodocs_build_help
    assert "--fail-on-warning" in oodocs_validate_help
    assert "--report-format" in oodocs_validate_help

    for old_option in ("--to", "--type", "--factory", "--strict", "--format"):
        assert old_option not in oodocs_build_help
        assert old_option not in oodocs_validate_help

    apidoc_parser = _build_apidoc_parser()
    apidoc_help = _subcommand_help(apidoc_parser, [], capsys)
    apidoc_init_help = _subcommand_help(apidoc_parser, ["init"], capsys)
    apidoc_collect_help = _subcommand_help(apidoc_parser, ["collect"], capsys)
    apidoc_check_help = _subcommand_help(apidoc_parser, ["check"], capsys)
    apidoc_snapshot_help = _subcommand_help(apidoc_parser, ["snapshot"], capsys)
    apidoc_diff_help = _subcommand_help(apidoc_parser, ["diff"], capsys)

    for command in ("collect", "check", "snapshot", "diff"):
        assert command in apidoc_help
    assert "build" not in apidoc_help
    assert "--config-format" in apidoc_init_help
    assert "--outputs" in apidoc_init_help
    assert "--max-heading-level" in apidoc_init_help
    assert "--save-json" in apidoc_collect_help
    assert "--report-format" in apidoc_check_help
    assert "--save-json" in apidoc_check_help
    assert "--save-csv" in apidoc_check_help
    assert "--save-json" in apidoc_snapshot_help
    assert "--save-json" in apidoc_diff_help

    for old_option in (
        "--to",
        "--profile",
        "--format",
        "--max-level",
        "--out-json",
        "--out-csv",
        "--base",
        "--head",
    ):
        assert old_option not in apidoc_init_help
        assert old_option not in apidoc_collect_help
        assert old_option not in apidoc_check_help
        assert old_option not in apidoc_snapshot_help
        assert old_option not in apidoc_diff_help
