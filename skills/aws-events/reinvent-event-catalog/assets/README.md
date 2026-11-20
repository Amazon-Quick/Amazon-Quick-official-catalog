---
description: "Human-facing overview, prerequisites, installation, and getting started for the Event Catalog skill."
last_updated: 2026-11-04
origin: original
---

# reinvent-event-catalog

Find AWS re:Invent 2026 sessions by topic, AWS service, speaker, day, time, venue, or session type.

## Overview

Event Catalog turns an attendee's question about what is on at re:Invent 2026 into one precise session search and hands back a short list in time order: day, start time in Las Vegas time, title, and room. It can filter by:

- **AWS service or subject**: whole words in a session's title, abstract, or service tags, such as Amazon Bedrock, Apache Iceberg, or Kubernetes, forgiving a typo in a long word
- **Speaker**: a full name, or a first or last name alone
- **Day**: Monday November 30 to Friday December 4
- **Start time**: after or before a time, such as "after 2 PM" or "this morning"
- **Venue**: Caesars Forum, Caesars Palace, MGM Grand, Venetian, Wynn Encore, or Caesars for both Caesars venues
- **Session type**: breakout, chalk talk, workshop, builders session, lightning talk, code talk, lab, gamified learning, bootcamp, exam prep, keynote, mainstage, featured experience, event service
- **Level, topic, format, job role, and area of interest**: the event's own values, such as 300 Advanced, Security and Identity, Hands-on, DevOps Engineer, or Agentic AI; "beginner" means 100 Foundational

A misspelled service or speaker, such as "Kubernets", still finds its sessions, and the skill says what it searched. When a partial name matches several speakers, such as two people named Alex, it asks which one you meant.

When more than 20 sessions match, it shows 20 at a time in start order and says so; ask for more to see the next 20. Asked for all of them, it shows every match in the chat when there are 50 or fewer, and saves them as a **PDF** when there are more. Before the event week, "right now" gets the event dates and an offer of Monday.

On request it also shows what a session covers, who is speaking, and when it repeats during the week; a repeat is listed as its own session with the same title. The sessions are the same for every attendee.

## Pre-requisites

- **AWS Events Central (cloud connector, custom-remote MCP, cloud runtime, required):** the connector named exactly `AWS Events Central` in AWS Quick, signed in with your AWS Builder ID. In Quick it appears as the skill `quick_suite__aws_events_central`, which the skill loads at run time. The skill searches the sessions through its `aws_events_central__event_get_event_catalog` tool (`get_event_catalog` on the MCP server). If the connector has a different name in your Quick, the skill finds it by the tool name ending in `get_event_catalog`. Without it, the skill stops and asks you to enable it.
- **canvas_pdf (system tool, built into Quick, optional):** makes the PDF of every match when the attendee asks for all of more than 50. It is pre-installed and marked with a System badge; make sure it is enabled in Customize > Skills.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Add the AWS Events Central connector and name it exactly `AWS Events Central`. For setup, see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html

## Getting started

Start with the help menu by saying: `riv sessions help`.

Or just ask in plain language, for example:

- "What AWS Quick sessions are on Tuesday afternoon?"
- "Workshops at the Venetian after 2 PM on Wednesday"
- "What's happening right now?"
- "Is there a repeat of the Apache Iceberg Redshift session later in the week?"
- "Give me a Tuesday plan of serverless sessions with no overlaps"
- "What sessions is <speaker name> speaking at?"
- "Advanced hands-on security sessions for architects"

## What it won't do

- It won't **reserve** seats, give **turn-by-turn directions**, or provide **shuttle times**: those live in the AWS Events app.
- It won't show the attendee's **own reserved sessions**: that is Daily Brief.
- It won't recommend **Skill Builder courses** to take after the event: that is Personalized Pathway.
- It won't invent sessions, times, rooms, or speakers the session data doesn't contain.
