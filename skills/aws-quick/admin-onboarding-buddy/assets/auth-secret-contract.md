---
description: "Secrets Manager JSON key contract per auth type (action connectors and secret-backed knowledge bases), read in Step 5 to help the admin create the secret and to check every key and the domain_url value before an enable call."
last_updated: 2026-11-12
origin: original
---

# Auth parameters in AWS Secrets Manager (contract)

The backend's enable operations need the authentication parameters for the
chosen auth type. They come from one AWS Secrets Manager secret that the admin
creates and passes by name as `secret_id`; the backend reads it server-side.
How credentials may and may not be supplied (only through `secret_id`; secret
values are rejected in `auth_params` or `config`; non-secret values such as
`client_id` or `domain_url` may be passed in `auth_params` and override the
same keys in the secret) is set by `<Definition - Action Connector Auth>` and
Rules 8 to 10 in `SKILL.md`. This file gives only the JSON keys each auth type
needs and how to create and check the secret.

The backend validates that every required parameter for the auth type is
present. If any is missing, the result is `validation_failure` with
`data.missing_params` and a `data.secret_contract` template, so the agent can
help the admin fix the secret. The backend's
[tool reference](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/docs/tool-reference.md)
documents the same contract.

> **`auth_type` in the secret JSON is optional.** The examples below include an
> `auth_type` key as a self-documenting hint. The backend takes `auth_type` from
> the tool argument and ignores any `auth_type` stored in the secret, so a
> secret with only the credential fields is equally valid.

## The JSON contract

The secret's plaintext value is a flat JSON object whose keys are the
snake_case parameter names for the chosen auth type:

```json
{ "<param_name>": "<value>", "<param_name>": "<value>" }
```

### Custom OAuth app (`custom_oauth_app`)

Required keys:

```json
{
  "auth_type": "custom_oauth_app",
  "client_id": "<your OAuth client id>",
  "client_secret": "<your OAuth client secret>",
  "domain_url": "<service API base URL>",
  "authorization_url": "<OAuth authorization endpoint>",
  "token_url": "<OAuth token endpoint>",
  "redirect_url": "https://<quick-region>.quicksight.aws.amazon.com/sn/oauthcallback"
}
```

> **`domain_url` becomes the connector's `BaseEndpoint`.** Set it to the
> provider's API base URL, not the organization's web domain. A wrong value is
> accepted at create time but breaks the connector's calls. For Gmail
> (`connector_key` `gmail`), `domain_url` must be
> `https://gmail.googleapis.com`, not your Google Workspace domain. The other
> Gmail values are the standard Google OAuth endpoints:
> `authorization_url` = `https://accounts.google.com/o/oauth2/v2/auth`,
> `token_url` = `https://oauth2.googleapis.com/token`.

### Service-to-Service OAuth (`service_to_service_oauth`)

Required keys (no interactive sign-in, so no authorization or redirect URL):

```json
{
  "auth_type": "service_to_service_oauth",
  "client_id": "<your OAuth client id>",
  "client_secret": "<your OAuth client secret>",
  "domain_url": "<service API base URL>",
  "token_url": "<OAuth token endpoint>"
}
```

These parameter names follow the AWS Quick
[Authentication methods](https://docs.aws.amazon.com/quick/latest/userguide/quick-action-auth.html)
page, in snake_case.

### API key (`api_key`): two-legged API-token auth (for example Atlassian Confluence Cloud)

Required keys, plus an optional `email`:

```json
{
  "auth_type": "api_key",
  "api_key": "<the API token>",
  "domain_url": "<service API base URL, for example https://api.atlassian.com/ex/confluence/<instanceId>>",
  "email": "<optional: account email the token belongs to>"
}
```

- `api_key` and `domain_url` are required; `email` is optional. For Atlassian
  Confluence Cloud, `email` is the Atlassian account email and `api_key` is the
  Confluence API token. The backend maps them to the API's
  `ApiKeyConnectionMetadata` (`ApiKey`, `BaseEndpoint`, `Email`), and omits
  `Email` when it is empty.
- Use the provider's `https://` API base URL for `domain_url`.
- `api_key` is a secret value: it lives only in the secret and is never echoed
  in a result.

### Knowledge base: SharePoint admin-managed (certificate)

The SharePoint admin-managed knowledge base is created through the backend
(`enable_kb_integration` with `auth_type: "admin_managed"`) from a Secrets
Manager secret. The backend reads the secret and sends the certificate fields
to AWS Quick in the data source's `SharePointClientCredentials` (not as a
`SecretArn`).

Required keys in the secret JSON:

```json
{
  "certificate_thumbprint": "<base64url SHA-1 (JWT x5t) of the certificate>",
  "kms_key_arn": "arn:aws:kms:<quick-region>:123456789012:key/<id>",
  "tenant_id": "<Entra directory (tenant) id>",
  "client_id": "<Entra application (client) id>",
  "domain_url": "https://<tenant>.sharepoint.com"
}
```

