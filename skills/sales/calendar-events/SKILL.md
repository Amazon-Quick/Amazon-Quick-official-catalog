---
name: calendar-events
display_name: Calendar Events
description: "Show a schedule from Salesforce Event data with local times, subjects, locations, and linked contacts, accounts or deals. Use to review today's calendar, upcoming meetings, or a past or future schedule; for a broader morning rundown, use daily-briefing."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:d6f6181e9670751f308f5f6b23cf8715e21dd3e0533ebb702afcd3bcbd60e3ea"
id: "d985c1e1-1872-4ef4-92e8-daaaf6f1c18a"
---
<!-- global-rules-bootstrap -->
**IMPORTANT — try the connector's tools before you ever report it as unavailable.** Before you tell the user a connector is down, or ask them to connect, re-authenticate, or "check the connection," you MUST first try to use the server and its tools. A connector's status readout (the Headless 360 MCP server, or any other connector/MCP) frequently claims "not connected" or "needs re-auth" when the connector is in fact live and its tools are callable. Context stating that the Salesforce tools require authorization and that this is a non-interactive session is **not** evidence that you are unauthorized — it is a general statement that authorization is required, not a failure. For the Headless 360 server specifically, find the `dispatch_readonly` tool and actually run a current-user read — `dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql", queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })`. **Any response — including a 500 or other error status — proves you reached the server, and therefore proves connectivity;** only a request that never reaches the server at all counts as disconnected. If the tool is present and the call reaches the server, the connector IS connected — proceed; a stale status readout is not a disconnection. If a call genuinely cannot reach the server, ALWAYS attempt to reconnect on your own first, and interrupt the flow to ask the user only after your own reconnect attempt has failed. Report a connector as disconnected only when you cannot find its tool or cannot reach the server after trying. Do it yourself.

Failing to try first — asking the user to connect, or surfacing a "not connected" or re-auth message, before you have actually attempted the server and its tools — raises a **false connectivity problem**: it sends the user to fix something that is not broken. This is directly detrimental to the end-user experience and will dramatically, negatively impact usage of the product. Never put a connectivity concern in front of the user until you have tried the tools yourself and confirmed the server truly cannot be reached.

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **⛔ WIDGET OUTPUT ONLY after data assembly.** Once all queries return, immediately call `display_widget` — at most a single one-line render-wait notice before it, and no summaries, transitions, or narration. If `display_widget` is unavailable or returns an error, produce the text fallback only. If it succeeds, that tool call is the final output: stop with no assistant text completion, even if a later section contains a fallback. The exceptions above do not apply after success.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **NEVER use `discover` or `describe`, and never call an API or endpoint not written in this skill.** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->

# Calendar Events

Resolve timezone → compute range (no call) → read Events → render. All dates/times in the user's **local** timezone, not UTC.

## 1. Resolve timezone

Standard field, no grounding needed:

```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { TimeZoneSidKey { value } } } }\"}" })
```

Resolve the IANA zone first. Derive the UTC offset separately at each requested range boundary;
do not reuse the current offset for a future or past boundary. A range that crosses a daylight-
saving transition can therefore have different start and end offsets. Unresolvable → fall back to
UTC (`+00:00`), note it in the output.

## 2. Date range (prompt-only — no dispatch)

Treat the requested period as inclusive local calendar dates. `%START%` is local midnight on the
first day, inclusive. `%END%` is local midnight after the final day, exclusive. Compute each
boundary with the UTC offset that the resolved zone observes on that boundary date.

- **today / tomorrow / yesterday** → that one local date
- **this / next / last week** → Monday–Sunday of that week
- **this / next / last month** → first–last day of that month
- **specific date** → that one local date
- **explicit range** → first and last dates as given, both inclusive; if end precedes start, ask for correction

Always ISO-8601 with each boundary's own offset (e.g. a daylight-saving transition may start at
`-07:00` and end at `-08:00`).

## 3. Read Events

