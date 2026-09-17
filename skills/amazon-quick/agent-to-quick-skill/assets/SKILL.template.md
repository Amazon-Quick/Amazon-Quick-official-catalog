---
name: <kebab-case-name>            # must match the folder name
display_name: <Human Readable Name>
description: "<what it does, in the source description's words, + Use when: '<trigger vocabulary>'>"
icon: "<one emoji>"
trigger: <2-4 word phrase, unquoted>
tools: [<verified_name>, <verified_name>]   # inline array; see knowledge-and-tools-remap.md
# Do not add an `id:` field - Quick assigns it.
---

# <Human Readable Name>

## Overview

<One paragraph: what this does, when to use it, what it is NOT for. Derived from the source agent's
"You are a…" opening, with the role-play cut and the scope kept.>

Converted from an existing chat agent configuration on <date>.

## Prerequisites

1. Amazon Quick desktop app (macOS or Windows) - skills do not run on Quick web.
2. <Connector> connected: Settings → Capabilities → Connections.
3. A local folder added under Settings → My computer → Local folders, containing:
   - `<file>` (`<format>`) - <what it is>

<Delete any that do not apply. Do not hardcode absolute paths - take the folder as an input or
state the convention here.>

## Workflow Steps

<OPTIONAL - delete this whole section if the source instructions contained no ordered procedure.
Do NOT invent steps to fill the scaffold. A skill with only Overview and Best Practices is a correct
output when that is all the source contained.>

### Step 1: <verb phrase>

<Atomic and self-contained. Assume the reader was not in the room. Full context inline, or a path
to follow. Mark the step deterministic (exact fields, exact order) or agentic (goal + success
criterion) as appropriate.>

**Success criterion:** <how the agent knows this step worked>

### Step 2: <verb phrase>

...

## Example invocations

<From the source agent's starter prompts, verbatim where possible.>

- "<starter prompt 1>"
- "<starter prompt 2>"

## Best Practices

- <Tone and voice rules from the source instructions - these port unchanged.>
- <"Always / Never" constraints, placed with the step they constrain where that reads better.>

## Failure handling

| If | Then |
| --- | --- |
| <a required connector is missing> | Stop and tell the user which connector and where to add it. Do not proceed with partial grounding. |
| <a knowledge source returns nothing> | Say so explicitly rather than answering from general knowledge. |
| <an outward-facing send is required> | Draft and wait for explicit approval. Never send without it. |

## Reference files

- `references/<file>.md` - <what it holds and which step reads it>
