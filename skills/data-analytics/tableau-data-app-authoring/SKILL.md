---
name: tableau-data-app-authoring
display_name: "Tableau Data App Authoring"
author: "Salesforce, Inc."
icon: assets/icon.svg
created_date: "2026-11-21"
last_updated: "2026-11-22"
description: Build and publish a Tableau data app, a custom viz-extension web app that queries a published datasource live, or a data file embedded in the workbook. Scaffolds the app with the scaffold-data-app MCP tool, writes its query and visualization from the user's criteria or vibe, then packages it as a .twbx for the user to upload to Tableau. Requires scaffold-data-app, which may be unavailable depending on the user's site role, site settings, or Tableau Server version; don't invoke this skill unless it is available. Use to create, build, vibe-code, or publish a data app. Not for native workbooks or dashboards built from marks, Show Me, or the chart catalog (tableau-workbook-authoring), or for opening existing content, including published data apps (tableau-content-viewer).
id: "5cadb40b-e13c-4d5f-8d52-dd977ea441e0"
checksum: "sha256:1f46c6877f04116fd17a8ba80f14a16c925e5073a70201f5e2aca4ec8851c5e1"
---

# Tableau Data App Authoring

Builds a Tableau data app from nothing to a packaged `.twbx` that the user
uploads to Tableau; see Running in Amazon Quick.
Walk the stages top to bottom — every request follows all five, in order.

```
Scaffold + finalize  →  Wire datasource*  →  Author (you)  →  Package  →  Hand off
```

\* Wiring is a prerequisite to a *working* app: the name-only `scaffold-data-app`
ships an empty `<datasources/>`, so a scaffolded app reaches no datasource at
runtime and renders "no data source found." Wire a datasource into the
`.twb` before authoring against it — see Wire a datasource in below. (Packaging the
starter as-is to prove packaging works does not need it.)

**Already have a built app locally?** Skip straight to whichever applies:
**Package into a .twbx** (unpacked `<App Name>/` folder) or **Hand off the file**
(already a `.twbx`) — but first confirm the `.twb`'s `<datasources>` is
actually wired (not empty) and the package layout is correct, since none of
this skill's tooling has run against it.

**Modifying an existing app?** Read every file in its `Resources/.agents/`
first (unzip a `.twbx` to reach it). Those docs hold the app's spec, design,
and past decisions; if `README.md` is the only file, none have been written yet.

