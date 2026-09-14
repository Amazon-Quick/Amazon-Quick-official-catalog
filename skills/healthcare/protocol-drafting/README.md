---
description: "Human-facing overview, prerequisites, installation, and getting started for the Clinical Trial Protocol Drafting skill."
last_updated: 2026-09-13
origin: original
---

# Clinical Trial Protocol Drafting

Drafts ICH- and FDA-grounded clinical trial protocol sections from a grant document or study synopsis.

## Overview

This skill turns a research source document into IRB-ready protocol text, producing Objectives, Background and Rationale, and Study Design sections and assembling them into a cohesive protocol. It is for clinical researchers, medical writers, and regulatory affairs staff who need a defensible first draft grounded in ICH E6/E8/E9 and 21 CFR Part 312. It extends Amazon Quick by pulling authoritative regulatory text through MCP servers and presenting each section for human review before proceeding, flagging gaps rather than fabricating content.

## Pre-requisites

Both MCP servers must be connected to Amazon Quick before use. Without them, the skill cannot retrieve authoritative regulatory text and will not function.

- fda-ecfr (custom/remote MCP server, required): retrieves 21 CFR regulatory text from the public FDA eCFR API. Source and setup: https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/tree/main/mcp-servers/agentcore-gateway/fda-ecfr
- awslabs.bedrock-kb-retrieval-mcp-server (custom/remote MCP server, required): queries ICH guideline content (E6, E8, E9) via an Amazon Bedrock Knowledge Base. Source and setup: https://github.com/awslabs/mcp/tree/main/src/bedrock-kb-retrieval-mcp-server

## Installation

1. Deploy the two MCP servers listed above from their source repositories.
2. Connect each deployed server to Amazon Quick as a remotely hosted MCP server. The path depends on your surface:
   - Desktop app: Customize > Connectors, then Create > Cloud Connector (a remotely hosted MCP server is added as a cloud connector). See https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html
   - Web console: Connectors > Create for your team > Model Context Protocol (MCP). See https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html
3. Add this skill: https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Provide a grant or synopsis and ask to "draft a clinical trial protocol", "write protocol objectives from this grant", or "generate a study design section". The skill drafts one section at a time and waits for your approval before continuing.
