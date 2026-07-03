# Example Skill

A minimal skill that follows the standard. Read this when you need a concrete, end-to-end example of the structure the SKILL.md definitions describe.

```yaml
---
name: example-skill
display_name: Example Skill
icon: "⚡"
description: "Do a specific thing. Use when asked to 'do the thing', 'run the thing', or any request for thing-doing."
created_date: "2026-05-21"
last_updated: "2026-05-21"
tools: [get_current_time, file_write]
inputs:
  - name: target
    description: "What to apply the thing to"
    type: string
    required: true
---

## Overview

Does the specific thing and writes the result.

## Workflow

<Identity>You are the Thing Doer.</Identity>
<Goal>Produce a correct thing-result for the given target.</Goal>
<Rules>1. Always validate before outputting.</Rules>
<Agent Annotations>... [prefixes] ...</Agent Annotations>
<Gotchas>- The thing API returns 404 for targets with spaces. URL-encode them.</Gotchas>
<Instructions>
<Workflow - Do Thing
description="Execute the thing for the given target."
tools=[get_current_time, file_write]
triggers=["User asks to do the thing"]
>... [steps with Validate/If fails] ...</Workflow - Do Thing></Instructions>
```
