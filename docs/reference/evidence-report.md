# Evidence reports

`EvidenceReport` renders only inputs selected by the caller. It never invents
missing rows, creates “passed” results, chooses an application title, or assumes
repository filenames.

```python
from pathlib import Path

from oodocs import DocumentMetadata, TitleMatter
from oodocs.evidence import EvidenceItem, EvidenceReport

report = EvidenceReport(
    "Verification packet",
    (
        EvidenceItem(Path("results/measurements.csv"), title="Measurements"),
        EvidenceItem(Path("results/summary.json"), title="Summary"),
        EvidenceItem(Path("results/inputs.sha256"), kind="checksums"),
    ),
    metadata=DocumentMetadata(author="Example Laboratory"),
    title_matter=TitleMatter(subtitle="Independent inputs"),
)

bundle = report.save_bundle(
    "dist/verification",
    stem="verification-packet",
    formats=("html", "pdf"),
)
```

`kind="auto"` selects CSV or JSON from the extension, recognizes common
checksum names, and treats every other input as text. Unknown text formats are
shown in a code block so their contents are preserved. Required missing files
raise `FileNotFoundError`; `missing_input_policy="warn"` adds a visible warning
without creating a file.

`EvidenceBundle` records the output directory, an `OutputBundle`, copied source
files, and a SHA-256 checksum file. Source files are copied under `sources/` and
must have unique basenames.

## Command line

Pass either a configuration file or one or more explicit items. Title, output
directory, stem, and formats remain application choices.

```powershell
python -m oodocs.evidence `
  --item results/measurements.csv:csv:Measurements `
  --item results/summary.json:json:Summary `
  --title "Verification packet" `
  --output-dir dist/verification `
  --stem verification-packet `
  --format html
```

A neutral TOML configuration uses the same values:

```toml
title = "Verification packet"
author = "Example Laboratory"
subtitle = "Independent inputs"
output_dir = "dist/verification"
stem = "verification-packet"
formats = ["html", "pdf"]

[[items]]
path = "results/measurements.csv"
kind = "csv"
title = "Measurements"

[[items]]
path = "results/summary.json"
kind = "json"
required = true
```

Config-relative item paths resolve from the configuration file directory.
Only `error` and `warn` are valid missing-input policies.
