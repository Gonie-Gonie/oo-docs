from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from oodocs.integrations.argparse import collect_argparse_cli


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release-tool",
        description="Prepare and inspect releases.",
    )
    parser.add_argument("manifest", help="Manifest to process.")
    parser.add_argument(
        "--channel",
        choices=("preview", "stable"),
        default="preview",
        help="Release channel.",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    inspect = commands.add_parser("inspect", help="Inspect release metadata.")
    inspect.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser


def test_collects_arguments_options_and_subcommands() -> None:
    application = collect_argparse_cli(_parser())

    assert application.name == "release-tool"
    assert application.root_command.name == "release-tool"
    assert application.description == "Prepare and inspect releases."
    assert application.root_command.usage == (
        "usage: release-tool [-h] [--channel {preview,stable}] manifest COMMAND ..."
    )
    assert [entry.names for entry in application.root_command.arguments] == [
        ("manifest",),
    ]
    assert [entry.names for entry in application.root_command.named_options] == [
        ("--channel",),
    ]
    channel = application.root_command.named_options[0]
    assert channel.default == "preview"
    assert channel.choices == ("preview", "stable")
    assert [command.name for command in application.root_command.subcommands] == [
        "inspect",
    ]
    assert application.root_command.subcommands[0].description == "Inspect release metadata."


def test_name_override_is_caller_owned() -> None:
    application = collect_argparse_cli(_parser(), name="release-tool.exe")

    assert application.name == "release-tool.exe"
    assert application.root_command.name == "release-tool.exe"


def test_collection_does_not_invoke_actions_types_or_handlers() -> None:
    calls: list[str] = []

    class ExplodingAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            calls.append("action")
            raise AssertionError("argument action was executed")

    def exploding_type(value: str) -> str:
        calls.append("type")
        raise AssertionError("argument type converter was executed")

    def exploding_handler() -> None:
        calls.append("handler")
        raise AssertionError("command handler was executed")

    parser = argparse.ArgumentParser(prog="safe-tool")
    parser.add_argument("--action", action=ExplodingAction)
    parser.add_argument("--typed", type=exploding_type)
    parser.set_defaults(handler=exploding_handler)

    application = collect_argparse_cli(parser)

    assert application.name == "safe-tool"
    assert calls == []


def test_argparse_private_access_is_isolated_to_integration() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    checked_paths = [
        repository_root / "src" / "oodocs" / "clidoc",
        repository_root / "examples" / "cli_manual_example",
    ]
    private_markers = ("._actions", "._choices_actions", "._HelpAction", "._SubParsersAction")

    findings: list[str] = []
    for root in checked_paths:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for marker in private_markers:
                if marker in source:
                    findings.append(f"{path.relative_to(repository_root)}: {marker}")

    assert findings == []


def test_rejects_non_argparse_input() -> None:
    with pytest.raises(TypeError, match="argparse.ArgumentParser"):
        collect_argparse_cli(object())  # type: ignore[arg-type]
