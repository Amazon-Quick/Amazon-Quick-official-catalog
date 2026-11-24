---
name: tableau-content-viewer
display_name: "Tableau Content Viewer"
author: "Salesforce, Inc."
icon: assets/icon.svg
created_date: "2026-11-21"
last_updated: "2026-11-22"
description: Show, open, or render an existing Tableau view, dashboard, or workbook live via render-interactive-viz, by name or keyword — for "show me/open/pull up this dashboard/view" requests. Do not use to query or analyze the data behind it or to create/edit/publish a workbook (tableau-workbook-authoring).
id: "05885eda-cbc9-401b-963e-4f2d62493da2"
checksum: "sha256:2e25cc89d9292c278778e32b17c8f4da793b180b7716ab652f65b32f4747135d"
---

# Purpose

Find a specific Tableau view (or workbook) and render it live via `render-interactive-viz`. Never touches a `.twb` file.

Tool names here are the Tableau MCP server's own names. The host may list them
with a server prefix (e.g. `mcp__<server>__search-content`); call the listed
tool whose name ends in the name given here.

# Routing

- Find the content → `search-content` — see [`references/search.md`](references/search.md) for the call shape and how to disambiguate multiple matches. Reuse an already-resolved LUID/URL instead of searching again for the same content.
- Get a render-ready URL → `get-view` (resolved `luid` as `viewId`) or `get-workbook` (as `workbookId`, only when no specific view matched). `search-content` never returns a URL — this call is required.
- Render → `render-interactive-viz` with the resolved `luid` and matching `objectType`. If it's unavailable, give the direct URL as a hyperlink (see [Build a direct view URL](references/rendering.md#build-a-direct-view-url)), then show a static image:
  1. Call `get-view-image` once with `viewId` and `format: "PNG"`. If it returns a link, download it as the very next action with Quick's Download file tool. Code Execution and Run python on device can't reach the internet, and the link expires in about a minute.
  2. Look at the downloaded image. If it's Tableau's sign-in page, the view is a data app, which Tableau's image renderer can't draw: don't retry, and don't copy or show that image. Tell the user to open the link to see the app.
  3. Otherwise show it inline in the reply as a Markdown image, `![<view name>](workspace/downloads/<file name>)`. Quick displays it only when the path starts with `workspace/`.
  4. After the image, give the link and at most a one-sentence takeaway, and nothing else. Don't say that the interactive render isn't available or that the image is static; just show it. Don't repeat the chart's values in text or a table; the user can read them in the image. List them only if the user asks for the numbers.

  [`references/rendering.md`](references/rendering.md) covers the rest, such as an expired link.

# Requirements

- Prefer a view result when the user asked for a view; a workbook-only match is fine only when the user asked for the workbook as a whole.
- Don't fabricate a view/workbook name or URL the search tools didn't surface.
- A missing `render-interactive-viz`/search/content tool usually means a site admin disabled its group (`mcp-apps`/`EXCLUDE_TOOLS`) — that's site config, not a bug.
- If the `download-workbook` tool returns a temporary URL, download the file locally

# References

- [`references/search.md`](references/search.md) — resolving a name/keyword to content and disambiguating multiple matches.
- [`references/rendering.md`](references/rendering.md) — exact render call sequence and URL construction.
