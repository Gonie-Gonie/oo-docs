# API Objects Example

This example shows the composable API-documentation workflow for any Python
package, module, file, or repository target:

1. collect an `ApiPackage` from a target Python project with an auto docstring
   parser
2. render a user-facing help-book API reference as DOCX, PDF, and HTML
   artifacts named `oodocs-api-reference`
3. render a hand-composed `oodocs-api-object-composition` document that inserts
   selected class sections, one focused module chapter, a function summary
   table, and coverage evidence into an ordinary OODocs document
4. write deterministic API object tree JSON plus coverage JSON/CSV sidecars for
   release evidence

The help-book reference keeps coverage evidence out of the reader-facing
chapters by default. Coverage remains available in the composition document and
in the JSON/CSV sidecars.

Run it against the current repository:

```powershell
python examples/api_objects_example/main.py . --config pyproject.toml
```

`--config` accepts a project root, `pyproject.toml`, or JSON config produced by
`oodocs apidoc init`. When supplied, the example reuses the same collector,
public boundary, docstring parser modules, object filters, output formats, and
max-heading-level settings as `ApiHelpBookConfig.save_all(...)`. JSON config files
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
python examples/api_objects_example/main.py ../other-repo --collector inspect --public-policy underscore --outputs html
```

Composable object-selection pattern:

```python
from examples.api_objects_example.main import collect_target_api
from oodocs import Chapter

api = collect_target_api("my_package", public_policy="__all__")
classes = api.select_objects(kind="class", module_prefix="my_package.core")
chapter = Chapter(
    "Core Classes",
    *[obj.to_section(level=2, presentation="manual") for obj in classes],
)
```

The script writes rendered files under `artifacts/api-objects-example` by
default. Both the help-book reference and the selected composition document are
saved as DOCX, PDF, and HTML unless `--outputs` is supplied. The generated files
can be reviewed, published, or attached to release evidence directly. The
sidecars use the `oodocs-api-object-tree.json` and
`oodocs-api-coverage.{json,csv}` filenames.
