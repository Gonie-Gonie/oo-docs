# Docscriptor Working Notes

This file is the shared memory for ongoing work on this repository. Keep it readable for the project owner, future Codex sessions, and other LLMs.

## Operating Rule

- Continue updating this file as the project evolves. Record design philosophy, API direction, compatibility rules, and decisions that future work should remember.
- Prefer explicit, author-friendly APIs over hidden magic. Docscriptor should feel like writing a document in Python, not like configuring a renderer.
- Keep one source document renderable to DOCX, PDF, and HTML. New components should define behavior for all supported renderers or clearly document limitations.
- Preserve existing examples and tests unless a user explicitly asks to change the public behavior.
- When adding a feature, update tests and examples enough that another contributor can see the intended usage.

## Current Direction

- The project builds structured documents from Python objects and exports them to DOCX, PDF, and HTML.
- Journal-style and usage-guide examples are important living specifications. They should stay realistic and readable.
- Cross-renderer consistency matters more than perfect renderer-specific fidelity.

## Active Work Memory

- Keep this shared note file and include the instruction to keep updating it.
- Keep active task details in commit messages, tests, examples, and PR notes rather than preserving every short-lived implementation idea here.

## API Evolution Notes

- From 1.0.0 onward, treat public API changes as semver-governed changes.
  Breaking changes should be deliberate, documented in release notes, and covered by
  tests or examples that show the replacement path.
- Prefer clear, explicit, maintainable APIs over carrying old names by default, but
  avoid casual public API churn after the 1.0.0 line.
- Prefer document-level defaults through `DocumentSettings` when a setting should apply consistently across renderers. `Document` owns content identity and rendering entry points; metadata, page geometry, overlays, units, and theme access should stay under `document.settings`. Use `metadata_author` for file properties and `authors` for visible structured title matter.
- Prefer editable flow primitives for report-like layouts: `Box` + `BoxStyle`, `Table`, `Figure`, and normal paragraphs should cover tcolorbox-style panels, callouts, and form sections before reaching for page-positioned drawing objects.
- The old `Sheet` model is removed. Use `DocumentSettings(page_items=[Shape..., TextBox..., ImageBox...])` for absolute page overlays that do not move body text. Anchors are `page`, `margin`/`content`, or an earlier named `Shape`.
- `Shape`, `TextBox`, and `ImageBox` also support `placement="inline"` so users can insert drawing objects into the body flow in a Word-like "in line with text" mode, similar to direct LaTeX `includegraphics` usage.
- Table authors should choose whether a table may split, not whether it is a normal table or longtable. `Table(split=True)` means here/in-source-order and splittable; `split=False` keeps short tables together but still auto-splits very long tables with repeated headers where possible. `placement=...` on tables and figures is an advanced hint for here/float/top/bottom/page-like behavior.
- Documents now have `validate()` as a preflight API. Validation returns a structured `ValidationResult` that prints as a table, records format scope (`docx`, `pdf`, `html`), and is run automatically before `save*` rendering. Keep future renderer-specific caveats connected to `docscriptor.compatibility` and validation issues rather than scattering ad hoc checks in renderers.
- The CLI entry point is `docscriptor.cli:main`, with `build`, `convert`, and `validate` subcommands. Keep CLI behavior thin over `docscriptor.workflows` so Python API and command-line behavior stay aligned.
- Theorem-like blocks use `CountableBlock` plus `countable_kind(...)`. Built-ins such as `Definition`, `Lemma`, `Proposition`, `Theorem`, `Corollary`, `Example`, `Remark`, `Assumption`, `Axiom`, `Claim`, and `Conjecture` share the document-wide `theorem` counter; `Proof` is unnumbered by default. Custom countable classes should be made with the factory instead of asking users to subclass.
- Markdown and notebook imports should preserve editable Docscriptor objects, not only rendered text. Prefer file-aware helpers such as `from_markdown_file(...)` for relative assets, and use `ImageData` for in-memory imported images such as notebook display outputs.
- Renderer image-source handling is centralized through media helpers such as `image_source_to_buffer(...)` and `image_source_to_bytes(...)`. Keep new image source types compatible there rather than duplicating save/buffer logic in each renderer.
- The usage guide example is the broad user-facing reference. Keep it current when major APIs change; it should show rendered examples, search-friendly section titles, and tests that confirm key concepts appear in DOCX, PDF, and HTML output.
- Example output regression tests should use `tests/example_regression.py` to check rendered bundles, DOCX structure, PDF text/page counts, and HTML internal anchors so examples act as output contracts.
- Example scripts should read like examples, not defensive libraries. Prefer a direct, serialized workflow that shows ordinary Python values becoming document objects; avoid extra wrappers, optional branches, and defensive checks unless they teach something important or the example genuinely needs them.
- Release versioning rule from 1.0.0 onward: bump the major version for public
  breaking changes, minor for backward-compatible features, and patch for fixes.

## Local Environment Notes

- This project requires Python 3.11 or newer. On this Windows machine, prefer `py -3.11 ...` when checking the minimum supported version.
- `pytest` may not be on PATH. Prefer `py -3.11 -m pytest ...` for minimum-version test commands.
