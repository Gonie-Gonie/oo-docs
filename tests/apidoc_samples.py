from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from oodocs.apidoc import ApiPackage, collect_api


def write_sample_package(tmp_path: Path, name: str = "samplepkg") -> Path:
    package_dir = tmp_path / name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            """Sample package.

            Notes:
                Used by apidoc regression tests.
            """

            __all__ = ["Widget", "CONSTANT", "make_widget"]

            CONSTANT: str = "value"
            """Documented constant."""

            class Widget:
                """A documented widget.

                Args:
                    name: Widget name.

                Attributes:
                    label: User-facing label.
                """

                label: str = "Widget"

                def __init__(self, name: str) -> None:
                    self.name = name

                @property
                def title(self) -> str:
                    """Widget title.

                    Returns:
                        str: Title text.
                    """
                    return self.name

                def render(self, path: str) -> str:
                    """Render the widget.

                    Args:
                        path: Output path.

                    Returns:
                        str: Rendered path.

                    Examples:
                        >>> Widget("demo").render("out")
                        'out'
                    """
                    return path

            def make_widget(name: str) -> Widget:
                """Create a widget.

                Args:
                    name: Widget name.

                Returns:
                    Widget: Created widget.
                """
                return Widget(name)
            '''
        ),
        encoding="utf-8",
    )
    return package_dir


def write_undocumented_package(tmp_path: Path, name: str = "undocpkg") -> Path:
    package_dir = tmp_path / name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "def undocumented(path: str) -> str:\n"
        "    return path\n",
        encoding="utf-8",
    )
    return package_dir


def write_private_package(tmp_path: Path, name: str = "privatepkg") -> Path:
    package_dir = tmp_path / name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            """Private API sample."""

            __all__ = ["PublicWidget"]

            _TOKEN: str = "secret"

            class PublicWidget:
                """Public widget."""

                def __init__(self) -> None:
                    self._cache = {}

                def public(self) -> None:
                    """Public method."""

                def _debug(self) -> str:
                    """Private debug hook."""
                    return "debug"

            def _helper() -> None:
                """Private helper."""
            '''
        ),
        encoding="utf-8",
    )
    return package_dir


def write_overload_package(tmp_path: Path, name: str = "overpkg") -> Path:
    package_dir = tmp_path / name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            """Overload API sample."""

            from typing import overload

            __all__ = ["Parser", "parse"]

            @overload
            def parse(value: str) -> str: ...

            @overload
            def parse(value: bytes) -> bytes: ...

            def parse(value):
                """Parse a value.

                Args:
                    value: Value to parse.
                """
                return value

            class Parser:
                """Parser object."""

                @overload
                def parse(self, value: str) -> str: ...

                @overload
                def parse(self, value: bytes) -> bytes: ...

                def parse(self, value):
                    """Parse a value.

                    Args:
                        value: Value to parse.
                    """
                    return value
            '''
        ),
        encoding="utf-8",
    )
    return package_dir


def write_dataclass_package(tmp_path: Path, name: str = "datapkg") -> Path:
    package_dir = tmp_path / name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            """Dataclass API sample."""

            from dataclasses import dataclass, field
            from typing import ClassVar

            __all__ = ["Settings"]

            @dataclass(slots=True)
            class Settings:
                """Runtime settings.

                Attributes:
                    path: Output path.
                    retries: Retry count.
                    tags: Labels attached to the run.
                """

                kind: ClassVar[str] = "settings"
                path: str
                retries: int = 3
                tags: list[str] = field(default_factory=list)
                cache: dict[str, str] = field(default_factory=dict, init=False)
            '''
        ),
        encoding="utf-8",
    )
    return package_dir


