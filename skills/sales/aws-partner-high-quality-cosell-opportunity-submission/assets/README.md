---
description: "Setup guide for the AWS Partner High-Quality Co-sell Opportunity Submission skill: what it needs connected and how to start."
last_updated: 2026-11-16
origin: original
---

# AWS Partner High-Quality Co-sell Opportunity Submission

Setup guide for the AWS Partner High-Quality Co-sell Opportunity Submission skill: what it needs connected and how to start.

## Overview

Turns notes, call summaries or emails into a submission-ready AWS co-sell opportunity, and reviews existing opportunities before you submit. Drafting and review work without any connector. Creating, updating or submitting in Partner Central needs the Partner Central connector.

## Pre-requisites

| Dependency | Type | Connector | Runs in | Required? |
|---|---|---|---|---|
| AWS Partner Central | Remote MCP connector | AWS Partner Central MCP server | Cloud | Required to create, update or submit. Not needed to draft or review |
If a required dependency is missing, the skill stops and tells you which one to connect. If an optional one is missing, the skill continues and says what it could not check.

## Installation

1. Install this skill from Customize > Skills. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. Connect the AWS Partner Central MCP server as a custom remote MCP connector. See [Custom MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html).
3. Connect any optional connectors you want from the table above. See [Connections](https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html).

## Getting started

Say "create an AWS co-sell opportunity from these notes" or "review my AWS opportunity before submitting".