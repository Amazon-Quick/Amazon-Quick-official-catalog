---
name: tableau-workbook-authoring
display_name: "Tableau Workbook Authoring (Preview)"
author: "Salesforce, Inc."
icon: assets/icon.svg
created_date: "2026-11-21"
last_updated: "2026-11-22"
description: Create, edit, copy, or republish a Tableau workbook by editing TWB XML, then validate and package it for the user to upload to Tableau. Requires Tableau Creator or Explorer (can publish), plus permission to publish to the target project. Use for create, build, edit, modify, copy, republish, or add-chart requests. Do not use for read-only analysis or for just opening/showing an existing view (tableau-content-viewer).
id: "8303ce48-d693-4afb-8524-cb38427e8045"
checksum: "sha256:ac732e6836c35c2e65e03d548ba44da261cb9e35d4dfc41e535f468b570662ff"
---

# Purpose

Build or edit a Tableau workbook — from the bundled chart catalog when the request matches it, otherwise by hand-editing TWB XML — validate it, and hand the file to the user to upload. In Amazon Quick it can't be published through the hosted Tableau MCP server; see Running the bundled scripts in Amazon Quick.

Script paths below are written relative to `<skill-dir>`: resolve it as the absolute directory containing this loaded `SKILL.md`, and don't assume it is the current working directory.

## Running the bundled scripts in Amazon Quick

Run the bundled scripts with Code Execution, where the skill's files are; "Run python on device" can't see them and lacks `lxml`. Code Execution runs Python, not a shell, and it blocks `subprocess` and `inspect`, so a `python3 <skill-dir>/scripts/<name>.py <args>` command in this skill or its references can't run as written. Instead, import the script by name and pass the same arguments to its `main()` as a list of strings. Code Execution already makes the skill's scripts importable, and it blocks `sys.path`, so don't add the folder yourself. `main()` prints what the command would print and returns its exit code. Always pass the list: with no arguments, `main()` parses Code Execution's own command line and exits with a usage error. A bad argument raises `SystemExit`, so catch it:

```python
import tableau_resources

# Same as: python3 <skill-dir>/scripts/tableau_resources.py list --tier executable --query "bar chart"
try:
    rc = tableau_resources.main(
        ["list", "--tier", "executable", "--query", "bar chart"]
    )
except SystemExit as exc:
    rc = exc.code
print("exit code", rc)
```

To read a catalog resource's file, such as a reference template to model a hand edit on, call `tableau_resources.resource_text("<resource-id>")`; it returns the file's text. Don't open the `path` that `inspect` prints: the reference templates under `templates/reference/` and the two large JSON references are packed in `references/reference.tar.xz`, not stored as files.

Code Execution already has `lxml`, which the validator needs, so the scripts need no launcher or install step. Keep the workbook files you edit in the Code Execution workspace (`WORKSPACE_DIR`).

`download-workbook` returns a short-lived link, not the file. Download it right away with Quick's Download file tool (its step shows as "Download file"), which saves it under `WORKSPACE_DIR/downloads/`. Code Execution and Run python on device can't reach the internet, so `urllib`, `requests`, and `curl` fail in both.

Quick can't publish the result. The hosted Tableau MCP server accepts a workbook only as a staged upload, an HTTP PUT of the file to the link `request-workbook-upload` returns, and nothing in Quick can send one: Download file only downloads. So don't call `request-workbook-upload` or `publish-workbook`. After validating, hand the file to the user as Validate and hand off describes. Don't mention publishing or uploading before then.

## Preflight requirements

Complete this preflight before downloading, editing, scaffolding, or creating
workbook files.

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

Do not begin substantive workbook authoring while this prerequisite remains
unconfirmed.

### Required Tableau MCP capabilities

Before beginning substantive work, verify that the Tableau MCP capabilities
needed by the requested workflow are callable:

- for an existing workbook, `search-content` and
  `download-workbook`.

The publishing tools aren't needed: in Amazon Quick this workflow ends with a
validated file for the user to upload (see Validate and hand off).

Interactive rendering is not required. It's the recommended way to verify the
published workbook with the user, but never block on it: when it isn't
available, open the published workbook in an embedded browser if you have one
available or encourage the user to open and verify it in their own browser
instead.

Check only the capabilities relevant to the current request. A capability is
not unavailable merely because it has not yet been loaded; perform one focused
availability lookup when necessary.

If a required capability is unavailable, stop before authoring and tell the
user exactly which capability is missing and why it prevents completion. Do
not create an unpublished workbook while presenting it as completion.

## Resolve the requested Tableau object

Resolve the object the user named before resolving its containing workbook.

- “Dashboard” always means a Tableau `view`. Search with
  `filter: { contentTypes: ["view"] }`.
- After resolving the dashboard view, use its metadata to identify the parent
  workbook, then download that workbook for editing.
