---
description: "How to add a color, tooltip, label or filter field to an existing worksheet with inspect-workbook, add-encoding and add-filter."
last_updated: 2026-11-22
---
# Field-level workbook edits

Read this when a request needs one small, mechanical change to an existing
worksheet that the chart catalog doesn't cover as a whole template — add a
breakdown/color split, or add a filter — rather than a brand-new chart. Full
CLI flags and failure recovery for `scripts/tableau_resources.py`'s
`inspect-workbook`, `add-encoding`, and `add-filter`. `<skill-dir>` is the
absolute directory containing the workbook-authoring `SKILL.md`.

These commands splice one bounded, verified XML shape into an existing
worksheet — they never invent a new chart type or restructure a view. Each is
deliberately scoped to the field types this module has confirmed against
real Tableau donor XML; anything outside that scope fails closed with a
message pointing back to a hand-edit (see
[`xml-troubleshooting.md`](xml-troubleshooting.md)) instead of guessing at an
unverified shape.

## Workflow

1. Resolve and download the workbook per `SKILL.md`'s "Existing workbook,
   first pass this task" — you need the extracted `.twb` before any of this.
2. Run `inspect-workbook` to see the exact field names, datatypes, and roles
   the target datasource declares. Never guess a field name from the user's
   phrasing — a prompt like "broken down by location" may not match the
   workbook's field name exactly (e.g. `Location` vs `Store Location`); if
   more than one field plausibly matches, ask the user rather than picking one.
3. Add the encoding and/or filter the user asked for with `add-encoding`
   and/or `add-filter`. Each command validates its own output before writing
   — see each section below.
4. Continue with `SKILL.md`'s "Validate and hand off" section.

## Quick reference

```bash
python3 <skill-dir>/scripts/tableau_resources.py inspect-workbook --input <file> --format text
python3 <skill-dir>/scripts/tableau_resources.py add-encoding \
  --input <file> --output <file> --worksheet <name> --field <name> [--channel color|tooltip|label]
python3 <skill-dir>/scripts/tableau_resources.py add-filter \
  --input <file> --output <file> --worksheet <name> --field <name> \
  --filter-type categorical --include <value> [--include <value> ...]
python3 <skill-dir>/scripts/tableau_resources.py add-filter \
  --input <file> --output <file> --worksheet <name> --field <name> \
  --filter-type quantitative --min <value> --max <value>
```

## `inspect-workbook` — read real field names before mapping

```bash
python3 <skill-dir>/scripts/tableau_resources.py inspect-workbook --input ./workbook.twb --format text
```

Returns each datasource the workbook's own `<datasources>` container
declares, with every field's datatype and role (`dimension`/`measure`).
Fields are read from both layers a real workbook may use — an explicit
`<column>` declaration and a physical `<metadata-record>` — so this also
surfaces columns the author never customized. `--format json` (the default)
returns the same data machine-readably.

This is read-only: it never writes a file, and it works on any `.twb`, not
only one this module produced.

## `add-encoding` — add a color, tooltip, or label field to a pane

```bash
python3 <skill-dir>/scripts/tableau_resources.py add-encoding \
  --input ./workbook.twb --output ./workbook-with-breakdown.twb \
  --worksheet "ARR Trend" --field Location

python3 <skill-dir>/scripts/tableau_resources.py add-encoding \
  --input ./workbook.twb --output ./workbook-with-tooltip.twb \
  --worksheet "ARR Trend" --field "Renewal Date" --channel tooltip
```

