from __future__ import annotations

from pathlib import Path
import subprocess

import pytest


MIN_IMMUTABLE_RELEASE_NOTE_VERSION = (1, 1, 0)


def _git(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
    )


def _git_ok(args: list[str]) -> bool:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
    ).returncode == 0


def _normalized_text(data: bytes | str) -> str:
    if isinstance(data, bytes):
        text = data.decode("utf-8")
    else:
        text = data
    return text.replace("\r\n", "\n")


def _version_tuple(tag: str) -> tuple[int, int, int] | None:
    parts = tag.removeprefix("v").split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        return None


def test_release_notes_for_existing_tags_from_v1_1_0_are_immutable() -> None:
    tagged_notes: list[str] = []

    for path in sorted(Path("release-notes").glob("v*.md")):
        tag = path.stem
        version = _version_tuple(tag)
        if version is None or version < MIN_IMMUTABLE_RELEASE_NOTE_VERSION:
            continue

        release_note_path = path.as_posix()
        if not _git_ok(["rev-parse", "--verify", "--quiet", tag]):
            continue

        if not _git_ok(["cat-file", "-e", f"{tag}:{release_note_path}"]):
            pytest.fail(
                f"{release_note_path} was added after tag {tag}; "
                "published release notes must stay immutable."
            )

        tagged_text = _normalized_text(_git(["show", f"{tag}:{release_note_path}"]).stdout)
        current_text = _normalized_text(path.read_text(encoding="utf-8"))
        assert current_text == tagged_text, (
            f"{release_note_path} differs from {tag}:{release_note_path}. "
            "Published release notes must stay immutable; put later changes in "
            "a future release note instead."
        )
        tagged_notes.append(release_note_path)

    if not tagged_notes:
        pytest.skip("No local release-note tags are available to compare.")
