# apidoc Docstring Styles

`parse_docstring(...)` normalizes common Python docstring styles into one
schema.

Supported styles:

- `google`: `Args:`, `Attributes:`, `Returns:`, `Yields:`, `Raises:`,
  `Examples:`, `See Also:`, `Notes:`, `Warnings:`, `Renderer Notes:`, and
  `Deprecated:`.
- `numpy`: dashed section headings such as `Parameters`, `Returns`, `Yields`,
  `Raises`, `Notes`, `Warnings`, `Renderer Notes`, and `Deprecated`.
- `sphinx`: `:param:`, `:type:`, `:returns:`, `:rtype:`, `:yields:`,
  `:ytype:`, directives, and code blocks.
- `markdown`: Markdown headings, parameter tables, `Returns`/`Yields`,
  `Raises` colon lines, exception tables, notes, warnings, renderer notes, and
  deprecation sections.
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

For NumPy-style `Returns` and `Yields` sections with multiple named values, the
fallback parser keeps each value in `ApiReturn.description` as a stable
line-delimited entry so rendered reference pages and serialized snapshots do not
lose the return names.

Use `ApiDocstringParser` when the same parser configuration should be reused
across parsing, collection, coverage, and rendering steps.

```python
from oodocs.apidoc import ApiDocstringParser, collect_api

parser = ApiDocstringParser.auto()
api = collect_api(".", collector="griffe", docstring_style=parser)
```

`ApiDocstringStyleName` names the built-in styles used by automatic detection.
`ApiDocstringParser` and `ParsedDocstring.style` also accept registered custom
style names, so a repository can keep its own parser convention in an importable
module and still pass that parser object through `collect_api(...)`, config
sidecars, and rendered issue tables.

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
parsed = parser("Short custom summary.")
assert parsed.style == "brief"
```

For CLI and `pyproject.toml` workflows, put the registration code in an
importable module and list it in `docstring-parser-modules`. The module should
call `register_docstring_parser(...)` when imported:

```python
# docs_parsers.py
from oodocs.apidoc import ParsedDocstring, register_docstring_parser

def parse_brief(text, qualname=None, module=None):
    return ParsedDocstring(summary=text.strip(), style="brief")

register_docstring_parser("brief", parse_brief)
```

```toml
[tool.oodocs.apidoc]
docstring-style = "brief"
docstring-parser-modules = ["docs_parsers"]
```

```powershell
python -m oodocs apidoc build . --config pyproject.toml
```

JSON config files use the same keys, which is useful for generated build
profiles or repository-local automation:

```json
{
  "collector": "inspect",
  "docstring_style": "brief",
  "docstring_parser_modules": ["docs_parsers"],
  "formats": ["html"],
  "out": "artifacts/api",
  "sidecars": true
}
```

```powershell
python -m oodocs apidoc build C:\work\mypkg --config C:\work\mypkg\apidoc-build.json
```

When the config is loaded from a repository path, OODocs temporarily adds the
config directory and its `src/` child to the import path while importing
`docstring-parser-modules`. CLI commands also add the target repository root,
its `src/` child, and the target parent while reading the config, so generated
JSON config files can live outside the target checkout and still load
repository-local parser modules. This lets a command target another checkout
without changing into it first:

```powershell
python -m oodocs apidoc build C:\work\mypkg --config C:\work\mypkg\pyproject.toml --out C:\work\mypkg\artifacts\api
```

The Python API uses the same target-local import path policy when
`docstring_parser_modules` is passed directly:

```python
from oodocs.apidoc import collect_api

api = collect_api(
    r"C:\work\mypkg",
    docstring_parser_modules=("docs_parsers",),
    docstring_style="brief",
)
```

When a Python script reads a generated config file that lives outside the
target checkout, pass the target path while reading the config. The config
reader adds both the config directory and target repository import roots while
validating parser modules:

```python
from oodocs.apidoc import ApiBuildConfig

repo = r"C:\work\mypkg"
build = ApiBuildConfig.read_file(r"C:\configs\mypkg-apidoc.json", target=repo)
outputs = build.save_all(repo, output_dir=r"C:\work\mypkg\artifacts\api")
```

When you construct an `ApiCollectConfig` object directly rather than reading a
file, use `docstring_parser_import_paths` around construction so repo-local
parser modules are importable while the config validates:

```python
from oodocs.apidoc import ApiCollectConfig, collect_api, docstring_parser_import_paths

repo = r"C:\work\mypkg"
with docstring_parser_import_paths(repo):
    config = ApiCollectConfig(
        docstring_parser_modules=("docs_parsers",),
        docstring_style="brief",
    )

api = collect_api(repo, config=config)
```

The same hook can be supplied directly to one command:

```powershell
python -m oodocs apidoc check . --docstring-parser-module docs_parsers --docstring-style brief
```
