# Engineering Report Example

This example shows how to keep engineering-method details in a focused report
instead of folding them into the general user guide.

It uses `oodocs.engineering.Algorithm` for numbered pseudocode, ordinary
`Table` objects for requirements and verification evidence, and normal
sections for the surrounding method explanation.

Render the example:

```powershell
python examples/engineering_report_example/main.py --output-dir artifacts/engineering-report-example
```

Render only HTML while iterating:

```powershell
python examples/engineering_report_example/main.py --outputs html --quiet
```
