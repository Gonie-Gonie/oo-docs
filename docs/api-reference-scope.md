# API Reference Scope

The API Reference owns per-symbol lookup material. It is not a second User
Guide and should stay short, searchable, and copy-friendly.

API Reference responsibilities:

- Public symbol signatures.
- Constructor and function input arguments.
- Name-value and keyword arguments.
- Return values.
- Raised exceptions.
- Short runnable examples.
- Related symbols.
- Class properties and methods.
- Source locations only in review/evidence profiles or explicit source-enabled
  help output.
- Coverage and inventory evidence as separate sidecars or evidence artifacts.

Overlap prevention rules:

- API Reference category introduction must be short.
- API Reference examples must be per-symbol and minimal.
- API Reference must not contain long conceptual chapters.
- API Reference must not repeat the User Guide reading map.
- API Reference must not expose local absolute source paths in the default
  user-facing help profile.
- API Reference must not append uncategorized API inventory by default.
- Coverage tables belong in CI/review evidence output, not the default
  user-facing reference.
- API Reference may link to the User Guide for workflow-level explanations.
