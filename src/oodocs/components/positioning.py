"""Positioned and inline drawing components.

Attributes:
    PositionAnchor: Page-positioning anchor name or custom named shape anchor.
    PositionPlacement: Placement mode for positioned content.
    PageItemScopeKind: Supported page overlay scope names.
    ShapeKind: Supported absolute-positioned shape kinds.
    ImageFit: Image fitting modes for positioned image boxes.
    PositionedItem: Union of supported page-positioned item objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, TYPE_CHECKING

from oodocs.components.base import Block
from oodocs.components.inline import InlineInput, Text, coerce_inlines
from oodocs.components.media import ImageData, coerce_image_source
from oodocs.core import PathLike, normalize_color, normalize_length_unit
from oodocs.styles import StrokeStyle

if TYPE_CHECKING:
    from oodocs.renderers.context import DocxRenderContext, HtmlRenderContext, PdfRenderContext
    from oodocs.settings import DocumentSettings


PositionAnchor = Literal["page", "margin", "content"] | str
PositionPlacement = Literal["absolute", "inline"]
PageItemScopeKind = Literal["all", "cover", "front", "main", "pages"]
PageItemPhase = Literal["cover", "front", "main"]
ShapeKind = Literal["rect", "ellipse", "line"]
ImageFit = Literal["contain", "stretch"]


@dataclass(frozen=True, slots=True, init=False)
class PageItemScope:
    """Page selection rule for document-level page items.

    Args:
        kind: Scope name. Supported values are ``"all"``, ``"cover"``,
            ``"front"``, ``"main"``, and ``"pages"``.
        start_page: One-based physical page number for ``"pages"`` scope.
        end_page: Optional inclusive end page for ``"pages"`` scope.

    Raises:
        ValueError: If the scope name or page range is invalid.

    Examples:
        ```python
        from oodocs import DocumentSettings, PageItemScope, TextBox

        settings = DocumentSettings(
            page_items=[
                TextBox("DRAFT", width=2, height=0.5, scope="all"),
                TextBox("Cover only", width=2, height=0.5, scope=PageItemScope.cover()),
                TextBox("Page 2", width=2, height=0.5, scope=PageItemScope.pages(2)),
            ]
        )
        ```
    """

    kind: PageItemScopeKind
    start_page: int | None
    end_page: int | None

    def __init__(
        self,
        kind: PageItemScopeKind | str = "all",
        *,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> None:
        normalized = str(kind).strip().lower().replace("_", "-")
        normalized = {
            "page": "pages",
            "page-range": "pages",
            "range": "pages",
        }.get(normalized, normalized)
        if normalized not in {"all", "cover", "front", "main", "pages"}:
            raise ValueError(f"Unsupported PageItemScope kind: {kind!r}")

        start: int | None = None
        end: int | None = None
        if normalized == "pages":
            if start_page is None:
                raise ValueError("PageItemScope('pages') requires start_page")
            start = _positive_page_number(start_page, "start_page")
            end = start if end_page is None else _positive_page_number(end_page, "end_page")
            if end < start:
                raise ValueError("PageItemScope end_page must be greater than or equal to start_page")
        elif start_page is not None or end_page is not None:
            raise ValueError("PageItemScope start_page and end_page require kind='pages'")

        object.__setattr__(self, "kind", normalized)
        object.__setattr__(self, "start_page", start)
        object.__setattr__(self, "end_page", end)

    @classmethod
    def all(cls) -> PageItemScope:
        """Return a scope that applies to every page.

        Returns:
            Scope matching every rendered page.
        """

        return cls("all")

    @classmethod
    def cover(cls) -> PageItemScope:
        """Return a scope for a separate cover page.

        Returns:
            Scope matching only the cover page when ``cover_page=True``.
        """

        return cls("cover")

    @classmethod
    def front(cls) -> PageItemScope:
        """Return a scope for front matter pages after the cover page.

        Returns:
            Scope matching front matter pages after the cover page.
        """

        return cls("front")

    @classmethod
    def main(cls) -> PageItemScope:
        """Return a scope for the main document body.

        Returns:
            Scope matching the numbered main document body.
        """

        return cls("main")

    @classmethod
    def pages(cls, start_page: int, end_page: int | None = None) -> PageItemScope:
        """Return a physical page-number range scope.

        Args:
            start_page: One-based first physical page.
            end_page: Optional one-based inclusive last physical page. Defaults
                to ``start_page``.

        Returns:
            Scope matching the requested physical page range.
        """

        return cls("pages", start_page=start_page, end_page=end_page)

    def matches(
        self,
        *,
        page_number: int | None = None,
        phase: PageItemPhase | str | None = None,
    ) -> bool:
        """Return whether this scope applies to a page context.

        Args:
            page_number: One-based physical page number, when available.
            phase: Page phase, such as ``"cover"``, ``"front"``, or
                ``"main"``.

        Returns:
            ``True`` when the scope applies to the provided page context.
        """

        if self.kind == "all":
            return True
        if self.kind == "pages":
            if page_number is None or self.start_page is None or self.end_page is None:
                return False
            return self.start_page <= page_number <= self.end_page
        return phase == self.kind


PageItemScopeInput = PageItemScope | str | int | tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class PositionedBox:
    """Resolved page-relative box in inches.

    Attributes:
        item: Original positioned item.
        x: Page-relative x coordinate in inches.
        y: Page-relative y coordinate in inches.
        width: Width in inches.
        height: Height in inches.

    Examples:
        ```python
        from oodocs import DocumentSettings, TextBox
        from oodocs.components.positioning import resolve_positioned_boxes

        settings = DocumentSettings()
        boxes = resolve_positioned_boxes([TextBox("DRAFT", width=2, height=0.5)], settings, settings.unit)
        ```
    """

    item: PositionedItem
    x: float
    y: float
    width: float
    height: float


def _positive_page_number(value: int, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"PageItemScope {field_name} must be a positive page number")
    page_number = int(value)
    if page_number < 1:
        raise ValueError(f"PageItemScope {field_name} must be a positive page number")
    return page_number


def coerce_page_item_scope(value: PageItemScopeInput = None) -> PageItemScope:
    """Normalize a page item scope value.

    Args:
        value: ``None``, a scope name, page number, page range tuple, or
            ``PageItemScope``.

    Returns:
        Normalized ``PageItemScope``.

    Raises:
        TypeError: If the value cannot be interpreted as a scope.
        ValueError: If the scope value is invalid.
    """

    if value is None:
        return PageItemScope.all()
    if isinstance(value, PageItemScope):
        return value
    if isinstance(value, str):
        return PageItemScope(value)
    if isinstance(value, bool):
        raise TypeError("Page item scope must not be a boolean")
    if isinstance(value, int):
        return PageItemScope.pages(value)
    if isinstance(value, tuple) and len(value) == 2:
        start_page, end_page = value
        return PageItemScope.pages(start_page, end_page)
    raise TypeError(f"Unsupported page item scope: {type(value)!r}")


def _normalize_anchor(anchor: PositionAnchor) -> str:
    value = str(anchor).strip()
    if not value:
        raise ValueError("Position anchor must not be empty")
    if value == "content":
        return "margin"
    return value


@dataclass(slots=True, init=False)
class TextBox(Block):
    """Positioned or inline text box.

    Absolute coordinates are measured from the selected anchor's top-left
    corner. Built-in anchors are ``"page"`` and ``"margin"``; any other anchor
    name refers to a named ``Shape``.

    Args:
        *content: Inline text content.
        x: X coordinate in ``unit`` from the anchor origin.
        y: Y coordinate in ``unit`` from the anchor origin.
        width: Box width in ``unit``.
        height: Box height in ``unit``.
        anchor: Built-in anchor or named shape anchor.
        placement: ``"absolute"`` for page items or ``"inline"`` in content.
        text_alignment: Horizontal text alignment.
        vertical_alignment: Vertical text alignment.
        font_size: Optional font size override.
        unit: Unit for coordinates and dimensions.
        z_index: Stacking order for page-positioned rendering.
        scope: Page selection for ``DocumentSettings(page_items=...)``.

    Raises:
        ValueError: If placement, alignment, or dimensions are invalid.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, Paragraph, TextBox

        watermark = TextBox(
            "DRAFT",
            x=1,
            y=1,
            width=2,
            height=0.5,
            font_size=24,
        )
        settings = DocumentSettings(page_items=[watermark])
        document = Document("Draft Report", Paragraph("Body"), settings=settings)
        ```
    """

    content: list[Text]
    x: float
    y: float
    width: float
    height: float
    anchor: str
    placement: PositionPlacement
    text_alignment: str
    vertical_alignment: str
    font_size: float | None
    unit: str | None
    z_index: int
    scope: PageItemScope

    def __init__(
        self,
        *content: InlineInput,
        x: float = 0.0,
        y: float = 0.0,
        width: float,
        height: float,
        anchor: PositionAnchor = "page",
        placement: PositionPlacement = "absolute",
        text_alignment: str = "left",
        vertical_alignment: str = "top",
        font_size: float | None = None,
        unit: str | None = None,
        z_index: int = 0,
        scope: PageItemScopeInput = None,
    ) -> None:
        if placement not in {"absolute", "inline"}:
            raise ValueError(f"Unsupported TextBox placement: {placement!r}")
        if text_alignment not in {"left", "center", "right"}:
            raise ValueError(f"Unsupported TextBox text alignment: {text_alignment!r}")
        if vertical_alignment not in {"top", "middle", "bottom"}:
            raise ValueError(f"Unsupported TextBox vertical alignment: {vertical_alignment!r}")
        if width < 0 or height < 0:
            raise ValueError("TextBox width and height must be >= 0")
        self.content = coerce_inlines(content)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.anchor = _normalize_anchor(anchor)
        self.placement = placement
        self.text_alignment = text_alignment
        self.vertical_alignment = vertical_alignment
        self.font_size = font_size
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.z_index = z_index
        self.scope = coerce_page_item_scope(scope)

    def plain_text(self) -> str:
        """Return the textbox content without styling metadata.

        Returns:
            Concatenated plain text for the textbox content.
        """

        return "".join(fragment.plain_text() for fragment in self.content)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this text box into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_text_box(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this text box into PDF flowables.

        Returns:
            ReportLab flowables for this text box.
        """

        return renderer.render_text_box(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this text box into HTML markup.

        Returns:
            HTML markup for this text box.
        """

        return renderer.render_text_box(self, context)


@dataclass(slots=True, init=False)
class Shape(Block):
    """A basic positioned or inline shape.

    Args:
        kind: Shape kind.
        x: X coordinate in ``unit`` from the anchor origin.
        y: Y coordinate in ``unit`` from the anchor origin.
        width: Shape width in ``unit``.
        height: Shape height in ``unit``.
        anchor: Built-in anchor or named shape anchor.
        placement: ``"absolute"`` for page items or ``"inline"`` in content.
        name: Optional anchor name other items can target.
        stroke: Optional stroke style.
        fill_color: Optional fill color as a hex string.
        unit: Unit for coordinates and dimensions.
        z_index: Stacking order for page-positioned rendering.
        scope: Page selection for ``DocumentSettings(page_items=...)``.

    Raises:
        ValueError: If kind, placement, dimensions, or name are invalid.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, Paragraph, Shape, StrokeStyle

        anchor = Shape.rect(
            width=2,
            height=1,
            x=0.5,
            y=0.5,
            name="logo-area",
            stroke=StrokeStyle.solid("CBD5E1", width=0.75),
            fill_color="F7FAFC",
        )
        settings = DocumentSettings(page_items=[anchor])
        document = Document("Branded Report", Paragraph("Body"), settings=settings)
        ```
    """

    kind: ShapeKind
    x: float
    y: float
    width: float
    height: float
    anchor: str
    placement: PositionPlacement
    name: str | None
    stroke: StrokeStyle
    fill_color: str | None
    unit: str | None
    z_index: int
    scope: PageItemScope

    def __init__(
        self,
        kind: ShapeKind,
        *,
        x: float = 0.0,
        y: float = 0.0,
        width: float,
        height: float,
        anchor: PositionAnchor = "page",
        placement: PositionPlacement = "absolute",
        name: str | None = None,
        stroke: StrokeStyle | None = None,
        fill_color: str | None = None,
        unit: str | None = None,
        z_index: int = 0,
        scope: PageItemScopeInput = None,
    ) -> None:
        if kind not in {"rect", "ellipse", "line"}:
            raise ValueError(f"Unsupported shape kind: {kind!r}")
        if placement not in {"absolute", "inline"}:
            raise ValueError(f"Unsupported Shape placement: {placement!r}")
        if kind != "line" and (width < 0 or height < 0):
            raise ValueError("Shape width and height must be >= 0")
        resolved_stroke = stroke or StrokeStyle.solid("000000", width=1.0)
        if not isinstance(resolved_stroke, StrokeStyle):
            raise TypeError("Shape.stroke must be a StrokeStyle")
        if name is not None and not name.strip():
            raise ValueError("Shape name must not be empty")
        self.kind = kind
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.anchor = _normalize_anchor(anchor)
        self.placement = placement
        self.name = name.strip() if name is not None else None
        self.stroke = resolved_stroke
        self.fill_color = normalize_color(fill_color)
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.z_index = z_index
        self.scope = coerce_page_item_scope(scope)

    @classmethod
    def rect(cls, *, width: float, height: float, **kwargs: object) -> Shape:
        """Create a rectangle shape.

        Args:
            width: Rectangle width.
            height: Rectangle height.
            **kwargs: Additional arguments forwarded to ``Shape``.

        Returns:
            Rectangle shape.

        Examples:
            ```python
            shape = Shape.rect(width=2, height=1, fill_color="E7EEF7")
            ```
        """

        return cls("rect", width=width, height=height, **kwargs)

    @classmethod
    def ellipse(cls, *, width: float, height: float, **kwargs: object) -> Shape:
        """Create an ellipse shape.

        Args:
            width: Ellipse bounding-box width.
            height: Ellipse bounding-box height.
            **kwargs: Additional arguments forwarded to ``Shape``.

        Returns:
            Ellipse shape.

        Examples:
            ```python
            shape = Shape.ellipse(width=1, height=1, stroke=StrokeStyle.solid("336699"))
            ```
        """

        return cls("ellipse", width=width, height=height, **kwargs)

    @classmethod
    def line(cls, *, width: float, height: float, **kwargs: object) -> Shape:
        """Create a line shape.

        Args:
            width: Horizontal line delta.
            height: Vertical line delta.
            **kwargs: Additional arguments forwarded to ``Shape``.

        Returns:
            Line shape.

        Examples:
            ```python
            shape = Shape.line(width=3, height=0, stroke=StrokeStyle.solid("334155", width=0.5))
            ```
        """

        return cls("line", width=width, height=height, **kwargs)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this shape into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_shape(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this shape into PDF flowables.

        Returns:
            ReportLab flowables for this shape.
        """

        return renderer.render_shape(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this shape into HTML markup.

        Returns:
            HTML markup for this shape.
        """

        return renderer.render_shape(self, context)

    def plain_text(self) -> str:
        """Return the inline text contribution for the shape.

        Returns:
            Empty string because shapes have no text content.
        """

        return ""


@dataclass(slots=True, init=False)
class ImageBox(Block):
    """A positioned or inline image.

    Args:
        image_source: Path, bytes, ``ImageData``, or plot-like object.
        x: X coordinate in ``unit`` from the anchor origin.
        y: Y coordinate in ``unit`` from the anchor origin.
        width: Image box width in ``unit``.
        height: Image box height in ``unit``.
        anchor: Built-in anchor or named shape anchor.
        placement: ``"absolute"`` for page items or ``"inline"`` in content.
        fit: Whether to contain the image or stretch it to the box.
        image_format: Image format for plot-like sources.
        image_dpi: Optional image DPI for plot-like sources.
        unit: Unit for coordinates and dimensions.
        z_index: Stacking order for page-positioned rendering.
        scope: Page selection for ``DocumentSettings(page_items=...)``.

    Raises:
        ValueError: If placement, dimensions, or fit are invalid.

    Examples:
        ```python
        from oodocs import Document, DocumentSettings, ImageBox, Paragraph

        logo = ImageBox("logo.png", x=0.5, y=0.5, width=1.2, height=0.6)
        settings = DocumentSettings(page_items=[logo])
        document = Document("Branded Report", Paragraph("Body"), settings=settings)
        ```
    """

    image_source: object
    x: float
    y: float
    width: float
    height: float
    anchor: str
    placement: PositionPlacement
    fit: ImageFit
    image_format: str
    image_dpi: int | None
    unit: str | None
    z_index: int
    scope: PageItemScope

    def __init__(
        self,
        image_source: PathLike | object,
        *,
        x: float = 0.0,
        y: float = 0.0,
        width: float,
        height: float,
        anchor: PositionAnchor = "page",
        placement: PositionPlacement = "absolute",
        fit: ImageFit = "contain",
        image_format: str = "png",
        image_dpi: int | None = 150,
        unit: str | None = None,
        z_index: int = 0,
        scope: PageItemScopeInput = None,
    ) -> None:
        if placement not in {"absolute", "inline"}:
            raise ValueError(f"Unsupported ImageBox placement: {placement!r}")
        if width < 0 or height < 0:
            raise ValueError("ImageBox width and height must be >= 0")
        if fit not in {"contain", "stretch"}:
            raise ValueError(f"Unsupported ImageBox fit: {fit!r}")
        self.image_source = coerce_image_source(image_source)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.anchor = _normalize_anchor(anchor)
        self.placement = placement
        self.fit = fit
        self.image_format = (
            self.image_source.image_format
            if isinstance(self.image_source, ImageData) and image_format == "png"
            else image_format
        )
        self.image_dpi = image_dpi
        self.unit = normalize_length_unit(unit) if unit is not None else None
        self.z_index = z_index
        self.scope = coerce_page_item_scope(scope)

    def render_to_docx(
        self,
        renderer: object,
        container: object,
        context: DocxRenderContext,
    ) -> None:
        """Render this image box into a DOCX container.

        Args:
            renderer: DOCX renderer instance.
            container: Target python-docx container.
            context: Shared DOCX render context.
        """

        renderer.render_image_box(container, self, context)

    def render_to_pdf(
        self,
        renderer: object,
        context: PdfRenderContext,
    ) -> list[object]:
        """Render this image box into PDF flowables.

        Returns:
            ReportLab flowables for this image box.
        """

        return renderer.render_image_box(self, context)

    def render_to_html(
        self,
        renderer: object,
        context: HtmlRenderContext,
    ) -> str:
        """Render this image box into HTML markup.

        Returns:
            HTML markup for this image box.
        """

        return renderer.render_image_box(self, context)

    def plain_text(self) -> str:
        """Return the inline text contribution for the image.

        Returns:
            Empty string because image boxes have no text content.
        """

        return ""


PositionedItem = TextBox | Shape | ImageBox


def coerce_positioned_items(values: Iterable[PositionedItem] | None) -> tuple[PositionedItem, ...]:
    """Validate page-positioned drawing items.

    Args:
        values: Positioned items or ``None``.

    Returns:
        Tuple of validated absolute-positioned items.

    Raises:
        TypeError: If an item type is unsupported.
        ValueError: If an item is inline or references an unknown anchor.

    Examples:
        ```python
        items = coerce_positioned_items([TextBox("DRAFT", width=2, height=0.5)])
        ```
    """

    if values is None:
        return ()
    items = tuple(values)
    for item in items:
        if not isinstance(item, (TextBox, Shape, ImageBox)):
            raise TypeError(f"Unsupported page item: {type(item)!r}")
        if item.placement != "absolute":
            raise ValueError("Document page_items require placement='absolute'")
    _validate_shape_anchors(items)
    return items


def resolve_positioned_boxes(
    items: Iterable[PositionedItem],
    settings: DocumentSettings,
    default_unit: str,
    *,
    page_number: int | None = None,
    phase: PageItemPhase | str | None = None,
) -> list[PositionedBox]:
    """Resolve item coordinates to page-relative inches.

    Args:
        items: Positioned items to resolve.
        settings: Document settings containing page and margin geometry.
        default_unit: Unit to use for items without explicit units.
        page_number: Optional one-based physical page number used to filter
            page-scoped items.
        phase: Optional page phase used to filter cover/front/main items.

    Returns:
        Resolved boxes sorted by stacking order.

    Raises:
        ValueError: If anchors are unknown, duplicated, or cyclic.

    Examples:
        ```python
        from oodocs import DocumentSettings, TextBox

        settings = DocumentSettings()
        boxes = resolve_positioned_boxes(
            [TextBox("DRAFT", width=2, height=0.5)],
            settings,
            settings.unit,
        )
        ```
    """

    item_list = tuple(
        item
        for item in items
        if _page_item_scope_matches(item, page_number=page_number, phase=phase)
    )
    _validate_shape_anchors(item_list)
    shape_indexes = {
        item.name: index
        for index, item in enumerate(item_list)
        if isinstance(item, Shape) and item.name is not None
    }
    resolved_by_index: dict[int, PositionedBox] = {}
    resolving: set[int] = set()

    def resolve_index(index: int) -> PositionedBox:
        existing = resolved_by_index.get(index)
        if existing is not None:
            return existing
        if index in resolving:
            raise ValueError("Shape anchors cannot form a cycle")
        resolving.add(index)
        item = item_list[index]
        if item.anchor in shape_indexes:
            # Shape anchors can depend on earlier or later items, so resolution
            # is recursive with cycle detection instead of a single pass.
            target = resolve_index(shape_indexes[item.anchor])
            origin = (target.x, target.y)
        else:
            origin = _anchor_origin(item.anchor, settings)
        box = _resolve_positioned_box(item, origin, default_unit)
        resolved_by_index[index] = box
        resolving.remove(index)
        return box

    resolved = [resolve_index(index) for index in range(len(item_list))]
    return [
        box
        for _, box in sorted(
            enumerate(resolved),
            key=lambda indexed: (indexed[1].item.z_index, indexed[0]),
        )
    ]


def _page_item_scope_matches(
    item: PositionedItem,
    *,
    page_number: int | None,
    phase: PageItemPhase | str | None,
) -> bool:
    if page_number is None and phase is None:
        return True
    return item.scope.matches(page_number=page_number, phase=phase)


def _validate_shape_anchors(items: tuple[PositionedItem, ...]) -> None:
    names: set[str] = set()
    for item in items:
        if isinstance(item, Shape) and item.name is not None:
            if item.name in names:
                raise ValueError(f"Duplicate shape name: {item.name!r}")
            names.add(item.name)
    for item in items:
        if item.anchor not in {"page", "margin"} and item.anchor not in names:
            raise ValueError(f"Unknown shape anchor: {item.anchor!r}")


def _resolve_positioned_box(
    item: PositionedItem,
    origin: tuple[float, float],
    default_unit: str,
) -> PositionedBox:
    origin_x, origin_y = origin
    unit = item.unit or default_unit
    from oodocs.core import length_to_inches

    return PositionedBox(
        item=item,
        x=origin_x + length_to_inches(item.x, unit),
        y=origin_y + length_to_inches(item.y, unit),
        width=length_to_inches(item.width, unit),
        height=length_to_inches(item.height, unit),
    )


def _anchor_origin(
    anchor: str,
    settings: DocumentSettings,
) -> tuple[float, float]:
    if anchor == "page":
        return 0.0, 0.0
    if anchor == "margin":
        top, _, _, left = settings.page_margin_inches()
        return left, top
    raise ValueError(f"Unknown shape anchor: {anchor!r}")


__all__ = [
    "ImageBox",
    "ImageFit",
    "PageItemPhase",
    "PageItemScope",
    "PageItemScopeInput",
    "PageItemScopeKind",
    "PositionAnchor",
    "PositionPlacement",
    "PositionedBox",
    "PositionedItem",
    "Shape",
    "ShapeKind",
    "TextBox",
    "coerce_page_item_scope",
    "coerce_positioned_items",
    "resolve_positioned_boxes",
]
