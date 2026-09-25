---
description: "Human-facing overview, pre-requisites, and getting-started for the personal-agent-architect skill."
last_updated: "2026-09-24"
origin: original
---

# personal-agent-architect

Builds a person a matched personalization set from their own Amazon Quick environment: a personal voice-and-preference skill, a space preloaded with the data they use often, and a lightweight agent wired to both.

## Overview
Personal Agent Architect reads what is already true about a person (memories, knowledge graph, past conversations, installed skills, connectors, and frequently-used data) and turns it into a working set they can use immediately, rather than asking them to configure an agent by hand. It is portable: it relies only on the tools, connectors, and data the current user has access to.

## Pre-requisites
This skill composes other built-in skills and one optional connector category. It depends on each built-in skill by capability, not by exact name: the running agent loads whichever installed skill currently provides the capability, matching by function if an identifier has changed. The names below are the current examples at time of writing.

- Type: built-in skills. Runtime: cloud agent runtime (no local machine needed). Required. Depended on by capability, currently:
  - Writing-style / voice cloning (currently engram_builder)
  - Agent creation (currently chat_agent_builder)
  - Space creation and document upload (currently quick_suite__spaces)
  - Skill authoring (currently skill-builder)
  - Past-conversation search (currently conversation_management)
  - Knowledge-graph search (currently knowledge_graph)
- Type: cloud connector. Runtime: cloud agent runtime (no local machine needed). Optional. A messaging or email connector (for example Slack, Outlook, or Gmail), used to build the voice engram and extract role signal. Without one, the run continues with a reduced voice and role profile.

## Installation
1. In Amazon Quick, go to Customize > Skills > Browse more, choose Official, and search for "Personal Agent Architect", then add it.
2. Enable the connectors you want available. For setup, follow the reference docs listed in this skill's <Resources>.

## Getting started
Say `paa help` to see the commands, or `paa build` to start.
