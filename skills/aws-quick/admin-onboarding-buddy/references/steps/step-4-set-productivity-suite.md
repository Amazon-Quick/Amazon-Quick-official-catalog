---
description: "Detailed method for <Workflow - Set Productivity Suite>: asking for the suite, calling set_productivity_suite, and handling suite_conflict."
last_updated: 2026-11-12
origin: original
---

# Step 4: Choose the productivity suite

**Mode:** agentic. **Entry:** from Step 1 or Step 2 once the connector is live
and tested. **Next:** [Step 5](step-5-setup-productivity-tools.md).

## Goal

Record the organization's corporate productivity suite on the backend. This is
the first real configuration call and it **gates every connector operation that
follows**: the server rejects a connector whose suite gate does not match the
stored suite.

Supported suites: **Microsoft 365** and **Google Workspace**.

## Ask

Ask a single question and wait for the answer.

```
<decision question="Which corporate productivity suite does your organization use?">
<option description="Outlook (email + calendar), Microsoft Teams, OneDrive">Microsoft 365</option>
<option description="Gmail, Google Chat, Google Drive, Google Calendar, Docs, Sheets, Slides, Meet">Google Workspace</option>
</decision>
```

Map the answer to a suite value:

- Microsoft 365: `microsoft_365`
- Google Workspace: `google_workspace`

## Apply

Call the backend to persist the suite:

```
quick-admin-buddy-runtime-target___set_productivity_suite  { "suite": "<microsoft_365 | google_workspace>" }
```

Remember the chosen value as `{suite}` for Step 5.

Branch on `Result_Status`:

- **`success`**: suite stored. Confirm using `message`, then **go to Step 5**.
- **`already_configured`**: the same suite was already set. Tell the admin, then
  **go to Step 5**.
- **`validation_failure`**: invalid suite value. Re-ask and retry.
- **`suite_conflict`**: a different suite is already stored and connectors gated
  to it are enabled. Show `data.conflicting_connectors` and ask the admin whether
  to keep the current suite or disable those connectors first (with
  `disable_action_connector` or `disable_kb_integration`) before switching.
  Switch only with the admin's explicit go-ahead.
- **`server_error` or `internal_error`**: surface `message`; offer to retry.

## Exit criteria

- `set_productivity_suite` returned `success` or `already_configured`, and
  `{suite}` is known: **[Step 5](step-5-setup-productivity-tools.md)**.
