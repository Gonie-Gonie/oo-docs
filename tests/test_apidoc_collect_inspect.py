from __future__ import annotations

from apidoc_samples import collect_sample_api, write_overload_package, write_private_package
from oodocs.apidoc import collect_api


def test_inspect_collector_collects_general_package_tree(tmp_path) -> None:
    api = collect_sample_api(tmp_path, collector="inspect")

    assert api.metadata["collector"] == "inspect"
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.Widget.name") is not None
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
    assert api.find("samplepkg.Widget.name") is None
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


def test_inspect_collector_can_include_private_objects(tmp_path) -> None:
    package_dir = write_private_package(tmp_path)

    default_api = collect_api(package_dir, collector="inspect", public_policy="__all__")
    private_api = collect_api(
        package_dir,
        collector="inspect",
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


def test_inspect_collector_records_overload_metadata(tmp_path) -> None:
    package_dir = write_overload_package(tmp_path)

    api = collect_api(package_dir, collector="inspect", public_policy="__all__")
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
