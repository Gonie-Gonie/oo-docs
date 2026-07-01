"""Example extraction and validation helpers for API docstrings."""

from __future__ import annotations

import doctest
import re
import textwrap
from typing import Mapping

from oodocs.apidoc.model import ApiDocIssue, ApiExample, ApiObject


_FENCED_BLOCK_RE = re.compile(
    r"^[ \t]*```(?P<language>[A-Za-z0-9_+-]*)[ \t]*\n"
    r"(?P<code>.*?)(?:\n[ \t]*```[ \t]*(?=\n|\Z)|\Z)",
    flags=re.DOTALL | re.MULTILINE,
)


def extract_code_blocks_from_docstring(text: str | None) -> list[ApiExample]:
    """Extract fenced and doctest-style examples from docstring text.

    Args:
        text: Raw docstring text.

    Returns:
        Parsed example objects. Fenced code blocks preserve their language
        labels. Doctest snippets outside fenced blocks use
        ``language="pycon"``.

    Examples:
        Extract fenced Python code for insertion into an API section:

        ```python
        from oodocs.apidoc.examples import extract_code_blocks_from_docstring

        examples = extract_code_blocks_from_docstring("```python\\nprint('ok')\\n```")
        assert examples[0].language == "python"
        ```

        Fenced console sessions stay as one fenced example instead of being
        counted again as a separate doctest block:

        ```python
        examples = extract_code_blocks_from_docstring("```pycon\\n>>> run()\\n```")
        assert [example.language for example in examples] == ["pycon"]
        ```
    """

    source = text or ""
    examples = [
        ApiExample(
            textwrap.dedent(match.group("code").strip("\n")).strip("\n"),
            language=match.group("language") or "text",
            caption=_caption_before_offset(source, match.start()),
        )
        for match in _FENCED_BLOCK_RE.finditer(source)
    ]
    for doctest_code, caption in _extract_doctest_blocks(_strip_fenced_blocks(source)):
        examples.append(ApiExample(doctest_code, language="pycon", caption=caption))
    return examples


def check_example_syntax(example: ApiExample) -> bool:
    """Check whether an example contains valid Python syntax.

    Args:
        example: Example to check.

    Returns:
        ``True`` when syntax is valid or the example is not Python code,
        otherwise ``False``.

    Examples:
        Mark parsed examples before writing coverage evidence:

        ```python
        from oodocs.apidoc import ApiExample
        from oodocs.apidoc.examples import check_example_syntax

        example = ApiExample("print('ok')", language="python")
        assert check_example_syntax(example)
        assert example.syntax_ok is True
        ```
    """

    if example.language.lower() not in {"python", "py", "pycon"}:
        example.syntax_ok = None
        return True
    source = _doctest_to_python(example.code) if example.language.lower() == "pycon" else example.code
    try:
        compile(source, example.source or "<apidoc-example>", "exec")
    except SyntaxError:
        example.syntax_ok = False
        return False
    example.syntax_ok = True
    return True


def check_doctest_examples(
    api_object: ApiObject,
    *,
    globs: Mapping[str, object] | None = None,
) -> list[ApiDocIssue]:
    """Validate doctest-style examples for one API object.

    Args:
        api_object: API object whose examples should be checked.
        globs: Optional namespace used to execute doctest examples. When
            omitted, examples are parsed for doctest validity without running
            user code.

    Returns:
        Issues for failing doctest examples.

    Notes:
        By default, this helper parses doctest syntax without executing it.
        Pass ``globs`` when a trusted caller wants to run examples against a
        prepared namespace.
        ``check_example_syntax`` performs compile-level checking for ``pycon``
        examples before coverage counters are computed.

    Examples:
        Check doctest snippets already attached to an ``ApiObject``:

        ```python
        from oodocs.apidoc import ApiExample, ApiObject
        from oodocs.apidoc.examples import check_doctest_examples

        obj = ApiObject(
            kind="function",
            name="echo",
            qualname="pkg.echo",
            module="pkg",
            examples=[ApiExample(">>> echo('ok')\\n'ok'", language="pycon")],
        )
        issues = check_doctest_examples(obj)
        assert not issues
        assert obj.examples[0].doctest_ok is True
        ```

        Execute doctest examples against a trusted namespace:

        ```python
        def echo(value):
            return value

        obj.examples[0].code = ">>> echo('ok')\\n'ok'"
        issues = check_doctest_examples(obj, globs={"echo": echo})
        assert not issues
        ```
    """

    issues: list[ApiDocIssue] = []
    parser = doctest.DocTestParser()
    for example in api_object.examples:
        if example.language.lower() != "pycon":
            continue
        try:
            if globs is None:
                parser.get_examples(example.code)
            else:
                test = parser.get_doctest(
                    example.code,
                    dict(globs),
                    api_object.qualname,
                    api_object.source_path or "<apidoc-doctest>",
                    api_object.line_number or 0,
                )
                result = doctest.DocTestRunner(
                    verbose=False,
                    optionflags=doctest.ELLIPSIS,
                ).run(test, out=lambda _: None)
                if result.failed:
                    raise ValueError(f"{result.failed} doctest example(s) failed")
        except ValueError as exc:
            example.doctest_ok = False
            issues.append(
                ApiDocIssue(
                    "warning",
                    "doctest-failed",
                    str(exc),
                    qualname=api_object.qualname,
                    module=api_object.module,
                    path=api_object.source_path,
                    line_number=api_object.line_number,
                )
            )
        else:
            example.doctest_ok = True
    return issues


def _extract_doctest_blocks(text: str) -> list[tuple[str, str | None]]:
    lines = text.splitlines()
    blocks: list[tuple[str, str | None]] = []
    current: list[str] = []
    current_start: int | None = None
    in_block = False
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(">>>") or stripped.startswith("..."):
            if not in_block:
                current_start = index
            in_block = True
            current.append(stripped)
        elif in_block and stripped:
            current.append(stripped)
        elif in_block:
            blocks.append(("\n".join(current), _caption_before_line(lines, current_start)))
            current = []
            current_start = None
            in_block = False
            continue
    if in_block and current:
        blocks.append(("\n".join(current), _caption_before_line(lines, current_start)))
    return blocks


_EXAMPLE_SECTION_CAPTIONS = {"example", "examples"}


def _caption_before_offset(text: str, offset: int) -> str | None:
    prefix = text[:offset]
    return _caption_before_line(prefix.splitlines(), len(prefix.splitlines()))


def _caption_before_line(lines: list[str], line_index: int | None) -> str | None:
    if line_index is None:
        return None
    for line in reversed(lines[:line_index]):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            caption = stripped.lstrip("#").strip()
        elif stripped.endswith(":"):
            caption = stripped[:-1].strip()
        else:
            return None
        normalized = caption.strip("` ").lower()
        if normalized in _EXAMPLE_SECTION_CAPTIONS:
            return None
        return caption or None
    return None


def _strip_fenced_blocks(text: str) -> str:
    return _FENCED_BLOCK_RE.sub("", text)


def _doctest_to_python(text: str) -> str:
    statements: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">>>"):
            statements.append(stripped[4:])
        elif stripped.startswith("..."):
            statements.append(stripped[4:])
    return "\n".join(statements)


__all__ = [
    "check_doctest_examples",
    "check_example_syntax",
    "extract_code_blocks_from_docstring",
]
