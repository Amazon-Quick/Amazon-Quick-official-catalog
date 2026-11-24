---
description: "How to resolve a name or keyword to one Tableau workbook, view or datasource with search-content, read the results, and present the candidates."
last_updated: 2026-11-22
---
# Search Tableau content

Resolve a name/keyword to a specific piece of Tableau content (workbook,
view, datasource, etc.) via `search-content`, and disambiguate when more
than one result plausibly matches.

Tool names here are the Tableau MCP server's own names. The host may list them
with a server prefix (e.g. `mcp__<server>__search-content`); call the listed
tool whose name ends in the name given here.

## Call `search-content`

```json
{ "terms": "<user's keyword or name>", "filter": { "contentTypes": ["view", "workbook"] }, "limit": 10 }
```

- `contentTypes` is nested under `filter` — not a top-level parameter.
- Pass only the content type(s) the calling skill actually needs (e.g.
  `["workbook"]` for authoring, `["view", "workbook"]` for the content
  viewer). A narrower filter means fewer irrelevant results to disambiguate.
- Keep `limit` small (10–20) — this is for resolving one specific item, not
  browsing.
- Reuse a LUID already resolved earlier in the current task instead of
  searching again for the same content.

`search-content` never returns a URL, only a `luid`. Resolving a
render-ready URL (`get-view`/`get-workbook`) is a separate step — not part
of search.

## Interpret the results

- **Zero results:** report that nothing matched — don't broaden the search
  silently or guess a nearby name. The tool distinguishes "nothing exists or
  you lack permission" from "results existed but were filtered out by server
  config"; relay whichever message it returned rather than treating both the
  same.
- **Exactly one plausible result:** proceed with its `luid`.
- **More than one plausible result:** don't guess — let the user pick.
  Give a numbered list of the possible results and ask the user to reply with
  a number.

## Troubleshooting
If `search-content` returns 429 (rate limited), wait and retry with
backoff: honor a `Retry-After` value if the error gives one, otherwise wait
about 2 s, then 4 s, then 8 s. After three failed retries, tell the user the
search is rate-limited instead of retrying further.

## Presenting the candidates

Build one option per candidate from the fields `search-content` actually
returns — don't invent a distinguishing detail it didn't surface:

- `title` — the name to show.
- `type` — `view`, `workbook`, `datasource`, etc.
- `parentWorkbookName` (for a `view` result) or `containerName` (for other
  types) — which workbook/project it lives in.
- `projectName` — the project, when it helps distinguish two same-named
  items in different projects.
- `ownerName` and `modifiedTime` — tie-breakers when names, types, and
  projects all match.

Ask a short question naming what was searched for, list each candidate with
enough of the fields above to tell them apart, and use the selected
candidate's `luid` for every subsequent call. Never fabricate a name, project,
or URL that wasn't in the search results.
