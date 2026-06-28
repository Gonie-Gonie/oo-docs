"""Build a configuration reference from TOML and JSON schema inputs."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import Sequence

from oodocs import (
    Chapter,
    Document,
    DocumentSettings,
    OutputBundle,
    Paragraph,
    Section,
    Table,
    TableOfContents,
    inline_code,
)


EXAMPLE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path("artifacts") / "config-reference-example"
OUTPUT_STEM = "config-reference"
SAMPLE_CONFIG_PATH = EXAMPLE_DIR / "sample_config.toml"
SAMPLE_SCHEMA_PATH = EXAMPLE_DIR / "sample_schema.json"


@dataclass(frozen=True, slots=True)
class ConfigField:
    """One documented configuration field."""

    name: str
    type: str
    required: bool
    default: object
    description: str
    env_var: str | None = None
    current_value: object | None = None

    def to_paragraph(self) -> Paragraph:
        """Return this field as a compact paragraph."""

        required = "required" if self.required else "optional"
        return Paragraph(
            inline_code(self.name),
            f" is a {required} {self.type} field. ",
            self.description,
        )

    def as_summary_row(self) -> list[str]:
        """Return this field as a table row."""

        return [
            self.name,
            self.type,
            "yes" if self.required else "no",
            _format_value(self.default),
            _format_value(self.current_value),
            self.env_var or "",
            self.description,
        ]


@dataclass(frozen=True, slots=True)
class ConfigReference:
    """Loaded configuration reference fields."""

    title: str
    fields: tuple[ConfigField, ...]
    config_path: Path
    schema_path: Path

    def to_summary_table(self, *, caption: str = "Configuration field reference.") -> Table:
        """Return all fields as one summary table."""

        return Table(
            ["Field", "Type", "Required", "Default", "Current value", "Env var", "Description"],
            [field.as_summary_row() for field in self.fields],
            caption=caption,
            split=True,
        )

    def to_section(self) -> Section:
        """Return this configuration reference as an OODocs section."""

        required_fields = [field for field in self.fields if field.required]
        optional_fields = [field for field in self.fields if not field.required]
        env_fields = [field for field in self.fields if field.env_var]
        return Section(
            "Configuration Reference",
            Paragraph(
                "Read from ",
                inline_code(self.config_path.as_posix()),
                " and ",
                inline_code(self.schema_path.as_posix()),
                ".",
            ),
            self.to_summary_table(),
            Section(
                "Required fields",
                *[field.to_paragraph() for field in required_fields],
                level=2,
            ),
            Section(
                "Optional fields",
                *[field.to_paragraph() for field in optional_fields],
                level=2,
            ),
            Section(
                "Environment variables",
                Table(
                    ["Environment variable", "Field", "Purpose"],
                    [
                        [field.env_var or "", field.name, field.description]
                        for field in env_fields
                    ],
                    caption="Environment variable overrides documented by the schema.",
                ),
                level=2,
            ),
            toc=True,
        )


def load_config_reference(
    config_path: str | Path = SAMPLE_CONFIG_PATH,
    schema_path: str | Path = SAMPLE_SCHEMA_PATH,
) -> ConfigReference:
    """Load TOML config and JSON schema into reference fields."""

    config_file = Path(config_path)
    schema_file = Path(schema_path)
    config_data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    schema_data = json.loads(schema_file.read_text(encoding="utf-8"))
    fields = []
    for name, spec in schema_data["properties"].items():
        if not isinstance(spec, dict):
            continue
        fields.append(
            ConfigField(
                name=name,
                type=str(spec.get("type", "")),
                required=bool(spec.get("required", False)),
                default=spec.get("default"),
                description=str(spec.get("description", "")),
                env_var=str(spec["env"]) if "env" in spec else None,
                current_value=_lookup_config_value(config_data, name),
            )
        )
    return ConfigReference(
        title=str(schema_data.get("title", "Configuration reference")),
        fields=tuple(fields),
        config_path=config_file,
        schema_path=schema_file,
    )


def _lookup_config_value(config: dict[str, object], dotted_name: str) -> object:
    current: object = config
    for part in dotted_name.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def build_document(reference: ConfigReference | None = None) -> Document:
    """Build the configuration reference example document."""

    reference = reference or load_config_reference()
    examples_table = Table(
        ["Task", "Configuration"],
        [
            ["HTML-only draft", "build.formats = ['html']"],
            ["Strict release gate", "build.strict = true or OODOCS_STRICT=1"],
            ["Custom cache", "environment.cache_dir = '.cache/oodocs'"],
        ],
        caption="Configuration examples derived from the schema.",
    )
    return Document(
        "Configuration Reference Example",
        TableOfContents(max_level=2),
        Chapter(
            "Configuration Overview",
            Paragraph(
                "This example turns a TOML config file and a JSON schema into a field reference document."
            ),
            reference.to_section(),
        ),
        Chapter(
            "Defaults and Examples",
            examples_table,
        ),
        settings=DocumentSettings(
            metadata_author="OODocs Contributors",
            subtitle="TOML config and JSON schema as a field reference",
            summary="Configuration reference generated from example config files",
        ),
    )


def build(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    output_formats: Sequence[str] | None = None,
    verbose: bool = False,
) -> OutputBundle:
    """Render the configuration reference example."""

    output_path = Path(output_dir)
    document = build_document()
    document.validate(raise_on_error=True)
    return document.save_all(
        output_path,
        stem=OUTPUT_STEM,
        formats=tuple(output_formats or ("docx", "pdf", "html")),
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Render the example from the command line."""

    parser = argparse.ArgumentParser(
        description="Render the OODocs configuration reference example.",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        type=Path,
        help="Directory where rendered files are written.",
    )
    parser.add_argument(
        "--outputs",
        action="append",
        choices=("docx", "pdf", "html"),
        dest="output_formats",
        help="Output format to render. Repeat for multiple formats.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress and output-path messages.",
    )
    args = parser.parse_args(argv)

    outputs = build(
        args.output_dir,
        output_formats=args.output_formats,
        verbose=not args.quiet,
    )
    if not args.quiet:
        for output_format, path in outputs:
            print(f"Wrote {output_format}: {path}")


if __name__ == "__main__":
    main()
