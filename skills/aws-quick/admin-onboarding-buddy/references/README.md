---
description: "Connector capability matrix and connector-key-to-file map for every connector the skill can set up, plus the guide-method to auth_type mapping; read to pick the right per-connector reference."
last_updated: 2026-11-12
origin: original
---

# Connector references

One file per connector capability the Quick Admin Onboarding Buddy skill can set
up. Each file holds only what the skill adds to the AWS Quick
[integration-specific guides](https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html):
the skill connector key, what the backend accepts, and traps the guide does not
state. Its `source_url` is the AWS Quick guide to fetch for the current
authentication methods, scopes, and console steps. Read only the file for the
connector and capability you are configuring, to keep context small.

Connectors that support both an action connector and a knowledge base have
separate `-action.md` and `-knowledge-base.md` files. Action-only connectors
have a single `-action.md` file. Capabilities follow the AWS Quick
[supported integrations](https://docs.aws.amazon.com/quick/latest/userguide/supported-integrations.html)
table.

## Capability matrix (skill-supported connectors)

| Skill connector key | Official integration | Actions | Knowledge base | Reference file(s) |
|---|---|---|---|---|
| `outlook` | Microsoft Outlook (email, calendar, contacts) | Yes | No | [microsoft-outlook-action.md](connectors/microsoft-outlook-action.md) |
| `ms_teams` | Microsoft Teams | Yes | No | [microsoft-teams-action.md](connectors/microsoft-teams-action.md) |
| `onedrive` | Microsoft OneDrive | Yes | Console only | [onedrive-action.md](connectors/onedrive-action.md), [onedrive-knowledge-base.md](connectors/onedrive-knowledge-base.md) |
| `sharepoint` | Microsoft SharePoint Online | Yes | Yes | [sharepoint-action.md](connectors/sharepoint-action.md), [sharepoint-knowledge-base.md](connectors/sharepoint-knowledge-base.md) |
| `gmail` | Gmail | Yes | No | [gmail-action.md](connectors/gmail-action.md) |
| `google_chat` | Google Chat | Yes | No | [google-chat-action.md](connectors/google-chat-action.md) |
| `google_calendar` | Google Calendar | Yes | No | [google-calendar-action.md](connectors/google-calendar-action.md) |
| `google_drive` | Google Drive | Yes | Yes | [google-drive-action.md](connectors/google-drive-action.md), [google-drive-knowledge-base.md](connectors/google-drive-knowledge-base.md) |
| `google_docs` | Google Docs | Yes | No | [google-docs-action.md](connectors/google-docs-action.md) |
| `google_meet` | Google Meet | Yes | No | [google-meet-action.md](connectors/google-meet-action.md) |
| `google_sheets` | Google Sheets | Yes | No | [google-sheets-action.md](connectors/google-sheets-action.md) |
| `google_slides` | Google Slides | Yes | No | [google-slides-action.md](connectors/google-slides-action.md) |
| `confluence` | Atlassian Confluence Cloud | Yes | Console only | [confluence-action.md](connectors/confluence-action.md), [confluence-knowledge-base.md](connectors/confluence-knowledge-base.md) |
| `atlassian` | Atlassian Jira Cloud | Yes | No | [jira-action.md](connectors/jira-action.md) |

**Legend.** "Yes" means the backend creates it (`enable_action_connector` for
actions, `enable_kb_integration` with `admin_managed` for knowledge bases).
"Console only" means AWS Quick supports the knowledge base but the skill guides
the admin through the AWS Quick console instead of calling the backend, per
`<Definition - Knowledge Base Setup>` in SKILL.md: `onedrive` takes its
certificate credentials in the console, and the backend has no
`CreateDataSource` credential it can send for `confluence`. "No" means AWS Quick
offers no knowledge base for the integration. The connector's
knowledge base file has the details.

Microsoft Calendar is not a standalone AWS Quick integration and has no
connector key. The Microsoft Outlook connector (`outlook`) covers email,
calendar, and contacts. Google Calendar is a standalone integration with its own
`google_calendar` key.

### Dual-capability connectors

`onedrive`, `sharepoint`, `google_drive`, and `confluence` each support an action
connector and a knowledge base under the same key. In Step 5 the skill offers
`onedrive` and `google_drive` as action connectors in the suite's capability
list, then offers knowledge bases for the dual-capability connectors in scope
for the suite. `sharepoint` and
`confluence` action connectors are set up when the admin asks for them.

## Authentication methods

Action connector credentials and `auth_type` values are defined in
`<Definition - Action Connector Auth>` in SKILL.md, which method to recommend in
`<Definition - Org Size Recommendation>`, and knowledge base setup methods in
`<Definition - Knowledge Base Setup>`.

The backend accepts every action connector `auth_type` for every connector key.
Offer only the methods the connector's AWS Quick guide lists, and map the
guide's method name to the `auth_type` to pass:

| Method name in the AWS Quick guide | `auth_type` |
|---|---|
| Custom OAuth app, or user authentication (3LO) for Atlassian | `custom_oauth_app` |
| Service-to-Service OAuth | `service_to_service_oauth` |
| Service authentication (API key) for Atlassian | `api_key` |
| Default OAuth app | n/a: console only, no backend call |

## Doc template

Use this shape for every `-action.md` connector file:

```markdown
---
description: "<Official integration> action connector: the skill's connector key, what the backend accepts, and traps the AWS Quick guide does not state. Read before offering or creating it, then fetch the guide in source_url."
last_updated: <YYYY-MM-DD>
source_url: <AWS Quick integration guide URL for this capability>
---

# <Official integration> action connector

| Field | Value |
|---|---|
| Skill connector key | `<key>` |
| Suite | <Microsoft 365 (`microsoft_365`) / Google Workspace (`google_workspace`) / Any (`any`)> |
| Capability | <Actions only / Actions. The same key also supports a knowledge base: see <relative link to the -knowledge-base.md file>.> |
| Created through the backend | Yes, with `enable_action_connector` |
| Backend `auth_type` values | `custom_oauth_app`, `service_to_service_oauth`, or `api_key` (see the method mapping) |
| Default secret name | None, or the backend default |

For the current authentication methods, required scopes, and console steps,
fetch the AWS Quick guide in this file's `source_url`. Order and label the
methods per `<Definition - Org Size Recommendation>` in SKILL.md.

## Traps

- <Connector-specific facts the guide does not state: the `domain_url` value,
  key names, backend limits. At least one bullet.>

## Secret example

<Optional. Only when the connector's secret values differ from the generic
templates in assets/auth-secret-contract.md. Use `<quick-region>`.>

## Sharing

Run `<Definition - Sharing Gate>` in SKILL.md before `enable_action_connector`.
```

Leave out auth-method descriptions, scope lists, redirect URIs, and console
steps: they come from the guide in `source_url` at run time.
