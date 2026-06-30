# Public API Policy

OODocs keeps the top-level `oodocs` namespace small enough for first-day use.
The source of truth is `src/oodocs/public_api.py`, and compatibility tests keep
`oodocs.__all__` aligned with that policy.

## Tier Model

| Tier | Meaning | Canonical import path |
|---|---|---|
| Tier 1 core | General document authoring objects and helpers that most users can learn first. | `from oodocs import ...` |
| Tier 2 domain | Focused or advanced workflows that should not crowd the first import surface. | Domain namespaces such as `oodocs.engineering`, `oodocs.review`, `oodocs.positioning`, `oodocs.generated`, `oodocs.apidoc`, `oodocs.media`, and `oodocs.references` |
| Tier 3 internal | Renderer hooks, coercion helpers, normalization helpers, and compatibility details. | Not exported from public `__all__` lists and excluded from user-facing API docs |

## Top-Level Rules

- `oodocs.__all__` is capped by `TOP_LEVEL_EXPORT_LIMIT`.
- Symbols listed in `TOP_LEVEL_SYMBOL_TIERS` must be assigned `core`,
  `domain`, or `internal`.
- Names containing internal helper patterns such as `coerce`, `normalize`, and
  `render_to_` must not appear in the top-level namespace.
- Stale aliases such as `reference`, `Ref`, `math`, top-level importer helpers,
  workflow helpers, and domain-only objects stay out of `oodocs.__all__`.

## Documentation Rules

- README Quick Start examples use Tier 1 imports only.
- Advanced examples import their domain namespace explicitly.
- API Reference pages prefer canonical paths and avoid documenting convenience
  re-export aliases as separate symbols.
- User Guide material explains workflows; API Reference material stays focused
  on symbol lookup, signatures, arguments, return values, examples, and related
  symbols.
