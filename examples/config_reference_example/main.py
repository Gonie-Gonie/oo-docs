"""Build a configuration reference from TOML and JSON schema inputs."""

import argparse
from dataclasses import replace
from pathlib import Path
import tomllib
from typing import Sequence

from oodocs import (
    Chapter,
    Document,
    DocumentMetadata,
    DocumentSettings,
    OutputBundle,
    Paragraph,
    Section,
    Table,
    TableOfContents,
    TitleMatter,
    inline_code,
)
from oodocs.integrations.json_schema import collect_json_schema
from oodocs.schema import FieldSpec, SchemaPresentation, SchemaSpec


EXAMPLE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path("artifacts") / "config-reference-example"
OUTPUT_STEM = "config-reference"
SAMPLE_CONFIG_PATH = EXAMPLE_DIR / "sample_config.toml"
SAMPLE_SCHEMA_PATH = EXAMPLE_DIR / "sample_schema.json"


def repo_relative(path: Path) -> str:
    """Return a repository-relative source path when possible."""

    try:
        return path.resolve().relative_to(EXAMPLE_DIR.parents[1]).as_posix()
    except ValueError:
        return path.as_posix()


def load_config_reference(
    config_path: str | Path = SAMPLE_CONFIG_PATH,
    schema_path: str | Path = SAMPLE_SCHEMA_PATH,
) -> SchemaSpec:
    """Collect the JSON Schema and add caller-owned current-value metadata."""

    config_file = Path(config_path)
    schema_file = Path(schema_path)
    config_data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    catalog = collect_json_schema(schema_file, key="configuration")
    schema = catalog.schemas[0]
    fields = tuple(
        replace(
            field,
            metadata={
                **field.metadata,
                "current_value": _lookup_config_value(config_data, field.name),
            },
        )
        for field in schema.fields
    )
    return replace(
        schema,
        fields=fields,
        metadata={
            **schema.metadata,
            "config_path": config_file,
            "schema_path": schema_file,
            "diagnostics": catalog.diagnostics,
        },
    )


def _lookup_config_value(config: dict[str, object], dotted_name: str) -> object:
    current: object = config
    for part in dotted_name.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _field_paragraph(field: FieldSpec) -> Paragraph:
    requirement = (field.requirement or "unspecified").replace("-", " ")
    return Paragraph(
        inline_code(field.name),
        f" is {requirement}. ",
        field.description,
    )


def _reference_section(reference: SchemaSpec) -> Section:
    required_fields = [
        field
        for field in reference.fields
        if field.requirement in {"required", "conditional-required"}
    ]
    optional_fields = [field for field in reference.fields if field not in required_fields]
    env_fields = [field for field in reference.fields if field.metadata.get("env")]
    config_path = Path(reference.metadata["config_path"])
    schema_path = Path(reference.metadata["schema_path"])
    presentation = SchemaPresentation(
        metadata_columns={
            "current_value": "Current value",
            "env": "Env var",
        }
    )
    return Section(
        "Configuration Reference",
        Paragraph(
            "Read from ",
            inline_code(repo_relative(config_path)),
            " and ",
            inline_code(repo_relative(schema_path)),
            ".",
        ),
        reference.to_table(
            presentation=presentation,
            caption="Configuration field reference.",
        ),
        Section(
            "Required fields",
            *[_field_paragraph(field) for field in required_fields],
            level=2,
        ),
        Section(
            "Optional fields",
            *[_field_paragraph(field) for field in optional_fields],
            level=2,
        ),
        Section(
            "Environment variables",
            Table(
                ["Environment variable", "Field", "Purpose"],
                [
                    [field.metadata.get("env", ""), field.name, field.description]
                    for field in env_fields
                ],
                caption="Environment variable overrides documented by the schema.",
            ),
            level=2,
        ),
        toc=True,
    )


def build_document(reference: SchemaSpec | None = None) -> Document:
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
                "This example turns a TOML config file and a JSON schema into "
                "a field reference document."
            ),
            _reference_section(reference),
        ),
        Chapter(
            "Defaults and Examples",
            examples_table,
        ),
        settings=DocumentSettings(
            metadata=DocumentMetadata(
                author="Example Documentation Team",
                description="Configuration reference generated from example config files",
            ),
            title_matter=TitleMatter(
                subtitle="TOML config and JSON schema as a field reference",
            ),
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
