"""Configuration-driven evidence report command line interface."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
import tomllib

from oodocs.evidence.model import EvidenceItem, EvidenceReport
from oodocs.settings import DocumentMetadata, TitleMatter


def main(argv: Sequence[str] | None = None) -> int:
    """Build an evidence report from a config file or explicit items."""

    parser = _parser()
    args = parser.parse_args(argv)
    config = _load_config(args.config) if args.config is not None else {}
    report, output_dir, stem, formats = _report_from_arguments(args, config, parser)
    bundle = report.save_bundle(
        output_dir,
        stem=stem,
        formats=formats,
        missing_input_policy=args.missing_input_policy,
    )
    print(f"Wrote evidence bundle: {bundle.output_dir}")
    for output_format, path in bundle.outputs:
        print(f"Wrote {output_format}: {path}")
    print(f"Wrote checksums: {bundle.checksum_file}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m oodocs.evidence")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", type=Path, help="TOML evidence configuration.")
    source.add_argument(
        "--item",
        action="append",
        help="Evidence item as path[:kind[:title]]. Repeat as needed.",
    )
    parser.add_argument("--title", help="Document title.")
    parser.add_argument("--output-dir", type=Path, help="Output directory.")
    parser.add_argument("--stem", help="Output filename stem.")
    parser.add_argument(
        "--format",
        action="append",
        choices=("docx", "pdf", "html"),
        dest="formats",
        help="Output format. Repeat for multiple formats.",
    )
    parser.add_argument(
        "--missing-input-policy",
        choices=("error", "warn"),
        default="error",
    )
    return parser


def _load_config(path: Path) -> Mapping[str, object]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {**data, "_config_dir": path.resolve().parent}


def _report_from_arguments(
    args: argparse.Namespace,
    config: Mapping[str, object],
    parser: argparse.ArgumentParser,
) -> tuple[EvidenceReport, Path, str, tuple[str, ...]]:
    title = args.title or _optional_text(config.get("title"))
    output_dir = args.output_dir or _optional_path(config.get("output_dir"))
    stem = args.stem or _optional_text(config.get("stem"))
    if not title:
        parser.error("--title is required unless config provides title")
    if output_dir is None:
        parser.error("--output-dir is required unless config provides output_dir")
    if not stem:
        parser.error("--stem is required unless config provides stem")

    if args.item:
        items = tuple(_parse_item_spec(value) for value in args.item)
    else:
        items = _config_items(config, parser)
    raw_formats = args.formats or config.get("formats") or config.get("format") or ("html",)
    if isinstance(raw_formats, str):
        formats = (raw_formats,)
    elif isinstance(raw_formats, Sequence):
        formats = tuple(str(value) for value in raw_formats)
    else:
        parser.error("formats must be a string or sequence")

    author = _optional_text(config.get("author"))
    subtitle = _optional_text(config.get("subtitle"))
    report = EvidenceReport(
        title,
        items,
        metadata=DocumentMetadata(author=author) if author else None,
        title_matter=TitleMatter(subtitle=subtitle) if subtitle else None,
    )
    return report, Path(output_dir), stem, formats


def _config_items(
    config: Mapping[str, object],
    parser: argparse.ArgumentParser,
) -> tuple[EvidenceItem, ...]:
    raw_items = config.get("items", config.get("item", ()))
    if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
        parser.error("config items must be an array of tables")
    base_dir = config.get("_config_dir")
    items: list[EvidenceItem] = []
    for raw in raw_items:
        if not isinstance(raw, Mapping) or "path" not in raw:
            parser.error("each config item needs a path")
        path = Path(str(raw["path"]))
        if not path.is_absolute() and isinstance(base_dir, Path):
            path = base_dir / path
        items.append(
            EvidenceItem(
                path,
                title=_optional_text(raw.get("title")),
                kind=str(raw.get("kind", "auto")),  # type: ignore[arg-type]
                required=bool(raw.get("required", True)),
                description=_optional_text(raw.get("description")),
            )
        )
    if not items:
        parser.error("config must provide at least one item")
    return tuple(items)


def _parse_item_spec(value: str) -> EvidenceItem:
    prefix = ""
    remainder = value
    if len(value) >= 3 and value[1] == ":" and value[2] in {"/", "\\"}:
        prefix, remainder = value[:2], value[2:]
    parts = remainder.split(":", 2)
    path = Path(prefix + parts[0])
    kind = parts[1] if len(parts) > 1 and parts[1] else "auto"
    title = parts[2] if len(parts) > 2 and parts[2] else None
    return EvidenceItem(path, title=title, kind=kind)  # type: ignore[arg-type]


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_path(value: object) -> Path | None:
    return None if value is None else Path(str(value))


__all__ = ["main"]
