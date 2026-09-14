---
description: "Human-facing overview, prerequisites, installation, and getting started for the Deposit Collection skill."
last_updated: 2026-09-13
origin: original
---

# Deposit Collection

Collects a deposit before work starts, so the cash arrives before the labor and materials go out.

## Overview

Deposit Collection creates a deposit request in QuickBooks for a configurable percentage of a job, sends it with a payment link after your approval, confirms when the money clears, and records it correctly as a customer prepayment (a liability). When the job is done, it generates the final invoice for the remaining balance, netting the deposit already paid so the customer is never double-charged. It is built for field-service and project businesses that want cash down first, and it never creates, sends, or refunds anything without explicit owner approval.

## Pre-requisites

- QuickBooks (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. It holds the customer record and stores the deposit as a prepayment and the final invoice; the skill does not run without it.
- Gmail (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used to send the deposit request and final invoice; if it is absent the skill gives you the payment link to share manually.
- Outlook (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. An alternative email connector for the same send path, with the same manual fallback.
- PayPal (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Offered only as an additional payment link when the customer accepts it; otherwise the QuickBooks payment link is used.


This skill also uses built-in Amazon Quick system tools. These are available by default (no install); manage them under Customize > Connectors (see https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html):
- `memory_management`: Knowledge and memory (built-in system tool) to recall the owner's preferences and prior decisions across runs.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask things like "collect a deposit", "request a deposit", "get a deposit before I start", or "bill upfront" when a new job is booked, and the skill prepares the deposit request for your approval.