def write_setuptools_package_dir_repo(
    tmp_path: Path,
    *,
    repo_name: str = "repo",
    package_name: str = "samplepkg",
    source_root: str = "lib",
    package_dir_key: str = "",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root if package_dir_key else repo / source_root / package_name
    package_dir.mkdir(parents=True)
    package_dir_entry = f'"{package_dir_key}" = "{source_root}"' if package_dir_key else f'"" = "{source_root}"'
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [project]
            name = "sample-project"

            [tool.setuptools]
            package-dir = {{{package_dir_entry}}}
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Sample package."""\nfrom .core import run\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            def run(path: str) -> str:
                """Run a task.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_setuptools_find_repo(
    tmp_path: Path,
    *,
    repo_name: str = "find-repo",
    package_name: str = "findpkg",
    source_root: str = "lib",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root / package_name
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [project]
            name = "{package_name.replace("_", "-")}"

            [tool.setuptools.packages.find]
            where = ["{source_root}"]
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Find package."""\nfrom .core import run\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            def run(path: str) -> str:
                """Run from a find-layout repository.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_hatch_package_repo(
    tmp_path: Path,
    *,
    repo_name: str = "hatch-repo",
    package_name: str = "hatchpkg",
    source_root: str = "lib",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root / package_name
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"

            [project]
            name = "{package_name.replace("_", "-")}"

            [tool.hatch.build.targets.wheel]
            packages = ["{source_root}/{package_name}"]
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Hatch package."""\nfrom .core import run\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            def run(path: str) -> str:
                """Run from a Hatch-layout repository.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_hatch_only_include_repo(
    tmp_path: Path,
    *,
    repo_name: str = "hatch-only-include-repo",
    package_name: str = "onlypkg",
    source_root: str = "lib",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root / package_name
    stray_dir = repo / source_root / "straypkg"
    package_dir.mkdir(parents=True)
    stray_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"

            [project]
            name = "{package_name.replace("_", "-")}"

            [tool.hatch.build.targets.wheel]
            only-include = ["{source_root}/{package_name}"]
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Hatch only-include package."""\nfrom .core import run\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            def run(path: str) -> str:
                """Run from a Hatch only-include repository.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    (stray_dir / "__init__.py").write_text(
        '"""Stray package that Hatch only-include should not expose."""\n__all__ = ["leak"]\n\ndef leak() -> None:\n    """Should not be collected."""\n',
        encoding="utf-8",
    )
    return repo


def write_hatch_multi_package_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "multi-hatch-repo"
    package_names = ("alpha", "beta")
    for package_name in package_names:
        package_dir = repo / "lib" / package_name
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text(
            f'"""{package_name.title()} package."""\nfrom .core import run\n__all__ = ["run"]\n',
            encoding="utf-8",
        )
        (package_dir / "core.py").write_text(
            dedent(
                f'''\
                def run() -> str:
                    """Run {package_name}.

                    Returns:
                        str: Package name.
                    """

                    return "{package_name}"
                '''
            ),
            encoding="utf-8",
        )
    (repo / "pyproject.toml").write_text(
        dedent(
            '''\
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"

            [project]
            name = "multi-hatch-project"

            [tool.hatch.build.targets.wheel]
            packages = ["lib/alpha", "lib/beta"]
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_poetry_package_repo(
    tmp_path: Path,
    *,
    repo_name: str = "poetry-repo",
    package_name: str = "poetrypkg",
    source_root: str = "lib",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root / package_name
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [tool.poetry]
            name = "{package_name.replace("_", "-")}"
            version = "0.1.0"
            packages = [{{ include = "{package_name}", from = "{source_root}" }}]
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Poetry package."""\nfrom .core import run\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            def run(path: str) -> str:
                """Run from a Poetry-layout repository.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_pdm_package_dir_repo(
    tmp_path: Path,
    *,
    repo_name: str = "pdm-repo",
    package_name: str = "pdmpkg",
    source_root: str = "lib",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root / package_name
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["pdm-backend"]
            build-backend = "pdm.backend"

            [project]
            name = "{package_name.replace("_", "-")}"

            [tool.pdm.build]
            package-dir = "{source_root}"
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""PDM package."""\nfrom .core import run\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            def run(path: str) -> str:
                """Run from a PDM-layout repository.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_pdm_module_file_repo(
    tmp_path: Path,
    *,
    repo_name: str = "pdm-module-repo",
    module_name: str = "pdmrunner",
) -> Path:
    repo = tmp_path / repo_name
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["pdm-backend"]
            build-backend = "pdm.backend"

            [project]
            name = "{module_name.replace("_", "-")}"

            [tool.pdm.build]
            includes = ["{module_name}.py"]
            '''
        ),
        encoding="utf-8",
    )
    (repo / f"{module_name}.py").write_text(
        dedent(
            '''\
            __all__ = ["Client", "stream"]

            class Client:
                """Client object."""

                def connect(self, endpoint: str) -> bool:
                    """Connect to an endpoint.

                    Args:
                        endpoint: Target endpoint.

                    Returns:
                        bool: Whether the connection succeeded.
                    """

                    return bool(endpoint)


            def stream(endpoint: str) -> str:
                """Stream from an endpoint.

                Args:
                    endpoint: Target endpoint.

                Returns:
                    str: Endpoint value.
                """

                return endpoint
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_flit_package_repo(
    tmp_path: Path,
    *,
    repo_name: str = "flit-repo",
    package_name: str = "flitpkg",
    project_name: str = "published-flit-project",
    source_root: str = "src",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root / package_name
    extra_package_dir = repo / source_root / "straypkg"
    package_dir.mkdir(parents=True)
    extra_package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["flit_core >=3.11,<5"]
            build-backend = "flit_core.buildapi"

            [project]
            name = "{project_name}"
            version = "0.1.0"
            description = "Flit fixture project."

            [tool.flit.module]
            name = "{package_name}"
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Flit package."""\nfrom .core import Runner, run\n__all__ = ["Runner", "run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            class Runner:
                """Runner from a Flit-layout repository."""

                def run(self, path: str) -> str:
                    """Run a task.

                    Args:
                        path: Input path.

                    Returns:
                        str: Input path.
                    """

                    return path

            def run(path: str) -> str:
                """Run from a Flit-layout repository.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    (extra_package_dir / "__init__.py").write_text(
        '"""Stray package that Flit should not expose."""\n__all__ = ["leak"]\n\ndef leak() -> None:\n    """Should not be collected."""\n',
        encoding="utf-8",
    )
    return repo


def write_flit_module_file_repo(
    tmp_path: Path,
    *,
    repo_name: str = "flit-module-repo",
    module_name: str = "flitrunner",
) -> Path:
    repo = tmp_path / repo_name
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["flit_core >=3.11,<5"]
            build-backend = "flit_core.buildapi"

            [project]
            name = "{module_name.replace("_", "-")}"
            version = "0.1.0"
            description = "Flit module fixture project."
            '''
        ),
        encoding="utf-8",
    )
    (repo / f"{module_name}.py").write_text(
        dedent(
            '''\
            __all__ = ["Client", "connect"]

            class Client:
                """Client object from a Flit module."""

                def connect(self, endpoint: str) -> bool:
                    """Connect to an endpoint.

                    Args:
                        endpoint: Target endpoint.

                    Returns:
                        bool: Whether the connection succeeded.
                    """

                    return bool(endpoint)

            def connect(endpoint: str) -> Client:
                """Create a client.

                Args:
                    endpoint: Target endpoint.

                Returns:
                    Client: Created client.
                """

                return Client()
            '''
        ),
        encoding="utf-8",
    )
    (repo / "helper.py").write_text(
        '"""Helper module that Flit should not expose."""\n__all__ = ["leak"]\n\ndef leak() -> None:\n    """Should not be collected."""\n',
        encoding="utf-8",
    )
    return repo


def write_import_names_package_repo(
    tmp_path: Path,
    *,
    repo_name: str = "import-names-repo",
    package_name: str = "importnamedpkg",
    project_name: str = "published-import-name-project",
    source_root: str = "src",
) -> Path:
    repo = tmp_path / repo_name
    package_dir = repo / source_root / package_name
    stray_dir = repo / source_root / "straypkg"
    package_dir.mkdir(parents=True)
    stray_dir.mkdir(parents=True)
    setuptools_section = (
        f'\n[tool.setuptools]\npackage-dir = {{"" = "{source_root}"}}\n'
        if source_root != "src"
        else ""
    )
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["setuptools>=77"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "{project_name}"
            version = "0.1.0"
            import-names = ["{package_name}"]
            {setuptools_section}
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '"""Import-name package."""\nfrom .core import run\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            def run(path: str) -> str:
                """Run from a declared import-name repository.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    (stray_dir / "__init__.py").write_text(
        '"""Stray package that import-names should not expose."""\n__all__ = ["leak"]\n\ndef leak() -> None:\n    """Should not be collected."""\n',
        encoding="utf-8",
    )
    return repo


def write_import_names_module_file_repo(
    tmp_path: Path,
    *,
    repo_name: str = "import-names-module-repo",
    module_name: str = "importnamedrunner",
) -> Path:
    repo = tmp_path / repo_name
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        dedent(
            f'''\
            [build-system]
            requires = ["setuptools>=77"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "published-module-project"
            version = "0.1.0"
            import-names = ["{module_name}"]
            '''
        ),
        encoding="utf-8",
    )
    (repo / f"{module_name}.py").write_text(
        dedent(
            '''\
            __all__ = ["run"]

            def run(path: str) -> str:
                """Run from a declared import-name module.

                Args:
                    path: Input path.

                Returns:
                    str: Input path.
                """

                return path
            '''
        ),
        encoding="utf-8",
    )
    (repo / "helper.py").write_text(
        '"""Helper module that import-names should not expose."""\n__all__ = ["leak"]\n\ndef leak() -> None:\n    """Should not be collected."""\n',
        encoding="utf-8",
    )
    return repo


def write_mixed_docstring_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "mixed-repo"
    package_dir = repo / "src" / "mixedpkg"
    package_dir.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            '''\
            [project]
            name = "mixed-project"

            [tool.setuptools]
            package-dir = {"" = "src"}

            [tool.oodocs.apidoc]
            collector = "inspect"
            public-policy = "__all__"
            docstring-style = "auto"
            module-prefix = "mixedpkg"
            profile = "manual"
            formats = ["html"]
            sidecars = true
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            """Mixed docstring package."""

            from .core import Client, connect, stream

            __all__ = ["Client", "connect", "stream"]
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "core.py").write_text(
        dedent(
            '''\
            """Core client API."""

            class Client:
                """HTTP client for the mixed sample package.

                Args:
                    endpoint: Base endpoint URL.
                """

                def __init__(self, endpoint: str) -> None:
                    self.endpoint = endpoint

                def connect(self, timeout: float = 1.0) -> bool:
                    """Connect to the configured endpoint.

                    Parameters
                    ----------
                    timeout : float
                        Timeout in seconds.

                    Returns
                    -------
                    bool
                        Whether the connection succeeded.
                    """

                    return bool(self.endpoint) and timeout >= 0

            def connect(endpoint: str) -> Client:
                """Create a client for an endpoint.

                Args:
                    endpoint: Base endpoint URL.

                Returns:
                    Client: Created client instance.
                """

                return Client(endpoint)

            def stream(endpoint: str):
                """Stream updates from an endpoint.

                ## Parameters

                - `endpoint` (`str`): Base endpoint URL.

                ## Yields

                str: Endpoint update payload.
                """

                yield endpoint
            '''
        ),
        encoding="utf-8",
    )
    return repo


def write_single_file_module(tmp_path: Path) -> Path:
    module_path = tmp_path / "singlemod.py"
    module_path.write_text(
        dedent(
            '''\
            """Single-file API module."""

            __all__ = ["Client", "connect", "stream"]

            class Client:
                """Client defined in one Python module.

                Args:
                    endpoint: Base endpoint URL.
                """

                def __init__(self, endpoint: str) -> None:
                    self.endpoint = endpoint

                def connect(self, timeout: float = 1.0) -> bool:
                    """Connect to the configured endpoint.

                    Parameters
                    ----------
                    timeout : float
                        Timeout in seconds.

                    Returns
                    -------
                    bool
                        Whether the connection succeeded.
                    """

                    return bool(self.endpoint) and timeout >= 0

            def connect(endpoint: str) -> Client:
                """Create a client for an endpoint.

                Args:
                    endpoint: Base endpoint URL.

                Returns:
                    Client: Created client instance.
                """

                return Client(endpoint)

            def stream(endpoint: str):
                """Stream updates from an endpoint.

                ## Parameters

                - `endpoint` (`str`): Base endpoint URL.

                ## Yields

                str: Endpoint update payload.
                """

                yield endpoint
            '''
        ),
        encoding="utf-8",
    )
    return module_path


def write_setuptools_py_module_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "single-module-repo"
    source_root = repo / "src"
    source_root.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        dedent(
            '''\
            [project]
            name = "singlemod"

            [tool.setuptools]
            package-dir = {"" = "src"}
            py-modules = ["singlemod"]
            '''
        ),
        encoding="utf-8",
    )
    write_single_file_module(source_root)
    return repo


def write_custom_docstring_parser_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "custom-parser-repo"
    package_dir = repo / "src" / "briefpkg"
    package_dir.mkdir(parents=True)
    (repo / "example_brief_parsers.py").write_text(
        "\n".join(
            [
                "from oodocs.apidoc import ParsedDocstring, docstring_parser_names, register_docstring_parser",
                "",
                "def parse_example_brief(text, qualname=None, module=None):",
                "    first = (text or '').strip().splitlines()[0]",
                "    return ParsedDocstring(summary=f'brief:{first}', style='example-brief')",
                "",
                "if 'example-brief' not in docstring_parser_names():",
                "    register_docstring_parser('example-brief', parse_example_brief)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        dedent(
            '''\
            [project]
            name = "briefpkg"

            [tool.setuptools]
            package-dir = {"" = "src"}

            [tool.oodocs.apidoc]
            collector = "inspect"
            public-policy = "__all__"
            docstring-style = "example-brief"
            docstring-parser-modules = ["example_brief_parsers"]
            profile = "compact"
            formats = ["html"]
            sidecars = true
            '''
        ),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        dedent(
            '''\
            """Brief package."""

            __all__ = ["Runner", "run"]

            class Runner:
                """Runner class."""

            def run():
                """Run custom command."""
            '''
        ),
        encoding="utf-8",
    )
    return repo


def collect_sample_api(tmp_path: Path, **kwargs: object) -> ApiPackage:
    package_dir = write_sample_package(tmp_path)
    options = {
        "collector": "inspect",
        "public_policy": "__all__",
    }
    options.update(kwargs)
    return collect_api(package_dir, **options)
