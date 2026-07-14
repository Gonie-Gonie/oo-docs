"""Generic cover-page model."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
from typing import Sequence

from oodocs.components.base import Block, BlockInput, coerce_blocks
from oodocs.components.inline import InlineInput, Text, coerce_inlines
from oodocs.components.media import Figure, processed_image_source_to_buffer
from oodocs.styles.cover import CoverPageStyle


@dataclass(slots=True, init=False)
class CoverPage:
    """Caller-owned cover content consumed by :class:`TitleMatter`."""

    eyebrow: list[Text] | None
    organization: list[Text] | None
    logo: object | None
    date: list[Text] | None
    footer: list[Text] | None
    note: tuple[Block, ...]
    extra_top: tuple[Block, ...]
    extra_bottom: tuple[Block, ...]
    style: CoverPageStyle | str | None

    def __init__(
        self,
        *,
        eyebrow: InlineInput | None = None,
        organization: InlineInput | None = None,
        logo: object | None = None,
        date: InlineInput | None = None,
        footer: InlineInput | None = None,
        note: BlockInput | Sequence[BlockInput] | None = None,
        extra_top: Sequence[BlockInput] = (),
        extra_bottom: Sequence[BlockInput] = (),
        style: CoverPageStyle | str | None = None,
    ) -> None:
        self.eyebrow = coerce_inlines((eyebrow,)) if eyebrow is not None else None
        self.organization = (
            coerce_inlines((organization,)) if organization is not None else None
        )
        self.logo = logo
        self.date = coerce_inlines((date,)) if date is not None else None
        self.footer = coerce_inlines((footer,)) if footer is not None else None
        if note is None:
            note_values: Sequence[BlockInput] = ()
        elif isinstance(note, Sequence) and not isinstance(note, (str, bytes, Block)):
            note_values = note
        else:
            note_values = (note,)  # type: ignore[assignment]
        self.note = tuple(coerce_blocks(note_values))
        self.extra_top = tuple(coerce_blocks(extra_top))
        self.extra_bottom = tuple(coerce_blocks(extra_bottom))
        if style is not None and not isinstance(style, (CoverPageStyle, str)):
            raise TypeError("CoverPage.style must be a CoverPageStyle, name, or None")
        self.style = style

    def resolved_style(self) -> CoverPageStyle:
        """Return the concrete cover style."""

        if self.style is None:
            return CoverPageStyle()
        if isinstance(self.style, str):
            return CoverPageStyle.named(self.style)
        return self.style

    def logo_figure(self) -> Figure | None:
        """Return a Figure fitted inside the style's logo bounds."""

        if self.logo is None:
            return None
        style = self.resolved_style()
        base = Figure(self.logo, alt_text="Cover logo")
        width, height = _fitted_logo_dimensions(base, style)
        return Figure(
            base.image_source,
            width=width,
            height=height,
            unit=style.unit,
            image_format=base.image_format,
            image_dpi=base.image_dpi,
            alt_text="Cover logo",
        )


def _fitted_logo_dimensions(
    figure: Figure,
    style: CoverPageStyle,
) -> tuple[float | None, float | None]:
    max_width = style.logo_max_width if style.logo_max_width > 0 else math.inf
    max_height = style.logo_max_height if style.logo_max_height > 0 else math.inf
    if math.isinf(max_width) and math.isinf(max_height):
        return None, None
    buffer = processed_image_source_to_buffer(
        figure.image_source,
        image_format=figure.image_format,
        image_dpi=figure.image_dpi,
        usage="cover logo sizing",
    )
    try:
        from PIL import Image

        with Image.open(BytesIO(buffer.getvalue())) as image:
            pixel_width, pixel_height = image.size
    except Exception as exc:
        raise ValueError("Cover logo dimensions could not be read") from exc
    if pixel_width <= 0 or pixel_height <= 0:
        raise ValueError("Cover logo dimensions must be positive")
    ratio = pixel_width / pixel_height
    if math.isinf(max_width):
        return max_height * ratio, max_height
    if math.isinf(max_height):
        return max_width, max_width / ratio
    width = min(max_width, max_height * ratio)
    return width, width / ratio


__all__ = ["CoverPage"]
