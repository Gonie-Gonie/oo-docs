from __future__ import annotations

from dataclasses import fields
import inspect

import pytest

import oodocs
import oodocs.apidoc as apidoc
import oodocs.components.references as references
from oodocs.apidoc.cli import _build_parser as _build_apidoc_parser
from oodocs.cli import _build_parser as _build_oodocs_parser


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
        "from_ipynb",
        "parse_ipynb",
        "RenderedOutputs",
        "build_python_document",
        "convert_source",
        "load_document",
        "load_python_document",
        "render_document",
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
        "load_document_from_python",
        "load_source_document",
        "BlockDefaults",
        "CaptionDefaults",
        "CitationDefaults",
        "GeneratedPageDefaults",
        "PageNumberDefaults",
        "RunInTitleStyle",
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
    assert {"citation_style", "reference_style"} <= theme_fields
    assert "citation_options" not in theme_fields
    assert "citations" in theme_fields
    assert "normalize_citation_format" not in references.__all__
    assert "normalize_reference_format" not in references.__all__
    assert "normalize_citation_style" in references.__all__
    assert "normalize_reference_style" in references.__all__


def test_list_style_uses_counter_format_field_name() -> None:
    field_names = {field.name for field in fields(oodocs.ListStyle)}

    assert "marker_format" not in field_names
    assert "marker_counter_format" in field_names


def test_heading_numbering_uses_level_counter_format_field_name() -> None:
    field_names = {field.name for field in fields(oodocs.HeadingNumbering)}

    assert "formats" not in field_names
    assert "level_counter_formats" in field_names


def test_page_and_part_numbering_use_template_and_counter_field_names() -> None:
    page_number_fields = {field.name for field in fields(oodocs.PageNumberDefaults)}
    block_fields = {field.name for field in fields(oodocs.BlockDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}

    forbidden_page_fields = {
        "page_number_format",
        "front_matter_page_number_format",
        "main_matter_page_number_format",
    }
    expected_page_fields = {
        "page_number_template",
        "front_matter_counter_format",
        "main_matter_counter_format",
    }

    assert forbidden_page_fields.isdisjoint(page_number_fields)
    assert expected_page_fields <= page_number_fields
    assert "part_number_format" not in block_fields
    assert "part_counter_format" in block_fields
    assert forbidden_page_fields.isdisjoint(theme_fields)
    assert expected_page_fields <= theme_fields
    assert "part_number_format" not in theme_fields
    assert "part_counter_format" in theme_fields


def test_run_in_title_style_uses_canonical_names() -> None:
    block_fields = {field.name for field in fields(oodocs.BlockDefaults)}
    theme_fields = {field.name for field in fields(oodocs.Theme)}

    assert "paragraph_title_style" not in block_fields
    assert "run_in_title_style" in block_fields
    assert "paragraph_title_style" not in theme_fields
    assert "run_in_title_style" in theme_fields


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
        apidoc.ApiCoverageResult: {"write_json", "read_json"},
        apidoc.ApiCollectConfig: {"write_json", "read_json"},
        apidoc.ApiBuildConfig: {"write_json", "read_json"},
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
        apidoc.ApiCoverageResult: {"save_json", "load_json"},
        apidoc.ApiCollectConfig: {"save_json", "load_json"},
        apidoc.ApiBuildConfig: {"save_json", "load_json"},
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
    apidoc_init_help = _subcommand_help(apidoc_parser, ["init"], capsys)
    apidoc_build_help = _subcommand_help(apidoc_parser, ["build"], capsys)
    apidoc_diff_help = _subcommand_help(apidoc_parser, ["diff"], capsys)

    assert "--config-format" in apidoc_init_help
    assert "--outputs" in apidoc_init_help
    assert "--outputs" in apidoc_build_help
    assert "--presentation-profile" in apidoc_build_help
    assert "--outputs" in apidoc_diff_help

    for old_option in ("--to", "--profile", "--format"):
        assert old_option not in apidoc_init_help
        assert old_option not in apidoc_build_help
        assert old_option not in apidoc_diff_help
