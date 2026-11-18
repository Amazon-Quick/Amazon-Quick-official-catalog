---
description: "Detailed method for <Workflow - Integration Testing>: read-only probes per action connector (knowledge bases are not tested), handling missing tools, and the Word report."
last_updated: 2026-11-12
origin: original
---

# Step 7: Integration testing and report

**Mode:** agentic (the agent invokes the connected integration tools itself).
**Entry:** from Step 6 after extensions, with the action connectors from Step 5
set up. **Next:** end of the workflow (final Word report).

## Goal

**Exercise each action connector by calling its connected tool**, one
integration per turn, with a **read-only** action, capture the real output, and
at the end compile all results into a **Microsoft Word (.docx) report**.

> **Scope: action connectors only.** A knowledge base cannot be tested by
> calling a tool, so this step probes action connectors only, and handles
> knowledge bases only in the report. Tell the admin openly that knowledge bases
> are excluded from the test. In the report, list the knowledge bases that are
> set up under "Integrations set up" with the note "not tested: knowledge bases
> are excluded from integration testing", and leave them out of the summary
> table.

The agent uses the integration tools that are **connected to its own agent
space** (for example a Gmail search tool or a Google Drive list tool) to submit
each read directly, then reports the actual result. The admin gets involved only
when a required tool is **not available** in the agent space; then the agent
explains how to add it in the AWS Quick desktop application.

