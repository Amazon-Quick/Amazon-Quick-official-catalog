---
description: "Human-facing overview, prerequisites, installation, and getting started for the skill-builder skill."
last_updated: 2026-09-13
origin: original
---

# skill-builder

Builds tested, reusable Amazon Quick agent skills from a description, an agent prompt, or an existing workflow.

## Overview

skill-builder turns an idea, a prompt, or a finished workflow into a skill that follows the Amazon Quick Skills Standard: structured SKILL.md, supporting files, and evals. It plans the skill with you, builds it in reviewable sections, audits it against the standard with a mechanical validator, and runs an eval loop that measures the skill against a no-skill baseline. It is for anyone authoring skills for Amazon Quick who wants them consistent, self-contained, and verified rather than one-shot.

## Pre-requisites

None. skill-builder uses only built-in Amazon Quick tools (file operations, code execution, web search, and background tasks) and needs no external connectors, MCP servers, or coding agents.

## Installation

1. Download the skill and add it in Customize > Skills. Keep the `scripts/` directory alongside `SKILL.md`; the scripts (check_skill.py, create_benchmark.py, find_lines.py, create_checksum.py, create_script.py, create_reference_file.py, create_readme.py) are used at runtime.
2. For how to add a skill, see the reference doc: <https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html>

## Getting started

Start with the help menu by saying: `sb help`.