- Search with `contentTypes: ["workbook"]` only when the user explicitly names
  a workbook or when no dashboard/view was specified.
- Never substitute a workbook search for a dashboard search.

## Canonical Tableau MCP tools

Call these tool IDs directly when they are available. Do not scan or print the
full tool catalog merely to rediscover their names or schemas.
The host may list these with a server prefix (e.g. `mcp__<server>__search-content`);
call the listed tool whose name ends in the name given here.

- Workbook search:
  `search-content`
  with `{ terms, filter: { contentTypes: ["workbook"] }, limit }`
- View / Dashboard search:
  `search-content`
  with `{ terms, filter: { contentTypes: ["view"] }, limit }`
- Exact project lookup:
  `list-projects`
  with `{ filter: "name:eq:<project-name>", limit }`
- Workbook download:
  `download-workbook`
  with `{ workbookId, includeExtract: true }`
- Publishing (`request-workbook-upload`, `publish-workbook`): not used in
  Amazon Quick; see Validate and hand off.
- Workbook metadata:
  `get-workbook`
- View metadata:
  `get-view`
- Static view render:
  `get-view-image`
  with `{ viewId, format: "PNG", width, height }`.
  If it returns a URL, download it as the very next action, before anything
  else, with Quick's Download file tool. The URL expires quickly; see [`references/rendering.md`](references/rendering.md#download-the-png-immediately).

If a directly named tool is not callable, perform one focused availability
lookup for that tool only. Do not enumerate the entire Tableau or global tool
catalog.

# Routing

- Follow-up edit on a workbook already resolved this task → the fast path below.
- Building or adding a chart:
  1. First run:
     `python3 <skill-dir>/scripts/tableau_resources.py list --tier executable --query "<intent>"`
  2. If the result is empty, immediately follow the hand-edit path below. Do not read `references/catalog-templates.md`.
  3. If a match is returned, read [`references/catalog-templates.md`](references/catalog-templates.md), inspect the match, and use `instantiate` for a new workbook or `inject` for an existing one.
- Adding a breakdown/color split, or a filter, to an existing worksheet (not a whole new chart) → read [`references/field-edits.md`](references/field-edits.md) and use `add-encoding`/`add-filter`. Run `inspect-workbook` first if the field names the user gave aren't confirmed against the workbook yet.
- No catalog match, and no field-level match above, or a genuinely custom construct neither covers → hand-edit the TWB XML per the steps below. Before writing the XML, look for a worked example with `python3 <skill-dir>/scripts/tableau_resources.py list --tier reference --query "<construct>"`, `inspect` the match, and read its XML with `tableau_resources.resource_text("<resource-id>")`. Examples include dashboard filter actions, URL actions, web page zones, and Top N with context filters.
- First edit/republish of an existing workbook this task → resolve it with `search-content` (`filter: { contentTypes: ["workbook"] }`; see [`references/search.md`](references/search.md) for disambiguating multiple matches), then `download-workbook`.
- Brand-new workbook with no starting point and no catalog match → read [`references/new-workbook.md`](references/new-workbook.md) first.
`download-workbook` and interactive rendering may be feature-gated — report a missing tool rather than retrying it.

## Fast path for follow-up edits

Reuse the extracted TWB/TWBX, published workbook ID, project ID, name, and view URL from this task. Make the smallest targeted XML edit, validate once, and hand off the new file as Validate and hand off describes, saying whether it should replace the workbook the user uploaded before or go up as a new copy. Don't re-search, re-download, or re-inspect the whole workbook unless the current artifact is missing or stale.

## Existing workbook, first pass this task

