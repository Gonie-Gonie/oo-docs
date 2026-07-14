from __future__ import annotations

import base64
from datetime import date
import json
from pathlib import Path

import pytest

from oodocs.components.blocks import Paragraph
from oodocs.components.cover import CoverPage
from oodocs.components.media import Figure
from oodocs.components.references import CitationLibrary
from oodocs.document import Document
from oodocs.settings import DocumentSettings, TitleMatter
from oodocs.suite import (
    AmbiguousAssetError,
    AssetResolver,
    DocumentSuite,
    DocumentSuiteContext,
    DocumentSuiteValidationError,
)


_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZK1sAAAAASUVORK5CYII="
)


def _write_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_ONE_PIXEL_PNG)
    return path


def test_asset_resolver_uses_suite_root_then_detects_registered_root_ambiguity(
    tmp_path: Path,
) -> None:
    root = tmp_path / "suite"
    first = root / "first assets"
    second = root / "second assets"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "shared.txt").write_text("first", encoding="utf-8")
    (second / "shared.txt").write_text("second", encoding="utf-8")

    context = DocumentSuiteContext(
        root=root,
        output_dir="dist",
        variables={},
        assets=AssetResolver((Path("first assets"), Path("second assets"))),
        citations=CitationLibrary(),
    )

    with pytest.raises(AmbiguousAssetError) as caught:
        context.assets.resolve("shared.txt")
    assert caught.value.candidates == (
        (first / "shared.txt").resolve(),
        (second / "shared.txt").resolve(),
    )

    suite_copy = root / "shared.txt"
    suite_copy.write_text("suite", encoding="utf-8")
    assert context.assets.resolve("shared.txt") == suite_copy.resolve()
    assert context.assets.resolve(suite_copy) == suite_copy.resolve()
    with pytest.raises(FileNotFoundError, match="missing.txt"):
        context.assets.require("missing.txt")


def test_suite_paths_are_cwd_independent_with_spaces_and_korean_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "suite root 한글"
    relative_asset = Path("asset files 자료") / "보고서 그림.png"
    expected_asset = _write_png(root / relative_asset)
    citations = CitationLibrary()
    context = DocumentSuiteContext(
        root=root,
        output_dir=Path("rendered 결과"),
        variables={
            "project": "중립 프로젝트",
            "version": "1.2",
            "date": date(2026, 7, 14),
            "runtime": object(),
        },
        assets=AssetResolver(),
        citations=citations,
    )
    suite = DocumentSuite("release documents", context)

    def build_report(shared: DocumentSuiteContext) -> Document:
        settings = DocumentSettings(
            title_matter=TitleMatter(cover=CoverPage(logo=relative_asset))
        )
        return Document(
            str(shared.variables["project"]),
            Figure(relative_asset, caption="결과", alt_text="결과 그림"),
            settings=settings,
            citations=shared.citations,
        )

    suite.add("Korean report", build_report, stem="보고서", formats=("html",))
    outside = tmp_path / "unrelated working directory"
    outside.mkdir()
    monkeypatch.chdir(outside)

    document = suite.build("Korean report")
    figure = document.body.children[0]
    assert isinstance(figure, Figure)
    assert figure.image_source == expected_asset.resolve()
    assert document.settings.title_matter.cover is not None
    assert document.settings.title_matter.cover.logo == expected_asset.resolve()
    assert document.citations is citations

    bundle = suite.save_all(formats=("pdf",))
    assert bundle["Korean report"].formats == ("html",)
    assert bundle["Korean report"]["html"].is_file()
    assert bundle["Korean report"]["html"].parent == context.output_dir

    manifest = bundle.as_manifest()
    assert manifest == {
        "suite": "release documents",
        "variables": {
            "project": "중립 프로젝트",
            "version": "1.2",
            "date": "2026-07-14",
        },
        "outputs": {"Korean report": {"html": "보고서.html"}},
    }
    manifest_path = bundle.save_manifest()
    assert manifest_path == context.output_dir / "suite-manifest.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest


def test_validate_all_reports_figure_and_cover_assets_without_using_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "suite"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    context = DocumentSuiteContext(
        root,
        "dist",
        {},
        AssetResolver(),
        CitationLibrary(),
    )
    suite = DocumentSuite("assets", context)
    suite.add(
        "missing",
        lambda _: Document(
            "Missing assets",
            Figure("missing figure.png", caption="Missing", alt_text="Missing"),
            settings=DocumentSettings(
                title_matter=TitleMatter(cover=CoverPage(logo="missing logo.png"))
            ),
        ),
        formats=("html",),
    )
    monkeypatch.chdir(outside)

    result = suite.validate_all()["missing"]
    suite_asset_issues = [
        issue for issue in result.issues if issue.code == "missing-suite-asset"
    ]
    assert {issue.path for issue in suite_asset_issues} == {
        "document.body.children[0].image_source",
        "document.settings.title_matter.cover.logo",
    }
    assert not result.ok
    with pytest.raises(FileNotFoundError, match="missing logo.png"):
        suite.build("missing")
    with pytest.raises(DocumentSuiteValidationError):
        suite.validate_all(raise_on_error=True)


def test_suite_preserves_factory_owned_citation_libraries(tmp_path: Path) -> None:
    shared = CitationLibrary()
    private = CitationLibrary()
    context = DocumentSuiteContext(
        tmp_path,
        "dist",
        {"literal": "{{ version }}"},
        AssetResolver(),
        shared,
    )
    suite = DocumentSuite("citations", context)
    suite.add(
        "shared",
        lambda current: Document(
            "Shared", Paragraph(str(current.variables["literal"])), citations=current.citations
        ),
    )
    suite.add("private", lambda _: Document("Private", citations=private))

    assert suite.build("shared").citations is shared
    assert suite.build("private").citations is private
    paragraph = suite.build("shared").body.children[0]
    assert isinstance(paragraph, Paragraph)
    assert paragraph.plain_text() == "{{ version }}"


def test_suite_rejects_duplicate_names_bad_factories_and_path_stems(
    tmp_path: Path,
) -> None:
    context = DocumentSuiteContext(tmp_path, "dist")
    suite = DocumentSuite("checks", context)
    suite.add("report", lambda _: Document("Report"))
    with pytest.raises(ValueError, match="Duplicate"):
        suite.add("report", lambda _: Document("Again"))
    with pytest.raises(ValueError, match="filename"):
        suite.add("nested", lambda _: Document("Nested"), stem="dir/report")

    suite.add("invalid", lambda _: "not a document")  # type: ignore[arg-type,return-value]
    with pytest.raises(TypeError, match="not Document"):
        suite.build("invalid")
    with pytest.raises(KeyError, match="unknown"):
        suite.build("unknown")
