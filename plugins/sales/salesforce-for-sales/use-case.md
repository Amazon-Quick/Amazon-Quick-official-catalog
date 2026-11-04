# Salesforce for Sales

## When to use

A seller or sales leader wants an answer grounded in their own Salesforce data: what's on today, how a deal or an account is doing, what to say next, or where the pipeline and the forecast stand.

## Steps

1. The user asks a question, or picks a starter prompt.
2. The skill that matches the request reads the records it needs.
3. The skill reads Salesforce through the Salesforce connector's `dispatch_readonly` tool, with the GraphQL and SOQL queries written in the skill, and batches independent reads in one turn. When email, calendar, document, Slack or web tools are connected, it reads them too.
4. The skill returns its result, with each Salesforce record linked. 27 skills show the result as a widget through `display_widget`, and fall back to Markdown when the widget can't be shown.
5. For the drafting skills (draft-outreach, call-follow-up, inbox-sweep and weekly-wrap), the user reviews the drafts and sends them.
6. For the five write skills (account-plan, assign-target-to-sdr, log-activity, schedule-meeting and update-opportunity), the skill makes its change only after the user says yes.

## Guardrails

- **Writes only after a yes.** Five skills write to Salesforce: account-plan, assign-target-to-sdr, log-activity, schedule-meeting and update-opportunity. Each makes one write with the connector's `dispatch` tool, only after the user says yes. No other skill changes Salesforce data.
- **Drafts only.** Emails and Slack messages are created as drafts. Nothing is sent or posted.
- **Documented calls only.** The skills never use the server's `discover` or `describe` tools, and never call an endpoint the skill doesn't name.
- **Totals from Salesforce.** Counts and dollar totals come from aggregate reads with the same filter as the rows, never from the model's arithmetic.
- **No silent widening.** If the user's own records come back empty, the skill says so and asks which scope to use.
- **No invented values.** Values are cited as queried, blanks show as blank, and fields show by their labels.

## Setup

In Salesforce, an admin:

1. Activates the Salesforce MCP Server (Headless 360) in Setup.
2. Creates a permission set for the users who should have access.
3. Creates the External Client App (ECA) for OAuth, with the `mcp_api` scope and PKCE required.
4. Sets which of the server's tools users can call:

| Tool | What the skills use it for | Setting |
|---|---|---|
| `dispatch_readonly` | every documented Salesforce read (SOQL, UI API, GraphQL) | allow |
| `display_widget` | the widgets 27 skills show | allow, unless you want text output only |
| `dispatch` | the one write each of the five write skills makes after a yes, and the transcript read in summarize-conversation-transcript | allow to use those skills; block for a read-only setup |
| `discover`, `describe` | nothing; the skills never call them | block |

With `dispatch` blocked, the five write skills can't save their change: log-activity and schedule-meeting return paste-ready text, update-opportunity gives a manual checklist, and assign-target-to-sdr stops. summarize-conversation-transcript can't read the transcript.

In Amazon Quick:

5. Connect the existing Salesforce connector to the org, with each user signing in as themselves. The skills read "my" records with `scope: MINE`, so a shared integration user would return that user's records instead.
6. Optionally connect email, calendar, document storage and Slack. Without them, the skills work from Salesforce alone.

## Sources beyond Salesforce

Salesforce is the only connector the plugin declares. Most skills also read email, calendar, documents and Slack when those tools are available, and skip them when they aren't. These skills depend on another source:

| Skill | Needs | Without it |
|---|---|---|
| voice-profile | sent email | stops and asks the user to connect email |
| inbox-sweep | unread and sent email | has nothing to sweep |
| customer-voice | call transcripts or email threads | finds no quotes; Salesforce only scopes the search |
| call-follow-up | the call transcript, pasted or from a document tool | works from a pasted transcript; shows the Slack recap for the user to copy when it can't create a draft |
| draft-outreach | an email tool that can create drafts | returns the subject and body as text |
| research-prospect | web search | Salesforce is only a duplicate check, so the brief has little else |
| find-internal-answer | documents, Slack and email | answers from Salesforce and says which sources it couldn't reach |

## Known limits

- Some reads pin Salesforce API v66.0, so the org must support it.
- The skills haven't run in Quick from this package. The source's eval specs and read fixtures were not copied.
- voice-profile returns a profile for the user to paste into their own agent instructions. The package doesn't store it.
