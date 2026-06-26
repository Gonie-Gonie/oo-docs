from __future__ import annotations

import json

import pytest

from apidoc_samples import (
    write_flit_package_repo,
    write_hatch_package_repo,
    write_import_names_package_repo,
    write_pdm_package_dir_repo,
    write_setuptools_find_repo,
)
from oodocs.apidoc import (
    ApiHelpBookConfig,
    ApiCollectConfig,
    ApiDocstringParser,
    ApiPublicPolicy,
    collect_api,
    docstring_parser_names,
)


def test_apidoc_config_roundtrip_supports_general_repo_policy(tmp_path) -> None:
    config = ApiHelpBookConfig(
        collection=ApiCollectConfig(
            collector="inspect",
            fallback_collector="none",
            public_policy=ApiPublicPolicy.explicit("samplepkg.Widget"),
            docstring_style=ApiDocstringParser.google(),
            include_private=True,
            include_attributes=False,
            include_properties=False,
            include_methods=False,
            include_source_locations=False,
            module_exclude_patterns=("samplepkg.tests*",),
            object_exclude_patterns=("*.render_to_pdf", "*.render_to_html"),
        ),
        presentation="website",
        output_formats=("html",),
        output_dir="artifacts/api",
        include_coverage=False,
        include_uncategorized_appendix=False,
        sidecars=True,
    )

    path = config.save_json(tmp_path / "apidoc-config.json")
    readback = ApiHelpBookConfig.load_json(path)

    assert readback.collection.public_policy == "explicit"
    assert readback.collection.fallback_collector == "none"
    assert readback.collection.explicit_names == ("samplepkg.Widget",)
    assert readback.collection.docstring_style == "google"
    assert readback.collection.include_private is True
    assert readback.collection.include_attributes is False
    assert readback.collection.include_properties is False
    assert readback.collection.include_methods is False
    assert readback.collection.include_source_locations is False
    assert readback.collection.object_exclude_patterns == (
        "*.render_to_pdf",
        "*.render_to_html",
    )
    assert readback.output_formats == ("html",)
    assert readback.include_coverage is False
    assert readback.include_uncategorized_appendix is False
    assert ApiCollectConfig.from_dict({"fallback-parser": "none"}).fallback_collector == "none"


def test_apidoc_build_config_rejects_sequence_module_prefix() -> None:
    with pytest.raises(TypeError, match="module_prefix must be a string"):
        ApiHelpBookConfig.from_dict({"module-prefix": ["samplepkg"]})