- API mapping: `certificate_thumbprint` to
  `SharePointClientCredentials.CertThumbprint`, `kms_key_arn` to
  `SharePointClientCredentials.KmsKeyArn`; `tenant_id` and `client_id` to
  `SharePointParameters.TenantId` and `ClientId`; `domain_url` to
  `SharePointParameters.SharePointDomain` (the backend strips the scheme to the
  bare host the API requires).
- **Default secret name:** `quick-admin-buddy/sharepoint-kb-admin`, used when
  `secret_id` is omitted. A custom name is allowed through `secret_id` but must
  start with the readable `quick-admin-buddy/` prefix.
- The site list to index is not in the secret: pass it as `config.sites` (a
  list of SharePoint site URLs) on the `enable_kb_integration` call.
- **Still set up out of band:** the Entra app and certificate, the AWS KMS
  asymmetric signing key, the `Sites.Selected` per-site grants (or all-sites
  permissions), and `kms:Sign` for AWS Quick on the signing key (AWS Quick
  console, Manage account, Permissions, AWS resources). See
  [`knowledge-base-auth-and-acl.md`](./knowledge-base-auth-and-acl.md).
- ACLs may be on or off for admin-managed (the admin's choice). ACL on needs
  the `fullcontrol` Graph permissions; with content-only permissions, use ACL
  off.

```bash
aws secretsmanager create-secret \
  --region "<quick-region>" \
  --name "quick-admin-buddy/sharepoint-kb-admin" \
  --secret-string '{
    "certificate_thumbprint": "...",
    "kms_key_arn": "arn:aws:kms:<quick-region>:123456789012:key/<id>",
    "tenant_id": "...",
    "client_id": "...",
    "domain_url": "https://<tenant>.sharepoint.com"
  }'
```

### Knowledge base: OneDrive admin-managed (`admin_managed`)

In this skill the OneDrive admin-managed knowledge base is created in the AWS
Quick console, not through `enable_kb_integration` (Rule 7 in `SKILL.md`). Its
certificate-based service credentials (`client_id`, `tenant_id`,
`kms_key_arn`, `certificate_thumbprint`) are entered directly in the console's
Create knowledge base flow. Per Rule 7, create no Secrets Manager secret for
them and grant no one access to such a secret.

The only AWS resource grant the OneDrive knowledge base needs is `kms:Sign` on
the KMS signing key, granted in the AWS Quick console under Manage account,
Permissions, AWS resources (add the KMS key ARN, then Finish and Save). The
secret contract in this file does not apply to it. See
[`knowledge-base-auth-and-acl.md`](./knowledge-base-auth-and-acl.md) and
[`../references/connectors/onedrive-knowledge-base.md`](../references/connectors/onedrive-knowledge-base.md).

### Knowledge base: Google Drive admin-managed (service account)

The Google Drive admin-managed knowledge base is created through the backend
(`enable_kb_integration` with `auth_type: "admin_managed"`) from a Secrets
Manager secret.

The secret's JSON body is the exact contents of the service-account key file
downloaded from the Google Cloud console, with one field added:
`admin_account_email`. Paste the downloaded JSON verbatim and add that key,
rather than transcribing individual fields.

Required keys (the backend reads these three; the other keys from the
downloaded JSON are ignored):

```json
{
  "client_email": "<service account client_email, from the downloaded JSON>",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "admin_account_email": "<delegated Google Workspace admin email you created>"
}
```

- API mapping (`ServiceAccountCredentials`): `client_email` to `ClientEmail`,
  `private_key` to `ServiceAccountPrivateKey`, `admin_account_email` to
  `AdminAccountEmail`. The backend reads the secret and sends these fields in
  the data source's credentials (not as a `SecretArn`).
- `private_key` must be the real PEM key from the downloaded JSON.
- **Default secret name:** `quick-admin-buddy/google-drive-kb-admin`, used when
  `secret_id` is omitted. A custom name is allowed through `secret_id` but must
  start with the readable `quick-admin-buddy/` prefix.

To create it, if `service-account.json` is the key file you downloaded:

```bash
# Add admin_account_email to the downloaded JSON and store the whole object.
# (jq keeps every original field and adds the one extra key.)
jq '. + {admin_account_email: "admin@your-workspace-domain.com"}' service-account.json \
  > /tmp/gdrive-kb-secret.json

aws secretsmanager create-secret \
  --region "<quick-region>" \
  --name "quick-admin-buddy/google-drive-kb-admin" \
  --secret-string file:///tmp/gdrive-kb-secret.json

rm -f /tmp/gdrive-kb-secret.json   # remove the private key from disk
```

## Creating the secret

The backend's execution role can read only secrets whose name starts with
`quick-admin-buddy/` (the `AuthSecretRead` policy in the backend's
[CloudFormation template](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml)).
Name the secret accordingly, for example
`quick-admin-buddy/outlook-custom-oauth`. Create it in `<quick-region>`, the
Region rule in `<Definition - Backend>` in `SKILL.md` and in
[`README.md`](./README.md).

### Get the values right before creating the secret

A secret with a wrong value is accepted at create time but breaks the
connector. A wrong `domain_url` is a common cause: the connector is created
(`CREATION_SUCCESSFUL`) but its API calls fail or reach the wrong endpoint.
Fill each field deliberately:

- **`client_id` / `client_secret`:** from the provider's OAuth app (for example
  the Google Cloud OAuth client).
