# CLI Documentation

`oodocs.clidoc` represents a command-line interface independently of the
library that created it. A command reference always renders in this order:

1. Syntax
2. Description
3. Arguments
4. Options
5. Subcommands

The order is stable even when a category is empty, which makes references
predictable across DOCX, PDF, and HTML output.

## Construct a model directly

```python
from oodocs.clidoc import CliApplication, CliCommand, CliOption

command = CliCommand(
    name="archive-tool",
    description="Create a portable archive.",
    usage="archive-tool SOURCE [--output PATH]",
    options=(
        CliOption(
            names=("SOURCE",),
            value_name="SOURCE",
            required=True,
            description="Directory to archive.",
        ),
        CliOption(
            names=("-o", "--output"),
            value_name="PATH",
            default="archive.zip",
            description="Destination archive path.",
        ),
    ),
)
application = CliApplication(
    name="archive-tool",
    description="Create a portable archive.",
    root_command=command,
)
reference = application.to_section()
```

Names without an option prefix represent positional arguments; option names
such as `-o` and `--output` represent named options. The application and root
command names are caller-owned, so executable names and platform-specific file
extensions are never hardcoded by the model.

Exit codes and environment variables are application policies rather than
parser structure. Represent them as ordinary `Table` values (or as records in
your own domain model) and place them beside the generated CLI section. They
can also be passed as additional blocks to `CliApplication.to_section()`.

## Collect from argparse

```python
from oodocs.integrations.argparse import collect_argparse_cli

parser = build_parser()
application = collect_argparse_cli(parser)
reference = application.to_section(title="Command Reference")
```

The integration is the only OODocs module that reads argparse's private parser
structures. It accepts an already-created parser and only inspects it: it does
not call `parse_args()`, invoke actions, run command handlers, or import the
application module.

Importing Python code still executes that module's top-level statements. Keep
parser construction in a side-effect-free `build_parser()` function and put
command execution behind an `if __name__ == "__main__"` guard. Treat an
untrusted CLI module like any other untrusted Python program; do not import it
into the documentation process. If isolation is required, construct and
inspect the parser in a separate trusted process and transfer neutral records
back to the documentation build.

There are no placeholder Click or Typer APIs. Their metadata should be mapped
to `CliApplication`, `CliCommand`, and `CliOption` only when a real integration
can preserve the same semantics.
