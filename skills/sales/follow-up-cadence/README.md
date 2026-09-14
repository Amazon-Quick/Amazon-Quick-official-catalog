---
description: "Human-facing overview, prerequisites, installation, and getting started for the follow-up-cadence skill."
last_updated: 2026-09-13
origin: original
---

# Follow-Up Cadence

Adds strategic follow-up sequences that keep sales momentum without sounding pushy.

## Overview

Follow-Up Cadence drafts context-aware follow-ups for meetings, proposals, events, cold leads, and post-purchase check-ins, then tracks each touch in a persistent ledger with reminders for the next action. It is for small business sellers who owe follow-ups and want every message to add new value. It extends Amazon Quick by pulling prior email and calendar context when available and staging or sending drafts, with a chat fallback when no connector is present.

## Pre-requisites

- Outlook (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Gmail (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Google Sheets (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Google Calendar (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used on the Gmail path to find the most recent meeting with a contact; meeting lookups are skipped silently if no calendar is connected.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask things like "follow up with [client]", "write a follow-up email", "send a recap", or "what follow-ups do I owe" to draft a single message or run a batch review.
