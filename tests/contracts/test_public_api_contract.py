from __future__ import annotations

from dataclasses import fields
import inspect

import pytest

import oodocs
import oodocs.apidoc as apidoc
import oodocs.engineering as engineering
import oodocs.importers as importers
import oodocs.pdf as pdf
import oodocs.positioning as positioning
import oodocs.public_api as public_api
import oodocs.review as review
import oodocs.structure as structure
import oodocs.styles as styles
import oodocs.workflows as workflows
from oodocs.evidence import EvidenceReport
from oodocs.integrations.github_actions import collect_github_actions_workflow
from oodocs.integrations.pyproject import collect_pyproject_info
from oodocs.metadata import ManifestSummary, ProjectInfo, WorkflowJob


pytestmark = pytest.mark.contracts


def test_top_level_public_api_matches_tier_policy_and_export_cap() -> None:
    export_names = set(oodocs.__all__)
    tier_names = set(public_api.TOP_LEVEL_SYMBOL_TIERS)
    allowed_tiers = {"core", "domain", "internal"}

    assert len(oodocs.__all__) <= public_api.TOP_LEVEL_EXPORT_LIMIT
    assert export_names == tier_names
    assert set(public_api.TOP_LEVEL_SYMBOL_TIERS.values()) <= allowed_tiers
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


def test_domain_api_stays_in_domain_namespaces() -> None:
    domain_symbols = {
        engineering: {"Algorithm"},
        structure: {"Theorem", "Proof", "Appendix"},
        positioning: {"Shape", "TextBox"},
        review: {"Todo", "MarginNote"},
        pdf: {"PdfPages"},
        importers: {"from_markdown", "parse_notebook"},
        workflows: {"save_document_outputs"},
    }

    for module, names in domain_symbols.items():
        assert names <= set(module.__all__), module.__name__
        for name in names:
            assert hasattr(module, name), f"{module.__name__}.{name}"
            assert name not in oodocs.__all__
            assert not hasattr(oodocs, name), name


def test_representative_stale_top_level_names_are_absent() -> None:
    stale_names = {
        "RenderedOutputs",
        "from_ipynb",
        "parse_ipynb",
        "ParagraphTitleStyle",
        "TypographyOptions",
        "CaptionOptions",
        "TextStyle.color",
        "render_document",
        "reference",
        "Ref",
        "math",
        "Component",
    }

    assert stale_names.isdisjoint(oodocs.__all__)
    assert not any(hasattr(oodocs, name) for name in stale_names)


def test_apidoc_public_contract_keeps_low_level_helpers_out_of_all() -> None:
    expected = {
        "ApiCollectConfig",
        "ApiHelpBookConfig",
        "ApiPackage",
        "ApiModule",
        "ApiObject",
        "ApiParameter",
        "ApiPresentationProfile",
        "check_api_docs",
        "check_api_help_categories",
        "collect_api",
        "diff_api",
    }
    low_level_helpers = {
        "parse_docstring",
        "register_docstring_parser",
        "docstring_parser_names",
        "check_example_syntax",
        "extract_code_blocks_from_docstring",
        "presentation_profile_names",
        "resolve_presentation_profile",
        "api_package_to_help_book",
        "api_objects_to_summary_table",
        "select_uncategorized_api_objects",
    }

    assert expected <= set(apidoc.__all__)
    assert low_level_helpers.isdisjoint(apidoc.__all__)


def test_style_and_theme_canonical_field_names_are_stable() -> None:
    text_style_fields = {field.name for field in fields(oodocs.TextStyle)}
    table_cell_fields = {field.name for field in fields(oodocs.TableCell)}
    table_style_fields = {field.name for field in fields(oodocs.TableStyle)}
    block_defaults_fields = {field.name for field in fields(styles.BlockDefaults)}
    theme_fields = {field.name for field in fields(styles.Theme)}
    box_parameters = set(inspect.signature(oodocs.Box).parameters)
    table_parameters = set(inspect.signature(oodocs.Table).parameters)
    textbox_parameters = set(inspect.signature(positioning.TextBox).parameters)

    assert {"color", "all_caps"}.isdisjoint(text_style_fields)
    assert {"text_color", "uppercase"} <= text_style_fields
    assert "horizontal_alignment" not in table_cell_fields
    assert "text_alignment" in table_cell_fields
    assert {"cell_horizontal_alignment", "header_horizontal_alignment"}.isdisjoint(
        table_style_fields
    )
    assert {"cell_text_alignment", "header_text_alignment"} <= table_style_fields
    assert {"cell_text_alignment", "header_text_alignment"} <= table_parameters
    assert "alignment" not in box_parameters
    assert "block_alignment" in box_parameters
    assert {"table_alignment", "figure_alignment", "box_alignment"}.isdisjoint(
        block_defaults_fields
    )
    assert {
        "table_block_alignment",
        "figure_block_alignment",
        "box_block_alignment",
    } <= block_defaults_fields
    assert {"citation_options", "table_alignment", "figure_alignment"}.isdisjoint(
        theme_fields
    )
    assert "citations" in theme_fields
    assert {"align", "valign"}.isdisjoint(textbox_parameters)
    assert {"text_alignment", "vertical_alignment"} <= textbox_parameters


def test_public_api_naming_conventions_are_explicit_and_complete() -> None:
    assert public_api.PUBLIC_API_NAMING_CONVENTIONS == {
        "to_": "return an OODocs document object",
        "as_": "return a raw Python value or record",
        "from_": "construct an object from external input",
        "collect_": "collect metadata from an external parser, program, or runtime",
        "load_": "restore an already-defined model from a file",
        "save_": "write a file or output bundle",
        "validate_": "return structured validation data",
        "style": "describe visual properties",
        "profile": "select presented content",
        "presentation": "select presented content",
        "integration": "parse or collect an external tool format",
    }


def test_new_generic_apis_follow_the_naming_contract() -> None:
    names = {
        ProjectInfo.to_table.__name__,
        ManifestSummary.as_mapping.__name__,
        ManifestSummary.from_mapping.__name__,
        ManifestSummary.load_json.__name__,
        WorkflowJob.as_record.__name__,
        EvidenceReport.to_document.__name__,
        EvidenceReport.save_bundle.__name__,
        collect_pyproject_info.__name__,
        collect_github_actions_workflow.__name__,
    }

    assert names == {
        "to_table",
        "as_mapping",
        "from_mapping",
        "load_json",
        "as_record",
        "to_document",
        "save_bundle",
        "collect_pyproject_info",
        "collect_github_actions_workflow",
    }