1. Resolve the workbook (and destination project, if named) — reuse LUIDs already known this task; otherwise `search-content` (see [`references/search.md`](references/search.md) for disambiguating multiple matches). Resolve independent lookups in parallel when supported.
2. `download-workbook` with `includeExtract: true` unless this is pure inspection that won't be republished, then download the link it returns right away with Quick's Download file tool. Unzip a TWBX and edit the root TWB.
3. Add or change content: prefer `inject` against a catalog match (see Routing and [`references/catalog-templates.md`](references/catalog-templates.md)); otherwise hand-edit only the affected worksheet/dashboard and its `<datasource-dependencies>`, matching adjacent XML conventions. If the workbook's `<document-format-change-manifest>` has `<SheetIdentifierTracking />` (Superstore's does), each new worksheet needs `<simple-id uuid='{…}' />` right after its closing `</table>` (a sibling of `<table>`, not inside it), and its window needs one as its last child, each with a fresh uppercase GUID; see [Manifest-gated elements](references/xml-troubleshooting.md#manifest-gated-elements). **Skip this step** for a plain copy/republish/move with no requested content change.
4. Validate and hand off (below).
5. After the user uploads it, check it as step 4 of Validate and hand off describes.

If the downloaded package looks incomplete or a dependency is missing, read [`references/package-and-upload-fallbacks.md`](references/package-and-upload-fallbacks.md). For a new XML construct (including adding a parameter to a worksheet), a validation failure, or a publish error such as "The worksheet does not have a valid data source", read [`references/xml-troubleshooting.md`](references/xml-troubleshooting.md).

## Validate and hand off

Skip local validation for unmodified content (plain copy/republish/move) — it's already known-valid. `instantiate`/`inject` check the sheet, field, and datasource references they write, but not the XSD schema. For a hand-edited TWB, after the edit, run the validator in one Code Execution call:

```python
edited = "/absolute/path/to/workbook.twb"  # the TWB you edited
original = "/absolute/path/to/original.twb"  # an unedited copy, kept before editing
try:
    import validate_workbook  # exits 2 here if lxml is missing

    rc = validate_workbook.main([edited, "--baseline", original])
except SystemExit as exc:
    rc = exc.code
print("exit code", rc)  # 0 valid, 1 invalid, 2 setup problem
```

It prints the workbook's version, the schema it chose, and the result.

Pass `--baseline` with an unedited copy of the workbook as downloaded (keep one before editing) so schema and reference errors your edit introduced block, and ones already in the original are dropped. Don't "fix" content you didn't edit to satisfy the validator: Tableau may reject the newer form. Without `--baseline`, for a workbook built from scratch, reference problems are only `reference check:` warnings: fix them in content you wrote, and leave them alone in content you didn't touch.

If the validator exits 2 because it can't import `lxml` or read its bundled schemas, tell the user local validation was skipped and why, and that Tableau validates the workbook again when they upload it. Don't retry.

If validation fails, fix the reported lines/elements and retry once; stop after 10 cycles and report the remaining errors.

For TWBX, check it after rebuilding: `zipfile.ZipFile(path).testzip()` returns `None` when every member is intact (there's no `unzip` without a shell). Then hand it off:

1. Copy the `.twbx` (or `.twb`) from the workspace into the user's Documents folder with Quick's file copy tool (its step shows as "Copying file"). Give it a path that exists in the workspace; list the folder first if you aren't sure.
2. Tell the user the workbook is built and validated but not published, and why: the hosted Tableau MCP server accepts a workbook only as a staged upload, which Quick can't send.
3. Tell them where the file is and how to publish it, with these steps as written:
   1. Go to Home or Explore in Tableau Cloud. Personal Space's New menu has no upload option.
   2. Choose New > Workbook Upload and pick the file.
   3. Set Project in the dialog to the target project.

   Tableau validates the workbook again when it's uploaded. Suggest a name no workbook in that project has yet, unless they mean to replace one: the dialog warns when a name is taken, and uploading anyway replaces that workbook.
4. Offer to check it once they've uploaded it. Find the new sheet's view with `search-content` (`filter: { contentTypes: ["view"] }`, with the sheet's name as `terms`) and use the match whose `parentWorkbookName` is the uploaded workbook. Call `get-view` with its LUID for the URL, and give the user the direct link ([`references/rendering.md`](references/rendering.md#build-a-direct-view-url) says how to build it). Then call `get-view-image` once, download its link right away with Quick's Download file tool, and show the PNG inline in the reply as a Markdown image, `![<sheet name>](workspace/downloads/<file name>)`. Quick displays it only when the path starts with `workspace/`. rendering.md covers an expired link.

Record the workbook/project LUIDs, URL, and local artifact paths so a follow-up can use the fast path.

# Requirements

- Keep worksheet, dashboard, datasource, and zone names unique and consistent.
- Prefer fields already declared in the TWB's `<column>` metadata over inspecting the extract or datasource metadata; `inspect-workbook` (see `references/field-edits.md`) reads exactly that metadata.
- Don't invent field names, roles, or numbers not backed by inspected metadata.
- Don't force-fit a catalog template onto a chart it doesn't match — fall back to hand-editing instead of stretching the closest template.
- When `download-workbook` returns a temporary URL, download it right away with Quick's Download file tool.

# References

- [`references/search.md`](references/search.md) — resolving a name/keyword to a workbook and disambiguating multiple matches.
- [`references/catalog-templates.md`](references/catalog-templates.md) — chart catalog: discover, inspect, and render bundled templates via `scripts/tableau_resources.py`.
- [`references/field-edits.md`](references/field-edits.md) — add a breakdown/color split or a filter to an existing worksheet via `inspect-workbook`/`add-encoding`/`add-filter`.
- [`references/new-workbook.md`](references/new-workbook.md) — brand-new workbook, no starting point, no catalog match.
- [`references/package-and-upload-fallbacks.md`](references/package-and-upload-fallbacks.md) — incomplete TWBX package.
- [`references/xml-troubleshooting.md`](references/xml-troubleshooting.md) — new XML construct (including adding a parameter to a worksheet) or validation/publish failure.
- [`references/rendering.md`](references/rendering.md) — render the published/target view.
