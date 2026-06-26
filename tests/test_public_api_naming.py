from __future__ import annotations

from dataclasses import fields
import inspect

import pytest

import oodocs
import oodocs.adapters as adapters
import oodocs.apidoc as apidoc
import oodocs.components.references as references
from oodocs.apidoc.cli import _build_parser as _build_apidoc_parser
from oodocs.cli import _build_parser as _build_oodocs_parser
from oodocs.importers.results import normalize_import_policy


def _public_members(cls: type[object]) -> set[str]:
    return {name for name, _ in inspect.getmembers(cls) if not name.startswith("_")}


def _subcommand_help(parser, args: list[str], capsys) -> str:
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([*args, "--help"])
    assert exc_info.value.code == 0
    return capsys.readouterr().out


def test_top_level_public_api_uses_completed_canonical_names() -> None:
    forbidden = {
        "strike",
        "code",
        "color",
        "countable_kind",
        "from_ipynb",
        "parse_ipynb",
        "RenderedOutputs",
        "build_python_document",
        "CommentsPage",
        "convert_source",
        "FigureList",
        "FootnotesPage",
        "GeneratedPageDefaults",
        "load_document",
        "load_python_document",
        "ReferencesPage",
        "render_document",
        "Subsubsection",
        "TableList",
        "BlockOptions",
        "CaptionOptions",
        "CitationOptions",
        "GeneratedPageOptions",
        "PageNumberOptions",
        "ParagraphTitleStyle",
        "TitleMatterOptions",
        "TypographyOptions",
        "validate_source",
    }
    expected = {
        "strikethrough",
        "inline_code",
        "text_color",
        "from_notebook",
        "parse_notebook",
        "OutputBundle",
        "build_source_outputs",
        "CommentList",
        "create_countable_block_type",
        "FootnoteList",
        "ListOfFigures",
        "ListOfTables",
        "load_document_from_python",
        "load_source_document",
        "BlockDefaults",
        "CaptionDefaults",
        "CitationDefaults",
        "GeneratedContentDefaults",
        "PageNumberDefaults",
        "RunInTitleStyle",
        "ReferenceList",
        "ResultLike",
        "SubSubsection",
        "TitleMatterDefaults",
        "TypographyDefaults",
        "save_document_outputs",
        "validate_source_document",
    }

    assert forbidden.isdisjoint(oodocs.__all__)
    assert not any(hasattr(oodocs, name) for name in forbidden)
    assert expected <= set(oodocs.__all__)


