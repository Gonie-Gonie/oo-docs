"""Collect neutral CLI documentation from a standard-library argparse parser.

All access to argparse's private parser structures is isolated in this module.
The collector inspects an already-created parser; it does not import an
application module, parse arguments, invoke actions, or call command handlers.
"""

from __future__ import annotations

import argparse as argparse_module

from oodocs.clidoc import CliApplication, CliCommand, CliOption


def _choice_descriptions(action: argparse_module._SubParsersAction) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for choice_action in action._choices_actions:
        name = str(choice_action.dest)
        help_text = choice_action.help
        descriptions[name] = "" if help_text is argparse_module.SUPPRESS else str(help_text or "")
    return descriptions


def _subcommands(parser: argparse_module.ArgumentParser) -> tuple[CliCommand, ...]:
    commands: list[CliCommand] = []
    seen_parsers: set[int] = set()
    for action in parser._actions:
        if not isinstance(action, argparse_module._SubParsersAction):
            continue
        descriptions = _choice_descriptions(action)
        for name, subparser in action.choices.items():
            parser_identity = id(subparser)
            if parser_identity in seen_parsers:
                continue
            seen_parsers.add(parser_identity)
            command = _collect_command(subparser, name=name)
            if not command.description:
                command.description = descriptions.get(name, "")
            commands.append(command)
    return tuple(commands)


def _value_name(action: argparse_module.Action) -> str | None:
    if action.nargs == 0:
        return None
    metavar = action.metavar
    if isinstance(metavar, tuple):
        return " ".join(str(value) for value in metavar)
    if metavar is not None:
        return str(metavar)
    return str(action.dest).upper()


def _option(action: argparse_module.Action) -> CliOption:
    names = tuple(action.option_strings) or (str(action.dest),)
    default = None if action.default is argparse_module.SUPPRESS else action.default
    choices = tuple(action.choices) if action.choices is not None else ()
    help_text = "" if action.help is None else str(action.help)
    return CliOption(
        names=names,
        value_name=_value_name(action),
        required=bool(action.required),
        default=default,
        choices=choices,
        description=help_text,
    )


def _options(parser: argparse_module.ArgumentParser) -> tuple[CliOption, ...]:
    options: list[CliOption] = []
    for action in parser._actions:
        if isinstance(action, (argparse_module._HelpAction, argparse_module._SubParsersAction)):
            continue
        if action.help is argparse_module.SUPPRESS:
            continue
        options.append(_option(action))
    return tuple(options)


def _collect_command(
    parser: argparse_module.ArgumentParser,
    *,
    name: str,
) -> CliCommand:
    return CliCommand(
        name=name,
        description=parser.description or "",
        usage=parser.format_usage().strip(),
        options=_options(parser),
        subcommands=_subcommands(parser),
    )


def collect_argparse_cli(
    parser: argparse_module.ArgumentParser,
    *,
    name: str | None = None,
) -> CliApplication:
    """Collect CLI documentation without executing the documented command.

    Args:
        parser: An already-created standard-library argument parser.
        name: Optional caller-owned application/executable name. The parser's
            ``prog`` value is used when omitted.

    Returns:
        A renderer-neutral CLI application model.

    Notes:
        Construct the parser in side-effect-free application code. Importing
        the module that defines a parser executes that module's top-level code;
        this collector deliberately performs no such import.
    """

    if not isinstance(parser, argparse_module.ArgumentParser):
        raise TypeError("parser must be an argparse.ArgumentParser")
    application_name = (name if name is not None else parser.prog).strip()
    if not application_name:
        raise ValueError("name or parser.prog must not be empty")
    root_command = _collect_command(parser, name=application_name)
    return CliApplication(
        name=application_name,
        description=parser.description or "",
        root_command=root_command,
    )


__all__ = ["collect_argparse_cli"]
