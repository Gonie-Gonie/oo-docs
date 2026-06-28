# Custom Styles Example

This example shows the named-style workflow for teams that want reusable
paragraph, table, box, and inline-chip styles without duplicating visual options
on every document object.

Use it when you want to verify that a `StyleSheet` can carry a small design
system through DOCX, PDF, and HTML rendering.

Run the full bundle:

```powershell
python examples/style_cleanup_smoke/main.py --output-dir artifacts/style-cleanup-smoke
```

The directory name and artifact stem remain `style_cleanup_smoke` for release
continuity; in the example catalog this is the custom styles workflow.

Render only one or two formats while iterating:

```powershell
python examples/style_cleanup_smoke/main.py --output-dir artifacts/style-cleanup-smoke --outputs html --quiet
python examples/style_cleanup_smoke/main.py --outputs pdf --outputs html
```

Programmatic entry points:

- `create_stylesheet()` builds the reusable `StyleSheet`.
- `write_stylesheet_sidecar(...)` and `load_stylesheet_sidecar(...)` demonstrate
  exporting a stylesheet to JSON and loading it back before rendering.
- `build_document()` returns the renderable `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs, writes `style-cleanup-smoke-stylesheet.json`, and returns a
  `StyleExampleBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
