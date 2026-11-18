---
description: "Atlassian Confluence Cloud knowledge base: console-only in this skill, why the backend cannot create it, the ACL decision, and the prerequisite checklist for ACLs. Read it when setting up a Confluence knowledge base."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/confluence-knowledge-base.html
---

# Atlassian Confluence Cloud knowledge base

| Field | Value |
|---|---|
| Skill connector key | `confluence` (the same key as the Confluence action connector in [confluence-action.md](confluence-action.md)) |
| Suite | Any (offered under either suite) |
| Capability | Knowledge base |
| Backend | Console-only, with or without ACLs. Never call `enable_kb_integration` for `confluence` (Rule 7 in SKILL.md); see [Why the console, not the backend API](#why-the-console-not-the-backend-api). |
| Secret | None. |

For the current prerequisites and console wizard steps, fetch the AWS Quick guide in this file's `source_url`, and for ACLs its [Document-level access controls](https://docs.aws.amazon.com/quick/latest/userguide/confluence-kb-acl.html) page. The skill's role is to guide and confirm the console steps.

## How to set this up

1. **Ask whether the admin wants document-level ACLs.** With ACLs, each user sees answers only from Confluence content they are allowed to see; without ACLs, anyone with access to the knowledge base sees answers from all its indexed content. Tell the admin up front that the ACL choice is fixed at creation: it cannot be changed afterward, and the Atlassian admin credentials ACLs need cannot be added later.
1. **With ACLs:** confirm the ACL prerequisites below one at a time, then guide the console wizard, where the admin enters them under ACL Management, Use Atlassian admin credentials, and later selects Control document access with ACLs.
1. **Without ACLs:** guide the console wizard directly. Only the Confluence URL (`https://<your-site>.atlassian.net`), the Confluence consent popup, and the space, blog, or page URLs are needed.

### Prerequisite checklist (ACLs only)

The Atlassian organization administrator obtains these before the console setup starts. For any item that is missing, give the admin the AWS Quick steps in [Obtain Atlassian admin credentials](https://docs.aws.amazon.com/quick/latest/userguide/confluence-kb-acl.html#confluence-kb-atlassian-admin-credentials) and wait for them to confirm it.

1. **An Atlassian admin API key** with exactly the scopes `read:directories:admin` and `read:workspaces:admin`. API keys expire, so the admin notes the expiry date and updates the credentials before it.
1. **The Organization ID (UUID)**, from the Atlassian admin portal URL.
1. **The Directory ID (UUID)**, which the Atlassian Admin Workspace API returns; the admin console does not show it.

The admin enters these values in the console wizard, not in the chat.

## Why the console, not the backend API

The backend cannot create a Confluence knowledge base in either case. The [`CreateKnowledgeBase` API reference](https://docs.aws.amazon.com/quicksight/latest/APIReference/API_CreateKnowledgeBase.html) lists the supported sources as S3, web crawler, Google Drive, SharePoint, and OneDrive; Confluence is not one of them. The backend therefore rejects `enable_kb_integration` for `confluence` with `validation_failure` and `data.error_type: "console_only_knowledge_base"`, before reading any secret.

The data source step fails too. A Confluence knowledge base would be a data source (`CreateDataSource`, `Type=CONFLUENCE`) plus a knowledge base, and `CreateDataSource` for that type requires a `Credentials` value but rejects every credential form in the SDK model, and also rejects omitting it. A test on 2026-11-12 against a deployed backend, with an ACL admin-credentials secret, returned the first error below:

| Credentials sent | API error (start of the message) |
|---|---|
| None (only `ConfluenceParameters.ConfluenceUrl`) | `DataSourceCredentials field is incorrectly set` |
| `SecretArn` | `SecretArn cannot be used for CONFLUENCE source` |
| `OAuthClientCredentials` | `OAuthClientCredentials are only supported for SNOWFLAKE or DATABRICKS` |
| `CredentialPair` | `CONFLUENCE source doesn't support CredentialPair authentication` |
| `CopySourceArn` | `CONFLUENCE source doesn't support CopySourceArn` |

The Confluence connection is user-based: the console's Add account flow opens an OAuth consent popup, and the SDK model has no equivalent connection or account resource. `ConfluenceParameters` carries only `ConfluenceUrl`, so the Atlassian admin credentials for ACLs are a console input, not an API parameter.

## Traps

- A URL ending in `/wiki/spaces/<key>/overview` is treated as a single page. To index a whole space, use the space URL without `/overview`.
- If the Atlassian site blocks user-installed OAuth apps, a site administrator authorizes the app, once per Atlassian site, not per organization. See the guide's [Blocked OAuth app authorization](https://docs.aws.amazon.com/quick/latest/userguide/confluence-knowledge-base.html#confluence-kb-troubleshooting-blocked-oauth).
- For an ACL-enabled knowledge base, each end user is prompted to sign in to Confluence on their first query, and access is checked live against the Confluence API at query time.
