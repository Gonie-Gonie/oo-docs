from __future__ import annotations

from apidoc_samples import collect_sample_api
from oodocs.apidoc import collect_api


def test_inspect_collector_collects_general_package_tree(tmp_path) -> None:
    api = collect_sample_api(tmp_path, collector="inspect")

    assert api.metadata["collector"] == "inspect"
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.make_widget") is not None
    assert api.classes()
    assert api.functions()


def test_inspect_collector_can_exclude_member_kinds(tmp_path) -> None:
    api = collect_sample_api(
        tmp_path,
        collector="inspect",
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


def test_inspect_collector_can_strip_source_locations(tmp_path) -> None:
    api = collect_sample_api(
        tmp_path,
        collector="inspect",
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


def test_inspect_collector_can_include_same_module_inherited_members(tmp_path) -> None:
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
        collector="inspect",
        public_policy="underscore",
    )
    inherited_api = collect_api(
        package_dir,
        collector="inspect",
        public_policy="underscore",
        include_inherited=True,
    )

    assert default_api.find("inheritpkg.Child.inherited") is None
    inherited = inherited_api.find("inheritpkg.Child.inherited")
    assert inherited is not None
    assert inherited.summary == "Inherited method."
    assert inherited.signature == "inheritpkg.Child.inherited(value: str) -> str"
    assert inherited.metadata["inherited_from"] == "inheritpkg.Base.inherited"