- **`domain_url`:** the provider's API base URL, which the backend sends as the
  connector's `BaseEndpoint`. It is not the organization's web domain; using the
  organization domain (for example `https://example.com`) is a common mistake.
- **`authorization_url` / `token_url`:** the provider's OAuth endpoints.
- **`redirect_url`:** the AWS Quick OAuth callback,
  `https://<quick-region>.quicksight.aws.amazon.com/sn/oauthcallback`. It must
  also be registered as an authorized redirect URI on the provider's OAuth app.

**Per-connector `custom_oauth_app` values** (`client_id` and `client_secret`
always come from your OAuth app):

| connector_key | `domain_url` (becomes BaseEndpoint) | `authorization_url` | `token_url` |
|---|---|---|---|
| `gmail` | `https://gmail.googleapis.com` | `https://accounts.google.com/o/oauth2/v2/auth` | `https://oauth2.googleapis.com/token` |
| `outlook` | `https://graph.microsoft.com` | `https://login.microsoftonline.com/<tenant>/oauth2/v2.0/authorize` | `https://login.microsoftonline.com/<tenant>/oauth2/v2.0/token` |

> For a connector not listed, take `domain_url` and the OAuth endpoints from
> that connector's file in
> [`../references/connectors/`](../references/connectors/) and the provider's
> own OAuth documentation. Never use the organization's web domain as
> `domain_url`.

### Example: Gmail secret

```bash
aws secretsmanager create-secret \
  --region "<quick-region>" \
  --name "quick-admin-buddy/google-gmail-custom-oauth" \
  --secret-string '{
    "auth_type": "custom_oauth_app",
    "client_id": "<your Google OAuth client id>",
    "client_secret": "<your Google OAuth client secret>",
    "domain_url": "https://gmail.googleapis.com",
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "redirect_url": "https://<quick-region>.quicksight.aws.amazon.com/sn/oauthcallback"
  }'
```

### Generic template (replace per the table above)

```bash
aws secretsmanager create-secret \
  --region "<quick-region>" \
  --name "quick-admin-buddy/<connector>-<auth-type>" \
  --secret-string '{
    "auth_type": "custom_oauth_app",
    "client_id": "...",
    "client_secret": "...",
    "domain_url": "<provider API base URL, not the organization web domain>",
    "authorization_url": "...",
    "token_url": "...",
    "redirect_url": "https://<quick-region>.quicksight.aws.amazon.com/sn/oauthcallback"
  }'
```

> **Updating an existing secret** (for example to fix a wrong `domain_url`):
> run `aws secretsmanager put-secret-value --secret-id <name> --secret-string '<full JSON>'`
> with the complete JSON object (put-secret-value replaces the whole value, so
> include every key, not only the changed one). Then re-create the connector
> (`disable_action_connector`, then `enable_action_connector`): the backend
> copies the values into the connector at create time, so an existing connector
> does not pick up secret edits.

### Verify the secret before enabling

After creating or editing the secret, the admin can check the non-sensitive
fields. This prints only the key names, `domain_url`, and `redirect_url`, never
the client secret:

```bash
# Confirm the required keys exist and domain_url is the API base, not the org domain
aws secretsmanager get-secret-value --region "<quick-region>" \
  --secret-id "quick-admin-buddy/<connector>-<auth-type>" \
  --query SecretString --output text \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
print('keys:', sorted(d)); print('domain_url:', d.get('domain_url')); \
print('redirect_url:', d.get('redirect_url'))"
```

Confirm that every required key is present, `domain_url` is the provider's API
base (matches the table), and the Region in `redirect_url` is `<quick-region>`.
Then pass the secret name as `secret_id` on the enable call.

> If the backend's role cannot read the secret name you chose, rename the
> secret to start with `quick-admin-buddy/`, or widen the `AuthSecretRead`
> statement in the backend's
> [CloudFormation template](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml)
> to include your secret and redeploy.

## What to pass as `secret_id`

Pass the secret name, never an ARN. When the admin gives an ARN, convert it per
Rule 9 in `SKILL.md`.
