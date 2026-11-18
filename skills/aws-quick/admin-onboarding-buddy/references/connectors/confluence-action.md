---
description: "Atlassian Confluence Cloud action connector: the skill's connector key, what the backend accepts, and traps the AWS Quick guide does not state. Read before offering or creating it, then fetch the guide in source_url."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/confluence-action-integration.html
---

# Atlassian Confluence Cloud action connector

| Field | Value |
|---|---|
| Skill connector key | `confluence` |
| Suite | Any (`any`) |
| Capability | Actions. The same key also supports a knowledge base: see [confluence-knowledge-base.md](confluence-knowledge-base.md). |
| Created through the backend | Yes, with `enable_action_connector` |
| Backend `auth_type` values | `custom_oauth_app`, `service_to_service_oauth`, or `api_key`. The backend accepts all three for every connector key; choose the one that matches a method the guide lists, per the [method mapping](../README.md#authentication-methods). |
| Default secret name | None. Pass `secret_id` as the name of a secret under `quick-admin-buddy/`. Example: `quick-admin-buddy/confluence-action`. |

For the current authentication methods, required scopes, and console steps, fetch the AWS Quick guide in this file's `source_url`. Order and label the methods per `<Definition - Org Size Recommendation>` in SKILL.md.

## Traps

- `domain_url` is the guide's **Base URL**, the API URL `https://api.atlassian.com/ex/confluence/<instanceId>`, not the site login URL. The guide shows how to find the instance ID.
- If one Atlassian app serves both Confluence and Jira, add each product's scopes under that product's API in the app's permissions.
- Only the action connector is created through the backend. The Confluence knowledge base is console-only (Rule 7 in SKILL.md); see [confluence-knowledge-base.md](confluence-knowledge-base.md).

## Secret example

Replace the placeholders, keep `<quick-region>` as the Region of the AWS Quick account, and pass the name as `secret_id`. `auth_type` is the tool argument, not a key in the secret.

`custom_oauth_app` (user authentication, 3LO):

```bash
aws secretsmanager create-secret \
  --region <quick-region> \
  --name quick-admin-buddy/confluence-action \
  --secret-string '{
    "client_id": "<client id>",
    "client_secret": "<client secret>",
    "domain_url": "https://api.atlassian.com/ex/confluence/<instanceId>",
    "authorization_url": "https://auth.atlassian.com/authorize",
    "token_url": "https://auth.atlassian.com/oauth/token",
    "redirect_url": "https://<quick-region>.quicksight.aws.amazon.com/sn/oauthcallback"
  }'
```

`api_key` (service authentication):

```bash
aws secretsmanager create-secret \
  --region <quick-region> \
  --name quick-admin-buddy/confluence-action \
  --secret-string '{
    "api_key": "<API token>",
    "domain_url": "https://api.atlassian.com/ex/confluence/<instanceId>",
    "email": "<Atlassian account email (optional)>"
  }'
```

The secret contract is in [`../../assets/auth-secret-contract.md`](../../assets/auth-secret-contract.md).

## Sharing

Run `<Definition - Sharing Gate>` in SKILL.md before `enable_action_connector`.