> **Always offer this step.** Ask first:
>
> ```
> <decision question="Would you like me to run a quick read-only test of each integration we set up, calling the connected tools directly?">
> <option description="I'll invoke each integration's tool with a safe read-only action and report what came back">Yes, test them</option>
> <option>Skip testing</option>
> </decision>
> ```
>
> On **skip**, go straight to the [report](#final-report-word-document) using
> live state only (mark every integration "not tested").

## Rules for testing (read this first)

1. **Read-only only** (Rule 12 in `SKILL.md`). Each probe is a list, read,
   search, or get action. If an integration exposes only mutating tools, mark
   it **not testable (no read-only action available)** and move on.
2. **The agent submits the action through the connected tool.** Call the
   integration tool in the agent space to perform the read (for example, call
   the Gmail tool to list recent messages) and report what it returned.
3. **Check tool availability first (per integration).** Before probing, verify
   the integration's tool is connected to the agent space. If it is **not**
   present, tell the admin how to add it in the desktop application (see
   [When the tool isn't available](#when-the-tool-isnt-available)), mark the
   integration **blocked (tool not connected)**, and continue.
4. **One integration per turn.** Run a single integration's probe, show its
   output, record the result, then move to the next on the next turn.
5. **Capture the real output.** Record a short, sanitized excerpt of what the
   tool returned (for example sender and subject lines, file names, page
   titles) for the report. Keep only what proves the call worked, and redact the
   rest (full message bodies, tokens, personal data).
6. **Consult the integration-specific guide** for the available read actions
   before choosing the probe (see
   [integration guides](#integration-specific-guides)). Dual-capability
   connectors get one probe for their **action** capability only.

## What to test

Enumerate from the **live server state**, not the conversation:

```
quick-admin-buddy-runtime-target___get_tenant_configuration
```

Build the test list from the `action_connector` entries in the per-connector
`integrations` breakdown; the `knowledge_base` entries go only to the report
(see the Goal). Test every enabled action connector for which a connected
read-only tool exists. Service-auth (`service_to_service_oauth` or `api_key`)
connectors may not expose a per-user tool in the agent space (see the `SKILL.md`
Gotchas); if no tool is connected for one, treat it as
[tool not available](#when-the-tool-isnt-available) rather than a functional
failure.

### Dual-capability connectors (knowledge base and action)

`onedrive`, `sharepoint`, `confluence`, and `google_drive` can each be enabled
as **both** a knowledge base and an action connector. Test the **action
capability** only, with a read, list, or search tool call (for example
Drive or OneDrive: list files; Confluence or Jira: search or get).

## Per-integration test procedure

Do this for each integration, one per turn:

1. **Check the tool is connected.** Confirm the integration's read tool is
   available in the agent space.
   - **Available:** go to step 2.
   - **Not available:** follow
     [When the tool isn't available](#when-the-tool-isnt-available); record
     **blocked (tool not connected)**; move to the next integration.
2. **Submit the read-only action through the tool.** Call the connected tool
   with the lightest supported read (see the
   [probe table](#simplest-read-only-probe-per-integration)). Example for
   Gmail: call the Gmail tool to **list the 5 most recent messages** (senders and
   subjects only).
3. **Capture and show the output.** Present a short, sanitized excerpt of what
   the tool returned, and classify the result:
   - **pass**: the tool returned plausible data from the source.
   - **empty-ok**: the call succeeded but there was nothing to return (for
     example no recent messages); still a working integration.
   - **fail**: the tool returned an error; capture the error text.
4. **Record** the integration, capability, tool used, probe, classification, and
   output excerpt for the final report. Move to the next integration.

## When the tool isn't available

If the integration's tool is not connected to the agent space, the integration
usually has not been added to **the desktop application** for the
signed-in user, or needs a sign-in or Re-Connect. Give the admin these steps:

1. Open the desktop application, signed in as the user the connectors were
   shared with (Step 5 `share_with`).
2. Add and enable the integration's tool for the agent (connect the account and
   complete any OAuth sign-in prompt). Only user-auth integrations surface for
   the signed-in user; a service-auth connector that does not appear as a
   per-user tool is recorded as **not interactively testable**, not a failure.
3. If it still doesn't appear, check it is **shared** with this user (re-share
   with `quick-admin-buddy-runtime-target___share_action_connector`) and that
   every required OAuth scope is registered (see
   [Troubleshooting](#troubleshooting)).

Then re-check availability and, if it is now connected, run the probe;
otherwise record **blocked (tool not connected)** and continue.

## Simplest read-only probe per integration

Pick the lightest supported read from the integration's guide:

| Integration | Read-only tool call |
|---|---|
| Gmail / Outlook | List the 5 most recent messages (senders and subjects); read only, never send |
| Google Drive / OneDrive (action) | List files, or read one known file |
| Google Calendar / Outlook calendar | List upcoming events |
| Google Docs / Sheets / Slides | Read one existing document |
| Google Chat / Microsoft Teams | List spaces or channels, or read recent messages; read only, never post |
| Google Meet | List upcoming meetings |
| Confluence (action) | Search or get a page; read only, never create or update |
| Jira (action) | Search issues or get an issue; read only, never create or edit |

Always confirm the exact available read actions in the integration's own guide
before calling the tool.

## Integration-specific guides

- [Atlassian Confluence Cloud](https://docs.aws.amazon.com/quick/latest/userguide/confluence-integration.html) (dual: knowledge base and action)
- [Atlassian Jira Cloud](https://docs.aws.amazon.com/quick/latest/userguide/jira-integration.html)
- [Gmail](https://docs.aws.amazon.com/quick/latest/userguide/gmail-integration.html)
- [Google Analytics](https://docs.aws.amazon.com/quick/latest/userguide/google-analytics-integration.html)
- [Google Calendar](https://docs.aws.amazon.com/quick/latest/userguide/google-calendar-integration.html)
- [Google Chat](https://docs.aws.amazon.com/quick/latest/userguide/google-chat-integration.html)
- [Google Docs](https://docs.aws.amazon.com/quick/latest/userguide/google-docs-integration.html)
- [Google Drive](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-integration.html) (dual: knowledge base and action)
- [Google Meet](https://docs.aws.amazon.com/quick/latest/userguide/google-meet-integration.html)
- [Google Sheets](https://docs.aws.amazon.com/quick/latest/userguide/google-sheets-integration.html)
- [Google Slides](https://docs.aws.amazon.com/quick/latest/userguide/google-slides-integration.html)
- [Microsoft OneDrive](https://docs.aws.amazon.com/quick/latest/userguide/onedrive-integration.html) (dual: knowledge base and action)
- [Microsoft OneNote](https://docs.aws.amazon.com/quick/latest/userguide/microsoft-onenote-integration.html)
- [Microsoft Outlook](https://docs.aws.amazon.com/quick/latest/userguide/microsoft-outlook-integration.html)
- [Microsoft SharePoint](https://docs.aws.amazon.com/quick/latest/userguide/microsoft-sharepoint-integration.html) (dual: knowledge base and action)
- [Microsoft Teams](https://docs.aws.amazon.com/quick/latest/userguide/microsoft-teams-integration.html)

## Example: Gmail (action connector)

Expected behavior, one integration per turn:

1. **Check availability:** confirm a Gmail read or search tool is connected to
   the agent space. If not, tell the admin how to add Gmail in the desktop
   application and mark **blocked (tool not connected)**.
2. **Submit the action through the tool:** call the Gmail tool to list the 5
   most recent messages, returning senders and subjects only (read-only).
3. **Report the output:** show the sanitized sender and subject lines returned,
   classify **pass**, **empty-ok**, or **fail**, and record it for the report.

The agent runs the probe itself; the admin's role is limited to adding a missing
tool or completing a sign-in.

## Final report (Word document)

Once every action connector has been tested (or marked blocked or not tested),
**compile all results into a Microsoft Word (`.docx`) document** and save it to
the working directory (for example
`quick-integration-test-report-<YYYY-MM-DD>.docx`). Generate the file with
**`python-docx`** (install it if needed: `pip install python-docx`). The
document contains:

- **Title and metadata**: account id, Region, date and time, the signed-in AWS
  Quick user the tools ran as.
- **Summary table**: one row per tested action connector, with *Integration,
  Tool used, Probe, Result (pass, empty-ok, fail, blocked, not testable), Output
  excerpt*. Knowledge bases get no row.
- **Integrations set up**: from `get_tenant_configuration` live state, grouped
  by action connector and knowledge base, flagging dual connectors. Mark every
  knowledge base "not tested: knowledge bases are excluded from integration
  testing".
- **Extensions**: installed or skipped (from Step 6).
- **Troubleshooting**: for every `fail` or `blocked` row, the matching guidance
  from [Troubleshooting](#troubleshooting).

Confirm the saved file path to the admin when done. If `python-docx` cannot be
installed in the environment, say so and fall back to a Markdown report with the
same structure, offering to convert it to `.docx` another way.

## Troubleshooting

- **Tool not connected in the agent space, or not visible in the desktop
  application.**
  - It may be **service-auth**, which has no per-user tool by design; confirm
    with `get_tenant_configuration` and mark **not interactively testable**.
  - It may not be **shared** with the signed-in user; re-share with
    `share_action_connector`.
  - The user may need to **sign in or Re-Connect** the integration in the
    desktop application (user-auth integrations require the user's own
    sign-in).
- **`authorization_required`, or sign-in never completes.** A required OAuth
  scope is likely missing from the provider consent screen; the user adds it and
  **Re-Connects** (see the `SKILL.md` Gotchas and the connector's file under
  [`../connectors/`](../connectors/)).
- **Tool call returns an API error.** Capture the error; common causes are a
  wrong **base URL / `domain_url`** (it must be the provider's API base URL, not
  the organization's web domain), bad client credentials, or missing scopes.
  Fix and re-test.
- Point to the integration-specific guide and the connector's file for deeper,
  source-specific troubleshooting.

## Exit criteria

- The admin was offered the test. Only action connectors were probed. For each
  enabled action connector with a connected read tool, the **agent invoked that
  tool** with a read-only action and captured the real output; integrations
  whose tool was not connected were reported as **blocked** with instructions to
  add them in the desktop application; every probe was read-only.
- A **Word (`.docx`) report** was generated in the working directory aggregating
  every result (integration, capability, tool, probe, classification, output
  excerpt), the integrations set up, extensions, and troubleshooting for any
  failures, and its path was confirmed to the admin.
