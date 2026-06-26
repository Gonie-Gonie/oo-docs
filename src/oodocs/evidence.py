"""Command line entry point for release evidence bundles."""

from __future__ import annotations

import argparse
from typing import Sequence

from oodocs.adapters import ReleaseEvidence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the release-evidence command line entry point.

    Args:
        argv: Optional argument sequence. ``None`` reads arguments from
            ``sys.argv``.

    Returns:
        Process exit code.
    """

    parser = argparse.ArgumentParser(prog="python -m oodocs.evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build release evidence files.")
    build.add_argument("--out", default="artifacts/evidence", help="Evidence output directory.")
    build.add_argument("--pyproject", default="pyproject.toml", help="pyproject.toml path.")
    build.add_argument(
        "--workflow",
        default=".github/workflows/release.yml",
        help="GitHub Actions workflow YAML path.",
    )
    build.add_argument(
        "--fail-on-missing-input",
        dest="fail_on_missing_input",
        action="store_true",
        help="Fail if optional evidence inputs are missing.",
    )
    build.set_defaults(func=_run_build)
    args = parser.parse_args(argv)
    return args.func(args)


def _run_build(args: argparse.Namespace) -> int:
    bundle = ReleaseEvidence.from_directory(
        args.out,
        pyproject=args.pyproject,
        workflow=args.workflow,
    ).save_bundle(
        fail_on_missing_input=args.fail_on_missing_input,
    )
    print(f"Wrote evidence bundle: {bundle.output_dir}")
    for output_format, path in bundle.outputs.items():
        print(f"Wrote {output_format}: {path}")
    print(f"Wrote checksums: {bundle.checksum_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
