"""API object collection and OODocs composition helpers.

The ``oodocs.apidoc`` package turns Python modules into structured API objects
that can be queried, filtered, serialized, checked, and inserted into ordinary
OODocs documents as ``Section``, ``Table``, ``Paragraph``, ``CodeBlock``, and
``Box`` blocks.
"""

from oodocs.apidoc.collect import collect_api, collect_module_api, collect_object_api
from oodocs.apidoc.config import (
    ApiBuildConfig,
    ApiCollectConfig,
    ApiCollectorName,
    ApiPublicPolicy,
    ApiPublicPolicyName,
)
from oodocs.apidoc.coverage import ApiCoverageResult, check_api_docs
from oodocs.apidoc.diff import ApiDiffResult, ApiSnapshot, diff_api
from oodocs.apidoc.docstring import (
    ApiDocstringParser,
    ParsedDocstring,
    detect_docstring_style,
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
    ApiRaises,
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
    api_package_to_document,
)
from oodocs.apidoc.styles import (
    ApiDocProfile,
    profile_names,
    register_profile,
    resolve_profile,
)


__all__ = [
    "ApiCollectConfig",
    "ApiBuildConfig",
    "ApiCollectorName",
    "ApiCoverageResult",
    "ApiDiffResult",
    "ApiDocIssue",
    "ApiDocIssueSeverity",
    "ApiDocProfile",
    "ApiDocstringParser",
    "ApiDocstringStyleName",
    "ApiExample",
    "ApiKind",
    "ApiModule",
    "ApiObject",
    "ApiPackage",
    "ApiParameter",
    "ApiPresentationProfileName",
    "ApiPublicPolicy",
    "ApiPublicPolicyName",
    "ApiRaises",
    "ApiRendererNote",
    "ApiReturn",
    "ApiSeeAlso",
    "ApiSnapshot",
    "ApiVisibility",
    "ParsedDocstring",
    "api_coverage_to_chapter",
    "api_diff_to_chapter",
    "api_objects_to_chapter",
    "api_objects_to_summary_table",
    "api_package_to_document",
    "check_api_docs",
    "check_doctest_examples",
    "check_example_syntax",
    "collect_api",
    "collect_module_api",
    "collect_object_api",
    "detect_docstring_style",
    "diff_api",
    "docstring_parser_names",
    "extract_code_blocks_from_docstring",
    "is_docstring_style_supported",
    "load_docstring_parser_modules",
    "parse_docstring",
    "profile_names",
    "register_docstring_parser",
    "register_profile",
    "resolve_profile",
]
