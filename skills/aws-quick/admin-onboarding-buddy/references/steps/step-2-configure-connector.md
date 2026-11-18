---
description: "Detailed method for <Workflow - Configure Connector>: creating the Admin Onboarding Buddy Endpoint connector from stack outputs, adding it to the desktop application, and testing it."
last_updated: 2026-11-12
origin: original
---

# Step 2: Configure the custom MCP action connector

**Mode:** agentic. **Entry:** from Step 1 when the connector is absent or not
callable. **Next:** Step 4 after a successful test; Step 3 if the backend stack
is unknown or not deployed.

## Goal

Help the admin create (or repair) the custom MCP action connector in AWS
Quick so the skill can call the backend. The connector uses **Custom
user-based OAuth** and must be named exactly **`Admin Onboarding Buddy
Endpoint`**, so the connection name the skill relies on is predictable.

- Custom user-based OAuth reference: https://docs.aws.amazon.com/quick/latest/userguide/quick-action-auth.html#quick-custom-user-auth
- Custom MCP connector reference: https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html
- The backend's own connector walkthrough is "Step 3: Create the action
  connector in AWS Quick" in its
  [deployment guide](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/docs/deployment-guide.md).

## Precondition: do we know where the backend is deployed?

The connector configuration values come from the **CloudFormation stack outputs**
of the deployed backend. Before collecting anything, confirm the admin can reach
a deployed stack.

```
<decision question="Is the Quick Admin Buddy backend already deployed, and can you access its CloudFormation stack outputs?">
<option description="The stack is deployed and you can open its Outputs tab in the CloudFormation console">Yes, I can see the stack outputs</option>
<option description="Not deployed, or you don't know where it is">No / I don't know</option>
</decision>
```

- **No or unknown: go to [Step 3](step-3-deploy-backend.md)** to deploy the
  backend first, then come back here.
- **Yes: continue below.**

## Create the connector in AWS Quick

In the AWS Quick console, add a new **custom MCP action connector** (Model
Context Protocol) and set:

| Connector field | Value | Where it comes from |
|---|---|---|
| **Name** | `Admin Onboarding Buddy Endpoint` | Fixed. Type it exactly. |
| Type | `MODEL_CONTEXT_PROTOCOL` (console: **Model Context Protocol (MCP)**) | Stack output `ActionConnectorType`. |
| Authentication | **Custom user-based OAuth** (OAuth2 authorization code, 3LO; console: **User authentication (OAuth)**) | Stack output `ActionConnectorAuthType` = `OAUTH2_AUTHORIZATION_CODE`. |
| Base endpoint (console: **MCP server endpoint**) | Gateway MCP URL, **as is** (it already ends in `/mcp`) | Stack output `ActionConnectorBaseEndpoint`. |
| Redirect / callback URL | AWS Quick OAuth callback | Stack output `ActionConnectorRedirectUrl` (already registered on the Cognito app client). |

