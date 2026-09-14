---
description: "Human-facing overview, prerequisites, installation, and getting started for the Instant Invoice skill."
last_updated: 2026-09-13
origin: original
---

# Instant Invoice

Creates and sends an invoice as soon as a job is complete, pulling customer and terms straight from QuickBooks.

## Overview

Instant Invoice generates a professional invoice from chat the moment a job is done: it looks up the customer in QuickBooks, assembles the line items, applies tax and any prior deposit, requests your approval, sends the invoice with payment instructions, and schedules a follow-up reminder. It is built for field-service businesses like plumbers, HVAC technicians, landscapers, and consultants that need to invoice promptly without switching between accounting software and email. Creating and sending each happen only after an explicit approval.

## Pre-requisites

- QuickBooks (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. It is the source of truth for customers, terms, tax status, and where the invoice is created; the skill does not run without it.
- Gmail (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used to email the created invoice; if it is absent the invoice still exists in QuickBooks and the skill gives you the link to share manually.
- Outlook (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. An alternative email connector for the same send step, with the same manual fallback.
- PayPal (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled. Used only to add an alternative payment link to the email; it is skipped silently when not connected.


This skill also uses built-in Amazon Quick system tools. These are available by default (no install); manage them under Customize > Connectors (see https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html):
- `agent_management`: Agent management (built-in system tool) to create and trigger the scheduled routine (create_scheduled_agent) that runs the skill automatically.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Say things like "invoice the job", "send invoice", "bill the customer", or "get me paid", or describe the work you just finished, and the skill prepares the invoice for your approval before it sends.
