---
description: "Human-facing overview, prerequisites, installation, and getting started for the Daily Brief skill."
last_updated: 2026-11-23
origin: original
---

# reinvent-daily-brief

Brief the attendee on their AWS re:Invent 2026 agenda for the day and time they ask about, from the sessions they reserved and attended, on demand or every event day.

## Overview

Daily Brief gives the signed-in attendee their re:Invent 2026 agenda in the time it takes to read a text:

- **The right window**: what's left of today by default. From 5 PM it adds tomorrow. It can also show a named day, what's next, or the sessions around a time they give ("after 2 PM"), widened by 15 minutes so nothing just before or still running is missed.
- **Before and after the event**: asked before Monday Nov 30 for today, what's next, or no day at all, it says re:Invent hasn't started yet and asks which event day to show. After Friday Dec 4 it says re:Invent has ended and offers the trip report or a personalized pathway. A named event day always gets its brief.
- **A clean, scannable layout**: a two-line header (the day, then `<first> to <last> · Las Vegas time`), then sessions grouped under Morning, Afternoon, and Evening. Each session is a list item with the start time and full title, and a nested item with the short room (venue plus room name) and its status: `Reserved` before a session ends, `Attended` or `Not attended` after. No summaries, no table, and no key explaining the ticks. Every line that must stand alone is its own list item or paragraph, because the Quick mobile app joins lines split by a single line break.
- **Nothing left today**: when nothing remains today, it shows tomorrow's first session under `Nothing else today. First up tomorrow:`. Left out on Friday, the last day.
- **Markers**: in progress (Now) and starting within 30 minutes (Next), today only.
- **No clutter**: no overlap or travel warnings, since double-booking is normal, and no notes about data quirks.

At the end it offers to share the brief on **Slack**, draft it as an **Outlook** email, or **schedule** it. Before offering a schedule it checks for existing routines, and offers to change them instead of adding duplicates. Nothing is posted or sent until the attendee confirms the draft.

It ends with gentle follow-ups, such as what else is on that day or briefing the next day.

## Scheduled brief

In one turn, the skill shows today's brief and sets up one routine that posts to the attendee's Quick feed every event day, and a short card each morning before the event, in Las Vegas time:

- **re:Invent morning brief**: the day's plan. The sessions in start order with short rooms, `different venue` on a session that starts less than 15 minutes after the previous one ends at another venue (never on overlapping sessions or on a keynote), a count of all the day's venue changes in the lead line, and a last line that points to the AWS Events app for repeat sessions. With nothing reserved, the day's keynotes still ahead (or `No keynote today.` on a day without one), and no session recommendations of any kind. A `Tips for today` section after the plan copies that day's fixed tips from `references/day-tips.md` word for word (badge pickup, reserved seating, re:Play, bag check, and more); edit the tips there and re-run setup to pick them up. An `AWS launches yesterday` section after the tips holds up to three launches from the day before, matched to the day's sessions (or to the attendee's topics on a day with no sessions, or the three newest when nothing matches), each a linked headline with about 12 words on what it does; it is left out only when nothing launched or a launches call failed (a normal run makes 3 AWS Events Central calls and at most 4 with a retry), and no launch is named in the title or lead line. No attendance marks and no walking times.
- **The workday first**: with Slack or Outlook connected, the card leads with up to four work items, today's meetings from the Outlook calendar and the messages of the last 12 hours that need attention today, about re:Invent or not, each cited by connector and sender first name only (no channel, subject, or message words), never from noise such as bots or newsletters, and never in the card's title or lead line, which stay sessions and keynotes only. With neither connected, the card ends with one line inviting the attendee to connect Outlook or Slack, and a `Connect my work apps` choice that sets it up in chat.
- **Before the event**: the routine starts the day it is set up. Before Monday Nov 30 every run posts one short card with no agenda and no keynotes: the workday first, as on event days, then up to three launches from the day before. With neither to show (no launch, or a failed launches call, and no work item) the card is one line with the start date that points to the latest launches. The run judges Slack and Outlook from its own tools, as on event days: it reads only the apps it can reach, and with neither it reads none and the card ends with the same connect line and `Connect my work apps` choice. Its prompt names no work apps, so connecting one later needs no prompt edit. A run makes at most 2 AWS Events Central calls and at most 2 calls per connected app.
- **End date**: the routine has no start date and an end date of Friday Dec 4, 2026, 11:59 PM, Las Vegas time, and its prompt skips any run after that day on its own. Signing up after Friday Dec 4 sets up nothing and offers the trip report or a personalized pathway instead.
- **Topics**: the skill writes the topics a request names into the routine as one line of topic names (at most 8, each at most 40 characters), leaving out any other text in the request. The setup reply ends with the connect line whenever neither Slack nor Outlook is connected, followed by one card to connect Slack, connect Outlook, or skip; it asks no topics question.
- **One card a day**: the routine posts one notifying feed card every event day, with a title of at most 22 characters (the width the phone Feed card shows) and a lead line from the card's own sessions (never work messages, since a push shows them on a locked phone), and the full plan in `update_feed`'s `summary`, which Quick shows as the card's full message. When a call or the post fails, it still posts a short fallback card; when the agenda call fails, that card lists no keynotes.
- **Self-contained prompt**: the routine's prompt is a template in `references/`, with the day tips copied in at setup, so a run needs no skill and no files.
- **No routine link**: the setup confirmation names the time and how to stop the brief, with no link to the routine, since that link doesn't open from the Quick mobile app.
- **Changing the time** updates the same routine, then sets its end date again, because changing the time clears it.
- **Stop and delete**: asked to stop, the skill turns the routines off, an evening recap from an earlier setup included. It deletes one only when the attendee explicitly asks to delete or remove it, and Quick's approval prompt is the confirmation.
- **Least access**: the routine reads AWS Events Central and the current time, reads Slack and Outlook when they were connected at setup, and posts to the feed. Nothing else, and no web search.

