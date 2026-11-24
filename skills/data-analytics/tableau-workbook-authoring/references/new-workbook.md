---
description: "How to build a new workbook when there's no starting workbook and no catalog match: the inputs to resolve and how to write the TWB."
last_updated: 2026-11-22
---
# New workbook route

Read this reference only when the user wants a workbook with no existing
workbook as a starting point, and the chart catalog has no matching
`tier: executable` resource (see [`catalog-templates.md`](catalog-templates.md);
check `list` before assuming no match).

## Resolve required inputs

Resolve these before authoring:

- **Published datasource:** search/list datasources and inspect its metadata.
  Never invent field names, roles, types, or captions.
- **Requested views:** establish the chart types, fields, filters, layout, and
  dashboards. Ask only about ambiguities that materially change the result.
- **Destination project:** resolve its project LUID. Run independent datasource
  and project lookups in parallel when supported.

## Author the TWB

Build a datasource block that references the real published datasource, a
worksheet per requested chart, and the requested dashboard zones. Keep all
names unique and all datasource, worksheet, and zone references consistent.

Use an existing nearby Tableau XML pattern when available. For a genuinely new
construct, check its schema in `references/schemas.tar.xz` (members are named
`YYYY_R/twb_YYYY.R.0.xsd`; read one with Python's `tarfile`), but pick the schema by the workbook's
build, not its `version` attribute (Tableau leaves that at `18.1`):
`validate_workbook.py` reports the schema it chose from `source-build`, and a
workbook built from the starter uses `2026_2`.
Don't use a schema newer than the target server's Tableau version, and look up
only the element you need rather than loading the entire XSD.

Return to `SKILL.md` for local validation, direct publish, and rendering.
