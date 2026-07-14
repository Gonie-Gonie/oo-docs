"""Data models for renderer-neutral command-line documentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal


if TYPE_CHECKING:
    from oodocs.components.blocks import Section
    from oodocs.components.media import Table


CliEntryKind = Literal["argument", "option"]


def _required_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


@dataclass(frozen=True, slots=True)
class CliOption:
    """A positional argument or named command-line option.

    An entry is positional when none of its names starts with ``-``. Named
    options retain every spelling supplied by the caller, such as
    ``("-o", "--output")``.
    """

    names: tuple[str, ...]
    value_name: str | None = None
    required: bool = False
    default: object | None = None
    choices: tuple[object, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        normalized_names = tuple(
            _required_text(name, field_name="CliOption name") for name in self.names
        )
        if not normalized_names:
            raise ValueError("CliOption.names must contain at least one name")
        object.__setattr__(self, "names", normalized_names)
        object.__setattr__(self, "choices", tuple(self.choices))
        if self.value_name is not None:
            if not isinstance(self.value_name, str):
                raise TypeError("CliOption.value_name must be a string or None")
            object.__setattr__(self, "value_name", self.value_name.strip() or None)
        if not isinstance(self.description, str):
            raise TypeError("CliOption.description must be a string")

    @property
    def kind(self) -> CliEntryKind:
        """Return whether this entry is positional or named."""

        return "option" if any(name.startswith("-") for name in self.names) else "argument"

    @property
    def is_positional(self) -> bool:
        """Return ``True`` for a positional command-line argument."""

        return self.kind == "argument"


@dataclass(slots=True)
class CliCommand:
    """A command with arguments, options, and optional subcommands."""

    name: str
    description: str = ""
    usage: str | None = None
    options: tuple[CliOption, ...] = ()
    subcommands: tuple["CliCommand", ...] = ()

    def __post_init__(self) -> None:
        self.name = _required_text(self.name, field_name="CliCommand.name")
        if not isinstance(self.description, str):
            raise TypeError("CliCommand.description must be a string")
        if self.usage is not None:
            if not isinstance(self.usage, str):
                raise TypeError("CliCommand.usage must be a string or None")
            self.usage = self.usage.strip() or None
        self.options = tuple(self.options)
        self.subcommands = tuple(self.subcommands)
        if not all(isinstance(option, CliOption) for option in self.options):
            raise TypeError("CliCommand.options must contain CliOption values")
        if not all(isinstance(command, CliCommand) for command in self.subcommands):
            raise TypeError("CliCommand.subcommands must contain CliCommand values")

    @property
    def arguments(self) -> tuple[CliOption, ...]:
        """Return positional arguments in their declared order."""

        return tuple(option for option in self.options if option.is_positional)

    @property
    def named_options(self) -> tuple[CliOption, ...]:
        """Return named options in their declared order."""

        return tuple(option for option in self.options if not option.is_positional)

    def to_option_table(
        self,
        *,
        positional: bool = False,
        caption: str | None = None,
    ) -> "Table":
        """Convert arguments or options to a neutral OODocs table.

        Args:
            positional: Select positional arguments instead of named options.
            caption: Optional caller-provided caption.
        """

        from oodocs.clidoc.render import command_option_table

        return command_option_table(self, positional=positional, caption=caption)

    def to_section(
        self,
        *,
        title: str | None = None,
        level: int = 2,
        toc: bool = True,
    ) -> "Section":
        """Convert this command to a reference section."""

        from oodocs.clidoc.render import command_to_section

        return command_to_section(self, title=title, level=level, toc=toc)


@dataclass(slots=True)
class CliApplication:
    """A documented CLI application whose executable name belongs to the caller."""

    name: str
    description: str = ""
    root_command: CliCommand = field(kw_only=True)

    def __post_init__(self) -> None:
        self.name = _required_text(self.name, field_name="CliApplication.name")
        if not isinstance(self.description, str):
            raise TypeError("CliApplication.description must be a string")
        if not isinstance(self.root_command, CliCommand):
            raise TypeError("CliApplication.root_command must be a CliCommand")

    def to_section(
        self,
        *additional_content: object,
        title: str | None = None,
        level: int = 2,
        toc: bool = True,
    ) -> "Section":
        """Convert the application to a reference section.

        Caller-owned blocks, such as exit-code or environment-variable tables,
        can be appended through ``additional_content`` without adding those
        policies to the CLI schema.
        """

        from oodocs.clidoc.render import application_to_section

        return application_to_section(
            self,
            *additional_content,
            title=title,
            level=level,
            toc=toc,
        )


__all__ = ["CliApplication", "CliCommand", "CliEntryKind", "CliOption"]
