from __future__ import annotations

from apidoc_samples import (
    collect_sample_api,
    write_flit_module_file_repo,
    write_flit_package_repo,
    write_hatch_multi_package_repo,
    write_hatch_only_include_repo,
    write_hatch_package_repo,
    write_import_names_module_file_repo,
    write_import_names_package_repo,
    write_pdm_package_dir_repo,
    write_pdm_module_file_repo,
    write_poetry_package_repo,
    write_setuptools_find_repo,
    write_setuptools_package_dir_repo,
    write_setuptools_py_module_repo,
    write_dataclass_package,
    write_overload_package,
    write_private_package,
)
from oodocs.apidoc import collect_api


def test_inspect_collector_collects_general_package_tree(tmp_path) -> None:
    api = collect_sample_api(tmp_path, collector="inspect")

    assert api.metadata["collector"] == "inspect"
    assert any(issue.code == "inspect-source-collector" for issue in api.issues)
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.Widget.name") is not None
    assert api.find("samplepkg.make_widget") is not None
    assert api.classes()
    assert api.functions()
    issue_table = api.to_issue_table()
    assert any(
        row[1].content.plain_text() == "inspect-source-collector"
        for row in issue_table.rows
    )


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


def test_inspect_collector_uses_pyproject_setuptools_package_dir(tmp_path) -> None:
    repo = write_setuptools_package_dir_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert [module.name for module in api.modules] == ["samplepkg", "samplepkg.core"]
    assert api.find("samplepkg.run") is not None
    assert api.find("samplepkg.core.run") is not None
    assert api.find("lib.samplepkg.run") is None


def test_inspect_collector_uses_pyproject_setuptools_find_where(tmp_path) -> None:
    repo = write_setuptools_find_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert [module.name for module in api.modules] == ["findpkg", "findpkg.core"]
    assert api.find("findpkg.run") is not None
    assert api.find("findpkg.core.run") is not None
    assert api.find("lib.findpkg.run") is None


def test_inspect_collector_uses_pyproject_setuptools_py_modules(tmp_path) -> None:
    repo = write_setuptools_py_module_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "singlemod"
    assert [module.name for module in api.modules] == ["singlemod"]
    assert api.find("singlemod.Client.connect") is not None
    assert api.find("src.singlemod.Client") is None


def test_inspect_collector_uses_pyproject_hatch_packages(tmp_path) -> None:
    repo = write_hatch_package_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert [module.name for module in api.modules] == ["hatchpkg", "hatchpkg.core"]
    assert api.find("hatchpkg.run") is not None
    assert api.find("hatchpkg.core.run") is not None
    assert api.find("lib.hatchpkg.run") is None


def test_inspect_collector_uses_pyproject_hatch_only_include(tmp_path) -> None:
    repo = write_hatch_only_include_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "onlypkg"
    assert [module.name for module in api.modules] == ["onlypkg", "onlypkg.core"]
    assert api.find("onlypkg.run") is not None
    assert api.find("onlypkg.core.run") is not None
    assert api.find("lib.onlypkg.run") is None
    assert api.find("straypkg.leak") is None


def test_inspect_collector_uses_pyproject_hatch_multi_packages(tmp_path) -> None:
    repo = write_hatch_multi_package_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert [module.name for module in api.modules] == [
        "alpha",
        "alpha.core",
        "beta",
        "beta.core",
    ]
    assert api.find("alpha.run") is not None
    assert api.find("beta.run") is not None
    assert api.find("lib.alpha.run") is None


def test_inspect_collector_uses_pyproject_poetry_packages(tmp_path) -> None:
    repo = write_poetry_package_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert [module.name for module in api.modules] == ["poetrypkg", "poetrypkg.core"]
    assert api.find("poetrypkg.run") is not None
    assert api.find("poetrypkg.core.run") is not None
    assert api.find("lib.poetrypkg.run") is None


def test_inspect_collector_uses_pyproject_pdm_package_dir(tmp_path) -> None:
    repo = write_pdm_package_dir_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert [module.name for module in api.modules] == ["pdmpkg", "pdmpkg.core"]
    assert api.find("pdmpkg.run") is not None
    assert api.find("pdmpkg.core.run") is not None
    assert api.find("lib.pdmpkg.run") is None


def test_inspect_collector_uses_pyproject_pdm_module_includes(tmp_path) -> None:
    repo = write_pdm_module_file_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "pdmrunner"
    assert [module.name for module in api.modules] == ["pdmrunner"]
    assert api.find("pdmrunner.Client.connect") is not None
    assert api.find("pdm_module_repo.pdmrunner.Client") is None


def test_inspect_collector_uses_pyproject_flit_module_name(tmp_path) -> None:
    repo = write_flit_package_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "flitpkg"
    assert [module.name for module in api.modules] == ["flitpkg", "flitpkg.core"]
    assert api.find("flitpkg.run") is not None
    assert api.find("flitpkg.core.Runner.run") is not None
    assert api.find("published_flit_project.flitpkg.run") is None
    assert api.find("straypkg.leak") is None


def test_inspect_collector_uses_pyproject_flit_default_module_file(
    tmp_path,
) -> None:
    repo = write_flit_module_file_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "flitrunner"
    assert [module.name for module in api.modules] == ["flitrunner"]
    assert api.find("flitrunner.Client.connect") is not None
    assert api.find("helper.leak") is None


def test_inspect_collector_uses_pyproject_import_names_package(tmp_path) -> None:
    repo = write_import_names_package_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "importnamedpkg"
    assert [module.name for module in api.modules] == [
        "importnamedpkg",
        "importnamedpkg.core",
    ]
    assert api.find("importnamedpkg.run") is not None
    assert api.find("published_import_name_project.importnamedpkg.run") is None
    assert api.find("straypkg.leak") is None


def test_inspect_collector_uses_import_names_with_configured_source_root(
    tmp_path,
) -> None:
    repo = write_import_names_package_repo(tmp_path, source_root="lib")

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "importnamedpkg"
    assert [module.name for module in api.modules] == [
        "importnamedpkg",
        "importnamedpkg.core",
    ]
    assert api.find("importnamedpkg.run") is not None
    assert api.find("lib.importnamedpkg.run") is None
    assert api.find("straypkg.leak") is None


def test_inspect_collector_uses_pyproject_import_names_module_file(tmp_path) -> None:
    repo = write_import_names_module_file_repo(tmp_path)

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert api.name == "importnamedrunner"
    assert [module.name for module in api.modules] == ["importnamedrunner"]
    assert api.find("importnamedrunner.run") is not None
    assert api.find("helper.leak") is None


def test_inspect_collector_uses_explicit_setuptools_package_mapping(tmp_path) -> None:
    repo = write_setuptools_package_dir_repo(
        tmp_path,
        repo_name="explicit-repo",
        source_root="lib/samplepkg",
        package_dir_key="samplepkg",
    )

    api = collect_api(repo, collector="inspect", public_policy="__all__")

    assert [module.name for module in api.modules] == ["samplepkg", "samplepkg.core"]
    assert api.find("samplepkg.run") is not None
    assert api.find("lib.samplepkg.run") is None


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


def test_inspect_collector_uses_dataclass_fields_for_class_signature(tmp_path) -> None:
    package_dir = write_dataclass_package(tmp_path)

    api = collect_api(package_dir, collector="inspect", public_policy="__all__")
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
