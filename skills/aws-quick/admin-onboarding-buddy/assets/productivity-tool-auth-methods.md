---
description: "Trade-offs of the four AWS Quick action connector authentication methods (Default OAuth app, Custom OAuth app, Service-to-Service OAuth, API key), read in Step 5 when the agent summarizes the options before the admin picks one."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/quick-action-auth.html
---

# Action connector authentication methods: trade-offs (Step 5 asset)

AWS Quick supports several authentication methods for action connectors, and
the available methods depend on the connector. Use this file to summarize the
trade-offs before the admin chooses a method in Step 5. Every fact here comes
from the AWS Quick User Guide page
[Authentication methods](https://docs.aws.amazon.com/quick/latest/userguide/quick-action-auth.html);
cite it when you explain a trade-off. *Content was rephrased for compliance
with licensing restrictions.*

Before you summarize, check two other sources:

- **Which method to recommend, and in what order:** follow
  `<Definition - Org Size Recommendation>` and Rule 14 in `SKILL.md`. This file
  describes the methods; it does not decide between them.
- **Which methods a given connector supports and which `auth_type` values the
  backend accepts for it:** the connector's file under
  [`../references/connectors/`](../references/connectors/) and the AWS Quick
  guide in its `source_url`.

How credentials reach the backend (only through `secret_id`) is set by
`<Definition - Action Connector Auth>` and `<Rules>` (Rules 8 to 10) in
`SKILL.md`; the secret JSON keys per `auth_type` are in
[`auth-secret-contract.md`](./auth-secret-contract.md). Knowledge bases use a
different model; see `<Definition - Knowledge Base Setup>` in `SKILL.md` and
[`knowledge-base-auth-and-acl.md`](./knowledge-base-auth-and-acl.md).

## Quick comparison

| Method | Backend `auth_type` | Who signs in | Whose access the actions use | What the organization supplies |
|---|---|---|---|---|
| Default OAuth app | None (console-only) | Each user, through the provider's sign-in | The signed-in user's own | Nothing: AWS Quick manages the OAuth flow |
| Custom OAuth app | `custom_oauth_app` | Each user, through the provider's sign-in | The signed-in user's own | Its own OAuth app and its credentials |
| Service-to-Service OAuth | `service_to_service_oauth` | No one: no user interaction | The service account's | Client credentials for a service app |
| API key | `api_key` | No one: a single token | The token's service-level access | An API key from the provider |

## Default OAuth app

Three-legged OAuth (3LO) where AWS Quick manages the OAuth flow. The AWS Quick
User Guide calls it the recommended authentication method for personal access
to third-party services. The backend cannot create it: guide its setup in the
AWS Quick console and make no backend call.

- **Strengths (per the guide):** no additional credentials or configuration
  from the organization; user-specific authentication through the provider's
  sign-in; credential storage managed by AWS Quick; automatic token refresh.
- **Limits (per the guide):** not every connector supports it, so check the
  connector's guide.
- **Notes:** the guide gives a 90-day refresh token lifecycle. The OAuth
  application is the one AWS Quick manages, not one the organization creates
  and configures.

## Custom OAuth app

Also 3LO, with users signing in directly to the provider, but the organization
provides its own OAuth credentials instead of using the application AWS Quick
manages. The guide describes it as the method for organizations that require
specific control over the OAuth application configuration.

- **Strengths (per the guide):** the organization creates and configures the
  OAuth application itself; access stays per user, because each user signs in.
- **Limits (per the guide):** the organization must first create an OAuth
  application in the provider's developer console, then enter its Client ID,
  Client Secret, Domain URL, Authorization URL, Token URL, and Redirect URL.
- **Skill-specific trap:** the provider's consent screen must list every scope
  the connector requests. See the consent-screen entry in `<Gotchas>` in
  `SKILL.md`.

## Service-to-Service OAuth

Client credentials for server-to-server authentication, without user
interaction.

- **Strengths (per the guide):** suits automated workflows and shared
  connectors.
- **Limits (per the guide):** actions run under a service account, so they use
  that account's access rather than each user's. It needs Client ID, Client
  Secret, Domain URL, Token URL, and connector-specific parameters.
- When the admin considers it, apply the Service-to-Service paragraph of
  `<Definition - Org Size Recommendation>` in `SKILL.md`.

## API key

A single token for service-level access, common for connectors that do not
support OAuth (for example Atlassian Confluence Cloud in this skill).

- **Strengths (per the guide):** one token, no OAuth app or sign-in flow.
- **Limits (per the guide):** access is service-level rather than per user. It
  needs a valid API key from the provider, the base URL or domain, and
  service-specific parameters such as an email or account ID.
