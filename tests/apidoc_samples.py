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

            from .core import Client, connect

            __all__ = ["Client", "connect"]
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