def test_apidoc_namespace_uses_canonical_exports() -> None:
    forbidden = {
        "ApiDocProfile",
        "ApiRaises",
        "profile_names",
        "register_profile",
        "resolve_profile",
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


def test_citation_defaults_use_style_field_names() -> None:
    citation_fields = {field.name for field in fields(oodocs.CitationDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}

    assert {"citation_format", "reference_format"}.isdisjoint(citation_fields)
    assert {"citation_style", "reference_style"} <= citation_fields
    assert {"citation_format", "reference_format"}.isdisjoint(theme_fields)
    assert {"citation_style", "reference_style"}.isdisjoint(theme_fields)
    assert "citation_options" not in theme_fields
    assert "citations" in theme_fields
    assert "normalize_citation_format" not in references.__all__
    assert "normalize_reference_format" not in references.__all__
    assert "normalize_citation_style" in references.__all__
    assert "normalize_reference_style" in references.__all__


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
        "references_title",
        "contents_title",
        "generated_section_level",
        "generated_page_breaks",
    }
    expected_fields = {
        "comment_list_title",
        "footnote_list_title",
        "reference_list_title",
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
        "page_numbers",
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
        "resolve_heading_size",
        "resolve_heading_emphasis",
        "resolve_heading_text_alignment",
        "resolve_paragraph_text_alignment",
        "resolve_caption_label",
        "resolve_generated_page_title",
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
    for cls in (oodocs.ImageData, oodocs.Figure, oodocs.SubFigure, oodocs.ImageBox):
        field_names = {field.name for field in fields(cls)}
        assert "format" not in field_names, cls.__name__
        assert "image_format" in field_names, cls.__name__


def test_image_components_use_image_dpi_field_name() -> None:
    for cls in (oodocs.Figure, oodocs.SubFigure, oodocs.ImageBox):
        field_names = {field.name for field in fields(cls)}
        assert "dpi" not in field_names, cls.__name__
        assert "image_dpi" in field_names, cls.__name__


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
        assert "fail_on_missing_input" in parameters, method.__name__


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
    field_names = {field.name for field in fields(oodocs.TextBox)}
    parameter_names = set(inspect.signature(oodocs.TextBox).parameters)

    assert {"align", "valign"}.isdisjoint(field_names)
    assert {"text_alignment", "vertical_alignment"} <= field_names
    assert {"align", "valign"}.isdisjoint(parameter_names)
    assert {"text_alignment", "vertical_alignment"} <= parameter_names


def test_api_renderer_note_uses_output_format_field_name() -> None:
    field_names = {field.name for field in fields(apidoc.ApiRendererNote)}

    assert "format" not in field_names
    assert "output_format" in field_names


def test_result_objects_use_format_text_names() -> None:
    assert "ResultLike" in oodocs.__all__
    assert "format_table" not in _public_members(oodocs.ValidationResult)
    assert "format_issues" not in _public_members(oodocs.ImportResult)
    assert "format_text" in _public_members(oodocs.ValidationResult)
    assert "format_text" in _public_members(oodocs.ImportResult)

    validation_result_members = _public_members(oodocs.ValidationResult)
    assert {
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
    } <= validation_result_members
    import_result_members = _public_members(oodocs.ImportResult)
    assert {
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
    } <= import_result_members
    coverage_result_members = _public_members(apidoc.ApiCoverageResult)
    assert {
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
    } <= coverage_result_members
    diff_result_members = _public_members(apidoc.ApiDiffResult)
    assert {
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
    } <= diff_result_members


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
    for callable_obj in (oodocs.parse_markdown, oodocs.parse_markdown_file, oodocs.parse_notebook):
        assert "diagnostics" not in inspect.signature(callable_obj).parameters

    markdown_result = oodocs.parse_markdown("# Title")
    notebook_result = oodocs.parse_notebook(
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
    option_fields = {field.name for field in fields(oodocs.NotebookImportOptions)}
    forbidden = {"include_raw", "code_language", "image_caption"}
    expected = {"include_raw_cells", "default_code_language", "output_image_caption"}

    assert forbidden.isdisjoint(option_fields)
    assert expected <= option_fields

    for callable_obj in (
        oodocs.parse_notebook,
        oodocs.from_notebook,
        oodocs.Document.from_notebook,
    ):
        parameters = set(inspect.signature(callable_obj).parameters)
        assert forbidden.isdisjoint(parameters)
        assert {"include_raw_cells", "default_code_language"} <= parameters


def test_apidoc_raw_value_helpers_use_as_prefix() -> None:
    forbidden_by_class = {
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
        apidoc.ApiParameter: {"as_table_cells", "as_parameter_row"},
        apidoc.ApiReturn: {"as_return_row"},
        apidoc.ApiException: {"as_exception_row"},
        apidoc.ApiExample: {"as_example_row", "to_code_block"},
        apidoc.ApiSeeAlso: {"as_see_also_row"},
        apidoc.ApiRendererNote: {"as_output_note_row"},
        apidoc.ApiDocIssue: {"as_issue_row"},
        apidoc.ApiObject: {"as_summary_row", "as_index_row", "as_issue_rows"},
    }

    for cls, forbidden in forbidden_by_class.items():
        members = _public_members(cls)
        assert forbidden.isdisjoint(members), cls.__name__
        assert expected_by_class[cls] <= members, cls.__name__


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
    assert "--save-json" in apidoc_collect_help
    assert "--report-format" in apidoc_check_help
    assert "--save-json" in apidoc_check_help
    assert "--save-csv" in apidoc_check_help
    assert "--save-json" in apidoc_snapshot_help
    assert "--save-json" in apidoc_diff_help

    for old_option in ("--to", "--profile", "--format", "--out-json", "--out-csv", "--base", "--head"):
        assert old_option not in apidoc_init_help
        assert old_option not in apidoc_collect_help
        assert old_option not in apidoc_check_help
        assert old_option not in apidoc_snapshot_help
        assert old_option not in apidoc_diff_help
