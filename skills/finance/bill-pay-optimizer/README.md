---
description: "Human-facing overview, prerequisites, installation, and getting started for the Bill Pay Optimizer skill."
last_updated: 2026-09-13
origin: original
---

# Bill Pay Optimizer

Turns your QuickBooks accounts payable into a prioritized pay-now-versus-defer plan that respects a minimum cash buffer.

## Overview

Bill Pay Optimizer pulls your open bills from QuickBooks, compares them to your available cash, and recommends which to pay now and which can safely wait, while flagging early-pay discounts and likely errors. It is built for small business owners who want a clear accounts-payable plan without logging into multiple tools. It is strictly read-only: it prepares a ready-to-pay list you action yourself and never moves money or writes to QuickBooks.

## Pre-requisites

- QuickBooks (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. It provides the open bills and cash balances the plan is built from; the skill does not run without it.
- Gmail (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only to scan for incoming vendor-invoice emails that are not yet in QuickBooks; the plan runs without it.
- Outlook (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. An alternative email connector for the same vendor-invoice scan; the plan runs without it.
- Google Calendar (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only to set optional bill-due reminders when you ask for them.
- Slack (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only to post optional reminders and notifications.


This skill also uses built-in Amazon Quick system tools. These are available by default (no install); manage them under Customize > Connectors (see https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html):
- `agent_management`: Agent management (built-in system tool) to create and trigger the optional scheduled routine.
- `memory_management`: Knowledge and memory (built-in system tool) to recall the owner's preferences and prior decisions across runs.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask things like "what bills do I need to pay", "what's due this week", "which bills can wait", or "optimize my payments", and the skill returns a prioritized plan with your projected cash position after paying.
