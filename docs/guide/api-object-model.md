# API Object Model

`oodocs.apidoc` turns a Python package, module, or repository into a tree of
objects that can be queried before rendering. The collector returns an
`ApiPackage`; each package contains `ApiModule` instances; each module contains
`ApiObject` instances for classes, functions, methods, properties, attributes,
and data.

The model is intended for composition. You can inspect and filter the tree,
then insert selected objects into a normal `Document`, `Chapter`, or `Section`.

```python
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")

for obj in api.select(kind="class"):
    print(obj.qualname, obj.summary)
```

Use `ApiPackage.select(...)` when you need a subset and `find(...)` when you
need one exact module or object. Rendering helpers live on the objects
themselves, so the parsed metadata stays useful outside a full API reference.
For common package-wide subsets, use `classes()`, `functions()`, `methods()`,
`properties()`, or `attributes()` before passing the objects into a table or
chapter.

```python
from oodocs import Chapter, Document
from oodocs.apidoc import collect_api

api = collect_api("oodocs", public_policy="__all__")
classes = api.select(kind="class", module_prefix="oodocs.components")

doc = Document(
    "Selected Component API",
    Chapter("Classes", *[obj.to_section(level=2, profile="manual") for obj in classes[:3]]),
)
```

`ApiObject` stores normalized docstring sections: summary, description,
parameters, returns, raises, examples, see-also entries, renderer notes, and
child members. Class and module `Attributes:` sections are connected to
attribute/data objects so API references can document fields and constants.