**Division of labor: you write ALL the code, every stage, always — including
`app.js`.** The human "vibe codes" by describing what they want (criteria,
theme, vibe, target insights) — they do not write `app.js` themselves. Read
the two bundled guides before authoring: [Design a data app](references/design-data-app.md)
(what to build) and [Build a data app](references/build-data-app.md) (how, using this
skill's local tools). Only skip authoring `app.js` if the human explicitly says
they want to write it themselves for this app (rare) — see the exception at
the end of Author `app.js` below.

**External APIs can come up at any point.** If the user asks for a
third-party API, remote images, or any other outside host, whether at the
start or after the app is already published, run Add external origins
below, then re-package and hand it off again. Read Security best practices first.

There's no separate validation stage — Tableau checks the workbook when it's
published. Get package *layout* right (see Package into a .twbx) or the
workbook won't open at all.

## Running in Amazon Quick

Quick has no shell, so every step below runs as Python in Code Execution, where
the skill's scripts are importable by name.

- **Run the scripts in Code Execution,** not Run python on device, which can't
  import them. Code Execution blocks `subprocess`, `inspect`, and changes to
  `sys.path`. Import the script by name and pass its command-line arguments to
  `main()` as a list of strings; setting `sys.argv` doesn't reach the script. A
  script that fails prints a `✗` message and raises `SystemExit`, so catch it.
  Each step below gives the exact call.
- **Keep the work in the Code Execution workspace,** under
  `os.path.join(WORKSPACE_DIR, "dataapp")`. Write JSON files such as
  `plan.json` with `json.dump`. Quick saves each Tableau tool result as a JSON
  file under `WORKSPACE_DIR/tools/`, one folder per tool, so you can load a
  result from there instead of retyping it.
- **Download links with Quick's Download file tool.** Code Execution and Run
  python on device can't reach the internet, so `curl`, `urllib`, and
  `requests` fail in both. Download file saves into `WORKSPACE_DIR/downloads/`.
- **Quick can't publish the app.** The hosted Tableau MCP server accepts a
  workbook only as a staged upload, an HTTP PUT of the file to the link
  `request-workbook-upload` returns, and nothing in Quick can send one:
  Download file only downloads. So don't call `request-workbook-upload` or
  `publish-workbook`. Build the app all the way through packaging, then hand
  the `.twbx` to the user to upload (see Hand off the file). Don't mention
  publishing or uploading before then.

## Preflight requirements

Complete this preflight before designing, scaffolding, coding, or creating
application files.

### Publishing access

This workflow requires the connected Tableau user to have:

- a Creator or Explorer (can publish) site role; and
- permission to publish to the target project.

Do not treat a generic Explorer license as sufficient: the user must have the
Explorer (can publish) site role or equivalent publishing capability.

Use Tableau metadata or permission information already available in the task
when it conclusively establishes publishing access. If the user's site role or
publishing access cannot be determined through the available Tableau tools,
ask the user to confirm that they have Creator or Explorer (can publish) and
permission to publish to the target project.

Do not begin substantive data-app work while this prerequisite remains
unconfirmed.

### Required Tableau MCP capabilities

Before beginning substantive work, verify that all of the following are
callable:

- `scaffold-data-app`.

The publishing tools aren't needed: in Amazon Quick this workflow ends with the
packaged `.twbx` for the user to upload (see Hand off the file).

Interactive rendering is not required. It's the recommended way to verify the
published app with the user, but never block on it: when it isn't available,
open the published app in an embedded browser if you have one available or
encourage the user to open and verify it in their own browser instead.

When the app will use a published datasource, also verify that the tools needed
to resolve that datasource and inspect its metadata are callable.

A capability is not unavailable merely because it has not yet been loaded.
Perform one focused availability lookup for a missing capability when
necessary.

If `scaffold-data-app` is unavailable, stop and report the missing capability.
Do not hand-build or substitute for its scaffold.

If any other required capability is unavailable, stop before scaffolding or
authoring and tell the user exactly which capability is missing and why it
prevents completion. Don't present the packaged, unpublished app as published.

## Scaffold and finalize the workspace

Call the `scaffold-data-app` MCP tool with the app name:

> scaffold-data-app({ datappName: "Sales Demo" })

The preflight must establish that `scaffold-data-app` is callable. If the tool
is present but the scaffold call fails, report the error and stop. Do not
hand-build the template or substitute another scaffold.

The result carries an un-substituted template **zip** plus a `postUnzip` plan.
The zip arrives as a short-lived link, in whichever of these fields is present;
past the fetch step the steps are identical:

- `downloadUrl` — a short-lived blob-storage link (newer servers).
- `s3URL` — the same thing on older servers.

A `downloadUrl`/`s3URL` link expires about 60 seconds after the call, so
download it **immediately**, before doing anything else. If the download fails
with an expired-link error, call `scaffold-data-app` again for a fresh link.

The result also carries:

- `allowedOrigins: string[]` — the external origins the site lets data apps
  reach. May be empty, in which case the app can't fetch any external origin.
- `requestedOrigins` — which file declares the origins the app requests
  (`file`) and how to write them (`instructions`). Every origin you put there
  must also appear in `allowedOrigins`; see External origins below.

Apply the plan deterministically with the bundled script — applying it freehand
leaves half-replaced `TODO-MANIFEST-ID` / `TODO App Name` / `TODO Sheet Name` tokens or interleaves
edits and renames in the wrong order.

Finalize the plan (fetch, save, apply). Fetch first — the link expires. The
scripts referenced below live under `scripts/` and run in Code Execution, as
Running in Amazon Quick describes:

1. Fetch the template. With `downloadUrl` (or `s3URL` on older servers),
   download it right away with Quick's Download file tool, named
   `template.zip`. Then unzip it in Code Execution:

   ```python
   import os
   import zipfile

   WORK = os.path.join(WORKSPACE_DIR, "dataapp")
   template = os.path.join(
       WORKSPACE_DIR, "downloads", "template.zip"
   )  # where Download file saved it
   os.makedirs(os.path.join(WORK, "unzipped"), exist_ok=True)
   zipfile.ZipFile(template).extractall(os.path.join(WORK, "unzipped"))
   print(os.listdir(os.path.join(WORK, "unzipped")))
   ```

2. Save the plan: write the result's `postUnzip` object to `plan.json`
   unchanged. Load it from the scaffold result Quick saved under
   `WORKSPACE_DIR/tools/` rather than retyping it; the `find` tokens must match
   byte-for-byte.

   ```python
   import json
   import os

   WORK = os.path.join(WORKSPACE_DIR, "dataapp")
   post_unzip = {}  # the scaffold result's postUnzip object, unchanged
   with open(os.path.join(WORK, "plan.json"), "w", encoding="utf-8") as f:
       json.dump(post_unzip, f)
   ```

3. Apply the plan (edits first, then renames; verifies no placeholders
   survive):

   ```python
   import os
   import apply_plan

   WORK = os.path.join(WORKSPACE_DIR, "dataapp")
   try:
       apply_plan.main([os.path.join(WORK, "unzipped"), os.path.join(WORK, "plan.json")])
       rc = 0
   except SystemExit as exc:
       rc = exc.code
   print("exit code", rc)
   ```

   `apply_plan.main()` prints the finalized workspace root. See
   its header comment for the full contract; it hard-fails if a `find` token is
   missing (the zip is stale / out of sync with the plan) rather than emitting a
   broken workspace.

At the end of this stage you have a finalized workspace directory:
```
<App Name>/
  <App Name>.twb
  Packages/com.tableau.mcp.<slug>/
    manifest.json           ← requestedOrigins lives here
    extensions/data-app.trex
    content/index.html
    content/src/app.js      ← the authoring surface
    content/src/styles.css
    content/src/tableau.extensions.1.latest.min.js
  Data/.gitkeep             ← placeholder; embedded datasource files go here
  Resources/.agents/README.md   ← which agent docs travel with the workbook
```

**Sheet name:** the worksheet is named after the app's display name. It's a
plain string with no hash/join-key involved, so it's freely hand-editable at
any point before packaging — edit all 3 matching locations in the `.twb` to
the same new value: the `<worksheet name='...'>` tag, the `<window class='worksheet'
name='...'>` tag, and `<referenced-view ... viewId='...' />`.

### External origins

The extension sandbox blocks every external origin the package doesn't
declare. To let the app reach one (an API, an image host), run Add external
origins below: `declare_origins.py` writes it to the file named by the scaffold
result's `requestedOrigins.file` (the package's `manifest.json`), in the format
its `requestedOrigins.instructions` gives, and fails unless the origin is in the
result's `allowedOrigins`. If `allowedOrigins` is empty, the app can't fetch any
external origin: tell the user the site admin must allow the origin first, or
design the app without it. Don't request origins the app doesn't use.

