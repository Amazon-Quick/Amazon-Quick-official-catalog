---
description: "Setup guide for the AWS Partner Funding Eligibility Check skill: what it needs connected and how to start."
last_updated: 2026-11-16
origin: original
---

# AWS Partner Funding Eligibility Check

Setup guide for the AWS Partner Funding Eligibility Check skill: what it needs connected and how to start.

## Overview

Checks which AWS Partner funding programs a co-sell opportunity is eligible to apply for, using Partner Central's funding-recommendation capability, and can draft (never submit) a fund request.

## Pre-requisites

| Dependency | Type | Connector | Runs in | Required? |
|---|---|---|---|---|
| AWS Partner Central | Remote MCP connector | AWS Partner Central MCP server | Cloud | Required |
If a required dependency is missing, the skill stops and tells you which one to connect. If an optional one is missing, the skill continues and says what it could not check.

## Installation

1. Install this skill from Customize > Skills. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. Connect the AWS Partner Central MCP server as a custom remote MCP connector. See [Custom MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html).
3. Connect any optional connectors you want from the table above. See [Connections](https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html).

## Getting started

Say "what AWS funding does opportunity O1234567 qualify for" or "how does MAP funding work".