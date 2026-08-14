# MODEL-NOTES: Operating Lessons for Council Reviewers

This file is the second-opinion skill's evolving memory of how to drive each
reviewer tier and model well. Read it before Stage 0 (council selection and
launch); update it, with the user's approval, at the end of each run (Stage 6).
Keep it tight: merge and prune rather than append endlessly.

---

## Global Operating Rules (All Reviewers)

### Task Spawning Rules

- Always spawn as independent tasks via start_task / create_task_group.
  Each reviewer gets its own isolated context, no conversation history leaks.
- No shared context between reviewers. Each task receives only the briefing
  and material. Never pass one reviewer's output to another during Stage 1.
- Parallel execution. Launch the full wave before waiting on any result.
- Timeout guidelines:
  - smart tier: 120s (deep reasoning takes time)
  - balanced tier: 90s
  - fast tier: 60s
  - MCP models: 120-180s (network latency + inference)

### Briefing Rules (Critical for Quality)

- Self-contained briefings. Every reviewer briefing must include ALL
  necessary information. Reference workspace file paths for large content.
- Strict output format. Always include the exact output format template in
  the briefing. Models that are not told the format produce unstructured prose.
- No-narration instruction. Always include: "Begin immediately with your
  findings. No preamble, no meta-commentary."
- Single-read for file-based material. When the briefing references a file
  path: "Read this file exactly once. Do NOT search, glob, or verify the path."

### Anti-Correlation Rules

- Shuffle reviewer order in the anonymous bundle (Stage 2) to prevent
  position bias (first review gets more attention).
- Never reveal reviewer identities to any task agent at any stage.
- For MCP models: prefer different families. Two models from the same family
  produce correlated opinions and reduce cross-review value.

---

## Built-in Tier Profiles

### Smart Tier (tier: smart)

Reasoning profile: Deep, thorough, catches subtle logic errors and nuanced
criteria violations. Takes longer but produces the most detailed analysis.

| Attribute | Value |
|-----------|-------|
| Typical response time | 30-90s |
| Typical finding count | 5-12 |
| Strength | Logic errors, architectural flaws, subtle inconsistencies |
| Weakness | May over-analyze trivial issues; occasionally verbose |
| Format compliance | High |
| Best role | Primary reviewer for complex material; default chair |

Operating notes:
- Produces the longest reviews. Set generous timeout (120s).
- May classify trivial formatting issues as "major": the cross-review stage
  corrects this through peer ranking.
- Excellent chair: synthesizes multiple viewpoints well.

---

### Balanced Tier (tier: balanced)

Reasoning profile: Practical all-rounder. Good coverage without over-analysis.

| Attribute | Value |
|-----------|-------|
| Typical response time | 15-45s |
| Typical finding count | 3-8 |
| Strength | Practical perspective, real-world applicability, good coverage |
| Weakness | May miss subtle issues that require deep reasoning |
| Format compliance | High |
| Best role | General reviewer; tie-breaking perspective |

Operating notes:
- Reliable and consistent. Rarely produces empty or malformed output.
- Its findings tend to be highly actionable (fewer nits, more genuine issues).
- Solid cross-reviewer: its rankings tend to align with final consensus.

---

### Fast Tier (tier: fast)

Reasoning profile: Quick pattern-matching, surface-level scan. Different
heuristics than deep reasoning: catches things others miss precisely
because it does not over-think.

| Attribute | Value |
|-----------|-------|
| Typical response time | 5-20s |
| Typical finding count | 2-6 |
| Strength | Obvious issues, formatting, consistency, quick patterns |
| Weakness | Misses subtle logic; may produce shallow rationales |
| Format compliance | Medium |
| Best role | Surface scanner; catching what deep reviewers overlook |

Operating notes:
- Fastest to complete. Set shorter timeout (60s).
- Format compliance tip: Include an explicit example finding in the briefing
  (not just the template). This significantly improves structured output quality.
- Useful as a "sanity check" reviewer: if fast catches something that smart
  missed, it is likely a genuine blind spot.

---

## MCP-Connected Model Notes

### Gemini (via MCP)

| Attribute | Value |
|-----------|-------|
| Strength | Very large context window; good at broad coverage |
| Weakness | May narrate before acting; occasionally produces extra tool calls |
| Format compliance | Medium-high (with explicit format instructions) |
| Best for | Long documents, broad coverage, large codebases |

Operating notes:
- Always include the no-narration instruction.
- Excellent for material that exceeds normal context limits.
- Cross-review rankings from Gemini tend to be reasonable and well-justified.

---

### DeepSeek (via MCP)

| Attribute | Value |
|-----------|-------|
| Strength | Strong, well-cited critical analysis; resilient to failures |
| Weakness | Occasional transient errors (502); can be overly critical |
| Format compliance | High |
| Best for | Code review, reasoning-heavy critique, structured evaluation |

Operating notes:
- Produces well-structured, well-cited output reliably.
- Occasional transient 502: just retry once.
- May be overly critical (inflates severity): cross-review corrects this.

---

### GPT (via MCP)

| Attribute | Value |
|-----------|-------|
| Strength | Structured output compliance; code review; refactoring insight |
| Weakness | Can be consensus-seeking (less contrarian than DeepSeek) |
| Format compliance | Very high |
| Best for | Code review, API design review, structured criteria evaluation |

Operating notes:
- Excellent format compliance: almost never produces malformed output.
- May agree with consensus too readily; less valuable as a contrarian reviewer.
- Strong as a chair model due to good synthesis capabilities.

---

## Reviewer-Reliability Table

Consulted in Stage 0 (council selection) and updated with approval in Stage 6.

| reviewer | runs | avg street-cred | confirm-rate | notes |
| --- | --- | --- | --- | --- |
| smart-tier | 0 | - | - | Deep reasoning; default chair; thorough but occasionally verbose |
| balanced-tier | 0 | - | - | Practical all-rounder; reliable format compliance; actionable findings |
| fast-tier | 0 | - | - | Quick patterns; fewer but different findings; include format example |
| gemini-mcp | 0 | - | - | Large context; needs no-narration instruction; good for long material |
| deepseek-mcp | 0 | - | - | Strong critique; resilient; occasional 502, retry |
| gpt-mcp | 0 | - | - | Excellent format compliance; consensus-seeking; strong chair candidate |

Seed rows only: values accumulate with each council run.

---

## Cost and Performance Guardrails

### Built-in Tiers

- No additional cost beyond normal Quick usage.
- Preferred for most runs unless the user explicitly requests multi-family diversity.

### MCP Models

- Cost depends on the user's MCP provider configuration and pricing.
- Always disclose when MCP models will be used.
- Never use expensive reasoning models (o3, o3-pro) unless explicitly requested.
- Warn about cost before proceeding even when asked for expensive models.

### Timeout and Retry Policy

- First failure: Retry once (transient failures are common).
- Second failure: Substitute with a different tier/model and disclose.
- Total run timeout: 10 minutes for built-in tiers, 15 minutes for MCP models.

---

## Lessons Changelog

- **2026-06-04** - Initial creation. Seeded from operating lessons. Established
  built-in tier profiles (smart/balanced/fast) as zero-config reviewers. Added
  MCP model placeholder sections for Gemini, DeepSeek, and GPT.
