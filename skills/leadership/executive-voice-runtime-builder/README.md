---
description: "Human-facing overview, prerequisites, installation, and getting started for the Executive Voice Runtime Builder skill."
last_updated: 2026-09-13
origin: original
---

# Executive Voice Runtime Builder

Analyzes how a person writes and encodes it into a portable, machine-readable voice profile (engram) for drafting in their voice.

## Overview

This skill studies a person's writing structure, tone, rhythm, register routing, and vocabulary and captures them in a portable engram file the user owns, with calibration gates and a governance log. It is for leaders, ICs, and executive assistants who want drafts that sound like them without handing over business judgment or authority to act. It extends Amazon Quick by mining connected sources for writing samples when available, and falling back to guided elicitation or pasted samples when they are not.

## Pre-requisites

- Gmail (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Outlook (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Slack (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.
- Microsoft Teams (cloud connector, cloud runtime, optional): ensure it is installed, you are signed in, and it is enabled.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Install and enable the connectors listed above. For connector setup see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html and the per-integration guides at https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html . For MCP setup see https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html . To add a skill see https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask to "build a voice profile", "capture my writing voice", "create a voice engram", "refresh my voice model", or "does this sound like me". The skill routes to the right path based on how many writing samples are available.
