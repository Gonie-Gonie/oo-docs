# Insert API Sections

Use this workflow when an ordinary Python development repository should provide
API sections for a larger authored document. The collector reads a package or
repository checkout, normalizes docstrings into `ApiObject` instances, and lets
you insert only the selected objects as normal OODocs blocks.

```python
from oodocs import Document
from oodocs.apidoc import ApiDocstringParser, api_objects_to_chapter, collect_api

parser = ApiDocstringParser.auto()
api = collect_api(
    ".",
    collector="griffe",
    public_policy="__all__",
    docstring_style=parser,
)

classes = api.select(kind="class", module_prefix="mypkg")

doc = Document(
    "Developer Notes",
    api_objects_to_chapter(
        "Selected API",
        classes[:5],
        profile="manual",
        max_level=3,
    ),
)
```

Use `profile="compact"` for dense reference appendices, `profile="manual"` for
guide-like prose, and `profile="reference"` when you want signatures,
parameters, returns, examples, see-also entries, and source locations.

For a `src/` layout repository, run the script from the repository root and pass
`.`. OODocs resolves the package root from the checkout and from
`[tool.setuptools] package-dir` or `[tool.setuptools.packages.find]` settings
when they exist, plus hatch wheel package paths, Poetry `packages` entries,
PDM build source roots, packaging-standard `[project] import-names`, and Flit
import-name metadata.
Single-module projects that declare
`[tool.setuptools] py-modules`, PDM module `includes`, or Flit module metadata
are also collected from the repository root, so `src/reporting.py` renders as
`reporting`, not `src.reporting`.

For a standalone module, pass the `.py` file path directly. The file stem is
used as the module name for lookup and anchors:

```python
from oodocs.apidoc import ApiDocstringParser, collect_api

api = collect_api(
    "scripts/reporting.py",
    collector="inspect",
    public_policy="underscore",
    docstring_style=ApiDocstringParser.auto(),
)
section = api.find("reporting.build_report").to_section(profile="manual")
```

## Build A Full Reference Bundle

Use `ApiPackage.to_document(...)` when the whole collected package should become
a standalone API reference. The returned value is a normal `Document`, so the
same `save_all(...)` call can produce DOCX, PDF, and HTML through the usual
OODocs renderer path. Keep the collected API and coverage result beside those
files as deterministic JSON/CSV sidecars when release review needs evidence.

```python
from oodocs.apidoc import ApiDocstringParser, check_api_docs, collect_api

api = collect_api(
    ".",
    collector="griffe",
    public_policy="__all__",
    docstring_style=ApiDocstringParser.auto(),
)
coverage = check_api_docs(api, fail_under=0.90)

document = api.to_document(
    title=f"{api.name} API Reference",
    profile="reference",
    max_level=3,
)
document.save_all(
    "artifacts/api",
    stem=f"{api.name}-api",
    formats=("docx", "pdf", "html"),
)
api.write_json("artifacts/api/api-objects.json")
coverage.write_json("artifacts/api/api-coverage.json")
coverage.write_csv("artifacts/api/api-coverage.csv")
```

## Insert One Object

Use `find(...)` when a guide needs one class or function rather than a full
reference chapter.

```python
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import ApiDocstringParser, collect_api

api = collect_api(".", collector="griffe", docstring_style=ApiDocstringParser.auto())
client = api.find("mypkg.Client")

doc = Document(
    "Client Integration Guide",
    Chapter(
        "Client API",
        Paragraph("The following section is generated from the package source."),
        client.to_section(level=2, profile="manual") if client else Paragraph("Client API not found."),
    ),
)
```

`ApiObject.to_section(...)` returns a normal OODocs `Section`, so it can be
mixed with handwritten paragraphs, tables, figures, and generated pages.

When the target object is already importable in a development environment, pass
the live class, function, method, property, or bound method to
`collect_object_api(...)`.