## Starter prompts

The starter card sends this prompt, with a morning time it fills in at random between 6:00 and 8:59 AM, Las Vegas time:

`Set up my daily re:Invent brief at 7:43 AM, Las Vegas time.`

The same prompt with no time (`Set up my daily re:Invent brief.`) also works, as do a form with a recap time as well, which the skill ignores, and a bare `Set up my daily brief`.

A time in the request always wins and is saved exactly. When a prompt has no time, the skill computes one: each attendee's morning brief gets a minute between 6:00 and 8:59 AM, Las Vegas time (180 minutes), worked out from the clock reading at setup, so routines don't all run at once. A brief that arrives after a session or keynote has started marks it `Now`.

## Pre-requisites

- **AWS Events Central (cloud connector, custom-remote MCP, cloud runtime, required):** the connector named exactly `AWS Events Central` in AWS Quick, signed in with your AWS Builder ID. In Quick it appears as the skill `quick_suite__aws_events_central`, which the skill loads at run time. The skill reads the attendee's agenda through its `aws_events_central__event_get_daily_brief` tool (`get_daily_brief` on the MCP server). If the connector has a different name in your Quick, the skill finds it by the tool name ending in `get_daily_brief`. Without it, the skill stops and asks you to enable it.
- **Slack and Outlook (cloud connectors, cloud runtime, optional):** if present, the brief can be posted to Slack or emailed from Outlook, always as a draft the attendee confirms first. If absent, the brief is still shown in the chat and can be scheduled.
- **Gmail and Microsoft Teams (cloud connectors, cloud runtime, optional):** if connected, the morning card adds recent Gmail mail and the newest Teams chat to the workday section. If absent, the brief works without them.
- **Quick schedules, the Schedule Management skill (system tool, cloud runtime, optional):** runs the routine in the cloud, so the attendee's computer does not need to be on. It also sets its end date, time zone, and description. If the attendee's organization denies scheduled reads, or requires approving each one, the skill says so instead of creating a routine that can't post. The routine counts toward Quick's limit on schedules. Without schedules, the brief is still available any time on request.

## Installation

1. Download the skill and add it in Customize > Skills.
2. Add the AWS Events Central connector and name it exactly `AWS Events Central`. For setup, see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html
3. Optionally, install and enable Slack, Outlook, Gmail, and Microsoft Teams. For setup, see the same guide.

## Getting started

Start with the help menu by saying: `riv brief help`.

Or just ask in plain language, for example:

- "What's on my schedule today?"
- "Give me my daily brief"
- "What's next?"
- "What do I have after 2 PM on Wednesday?"
- "Brief me on Wednesday"
- "Set up my daily re:Invent brief"
- "Move my morning brief to 7 AM"
- "Do a test run of my morning brief"
- "Stop my re:Invent briefs"

## What it won't do

- It won't list sessions the attendee hasn't reserved: that is Event Catalog.
- It won't write up the whole week: that is Trip Report.
- It won't give directions or walking times, or reserve seats: those belong to the AWS Events app.
- It won't remind the attendee before each session. The routine posts once each event day; session reminders belong to the AWS Events app.
- It won't delete a routine unless the attendee explicitly asks it to. Routines end on their own after Friday Dec 4, or the attendee can remove one in Schedules.
- It won't show **another attendee's** agenda; it only sees the signed-in attendee's own.
