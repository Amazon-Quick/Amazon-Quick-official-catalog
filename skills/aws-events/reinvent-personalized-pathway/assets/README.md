---
description: "Human-facing overview, prerequisites, installation, and getting started for the Personalized Pathway skill."
last_updated: 2026-11-04
origin: original
---

# reinvent-personalized-pathway

Recommend the AWS Skill Builder training an attendee should take after re:Invent 2026, from the sessions they attended and registered for.

## Overview

Personalized Pathway connects what the signed-in attendee saw at re:Invent 2026 to what they should learn next, from about 2,000 English AWS Training and Certification courses on AWS Skill Builder. It covers:

- **Digital courses**: self-paced courses and videos
- **Hands-on labs**: Builder Labs in a real AWS console
- **Simulations and games**: AWS SimuLearn, Cloud Quest, Industry Quest, escape rooms, and AWS Jam
- **Certification exam prep**: for 12 AWS Certifications, such as Solutions Architect Associate or AI Practitioner: exam prep plans, domain reviews, practice question sets, SimuLearn practice, escape rooms, and recertification

A misspelled service, such as "Kubernets", still finds its courses, and the skill says what it searched.

It narrows to what the attendee asks, such as an AWS service, a topic, a job role, a certification, a level, a format, free courses, or a time budget, and lays the picks out as a path, start here, then next, then stretch, with format, level, duration, whether it is free, and a link for each. It is personalized to the signed-in attendee and works during and after the event.

At the end of the first learning path in a conversation, it adds two or three chapters of the AWS report *Reimagine: Turning AI into Value* that match their sessions or request, or two starting chapters when none match. Later refinements leave it out unless the attendee asks for business, leadership, executive, or AI-strategy reading.

## Pre-requisites

- **AWS Events Central (cloud connector, custom-remote MCP, cloud runtime, required):** the connector named exactly `AWS Events Central` in AWS Quick, signed in with your AWS Builder ID. In Quick it appears as the skill `quick_suite__aws_events_central`, which the skill loads at run time. The skill reads the attendee's session interests and the Skill Builder courses through its `aws_events_central__event_get_personalized_pathway` tool (`get_personalized_pathway` on the MCP server). If the connector has a different name in your Quick, the skill finds it by the tool name ending in `get_personalized_pathway`. Without it, the skill stops and asks you to enable it.
- **Slack and Outlook (cloud connectors, cloud runtime, optional):** if present, the path can be posted to Slack or emailed from Outlook, always as a draft the attendee confirms first. If absent, the path is still offered as a PDF study plan.
- **canvas_pdf (system tool, built into Quick, optional):** makes the PDF. It is pre-installed and marked with a System badge; make sure it is enabled in Customize > Skills.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Add the AWS Events Central connector and name it exactly `AWS Events Central`. For setup, see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html
3. Optionally, install and enable Slack and Outlook. For setup, see the same guide.

## Getting started

Start with the help menu by saying: `riv pathway help`.

Or just ask in plain language, for example:

- "What should I learn next based on the sessions I attended?"
- "Free beginner Lambda lab under 45 minutes"
- "How do I prepare for the AWS Certified AI Practitioner exam?"
- "Something on generative AI for business leaders, not too technical"
- "Build me a 4 week learning plan after re:Invent"

## What it won't do

- It won't find **sessions at the event**: that is Event Catalog.
- It won't show **another attendee's** sessions or courses; it only sees the signed-in attendee's own.
- It won't invent courses, prices, durations, or links the data doesn't contain, or promise a certification outcome.
