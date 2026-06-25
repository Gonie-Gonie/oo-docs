from __future__ import annotations

from dataclasses import dataclass


def load_widget(path: str) -> bool:
    """Load a widget from disk.

    Parameters
    ----------
    path : str
        Input path.

    Returns
    -------
    bool
        Whether loading succeeded.

    Raises
    ------
    ValueError
        If the path is empty.

    Examples
    --------
    >>> load_widget("widget.json")
    True

    See Also
    --------
    Widget.render : Render the loaded widget.

    Notes
    -----
    Used by NumPy-style parser fixtures.

    Renderer Notes
    --------------
    HTML: Adds stable anchors for generated API pages.

    Deprecated
    ----------
    Use load_widget_v2 instead.
    """

    return bool(path)


class Widget:
    """A NumPy-style widget.

    Parameters
    ----------
    name : str
        Widget name.

    Attributes
    ----------
    label : str
        User-facing label.
    """

    label: str = "Widget"

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def title(self) -> str:
        """Widget title.

        Returns
        -------
        str
            Display title.
        """

        return self.name

    def render(self, path: str) -> str:
        """Render the widget.

        Parameters
        ----------
        path : str
            Output path.

        Returns
        -------
        str
            Rendered path.
        """

        return path


@dataclass
class WidgetRecord:
    """Stored widget record.

    Attributes
    ----------
    identifier : str
        Stable record id.
    """

    identifier: str
