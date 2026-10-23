---
description: "Human-facing overview, prerequisites, installation, and getting started for the skill-builder skill."
last_updated: 2026-10-22
origin: original
---

# skill-builder

Builds tested, reusable Amazon Quick agent skills from a description, an agent prompt, or an existing workflow.

## Overview

skill-builder turns an idea, a prompt, or a finished workflow into a skill that follows the Amazon Quick Skills Standard: structured SKILL.md, supporting files, and evals. It plans the skill with you, builds it in reviewable sections, audits it against the standard with a mechanical validator, and runs evals that score the skill against the agent alone and track the results over time. It is for anyone authoring skills for Amazon Quick who wants them consistent, self-contained, and verified rather than one-shot.

## Pre-requisites

None. skill-builder uses only built-in Amazon Quick tools (file operations, code execution, web search, and background tasks) and needs no external connectors, MCP servers, or coding agents.

## Installation

1. In Amazon Quick on desktop, go to Customize > Skills, choose Browse all, select the Official tab, and search for the skill by name. Choose Install. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html). Keep the `scripts/` directory alongside `SKILL.md`; the scripts (check_skill.py, create_benchmark.py, find_lines.py, create_checksum.py, create_script.py, create_reference_file.py, create_readme.py, record_event.py) are used at runtime.
2. Install and enable any connectors listed in Pre-requisites above. For connector setup, see https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html

## Getting started

Start with the help menu by saying: `sb help`.
