---
description: "Human-facing overview, prerequisites, installation, and getting started for the Business Pulse skill."
last_updated: 2026-09-13
origin: original
---

# Business Pulse

Delivers a plain-language business health briefing by synthesizing your cash, receivables, payables, schedule, and anomalies from QuickBooks.

## Overview

Business Pulse produces a briefing you can read in under 60 seconds: cash position, money owed to you with aging, bills due this week, anything unusual worth a look, and a short narrative. It is built for owner-operators who want to start the day informed without opening several apps. It reads data only and never moves money or changes records, and it can optionally add calendar, email, and Slack context.

## Pre-requisites

- QuickBooks (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. It supplies every dollar figure in the briefing; the skill does not run without it.
- Google Calendar (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only to add today's schedule section; the briefing is delivered without it.
- Outlook (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. An optional calendar or email connector used only for the schedule and email-signals sections.
- Gmail (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only for the optional email-signals section that surfaces payment and invoice activity.
- Slack (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only as an optional delivery channel for the briefing.


This skill also uses built-in Amazon Quick system tools. These are available by default (no install); manage them under Customize > Connectors (see https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html):
- `agent_management`: Agent management (built-in system tool) to create and trigger the optional scheduled routine.
- `memory_management`: Knowledge and memory (built-in system tool) to recall the owner's preferences and prior decisions across runs.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask things like "how's my business doing", "give me my morning briefing", "what's my cash position", or "who owes me money", and the skill assembles and delivers the full briefing.
