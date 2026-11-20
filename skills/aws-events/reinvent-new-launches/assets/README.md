---
description: "Human-facing overview, prerequisites, installation, and getting started for the New Launches skill."
last_updated: 2026-11-04
origin: original
---

# reinvent-new-launches

Show the AWS launches announced around AWS re:Invent 2026, filtered to what the attendee cares about.

## Overview

New Launches cuts the full announcement list down to a day, a service, or a topic and shows each launch with:

- **Headline**: linked to the announcement
- **What it does**: one line from the launch summary
- **Topic**: such as Artificial Intelligence, Compute, or Serverless & Containers
- **Day**: the day it posted, in Las Vegas time

Newest first: every match when 25 or fewer match, otherwise the newest 20. For a day, the whole week, or every launch it says how many matched; for a service or topic it gives no count, and says when more matched than are shown. The list is the same for every attendee; asked for launches "for me" or "for my sessions", it matches them to the services in the attendee's own sessions or the topics they name, and says which session or topic each launch matches. At the end it offers to save the list as a **PDF**; when more matched than are shown, the PDF holds every match. Asked for all of them up front, it makes that PDF straight away.

## Pre-requisites

- **AWS Events Central (cloud connector, custom-remote MCP, cloud runtime, required):** the connector named exactly `AWS Events Central` in AWS Quick, signed in with your AWS Builder ID. In Quick it appears as the skill `quick_suite__aws_events_central`, which the skill loads at run time. The skill reads the launches through its `aws_events_central__event_get_new_launches` tool (`get_new_launches` on the MCP server). If the connector has a different name in your Quick, the skill finds it by the tool name ending in `get_new_launches`. Without it, the skill stops and asks you to enable it.
- **canvas_pdf (system tool, built into Quick, optional):** makes the PDF. It is pre-installed and marked with a System badge; make sure it is enabled in Customize > Skills.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Add the AWS Events Central connector and name it exactly `AWS Events Central`. For setup, see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html

## Getting started

Start with the help menu by saying: `riv launches help`.

Or just ask in plain language, for example:

- "What are the top AWS launches from re:Invent this year?"
- "What was announced today?"
- "What's new in Amazon Bedrock?"
- "Serverless launches this week"
- "What launched on Tuesday?"

## What it won't do

- It won't find **sessions** about a launch: that is Event Catalog.
- It won't speculate about embargoed or upcoming launches; it shows only what has posted.
- It won't invent launches, features, dates, or links the list doesn't contain.
