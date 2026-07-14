# Document Suite Reference

Use `DocumentSuite` when several documents share project variables, citations,
asset roots, and an output directory. Suite factories are ordinary Python
callables; the suite does not provide a macro or string-template language.

```python
from pathlib import Path

from oodocs.components.blocks import Paragraph
from oodocs.components.references import CitationLibrary
from oodocs.document import Document
from oodocs.suite import AssetResolver, DocumentSuite, DocumentSuiteContext

root = Path(__file__).resolve().parent
context = DocumentSuiteContext(
    root=root,
    output_dir=root / "dist",
    variables={"project": "Example Project", "version": "1.0"},
    assets=AssetResolver((Path("assets"),)),
    citations=CitationLibrary(),
)
suite = DocumentSuite("release", context)
suite.add(
    "overview",
    lambda current: Document(
        f"{current.variables['project']} Overview",
        Paragraph(f"Version {current.variables['version']}"),
        citations=current.citations,
    ),
    formats=("html", "pdf"),
)
outputs = suite.save_all()
outputs.save_manifest()
```

## Asset lookup

`context.assets.resolve(path)` searches in a fixed order:

1. an absolute path;
2. the suite root;
3. each registered asset root.

The suite-root file wins when it exists. If the same relative path exists in
two registered roots, resolution raises `AmbiguousAssetError`; it never depends
on root registration order. `require(path)` raises `FileNotFoundError` when no
file exists. Relative registered roots and `output_dir` are anchored to the
suite root when the context is created, so changing the process working
directory later has no effect.

`build()` resolves every path-backed `Figure`, subfigure, cover logo, and figure
inside cover content to an absolute `Path`. `validate_all()` reports missing or
ambiguous assets in each document's `ValidationResult`. Renderers therefore
receive resolved paths and do not perform their own asset search.

## Shared state and output policy

A factory opts into shared citations explicitly with
`Document(..., citations=context.citations)`. The suite never replaces a
library chosen by the factory. Variables remain an ordinary read-only Python
mapping; interpolate or transform them in the factory.

`DocumentSuite.add(..., formats=...)` sets a per-document format policy and
takes precedence over formats passed to `save_all()`. Without an item policy,
the `save_all()` formats apply. Rendering validates every built document before
writing the first file, and the returned `DocumentSuiteBundle` indexes one
`OutputBundle` per item name.

`DocumentSuiteBundle.as_manifest()` returns the suite name, JSON-compatible
variables, and output paths relative to the output directory. Unsupported
runtime-only variable values are omitted. `save_manifest()` writes the mapping
as UTF-8 JSON, using `suite-manifest.json` by default.
