---
description: "Setup guide for the AWS Partner Weekly Digest skill: what it needs connected and how to start."
last_updated: 2026-11-16
origin: original
---

# AWS Partner Weekly Digest

Setup guide for the AWS Partner Weekly Digest skill: what it needs connected and how to start.

## Overview

Compiles one ranked weekly view of what needs a partner's attention across their AWS partnership, delivered on a schedule or on demand.

## Pre-requisites

| Dependency | Type | Connector | Runs in | Required? |
|---|---|---|---|---|
| AWS Partner Central | Remote MCP connector | AWS Partner Central MCP server | Cloud | Required |
| AWS Marketplace | Remote MCP connector | AWS Marketplace MCP server | Cloud | Optional, used automatically for Marketplace sections |
| Chat | Cloud connector | Chat (for example, Slack) | Cloud | Optional, for support signals and delivery |
| Email | Cloud connector | Email (for example, Outlook or Gmail) | Cloud | Optional, for support signals and delivery |
If a required dependency is missing, the skill stops and tells you which one to connect. If an optional one is missing, the skill continues and says what it could not check.

## Installation

1. Install this skill from Customize > Skills. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. Connect the AWS Partner Central MCP server as a custom remote MCP connector. See [Custom MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html).
3. Connect any optional connectors you want from the table above. See [Connections](https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html).
4. Before relying on scheduled delivery, read `references/installation.md`. It explains when scheduled runs happen and results that look like faults.

## Getting started

Say "set up my AWS Partner digest". Setup takes about ten minutes and saves nothing until you finish.