---
description: "How to list, inspect, instantiate, inject and validate the bundled chart templates with scripts/tableau_resources.py, with flags and failure recovery."
last_updated: 2026-11-22
---
# Chart catalog templates

Read this when adding or building a chart that might match a bundled
template — full CLI flags, mapping/parameter syntax, and failure recovery for
`scripts/tableau_resources.py`. `<skill-dir>` is the absolute directory
containing the workbook-authoring `SKILL.md`, as defined there.

Catalog templates are the required entry point for any chart build/edit that
the catalog covers: run `list` before hand-editing TWB XML. If `list` turns
up no `tier: executable` match for what the user wants, don't force-fit a
mismatched template — fall back to hand-authoring the worksheet per
[`new-workbook.md`](new-workbook.md) or the direct XML edit steps in
`SKILL.md`.

## Workflow

1. Run `list` before choosing a chart — never guess a resource id.
2. Run `inspect` before mapping fields — it returns the required field,
   parameter, and datasource contract for that resource. Each `--map` must
   point at a target field of the same datatype family (below).
3. Treat `tier: reference` resources (examples, corpus entries, schema docs)
   as inspiration only. Only `tier: executable` resources are accepted by
   `instantiate`/`inject`; the CLI rejects the rest.
4. Transform: `instantiate` builds a new workbook from the bundled starter;
   `inject` adds a resource into an existing workbook (from
   `download-workbook`).
5. `instantiate`/`inject` validate their own output before writing it — see
   each command's section below. Run `validate` again only if you need an
   absolute structural check independent of that built-in gate.
6. Continue with `SKILL.md`'s "Validate and hand off" section.

## Quick reference

```bash
python3 <skill-dir>/scripts/tableau_resources.py list --tier executable --query "<intent>"
python3 <skill-dir>/scripts/tableau_resources.py inspect <resource-id>
python3 <skill-dir>/scripts/tableau_resources.py instantiate <resource-id> \
  --datasource-definition <file> --output <file> --worksheet-name <name> \
  --map SOURCE=TARGET --param NAME=VALUE
python3 <skill-dir>/scripts/tableau_resources.py inject <resource-id> \
  --input <existing.twb> --output <file> --datasource <name> \
  --worksheet-name <name> --map SOURCE=TARGET --param NAME=VALUE
python3 <skill-dir>/scripts/tableau_resources.py validate --input <file>
```

## Catalog shape

Every entry in `references/catalog.json` has:

- `id` — stable identifier, e.g. `insights__bar_chart`.
- `type` — `template`, `example`, `reference`, or `starter`.
- `tier` — `executable` (renderable via `instantiate`/`inject`) or
  `reference` (inspiration only — corpus entries, worked examples, schema
  docs). Passing a `reference`-tier id to `instantiate`/`inject` fails
  closed with "is reference-only and cannot be rendered".
- `family` — grouping such as `pulse-insights`, `magnitude`,
  `change-over-time`, `distribution`, `ranking`, `deviation`, `correlation`,
  `flow`, `part-to-whole`, `spatial`, or `null` for ungrouped resources.
- `datasources` — the donor datasource name(s) a template's bookmark
  references. `instantiate`/`inject` renders against a single donor.
- `fields` — the donor fields a template places on a shelf
  (`sourceField`, `role`, `derivation`, `shelf`). These are the field
  mappings `--map` must satisfy.
- `parameters` — typed contracts (`date`, `enum`, `number`, `string`) for
  every `{{PARAMETER}}` token the bookmark declares. `--param` must satisfy
  every `required: true` entry.

## `list` — discover before choosing

```bash
python3 <skill-dir>/scripts/tableau_resources.py list \
  --query "rank products by revenue" \
  --family pulse-insights \
  --type template \
  --tier executable \
  --format text
```

All filters are optional and exact-match except `--query`, which tokenizes
and matches against id, intent, family, and keywords. Omit `--tier` to see
reference material too, but never pass a reference-tier id to a transform
command.

## `inspect` — read the contract before mapping

```bash
python3 <skill-dir>/scripts/tableau_resources.py inspect insights__bar_chart --format text
```

