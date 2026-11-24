---
description: "How to render a Tableau view: choose the render path, download view images right away, resolve the target view, build a direct view URL, and handle failures."
last_updated: 2026-11-22
---
# Render published Tableau content

Render the published or target Tableau view using the least expensive path
that satisfies the user’s intent. Reuse workbook IDs, view IDs, and URLs
already resolved during the current task.

## Choose the render path

Rendering: use a static image. Reuse workbook IDs, view IDs, and URLs already
resolved during the current task.

1. Static image.
   Give the user the full direct `/t/SITE/views/...` URL as a Markdown
   hyperlink, e.g. `[<view name>](https://HOST/t/SITE/views/WORKBOOK/VIEW?...)`,
   then call `get-view-image` once with `viewId` (the resolved
   view LUID) and `format: "PNG"` and handle the result as described in
   [Download the PNG immediately](#download-the-png-immediately).

## Download the PNG immediately

`get-view-image` returns either an inline image or a
`resource_link` holding a short-lived presigned URL. The URL expires quickly,
so any delay between receiving it and fetching it can lose the render.

- **Before calling**, pick the file name, e.g. `<view-luid>.png`, so
  nothing is left to work out afterwards.
- **Inline image:** it's already in the chat; don't download it.
- **`resource_link`:** downloading it is the very next action. Don't call
  any other tool, read a reference file, write to the user, or reason about
  the result first. Download it with Quick's Download file tool (its step
  shows as "Download file"), passing the link's URL and the file name. It
  saves the file in the Code Execution workspace, under
  `WORKSPACE_DIR/downloads/`. Don't download it from Code Execution or Run
  python on device: neither can reach the internet, so `urllib` and
  `requests` fail there, and neither has a shell for `curl`.
- **Website permission:** Quick may ask the user to allow the image host
  first. The link can expire while that question waits; a download that then
  fails with HTTP 403 needs a fresh link.
- **After downloading**, check the file is a non-empty image, then show it
  to the user inline in the reply, as a Markdown image:
  `![<view name>](workspace/downloads/<file name>)`. Use the part of the path
  Download file returns from `workspace/` on: Quick displays
  `workspace/downloads/<file name>` in the chat, but not
  `downloads/<file name>`. Describing the chart doesn't replace showing it.
- **If the image is Tableau's sign-in page**, the view is most likely a data
  app, a sheet drawn by a viz extension. Tableau's image renderer can't draw
  one and returns its sign-in page instead. Don't retry, and don't copy or
  show that image. Give the direct link and tell the user the app can only be
  seen by opening it in Tableau. When you already know the view is a data
  app, for example because you built it, skip `get-view-image`.
- **If the download fails because the URL expired**, call
  `get-view-image` once more and download the new URL
  straight away. This is the only exception to calling it once. If that also
  fails, treat the PNG path as failed.

## Resolve the target view

Reuse view IDs and URLs already resolved during the current task.

In Amazon Quick nothing is published from the chat. After the user uploads a
workbook, find its view with `search-content`
(`filter: { contentTypes: ["view"] }`, with the sheet's name as `terms`) and
use the match whose `parentWorkbookName` is that workbook. Then call
`get-view` with its LUID for the `url`: `search-content` doesn't return one.

Search or list views only when the current task has not already resolved the
target view.

## Build a direct view URL

Convert a Tableau application-shell URL:

`https://HOST/#/site/SITE/views/WORKBOOK/VIEW`

to:

`https://HOST/t/SITE/views/WORKBOOK/VIEW`

Preserve URLs already using `/t/SITE/views/...` or `/views/...`.

For Pulse metric URLs such as:

`https://HOST/pulse/site/SITE/metrics/METRIC_ID`

preserve the URL unchanged.

For a specific view, merge these query parameters before any fragment:

- `:showVizHome=no`
- `:embed=yes`
- `:toolbar=no`
- `:tabs=no`

Example:

`https://HOST/t/SITE/views/WORKBOOK/VIEW?:showVizHome=no&:embed=yes&:toolbar=no&:tabs=no`

Use `:tabs=yes` only when intentionally rendering a tabbed workbook rather
than one specific view.

## Failure handling

- Attempt each available render path at most once.
- Use this fallback order:
  hyperlink plus `get-view-image` PNG.
- Do not retry tools that report unknown, unavailable, or disabled.
- If the PNG also fails, still give the direct URL hyperlink and briefly
  identify which rendering capabilities were unavailable.
- Do not let rendering failure obscure a successful workbook publication.

## Success criteria

Rendering is complete when one of the following is true:

- the user has the direct URL as a hyperlink and can see a PNG of the view;
- the view is a data app, and the user has the direct URL hyperlink and knows
  to open it in Tableau; or
- every render path failed and the user has the direct URL hyperlink with a
  concise explanation.

Report the rendered view’s name and preserve the workbook LUID, view LUID,
project LUID, and direct URL for follow-up edits.
