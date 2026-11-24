---
description: "The validator's exit codes and fixes for TWB XML problems: manifest-gated elements, filter references, and parameters in a worksheet."
last_updated: 2026-11-22
---
# TWB XML troubleshooting

Read only for an XML construct not represented in the workbook or after local
or remote validation fails.

The bundled validator auto-detects the workbook version and selects the matching
XSD from `references/schemas.tar.xz`, which packs every bundled schema. Its exit codes are:

- `0`: structurally valid
- `1`: structurally invalid; fix the reported line/element
- `2`: setup problem, missing file/dependency, or unsupported workbook version

Use `--json` only when machine-readable errors help automate a repair.

A clean XSD pass is necessary but not sufficient. It may not catch calculated
field formula errors, dangling datasource/worksheet references, or invalid
connection attributes. In Amazon Quick the user uploads the workbook, so
Tableau's own validation happens then, and the user sees any error it reports;
ask them for its text to make a targeted repair. (Through MCP, a TWB published
with `publish-workbook` returns structured `errors`/`warnings` with line,
column, element, and message.) For a TWBX, Tableau validates
the packaged extract during publish itself, so a failure surfaces as a
publish error rather than a structured findings list; rely on the local XSD
validator and the package-completeness checks before publishing.

When schema inspection is required, use the schema the validator reported (it
is chosen from `source-build`, then the `<!-- build -->` comment, then the
`version` attribute, which Tableau leaves at `18.1`) and search for the failing
element. Do not read unrelated XSD sections, use a schema newer than the target
server's Tableau version, or change the workbook's build stamp solely to use a
newer schema.

### Manifest-gated elements

Tableau accepts `<computed-sort>`, `<manual-sort>`, `<natural-sort>`, and
`<alphabetic-sort>` only when `<document-format-change-manifest>` has
`<SortTagCleanup />`, and `<simple-id>` only with `<SheetIdentifierTracking />`.
With that flag, every worksheet (after `<table>`) and window needs its own
`<simple-id uuid='{…}' />` with a fresh uppercase GUID.
In a workbook without those flags, write the form its other sheets use:
`<sort class='computed' ...>` (same attributes and children) and no
`<simple-id>`. Don't add the flag to someone else's workbook to make your
element pass.

### Filter-reference integrity

When adding or changing a filter, never infer the `groupfilter level` from
the raw field name.

1. Locate or create the target `<column-instance>` in the worksheet's
   `<datasource-dependencies>`.
2. Use that instance's exact `name` consistently:
   - the outer `<filter column='...'>` references the fully qualified instance;
   - `groupfilter level='...'` uses the exact unqualified instance name.
3. Copy the closest existing filter pattern from the same TWB whenever possible.
4. Before packaging, verify every categorical filter's `column`, `level`, and
   `<slices>` references resolve to declared datasource dependencies.
5. Treat XSD validation as structural only. A passing XSD check does not verify
   field, filter, datasource, or dashboard cross-references.

### Parameters in a worksheet

A worksheet that uses a parameter lists the `Parameters` datasource in its
`<view><datasources>`, but Tableau treats the first entry as the sheet's
primary datasource. Always list the data datasource first and `Parameters`
after it, the same order Tableau writes:

```xml
<view>
  <datasources>
    <datasource caption='Superstore' name='sqlproxy.1w05q7c0uf6jgq1gfw6pl0o3rfmw' />
    <datasource name='Parameters' />
  </datasources>
  <datasource-dependencies datasource='Parameters'>...</datasource-dependencies>
  <datasource-dependencies datasource='sqlproxy.1w05q7c0uf6jgq1gfw6pl0o3rfmw'>...</datasource-dependencies>
```

With `Parameters` first, the XSD check still passes but publish fails with
error 400011 "The worksheet does not have a valid data source". On that error,
check this order before changing connections, metadata records, or the
object graph.
