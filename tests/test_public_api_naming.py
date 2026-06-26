from __future__ import annotations

import inspect

import oodocs
import oodocs.apidoc as apidoc


def _public_members(cls: type[object]) -> set[str]:
    return {name for name, _ in inspect.getmembers(cls) if not name.startswith("_")}


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
