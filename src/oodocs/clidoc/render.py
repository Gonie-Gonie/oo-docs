"""OODocs block conversion for command-line documentation models."""

from __future__ import annotations

from collections.abc import Sequence

from oodocs.clidoc.model import CliApplication, CliCommand, CliOption
from oodocs.components.blocks import CodeBlock, Paragraph, Section
from oodocs.components.media import Table


def _display_value(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _display_choices(choices: Sequence[object]) -> str:
    return ", ".join(str(choice) for choice in choices)


def _entry_row(entry: CliOption) -> list[str]:
    return [
        ", ".join(entry.names),
        entry.value_name or "",
        "Yes" if entry.required else "No",
        _display_value(entry.default),
        _display_choices(entry.choices),
        entry.description,
    ]


def command_option_table(
    command: CliCommand,
    *,
    positional: bool = False,
    caption: str | None = None,
) -> Table:
    """Build a table for one command's arguments or named options."""

    entries = command.arguments if positional else command.named_options
    label = "Argument" if positional else "Option"
    empty_description = "No positional arguments." if positional else "No named options."
    rows = [_entry_row(entry) for entry in entries]
    if not rows:
        rows = [["(none)", "", "", "", "", empty_description]]
    return Table(
        [label, "Value", "Required", "Default", "Choices", "Description"],
        rows,
        caption=caption or f"{label}s for {command.name}.",
        split=True,
    )


def _subcommands_table(command: CliCommand) -> Table:
    rows = [
        [subcommand.name, subcommand.description, subcommand.usage or ""]
        for subcommand in command.subcommands
    ]
    if not rows:
        rows = [["(none)", "No subcommands.", ""]]
    return Table(
        ["Command", "Description", "Syntax"],
        rows,
        caption=f"Subcommands for {command.name}.",
        split=True,
    )


def _reference_children(
    command: CliCommand,
    *,
    description: str | None = None,
    level: int,
) -> list[Section]:
    nested_level = level + 1
    resolved_description = command.description if description is None else description
    syntax = command.usage or command.name
    return [
        Section(
            "Syntax",
            CodeBlock(syntax, language="text"),
            level=nested_level,
            numbered=False,
            toc=False,
        ),
        Section(
            "Description",
            Paragraph(resolved_description or "No description provided."),
            level=nested_level,
            numbered=False,
            toc=False,
        ),
        Section(
            "Arguments",
            command_option_table(command, positional=True),
            level=nested_level,
            numbered=False,
            toc=False,
        ),
        Section(
            "Options",
            command_option_table(command),
            level=nested_level,
            numbered=False,
            toc=False,
        ),
        Section(
            "Subcommands",
            _subcommands_table(command),
            *[
                command_to_section(
                    subcommand,
                    title=f"{subcommand.name} command",
                    level=nested_level + 1,
                    toc=False,
                )
                for subcommand in command.subcommands
            ],
            level=nested_level,
            numbered=False,
            toc=False,
        ),
    ]


def command_to_section(
    command: CliCommand,
    *,
    title: str | None = None,
    level: int = 2,
    toc: bool = True,
) -> Section:
    """Build a command reference in its stable semantic order."""

    return Section(
        title or command.name,
        *_reference_children(command, level=level),
        level=level,
        toc=toc,
    )


def application_to_section(
    application: CliApplication,
    *additional_content: object,
    title: str | None = None,
    level: int = 2,
    toc: bool = True,
) -> Section:
    """Build an application reference while preserving caller-owned policies."""

    return Section(
        title or application.name,
        *_reference_children(
            application.root_command,
            description=application.description or application.root_command.description,
            level=level,
        ),
        *additional_content,
        level=level,
        toc=toc,
    )


__all__ = ["application_to_section", "command_option_table", "command_to_section"]
