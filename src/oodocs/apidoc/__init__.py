"""API object collection and OODocs composition helpers.

The ``oodocs.apidoc`` package turns Python modules into structured API objects
that can be queried, filtered, serialized, checked, and inserted into ordinary
OODocs documents as ``Section``, ``Table``, ``Paragraph``, ``CodeBlock``, and
``Box`` blocks.
"""

from oodocs.apidoc.collect import collect_api, collect_module_api, collect_object_api
from oodocs.apidoc.config import ApiCollectConfig, ApiCollectorName, ApiPublicPolicy, ApiPublicPolicyName
from oodocs.apidoc.coverage import ApiCoverageResult, check_api_docs
from oodocs.apidoc.diff import ApiDiffResult, ApiSnapshot, diff_api
from oodocs.apidoc.docstring import (
    ParsedDocstring,
    detect_docstring_style,
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
    "ApiCollectorName",
    "ApiCoverageResult",
    "ApiDiffResult",
    "ApiDocIssue",
    "ApiDocIssueSeverity",
    "ApiDocProfile",
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
    "extract_code_blocks_from_docstring",
    "parse_docstring",
    "profile_names",
    "register_docstring_parser",
    "register_profile",
    "resolve_profile",
]
