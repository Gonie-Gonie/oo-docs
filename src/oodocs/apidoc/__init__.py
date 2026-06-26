"""API object collection and OODocs composition helpers.

The ``oodocs.apidoc`` package turns Python modules into structured API objects
that can be queried, filtered, serialized, checked, and inserted into ordinary
OODocs documents as ``Section``, ``Table``, ``Paragraph``, ``CodeBlock``, and
``Box`` blocks.

Attributes:
    ApiCollectorName: Literal collector backend names.
    ApiFallbackCollectorName: Literal collector fallback policy names.
"""

from oodocs.apidoc.collect import collect_api, collect_module_api, collect_object_api
from oodocs.apidoc.builtin_categories import OODocs_API_CATEGORIES
from oodocs.apidoc.categories import ApiCategory, GuideLink
from oodocs.apidoc.config import (
    ApiHelpBookConfig,
    ApiCollectConfig,
    ApiCollectorName,
    ApiFallbackCollectorName,
    ApiPublicPolicy,
    ApiPublicPolicyName,
)
from oodocs.apidoc.coverage import ApiCoverageResult, check_api_docs
from oodocs.apidoc.diff import ApiDiffResult, ApiSnapshot, diff_api
from oodocs.apidoc.docstring import (
    ApiDocstringParser,
    ParsedDocstring,
    detect_docstring_style,
    docstring_parser_import_paths,
    docstring_parser_names,
    is_docstring_style_supported,
    load_docstring_parser_modules,
    parse_docstring,
    register_docstring_parser,
)
from oodocs.apidoc.examples import (
    check_doctest_examples,
    check_example_syntax,
    extract_code_blocks_from_docstring,
)
from oodocs.apidoc.model import (
    ApiDocIssue,
    ApiDocIssueSeverity,
    ApiDocstringStyleName,
    ApiExample,
    ApiKind,
    ApiModule,
    ApiObject,
    ApiPackage,
    ApiParameter,
    ApiPresentationProfileName,
    ApiException,
    ApiRendererNote,
    ApiReturn,
    ApiSeeAlso,
    ApiVisibility,
)
from oodocs.apidoc.render import (
    api_coverage_to_chapter,
    api_diff_to_chapter,
    api_objects_to_chapter,
    api_objects_to_summary_table,
)
from oodocs.apidoc.help import (
    api_category_to_chapter,
    api_object_to_help_section,
    api_package_to_help_book,
)
from oodocs.apidoc.profiles import (
    ApiPresentationProfile,
    presentation_profile_names,
    register_presentation_profile,
    resolve_presentation_profile,
)


__all__ = [
    "ApiCollectConfig",
    "ApiHelpBookConfig",
    "ApiCategory",
    "ApiCollectorName",
    "ApiCoverageResult",
    "ApiDiffResult",
    "ApiDocIssue",
    "ApiDocIssueSeverity",
    "ApiPresentationProfile",
    "ApiDocstringParser",
    "ApiDocstringStyleName",
    "ApiFallbackCollectorName",
    "ApiExample",
    "ApiKind",
    "ApiModule",
    "ApiObject",
    "ApiPackage",
    "ApiParameter",
    "ApiPresentationProfileName",
    "ApiPublicPolicy",
    "ApiPublicPolicyName",
    "ApiException",
    "ApiRendererNote",
    "ApiReturn",
    "ApiSeeAlso",
    "ApiSnapshot",
    "ApiVisibility",
    "GuideLink",
    "OODocs_API_CATEGORIES",
    "ParsedDocstring",
    "api_coverage_to_chapter",
    "api_diff_to_chapter",
    "api_objects_to_chapter",
    "api_objects_to_summary_table",
    "api_category_to_chapter",
    "api_object_to_help_section",
    "api_package_to_help_book",
    "check_api_docs",
    "check_doctest_examples",
    "check_example_syntax",
    "collect_api",
    "collect_module_api",
    "collect_object_api",
    "detect_docstring_style",
    "diff_api",
    "docstring_parser_import_paths",
    "docstring_parser_names",
    "extract_code_blocks_from_docstring",
    "is_docstring_style_supported",
    "load_docstring_parser_modules",
    "parse_docstring",
    "presentation_profile_names",
    "register_docstring_parser",
    "register_presentation_profile",
    "resolve_presentation_profile",
]