## Wire a datasource in

The scaffolded `.twb` ships an **empty `<datasources/>`** (both at the workbook
root and inside the worksheet `<view>`). At runtime the app calls
`getAllDataSourcesAsync()` and finds nothing → it renders **"no data source found
in the workbook."** To query live data the workbook must have a real datasource
wired in — this stage is a prerequisite for a working app.

Do this once the user has told you what to connect to; it is skippable if the
user only wants to publish the starter to prove packaging. Only add, remove, or
swap datasources the user asked for; if you think a different or extra
datasource would help, ask first.

The app queries either kind of datasource, in any mix:

- **Published:** a datasource that already exists on the server (a `sqlproxy`
  connection, resolved live by VDS). Its identity can come straight from the
  user, or be reused from a datasource already wired into some other existing
  workbook (see Reuse an existing workbook's datasource below).
- **Embedded file:** a data file the user supplies, copied into
  the workspace's `Data/` folder and packed into the `.twbx` (see Embedded
  file datasource below).

Do **not** hand-edit the XML — the anchors must be filled atomically with a
matching join key across multiple coordinated locations, or the app silently
reaches no data. Use the bundled wiring script.

**Published datasource:** the wiring spans four coordinated locations (root
datasource `name`, root `relation connection`, view `datasource name`,
`datasource-dependencies datasource`) that must all carry the identical
`sqlproxy.<hash>` join key. Use `scripts/wire_datasource.py`, which does all
four edits atomically and hard-fails rather than emitting a half-wired workbook.

