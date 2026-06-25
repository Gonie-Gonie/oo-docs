# Compare API Snapshots

Snapshots make API changes reviewable between releases. Write a baseline JSON
file, collect a new snapshot, then render a diff document.

```powershell
python -m oodocs apidoc snapshot oodocs --out artifacts/api-base.json
python -m oodocs apidoc snapshot oodocs --out artifacts/api-head.json
python -m oodocs apidoc diff --base artifacts/api-base.json --head artifacts/api-head.json --out artifacts/api-diff --to docx,pdf,html
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

The diff tracks added and removed objects, changed signatures, changed default
values, changed docstrings, deprecated objects, and coverage deltas.

