# apidoc Docstring Styles

`parse_docstring(...)` normalizes common Python docstring styles into one
schema.

Supported styles:

- `google`: `Args:`, `Attributes:`, `Returns:`, `Raises:`, `Examples:`,
  `See Also:`, `Notes:`, `Warnings:`, `Renderer Notes:`, and `Deprecated:`.
- `numpy`: dashed section headings such as `Parameters` and `Returns`.
- `sphinx`: `:param:`, `:type:`, `:returns:`, `:rtype:`, directives, and code
  blocks.
- `markdown`: Markdown headings and parameter tables.
- `plain`: summary and paragraph extraction only.
- `auto`: style detection.

```python
from oodocs.apidoc import parse_docstring

parsed = parse_docstring(
    """Load data.

    Args:
        path (str): File path.

    Attributes:
        cache_key (str): Stable cache key used by generated indexes.

    Returns:
        bool: Whether loading succeeded.
    """,
    style="google",
)

assert parsed.parameters[0].name == "path"
assert parsed.attributes[0].name == "cache_key"
```

`docstring-parser` is used when installed for Google, NumPy, and Sphinx styles;
OODocs keeps fallback parsers so the public API remains usable without the
optional extra.