def test_apidoc_config_load_file_accepts_target_for_parser_modules(tmp_path) -> None:
    repo = tmp_path / "target-config-repo"
    package_dir = repo / "src" / "targetconfigpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "targetconfigpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "target_config_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_target_config_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"target-config:{first}", style="target-config-brief")',
                "",
                'if "target-config-brief" not in docstring_parser_names():',
                '    register_docstring_parser("target-config-brief", parse_target_config_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Target-aware config package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run through target-aware config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "external-collect-config.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "target-config-brief",
                "docstring_parser_modules": ["target_config_parsers"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "target-config-brief" not in docstring_parser_names()
    with pytest.raises(ImportError):
        ApiCollectConfig.load_file(config_path)

    config = ApiCollectConfig.load_file(config_path, target=repo)
    api = collect_api(repo, config=config)
    run = api.find_object("targetconfigpkg.run")

    assert run is not None
    assert run.summary == "target-config:Run through target-aware config."


def test_apidoc_build_config_load_file_accepts_target_for_parser_modules(tmp_path) -> None:
    repo = tmp_path / "target-build-config-repo"
    package_dir = repo / "src" / "targetbuildpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "targetbuildpkg"',
                "",
                "[tool.setuptools]",
                'package-dir = {"" = "src"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "target_build_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_target_build_style(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                '    return ParsedDocstring(summary=f"target-build:{first}", style="target-build-brief")',
                "",
                'if "target-build-brief" not in docstring_parser_names():',
                '    register_docstring_parser("target-build-brief", parse_target_build_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "\n".join(
            [
                '"""Target-aware build config package."""',
                "",
                '__all__ = ["run"]',
                "",
                "def run() -> None:",
                '    """Run through target-aware build config."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "external-build-config.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "target-build-brief",
                "docstring_parser_modules": ["target_build_parsers"],
                "presentation": "compact",
                "output_formats": ["html"],
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "target-build-brief" not in docstring_parser_names()
    with pytest.raises(ImportError):
        ApiHelpBookConfig.load_file(config_path)

    build = ApiHelpBookConfig.load_file(config_path, target=repo)
    api = collect_api(repo, config=build.collection)
    run = api.find_object("targetbuildpkg.run")

    assert build.presentation == "compact"
    assert build.output_formats == ("html",)
    assert run is not None
    assert run.summary == "target-build:Run through target-aware build config."


def test_apidoc_build_config_load_file_uses_setuptools_find_target_import_roots(tmp_path) -> None:
    repo = write_setuptools_find_repo(
        tmp_path,
        repo_name="find-target-build-config-repo",
        package_name="findtargetpkg",
    )
    parser_path = repo / "lib" / "findtargetpkg" / "docs_parsers.py"
    parser_path.write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_find_target_style(text, qualname=None, module=None):",
                "    lines = (text or '').strip().splitlines()",
                "    first = lines[0] if lines else ''",
                "    summary = f'find-target:{first}' if first else None",
                '    return ParsedDocstring(summary=summary, style="find-target-brief")',
                "",
                'if "find-target-brief" not in docstring_parser_names():',
                '    register_docstring_parser("find-target-brief", parse_find_target_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "external-find-build-config.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "find-target-brief",
                "docstring_parser_modules": ["findtargetpkg.docs_parsers"],
                "presentation": "compact",
                "output_formats": ["html"],
                "module_exclude_patterns": ["*.docs_parsers"],
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "find-target-brief" not in docstring_parser_names()
    with pytest.raises(ImportError):
        ApiHelpBookConfig.load_file(config_path)

    build = ApiHelpBookConfig.load_file(config_path, target=repo)
    api = build.collect(repo)
    document = build.to_help_book(repo)
    run = api.find_object("findtargetpkg.run")

    assert document.validate(formats=("html",)).ok
    assert run is not None
    assert run.summary == "find-target:Run from a find-layout repository."


def test_apidoc_build_config_load_file_uses_hatch_target_import_roots(tmp_path) -> None:
    repo = write_hatch_package_repo(
        tmp_path,
        repo_name="hatch-target-build-config-repo",
        package_name="hatchtargetpkg",
    )
    parser_path = repo / "lib" / "hatchtargetpkg" / "docs_parsers.py"
    parser_path.write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_hatch_target_style(text, qualname=None, module=None):",
                "    lines = (text or '').strip().splitlines()",
                "    first = lines[0] if lines else ''",
                "    summary = f'hatch-target:{first}' if first else None",
                '    return ParsedDocstring(summary=summary, style="hatch-target-brief")',
                "",
                'if "hatch-target-brief" not in docstring_parser_names():',
                '    register_docstring_parser("hatch-target-brief", parse_hatch_target_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "external-hatch-build-config.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "hatch-target-brief",
                "docstring_parser_modules": ["hatchtargetpkg.docs_parsers"],
                "presentation": "compact",
                "output_formats": ["html"],
                "module_exclude_patterns": ["*.docs_parsers"],
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "hatch-target-brief" not in docstring_parser_names()
    with pytest.raises(ImportError):
        ApiHelpBookConfig.load_file(config_path)

    build = ApiHelpBookConfig.load_file(config_path, target=repo)
    api = build.collect(repo)
    document = build.to_help_book(repo)
    run = api.find_object("hatchtargetpkg.run")

    assert document.validate(formats=("html",)).ok
    assert run is not None
    assert run.summary == "hatch-target:Run from a Hatch-layout repository."


def test_apidoc_build_config_load_file_uses_pdm_target_import_roots(tmp_path) -> None:
    repo = write_pdm_package_dir_repo(
        tmp_path,
        repo_name="pdm-target-build-config-repo",
        package_name="pdmtargetpkg",
    )
    parser_path = repo / "lib" / "pdmtargetpkg" / "docs_parsers.py"
    parser_path.write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_pdm_target_style(text, qualname=None, module=None):",
                "    lines = (text or '').strip().splitlines()",
                "    first = lines[0] if lines else ''",
                "    summary = f'pdm-target:{first}' if first else None",
                '    return ParsedDocstring(summary=summary, style="pdm-target-brief")',
                "",
                'if "pdm-target-brief" not in docstring_parser_names():',
                '    register_docstring_parser("pdm-target-brief", parse_pdm_target_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "external-pdm-build-config.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "pdm-target-brief",
                "docstring_parser_modules": ["pdmtargetpkg.docs_parsers"],
                "presentation": "compact",
                "output_formats": ["html"],
                "module_exclude_patterns": ["*.docs_parsers"],
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "pdm-target-brief" not in docstring_parser_names()
    with pytest.raises(ImportError):
        ApiHelpBookConfig.load_file(config_path)

    build = ApiHelpBookConfig.load_file(config_path, target=repo)
    api = build.collect(repo)
    document = build.to_help_book(repo)
    run = api.find_object("pdmtargetpkg.run")

    assert document.validate(formats=("html",)).ok
    assert run is not None
    assert run.summary == "pdm-target:Run from a PDM-layout repository."


def test_apidoc_build_config_load_file_uses_flit_target_import_roots(tmp_path) -> None:
    repo = write_flit_package_repo(
        tmp_path,
        repo_name="flit-target-build-config-repo",
        package_name="flittargetpkg",
    )
    parser_path = repo / "src" / "flittargetpkg" / "docs_parsers.py"
    parser_path.write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_flit_target_style(text, qualname=None, module=None):",
                "    lines = (text or '').strip().splitlines()",
                "    first = lines[0] if lines else ''",
                "    summary = f'flit-target:{first}' if first else None",
                '    return ParsedDocstring(summary=summary, style="flit-target-brief")',
                "",
                'if "flit-target-brief" not in docstring_parser_names():',
                '    register_docstring_parser("flit-target-brief", parse_flit_target_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "external-flit-build-config.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "flit-target-brief",
                "docstring_parser_modules": ["flittargetpkg.docs_parsers"],
                "presentation": "compact",
                "output_formats": ["html"],
                "module_exclude_patterns": ["*.docs_parsers"],
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "flit-target-brief" not in docstring_parser_names()
    with pytest.raises(ImportError):
        ApiHelpBookConfig.load_file(config_path)

    build = ApiHelpBookConfig.load_file(config_path, target=repo)
    api = build.collect(repo)
    document = build.to_help_book(repo)
    run = api.find_object("flittargetpkg.run")

    assert document.validate(formats=("html",)).ok
    assert run is not None
    assert run.summary == "flit-target:Run from a Flit-layout repository."
    assert api.find_object("straypkg.leak") is None


def test_apidoc_build_config_load_file_uses_import_names_target_import_roots(
    tmp_path,
) -> None:
    repo = write_import_names_package_repo(
        tmp_path,
        repo_name="import-names-target-build-config-repo",
        package_name="importnamestargetpkg",
    )
    parser_path = repo / "src" / "importnamestargetpkg" / "docs_parsers.py"
    parser_path.write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_import_names_target_style(text, qualname=None, module=None):",
                "    lines = (text or '').strip().splitlines()",
                "    first = lines[0] if lines else ''",
                "    summary = f'import-names-target:{first}' if first else None",
                '    return ParsedDocstring(summary=summary, style="import-names-target-brief")',
                "",
                'if "import-names-target-brief" not in docstring_parser_names():',
                '    register_docstring_parser("import-names-target-brief", parse_import_names_target_style)',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "external-import-names-build-config.json"
    config_path.write_text(
        json.dumps(
            {
                "collector": "inspect",
                "public_policy": "__all__",
                "docstring_style": "import-names-target-brief",
                "docstring_parser_modules": ["importnamestargetpkg.docs_parsers"],
                "presentation": "compact",
                "output_formats": ["html"],
                "module_exclude_patterns": ["*.docs_parsers"],
                "sidecars": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert "import-names-target-brief" not in docstring_parser_names()
    with pytest.raises(ImportError):
        ApiHelpBookConfig.load_file(config_path)

    build = ApiHelpBookConfig.load_file(config_path, target=repo)
    api = build.collect(repo)
    document = build.to_help_book(repo)
    run = api.find_object("importnamestargetpkg.run")

    assert document.validate(formats=("html",)).ok
    assert run is not None
    assert run.summary == "import-names-target:Run from a declared import-name repository."
    assert api.find_object("straypkg.leak") is None
