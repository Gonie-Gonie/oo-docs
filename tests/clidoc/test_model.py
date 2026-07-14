from __future__ import annotations

import pytest

from oodocs import Paragraph, Table
from oodocs.clidoc import CliApplication, CliCommand, CliOption


def _row_text(table: Table) -> list[list[str]]:
    return [
        [cell.content.plain_text() for cell in row]
        for row in table.rows
    ]


def test_command_renders_in_stable_reference_order() -> None:
    command = CliCommand(
        name="archive-tool",
        description="Create an archive.",
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
                choices=("zip", "tar"),
                description="Destination path.",
            ),
        ),
        subcommands=(
            CliCommand(name="inspect", description="Inspect an archive."),
        ),
    )

    section = command.to_section(title="Command Reference")

    assert [child.plain_title() for child in section.children] == [
        "Syntax",
        "Description",
        "Arguments",
        "Options",
        "Subcommands",
    ]
    assert command.arguments == (command.options[0],)
    assert command.named_options == (command.options[1],)


def test_argument_and_option_tables_keep_distinct_semantics() -> None:
    command = CliCommand(
        name="archive-tool",
        options=(
            CliOption(names=("SOURCE",), required=True, description="Input directory."),
            CliOption(names=("--quiet",), default=False, description="Suppress output."),
        ),
    )

    argument_rows = _row_text(command.to_option_table(positional=True))
    option_rows = _row_text(command.to_option_table())

    assert argument_rows == [
        ["SOURCE", "", "Yes", "", "", "Input directory."],
    ]
    assert option_rows == [
        ["--quiet", "", "No", "False", "", "Suppress output."],
    ]


def test_empty_categories_remain_explicit() -> None:
    command = CliCommand(name="status")

    argument_rows = _row_text(command.to_option_table(positional=True))
    option_rows = _row_text(command.to_option_table())

    assert argument_rows[0][0] == "(none)"
    assert argument_rows[0][-1] == "No positional arguments."
    assert option_rows[0][0] == "(none)"
    assert option_rows[0][-1] == "No named options."


def test_application_uses_caller_name_and_accepts_policy_tables() -> None:
    root = CliCommand(name="tool.cmd", usage="tool.cmd --help")
    exit_codes = Table(
        ["Exit code", "Meaning"],
        [["0", "Success"]],
        caption="Caller-owned exit codes.",
    )
    environment = Table(
        ["Variable", "Meaning"],
        [["TOOL_HOME", "Configuration root"]],
        caption="Caller-owned environment variables.",
    )
    application = CliApplication(
        name="tool.cmd",
        description="Caller-selected executable.",
        root_command=root,
    )

    section = application.to_section(exit_codes, environment)

    assert section.plain_title() == "tool.cmd"
    assert section.children[-2:] == [exit_codes, environment]
    assert section.children[1].children[0].plain_text() == "Caller-selected executable."


@pytest.mark.parametrize(
    ("factory", "error"),
    [
        (lambda: CliOption(names=()), ValueError),
        (lambda: CliCommand(name="  "), ValueError),
        (lambda: CliCommand(name="tool", options=(object(),)), TypeError),
    ],
)
def test_models_reject_invalid_structure(factory, error: type[Exception]) -> None:
    with pytest.raises(error):
        factory()