Returns the full catalog entry: donor datasource, every source field with
its shelf/role/derivation/datatype, and every parameter's type (and `allowed`
values for `enum`). Use this output to build the `--map` and `--param`
arguments — never invent a field name or parameter value from memory.

## Datatype compatibility

A `--map` may only point a source field at a target field in the same
datatype family:

| Family | Tableau datatypes |
| --- | --- |
| numeric | `integer`, `real` |
| temporal | `date`, `datetime` |
| string | `string` |
| boolean | `boolean` |
| spatial | `spatial` |

Within a family the template survives being repointed — the derivation, the
shelf role, and the mark type stay valid — so only the declared type changes.
Across a family boundary it does not, so the mapping is refused before
anything is written. The datatype each source field expects is the last item
in `inspect`'s `fields` list.

The rendered worksheet declares each mapped field with the *target's* own
datatype and role, read from the target datasource's `<column>` declaration
or, when it has none, from its `<metadata-record>` entry. A target field
whose datatype cannot be determined from either is refused rather than
guessed.

## `--map` / `--param` syntax

Both flags are repeatable — pass one per field or parameter:

```bash
--map SOURCE=TARGET --map "Close Date"="Order Date" --param NAME=VALUE
```

- Each occurrence is exactly one `NAME=VALUE` pair, split on the *first*
  `=` (so a value containing its own `=` is fine).
- Leading/trailing whitespace around both `NAME` and `VALUE` is stripped.
- Neither `NAME` nor `VALUE` may be blank after stripping.
- The same `NAME` cannot appear twice across repeated `--map` (or
  `--param`) flags — a duplicate name fails closed rather than silently
  keeping the last value.

## `instantiate` — new workbook from the starter

```bash
python3 <skill-dir>/scripts/tableau_resources.py instantiate insights__bar_chart \
  --datasource-definition ./my-datasource.xml \
  --output ./workbook.twb \
  --worksheet-name "ARR by Product" \
  --map ARR=Revenue \
  --map "Close Date"="Order Date" \
  --map Product=Product \
  --param DATE_MIN=2024-01-01 \
  --param DATE_MAX=2024-12-31 \
  --param DIRECTION=DESC
```

- `--datasource-definition` must be a file containing exactly one
  `<datasource>` element with a nonempty `name` attribute; that name becomes
  the workbook's target datasource.
