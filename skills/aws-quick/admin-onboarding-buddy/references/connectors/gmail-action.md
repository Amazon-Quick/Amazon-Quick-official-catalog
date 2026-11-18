---
description: "Gmail action connector: the skill's connector key, what the backend accepts, and traps the AWS Quick guide does not state. Read before offering or creating it, then fetch the guide in source_url."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/gmail-integration.html
---

# Gmail action connector

| Field | Value |
|---|---|
| Skill connector key | `gmail` |
| Suite | Google Workspace (`google_workspace`) |
| Capability | Actions only |
| Created through the backend | Yes, with `enable_action_connector` |
| Backend `auth_type` values | `custom_oauth_app`, `service_to_service_oauth`, or `api_key`. The backend accepts all three for every connector key; choose the one that matches a method the guide lists, per the [method mapping](../README.md#authentication-methods). |
| Default secret name | None. Pass `secret_id` as the name of a secret under `quick-admin-buddy/`. |

For the current authentication methods, required scopes, and console steps, fetch the AWS Quick guide in this file's `source_url`. Order and label the methods per `<Definition - Org Size Recommendation>` in SKILL.md.

## Traps

- `domain_url` must be `https://gmail.googleapis.com`. The guide marks **Base URL** optional, but the backend requires `domain_url` and uses it as the connector's base endpoint. Any other value, such as the Google Workspace domain, is accepted at create time and the connector's calls then fail.
- A common cause of a Custom OAuth app setup that stalls on the AWS Quick sign-in page, without reaching **Review**, is a scope from the guide that is missing on the Google consent screen. Have the admin register every scope the guide lists before connecting (see the consent-screen gotcha in SKILL.md).

## Sharing

Run `<Definition - Sharing Gate>` in SKILL.md before `enable_action_connector`.
