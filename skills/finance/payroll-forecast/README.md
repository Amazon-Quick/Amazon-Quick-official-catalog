---
description: "Human-facing overview, prerequisites, installation, and getting started for the Payday Cash Projection skill."
last_updated: 2026-09-13
origin: original
---

# Payday Cash Projection

Projects whether you can cover payroll on an upcoming payday using only the cash you actually control.

## Overview

Payday Cash Projection answers "can I make payroll?" conservatively: it computes a cash floor from cleared bank cash minus your buffer minus every must-pay obligation due before payday, and issues a covered-or-short verdict. It is built for small business owners who need a reliable payroll go/no-go, and it shows expected invoice collections only as separately labeled upside, never as part of the verdict. The skill is read-only and never moves money or runs payroll.

## Pre-requisites

- QuickBooks (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled. It supplies the bank balances, payroll liabilities, bills, and obligations the projection is built from; the skill does not run without it.


This skill also uses built-in Amazon Quick system tools. These are available by default (no install); manage them under Customize > Connectors (see https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html):
- `agent_management`: Agent management (built-in system tool) to create and trigger the optional scheduled routine.
- `memory_management`: Knowledge and memory (built-in system tool) to recall the owner's preferences and prior decisions across runs.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask things like "will I make payroll", "can I make payroll this week", "payday cash check", or "project cash for payday", and the skill returns a conservative covered-or-short verdict with the days until payday.