- `--map SOURCE=TARGET` maps one donor field (from `inspect`'s `fields`) to
  a field name in your datasource. Supply one `--map` per required field;
  an unknown or missing mapping fails closed.
- `--param NAME=VALUE` supplies one declared parameter. Dates must be
  ISO-8601 (`YYYY-MM-DD`); enums must be one of the `allowed` values.
- Validation for `instantiate` runs against the *clean bundled starter* as
  its baseline. The starter has no pre-existing errors, so there is
  nothing to tolerate: every error in the output is your responsibility.
  This is not a delta check (see `inject`, below) — it behaves like an
  absolute check because the baseline is always clean.

## `inject` — add to an existing workbook

```bash
python3 <skill-dir>/scripts/tableau_resources.py inject insights__line_chart \
  --input ./workbook.twb \
  --output ./workbook-with-trend.twb \
  --datasource "Sample - Superstore" \
  --worksheet-name "ARR Trend" \
  --map ARR=ARR \
  --map "Close Date"="Close Date"
```

- `--output` is a **distinct path** here on purpose: a failed run never
  touches the input workbook. Writing back to the same path as `--input`
  is a deliberate, explicit exception — it requires `--overwrite` so that
  in-place replacement is opt-in rather than the default, e.g.
  `--output ./workbook.twb --overwrite`.
- `--datasource` is the *internal* `name` attribute of a `<datasource>`
  element in the input workbook's own `<datasources>` container — not
  necessarily its on-screen caption. Open the workbook's XML to confirm
  the name if you are unsure. A name the workbook does not have fails
  closed: `Workbook has no datasource named <name> (available: <name,
  name, ...>)`, so you can retry with a value from that list instead of
  guessing.
- Validation for `inject` is a **delta** against the input workbook's own
  pre-existing errors: an inherited error (for example a hidden sheet with
  no window) does not block the run, but any *new* error the injected
  content introduces does. This delta behavior is specific to `inject`;
  the standalone `validate` command below never grants this tolerance.
- `--worksheet-name` must be unique in the workbook; a collision fails
  closed rather than silently renaming.
- Pass `--overwrite` only when you intend to replace the input file itself,
  or an existing output file.

## `validate` — read the errors, don't guess

```bash
python3 <skill-dir>/scripts/tableau_resources.py validate --input ./workbook.twb
```

This standalone command is an **absolute** structural check on the whole
file you point it at: it reports every error the workbook has, with no
tolerance for pre-existing problems. (Delta tolerance is internal to
`inject`'s own pre-write check, above; `instantiate`'s check has nothing
to tolerate because its baseline is the clean bundled starter.)

- Exit code `0` with `[]` means no structural errors.
- Exit code `1` prints a JSON list of stable error codes, in this fixed
  order: `malformed-xml`, `not-tableau-workbook`, `missing-*-container`,
  `unresolved-template-token`, `unresolved-federated-placeholder`,
  `duplicate-worksheet-name: <name>`, `duplicate-window-name: <name>`,
  `worksheet-window-name-mismatch: <name>`,
  `unknown-datasource-reference: <name>`,
  `unknown-field-reference: <datasource>.<field>`.
- Exit code `2` means the command itself failed operationally, before or
  instead of producing that list — for example `--input` does not exist,
  is not readable, or is not valid UTF-8. The error text goes to stderr
  instead of stdout, and there is no JSON list to parse.

This local check is not the same gate as Tableau's own validation when the
user uploads the workbook: this catches structural drift the moment you
produce a file, and the upload is still the final gate before the workbook is
live (see `SKILL.md`'s "Validate and hand off" section).

## Failure recovery

| Error | Cause | Fix |
|---|---|---|
| `Resource <id> is reference-only and cannot be rendered` | Passed a `reference`-tier id to `instantiate`/`inject` | Use `list --tier executable` to find a renderable id, or treat the resource purely as inspiration |
| `Unknown field mappings: ...` | `--map` names a field not in the resource's `fields`/metadata list | Re-run `inspect` and map only the listed source fields |
| `Missing field mappings: ...` | A required source field has no `--map` | Add the missing `--map SOURCE=TARGET` |
| `Missing parameters: ...` / `Unknown parameters: ...` | `--param` doesn't match the resource's typed contract | Re-run `inspect` for exact names, types, and `allowed` values |
| `Parameter <name> must be an ISO-8601 date...` | Bad date format | Use `YYYY-MM-DD` |
| `Datasource <name> has no field named ...` | `--map` target field doesn't exist in the workbook's/definition's datasource | Fix the datasource definition or choose an existing field |
| `Incompatible field mappings: ...` | A `--map` crosses a datatype family, or its target field declares no datatype | Map the source field to a target field of the same family (see *Datatype compatibility*), or declare the target field's `datatype` |
| `Workbook already contains a worksheet/window named <name>` | `--worksheet-name` collides with an existing one | Choose a different `--worksheet-name` |
| `Generated workbook failed validation: ...` | The transform would introduce a new structural error | Read the listed error codes; for `inject`, only *new* errors block, so check the message's "pre-existing errors" list to see what was already broken |
| `Refusing to replace existing file ...` | `--output` exists and `--overwrite` was omitted | Pass `--overwrite` or choose a different `--output` |

## Reference-only resources are inspiration, not input

Resources with `tier: reference` — worked examples in `references/examples/`,
the corpus and schema references in `references/references/`, and any
`reference/*.tbm` template — describe patterns to study when designing a
viz by hand. They are never valid arguments to `instantiate`/`inject`, and
the CLI enforces this: attempting to render one raises `ResourceError`
before touching any file.

In this Quick copy, the `reference/*.tbm` templates and the two large JSON
references are packed in `references/reference.tar.xz`, so their `path` isn't
a file. Read any resource's file with `tableau_resources.resource_text("<id>")`.
