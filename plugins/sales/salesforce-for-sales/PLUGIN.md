---
name: salesforce-for-sales
display_name: Salesforce for Sales
description: "Sales workflows for account executives and sales leaders, grounded in Salesforce: daily briefings, call prep and follow-up, deal and account reviews, account plans, renewals, prospect research, lead triage, outreach drafts, pipeline reviews, forecasts and confirmed record updates. Use when a seller or sales leader wants answers from, or changes to, their own Salesforce data. Skills read Salesforce through Amazon Quick's existing Salesforce connector (Headless 360 MCP). Five skills each make one write to Salesforce, only after the user says yes to the exact change, and emails and Slack messages are created only as drafts for the user to send."
author: Salesforce
version: 2.0.0
kind: solution
icon: assets/icon.svg

# References into the shared pools, form <category>/<name>.
skills:
  - sales/account-context
  - sales/account-plan
  - sales/account-tiering
  - sales/assign-target-to-sdr
  - sales/calendar-events
  - sales/call-follow-up
  - sales/call-prep
  - sales/close-plan
  - sales/configure
  - sales/customer-health
  - sales/customer-voice
  - sales/daily-briefing
  - sales/deal-advance-gap
  - sales/deal-review
  - sales/deal-signals
  - sales/deal-slip-scenario
  - sales/draft-outreach
  - sales/expansion-whitespace
  - sales/find-internal-answer
  - sales/forecast-narrative
  - sales/handle-objection
  - sales/inbox-sweep
  - sales/lead-triage
  - sales/log-activity
  - sales/pipeline-review
  - sales/query-activity-history
  - sales/renewal-radar
  - sales/rep-context
  - sales/research-prospect
  - sales/salesforce-hygiene-check
  - sales/schedule-meeting
  - sales/stakeholder-map
  - sales/summarize-conversation-transcript
  - sales/team-pipeline
  - sales/update
  - sales/update-opportunity
  - sales/using-display-widget
  - sales/voice-profile
  - sales/weekly-wrap
  - sales/win-loss-review

categories:
  - Sales

connectors:
  - key: salesforce
    label: Your Salesforce
    description: The Salesforce org the skills read from and, after you confirm, write to.
    types: [SALESFORCE_CRM]
    required: true
---

# Salesforce for Sales

Sales workflows for account executives and sales leaders, grounded in Salesforce: daily briefings, call prep and follow-up, deal and account reviews, account plans, renewals, prospect research, lead triage, outreach drafts, pipeline reviews, forecasts and confirmed record updates. Use when a seller or sales leader wants answers from, or changes to, their own Salesforce data. Skills read Salesforce through Amazon Quick's existing Salesforce connector (Headless 360 MCP). Five skills each make one write to Salesforce, only after the user says yes to the exact change, and emails and Slack messages are created only as drafts for the user to send.

Starter prompts are in `initial-starter-prompt.md` and the use case in `use-case.md`.

## Source

Skills by Salesforce, Inc. ([https://github.com/salesforce/salesforce-skills](https://github.com/salesforce/salesforce-skills)), Apache-2.0; see each skill's README.
