"""Adapters that turn repository artefacts into OODocs objects."""

from oodocs.adapters.evidence import ReleaseEvidence, ReleaseEvidenceBundle
from oodocs.adapters.github_actions import GithubWorkflowSummary
from oodocs.adapters.manifest import ReleaseManifestSummary
from oodocs.adapters.pyproject import ProjectMetadata

__all__ = [
    "GithubWorkflowSummary",
    "ProjectMetadata",
    "ReleaseEvidence",
    "ReleaseEvidenceBundle",
    "ReleaseManifestSummary",
]
