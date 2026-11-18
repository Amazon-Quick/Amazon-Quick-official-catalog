---
description: "Setup guide for the AWS Partner Deal Progression and Sales Play skill: what it needs connected and how to start."
last_updated: 2026-11-16
origin: original
---

# AWS Partner Deal Progression and Sales Play

Setup guide for the AWS Partner Deal Progression and Sales Play skill: what it needs connected and how to start.

## Overview

Goes deep on one AWS co-sell opportunity: checks its stage gate, names the one blocker, benchmarks it against the customer's past deals, and gets a tailored sales play from Partner Central.

## Pre-requisites

| Dependency | Type | Connector | Runs in | Required? |
|---|---|---|---|---|
| AWS Partner Central | Remote MCP connector | AWS Partner Central MCP server | Cloud | Required |
| Chat | Cloud connector | Chat (for example, Slack or Microsoft Teams) | Cloud | Optional |
| Email and calendar | Cloud connector | Email and calendar (for example, Outlook or Gmail) | Cloud | Optional |
If a required dependency is missing, the skill stops and tells you which one to connect. If an optional one is missing, the skill continues and says what it could not check.

## Installation

1. Install this skill from Customize > Skills. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. Connect the AWS Partner Central MCP server as a custom remote MCP connector. See [Custom MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html).
3. Connect any optional connectors you want from the table above. See [Connections](https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html).

## Getting started

Say "help me prepare for my AWS opportunity with Acme" or "what is blocking this AWS opportunity".