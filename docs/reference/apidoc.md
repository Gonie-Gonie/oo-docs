# apidoc Reference

`oodocs.apidoc` collects Python API metadata into renderer-neutral objects that
can be queried, serialized, checked for docstring coverage, or inserted into
OODocs documents.

Install the API collection dependencies before using the Griffe collector or
docstring parsers:

```powershell
pip install "oodocs[apidoc]"
```

## Collectors

- `collector="griffe"` reads source without importing the target package.
- `collector="inspect"` imports live modules and objects.
- `collector="auto"` prefers griffe when available and falls back according to
  `fallback_collector`.

Targets can be import names, package directories, repository roots, or `.py`
files. Repository roots can use `src/`, setuptools, hatch, Poetry, PDM, Flit,
and `[project] import-names` metadata.

```python
from oodocs.apidoc import collect_api

api = collect_api(".", collector="griffe", public_policy="__all__")
```

## Docstring Styles

Built-in styles are `auto`, `google`, `numpy`, `sphinx`, `markdown`, and
`plain`. Parser extension APIs live in `oodocs.apidoc.docstring`.

```python
from oodocs.apidoc import collect_api
from oodocs.apidoc.docstring import ApiDocstringParser, parse_docstring

parser = ApiDocstringParser.auto()
parsed = parse_docstring("Load.\n\nArgs:\n    path: Input path.")
api = collect_api(".", docstring_style=parser)
```

Custom parser modules should call `register_docstring_parser(...)` at import
time and be listed in `docstring-parser-modules`.

## Presentation Profiles

- `help`: user-facing help pages; source locations are hidden by default.
- `manual`: guide-friendly sections for authored documents.
- `compact`: dense appendices and summary output.
- `reference`: full signatures and supporting metadata.
- `evidence`: review/evidence output with source locations.
- `review`: DOCX-friendly review-note output.
- `website`: HTML anchor/source-link oriented output.

Enable source rendering explicitly when a help-style page needs it:

```python
from oodocs.apidoc import ApiPresentationProfile

profile = ApiPresentationProfile.help().with_source()
document = api.to_help_book(presentation=profile)
```

## pyproject Configuration

Keep the base table user-facing and put coverage/inventory output in a named
profile table.

```toml
[tool.oodocs.apidoc]
collector = "griffe"
public-policy = "__all__"
docstring-style = "auto"
presentation = "help"
include-source = false
include-coverage = false
include-uncategorized-appendix = false
output-formats = ["docx", "pdf", "html"]
output-dir = "artifacts/api"
stem = "oodocs-api"
sidecars = true

[tool.oodocs.apidoc.evidence]
presentation = "evidence"
include-source = true
include-coverage = true
include-uncategorized-appendix = true
sidecars = true
```

```python
from oodocs.apidoc import ApiHelpBookConfig

reference = ApiHelpBookConfig.from_pyproject(".")
evidence = ApiHelpBookConfig.from_pyproject(".", profile="evidence")
```

## CLI

```powershell
python -m oodocs apidoc collect . --config pyproject.toml --save-json artifacts/api-index.json
python -m oodocs apidoc check . --config pyproject.toml --fail-under 0.90 --save-json artifacts/api-coverage.json --save-csv artifacts/api-coverage.csv
python -m oodocs apidoc snapshot . --config pyproject.toml --save-json artifacts/api-snapshot.json
python -m oodocs apidoc diff artifacts/api-base.json artifacts/api-head.json --save-json artifacts/api-diff.json
```

Rendered API documents are created through Python with
`ApiHelpBookConfig.save_all(...)`.

## Sidecars

`save_all(..., sidecars=True)` writes the rendered document plus API object tree
and coverage JSON/CSV sidecars. Sidecars are release/development evidence; they
should not be folded back into the user-facing API reference unless an evidence
profile explicitly asks for that.
