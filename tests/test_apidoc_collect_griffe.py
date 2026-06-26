from __future__ import annotations

import importlib.util

import pytest

from apidoc_samples import (
    collect_sample_api,
    write_flit_module_file_repo,
    write_flit_package_repo,
    write_hatch_multi_package_repo,
    write_hatch_only_include_repo,
    write_hatch_package_repo,
    write_import_names_module_file_repo,
    write_import_names_package_repo,
    write_mixed_docstring_repo,
    write_pdm_package_dir_repo,
    write_pdm_module_file_repo,
    write_poetry_package_repo,
    write_dataclass_package,
    write_overload_package,
    write_private_package,
    write_sample_package,
    write_setuptools_find_repo,
    write_setuptools_package_dir_repo,
    write_setuptools_py_module_repo,
)
from example_regression import (
    assert_docx_structure,
    assert_html_internal_links_resolve,
    assert_pdf_text_and_pages,
    assert_rendered_bundle,
)
from oodocs.apidoc import ApiDocstringParser, collect_api, docstring_parser_names


def test_inspect_and_griffe_collect_same_sample_public_objects(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    inspect_root = tmp_path / "inspect"
    griffe_root = tmp_path / "griffe"
    inspect_root.mkdir()
    griffe_root.mkdir()

    inspect_api = collect_sample_api(inspect_root, collector="inspect")
    griffe_api = collect_sample_api(griffe_root, collector="griffe")
    inspect_names = sorted(obj.qualname for obj in inspect_api.iter_objects(recursive=True))
    griffe_names = sorted(obj.qualname for obj in griffe_api.iter_objects(recursive=True))

    assert inspect_names == griffe_names


def test_griffe_collector_collects_general_package_tree(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    api = collect_sample_api(tmp_path, collector="griffe")

    assert api.metadata["collector"] == "griffe"
    assert api.find_object("samplepkg.Widget") is not None
    assert api.find_object("samplepkg.make_widget") is not None


def test_griffe_collector_passes_docstring_parser_hint(tmp_path, monkeypatch) -> None:
    griffe = pytest.importorskip("griffe")
    original_load = griffe.load
    seen_parsers: list[object] = []

    def spy_load(*args, **kwargs):
        seen_parsers.append(kwargs.get("docstring_parser"))
        return original_load(*args, **kwargs)

    monkeypatch.setattr(griffe, "load", spy_load)
    api = collect_sample_api(tmp_path, collector="griffe", docstring_style="google")
    render = api.find_object("samplepkg.Widget.render")

    assert seen_parsers[-1] == "google"
    assert render is not None
    assert render.metadata["docstring_style"] == "google"

    plain_root = tmp_path / "plain"
    plain_root.mkdir()
    collect_sample_api(plain_root, collector="griffe", docstring_style="plain")
    assert seen_parsers[-1] is None


def test_griffe_collector_uses_auto_parser_object_on_mixed_repo(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_mixed_docstring_repo(tmp_path)
    api = collect_api(
        repo,
        collector="griffe",
        public_policy="__all__",
        docstring_style=ApiDocstringParser.auto(),
    )
    method = api.find_object("mixedpkg.core.Client.connect")
    function = api.find_object("mixedpkg.core.connect")
    stream = api.find_object("mixedpkg.core.stream")

    assert method is not None
    assert method.metadata["docstring_style"] == "numpy"
    assert method.parameters[0].description == "Timeout in seconds."
    assert method.returns is not None
    assert method.returns.description == "Whether the connection succeeded."
    assert function is not None
    assert function.metadata["docstring_style"] == "google"
    assert stream is not None
    assert stream.metadata["docstring_style"] == "markdown"
    assert stream.returns is not None
    assert stream.returns.description == "Endpoint update payload."

    document = api.to_document(profile="compact", max_level=3)
    outputs = document.save_all(
        tmp_path / "griffe-mixed-rendered",
        stem="mixedpkg-griffe-api",
        formats=("docx", "pdf", "html"),
    )

    assert_rendered_bundle(outputs["docx"], outputs["pdf"], outputs["html"])
    assert document.validate(formats=("docx", "pdf", "html")).ok
    assert_docx_structure(
        outputs["docx"],
        required_paragraphs=(
            "mixedpkg API Reference",
            "1 API Documentation Coverage",
            "2 mixedpkg",
            "3 mixedpkg.core",
        ),
        min_tables=6,
    )
    assert_pdf_text_and_pages(
        outputs["pdf"],
        required_text=(
            "mixedpkg API Reference",
            "mixedpkg.core.Client",
            "Base endpoint URL.",
        ),
        min_pages=1,
    )
    assert_html_internal_links_resolve(
        outputs["html"],
        required_text=("mixedpkg.core.Client", "Base endpoint URL."),
    )


def test_griffe_collector_uses_repo_local_custom_docstring_parser(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = tmp_path / "griffe-custom-repo"
    package_dir = repo / "src" / "griffecustompkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "griffecustompkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "griffe_custom_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_griffe_custom(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"griffe:{first}", style="griffe-custom-brief")',
                "",
                'if "griffe-custom-brief" not in docstring_parser_names():',
                '    register_docstring_parser("griffe-custom-brief", parse_griffe_custom)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Griffe custom parser package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run with a custom parser."""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert "griffe-custom-brief" not in docstring_parser_names()
    api = collect_api(
        repo,
        collector="griffe",
        public_policy="__all__",
        docstring_parser_modules=("griffe_custom_parsers",),
        docstring_style="griffe-custom-brief",
    )
    run = api.find_object("griffecustompkg.run")

    assert api.metadata["collector"] == "griffe"
    assert run is not None
    assert run.summary == "griffe:Run with a custom parser."
    assert run.metadata["docstring_style"] == "griffe-custom-brief"


def test_griffe_collector_can_exclude_member_kinds(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    api = collect_sample_api(
        tmp_path,
        collector="griffe",
        include_attributes=False,
        include_properties=False,
        include_methods=False,
    )

    assert api.find_object("samplepkg.Widget") is not None
    assert api.find_object("samplepkg.make_widget") is not None
    assert api.find_object("samplepkg.CONSTANT") is None
    assert api.find_object("samplepkg.Widget.label") is None
    assert api.find_object("samplepkg.Widget.title") is None
    assert api.find_object("samplepkg.Widget.render") is None


def test_griffe_collector_copies_reexported_attribute_docs(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    package_dir = tmp_path / "reexportpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                "from .core import OutputFormat",
                "",
                '__all__ = ["OutputFormat"]',
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        "\n".join(
            [
                '"""Core public types.',
                "",
                "Attributes:",
                "    OutputFormat: Supported output target names.",
                '"""',
                "",
                "from typing import Literal",
                "",
                'OutputFormat = Literal["docx", "pdf"]',
                "",
                '__all__ = ["OutputFormat"]',
            ]
        ),
        encoding="utf-8",
    )

    api = collect_api(package_dir, collector="griffe", public_policy="__all__")
    target = api.find_object("reexportpkg.core.OutputFormat")
    exported = api.find_object("reexportpkg.OutputFormat")

    assert target is not None
    assert target.summary == "Supported output target names."
    assert exported is not None
    assert exported.summary == "Supported output target names."
    assert exported.metadata["reexported_from"] == "reexportpkg.core.OutputFormat"


def test_griffe_collector_can_strip_source_locations(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    api = collect_sample_api(
        tmp_path,
        collector="griffe",
        include_source_locations=False,
    )
    widget = api.find_object("samplepkg.Widget")
    render = api.find_object("samplepkg.Widget.render")

    assert api.metadata.get("source_root") is None
    assert api.modules[0].source_path is None
    assert api.modules[0].line_number is None
    assert widget is not None
    assert widget.source_path is None
    assert widget.line_number is None
    assert render is not None
    assert render.source_path is None
    assert render.line_number is None


def test_griffe_collector_uses_pyproject_setuptools_package_dir(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_setuptools_package_dir_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert [module.name for module in api.modules] == ["samplepkg", "samplepkg.core"]
    assert api.find_object("samplepkg.run") is not None
    assert api.find_object("samplepkg.core.run") is not None
    assert api.find_object("lib.samplepkg.run") is None


def test_griffe_collector_uses_pyproject_setuptools_find_where(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_setuptools_find_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert [module.name for module in api.modules] == ["findpkg", "findpkg.core"]
    assert api.find_object("findpkg.run") is not None
    assert api.find_object("findpkg.core.run") is not None
    assert api.find_object("lib.findpkg.run") is None


def test_griffe_collector_uses_pyproject_setuptools_py_modules(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_setuptools_py_module_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "singlemod"
    assert [module.name for module in api.modules] == ["singlemod"]
    assert api.find_object("singlemod.Client.connect") is not None
    assert api.find_object("src.singlemod.Client") is None


def test_griffe_collector_uses_pyproject_hatch_packages(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_hatch_package_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert [module.name for module in api.modules] == ["hatchpkg", "hatchpkg.core"]
    assert api.find_object("hatchpkg.run") is not None
    assert api.find_object("hatchpkg.core.run") is not None
    assert api.find_object("lib.hatchpkg.run") is None


def test_griffe_collector_uses_pyproject_hatch_only_include(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_hatch_only_include_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "onlypkg"
    assert [module.name for module in api.modules] == ["onlypkg", "onlypkg.core"]
    assert api.find_object("onlypkg.run") is not None
    assert api.find_object("onlypkg.core.run") is not None
    assert api.find_object("lib.onlypkg.run") is None
    assert api.find_object("straypkg.leak") is None


def test_griffe_collector_uses_pyproject_hatch_multi_packages(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_hatch_multi_package_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert [module.name for module in api.modules] == [
        "alpha",
        "alpha.core",
        "beta",
        "beta.core",
    ]
    assert api.find_object("alpha.run") is not None
    assert api.find_object("beta.run") is not None
    assert api.find_object("lib.alpha.run") is None


def test_griffe_collector_uses_pyproject_poetry_packages(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_poetry_package_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert [module.name for module in api.modules] == ["poetrypkg", "poetrypkg.core"]
    assert api.find_object("poetrypkg.run") is not None
    assert api.find_object("poetrypkg.core.run") is not None
    assert api.find_object("lib.poetrypkg.run") is None


def test_griffe_collector_uses_pyproject_pdm_package_dir(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_pdm_package_dir_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert [module.name for module in api.modules] == ["pdmpkg", "pdmpkg.core"]
    assert api.find_object("pdmpkg.run") is not None
    assert api.find_object("pdmpkg.core.run") is not None
    assert api.find_object("lib.pdmpkg.run") is None


def test_griffe_collector_uses_pyproject_pdm_module_includes(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_pdm_module_file_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "pdmrunner"
    assert [module.name for module in api.modules] == ["pdmrunner"]
    assert api.find_object("pdmrunner.Client.connect") is not None
    assert api.find_object("pdm_module_repo.pdmrunner.Client") is None


def test_griffe_collector_uses_pyproject_flit_module_name(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_flit_package_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "flitpkg"
    assert [module.name for module in api.modules] == ["flitpkg", "flitpkg.core"]
    assert api.find_object("flitpkg.run") is not None
    assert api.find_object("flitpkg.core.Runner.run") is not None
    assert api.find_object("published_flit_project.flitpkg.run") is None
    assert api.find_object("straypkg.leak") is None


def test_griffe_collector_uses_pyproject_flit_default_module_file(
    tmp_path,
) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_flit_module_file_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "flitrunner"
    assert [module.name for module in api.modules] == ["flitrunner"]
    assert api.find_object("flitrunner.Client.connect") is not None
    assert api.find_object("helper.leak") is None


def test_griffe_collector_uses_pyproject_import_names_package(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_import_names_package_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "importnamedpkg"
    assert [module.name for module in api.modules] == [
        "importnamedpkg",
        "importnamedpkg.core",
    ]
    assert api.find_object("importnamedpkg.run") is not None
    assert api.find_object("published_import_name_project.importnamedpkg.run") is None
    assert api.find_object("straypkg.leak") is None


def test_griffe_collector_uses_import_names_with_configured_source_root(
    tmp_path,
) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_import_names_package_repo(tmp_path, source_root="lib")

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "importnamedpkg"
    assert [module.name for module in api.modules] == [
        "importnamedpkg",
        "importnamedpkg.core",
    ]
    assert api.find_object("importnamedpkg.run") is not None
    assert api.find_object("lib.importnamedpkg.run") is None
    assert api.find_object("straypkg.leak") is None


def test_griffe_collector_uses_pyproject_import_names_module_file(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    repo = write_import_names_module_file_repo(tmp_path)

    api = collect_api(repo, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "griffe"
    assert api.name == "importnamedrunner"
    assert [module.name for module in api.modules] == ["importnamedrunner"]
    assert api.find_object("importnamedrunner.run") is not None
    assert api.find_object("helper.leak") is None


def test_griffe_collector_records_load_failure_fallback_issue(
    tmp_path,
    monkeypatch,
) -> None:
    griffe = pytest.importorskip("griffe")
    package_dir = write_sample_package(tmp_path, name="fallbackpkg")

    def fail_load(*args, **kwargs):
        raise RuntimeError("forced griffe failure")

    monkeypatch.setattr(griffe, "load", fail_load)

    api = collect_api(package_dir, collector="griffe", public_policy="__all__")

    assert api.metadata["collector"] == "inspect"
    assert api.metadata["requested_collector"] == "griffe"
    assert api.metadata["fallback_collector"] == "inspect"
    assert api.find_object("fallbackpkg.Widget") is not None
    assert any(issue.code == "griffe-load-failed" for issue in api.issues)


def test_griffe_collector_can_include_private_objects(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    package_dir = write_private_package(tmp_path)

    default_api = collect_api(package_dir, collector="griffe", public_policy="__all__")
    private_api = collect_api(
        package_dir,
        collector="griffe",
        public_policy="__all__",
        include_private=True,
    )

    assert default_api.find_object("privatepkg._helper") is None
    assert default_api.find_object("privatepkg.PublicWidget._debug") is None
    assert default_api.find_object("privatepkg.PublicWidget._cache") is None
    assert private_api.find_object("privatepkg._helper") is not None
    assert private_api.find_object("privatepkg._TOKEN") is not None
    debug = private_api.find_object("privatepkg.PublicWidget._debug")
    cache = private_api.find_object("privatepkg.PublicWidget._cache")
    assert debug is not None
    assert debug.visibility == "protected"
    assert cache is not None
    assert cache.visibility == "protected"
    assert private_api.select_private_objects()


def test_griffe_collector_records_overload_metadata(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    package_dir = write_overload_package(tmp_path)

    api = collect_api(package_dir, collector="griffe", public_policy="__all__")
    parse = api.find_object("overpkg.parse")
    method = api.find_object("overpkg.Parser.parse")

    assert parse is not None
    assert method is not None
    assert [obj.qualname for obj in api.iter_objects(recursive=True)].count("overpkg.parse") == 1
    assert [item["signature"] for item in parse.metadata["overloads"]] == [
        "overpkg.parse(value: str) -> str",
        "overpkg.parse(value: bytes) -> bytes",
    ]
    assert [item["signature"] for item in method.metadata["overloads"]] == [
        "overpkg.Parser.parse(value: str) -> str",
        "overpkg.Parser.parse(value: bytes) -> bytes",
    ]


def test_griffe_collector_uses_dataclass_fields_for_class_signature(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    package_dir = write_dataclass_package(tmp_path)

    api = collect_api(package_dir, collector="griffe", public_policy="__all__")
    settings = api.find_object("datapkg.Settings")
    tags = api.find_object("datapkg.Settings.tags")
    cache = api.find_object("datapkg.Settings.cache")

    assert settings is not None
    assert settings.signature == "datapkg.Settings(path: str, retries: int = 3, tags: list[str] = list())"
    assert [parameter.name for parameter in settings.parameters] == ["path", "retries", "tags"]
    assert all(parameter.documented for parameter in settings.parameters)
    assert {member.name for member in settings.members} >= {"path", "retries", "tags", "cache"}
    assert tags is not None
    assert tags.summary == "Labels attached to the run."
    assert cache is not None
    assert cache.metadata["default"] == "field(default_factory=dict, init=False)"


def test_griffe_collector_can_include_inherited_members(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    package_dir = tmp_path / "inheritpkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                "class Base:",
                '    """Base class."""',
                "    def inherited(self, value: str) -> str:",
                '        """Inherited method."""',
                "        return value",
                "",
                "class Child(Base):",
                '    """Child class."""',
                "    def own(self) -> None:",
                '        """Own method."""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    default_api = collect_api(
        package_dir,
        collector="griffe",
        public_policy="underscore",
    )
    inherited_api = collect_api(
        package_dir,
        collector="griffe",
        public_policy="underscore",
        include_inherited=True,
    )

    assert default_api.find_object("inheritpkg.Child.inherited") is None
    inherited = inherited_api.find_object("inheritpkg.Child.inherited")
    assert inherited is not None
    assert inherited.summary == "Inherited method."
    assert inherited.metadata["inherited_from"] == "inheritpkg.Base.inherited"
