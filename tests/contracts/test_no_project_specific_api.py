from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib

import pytest


pytestmark = pytest.mark.contracts

ROOTS = (
    Path("src/oodocs"),
    Path("docs"),
    Path("examples"),
    Path("tests"),
    Path("README.md"),
    Path("README-PYPI.md"),
)
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ALLOWLIST_PATH = Path("tests/contracts/project-specific-string-allowlist.toml")

# Keep the forbidden spellings out of this test's own source so the scanner
# exercises the same repository surface as the documented ripgrep command.
FORBIDDEN_PATTERNS = {
    "application-name": re.compile("EPlus" + "Simple", re.IGNORECASE),
    "engine-name": re.compile("Energy" + "Plus", re.IGNORECASE),
    "package-alias": re.compile("ep" + "simple", re.IGNORECASE),
    "industry-standard": re.compile("ASH" + "RAE", re.IGNORECASE),
    "laboratory-name": re.compile("Building Simulation " + "Lab", re.IGNORECASE),
    "artifact-abbreviation-m": re.compile(r"\bgr" + r"m\b", re.IGNORECASE),
    "artifact-abbreviation-r": re.compile(r"\bgr" + r"r\b", re.IGNORECASE),
}


@dataclass(frozen=True, slots=True)
class AllowEntry:
    path: str
    term: str
    reason: str


def _text_files() -> list[Path]:
    paths: list[Path] = []
    for root in ROOTS:
        if root.is_file():
            paths.append(root)
            continue
        paths.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in TEXT_SUFFIXES
            and "__pycache__" not in path.parts
        )
    return sorted(set(paths))


def _allowlist() -> tuple[AllowEntry, ...]:
    payload = tomllib.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    entries: list[AllowEntry] = []
    for raw in payload.get("entry", payload.get("entries", [])):
        entry = AllowEntry(
            path=str(raw.get("path", "")).strip(),
            term=str(raw.get("term", "")).strip().casefold(),
            reason=str(raw.get("reason", "")).strip(),
        )
        assert entry.path and entry.term and entry.reason, (
            "Every project-string allowlist entry needs path, term, and reason"
        )
        entries.append(entry)
    return tuple(entries)


def _is_allowed(path: Path, matched_text: str, entries: tuple[AllowEntry, ...]) -> bool:
    normalized_path = path.as_posix()
    normalized_term = matched_text.casefold()
    return any(
        entry.path == normalized_path and entry.term == normalized_term
        for entry in entries
    )


def test_source_and_documentation_have_no_project_specific_strings() -> None:
    allowlist = _allowlist()
    findings: list[str] = []

    for path in _text_files():
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            for label, pattern in FORBIDDEN_PATTERNS.items():
                for match in pattern.finditer(line):
                    if not _is_allowed(path, match.group(0), allowlist):
                        findings.append(
                            f"{path.as_posix()}:{line_number}: "
                            f"{label}={match.group(0)!r}: {line.strip()}"
                        )

    assert not findings, "Project-specific strings found:\n" + "\n".join(findings)


def test_allowlist_entries_are_used_and_never_cover_api_defaults() -> None:
    entries = _allowlist()
    forbidden_context = re.compile(
        r"(?:class|def)\s|preset|default|footer|title",
        re.IGNORECASE,
    )

    for entry in entries:
        path = Path(entry.path)
        assert path.exists(), f"Allowlist path does not exist: {entry.path}"
        matching_lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if entry.term in line.casefold()
        ]
        assert matching_lines, f"Unused allowlist entry: {entry}"
        assert not any(forbidden_context.search(line) for line in matching_lines), (
            f"Allowlist entry covers an API/default context: {entry}"
        )
