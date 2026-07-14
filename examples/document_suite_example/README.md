# Document suite example

This example builds two small HTML documents from one explicit
`DocumentSuiteContext`. The documents share caller-owned variables, an asset
resolver, a citation library, and an output policy without introducing a
template or macro language.

```powershell
python examples/document_suite_example/main.py
```

The generated manifest records the suite name, serializable variables, and the
outputs produced for each document.
