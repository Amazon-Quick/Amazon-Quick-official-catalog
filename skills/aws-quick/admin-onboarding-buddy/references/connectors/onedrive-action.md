---
description: "Microsoft OneDrive action connector: the skill's connector key, what the backend accepts, and traps the AWS Quick guide does not state. Read before offering or creating it, then fetch the guide in source_url."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/onedrive-action-integration.html
---

# Microsoft OneDrive action connector

| Field | Value |
|---|---|
| Skill connector key | `onedrive` |
| Suite | Microsoft 365 (`microsoft_365`) |
| Capability | Actions. The same key also supports a knowledge base: see [onedrive-knowledge-base.md](onedrive-knowledge-base.md). |
| Created through the backend | Yes, with `enable_action_connector` |
| Backend `auth_type` values | `custom_oauth_app`, `service_to_service_oauth`, or `api_key`. The backend accepts all three for every connector key; choose the one that matches a method the guide lists, per the [method mapping](../README.md#authentication-methods). |
| Default secret name | None. Pass `secret_id` as the name of a secret under `quick-admin-buddy/`. |

For the current authentication methods, required scopes, and console steps, fetch the AWS Quick guide in this file's `source_url`. Order and label the methods per `<Definition - Org Size Recommendation>` in SKILL.md.

## Traps

- The guide marks **Base URL** optional. The backend requires it as the secret's `domain_url` and uses it as the connector's base endpoint, so set it to the Microsoft Graph API base URL the guide gives, not the organization's domain (see the `domain_url` gotcha in SKILL.md).
- Only the action connector is created through the backend. The OneDrive knowledge base is console-only (Rule 7 in SKILL.md); see [onedrive-knowledge-base.md](onedrive-knowledge-base.md).

## Sharing

Run `<Definition - Sharing Gate>` in SKILL.md before `enable_action_connector`.
