---
description: "Detailed method for <Workflow - Verify Connector>: what to tell the admin, the read-only connector probe, and routing to configure or set the suite."
last_updated: 2026-11-12
origin: original
---

# Step 1: Verify the MCP connector exists

**Mode:** agentic. **Entry:** start of onboarding. **Next:** Step 4 if the
connector is callable, otherwise Step 2.

## Goal

Set the admin's context about what this skill does and how it works, then
determine whether the custom MCP action connector that powers the skill is
already present and callable in the AWS Quick account. If it is, the skill can
call its operations immediately; if not, the admin configures it (Step 2) and
possibly deploys the backend (Step 3).

## What to tell the admin (context)

Open with a short, welcoming framing (a few sentences, not a wall of text) that
covers three things:

1. **What the skill can do.** It sets up AWS Quick for the organization by
   configuring **knowledge bases** (enterprise sources AWS Quick can search) and
   **action connectors** (productivity and line-of-business integrations), one
   step at a time, and applies every choice for real.
2. **How it works.** Summarize <Definition - Backend> in `SKILL.md`: the Quick
   Admin Buddy MCP server on Amazon Bedrock AgentCore, reached from AWS Quick
   through a custom MCP action connector, performs the real configuration.
3. **What has to be in place.** The connector named
   **`Admin Onboarding Buddy Endpoint`** exists in the AWS Quick account, is
   connected, is added to the AWS Quick desktop application (installed, signed
   in, enabled, tools enabled; creating it in the web console does not do this),
   and the skill was opened in a new chat afterwards (Skills,
   `admin-onboarding-buddy`, Try it), because an existing chat does not see a
   newly installed connector. This step checks that.

## Check whether the connector is present

Check in this order and stop at the first conclusive result.

### 1. Try an MCP operation (fastest conclusive check)

Attempt a read-only call to
`quick-admin-buddy-runtime-target___get_tenant_configuration` (no input).

- If it returns a **Tool_Result** (`status` present, for example `success`),
  the connector exists and is connected. Tell the admin it is ready and **go to
  Step 4**.
- If the tool **is available but the call errors** instead of returning a
  Tool_Result (for example HTTP 404 "The requested action was not found for
  this Action Connector"), go to
  [check 1b](#1b-connector-shows-healthy-but-its-actions-fail).
- If the operation is **not available** in the toolset, or the call fails
  because the connection is missing or unauthorized, the connector is not usable
  yet. Continue to check 2 to confirm, then route to Step 2 or Step 3.

### 1b. Connector shows healthy but its actions fail

Diagnose and recover per <Definition - Stale Connector Actions> in `SKILL.md`.
Ask the admin to run **Test** in the AWS Quick web console with this decision:

```
<decision question="In the AWS Quick web console, open 'Admin Onboarding Buddy Endpoint' and run Test on quick-admin-buddy-runtime-target___get_onboarding_summary. Did the Test succeed?">
<option description="The action returned a result in the web console">Test passed</option>
<option description="The action errored in the web console">Test failed</option>
</decision>
```

- **Test failed:** give the recovery paths from <Definition - Stale Connector
  Actions> one at a time (Sync and retest first, then the full rebuild, which
  recreates the connector by following [Step 2](step-2-configure-connector.md)).
- **Test passed:** the connector itself works, so the problem is on the desktop
  application side. **Go to Step 2**, starting at "Make the connector available
  in the desktop application".

### 2. Confirm in the AWS Quick account

Ask the admin to confirm from the AWS Quick console whether a custom MCP
action connector named **`Admin Onboarding Buddy Endpoint`** already exists in
their account's connectors list.

```
<decision question="Do you already have an action connector named 'Admin Onboarding Buddy Endpoint' in your AWS Quick account?">
<option description="It's listed under your action connectors / MCP integrations">Yes, it's there</option>
<option description="No such connector, or you're not sure">No / not sure</option>
</decision>
```

## Routing (exit criteria)

- **Connector present and callable** (the operation returned a Tool_Result):
  **go to Step 4** (choose the productivity suite).
- **Connector healthy in the web console but its actions fail** (the tool is
  visible, the call errors, and the web console **Test** also fails): recover
  only through [check 1b](#1b-connector-shows-healthy-but-its-actions-fail).
- **Connector present but not callable** (listed in AWS Quick but the operation
  fails on auth or connection, or the tool is missing): it exists but is
  misconfigured, not connected, or, commonly when the web console shows it as
  connected but the tool never appears, not yet added to the desktop
  application. **Go to Step 2**, starting at "Make the connector available in
  the desktop application".
- **Connector absent:** **go to Step 2**. Step 2 falls back to Step 3 if the
  backend CloudFormation stack is not deployed, because the connector is created
  from the stack's outputs.

## Notes

- This step performs no state-changing operation. The only call it makes is the
  read-only `get_tenant_configuration` probe.
- The connector name is fixed to `Admin Onboarding Buddy Endpoint` (Rule 13 in
  `SKILL.md`), so the skill never has to ask which connection to use.
