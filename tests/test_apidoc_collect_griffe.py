from __future__ import annotations

import importlib.util

import pytest

from apidoc_samples import collect_sample_api, write_private_package
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
