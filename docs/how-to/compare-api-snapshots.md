# Compare API Snapshots

Snapshots make API changes reviewable between releases. Write a baseline JSON
file, collect a new snapshot, then render a diff document.

```powershell
python -m oodocs apidoc snapshot oodocs --out artifacts/api-base.json
python -m oodocs apidoc snapshot oodocs --out artifacts/api-head.json
python -m oodocs apidoc diff --base artifacts/api-base.json --head artifacts/api-head.json --out artifacts/api-diff --to docx,pdf,html
```

Snapshot only a subset when a package area has its own compatibility promise:

```powershell
python -m oodocs apidoc snapshot . --kind function --module-prefix mypkg.adapters --out artifacts/adapter-api.json
```

Python usage gives direct access to the diff object:

```python
from oodocs.apidoc import ApiSnapshot, diff_api

base = ApiSnapshot.read_json("artifacts/api-base.json")
head = ApiSnapshot.read_json("artifacts/api-head.json")
diff = diff_api(base, head)

document = diff.to_document()
document.save_all("artifacts/api-diff", stem="api-diff")
```

When diffing and rendering happen in separate jobs, write and read the diff
sidecar:

```python
from oodocs.apidoc import ApiDiffResult

diff.write_json("artifacts/api-diff/api-diff.json")
readback = ApiDiffResult.read_json("artifacts/api-diff/api-diff.json")
readback.to_document().save_all("artifacts/api-diff", stem="api-diff")
```

The diff tracks added and removed objects, changed signatures, changed default
values, changed parameter annotations, changed return annotations, changed
docstrings, deprecated objects, and coverage deltas. Coverage deltas are
computed from either live `ApiPackage` objects or persisted `ApiSnapshot`
sidecars, so CI can compare release artifacts without importing the target
package again.
