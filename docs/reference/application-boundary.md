# Application Boundary

OODocs provides reusable document structure, styling, validation, rendering,
schema, and suite primitives. Application vocabulary and business rules stay
in the application repository and are passed to OODocs as ordinary Python
objects.

| Requirement | Existing mechanism and ownership |
|---|---|
| Repeated terminology, version, and date | Define Python variables or use `DocumentSuiteContext.variables`. OODocs does not provide a LaTeX macro engine. |
| Arbitrary TeX source | Rebuild the required document with explicit OODocs blocks or maintain a domain importer outside core. OODocs does not automatically convert arbitrary TeX. |
| Directory tree | Render text with `CodeBlock` or structured entries with an ordinary `Table`. |
| Added/Changed/Fixed/Removed release notes | Compose `Section`, `BulletList`, and `PageBreak`. |
| One workbook's sheet structure | Describe reusable fields with `SchemaCatalog` and present the workbook overview with an ordinary table. |
| Application field type codes, requirement codes, and unit aliases | Define and validate them in the application repository. |
| Cover branding, organization, logo, and funding note | Supply them from the application repository through `CoverPage`, title matter, and ordinary blocks. |
| Simulation-specific result-table layout | Build it in the application repository with `Table`, `TableCell`, `ColumnSpec`, and local helpers. |

This boundary keeps the public API neutral: new core objects are justified by
cross-application document semantics, not by a single workbook, simulator,
branding system, or release process. Python remains the composition and
variable language.
