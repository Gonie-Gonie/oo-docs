# CLI Manual Example

This example converts an `argparse.ArgumentParser` into a CLI reference manual.
It documents command overview, usage, options, subcommands, exit codes, and
copyable examples from a runnable sample parser.

Use it when a Python command-line tool should publish a DOCX/PDF/HTML manual
without maintaining separate option tables by hand.

Run the full bundle:

```powershell
python examples/cli_manual_example/main.py --output-dir artifacts/cli-manual-example
```

Render one format while iterating:

```powershell
python examples/cli_manual_example/main.py --outputs html --quiet
```

Programmatic entry points:

- `load_sample_parser()` imports `sample_cli.py` and returns its parser.
- `argparse_parser_to_section(parser)` converts the parser into OODocs blocks.
- `build_document(parser=None)` returns the complete `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs and returns an `OutputBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.