**More than one datasource:** wire them all in **one run** — the script fills
the empty anchors once, so it can't add another datasource to an already-wired
`.twb` (re-scaffold instead). It lists every datasource on the app's sheet,
which is required: the server only connects datasources listed there, so a
datasource placed only on some other sheet fails at query time. Don't move
datasources onto separate sheets afterward.

1. **Get the datasource's identity** with `list-datasources` (LUID, name/caption,
   contentUrl) and `get-datasource-metadata({ datasourceLuid })`
   (field names + datatypes). The published DS **contentUrl** is the
   `repositoryId`. (To reuse an existing workbook's datasource instead, see
   Reuse an existing workbook's datasource below — it gets you here, then
   continues at step 2.)
2. **Write a descriptor** listing *only the fields the app will query* (name +
   datatype + role), saved as `descriptor.json` in the work folder. One
   datasource:

   ```python
   import json
   import os

   WORK = os.path.join(WORKSPACE_DIR, "dataapp")
   descriptor = {
       "caption": "<Friendly Name>",
       "repositoryId": "<published DS contentUrl>",
       "fields": [
           {"name": "Profit", "datatype": "real", "role": "measure"},
           {"name": "Region", "datatype": "string", "role": "dimension"},
       ],
   }
   with open(os.path.join(WORK, "descriptor.json"), "w", encoding="utf-8") as f:
       json.dump(descriptor, f)
   ```

   Several datasources (any number) go in a `datasources` array, **primary
   first**, with nothing else at the top level; each entry has the same shape
   as the single-datasource object:

   ```json
   { "datasources": [ { "caption": "Orders", "...": "..." },
                      { "caption": "People", "...": "..." } ] }
   ```

   The primary is the sheet's main datasource. The app reaches every one by
   caption via `getAllDataSourcesAsync()` — look each up by `name`, never by
   position (the list isn't returned in wiring order).

   Captions must be distinct. A caption is only this workbook's display name;
   the server matches the published datasource by `repositoryId`, so if two
   published datasources share a name, give them different captions here
   (e.g. "Sales Orders" / "Finance Orders") rather than renaming them on the
   server.

3. **Run the wiring script** (it prints the wired `.twb` path, and generates a
   consistent `sqlproxy.<hash>` unless you supply `connectionName`). The
   `.twb` is in the folder `apply_plan.main()` printed:

   ```python
   import os
   import wire_datasource

   WORK = os.path.join(WORKSPACE_DIR, "dataapp")
   twb = os.path.join(
       WORK, "unzipped", "Sales Demo", "Sales Demo.twb"
   )  # <App Name>/<App Name>.twb
   try:
       wire_datasource.main([twb, os.path.join(WORK, "descriptor.json")])
       rc = 0
   except SystemExit as exc:
       rc = exc.code
   print("exit code", rc)
   ```

The script hard-fails if the `.twb` is already wired (re-scaffold, keep your `app.js`),
if an anchor is missing (template drifted),
if any empty `<datasources />` survives, if a join key is missing from where the server
reads it (including the host sheet's view listing every datasource), or
if a `repositoryId`, `caption`, or `connectionName` repeats across datasources.
Trust that failure over patching the XML by hand. `datatype` maps to the column
`type` (`real`/`integer` → quantitative, `date`/`datetime` → ordinal, else
nominal); `role: "measure"` gets a `Sum` aggregation, `dimension` a `Count`.

**Embedded file datasource:** use this when the user hands you a data file
instead of naming a published datasource. The same script wires it (and rejects
file types it can't); the descriptor just has `"type": "file"`.

1. **Copy the file into the workspace** under `Data/`, conventionally
   `Data/Datasources/<file>`. The script fails if the file isn't there, or if
   its path is outside `Data/`.
2. **Write a descriptor.** `file` is the path relative to the `.twb`. `table`
   picks the table in a file that holds several (an Excel sheet); the script
   says when it's needed. Field names must match the column names Tableau reads
   from the file, usually its header row. No `repositoryId`. Save it as
   `descriptor.json` the same way:

   ```json
   {
     "type": "file",
     "caption": "Sample - Superstore",
     "file": "Data/Datasources/Sample - Superstore.xls",
     "table": "Orders",
     "fields": [
       { "name": "Sales",  "datatype": "real",   "role": "measure"   },
       { "name": "Region", "datatype": "string", "role": "dimension" }
     ]
   }
   ```

   To mix it with published datasources, put every entry in one
   `datasources` array (primary first) as above.
3. **Run the wiring script** the same way as for a published datasource.

**Reuse an existing workbook's datasource:** point the Published path above
at a datasource already wired into some *other* already-published workbook,
instead of a fresh published DS. Only applies when that datasource actually
resolves as published — resolve it, then continue in Published datasource
above, picking up at its step 2 (you already have what its own step 1 would
have produced).

1. Find the workbook (`list-workbooks`/`search-content`; ask the user which
   if ambiguous), then call `get-workbook({ workbookId })` and read
   `upstreamDatasources[]` — ask which entry if it lists more than one.
2. Check the matched entry's `datasourceType`:
   - **`"embedded"`**: its data lives inside that workbook, so it can't be
     reused by reference. Ask the user for either a published datasource or
     the source data file, and wire the file as an Embedded file
     datasource above.
   - **`"published"`** — still run the rest of Published datasource step 1
     (`list-datasources` filtered by this LUID, for `contentUrl`, plus
     `get-datasource-metadata({ datasourceLuid })` for fields, whose
     top-level `datasourceType` should also read `"published"` when present),
     then continue at step 2. Filter candidate fields to `columnClass: "COLUMN"`
     (drop `CALCULATION`/`TABLE_CALCULATION`/`BIN`/`GROUP` — those are
     Tableau-computed groupings with no matching raw column). This metadata
     response often includes an explicit `role` (`"DIMENSION"`/`"MEASURE"`)
     per field — when present, lowercase and use it directly instead of
     inferring from `defaultAggregation`; fall back to that heuristic when
     `role` is absent.

## Author `app.js`

**Always author `app.js` yourself — this is the fixed default, not a
fallback.** The human vibe-codes: they describe what they want (criteria,
theme, target insights, audience) and you turn that into the actual
`ds.queryAsync(...)` → chart implementation.

Read [Design a data app](references/design-data-app.md) (what to build) and
[Build a data app](references/build-data-app.md) (how — introspect the
datasource, design the chart, edit `content/src/app.js`, follow the sandbox
rules in its `AUTHOR YOUR APP HERE` comment) and follow that workflow; it is
not restated here. There is no local preview — the visual review happens live
in Tableau, once the app is published.

**Record context in `Resources/.agents/`** when it would help whoever edits the
app next: `spec.md` (what it does, for whom), `design.md` (datasources, queries,
chart choices), `memories.md` (decisions, gotchas, the user's preferences).
Update them when you change the app. Follow the folder's `README.md`: no
secrets, tokens, or personal data (anyone who can download the workbook can
read them), and never put these docs under `Packages/<id>/content/`.

**Exception — the human wants to write `app.js` themselves:** only skip
authoring if the human explicitly says they want to write `app.js` themselves
for this app — an override of the default, not the norm. Stop and hand off:
tell them the workspace path
(`Packages/com.tableau.mcp.<slug>/content/src/app.js`) and point them at
[Design a data app](references/design-data-app.md) and
[Build a data app](references/build-data-app.md) as their own reference.
Resume at Package into a .twbx once they say it's authored.

## Add external origins (any time)

Run this whenever the app needs to reach a host outside its package: the user
asks for an external API (at the start of the session or after the app is
published), or `app.js` calls one. The rules behind these steps (two-part
allowlisting, origin format, CORS) live in
[Calling external APIs](references/external-apis.md).

1. **Get a fresh site allow-list.** Call `scaffold-data-app` again with the
   app's name and use only its `allowedOrigins`; ignore the zip and plan. The
   list from the start of the session may be stale. Save it as `allowed.json`
   in the work folder, loading the array from the result Quick saved under
   `WORKSPACE_DIR/tools/`:

   ```python
   import json
   import os

   WORK = os.path.join(WORKSPACE_DIR, "dataapp")
   allowed_origins = []  # the new scaffold result's allowedOrigins array
   with open(os.path.join(WORK, "allowed.json"), "w", encoding="utf-8") as f:
       json.dump(allowed_origins, f)
   ```

2. **Check every origin you need is on it.** If one isn't, stop and tell the
   user: a site admin has to add it under Settings > Extensions > Extension
   Package Allowed Origins. Don't work around it.

3. **Declare the origins in the package:**

   ```python
   import os
   import declare_origins

   WORK = os.path.join(WORKSPACE_DIR, "dataapp")
   app_dir = os.path.join(
       WORK, "unzipped", "Sales Demo"
   )  # the <App Name> workspace folder
   try:
       declare_origins.main(
           [
               app_dir,
               "--allowed",
               os.path.join(WORK, "allowed.json"),
               "--add",
               "https://api.example.com",
               "https://auth.example.com",
           ]
       )
       rc = 0
   except SystemExit as exc:
       rc = exc.code
   print("exit code", rc)
   ```

   It writes `requestedOrigins` into `Packages/<package id>/manifest.json`,
   merges with origins already declared, and fails if an origin isn't on the
   allow-list or isn't a plain `https` origin. Use `--list` to see what's
   declared and `--remove` to drop an origin the app no longer uses.

4. **Re-package and hand it off again** (Package into a .twbx, then Hand off
   the file). The new policy takes effect only after the new file is
   published over the old one.

## Package into a .twbx

A `.twbx` is a zip of the workspace **contents** with the `.twb` and `Packages/`
at the **archive root** — never nested inside the `<App Name>/` folder. Nesting
is the #1 cause of `NativeException: An unexpected error occurred opening the
packaged workbook` and `PackageValidationException: Package directory contains no
extension .trex files under extensions/`.

Package with `scripts/package_twbx.py`. It hard-fails with a `✗` message if
the workspace isn't packageable; fix what it reports rather than zipping by
hand:

```python
import os
import package_twbx

WORK = os.path.join(WORKSPACE_DIR, "dataapp")
app_dir = os.path.join(
    WORK, "unzipped", "Sales Demo"
)  # the finalized <App Name> workspace folder
try:
    package_twbx.main([app_dir])
    rc = 0
except SystemExit as exc:
    rc = exc.code
print("exit code", rc)
```

It also packs `Data/` and `Resources/.agents/` at the archive root. Under
`Data/`, only the files the `.twb` references are packed. Hidden files are
never packed.

It writes `<App Name>.twbx` next to the workspace dir (pass a second arg to
override), overwriting any existing file, and prints the path for Hand off the file.
It also prints `⚠` warnings for problems that only show up at runtime:
undeclared external origins, package-relative `fetch()`, and secret-looking
keys. They don't stop packaging, but fix them or tell the user
about them before handing it off.

> The template these workspaces come from is already publish-valid (`.twb`
> extension wired into a pane, `.trex` with `author email`, `<resources>` block,
> `<icon>`, `min-api-version`). Packaging is the only structural step you own.

## Hand off the file

In Amazon Quick the skill ends here, with the packaged `.twbx` for the user to
upload. Don't call `request-workbook-upload` or `publish-workbook`.

1. **Copy the `.twbx` to the user's computer.** Copy it from the workspace into
   the user's Documents folder with Quick's file copy tool (its step shows as
   "Copying file"). Give it the path `package_twbx.main()` printed.
2. **Tell the user the app is built and packaged but not published,** and why:
   the hosted Tableau MCP server accepts a workbook only as a staged upload,
   which Quick can't send. Say where the `.twbx` is.
3. **Tell them how to publish it,** with these steps as written:
   1. Go to Home or Explore in Tableau Cloud. Personal Space's New menu has
      no upload option.
   2. Choose New > Workbook Upload and pick the file.
   3. Set Project in the dialog to the project they named, or to Personal
      Space if it's listed. Otherwise pick any project, then move the
      workbook to Personal Space with its Actions > Move.

   Suggest a name no workbook there has yet, unless they mean to replace one.
   The upload is where Tableau validates the workbook; if it reports an error,
   ask for its text. Common causes trace back to `.twb`/`.trex` wiring, not
   packaging. If the app goes in a shared project, viewers need View, Full
   Data Query, and API Access on the workbook.
4. **Offer to check it once they've uploaded it:** find its view with
   `search-content`, call `get-view` with the view's LUID for its URL, and give
   the user that link. Don't call `get-view-image`: for a data app, Tableau
   returns an image of its sign-in page instead of the app. Ask the user to
   open the link and tell you what they see. Tableau may ask them to allow the
   extension the first time it opens. To move the app into a shared project
   afterwards:
   > move-workbook({ workbookId: "<the workbook's LUID>", projectId: "<LUID>" })   → { id, name, projectId }

   If `move-workbook` isn't available, tell the user.

## Limitations and gotchas

### Multiple datasources

`wire_datasource.py` wires any number of published datasources, with these
constraints:

- **One run, all at once.** List every datasource in the descriptor's
  `datasources` array, primary first. The script refuses an already-wired
  `.twb`, so adding a datasource later means re-scaffolding, copying
  `content/src/app.js` into the new workspace, and wiring the full set again.
- **What gets wired.** Each datasource gets its own root `<datasource>` and its
  own `sqlproxy.<hash>` join key (unique across the set), and all of them are
  listed on the host sheet's `<view>` — the server only connects datasources
  listed there. Only the primary gets `datasource-dependencies`; the others are
  reached through `getAllDataSourcesAsync()`.
- **Distinct identities.** `caption`, `repositoryId`, and `connectionName` must
  each be unique across the set, or the script hard-fails. Captions matter
  most: they are how `app.js` finds each datasource.
- **Find by name in `app.js`, never by position.** `getAllDataSourcesAsync()`
  doesn't return datasources in wiring order. The starter's `pickDataSource()`
  takes `list[0]`, so a multi-datasource app must replace it with a lookup by
  `ds.name` (the caption).
- **No blending or joins.** Query each datasource separately with its own
  `queryAsync()` and combine the rows in `app.js`. Don't add blend or
  relationship XML.

### External origins and package hosting

Read [Calling external APIs](references/external-apis.md) before building
anything that leaves the package: it covers what the sandbox blocks no matter
what, allowlisting, CORS, and how to debug a blocked call. What the package
host serves is in [Build a data app](references/build-data-app.md), Sandbox and
lifecycle rules. `package_twbx.py` warns about undeclared origins and
package-relative `fetch()`.

## Security best practices

- **Prefer network-isolated apps.** Build the app so it talks only to Tableau
  through the Extensions API. Every external origin needs a site admin's
  approval and gives data a path out of Tableau. Before adding one, ask whether
  the feature needs it, and tell the user what data would leave Tableau.
- **Keep secrets and credentials out of the package.** Anything in `content/`
  (API keys, client secrets, refresh tokens) can be read by anyone who can
  open or download the workbook. If the user still wants one embedded (e.g. a
  personal demo), tell them that first, keep the workbook out of shared
  projects, and keep the secret out of git. Expect the agent's safety checks
  to ask for explicit approval before publishing or downloading a workbook
  that contains credentials. `package_twbx.py` warns about secret-looking keys.
- **Avoid hardcoding data where possible.** Query the datasource live with
  `queryAsync()` instead of copying rows into `app.js` or a bundled file. If
  data must be hardcoded, tell the user the implications first: it's a
  snapshot that won't refresh, and Tableau's query-time protections, such as
  row-level security policies and user filters, don't apply to it, so every
  viewer sees all of it.

## Non-negotiable limits

- Don't zip the `.twbx` freehand. Use `scripts/package_twbx.py` — it keeps
  `.twb`, `Packages/`, and any `Data/`/`Resources/.agents/` at the archive root, never
  nested under `<App Name>/`.
- Don't apply a postUnzip plan freehand. Use `scripts/apply_plan.py` — edits
  before renames, renames deepest-first, verified; see its header comment for
  the full contract.
- Don't hand-edit the `<datasources/>` wiring. Use `scripts/wire_datasource.py` —
  freehand edits mismatch the join key across its coordinated locations or
  leave an empty `<datasources />` anchor, and the app silently reaches no data.
- Don't hand-edit `manifest.json` to allow external origins. Use
  `scripts/declare_origins.py` — Tableau ignores an array or an
  `allowedOrigins` key without any error, and the app stays blocked.
- Don't assume the scaffold result's zip is already substituted, or skip
  unzip. Whether it arrives as `downloadUrl` or `s3URL`, it's the
  same static, un-substituted template **zip** — unzip it and apply the plan
  before authoring.
- Don't guess `repositoryId`. It's the datasource's `contentUrl` from
  `list-datasources`, not its name or LUID; a wrong one fails at publish.
- Don't hand off `app.js` to the human unprompted. Authoring `app.js` yourself
  is the fixed default — always write it from the human's stated
  criteria/vibe. Only hand off when the human explicitly says they want to
  write it themselves.
