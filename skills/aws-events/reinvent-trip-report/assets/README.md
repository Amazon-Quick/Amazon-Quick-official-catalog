---
description: "Human-facing overview, prerequisites, installation, and getting started for the Trip Report skill."
last_updated: 2026-11-04
origin: original
---

# reinvent-trip-report

Draft the attendee's AWS re:Invent 2026 trip report, day by day, from the sessions they attended and the booths they visited.

## Overview

Trip Report turns the signed-in attendee's re:Invent 2026 week into a report they can share with their manager or team:

- **Day by day**: one section per event day
- **Sessions attended**: a table of title, what it covered, type, and room
- **Booths visited**: a list of booth names
- **Highlights**: up to three themes, drawn only from what the attended sessions covered, with an invitation to add your own takeaways
- **Further reading**: two or three chapters of the AWS report *Reimagine: Turning AI into Value* that fit the attended sessions, or two starting chapters when none fits, with a link to the report, at the end of every full report

At the end it always offers to save the report as a **PDF**, share it on **Slack**, or draft it as an **Outlook** email. If Slack or Outlook isn't connected yet, it asks you to connect it first. Nothing is posted or sent until the attendee confirms the draft.

Before re:Invent starts on Monday Nov 30, it says the report fills in once the event begins.

Booths are placed on the day they were scanned. Visits from before scan times were recorded are listed under "Other booths visited".

It ends with gentle follow-ups, such as generating a personalized pathway or new launches for the attendee's main topic, which the Personalized Pathway and New Launches skills answer.

## Pre-requisites

- **AWS Events Central (cloud connector, custom-remote MCP, cloud runtime, required):** the connector named exactly `AWS Events Central` in AWS Quick, signed in with your AWS Builder ID. In Quick it appears as the skill `quick_suite__aws_events_central`, which the skill loads at run time. The skill reads the attendee's activity through its `aws_events_central__event_get_trip_report` tool (`get_trip_report` on the MCP server). If the connector has a different name in your Quick, the skill finds it by the tool name ending in `get_trip_report`. Without it, the skill stops and asks you to enable it.
- **Slack and Outlook (cloud connectors, cloud runtime, optional):** the report can be posted to Slack or emailed from Outlook, always as a draft the attendee confirms first. Both are always offered; when the one picked isn't connected, the skill asks you to connect it and offers the PDF meanwhile.
- **canvas_pdf (system tool, built into Quick, optional):** makes the PDF. It is pre-installed and marked with a System badge; make sure it is enabled in Customize > Skills.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Add the AWS Events Central connector and name it exactly `AWS Events Central`. For setup, see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html
3. Optionally, install and enable Slack and Outlook. For setup, see the same guide.

## Getting started

Start with the help menu by saying: `riv report help`.

Or just ask in plain language, for example:

- "Write my re:Invent trip report"
- "Summarize my week at re:Invent for my manager"
- "What did I do on Tuesday?"

## What it won't do

- It won't list sessions the attendee only **reserved**: that is Daily Brief.
- It won't show **another attendee's** activity; it only sees the signed-in attendee's own.
- It won't invent sessions, booths, times, or takeaways the data doesn't contain.
