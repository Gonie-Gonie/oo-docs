# Page Overlay Example

This example shows page-positioned drawing and text overlays in a focused
workflow instead of folding every overlay detail into the general user guide.

It uses `Shape`, `TextBox`, `ImageBox`, and `PageItemScope` from
`oodocs.positioning` with `DocumentSettings(overlays=...)`. The same source also
shows inline placement for positioning objects when a drawing should move with
the body text.

Render the example:

```powershell
python examples/page_overlay_example/main.py --output-dir artifacts/page-overlay-example
```

Render only HTML while iterating:

```powershell
python examples/page_overlay_example/main.py --outputs html --quiet
```
