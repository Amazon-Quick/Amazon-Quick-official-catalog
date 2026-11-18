---
description: "Setup guide for the AWS Partner Pipeline Health Check skill: what it needs connected and how to start."
last_updated: 2026-11-16
origin: original
---

# AWS Partner Pipeline Health Check

Setup guide for the AWS Partner Pipeline Health Check skill: what it needs connected and how to start.

## Overview

Gives a partner sales leader a ranked briefing of their open AWS co-sell pipeline: at-risk and stalled deals, customers waiting on a reply, and the three actions that matter most this week. Partner Central supplies the deals. Email, calendar and chat show whether customers are engaging.

## Pre-requisites

| Dependency | Type | Connector | Runs in | Required? |
|---|---|---|---|---|
| AWS Partner Central | Remote MCP connector | AWS Partner Central MCP server | Cloud | Required |
| Email and calendar | Cloud connector | Email and calendar (for example, Outlook or Gmail) | Cloud | Optional |
| Chat | Cloud connector | Chat (for example, Slack or Microsoft Teams) | Cloud | Optional |
| CRM | Cloud connector | CRM (for example, Salesforce) | Cloud | Optional, for the closed-deal check |
If a required dependency is missing, the skill stops and tells you which one to connect. If an optional one is missing, the skill continues and says what it could not check.

## Installation

1. Install this skill from Customize > Skills. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. Connect the AWS Partner Central MCP server as a custom remote MCP connector. See [Custom MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html).
3. Connect any optional connectors you want from the table above. See [Connections](https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html).

## Getting started

Say "run my ACE pipeline health check" or "which AWS co-sell deals need my attention".