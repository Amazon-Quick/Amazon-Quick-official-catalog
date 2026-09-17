---
description: "The full failure-handling table for the conversion workflow, grouped by the workflow phase where each failure surfaces, with the recovery action for every case."
last_updated: 2026-09-08
origin: original
---

# Failure handling

The full failure-handling table for the conversion workflow. Read this whenever a step cannot
complete as written. Grouped by the workflow phase where the failure surfaces.

## Source intake (Step 2)

| If | Then |
| --- | --- |
| The user has no config file and cannot access the source platform's UI | You cannot recover the instructions. Say so. Offer to build a new skill from a description of what the agent did, but label it a rebuild, not a conversion. |
| The source is a markdown definition with no `tools:` at all | It inherited every tool from its host. Build the `tools:` list from scratch by reading what the body actually does, then verify each name. |
| The source agent depended on a general shell | Quick has no shell. Rewrite each shell step as Python (`run_python`) or as prose instructions. Do not convert `bash` to `run_python` and assume the body still works. |
| The agent came bundled in a plugin with other agents, skills and connectors | Quick has no plugin equivalent. Say so before starting. Convert each piece separately and tell the user how many objects they will end up installing. |

## Destination and shape (Step 1)

| If | Then |
| --- | --- |
| The source instructions have no ordered steps | That decides the shape (omit `## Workflow Steps`) and nothing else. Do NOT treat it as a signal for `AGENTS.md`. Work Decision A separately; a step-free persona is often a strong candidate for a shared agent. |
| The user says a teammate will use it | Do NOT auto-route to an agent. Skills can be shared on desktop (publish/share, or export `.zip`/`.qplugin`). Decide on surfaces and grounding (Q2/Q4): an agent wins when they need it beyond desktop or want one central object that updates for everyone; a shared skill is fine for a desktop-only hand-off. `AGENTS.md` cannot be shared at all. |
| The conversion is finished and the user then asks "is this a skill or an agent?" | You failed to confirm the destination up front. State what was built and why, and offer to move it. Prevent the repeat by putting the named shape options in front of the user and getting a pick before writing anything. |
| You recommended a destination and started building on the strength of your own reasoning | Not sufficient. Stop, present the two shapes plus "explain the tradeoffs", and get a pick. Desktop-versus-web is the user's call, not an inference from the source material. |
| The user asks where the MCP server for their data would run | On AWS it can be hosted on Bedrock AgentCore, and it is registered under Settings, Capabilities, Connections. Name it in the shape option rather than surfacing it as a surprise after the skill is built. |

## Knowledge and tool remap (Step 3)

| If | Then |
| --- | --- |
| A knowledge source has a link, but the link is behind a sign-in wall | The source is permission-controlled. Route to the matching connection under Settings, Capabilities, Connections, or a knowledge base in a space, and reference it by link. Do not ask for a manual download, and do not report the sign-in page as the document's content. A local copy is the fallback only if no connector exists for that system. |
| A direct fetch or download of a source fails on authentication | Same answer: add the connection. Do not retry, and do not hand the download back to the user as a manual task. The failure told you which landing spot was correct. |
| The user offers to upload the file into the conversation instead | Accept it only after establishing no connector can reach it. Then say plainly that it is a dated snapshot, record the date, and name the staleness in the Step 8 report. An uploaded copy also strips the permission model the library was providing. |
| A knowledge source exists but has neither a link nor a local copy | Record it as dropped now, with the specific consequence, rather than leaving the row pending. |
| A knowledge source has no Quick equivalent the user will set up | Record it as dropped. Continue with the rest. Name it in the Step 8 report with the specific consequence. |
| A source contains Red Data / HIPAA / PII | Hard stop for that source. Do not connect it. Record as dropped with that reason and do not offer a workaround. |
| A tool name cannot be verified against this build | Drop that one name from `tools:` and describe the need in prose in the body. Do not guess a name. |
| A source tool has no Quick equivalent at all | Find where the body uses it, rewrite that step, and report the capability as dropped. Never substitute a different tool and hope. |

## Writing and packaging (Steps 5 and 6)

| If | Then |
| --- | --- |
| The installed skill's name shows as `---`, or blank, in Quick | The frontmatter was not parsed. Open the file: either line 1 is not `---`, the block is not closed, or every key collapsed onto one line. Fix the block, re-read it back, and re-upload. Editing the name in the UI hides the cause and leaves `tools:` still unparsed. |
| Quick reports `0 tools` but `tools:` is clearly listed | Same root cause as a blank name: the `tools:` line is being read as body text, not frontmatter. Check the delimiters and the one-key-per-line rule before touching the tool names; they are almost certainly fine. |
| The whole frontmatter appears in the Instructions panel as prose | Either the block was written without real newlines, or the entire file was pasted into Quick's Custom skill form instead of only the body. In the form, each frontmatter value has its own field; only the text below the closing `---` goes in Instructions. |
| A key was written as `## name:` or `# trigger:` | `#` starts a YAML comment, so the key is silently dropped and Quick sees it as missing. Remove the `#`. Nothing inside the frontmatter block is a heading. |
| No connected local folder contains any `SKILL.md` | The user has no skills folder yet. Create `skills/` inside a connected folder, say you created it, and give the full path. Still do not ask them to choose one. |
| Several connected folders contain skills | The one case where you ask about location. List each candidate path with the number of skills it holds and let the user pick. |
| The new skill folder was written but does not appear in Quick's skill list | Expected: writing the folder is not installing it. The zip must be uploaded in Step 7 and Quick restarted. Quick's own skills directory is not a connected folder and cannot be written to directly. |
| Code execution is unavailable | Do Steps 2 and 6 by hand using the checklists given there. Do not treat the scripts as required. |

## Install and verify (Step 7)

| If | Then |
| --- | --- |
| The upload is not recognised after a restart | Restart Quick desktop a second time; processing can take five minutes. If it still fails, check that `name` matches the folder name and that the zip's top-level entry is the folder. |
| `Tell me about <skill name>` returns nothing after two restarts | Stop and troubleshoot the install. Do not proceed to behavioural testing; you would be testing a skill that is not loaded. |
| The converted skill's output differs materially from the baseline | Diff the instructions, then check Step 3's remap. A silent-empty result almost always means an unresolved knowledge source, not a bad prompt. |
