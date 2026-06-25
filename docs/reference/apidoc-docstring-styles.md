# apidoc Docstring Styles

`parse_docstring(...)` normalizes common Python docstring styles into one
schema.

Supported styles:

- `google`: `Args:`, `Attributes:`, `Returns:`, `Raises:`, `Examples:`,
  `See Also:`, `Notes:`, `Warnings:`, `Renderer Notes:`, and `Deprecated:`.
- `numpy`: dashed section headings such as `Parameters`, `Returns`, `Notes`,
  `Warnings`, and `Renderer Notes`.
- `sphinx`: `:param:`, `:type:`, `:returns:`, `:rtype:`, directives, and code
  blocks.
- `markdown`: Markdown headings, parameter tables, notes, warnings, renderer
  notes, and deprecation sections.
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

    Notes:
        The parsed notes remain available on ApiObject.notes.

    Warnings:
        The parsed warnings render as warning blocks in full profiles.
    """,
    style="google",
)

assert parsed.parameters[0].name == "path"
assert parsed.attributes[0].name == "cache_key"
```

`ParsedDocstring.to_dict()` and `ParsedDocstring.from_dict(...)` preserve the
normalized parser output when a workflow wants to cache raw docstring parse
results before converting them into collected API objects.

`docstring-parser` is used when installed for Google, NumPy, and Sphinx styles;
OODocs keeps fallback parsers so the public API remains usable without the
optional extra.

Use `ApiDocstringParser` when the same parser configuration should be reused
across parsing, collection, coverage, and rendering steps.

```python
from oodocs.apidoc import ApiDocstringParser, collect_api

parser = ApiDocstringParser.auto()
api = collect_api(".", collector="griffe", docstring_style=parser)
```

When an explicit style is requested but the docstring looks like another
supported style, the parser records a `docstring-style-mismatch` warning. These
warnings are available on parsed results and through package issue tables after
collection:

```python
from oodocs.apidoc import collect_api, parse_docstring

parsed = parse_docstring("Summary.\n\nArgs:\n    path: Input path.", style="numpy")
assert parsed.issues[0].code == "docstring-style-mismatch"

api = collect_api(".", docstring_style="numpy")
issue_table = api.to_issue_table()
```

Custom styles can be registered and then used by parser objects or
`collect_api(...)`.

```python
from oodocs.apidoc import ApiDocstringParser, ParsedDocstring, register_docstring_parser

def parse_brief(text, qualname, module):
    return ParsedDocstring(summary=text.strip(), style="brief")

register_docstring_parser("brief", parse_brief)
parser = ApiDocstringParser("brief")
```
