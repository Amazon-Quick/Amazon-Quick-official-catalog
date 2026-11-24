---
description: "How to choose the Tableau MCP tools that list datasources and read their metadata, cover the requested scope, and handle failures."
last_updated: 2026-11-22
---
# Tableau MCP routing

Use the tools exposed in the current session; names and schemas vary by server version and configuration.

## Capability selection

Look for read-only capabilities that can list/search published datasources and retrieve one datasource's metadata by stable identifier. Lineage, usage, and refresh capabilities are optional. Inspect every declared input schema before calling and pass only supported arguments. If the server exposes search rather than list, use a broad query and document that coverage may be incomplete. If it exposes neither inventory nor metadata retrieval, stop execution and explain the missing capability.

## Resolution and coverage

- Match a named source by exact name when possible, then project and owner. Ask if multiple candidates remain.
- Follow cursor/page tokens until scope completion or a documented/requested cap.
- Record returned, profiled, reused, failed, and excluded counts.
- Never translate an omitted property to `false`, zero, empty, or healthy. Use `not assessed`.
- Stable IDs are internal matching keys; omit them from prose unless useful for disambiguation.

## Failures

- Authentication/authorization failure on inventory: stop and explain that the scan could not start.
- Permission failure on one source: skip it for this run and report it as inaccessible.
- Rate limit or transient server failure: honor retry guidance; otherwise retry once with bounded backoff.
- Empty or partial metadata: score only observable checks and list unavailable checks.
- Timeout: continue with other sources; do not silently cache a permanent block.

Never expose tokens, request headers, internal stack traces, or sensitive connection strings.

