# API Objects Example

This example shows the composable API-documentation workflow for any Python
package, module, file, or repository target:

1. collect an `ApiPackage` from a target Python project with an auto docstring
   parser
2. render a full package API reference as DOCX, PDF, and HTML artifacts named
   `oodocs-full-api-reference`
3. render a hand-composed `oodocs-api-objects` document that inserts selected
   class sections, one focused module chapter, a function summary table, and
   coverage evidence into an ordinary OODocs document
4. write deterministic API JSON plus coverage JSON/CSV sidecars for release
   evidence

Run it against the current repository:

```powershell
python examples/api_objects_example/main.py . --config pyproject.toml
```

`--config` accepts a project root, `pyproject.toml`, or JSON config produced by
`oodocs apidoc init`. When supplied, the example reuses the same collector,
public boundary, docstring parser modules, object filters, profile, formats,
and max-level settings as `python -m oodocs apidoc build`. JSON config files
can live outside the target checkout; the example still adds the target root
and configured source roots such as `src/`, `package-dir`, or
`packages.find.where` entries, plus hatch/Poetry package roots, while loading
repository-local parser modules.

Run it against an installed package or importable module:

```powershell
python examples/api_objects_example/main.py oodocs --collector auto
```

For a quick HTML-only check while developing another package:

```powershell
python examples/api_objects_example/main.py C:\path\to\repo --collector inspect --public-policy underscore --to html
```

The script writes rendered files under `artifacts/api-objects-example` by
default. Both the full package reference and the selected composition document
are saved as DOCX, PDF, and HTML unless `--to` is supplied. The generated files
can be reviewed, published, or attached to release evidence directly. The
sidecars use the `oodocs-api-objects.json` and
`oodocs-api-coverage.{json,csv}` filenames.