> **Base endpoint: copy it verbatim, never build it.** Have the admin paste
> the `ActionConnectorBaseEndpoint` output exactly as shown (it is identical to
> `AgentCoreGatewayEndpoint`). It contains **exactly one** `/mcp`, at the end:
> `https://<gateway-id>.gateway.bedrock-agentcore.<quick-region>.amazonaws.com/mcp`.
> Tell the admin to use it unchanged. A doubled `/mcp/mcp` is rejected by the
> gateway with HTTP 400 ("Http operation is not supported for gateway protocol
> type MCP"), and the connector's test call fails.

Then fill the **Custom user-based OAuth** credential fields. Have the admin
open the CloudFormation stack's **Outputs** tab and copy these values:

| OAuth field | Stack output | Notes |
|---|---|---|
| **Authorization URL** | `CognitoAuthorizationEndpoint` | `https://<prefix>.auth.<quick-region>.amazoncognito.com/oauth2/authorize` |
| **Token URL** | `CognitoTokenEndpoint` | `https://<prefix>.auth.<quick-region>.amazoncognito.com/oauth2/token` |
| **Client ID** | `CognitoUserPoolClientId` | (none) |
| **Client secret** | value stored at `CognitoClientSecretArn` | The output is the secret's ARN, not the value; the value lives in Secrets Manager (see below). |

### Retrieving the Client secret

The client secret is stored in AWS Secrets Manager, referenced by the stack
output `CognitoClientSecretArn`. Give the admin this command to run:

```bash
aws secretsmanager get-secret-value \
  --region "<quick-region>" \
  --secret-id "<CognitoClientSecretArn value>" \
  --query SecretString --output text
```

The admin pastes the returned value into the connector's **Client secret**
field. Refer to it by field name only (Rule 10 in `SKILL.md`).

### Signing in during the OAuth flow

Custom user-based OAuth is interactive (3LO): completing the connection opens the
Cognito hosted sign-in. The stack provisions a sign-in user `quickadminbuddy`
(output `CognitoUsername`) whose credentials are stored in Secrets Manager
(output `CognitoUserCredentialsSecretArn`). If the admin needs them, give this
command to run:

```bash
aws secretsmanager get-secret-value \
  --region "<quick-region>" \
  --secret-id "<CognitoUserCredentialsSecretArn value>" \
  --query SecretString --output text
```

## Make the connector available in the desktop application (required, not automatic)

Creating and connecting the connector in the **AWS Quick web console** does
**not** make it usable from **the AWS Quick desktop application**, which is
where this skill runs and calls the connector's tools. Each user adds it in the
desktop application, signs in, and enables its tools. **Tell the admin this
explicitly before testing.** Without it, the skill cannot see
`Admin Onboarding Buddy Endpoint`, and the test below fails with "operation not
available" even though the web console shows it as connected.

> **Prerequisite: a NEW chat is required after installing the connector.** A
> chat sees only the tools that were connected when it started, so the
> conversation you are in right now **cannot** use the connector after it is
> installed. The admin opens a fresh chat **from the skill**: **Skills,
> `admin-onboarding-buddy`, Try it**. Tell them this *before* they start
> the steps below, and remind them again at the end.

Walk the admin through these steps in the desktop application, signed in as the
**same AWS Quick user the connector is shared with** (the user who created it,
or whoever it was shared with; see "Give other AWS Quick users access to the
connector" in the backend's
[deployment guide](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/docs/deployment-guide.md)):

1. Open **Customize**, then choose the **Connectors** tab.
2. **Find the connector.** It appears under **Suggested for you** (connectors
   already set up and shared with you) or through **Browse all**. Search for
   `Admin Onboarding Buddy Endpoint`. If it is not listed at all, it is not
   shared with this AWS Quick user: share it (web console, connector
   permissions), then return here.
3. **Install it, then sign in.** Choose **Install**, then complete **Sign in**
   (the Cognito hosted sign-in: user `quickadminbuddy`, credentials from the
   `CognitoUserCredentialsSecretArn` secret, see above). A connector that
   requires authentication cannot be used until the sign-in completes.
4. **Confirm it is enabled.** In the connectors table the entry shows
   **Type: Cloud** and an **enabled** status; turn the status toggle on if it is
   off.
5. **Enable its tools (easy to miss).** Tools discovered when the MCP server
   is synced are **disabled by default** so the owner can review them. Open the
   connector's actions menu, choose **Manage tool permissions**, and make sure
   the backend's tools are **not** set to *Disable*. The tools are listed in
   <Definition - MCP Operations> in `SKILL.md` (each is prefixed
   `quick-admin-buddy-runtime-target___` in chat). Read tools can stay on
   *Always Allow*; state-changing tools can stay on *Ask Each Time* (the default
   for write tasks) so the admin approves each change.
6. **Open a new chat from the skill** (required): in the desktop application go
   to **Skills**, select **`admin-onboarding-buddy`**, and choose **Try it**.
   Continue only in that new chat, because the existing chat started before the
   connector was installed and does not see its tools. In the new chat the skill
   starts again at Step 1; its read-only `get_tenant_configuration` probe
   succeeds and routes straight to [Step 4](step-4-set-productivity-suite.md),
   so the admin does **not** repeat the connector setup.

> This is a **per-user** action: every admin who will run the skill has the
> connector shared with their AWS Quick user and repeats steps 1 to 5 in their
> own desktop application. The menu labels above follow the AWS Quick
> connectors documentation
> (<https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html>);
> if the app's wording differs slightly, follow the on-screen equivalent.

Continue only after the admin confirms the connector is installed, signed in,
enabled, and its tools are enabled in the desktop application:

```
<decision question="In the AWS Quick desktop application, is 'Admin Onboarding Buddy Endpoint' installed, signed in, enabled, with its tools enabled, and have you opened a NEW chat via Skills, admin-onboarding-buddy, Try it?">
<option description="Enabled Cloud connector, tools not disabled, and you are now in a fresh chat started from the skill">Yes, I'm in a new chat and it's ready</option>
<option description="Not added to the desktop application yet, or unsure: walk me through it">No / not sure</option>
</decision>
```

On **No / not sure**, walk through steps 1 to 6 one at a time. If the admin says
the connector is installed but is still talking to you in the **same chat** they
installed it from, have them do step 6 (new chat via **Try it**); that alone is
the usual fix.

## Test the connector

Once the connector shows connected, verify it end to end by issuing the
read-only operation:

```
quick-admin-buddy-runtime-target___get_tenant_configuration
```

Branch on the result:

- **A Tool_Result comes back** (`status` such as `success`): the connector works.
  Tell the admin it is connected and tested, and **go to
  [Step 4](step-4-set-productivity-suite.md)**.
- **The operation is not available in the toolset** (the connector shows
  connected in the web console but the tool never appears): this is usually the
  desktop application step, not the connector configuration. Re-check
  [Make the connector available in the desktop application](#make-the-connector-available-in-the-desktop-application-required-not-automatic)
  (installed, signed in, enabled, **tools not disabled**, and a **new chat
  opened from the skill**) before touching the endpoint or credentials.
- **The call fails with an action-not-found error** (the tool is visible but
  the call returns, for example, HTTP 404 *"The requested action was not found
  for this Action Connector"*): diagnose and recover per
  <Definition - Stale Connector Actions> in `SKILL.md`, using the Test decision
  in [Step 1, check 1b](step-1-verify-connector.md#1b-connector-shows-healthy-but-its-actions-fail).
- **The call fails with an auth error or `internal_error`** (the tool is
  visible but the call errors): the connector is not configured correctly.
  Re-check the Base endpoint, the Authorization and Token URLs, the Client ID,
  and the Client secret against the stack outputs, then test again. Common
  causes: wrong Region in the Cognito URLs, a stale Client secret, or a Base
  endpoint that is not exactly the gateway URL from the stack output (it already
  ends in `/mcp`; a second `/mcp` makes the gateway return HTTP 400).

## Exit criteria

- Connector named `Admin Onboarding Buddy Endpoint` exists, is connected, **has
  been added to the desktop application (installed, signed in, enabled, tools
  enabled), and the skill was reopened in a new chat via Skills, Try it**, and
  `quick-admin-buddy-runtime-target___get_tenant_configuration` returns a
  Tool_Result: **Step 4**.
- Backend stack unknown or not deployed: **Step 3**.
