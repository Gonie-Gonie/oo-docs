"""Shared helpers for style object construction."""

from __future__ import annotations

from dataclasses import fields


def _style_with_overrides(
    style: object | None,
    style_type: type,
    overrides: dict[str, object | None],
) -> object:
    values = {name: value for name, value in overrides.items() if value is not None}
    if isinstance(style, str):
        if values:
            raise TypeError("Named styles cannot be combined with direct style overrides")
        return style
    if style is None:
        return style_type(**values)
    if not values:
        return style
    merged = {style_field.name: getattr(style, style_field.name) for style_field in fields(style_type)}
    merged.update(values)
    return style_type(**merged)
