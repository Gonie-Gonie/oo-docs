from __future__ import annotations

from dataclasses import dataclass


def load_widget(path: str) -> bool:
    """Load a widget from disk.

    :param path: Input path.
    :type path: str
    :returns: Whether loading succeeded.
    :rtype: bool
    :raises ValueError: If the path is empty.

    .. code-block:: python

        load_widget("widget.json")

    .. note::

        Used by Sphinx-style parser fixtures.

    .. warning::

        Fixture warnings are parser-visible.

    .. deprecated::

        Use load_widget_v2 instead.
    """

    return bool(path)


class Widget:
    """A Sphinx-style widget.

    :param name: Widget name.
    :type name: str
    :ivar label: User-facing label.
    :vartype label: str
    """

    label: str = "Widget"

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def title(self) -> str:
        """Widget title.

        :returns: Display title.
        :rtype: str
        """

        return self.name

    def render(self, path: str) -> str:
        """Render the widget.

        :param path: Output path.
        :type path: str
        :returns: Rendered path.
        :rtype: str
        """

        return path


@dataclass
class WidgetRecord:
    """Stored widget record.

    :ivar identifier: Stable record id.
    :vartype identifier: str
    """

    identifier: str
