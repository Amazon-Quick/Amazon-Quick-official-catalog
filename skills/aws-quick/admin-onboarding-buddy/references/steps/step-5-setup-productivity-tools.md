---
description: "Detailed method for <Workflow - Set Up Productivity Tools>: the per-capability action connector loop, auth parameters, secrets, sharing, and the knowledge base pass."
last_updated: 2026-11-12
origin: original
---

# Step 5: Set up individual productivity tools

**Mode:** agentic. **Entry:** from Step 4 with `{suite}` set. **Next:** Step 6
(extensions), then Step 7 (integration testing).

## Goal

Guide the admin through enabling the productivity tools the skill supports,
**one capability at a time**. Each productivity tool is set up as an **action
connector** with `quick-admin-buddy-runtime-target___enable_action_connector`.
For each capability the admin picks an **authentication method** and supplies its
parameters as an AWS Secrets Manager secret, per <Definition - Action Connector
Auth> in `SKILL.md`; then the skill creates the connector.

> **Order within this phase: action connectors first, then knowledge bases.**
> Run the per-capability loop below for the whole `{suite}` set first. Then run
> the [knowledge base pass](#knowledge-base-pass) for the dual-capability
> connectors (`onedrive`, `sharepoint`, `confluence`, `google_drive`). When both
> are done, continue to [Step 6: extensions](step-6-setup-extensions.md).

Supported capabilities in this phase:

| Capability | Microsoft 365 connector | Google Workspace connector |
|---|---|---|
| Email | `outlook` | `gmail` |
| Instant messaging | `ms_teams` | `google_chat` |
| File storage | `onedrive` | `google_drive` |
| Calendar | *(covered by `outlook`)* | `google_calendar` |
| Documents | (none) | `google_docs` |
| Spreadsheets | (none) | `google_sheets` |
| Presentations | (none) | `google_slides` |
| Meetings | *(covered by `ms_teams`)* | `google_meet` |

Use `{suite}` from Step 4 to pick the right `connector_key`. The server also
enforces the suite gate, so a mismatched connector returns `validation_failure`.

> **Google Workspace: offer the full action set.** When `{suite}` is
> `google_workspace`, run the loop for **all eight** Google Workspace action
> connectors in the table, in order. All eight are action connectors, set up the
> same way through `enable_action_connector`. Of the Google Workspace
> connectors, only Google Drive also offers a knowledge base; Google Docs,
> Sheets, Slides, and Meet are action-only. This full-set offer applies to
> Google Workspace only; the Microsoft 365 list stays at three capabilities.

## Ask the organization's size (once, before the loop)

The recommended auth method for every action connector and every knowledge base
depends on organization size, per <Definition - Org Size Recommendation> in
`SKILL.md`. Ask once, unless the admin already said it in this conversation, and
remember it as `{org_size}`. Fill each option description from that
definition's Small and Large descriptions, including its user cutoff:

```
<decision question="Roughly how large is the organization that will use these connectors and knowledge bases?">
<option description="{Large description from <Definition - Org Size Recommendation>}">Large (or not sure)</option>
<option description="{Small description from <Definition - Org Size Recommendation>}">Small</option>
</decision>
```

If the admin is unsure, use **large** and say so. Reuse `{org_size}` for every
capability and knowledge base below; ask only once.

## Per-capability loop

Run this loop for each capability. For Microsoft 365, the order is email,
instant messaging, file storage. For Google Workspace, run it for all eight
capabilities in the table above, in order. Do one capability per turn.

### 1. Offer the capability

```
<decision question="Would you like to set up the Email connector now?">
<option description="Enable email for AWS Quick">Yes, set it up</option>
<option>Skip for now</option>
</decision>
```

On **skip**, move to the next capability. On **yes**, continue.

### 2. Choose the authentication method

Read the connector's file under [`../connectors/`](../connectors/) for the
`auth_type` values the backend accepts, then fetch the AWS Quick guide in that
file's `source_url` for the connector's current authentication methods. Offer
**Default OAuth app** only if that guide lists it; it is console-only, so the
backend cannot create it. Summarize the trade-offs from
[`../../assets/productivity-tool-auth-methods.md`](../../assets/productivity-tool-auth-methods.md),
then order and label the options for `{org_size}` per
<Definition - Org Size Recommendation>, using its reasons.

**Large organization (or size unknown):** recommend Custom OAuth app; offer
Default OAuth app only as not recommended, with the reason from the definition.

```
<decision question="Which authentication method do you want for this connector?">
<option description="Recommended for large organizations. Per-user sign-in through an OAuth app your organization creates and configures, so you own its consent screen, scopes, and credentials">Custom OAuth app</option>
<option description="Server-to-server under a service identity; no interactive sign-in; every user inherits the service identity's access. Only for unattended or shared-identity use">Service-to-Service OAuth</option>
<option description="Not recommended for large organizations: AWS Quick manages the OAuth flow, and the AWS Quick User Guide recommends it for personal access; your organization does not own the app's configuration. Console-only">Default OAuth app</option>
</decision>
```

**Small organization:** recommend Default OAuth app when the connector supports
it; otherwise recommend Custom OAuth app.

```
<decision question="Which authentication method do you want for this connector?">
<option description="Recommended for small organizations. AWS Quick manages the OAuth flow; per-user sign-in; nothing to register. Set up in the AWS Quick console, not through the backend">Default OAuth app</option>
<option description="Per-user sign-in through an OAuth app your organization creates and configures">Custom OAuth app</option>
<option description="Server-to-server under a service identity; no interactive sign-in; every user inherits the service identity's access">Service-to-Service OAuth</option>
</decision>
```

Drop any option the connector's guide or file does not support. Map the answer:

- Custom OAuth app: `custom_oauth_app`
- Service-to-Service OAuth: `service_to_service_oauth`
- Default OAuth app: **no backend call.** Guide the admin to create the
  integration in the AWS Quick console with the Default OAuth app option,
  following the connector's AWS Quick guide. If `{org_size}` is large, restate
  once that this is not the recommended method and why, then respect the
  admin's choice. Then run the console share offer in
  <Definition - Sharing Gate> for this connector before offering the next
  capability.

> **Prerequisite for `custom_oauth_app`: the provider consent screen lists every
> scope.** State this as information in the same message as the next question,
> not as a separate question. The admin registers every scope the connector's
> AWS Quick guide gives on their own OAuth app, in the provider's console:
> for Google, the consent screen's data access settings
> ([Google: Configure the OAuth consent screen and choose scopes](https://developers.google.com/workspace/guides/configure-oauth-consent));
> for Microsoft, the app registration's API permissions
> ([Microsoft: Configure an app to access a web API](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-access-web-apis)).
> What happens when a scope is missing, and why the user must Re-Connect after a
> scope is added, is in the `SKILL.md` Gotchas. The backend tool cannot set
> scopes; this is a provider-side prerequisite.

### 3. Collect the auth parameters

The admin provides the parameters as a Secrets Manager secret, passed by name as
`secret_id`, per <Definition - Action Connector Auth> and Rules 8 to 10 in
`SKILL.md`. The required keys for each `auth_type`, the JSON shape, the
per-connector values, and a command to verify the secret are in
[`../../assets/auth-secret-contract.md`](../../assets/auth-secret-contract.md).

- **Create and check the secret.** Point the admin to the contract to create the
  JSON secret. After they create or edit it, have them verify it with the
  contract's check command (all keys present, `domain_url` is the provider's API
  base URL per the `SKILL.md` Gotchas) before calling `enable_action_connector`.
- **Fix a connector created from a wrong secret.** Have the admin correct the
  secret (with `put-secret-value`, passing the full JSON), then
  `disable_action_connector` followed by `enable_action_connector` recreates the
  connector from the corrected secret.
- **Secret name, not ARN.** Convert any ARN the admin gives per Rule 9 in
  `SKILL.md`.
- **`redirect_url` for Custom OAuth app** is the AWS Quick callback:
  `https://<quick-region>.quicksight.aws.amazon.com/sn/oauthcallback`. Its
  Region matches the stack's Region (see <Definition - Backend>).

### 4. Sharing gate: offer to share it with the signed-in desktop application user

Run <Definition - Sharing Gate> in `SKILL.md` before every
`enable_action_connector` call, for every connector in this loop, and format the
answer per <Definition - Principal Format>. Step-specific details:

- `share_with` takes exactly one principal per call. To share with more users
  or groups afterward, use `share_action_connector` (or the AWS Quick console).
- If a custom id prefix is set (section 4b), pass the same
  `connector_id_prefix` to `share_action_connector` so it targets the same
  resource.

### 4b. (Optional) Set a custom resource id prefix

By default each connector's resource id is `quickadminbuddy-<connector_key>`
(for example `quickadminbuddy-outlook`). Most admins can skip this. If the
organization has a naming convention, or wants to avoid colliding with an
existing `quickadminbuddy-...` resource, offer to set a custom prefix:

```
<decision question="Use a custom id prefix for this connector, or the default (quickadminbuddy-)?">
<option description="Keep the default quickadminbuddy- prefix">Use the default</option>
<option description="Provide your own prefix, e.g. my-company-">Set a custom prefix</option>
</decision>
```

- **Set a custom prefix:** ask for the prefix and pass it as
  `connector_id_prefix`. The resulting id is `<prefix><connector_key>` (so
  `my-company-` gives `my-company-outlook`). The prefix may contain only
  letters, digits, underscores, and hyphens (pattern `[\w\-]+`); if it has
  anything else the backend returns `validation_failure` with
  `data.invalid_connector_id_prefix`, so ask for a corrected prefix.
- **Record the chosen prefix.** The backend does not remember it, so you must
  pass the **same** `connector_id_prefix` to `disable_action_connector` later to
  delete this connector. Note it in the recap so the admin has it on record.

### 5. Enable the connector

Call the backend with the connector key for `{suite}`, the chosen `auth_type`,
the secret name, who to share it with, and (if set) the custom id prefix. The
request carries only the secret's name, never a credential value:

```
quick-admin-buddy-runtime-target___enable_action_connector
  {
    "connector_key": "<outlook|gmail|ms_teams|google_chat|onedrive|google_drive|google_calendar|google_docs|google_sheets|google_slides|google_meet>",
    "auth_type": "<custom_oauth_app|service_to_service_oauth>",
    "secret_id": "quick-admin-buddy/outlook-custom-oauth",
    "share_with": "<the admin's Quick user name, or whoever they chose>",
    "connector_id_prefix": "<optional; omit to use the default quickadminbuddy->"
  }
```

Branch on `Result_Status` (general handling in <Definition - Result Status>):

- **`success`**: confirm using `message` and who it was shared with, then move
  to the next capability.
- **`already_configured`**: tell the admin it was already enabled, still run
  the Sharing Gate and apply it with `share_action_connector`, then continue.
- **`validation_failure`**: the backend says exactly what to fix:
  - `data.missing_params` lists missing auth parameters for the auth type, and
    `data.secret_contract` shows the JSON secret shape. Help the admin fix the
    secret and retry.
  - `data.missing_config_fields` lists any connector-specific config still
    needed.
  - An invalid `auth_type` returns `data.valid_auth_types`.
  - An invalid id prefix returns `data.invalid_connector_id_prefix`; ask for a
    prefix matching `[\w\-]+` (or drop it to use the default) and retry.
  - A suite-gate mismatch returns `data.suite_gate` and `data.stored_suite`.
  - `data.error_type: "inline_secret_not_allowed"`: a secret value was sent in
    `auth_params` or `config` (`data.inline_secret_params` names the keys).
    Nothing was created. Handle per <Definition - Result Status>.
  - `data.error_type: "principal_not_found"`: the `share_with` user does not
    exist. Nothing was created. Handle per <Definition - Principal Format>.
  - If the secret is missing or its body is malformed, the message says whether
    to fix the id or the secret JSON.
- **`server_error`**: the underlying `CreateActionConnector` call failed; the
  `message` carries the API's reported error. Relay it so the admin can fix the
  configuration (for example wrong URLs, bad client credentials, or missing
  scopes), then retry.
- **`internal_error`**: surface `message` and offer to retry. On `internal_error`
  nothing was created, so the connector is not enabled. When the message is
  about **reading the authentication secret**, walk the admin through these
  causes:
  1. **The backend can't read the secret (access denied).** The execution role
     has `secretsmanager:GetSecretValue` only on secrets named
     `quick-admin-buddy/*`. Two sub-cases:
     - The secret is named correctly but the **running stack predates the
       secret-read permission**: the `AuthSecretRead` policy must be deployed.
       The admin redeploys the backend stack (the policy is in the backend
       [template](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml)),
       then retries. This is a common cause when the secret name is already
       correct.
     - The secret is **not** named with the `quick-admin-buddy/` prefix: rename
       it (or widen the `AuthSecretRead` policy) per
       [`../../assets/auth-secret-contract.md`](../../assets/auth-secret-contract.md).
  2. **A full ARN was sent as `secret_id`.** Re-send only the name per Rule 9 in
     `SKILL.md`.

Then move to the next capability and repeat.

## Knowledge base pass

After the action connectors, handle each dual-capability connector in scope
(`onedrive`, `sharepoint`, `confluence`, `google_drive`) and any knowledge base
the admin asked for:

1. **Recommend a setup method** for `{org_size}` per
   <Definition - Org Size Recommendation>, with its reasons.
2. **Choose the path** per <Definition - Knowledge Base Setup>: console guidance
   for user-managed setup, `onedrive`, and `confluence`; the backend
   (`enable_kb_integration` with `auth_type: "admin_managed"`) for admin-managed
   `sharepoint` and `google_drive`. For the console walkthroughs, admin consent,
   service credentials, and ACL guidance, use
   [`../../assets/knowledge-base-auth-and-acl.md`](../../assets/knowledge-base-auth-and-acl.md)
   and the connector's file under [`../connectors/`](../connectors/).
3. **Confirm the out-of-band prerequisites** for a backend knowledge base, one
   at a time (below for SharePoint; for Google Drive, the Google-side setup in
   [`../connectors/google-drive-knowledge-base.md`](../connectors/google-drive-knowledge-base.md)).
4. **Run <Definition - Sharing Gate>** for the knowledge base `owner`.
   Knowledge bases take `owner`, not `share_with`; to give another user view
   access afterward, use `share_kb_integration` (Rule 6 in `SKILL.md`).
5. **Call `enable_kb_integration`** with the parameters listed for the source in
   <Definition - Knowledge Base Setup>. On failure, read `data.rollback` and
   follow <Definition - Knowledge Base Cleanup> before retrying.

### Prerequisites for a SharePoint `Sites.Selected` admin-managed knowledge base

The admin sets these up in Microsoft Entra and AWS before the backend
`enable_kb_integration` call; the certificate, KMS, tenant, client, and domain
values then go in the Secrets Manager secret the backend reads. Step-by-step
instructions are in
[`../../assets/knowledge-base-auth-and-acl.md`](../../assets/knowledge-base-auth-and-acl.md)
and [`../connectors/sharepoint-knowledge-base.md`](../connectors/sharepoint-knowledge-base.md).

- **Admin role.** Granting per-site access on a site's permissions requires the
  admin to hold the **SharePoint Administrator** or **Global Administrator**
  role (and to be able to administer the target sites); with other roles the
  grant calls return `accessDenied`. Microsoft lists the roles and their
  template IDs in
  [Microsoft Entra built-in roles](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference).
  Confirm the admin has one of these before walking into the grant flow.
- **AWS KMS asymmetric signing key.** An AWS KMS key in the same Region as the
  AWS Quick account (see <Definition - Backend>): key type **Asymmetric**, key
  usage **Sign and verify**, key spec **RSA_2048**, Single-Region. For example,
  the admin runs
  `aws kms create-key --region <quick-region> --key-spec RSA_2048 --key-usage SIGN_VERIFY`.
  Its ARN is needed for the certificate, the secret's `kms_key_arn`, and the
  AWS Quick grant below.
- **Credentials in the secret.** `certificate_thumbprint`, `kms_key_arn`,
  `tenant_id`, `client_id`, and `domain_url` go in the secret named in
  <Definition - Knowledge Base Setup>. OneDrive is console-only: the admin
  enters these values in the console Create knowledge base flow (Rule 7 in
  `SKILL.md`).
- **Grant AWS Quick `kms:Sign` on the signing key (required).** The admin grants
  it in the AWS Quick console under **Manage account**, **Permissions**, **AWS
  resources**: add the KMS signing key ARN, then **Finish** and **Save**. This
  is done in AWS Quick, not by editing the KMS key policy, and before creating
  the SharePoint knowledge base (backend) or the OneDrive knowledge base
  (console). For a self-managed AWS Quick IAM service role, the equivalent is
  `kms:Sign` on the key.
- **Permission scope.** When the admin wants only some sites indexed, or cannot
  grant tenant-wide SharePoint access, recommend least-privilege
  `Sites.Selected` (per-site Graph grants), per <Definition - Knowledge Base
  Setup>.

## Wrap up

After the capabilities for `{suite}` (three for Microsoft 365, eight for Google
Workspace) and the knowledge base pass, recap what was enabled versus skipped
from the server's live state (not the conversation):

```
quick-admin-buddy-runtime-target___get_onboarding_summary
```

`get_tenant_configuration` also reports, per connector, an `integrations`
breakdown showing the status of its `action_connector` and `knowledge_base`
separately. Present the recap, and offer to revisit any skipped capability
(another `enable_action_connector`) or to turn one off
(`disable_action_connector`). If any connector was enabled with a custom
`connector_id_prefix`, include that prefix in the recap and **pass the same
prefix to `disable_action_connector`** when turning it off; otherwise the
delete targets the default-prefixed id and does not find the resource.

When the admin is done with action connectors and knowledge bases, continue to
**[Step 6: Set up AWS Quick extensions](step-6-setup-extensions.md)**.

## Exit criteria

- `{org_size}` was asked once (or taken from the conversation), and every
  auth-method and knowledge base recommendation followed it: Default OAuth app
  and user-managed setup were recommended only for a small organization, and
  marked not recommended for a large one.
- Each capability for `{suite}` was offered individually, and every "yes"
  resulted in `enable_action_connector` returning `success` or
  `already_configured` (after resolving any missing parameters), with
  `share_with` set to whoever the admin chose, and **the Sharing Gate was run
  before every create** (a username was resolved or asked for, and the share was
  explicitly offered, for each connector and each knowledge base).
