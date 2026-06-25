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


def collect_sample_api(tmp_path: Path, **kwargs: object) -> ApiPackage:
    package_dir = write_sample_package(tmp_path)
    options = {
        "collector": "inspect",
        "public_policy": "__all__",
    }
    options.update(kwargs)
    return collect_api(package_dir, **options)
