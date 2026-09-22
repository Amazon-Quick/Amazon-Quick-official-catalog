---
description: "README for selling-partner-knowledge: overview, the required Amazon Selling Partner built-in connector prerequisite, installation, and getting started."
last_updated: "2026-09-15"
origin: original
---

# Selling Partner Knowledge (`selling-partner-knowledge`)

Answers Selling Partner API (SP-API) developer questions and guides developers from idea to design to code, grounded strictly in the SP-API documentation knowledge base, read-only, with a visual on every turn.

## Overview
Searches the SP-API docs first, fetches full content, routes by question shape (factual lookup, how it works, getting started, which API, does-X-support, build, design, code), and pairs every answer with a rendered mermaid diagram or table. It never answers from general knowledge, and it never changes a seller account. For live account metrics it points to selling-partner-seller-analytics; for account actions it points to the transactional selling-partner skills.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the read-only SP-API knowledge operations this skill uses (documentation search, full-document fetch, section browse, and operation-spec lookup).
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot retrieve documentation, and it must not answer SP-API questions from general knowledge.

The connector is offered during Amazon Quick onboarding. If the developer connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
Ask an SP-API developer question, for example "how does the Feeds upload flow work?" or "which SP-API should I use to get my orders and buyer info?", and the skill will search the docs, answer grounded in what it retrieves, and render a diagram or table alongside the answer. Ask it to design an integration or write code and it produces a grounded proposal artifact or SDK-based code with a workflow diagram.
