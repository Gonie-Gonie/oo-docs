# CLI Manual Example

This example collects an `argparse.ArgumentParser` into `CliApplication`, then
renders the neutral model as a CLI reference manual. It documents syntax,
description, positional arguments, named options, subcommands, exit codes,
environment-variable policy, and copyable examples.

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

- `load_sample_parser()` imports the side-effect-free parser builder in
  `sample_cli.py` and returns its parser.
- `collect_argparse_cli(parser)` converts a parser to the neutral CLI model.
- `CliApplication.to_section()` converts that model into OODocs blocks.
- `build_document(parser=None)` returns the complete `Document`.
- `build(output_dir=..., output_formats=..., verbose=False)` writes selected
  outputs and returns an `OutputBundle`.
- `main(argv=None)` exposes the same workflow as a command-line script.

`collect_argparse_cli()` never imports an application module, calls
`parse_args()`, invokes an argparse action, or executes a command handler. The
caller is responsible for creating the parser. Because Python executes
top-level statements while importing a module, keep parser construction in a
function and command execution under an `if __name__ == "__main__"` guard, as
`sample_cli.py` does. Do not import an untrusted command module in the current
process merely to document it.
