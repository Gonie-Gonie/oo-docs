# Compare API Snapshots

Snapshots make API changes reviewable between releases. Write a baseline JSON
file, collect a new snapshot, then render a diff document.

```powershell
python -m oodocs apidoc snapshot oodocs --save-json artifacts/api-base.json
python -m oodocs apidoc snapshot oodocs --save-json artifacts/api-head.json
python -m oodocs apidoc diff artifacts/api-base.json artifacts/api-head.json --save-json artifacts/api-diff.json
```

Snapshot only a subset when a package area has its own compatibility promise:

```powershell
python -m oodocs apidoc snapshot . --kind function --module-prefix mypkg.adapters --save-json artifacts/adapter-api.json
```

Python usage gives direct access to the diff object:

```python
from oodocs.apidoc import ApiHelpBookConfig, ApiSnapshot, diff_api

build = ApiHelpBookConfig.from_pyproject(".")
build.save_snapshot(".", "artifacts/api-head.json")

base = ApiSnapshot.load_json("artifacts/api-base.json")
head = ApiSnapshot.load_json("artifacts/api-head.json")
diff = diff_api(base, head)

document = diff.to_document()
document.save_all("artifacts/api-diff", stem="api-diff")
```

When diffing and rendering happen in separate jobs, write and read the diff
sidecar:

```python
from oodocs.apidoc import ApiDiffResult

diff.save_json("artifacts/api-diff/api-diff.json")
readback = ApiDiffResult.load_json("artifacts/api-diff/api-diff.json")
readback.to_document().save_all("artifacts/api-diff", stem="api-diff")
```

The diff tracks added and removed objects, changed signatures, changed default
values, changed parameter annotations, changed return annotations, changed
docstrings, deprecated objects, and coverage deltas. Coverage deltas are
computed from either live `ApiPackage` objects or persisted `ApiSnapshot`
sidecars, so CI can compare release artifacts without importing the target
package again. Rendered diff documents include a `Coverage Delta` chapter with
base/head public-object counts, documented-object counts, coverage ratios, and
the coverage movement between snapshots.
