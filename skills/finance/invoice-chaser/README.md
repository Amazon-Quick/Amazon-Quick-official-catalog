---
description: "Human-facing overview, prerequisites, installation, and getting started for the Invoice Chaser skill."
last_updated: 2026-09-13
origin: original
---

# Invoice Chaser

Pulls overdue invoices from QuickBooks, segments them by how late they are, drafts tone-appropriate follow-ups, and sends only after your approval.

## Overview

Invoice Chaser answers the weekly question "who hasn't paid me, and what should I do about each one?" It gathers overdue invoices, segments them into Friendly, Firm, and Final Notice tiers, drafts the follow-up messages, and surfaces every draft for you to approve, edit, or skip before anything sends. It is built for small business owners running accounts-receivable follow-up, with optional SMS, customer-group segmentation, and scheduled automation.

## Pre-requisites

- QuickBooks (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. It provides the overdue invoices, customer contacts, and notes the chase is built from; the skill does not run without it.
- Gmail (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. The skill needs one email provider to send or stage the follow-up emails, and Gmail or Outlook satisfies this; without an email provider it cannot deliver reminders.
- Outlook (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. The alternative email provider to Gmail; one of the two is needed so the skill can send the follow-up emails.
- Twilio (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only for the secondary SMS channel; if it is absent the skill falls back to email.


This skill also uses built-in Amazon Quick system tools. These are available by default (no install); manage them under Customize > Connectors (see https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html):
- `agent_management`: Agent management (built-in system tool) to create and trigger the scheduled routine (create_scheduled_agent) that runs the skill automatically.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask things like "who hasn't paid me", "what's overdue", "chase unpaid invoices", "send payment reminders", or "set up automatic reminders", and the skill drafts the follow-ups for your review before anything sends.
