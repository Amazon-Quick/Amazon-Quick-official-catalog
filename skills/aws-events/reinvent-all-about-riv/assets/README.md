---
description: "Human-facing overview, prerequisites, installation, and getting started for the All About re:Invent skill."
last_updated: 2026-11-04
origin: original
---

# reinvent-all-about-riv

Answer AWS re:Invent 2026 attendee questions about how the event works, in plain language, from the official event FAQ.

## Overview

All About re:Invent is the attendee's plain-language answer desk for re:Invent 2026. It answers from the official event FAQ behind the AWS Events Central connector:

- **General**: Wi-Fi, meals, lost and found, registration, age requirement, who to contact
- **Badge pickup**: check-in requirements, pickup locations and dates, lanyard policy, reprints, recycling
- **Content and sessions**: session formats, venues, what to bring, agenda, on-demand
- **Reserved seating**: what it is, included session types, how it works, favoriting versus reserving
- **Accessibility**: services available to all, and services available by advance request
- **Safety**: code of conduct, security measures, bag and screening policy

For reserving seats, wayfinding between venues, and shuttle schedules, it points attendees to the **AWS Events app**. The event runs November 30 to December 4, 2026 in Las Vegas.

## Pre-requisites

- **AWS Events Central (cloud connector, custom-remote MCP, cloud runtime, required):** the connector named exactly `AWS Events Central` in AWS Quick, signed in with your AWS Builder ID. In Quick it appears as the skill `quick_suite__aws_events_central`, which the skill loads at run time. The skill reads the event FAQ through its `aws_events_central__event_get_all_about_reinvent` tool (`get_all_about_reinvent` on the MCP server). If the connector has a different name in your Quick, the skill finds it by the tool name ending in `get_all_about_reinvent`. Without it, the skill stops and asks you to enable it.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Add the AWS Events Central connector and name it exactly `AWS Events Central`. For setup, see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html

## Getting started

Start with the help menu by saying: `riv faq help`.

Or just ask in plain language, for example:

- "What's the Wi-Fi password?"
- "Where do I pick up my badge?"
- "How does reserved seating work?"
- "What accessibility services are available?"

## What it won't do

- It won't **reserve** seats, give **turn-by-turn directions**, or provide **shuttle times**: those live in the AWS Events app.
- It won't invent facts. For anything it can't answer, it points you to the AWS Events app, a help desk, or the re:Invent support email.
