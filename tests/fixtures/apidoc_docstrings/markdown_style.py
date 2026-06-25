from __future__ import annotations

from dataclasses import dataclass


def load_widget(path: str) -> bool:
    """Load a widget from disk.

    ## Parameters

    | Name | Type | Description |
    | --- | --- | --- |
    | path | str | Input path. |

    ## Returns

    bool: Whether loading succeeded.

    ## Raises

    ValueError: If the path is empty.

    ## Examples

    ```python
    load_widget("widget.json")
    ```

    ## See Also

    Widget.render: Render the loaded widget.

    ## Notes

    Used by Markdown-style parser fixtures.

    ## Renderer Notes

    HTML: Adds stable anchors for generated API pages.
    """

    return bool(path)


class Widget:
    """A Markdown-style widget.

    ## Parameters

    - `name` (`str`): Widget name.

    ## Attributes

    | Name | Type | Description |
    | --- | --- | --- |
    | label | str | User-facing label. |
    """

    label: str = "Widget"

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def title(self) -> str:
        """Widget title.

        ## Returns

        str: Display title.
        """

        return self.name

    def render(self, path: str) -> str:
        """Render the widget.

        ## Parameters

        - `path` (`str`): Output path.

        ## Returns

        str: Rendered path.
        """

        return path


@dataclass
class WidgetRecord:
    """Stored widget record.

    ## Attributes

    - `identifier` (`str`): Stable record id.
    """

    identifier: str
