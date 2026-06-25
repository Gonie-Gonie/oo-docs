from __future__ import annotations

from dataclasses import dataclass


def load_widget(path: str) -> bool:
    """Load a widget from disk.

    This fixture intentionally uses plain prose without structured sections.
    """

    return bool(path)


class Widget:
    """A plain-style widget.

    The class has only prose, so structured parser fields remain empty.
    """

    label: str = "Widget"

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def title(self) -> str:
        """Widget title.

        Returns are described only as prose.
        """

        return self.name

    def render(self, path: str) -> str:
        """Render the widget.

        Parameters are described only as prose.
        """

        return path


@dataclass
class WidgetRecord:
    """Stored widget record.

    The identifier field exists for dataclass attribute fixture coverage.
    """

    identifier: str