`scope: MINE` already filters to the current user — no Id lookup needed. `%START%`/`%END%` are
Step 2's inclusive-start/exclusive-end ISO boundaries. `%FIRST_DAY%`/`%LAST_DAY%` are the same
inclusive local dates in `YYYY-MM-DD`. `Who`/`What` are polymorphic unions on Event (stable, not
org-specific) — span via inline fragments, never bare:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { or: [ { and: [ { IsAllDayEvent: { eq: false } }, { StartDateTime: { gte: { value: \\\"%START%\\\" }, lt: { value: \\\"%END%\\\" } } } ] }, { and: [ { IsAllDayEvent: { eq: true } }, { ActivityDate: { gte: { value: \\\"%FIRST_DAY%\\\" }, lte: { value: \\\"%LAST_DAY%\\\" } } } ] } ] }, orderBy: { StartDateTime: { order: ASC } }, first: 100) { pageInfo { hasNextPage } edges { node { Id Subject { value } StartDateTime { value displayValue } EndDateTime { value displayValue } ActivityDate { value } Description { value } Location { value } IsAllDayEvent { value } Who { ... on Contact { Name { value } } ... on Lead { Name { value } } } What { __typename ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } Amount { value displayValue } Account { Name { value } } } } } } } } } } \"}" })
```
**Local grounding and summary rule:** Count an Event as deal-linked only when `What.__typename` is `Opportunity`; use returned `What.Id` for the link and `Amount.value` for currency, otherwise use the existing non-deal / unavailable sentinel without inferring from `Name`. Use returned Account facts only when present. The grounded hybrid does not query or display Stage or Close Date because its agenda output does not need them. `Who` is not an attendee collection, so the subtitle contains no attendee count.

**Local range and agenda rule — candidate-derived hybrid:** The two filter branches are one read,
not two requests. For `IsAllDayEvent.value == true`, use returned `ActivityDate.value` for inclusion
and day grouping without timezone conversion; show `All day`. For timed Events, use the converted
`StartDateTime`/`EndDateTime` values and group by the resolved local date. Blank Subject becomes
`(No subject)`; blank related record, Location, or Amount stays unavailable. `pageInfo.hasNextPage ==
true` means the 100-row result is incomplete: say `showing first 100` in the widget caption or text
fallback and ask for a shorter range, never claim a complete total. Do not infer duplicates merely
because Events share a time or related record. This query does not establish logged follow-up,
attendee completeness, readiness, missing prep, or task/activity state.

**Grounded hybrid widget mode:** Keep the native widget and its two source actions, but use the
candidate's factual agenda fields instead of unsupported prep/status claims. Rows contain only Time,
Event, Related to, Location, and Value. The callout identifies the first returned Event in the range
and repeats only its returned time, related record, location, and Opportunity value; it never says
the Event needs prep or that work is missing. Keep the primary `Draft agenda` send-message action
for that exact Event. Include `View in Salesforce` only when an Event Id and returned instance host
produce the exact Event URL; otherwise remove that entire secondary button before rendering. A
successful widget call remains terminal.

Empty `edges` → say "No events found for [range]", don't retry with a broader window unasked.

## 4. Render — widget first

Call `display_widget` immediately after assembling the event list. Do not write markdown first. A
widget success requires a structured widget/UI result. If the tool is unavailable, returns an
error, or returns only a flattened plain-text summary without structured widget/UI content, treat
rendering as unavailable and emit the Step 5 fallback once. Do not mix that fallback with a free-
form summary, correction, or choices. If a structured widget succeeds, that call is terminal.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] Every `{{token}}` placeholder replaced with a resolved literal — no `{{…}}` left, no `{!…}` expressions in the widget definition.
- [ ] No graphs (heatmap/piechart/chart/meter/waterfall count = 0).
- [ ] Datagrid rows contain only `time`, `title`, `related`, `location`, and `value`; no `status` or
  `prep`. `value` is a raw returned number for a deal-linked Event or
  `{ value: 0, display: "—" }` when unavailable.
- [ ] All-day rows use `ActivityDate` and `All day`; timed rows use converted local date/times.
- [ ] `pageInfo.hasNextPage == true` is disclosed as `showing first 100` in `datagridCaption`.
- [ ] The callout names the first returned Event and contains only returned factual values — no
  duplicate, follow-up, readiness, or missing-prep claim.
- [ ] `recordLinkButtons` contains one exact Event link per displayed row and one link per distinct
  returned typed Account/Opportunity when the host is available; no raw Id label. If none can be
  grounded, the complete Record links block is removed.
- [ ] The primary button is `action/sendMessage`. The secondary `action/openLink` button is present
  only with a grounded first-Event URL; otherwise its whole button object is removed.
- [ ] The `display_widget` response is classified by capability: structured widget/UI result →
  terminal success; error/unavailable/plain-text-only result → exactly the Step 5 fallback.

The widget template is embedded below. Call `display_widget` in **dynamic** mode with it. It is a skeleton: replace every `{{token}}` with a fully-resolved literal computed from the events you gathered — this echo path does no expression compilation, so no `{!…}` bindings.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the grounded hybrid calendar widget. Hydrate every {{token}} as a typed literal, then call display_widget once in dynamic mode. Rows use only returned Time, Event, Related to, Location, and typed Opportunity Value. Build {{recordLinkButtons}} only from returned Event and typed Account/Opportunity identities plus the returned instance host; remove the complete Record links block when none are grounded. The callout repeats factual fields for the first returned Event; it never infers prep, readiness, duplicates, or follow-up. Keep the Draft agenda action. Remove the complete View in Salesforce button when no grounded first-Event URL is available.",
  "props": {
    "title": {
      "description": "Page title — the day (e.g. \"Today — Thursday, Jul 24\").",
      "type": "string",
      "example": "Today — Thursday, Jul 24"
    },
    "subtitle": {
      "description": "Caption subhead: Event count, deal-linked count, first start / last end, and resolved timezone.",
      "type": "string",
      "example": "6 events · 4 deal-linked · first at 9:00 AM, last ends 4:30 PM · times in America/Los_Angeles"
    },
    "datagridCaption": {
      "description": "Use 'Schedule, in order' when complete. When pageInfo.hasNextPage is true, append ' · showing first 100; narrow the date range to check for more'.",
      "type": "string",
      "example": "Schedule, in order"
    },
    "datagridRows": {
      "description": "Returned Events in local-day/start order. All-day rows use ActivityDate and 'All day'. Empty array omits the datagrid.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "time": {
            "description": "Event time: a converted local start–end range, or 'All day'.",
            "type": "string"
          },
          "title": {
            "description": "Returned Event Subject; use '(No subject)' when blank.",
            "type": "string"
          },
          "related": {
            "description": "Returned Who and What names joined with a comma; use \"—\" when neither is returned.",
            "type": "string"
          },
          "location": {
            "description": "Returned Event location; use \"—\" when blank.",
            "type": "string"
          },
          "value": {
            "description": "Returned Opportunity amount. Use a raw number only for a typed deal-linked Event; otherwise use { value: 0, display: \"—\" }.",
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "object",
                "properties": {
                  "value": {
                    "type": "number"
                  },
                  "display": {
                    "type": "string"
                  }
                }
              }
            ]
          }
        }
      },
      "example": [
        {
          "time": "9:00–9:45 AM",
          "title": "Cobalt contract walkthrough",
          "related": "Jordan Lee, Cobalt renewal",
          "location": "Video call",
          "value": 1800000
        },
        {
          "time": "All day",
          "title": "Team offsite",
          "related": "—",
          "location": "Main office",
          "value": {
            "value": 0,
            "display": "—"
          }
        }
      ]
    },
    "recordLinkButtons": {
      "description": "One complete tile/button per returned Event and distinct typed Account/Opportunity when an exact instance host and record Id are available. Labels use returned names, never raw Ids. Use an empty array and remove the complete Record links block when no URL can be grounded.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "definition": {
            "type": "string",
            "enum": [
              "tile/button"
            ]
          },
          "attributes": {
            "type": "object"
          }
        }
      },
      "example": [
        {
          "definition": "tile/button",
          "attributes": {
            "label": "Open Cobalt contract walkthrough event",
            "iconName": "open-in-new",
            "variant": "secondary",
            "actions": {
              "click": [
                {
                  "definition": "action/openLink",
                  "attributes": {
                    "url": "https://org.lightning.force.com/lightning/r/Event/00U000000000000AAA/view"
                  }
                }
              ]
            }
          }
        }
      ]
    },
    "calloutVariant": {
      "description": "Use info for the factual first-Event summary.",
      "type": "string",
      "enum": [
        "error",
        "warning",
        "success",
        "info",
        "recommended"
      ],
      "example": "info"
    },
    "calloutTitle": {
      "description": "Factual heading naming the first returned Event in the requested range.",
      "type": "string",
      "example": "First event in range: Cobalt contract walkthrough"
    },
    "calloutDescription": {
      "description": "Returned facts for the first Event: time, related record, location, and typed Opportunity value. Omit unavailable facts and make no readiness or follow-up claim.",
      "type": "string",
      "example": "9:00–9:45 AM · Cobalt renewal · Video call · $1.8M"
    },
    "primaryButtonLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft agenda"
    },
    "primaryButtonMsg": {
      "description": "First-person prompt naming only the exact returned Event.",
      "type": "string",
      "example": "Draft an agenda for the Cobalt contract walkthrough."
    },
    "salesforceUrl": {
      "description": "Exact Event Lightning URL for the secondary openLink. Remove the complete secondary button when the instance host or Event Id is unavailable.",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/r/Event/00U000000000000AAA/view"
    }
  }
}
```
```json
{
  "renderer": {
    "componentOverrides": {
      "$": {
        "type": "mosaic",
        "definition": "tile/widget",
        "children": [
          {
            "definition": "tile/row",
            "attributes": {
              "gap": "sm",
              "align": "center",
              "isWrapped": false
            },
            "children": [
              {
                "definition": "tile/icon",
                "attributes": {
                  "name": "calendar",
                  "size": "xl",
                  "alt": ""
                }
              },
              {
                "definition": "tile/text",
                "attributes": {
                  "text": "{{title}}",
                  "variant": "h1"
                }
              }
            ]
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "{{subtitle}}",
              "variant": "caption",
              "color": "muted"
            }
          },
          {
            "definition": "tile/separator"
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "time",
                  "header": "Time",
                  "type": "text"
                },
                {
                  "key": "title",
                  "header": "Event",
                  "type": "text"
                },
                {
                  "key": "related",
                  "header": "Related to",
                  "type": "text"
                },
                {
                  "key": "location",
                  "header": "Location",
                  "type": "text"
                },
                {
                  "key": "value",
                  "header": "Value",
                  "type": "currency",
                  "align": "right"
                }
              ],
              "rows": "{{datagridRows}}"
            }
          },
          {
            "definition": "tile/column",
            "attributes": {
              "gap": "sm"
            },
            "children": [
              {
                "definition": "tile/text",
                "attributes": {
                  "text": "Record links",
                  "variant": "section-title"
                }
              },
              {
                "definition": "tile/row",
                "attributes": {
                  "gap": "sm",
                  "align": "center",
                  "isWrapped": true
                },
                "children": "{{recordLinkButtons}}"
              }
            ]
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "{{calloutVariant}}",
              "title": "{{calloutTitle}}",
              "description": "{{calloutDescription}}"
            },
            "children": [
              {
                "definition": "tile/row",
                "attributes": {
                  "gap": "sm",
                  "align": "center",
                  "isWrapped": true
                },
                "children": [
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{primaryButtonLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{primaryButtonMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "View in Salesforce",
                      "iconName": "open-in-new",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/openLink",
                            "attributes": {
                              "url": "{{salesforceUrl}}"
                            }
                          }
                        ]
                      }
                    }
                  }
                ]
              }
            ]
          }
        ]
      }
    }
  }
}
```

What each block shows, from data you already have:

- **Header** — an icon + page-title text (`{{title}}`) with `{{subtitle}}`: returned Event count,
  typed deal-linked count, first/last timed boundaries when available, and resolved timezone.
- **Schedule datagrid** (`{{datagridCaption}}`, `{{datagridRows}}`) — one row per returned Event in
  local-day/start order. Columns: Time, Event, Related to, Location, and typed Opportunity Value.
  All-day rows use `ActivityDate`; unavailable values use the existing `—` sentinel. The caption
  discloses `showing first 100` when `pageInfo.hasNextPage` is true.
- **Record links** (`{{recordLinkButtons}}`) — one exact Event button per row plus one button per
  distinct typed Account/Opportunity, only from returned Ids and the returned instance host. Remove
  the whole block when no exact URL is available.
- **One factual callout** (`variant` = `{{calloutVariant}}`, normally `info`) —
  `{{calloutTitle}}` names the first returned Event and `{{calloutDescription}}` repeats only its
  returned time, related record, location, and typed Opportunity value. The primary button sends
  `{{primaryButtonMsg}}` through `action/sendMessage`. Keep the secondary `action/openLink` button
  only when `{{salesforceUrl}}` is grounded; otherwise remove that button object.

**Hydration rules:**
1. Start from the embedded template above — a valid-JSON widget-definition envelope whose leaf values carry `{{token}}` placeholders.
2. Resolve every `{{token}}`. A value that is **only** a `{{token}}` (datagrid `rows`) becomes the resolved **typed** literal — numbers stay numbers, arrays stay arrays. A `{{token}}` **inside** a larger string is interpolated as text.
3. `{{datagridRows}}` is an array with exactly `time`, `title`, `related`, `location`, and `value`.
   Use a raw returned number for typed Opportunity value; otherwise use
   `{ value: 0, display: "—" }`. Do not add status/prep fields.
4. `{{recordLinkButtons}}` is an array of complete `tile/button` objects built from exact returned
   record identity. If it is empty, remove the complete Record links column block.
5. The result is hydrated widget definition (no `{{…}}` placeholders remain). Then call:

```
display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated renderer.json> })
```

**Binding rules:**
- Resolve every `{{token}}` to a literal before calling — numbers stay numbers (`value`), arrays stay arrays.
- Build every row only from the same returned Event node. Use `ActivityDate` for all-day grouping and
  converted date-times for timed Events; never infer duplicate, follow-up, or prep state.
- Datagrid `value` is a raw number only for a typed deal-linked Event; otherwise use
  `{ value: 0, display: "—" }`.
- Build `{{recordLinkButtons}}` only from exact returned Event and typed What identity. Deduplicate
  related-record buttons by object type and Id. Remove the whole Record links block when no returned
  instance host is available.
- Set `{{calloutVariant}}` to `info`. The callout repeats factual fields for the first returned Event.
- The primary button is `action/sendMessage` with a first-person exact-Event agenda prompt. Keep the
  secondary `action/openLink` only with a grounded Event URL; otherwise remove its whole button.
- If `pageInfo.hasNextPage` is true, disclose `showing first 100` in `{{datagridCaption}}`; otherwise
  do not add a truncation claim.
- Treat a flattened plain-text-only tool response with no structured widget/UI content as renderer
  unavailable and emit only the Step 5 fallback. Do not append arbitrary prose or choices.

## 5. Markdown — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

One table per day, times in the resolved local timezone (label `(times in UTC)` if it fell back):

```
# Calendar - [Date Range] (times in [TZ label])

## [Day Name], [Mon DD]
| Time | Event | Related to | Location | Value |
|------|-------|------------|----------|------:|
| [Start]–[End] | [Subject] | [Who, What] | [Location] | [Opportunity Amount] |
| All day | [Subject] | — | — | — |

**Total events:** [N]
```

Group by local day (`##` heading, one table each). All-day rows use returned `ActivityDate` and
`All day`; timed rows use converted local start/end values. Blank Subject → `(No subject)`; blank
related record, location, or typed Opportunity Amount → `—`. Use times such as `10:00 AM` /
`2:30 PM` (12-hour). When `pageInfo.hasNextPage` is true, replace the complete-total claim with
`**Showing first 100 events.** Ask for a shorter period to check for more.` No events →
`No events found for [range].`

## [CUSTOMIZE]

- **Time format:** 12-hour default; switch to 24-hour if preferred.
- **What/Who members:** Step 3 spans `Account`/`Opportunity` (What) and `Contact`/`Lead` (Who) — the common cases. Add another member's inline fragment (e.g. `... on Campaign`) if your org uses it on Event.
