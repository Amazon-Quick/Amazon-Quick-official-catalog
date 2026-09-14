---
description: "Human-facing overview, prerequisites, installation, and getting started for the OOO Setup skill."
last_updated: 2026-09-13
origin: original
---

# OOO Setup

Automates full out-of-office setup: meeting conflict resolution, calendar invites with smart recipient discovery, messaging status, email auto-reply drafts, and signature updates.

## Overview

This skill solves the chore of bouncing between apps to prepare for leave. It reads your calendar history to discover who to notify, groups them into tiers, resolves meeting conflicts, and walks through each action with explicit confirmation before anything sends. It is for anyone taking PTO or leave, and it extends Amazon Quick by coordinating calendar, messaging, and email actions from one guided workflow.

## Pre-requisites

- Outlook (cloud connector, cloud runtime, required): ensure it is installed, you are signed in, and it is enabled.
- Gmail (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Slack (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Microsoft Teams (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Invoke the skill with a request like "set up out of office", "going on PTO", "block my calendar for vacation", or "notify team about time off". Provide your leave dates and it will resolve conflicts, build the invite, and set your status after you confirm each step. A calendar provider (Outlook, or Teams as an alternative) is needed for the core flow; Slack, Teams, and Gmail support the messaging and email steps.
