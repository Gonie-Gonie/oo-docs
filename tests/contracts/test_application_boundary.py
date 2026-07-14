from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.contracts


def test_application_boundary_assigns_domain_content_to_callers() -> None:
    reference = Path("docs/reference/application-boundary.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(reference.split())

    for phrase in (
        "`DocumentSuiteContext.variables`",
        "does not provide a LaTeX macro engine",
        "does not automatically convert arbitrary TeX",
        "`CodeBlock` or structured entries with an ordinary `Table`",
        "`Section`, `BulletList`, and `PageBreak`",
        "`SchemaCatalog`",
        "field type codes, requirement codes, and unit aliases",
        "Cover branding, organization, logo, and funding note",
        "Simulation-specific result-table layout",
        "application repository",
        "Python remains the composition and variable language",
    ):
        assert phrase in normalized