Splices a `<color column='[ds].[field-instance]' />`, `<tooltip ...>`, or
`<text ...>` (`--channel label` maps to Tableau's own `<text>` tag) into the
target worksheet's single `<table><panes><pane><encodings>`, declaring the
field's `<column>`/`<column-instance>` dependency first if the worksheet
doesn't already carry one for it.

- `--channel` defaults to `color`; `tooltip` and `label` are also supported.
  `size`/`shape` are not implemented — no bundled donor XML verifies their
  column-instance shape.
- `color` requires a **string dimension** field, per `inspect-workbook`. A
  numeric measure, a date, or a boolean field is refused for `color` — hand-
  edit the worksheet for those instead.
- `tooltip`/`label` additionally accept a **numeric or date/datetime**
  field, verified against bundled donor XML (a candlestick chart's stacked
  `<tooltip>` elements, a treemap's stacked `<text>` elements) — a boolean
  field is still refused for every channel.
- The worksheet must have exactly one pane (a trellis/dual-axis worksheet
  with more than one pane is refused — which pane the user meant is
  ambiguous) and exactly one `<datasource-dependencies>` block (a blended,
  multi-datasource worksheet is refused for the same reason).
- A mark has exactly one color, so if the pane already has a color encoding,
  `add-encoding --channel color` refuses rather than guessing whether to
  replace it — remove the existing one by hand first. `tooltip`/`label` are
  additive instead: adding a second (or third) tooltip/label field stacks it
  alongside any that already exist, matching Tableau's own behavior for
  those two channels.
- Only `<encodings>` is touched. A worksheet's `<window><cards>` shelf layout
  (which panel the authoring UI shows) is left as-is; Tableau resynthesizes
  it from the pane's encodings the next time the workbook is opened in
  Desktop, and the rendered view does not depend on it. Confirm the rendered
  color legend/tooltip/label looks right during the render step regardless.

## `add-filter` — add a categorical or range filter to a worksheet

```bash
# Categorical: one or more values to include
python3 <skill-dir>/scripts/tableau_resources.py add-filter \
  --input ./workbook.twb --output ./workbook-filtered.twb \
  --worksheet "ARR Trend" --field "Admission Type" \
  --filter-type categorical --include Readmission

# Quantitative: a numeric or date range
python3 <skill-dir>/scripts/tableau_resources.py add-filter \
  --input ./workbook.twb --output ./workbook-filtered.twb \
  --worksheet "ARR Trend" --field "Length of Stay" \
  --filter-type quantitative --min 1 --max 30
```

Splices a `<filter>` immediately after the target worksheet's
`<datasource-dependencies>` in `<table><view>` — the same position bundled
donor `.tbm` files use — declaring the field's dependency first if needed.

- `categorical` requires one or more `--include` values and a **string
  dimension** field. A single value becomes a bare
  `<groupfilter function='member'>`; more than one wraps each value's
  `member` groupfilter in a `function='union'` groupfilter. Both shapes are
  verified against bundled reference `.tbm` XML. There is no `--exclude` —
  Tableau's exclude-filter shape isn't verified here, so an exclude filter
  needs a hand-edit.
- `quantitative` requires both `--min` and `--max` and a **numeric, date, or
  datetime** field. A numeric field's `--min`/`--max` must be plain numbers
  (`-?\d+(\.\d+)?`); a date field's must be `YYYY-MM-DD`; a datetime field's
  may be either `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`. Any of these is
  written as a `#...#` literal (Tableau's date/datetime-literal delimiter,
  e.g. `#2025-06-30 17:30:00#`). Only an `in-range` (both bounds) filter is
  supported — a one-sided or `non-null`-only filter needs a hand-edit.
- Relative-date filters (e.g. "last 90 days") and boolean-field filters
  aren't implemented — neither has a bundled donor example this module could
  verify the exact attribute shape against.
- Adding a second filter on a field that already has one is allowed; this
  does not check for or dedupe against existing filters.

## Datatype/role scope, at a glance

| Operation | Requires | Instance shape used |
| --- | --- | --- |
| `add-encoding --channel color` | string, `role=dimension` | `[none:<field>:nk]`, `type='nominal'` |
| `add-encoding --channel tooltip\|label` | string, numeric, or date/datetime | `[none:<field>:nk]` or `[none:<field>:qk]` |
| `add-filter categorical` | string, `role=dimension` | `[none:<field>:nk]`, `type='nominal'` |
| `add-filter quantitative` | numeric, date, or datetime | `[none:<field>:qk]`, `type='quantitative'` |

Both commands reuse an existing `derivation='None'` column-instance for the
field when the worksheet's `<datasource-dependencies>` already declares one
(matching by the underlying field, not by name), so a field the worksheet
already uses elsewhere doesn't get a redundant second declaration.

## Failure recovery

| Error | Cause | Fix |
| --- | --- | --- |
| `Workbook has no <worksheet> named ...` | `--worksheet` doesn't match any worksheet in the input | Re-check the name against `download-workbook`'s content or the raw XML |
| `Workbook has N <datasource-dependencies> blocks; expected exactly one` | The worksheet blends more than one datasource | Not supported — hand-edit instead |
| `Workbook has N <pane> elements; expected exactly one` | The worksheet is a trellis/dual-axis view with multiple panes | Not supported — hand-edit the specific pane instead |
| `Datasource <name> has no field named ...` | `--field` doesn't match a declared field | Run `inspect-workbook` for the exact name |
| `... only supports a string dimension field; <field> is <datatype>/<role>` | `--field` is the wrong type for `add-encoding --channel color` or a categorical `add-filter` | Use a string dimension field, or hand-edit for another type |
| `... only supports a string, numeric, or date/datetime field; <field> is <datatype>` | `--field` is the wrong type for `add-encoding --channel tooltip\|label` | Use a string, numeric, or date/datetime field, or hand-edit for another type |
| `... only supports a numeric or date field; <field> is <datatype>` | `--field` is the wrong type for a quantitative `add-filter` | Use a numeric, date, or datetime field, or hand-edit for another type |
| `Pane already has a color encoding; remove it by hand ...` | The worksheet already has a color breakdown | Remove the existing `<color>` encoding by hand first, or pick a different worksheet — `tooltip`/`label` don't hit this, they stack instead |
| `Workbook already declares a column-instance named [...] for a different field` | An unrelated field already uses the exact instance name this would synthesize | Rename or hand-edit; this refuses to reuse a name it didn't create for this field |
| `--min/--max must be plain numbers ...` / `--min/--max must be YYYY-MM-DD ...` / `--min/--max must be YYYY-MM-DD or YYYY-MM-DD HH:MM:SS ...` | Range bounds don't match the target field's datatype | Fix the literal format |
| `Generated workbook failed validation: ...` | The edit would introduce a new structural error | This is a delta check like `inject`'s — only *new* errors block; read the listed codes |
| `Refusing to replace existing file ...` | `--output` exists and `--overwrite` was omitted | Pass `--overwrite` or choose a different `--output` |
