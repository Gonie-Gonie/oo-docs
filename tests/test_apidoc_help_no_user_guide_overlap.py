from __future__ import annotations

from pathlib import Path


GUIDE_ONLY_PHRASES = (
    "LaTeX habits",
    "Getting Started",
    "reading map",
    "workflow diagram",
    "pipeline diagram",
)


def _words(text: str) -> list[str]:
    return [word for word in text.replace("\n", " ").split(" ") if word.strip()]


def test_api_reference_scope_excludes_user_guide_responsibilities() -> None:
    scope = Path("docs/api-reference-scope.md").read_text(encoding="utf-8")

    assert "API Reference responsibilities:" in scope
    assert "Public symbol signatures." in scope
    assert "API Reference must not repeat the User Guide reading map." in scope
    for phrase in GUIDE_ONLY_PHRASES:
        assert phrase not in scope.replace("reading map.", "reading-map.")


def test_usage_guide_scope_keeps_workflow_material_out_of_api_reference() -> None:
    usage_scope = Path("docs/usage-guide-scope.md").read_text(encoding="utf-8")
    api_scope = Path("docs/api-reference-scope.md").read_text(encoding="utf-8")

    assert "OODocs philosophy and authoring model explanation." in usage_scope
    assert "LaTeX concepts" in usage_scope
    assert "Constructor and function input arguments." in api_scope
    assert "LaTeX concepts" not in api_scope


def test_api_reference_scope_intro_is_short() -> None:
    scope = Path("docs/api-reference-scope.md").read_text(encoding="utf-8")
    intro = scope.split("API Reference responsibilities:", 1)[0]

    assert len(_words(intro)) <= 120
