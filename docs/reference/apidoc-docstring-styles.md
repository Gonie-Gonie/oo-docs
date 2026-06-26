# apidoc Docstring Styles

`parse_docstring(...)` normalizes common Python docstring styles into one
schema.

Supported styles:

- `google`: `Args:`, `Arguments:`, `Parameters:`, `Keyword Args:`,
  `Keyword Arguments:`, `Kwargs:`, `Attributes:`, `Returns:`, `Yields:`,
  `Raises:`, `Examples:`, `See Also:`, `Notes:`, `Warnings:`,
  `Renderer Notes:`, and `Deprecated:`. Singular aliases such as
  `Parameter:`, `Return:`, `Example:`, `Note:`, and `Warning:` are also
  accepted by automatic detection.
- `numpy`: dashed section headings such as `Parameters`, `Other Parameters`,
  `Attributes`, `Returns`, `Yields`, `Raises`, `Examples`, `See Also`,
  `Notes`, `Warnings`, `Renderer Notes`, and `Deprecated`.
- `sphinx`: `:param:`, `:type:`, `:param *args:`, `:param **kwargs:`,
  `:keyword:`, `:kwarg:`, `:key:`, `:kwtype:`, `:returns:`, `:rtype:`,
  `:yields:`, `:ytype:`, `.. seealso::`,
  `.. admonition:: Renderer Notes`, directives, and code blocks.
- `markdown`: Markdown headings, parameter tables, bullet lists, plain
  `name (type): description` lines, NumPy-like `name : type` definition
  lists, `Parameters`, `Keyword Arguments`, `Other Parameters`,
  `Returns`/`Yields`, `Raises` colon lines, exception tables, notes, warnings,
  renderer notes, and deprecation sections. Singular heading aliases such as
  `## Parameter`, `## Return`, `## Example`, `## Note`, and `## Warning` are
  also accepted by automatic detection.
- `plain`: summary and paragraph extraction only.
- `auto`: style detection.

```python
from oodocs.apidoc import parse_docstring

parsed = parse_docstring(
    """Load data.

    Args:
        path (str): File path.

    Keyword Args:
        retries (int): Retry count.

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
assert parsed.parameters[1].name == "retries"
assert parsed.attributes[0].name == "cache_key"
```

NumPy `Other Parameters` sections are merged into the same normalized
`ApiParameter` list as `Parameters`, so keyword-only arguments render in the
same parameter table:

```python
from oodocs.apidoc import parse_docstring

parsed = parse_docstring(
    """Load data.

    Parameters
    ----------
    path : str
        File path.

    Other Parameters
    ----------------
    timeout : float
        Timeout in seconds.
    """,
    style="numpy",
)

assert [parameter.name for parameter in parsed.parameters] == ["path", "timeout"]
```

Markdown parameter sections can use tables, bullet lists, or plain lines:

```python
from oodocs.apidoc import parse_docstring

parsed = parse_docstring(
    """Load data.

    ## Parameters

    path (str): File path.

    ## Other Parameters

    timeout : float
        Timeout in seconds.
    """,
    style="markdown",
)

assert [parameter.name for parameter in parsed.parameters] == ["path", "timeout"]
```

Sphinx `.. seealso::` and renderer-note admonitions are normalized into
sections that render in reference profiles. Sphinx keyword fields are merged
into the same parameter list, so keyword-only parameters render in the normal
parameter table:

```python
from oodocs.apidoc import parse_docstring

parsed = parse_docstring(
    """Load data.

    :param path: File path.
    :type path: str
    :keyword cache: Whether to use cached data.
    :kwtype cache: bool
    :returns: Loaded object.
    :rtype: object

    .. seealso::

        :func:`open_data`: Open the source file.

    .. admonition:: Renderer Notes

        HTML: :func:`open_data` receives a stable anchor.
    """,
    style="sphinx",
)

assert [parameter.name for parameter in parsed.parameters] == ["path", "cache"]
assert parsed.see_also[0].label == "open_data"
assert parsed.renderer_notes[0].output_format == "html"
```

Sphinx varargs names are preserved with their leading stars so they match
signature parameters during coverage checks:

```python
from oodocs.apidoc import parse_docstring

parsed = parse_docstring(
    """Call a hook.

    :param *args: Positional hook arguments.
    :type *args: tuple[object, ...]
    :param **kwargs: Keyword hook arguments.
    :type **kwargs: dict[str, object]
    """,
    style="sphinx",
)

assert [parameter.name for parameter in parsed.parameters] == ["*args", "**kwargs"]
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

```python
from oodocs.apidoc import ApiBuildConfig

ApiBuildConfig.from_pyproject(".").save_all(".")
```

JSON config files use the same keys, which is useful for generated build
profiles or repository-local automation:

```json
{
  "collector": "inspect",
  "docstring_style": "brief",
  "docstring_parser_modules": ["docs_parsers"],
  "formats": ["docx", "pdf", "html"],
  "out": "artifacts/api",
  "sidecars": true
}
```

```python
from oodocs.apidoc import ApiBuildConfig

repo = r"C:\work\mypkg"
ApiBuildConfig.load_file(r"C:\work\mypkg\apidoc-build.json", target=repo).save_all(repo)
```

When the config is loaded from a repository path, OODocs temporarily adds the
config directory and its configured source roots to the import path while
importing `docstring-parser-modules`. Source roots include `src/`,
`[tool.setuptools] package-dir`, and `[tool.setuptools.packages.find] where`
entries, plus hatch wheel package paths, Poetry package entries, PDM
build source roots, `[project] import-names`, and Flit import-name source
roots. CLI
commands also add the target repository root, those target source roots, and
the target parent while reading the config, so generated JSON config files can
live outside the target checkout and still load repository-local parser
modules. This lets a command target another checkout without changing into it
first:

```python
from oodocs.apidoc import ApiBuildConfig

repo = r"C:\work\mypkg"
ApiBuildConfig.load_file(r"C:\work\mypkg\pyproject.toml", target=repo).save_all(repo)
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
build = ApiBuildConfig.load_file(r"C:\configs\mypkg-apidoc.json", target=repo)
outputs = build.save_all(repo, output_dir=r"C:\work\mypkg\artifacts\api")
assert outputs["docx"].exists()
assert outputs["pdf"].exists()
assert outputs["html"].exists()
assert outputs["api-json"].exists()
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
