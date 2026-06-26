"""Helpers for lightweight Markdown inline parsing."""

from __future__ import annotations

import re
from collections.abc import Mapping

from oodocs.components.inline import (
    Bold,
    Hyperlink,
    Italic,
    LineBreak,
    InlineCode,
    Strikethrough,
    Text,
)
from oodocs.layout.theme import TextStyle

_BARE_LINK_RE = re.compile(
    r"(https?://[^\s<]+|www\.[^\s<]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
)
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_PUNCTUATION_ESCAPES = set(r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~-')


def markup(
    source: str,
    *,
    style: TextStyle | None = None,
    references: Mapping[str, str] | None = None,
) -> list[Text]:
    """Parse lightweight Markdown inline text into fragments.

    Supported markers:
    - ``**bold**``
    - ``__bold__``
    - ``*italic*``
    - ``_italic_``
    - ``~~strikethrough~~``
    - `` `code` ``
    - ``[label](https://example.com)`` links
    - ``<https://example.com>`` and bare URL autolinks

    Args:
        source: Markup source text.
        style: Base style applied to parsed fragments.
        references: Optional reference-style link targets keyed by label.

    Returns:
        Parsed inline fragments.

    Examples:
        ```python
        from oodocs import Paragraph, markup

        paragraph = Paragraph(markup("Use **bold** and `code`."))
        ```
    """

    base_style = style or TextStyle()
    normalized_references = {
        _normalize_reference_label(label): target
        for label, target in (references or {}).items()
    }
    return _parse_markup(source, base_style, normalized_references)


def _parse_markup(
    source: str,
    base_style: TextStyle,
    references: Mapping[str, str],
) -> list[Text]:
    fragments: list[Text] = []
    cursor = 0
    length = len(source)

    while cursor < length:
        if source[cursor] == "\\":
            if cursor + 1 < length and source[cursor + 1] == "\n":
                fragments.append(LineBreak())
                cursor += 2
                continue
            if cursor + 1 < length and source[cursor + 1] in _PUNCTUATION_ESCAPES:
                fragments.append(Text(source[cursor + 1], style=base_style))
                cursor += 2
                continue

        if source[cursor] == "\n":
            if not _trim_trailing_hard_break_spaces(fragments):
                fragments.append(Text(" ", style=base_style))
            cursor += 1
            continue

        code_fragment = _parse_code_span(source, cursor, base_style)
        if code_fragment is not None:
            fragment, cursor = code_fragment
            fragments.append(fragment)
            continue

        link_fragment = _parse_markdown_link(
            source,
            cursor,
            base_style,
            references,
        )
        if link_fragment is not None:
            fragment, cursor = link_fragment
            fragments.append(fragment)
            continue

        autolink_fragment = _parse_angle_autolink(source, cursor, base_style)
        if autolink_fragment is not None:
            fragment, cursor = autolink_fragment
            fragments.append(fragment)
            continue

        bare_link_fragment = _parse_bare_autolink(source, cursor, base_style)
        if bare_link_fragment is not None:
            fragment, cursor = bare_link_fragment
            fragments.append(fragment)
            continue

        if source.startswith("~~", cursor):
            end = source.find("~~", cursor + 2)
            if end != -1:
                fragments.extend(
                    _rebase(
                        markup(source[cursor + 2 : end], references=references),
                        base_style.merged(TextStyle(strikethrough=True)),
                    )
                )
                cursor = end + 2
                continue

        if source.startswith(("**", "__"), cursor):
            marker = source[cursor : cursor + 2]
            end = source.find(marker, cursor + 2)
            if end != -1:
                fragments.extend(
                    _rebase(
                        markup(source[cursor + 2 : end], references=references),
                        base_style.merged(TextStyle(bold=True)),
                    )
                )
                cursor = end + 2
                continue

        if source[cursor] in {"*", "_"}:
            marker = source[cursor]
            if cursor + 1 < length and source[cursor + 1] == marker:
                fragments.append(Text(marker, style=base_style))
                cursor += 1
                continue
            end = source.find(marker, cursor + 1)
            if end != -1:
                fragments.extend(
                    _rebase(
                        markup(source[cursor + 1 : end], references=references),
                        base_style.merged(TextStyle(italic=True)),
                    )
                )
                cursor = end + 1
                continue

        next_positions = [
            position
            for position in (
                source.find("\\", cursor),
                source.find("**", cursor),
                source.find("__", cursor),
                source.find("*", cursor),
                source.find("_", cursor),
                source.find("~~", cursor),
                source.find("`", cursor),
                source.find("[", cursor),
                source.find("<", cursor),
                source.find("\n", cursor),
            )
            if position != -1
        ]
        bare_match = _BARE_LINK_RE.search(source, cursor)
        if bare_match is not None:
            next_positions.append(bare_match.start())
        # Jump directly to the next special marker instead of appending one
        # character at a time; this keeps ordinary text runs compact.
        next_marker = min(next_positions, default=length)
        if next_marker == cursor:
            next_marker = cursor + 1
        fragments.append(Text(source[cursor:next_marker], style=base_style))
        cursor = next_marker

    return fragments


def _rebase(fragments: list[Text], style: TextStyle) -> list[Text]:
    rebased: list[Text] = []
    for fragment in fragments:
        if isinstance(fragment, Bold):
            rebased.append(Bold(fragment.value, style=style.merged(fragment.style)))
        elif isinstance(fragment, Italic):
            rebased.append(Italic(fragment.value, style=style.merged(fragment.style)))
        elif isinstance(fragment, InlineCode):
            rebased.append(InlineCode(fragment.value, style=style.merged(fragment.style)))
        elif isinstance(fragment, Strikethrough):
            rebased.append(Strikethrough(fragment.value, style=style.merged(fragment.style)))
        elif isinstance(fragment, Hyperlink):
            rebased.append(
                Hyperlink(
                    fragment.target,
                    _rebase(fragment.label, style),
                    internal=fragment.internal,
                    style=style.merged(fragment.style),
                )
            )
        elif isinstance(fragment, LineBreak):
            rebased.append(fragment)
        else:
            rebased.append(Text(fragment.value, style=style.merged(fragment.style)))
    return rebased


def _parse_code_span(
    source: str,
    cursor: int,
    base_style: TextStyle,
) -> tuple[InlineCode, int] | None:
    if source[cursor] != "`":
        return None
    marker_end = cursor
    while marker_end < len(source) and source[marker_end] == "`":
        marker_end += 1
    marker = source[cursor:marker_end]
    end = source.find(marker, marker_end)
    if end == -1:
        return None
    value = source[marker_end:end].replace("\n", " ")
    if len(value) >= 2 and value[:1] == value[-1:] == " " and value.strip(" "):
        value = value[1:-1]
    return InlineCode(value, style=base_style), end + len(marker)


def _parse_markdown_link(
    source: str,
    cursor: int,
    base_style: TextStyle,
    references: Mapping[str, str],
) -> tuple[Text, int] | None:
    image = source.startswith("![", cursor)
    if image:
        label_start = cursor + 2
    elif source[cursor] == "[":
        label_start = cursor + 1
    else:
        return None

    label_end = _find_closing_bracket(source, label_start)
    if label_end == -1:
        return None
    label = source[label_start:label_end]
    after_label = label_end + 1

    if after_label < len(source) and source[after_label] == "(":
        destination_end = _find_closing_parenthesis(source, after_label + 1)
        if destination_end == -1:
            return None
        destination_text = source[after_label + 1 : destination_end].strip()
        target = _first_link_destination(destination_text)
        if not target:
            return None
        if image:
            # Inline image syntax degrades to alt text because image placement
            # is represented by block media components elsewhere.
            return Text(label, style=base_style), destination_end + 1
        return (
            Hyperlink.external(
                _strip_angle_destination(target),
                markup(label, style=base_style, references=references),
                style=base_style,
            ),
            destination_end + 1,
        )

    if after_label < len(source) and source[after_label] == "[":
        reference_end = _find_closing_bracket(source, after_label + 1)
        if reference_end == -1:
            return None
        reference_label = source[after_label + 1 : reference_end] or label
        target = references.get(_normalize_reference_label(reference_label))
        if target is None:
            return None
        return (
            Hyperlink.external(
                target,
                markup(label, style=base_style, references=references),
                style=base_style,
            ),
            reference_end + 1,
        )

    return None


def _parse_angle_autolink(
    source: str,
    cursor: int,
    base_style: TextStyle,
) -> tuple[Hyperlink, int] | None:
    if source[cursor] != "<":
        return None
    end = source.find(">", cursor + 1)
    if end == -1:
        return None
    value = source[cursor + 1 : end]
    target = _autolink_target(value)
    if target is None:
        return None
    return Hyperlink.external(target, value, style=base_style), end + 1


def _parse_bare_autolink(
    source: str,
    cursor: int,
    base_style: TextStyle,
) -> tuple[Hyperlink, int] | None:
    match = _BARE_LINK_RE.match(source, cursor)
    if match is None:
        return None
    label = match.group(0)
    stripped_label = label.rstrip(".,;:!?")
    if not stripped_label:
        return None
    target = _autolink_target(stripped_label)
    if target is None:
        return None
    return Hyperlink.external(target, stripped_label, style=base_style), cursor + len(stripped_label)


def _autolink_target(value: str) -> str | None:
    if value.startswith(("http://", "https://", "mailto:")):
        return value
    if value.startswith("www."):
        return f"http://{value}"
    if _EMAIL_RE.match(value):
        return f"mailto:{value}"
    return None


def _find_closing_bracket(source: str, cursor: int) -> int:
    while cursor < len(source):
        if source[cursor] == "\\":
            cursor += 2
            continue
        if source[cursor] == "]":
            return cursor
        cursor += 1
    return -1


def _find_closing_parenthesis(source: str, cursor: int) -> int:
    depth = 0
    while cursor < len(source):
        character = source[cursor]
        if character == "\\":
            cursor += 2
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                return cursor
            depth -= 1
        cursor += 1
    return -1


def _first_link_destination(value: str) -> str:
    if value.startswith("<"):
        end = value.find(">")
        return value[: end + 1] if end != -1 else value
    quote_start = min(
        [position for position in (value.find('"'), value.find("'")) if position != -1],
        default=-1,
    )
    paren_title_start = value.find(" (")
    split_at = min(
        [position for position in (quote_start, paren_title_start) if position != -1],
        default=-1,
    )
    if split_at != -1:
        value = value[:split_at]
    return value.strip()


def _strip_angle_destination(value: str) -> str:
    if len(value) >= 2 and value[0] == "<" and value[-1] == ">":
        return value[1:-1]
    return value


def _normalize_reference_label(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _trim_trailing_hard_break_spaces(fragments: list[Text]) -> bool:
    if not fragments:
        return False
    fragment = fragments[-1]
    if type(fragment) is not Text or not fragment.value.endswith("  "):
        return False
    fragment.value = fragment.value[:-2]
    fragments.append(LineBreak())
    return True


__all__ = ["markup"]
