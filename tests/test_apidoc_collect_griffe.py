from __future__ import annotations

import importlib.util

import pytest

from apidoc_samples import (
    collect_sample_api,
    write_dataclass_package,
    write_overload_package,
    write_private_package,
    write_setuptools_package_dir_repo,
)
from oodocs.apidoc import collect_api


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
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.make_widget") is not None


def test_griffe_collector_passes_docstring_parser_hint(tmp_path, monkeypatch) -> None:
    griffe = pytest.importorskip("griffe")
    original_load = griffe.load
    seen_parsers: list[object] = []

    def spy_load(*args, **kwargs):
        seen_parsers.append(kwargs.get("docstring_parser"))
        return original_load(*args, **kwargs)

    monkeypatch.setattr(griffe, "load", spy_load)
    api = collect_sample_api(tmp_path, collector="griffe", docstring_style="google")
    render = api.find("samplepkg.Widget.render")

    assert seen_parsers[-1] == "google"
    assert render is not None
    assert render.metadata["docstring_style"] == "google"

    plain_root = tmp_path / "plain"
    plain_root.mkdir()
    collect_sample_api(plain_root, collector="griffe", docstring_style="plain")
    assert seen_parsers[-1] is None


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

    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.make_widget") is not None
    assert api.find("samplepkg.CONSTANT") is None
    assert api.find("samplepkg.Widget.label") is None
    assert api.find("samplepkg.Widget.title") is None
    assert api.find("samplepkg.Widget.render") is None


def test_griffe_collector_can_strip_source_locations(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    api = collect_sample_api(
        tmp_path,
        collector="griffe",
        include_source_locations=False,
    )
    widget = api.find("samplepkg.Widget")
    render = api.find("samplepkg.Widget.render")

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
    assert api.find("samplepkg.run") is not None
    assert api.find("samplepkg.core.run") is not None
    assert api.find("lib.samplepkg.run") is None


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

    assert default_api.find("privatepkg._helper") is None
    assert default_api.find("privatepkg.PublicWidget._debug") is None
    assert default_api.find("privatepkg.PublicWidget._cache") is None
    assert private_api.find("privatepkg._helper") is not None
    assert private_api.find("privatepkg._TOKEN") is not None
    debug = private_api.find("privatepkg.PublicWidget._debug")
    cache = private_api.find("privatepkg.PublicWidget._cache")
    assert debug is not None
    assert debug.visibility == "protected"
    assert cache is not None
    assert cache.visibility == "protected"
    assert private_api.private_objects()


def test_griffe_collector_records_overload_metadata(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    package_dir = write_overload_package(tmp_path)

    api = collect_api(package_dir, collector="griffe", public_policy="__all__")
    parse = api.find("overpkg.parse")
    method = api.find("overpkg.Parser.parse")

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
    settings = api.find("datapkg.Settings")
    tags = api.find("datapkg.Settings.tags")
    cache = api.find("datapkg.Settings.cache")

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

    assert default_api.find("inheritpkg.Child.inherited") is None
    inherited = inherited_api.find("inheritpkg.Child.inherited")
    assert inherited is not None
    assert inherited.summary == "Inherited method."
    assert inherited.metadata["inherited_from"] == "inheritpkg.Base.inherited"
