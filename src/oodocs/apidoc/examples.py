"""Example extraction and validation helpers for API docstrings."""

from __future__ import annotations

import doctest
import re

from oodocs.apidoc.model import ApiDocIssue, ApiExample, ApiObject


_FENCED_BLOCK_RE = re.compile(
    r"```(?P<language>[A-Za-z0-9_+-]*)[ \t]*\n(?P<code>.*?)(?:\n```|$)",
    flags=re.DOTALL,
)


def extract_code_blocks_from_docstring(text: str | None) -> list[ApiExample]:
    """Extract fenced and doctest-style examples from docstring text.

    Args:
        text: Raw docstring text.

    Returns:
        Parsed example objects. Fenced code blocks preserve their language
        labels. Doctest snippets use ``language="pycon"``.

    Examples:
        ```python
        examples = extract_code_blocks_from_docstring("```python\\nprint('ok')\\n```")
        assert examples[0].language == "python"
        ```
    """

    source = text or ""
    examples = [
        ApiExample(match.group("code").strip("\n"), language=match.group("language") or "text")
        for match in _FENCED_BLOCK_RE.finditer(source)
    ]
    doctest_code = _extract_doctest_block(source)
    if doctest_code:
        examples.append(ApiExample(doctest_code, language="pycon"))
    return examples


def check_example_syntax(example: ApiExample) -> bool:
    """Check whether an example contains valid Python syntax.

    Args:
        example: Example to check.

    Returns:
        ``True`` when syntax is valid or the example is not Python code,
        otherwise ``False``.
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


def check_doctest_examples(api_object: ApiObject) -> list[ApiDocIssue]:
    """Validate doctest-style examples for one API object.

    Args:
        api_object: API object whose examples should be checked.

    Returns:
        Issues for failing doctest examples.

    Notes:
        This helper parses doctest syntax and performs compile-level checking.
        It does not execute examples because API reference generation should not
        run arbitrary user code by default.
    """

    issues: list[ApiDocIssue] = []
    parser = doctest.DocTestParser()
    for example in api_object.examples:
        if example.language.lower() != "pycon":
            continue
        try:
            parser.get_examples(example.code)
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


def _extract_doctest_block(text: str) -> str | None:
    lines = []
    in_block = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(">>>") or stripped.startswith("..."):
            in_block = True
            lines.append(stripped)
        elif in_block and stripped:
            lines.append(stripped)
        elif in_block:
            break
    return "\n".join(lines) if lines else None


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