```python
from mypkg.client import Client
from oodocs import Chapter, Document
from oodocs.apidoc import collect_object_api

client_api = collect_object_api(
    Client,
    collector="inspect",
    public_policy="underscore",
)

doc = Document(
    "Client API Notes",
    Chapter("Client", client_api.to_section(level=2, profile="manual")),
)
```

For repository checkouts that should not depend on import path setup, pass the
checkout as `target` and select the fully qualified object from the collected
API tree.

```python
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import collect_object_api

client_api = collect_object_api(
    "mypkg.client.Client",
    target=".",
    public_policy="__all__",
)

doc = Document(
    "Client API Notes",
    Chapter(
        "Client",
        Paragraph("This section is generated from the current checkout."),
        client_api.to_section(level=2, profile="manual"),
    ),
)
```

## Insert One Module

Use `collect_module_api(...)` when a guide or appendix needs one module instead
of the whole package. Pass `target` for a repository checkout, package
directory, or Python file that should be collected before module selection.

```python
from oodocs import Document
from oodocs.apidoc import collect_module_api

module = collect_module_api(
    "mypkg.adapters.http",
    target=".",
    public_policy="underscore",
)

doc = Document(
    "HTTP Adapter API",
    module.to_chapter(profile="manual"),
)
```

For already importable modules, omit `target`:

```python
module = collect_module_api(
    "mypkg.adapters.http",
    collector="inspect",
    public_policy="underscore",
)
```

## Insert A Summary Table

When release notes or design docs need an index instead of detailed sections,
filter objects first and pass the subset to `to_summary_table(...)`.

```python
from oodocs import Chapter, Document, Paragraph
from oodocs.apidoc import collect_api

api = collect_api(".", collector="griffe", public_policy="__all__")
functions = api.select(kind="function", module_prefix="mypkg.adapters")

doc = Document(
    "Adapter Release Notes",
    Chapter(
        "Public Adapter Functions",
        Paragraph("This table is generated from the current checkout."),
        api.to_summary_table(functions, profile="compact"),
    ),
)
```

## Keep Coverage Evidence

Use `check_api_docs(...)` on the same `ApiPackage` before rendering when the
document should include docstring coverage or when CI should keep sidecars for
review.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import check_api_docs, collect_api

api = collect_api(".", collector="griffe", docstring_style="auto")
coverage = check_api_docs(api, fail_under=0.90)

doc = Document(
    "API Review",
    Chapter("Selected API", *[obj.to_section(level=2) for obj in api.classes()[:3]]),
    Chapter("Coverage", coverage.to_table()),
)

api.write_json("artifacts/api/api-objects.json")
coverage.write_json("artifacts/api/api-coverage.json")
coverage.write_csv("artifacts/api/api-coverage.csv")
```

The same options can live in `pyproject.toml` so Python scripts and CLI commands
collect the same public surface:

```toml
[tool.oodocs.apidoc]
collector = "griffe"
public-policy = "__all__"
docstring-style = "auto"
module-prefix = "mypkg"
profile = "manual"
formats = ["docx", "pdf", "html"]
sidecars = true
```

`module-prefix` is a single post-collection filter. Use
`module-include-patterns = ["mypkg.*", "plugins.*"]` when the collection step
should include several module families.

Then build a full reference bundle or sidecars from the command line:

```powershell
python -m oodocs apidoc build . --config pyproject.toml --out artifacts/api
```

## Custom Parser Modules

If a repository uses a house docstring format, register it once and pass the
parser name through the same collection flow.

```python
# docs_parsers.py
from oodocs.apidoc import ParsedDocstring, register_docstring_parser

def parse_brief(text, qualname=None, module=None):
    return ParsedDocstring(summary=(text or "").strip(), style="brief")

register_docstring_parser("brief", parse_brief)
```

```toml
[tool.oodocs.apidoc]
docstring-style = "brief"
docstring-parser-modules = ["docs_parsers"]
```

`collect_api(...)`, `check_api_docs(...)`, and `python -m oodocs apidoc build`
will all use the registered parser after the module is imported.
