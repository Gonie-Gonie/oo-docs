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

- Backward compatibility does not need to be preserved unless the user gives a specific compatibility guide or constraint.
- This project is still in an API-shaping stage. Prefer clear, explicit, maintainable APIs over carrying old names by default.
- Prefer document-level defaults through `DocumentSettings` when a setting should apply consistently across renderers.
- Prefer editable flow primitives for report-like layouts: `Box` + `BoxStyle`, `Table`, `Figure`, and normal paragraphs should cover tcolorbox-style panels, callouts, and form sections before reaching for page-positioned drawing objects.
- The old `Sheet` model is removed. Use `Document(..., page_items=[Shape..., TextBox..., ImageBox...])` for absolute page overlays that do not move body text. Anchors are `page`, `margin`/`content`, or an earlier named `Shape`.
- `Shape`, `TextBox`, and `ImageBox` also support `placement="inline"` so users can insert drawing objects into the body flow in a Word-like "in line with text" mode, similar to direct LaTeX `includegraphics` usage.
- Table authors should choose whether a table may split, not whether it is a normal table or longtable. `Table(split=True)` means here/in-source-order and splittable; `split=False` keeps short tables together but still auto-splits very long tables with repeated headers where possible. `placement=...` on tables and figures is an advanced hint for here/float/top/bottom/page-like behavior.
- Documents now have `validate()` as a preflight API. Validation returns a structured `ValidationResult` that prints as a table, records format scope (`docx`, `pdf`, `html`), and is run automatically before `save*` rendering. Keep future renderer-specific caveats connected to `docscriptor.compatibility` and validation issues rather than scattering ad hoc checks in renderers.
- The CLI entry point is `docscriptor.cli:main`, with `build`, `convert`, and `validate` subcommands. Keep CLI behavior thin over `docscriptor.workflows` so Python API and command-line behavior stay aligned.
- Theorem-like blocks use `CountableBlock` plus `countable_kind(...)`. Built-ins such as `Definition`, `Lemma`, `Proposition`, `Theorem`, `Corollary`, `Example`, `Remark`, `Assumption`, `Axiom`, `Claim`, and `Conjecture` share the document-wide `theorem` counter; `Proof` is unnumbered by default. Custom countable classes should be made with the factory instead of asking users to subclass.
- The usage guide example is the broad user-facing reference. Keep it current when major APIs change; it should show rendered examples, search-friendly section titles, and tests that confirm key concepts appear in DOCX, PDF, and HTML output.
- Release versioning rule: bump the minor version when backward compatibility is not guaranteed; bump only the patch version when backward compatibility is preserved.

## Local Environment Notes

- This project requires Python 3.14. On this Windows machine, use `py -3.14 ...`.
- `pytest` may not be on PATH. Prefer `py -3.14 -m pytest ...` for test commands.
