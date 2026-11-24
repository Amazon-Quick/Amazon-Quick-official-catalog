---
description: "How to build a data app: the live-query model, the workflow, writing app.js, sandbox and lifecycle rules, and reviewing the app in Tableau."
last_updated: 2026-11-22
---
# Build a data app — the HOW (workflow + mechanics)

> The **HOW** layer of authoring, adapted for this skill's local MCP tools. Read
> [design-data-app.md](design-data-app.md) first for **WHAT** to build. This file owns the workflow;
> the in-code mechanics (sandbox rules, VDS query shape, safe DOM, Vega-Lite-local) are owned by the
> `AUTHOR YOUR APP HERE` comment block in the scaffolded `content/src/app.js` — follow it there, this
> file only points at it.

## Live-query model (read this first)

**The data app queries its datasource live via the Tableau Extensions API: no data is baked into
the app code.** The shipped app calls `readMetadataAsync()` / `queryAsync()` at view time against the
wired datasource. A published datasource always reflects current data; an embedded file is
packed into the `.twbx` and is current only as of packaging. Two consequences:

1. **The app reaches datasources through the workbook, and queries them directly.** It is a viz
   extension hosted on a worksheet, so it uses
   `tableau.extensions.workbook.getAllDataSourcesAsync()` to reach every datasource wired into the
   workbook, then calls `ds.readMetadataAsync()` / `ds.queryAsync(query)`. It does **not** read
   marks-card summary data and the host worksheet declares **no encodings** — the app builds its own
   VDS query. Results come back in the standard VizQL Data Service shape `{ data: [...] }`; the
   starter's `extractData()` helper reads `result.data` — use it, and match columns by field name
   (not position).
   - **Prerequisite:** the workbook must actually have that datasource wired in. Our name-only
     `scaffold-data-app` ships an **empty `<datasources/>`**, so a freshly scaffolded workbook
     reaches *nothing* at runtime and renders "no data source found." **The SKILL's 'Wire a
     datasource in' stage wires the datasource into the `.twb`** — do that before authoring, or the
     live query has no target.
2. **You cannot run the live query yourself.** A live query only executes inside the Tableau host, so
   you cannot see real rows until the app is published and opened in Tableau. While authoring,
   introspect the datasource with `get-datasource-metadata` / `query-datasource` to design and
   sanity-check the query; do the **visual** review in Tableau **after** publishing.

## Workflow

1. **Detect intent.** Author a real app (beyond the starter) when the user asks to "chart",
   "visualize", "build a dashboard", or otherwise wants a live visual over a specific published
   datasource. Skip it when the answer is a single-value lookup or text and the user hasn't signaled
   interest in a reusable visual — then the starter handoff (the SKILL's 'Author `app.js`' default)
   is enough.
2. **Identify the datasource(s).** Find the target published datasource and its LUID with
   `list-datasources` (ask the user which one if ambiguous). You can wire any number if the app
   genuinely needs them — all in one 'Wire a datasource in' run, primary first. Each LUID drives
   both the `.twb` wiring and your introspection queries. If the user supplies a data file
   instead, copy it into `Data/` and wire it as an embedded file; the SKILL's
   'Embedded file datasource' covers it. In `app.js`, find each datasource by
   `name` (its caption) in `getAllDataSourcesAsync()`, not by position. Query each separately and
   combine results in `app.js` — Tableau data blending doesn't apply, so don't add blend XML.
3. **Introspect the datasource before writing `app.js`.**
   - `get-datasource-metadata({ datasourceLuid })` → fields, data model, parameters. This is the
     field list the app will match by name.
   - `query-datasource({ datasourceLuid, query, limit })` → preview real VDS `{ data: [...] }` rows
     so you can sanity-check the exact query the app will run before you commit to a chart. Match
     columns by field caption/name, not by position.
4. **Author `content/src/app.js`** — see Author `app.js` below.
5. **Package** the workspace into a flat `.twbx` with `scripts/package_twbx.py` per the SKILL's
   'Package into a .twbx' stage.
   There is **no separate validation tool and no local preview** — a `.twbx` cannot be pre-validated;
   Tableau validates when the app is published.
6. **Hand off the `.twbx` for the user to upload** — see the SKILL's 'Hand off the file' stage. In
   Amazon Quick the skill can't publish through the hosted Tableau MCP server, so the user uploads
   the file with New > Workbook Upload. That upload is where Tableau validates the workbook.
7. **Check it once it's uploaded,** if the user asks: find it with `search-content`, get its link
   with `get-view`, and share the link. Tableau's image renderer can't draw a data app.
8. **Review the live app in Tableau** — see Review the live app in Tableau below.

## Author `app.js`

There is no upsert tool — **edit the file on disk.** Inside the `AUTHOR YOUR APP HERE` block, replace
the `renderStarter(...)` call with the real flow:

- Build a VDS query (fields + optional filters/aggregations) and call `ds.queryAsync(query)`.
- Read rows with the provided `extractData()` helper (returns `result.data`); match columns by field
  name.
- Render the rows with the charting library named in the `AUTHOR YOUR APP HERE` block.

Prefer to derive new fields / change data shapes **at query time** rather than in JS. There is no
required file layout, chart count, or palette — a good app clearly addresses the user's objective.
See [design-data-app.md](design-data-app.md) for encoding, narrative, integrity, and color.

## Sandbox and lifecycle rules

The published app runs inside the Tableau viz-extension sandbox, not a browser. The authoritative
rules live in the `AUTHOR YOUR APP HERE` comment in the scaffolded `app.js` and are **not restated
here** to avoid drift. In brief, that comment requires: surface every error on-screen (no visible
console — use the starter's `renderError`); render first / initialize second; **vendor libraries
locally, no CDN** (mirroring how `tableau.extensions.1.latest.min.js` is already vendored and loaded
before `app.js`); prefer 2D (SVG/Canvas/DOM) over WebGL; use safe DOM APIs
(`textContent` / `createElement`), never `innerHTML` with live values.

**Package hosting.** Only web assets under the package's `content/` folder are served. Files at
the package root still go into the `.twbx` but 404 at runtime; hidden files are never packaged.
`fetch()` of package files also fails (see [external-apis.md](external-apis.md), Origin `null`
and CORS), and `package_twbx.py` warns about it. Don't ship data in the package:
publish it as a Tableau datasource and query it, so it refreshes and row-level security and user
filters apply. Small static config can be a `.js` file that sets a global, loaded with
`<script src>` before `app.js`.

**External origins.** Rules: [external-apis.md](external-apis.md). Declare origins with
`scripts/declare_origins.py` (SKILL.md, Add external origins).

## Review the live app in Tableau

There is **no local preview** — the live query only runs inside Tableau. Open the published workbook
(the user's personal space is the natural iteration target) and confirm the viz-extension worksheet
renders the real chart — not "no data source found" ('Wire a datasource in' wiring missing) or "Live
query unavailable" (query/render error). Tableau may show a one-time extension trust prompt on first
load; that's not a failure. Apply the design checks in [design-data-app.md](design-data-app.md) (5-second +
takeaway test). To iterate: edit `app.js` (Author `app.js`), re-package (Workflow step 5), and hand it off
again (Workflow steps 6–7); it then has to be published over the old one.
