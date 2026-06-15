# Session Analysis

<Metadata>
Name: Session Analysis
Category: ai-agent
Aliases: Agent Performance Review, AI Session Retro, Agent Learning Cycle, Agent Self-Improvement Retrospective
Duration: 45–60 minutes
Team Size: 1–4 (AI engineers, product team)
Best For: Structured review of AI agent performance across sessions to identify failure patterns, capability gaps, and specific improvements
Definition: A structured review of an AI agent's performance across sessions, examining where it succeeded, failed, or could improve.
</Metadata>

<Gotchas>
1. Use when: Weekly or bi-weekly review of agent performance during active development; After launching new capabilities or tools to assess real-world effectiveness; When user satisfaction drops or error rates exceed acceptable thresholds; When qualitative user feedback suggests systematic issues; After significant model updates or architectural changes
2. Do NOT use when: Insufficient session data (fewer than 50 sessions; patterns won't be statistically meaningful); When fundamental architecture redesign is needed (not incremental improvement); During initial prototyping where rapid iteration is more valuable than systematic review; When the issue is clearly model capability limitation rather than system design
3. Optimizing metrics that don't reflect user value: Improving completion rate while users are unhappy with output quality. Fix: Always include user satisfaction alongside task completion. A fast wrong answer optimizes the wrong metric.
4. Changing too many variables simultaneously: Implementing 5 changes at once, making it impossible to know what helped. Fix: Change one thing at a time where possible. Use A/B evaluation to isolate impact.
5. Anecdote-driven improvement: Fixing the most dramatic single failure rather than the most common failure pattern. Fix: Always quantify; frequency × severity. The boring repeated failure often matters more than the dramatic one-off.
6. No baseline measurement: Making changes without measuring before and after. Fix: Establish clear metrics before implementing any improvement. Run the same evaluation set before and after to verify improvement.
7. Ignoring success patterns: Focusing exclusively on failures without understanding what makes successful sessions work. Fix: Analyze top-performing sessions too; what conditions enable excellence? Can those conditions be replicated?
</Gotchas>

<Instructions>
<Workflow - Session Analysis
  description="Step-by-step facilitation guide for Session Analysis."
>
1. [Setup] (1–2 days prior)
   - Collect session data: logs, user feedback, success/failure signals, error rates, conversation transcripts
   - Categorize sessions by outcome: successful, partially successful, failed
   - Calculate baseline metrics: success rate, average turns to completion, user satisfaction signals
   - Identify outlier sessions (spectacular successes and notable failures) for deep-dive
   - Prepare comparison data: current period vs. previous period (trend)

2. [Open] (5 minutes)
   - State purpose: "We're reviewing how the agent performed over the past [period] to identify systematic improvements - not fixing individual conversations, but improving the system"
   - Present high-level metrics: total sessions, success rate, key failure categories
   - Frame: "We're looking for PATTERNS, not anecdotes. What keeps happening?"

3. [Stage: Success Rate & Trends] (10 minutes)
   - Purpose: Establish factual baseline of agent performance and trajectory
   - Prompt: "What's our overall success rate? How does it compare to last period? Which capabilities/intents have highest and lowest success rates?"
   - Facilitation tip: Break down by intent/capability if possible. An 80% overall success rate might hide a 95% rate on simple tasks and 40% on complex ones. Identify which specific capabilities are underperforming. Trends matter more than absolutes; is performance improving or degrading?

4. [Stage: Failure Taxonomy] (15 minutes)
   - Purpose: Categorize failures into actionable types that suggest different remediation approaches
   - Prompt: "What types of failures are we seeing? Categorize: wrong tool selection, hallucination, incomplete understanding, missing capability, wrong reasoning, context loss, instruction non-compliance, tool execution error."
   - Facilitation tip: Create a failure taxonomy specific to your agent. Each category suggests a different fix: wrong tool → improve tool descriptions or routing logic. Hallucination → add grounding or retrieval. Missing capability → build new tool/skill. Context loss → adjust context management. Group failures and count frequencies; fix the most common category first.

5. [Stage: User Feedback Patterns] (10 minutes)
   - Purpose: Understand user experience beyond technical success/failure metrics
   - Prompt: "What do users correct most frequently? Where do they express frustration? What do they praise? Where do they give up?"
   - Facilitation tip: Technical success (task completed) and user satisfaction (happy with experience) are different. An agent might complete a task but take 15 turns to do it (frustrating). Or produce a correct result in the wrong format. User corrections and reformulations are gold; they show exactly where the agent's model of user needs diverges from reality.

6. [Stage: Capability Gap Identification] (10 minutes)
   - Purpose: Identify what requests the agent cannot handle and whether it should
   - Prompt: "What requests came in that the agent couldn't fulfill? Of those, which SHOULD it be able to handle? What's the gap - missing tool, missing knowledge, missing reasoning?"
   - Facilitation tip: Not every gap needs filling - some requests are out of scope. But gaps in core capabilities are high-priority fixes. Categorize unfulfilled requests: (a) in-scope but can't do (build), (b) adjacent to scope (evaluate), (c) out of scope (graceful decline needed).

7. [Stage: Efficiency Analysis] (5 minutes)
   - Purpose: Identify where the agent takes too many steps or wastes tokens
   - Prompt: "Where does the agent take too many steps? Where is it verbose or redundant? Where could it be more direct?"
   - Facilitation tip: Efficiency affects both cost and user experience. Look for: unnecessary confirmation loops, over-explanation, tool calls that could be combined, repeated context gathering that should be cached. Each inefficiency is a specific optimization target.

8. [Stage: Improvement Prioritization] (10 minutes)
   - Purpose: Convert findings into a prioritized improvement backlog
   - Prompt: "Given our failure categories, user feedback, and capability gaps - what are the top 3 improvements that would have the highest impact on the most sessions?"
   - Facilitation tip: Prioritize by: frequency × severity. A common minor issue might be higher priority than a rare catastrophic one (or vice versa). Each improvement should be specific enough to implement and measurable enough to verify: "Improve financial question routing accuracy from 60% to 85%."

9. [Synthesize] (5 minutes)
   - Document top 3 prioritized improvements with success criteria
   - Assign owners and timelines
   - Define how we'll measure improvement (A/B test, before/after metrics)
   - Schedule next session analysis

10. [Close] (5 minutes)
    - Confirm improvement backlog and next steps
    - Note any data collection improvements needed for next review
    - Set next session analysis date
</Workflow - Session Analysis>
</Instructions>

<Templates>
```markdown
# Agent Session Analysis: [Agent Name] - [Period]

**Date:** [Date]
**Period Reviewed:** [Start] – [End]
**Sessions Analyzed:** [Count]
**Participants:** [Names and roles]

## Performance Summary
| Metric | This Period | Last Period | Trend |
|--------|------------|------------|-------|
| Total Sessions | X | Y | ↑↓→ |
| Success Rate | X% | Y% | ↑↓→ |
| Partial Success | X% | Y% | ↑↓→ |
| Failure Rate | X% | Y% | ↑↓→ |
| Avg Turns to Completion | X | Y | ↑↓→ |
| User Satisfaction Signal | X | Y | ↑↓→ |

## Performance by Capability
| Capability/Intent | Volume | Success Rate | Trend | Notes |
|-------------------|--------|--------------|-------|-------|
| [Capability 1] | X | Y% | ↑↓→ | [Commentary] |
| [Capability 2] | X | Y% | ↑↓→ | [Commentary] |

## Failure Taxonomy
| Failure Type | Count | % of Failures | Example | Fix Category |
|--------------|-------|---------------|---------|--------------|
| Wrong tool selection | X | Y% | [Brief example] | Routing logic |
| Hallucination | X | Y% | [Brief example] | Grounding |
| Missing capability | X | Y% | [Brief example] | Build new |
| Context loss | X | Y% | [Brief example] | Architecture |
| Instruction non-compliance | X | Y% | [Brief example] | Prompt engineering |

## User Feedback Patterns
- **Most common correction:** [What users fix most]
- **Frustration signals:** [Where users express frustration]
- **Praise signals:** [What users appreciate]
- **Abandonment points:** [Where users give up]

## Capability Gaps
| Gap | In Scope? | Priority | Approach |
|-----|-----------|----------|----------|
| [Request type can't handle] | Yes/No/Maybe | High/Med/Low | Build/Evaluate/Decline |

## Improvement Backlog (Prioritized)
| # | Improvement | Impact (sessions affected) | Effort | Success Metric |
|---|-------------|---------------------------|--------|----------------|
| 1 | [Specific improvement] | ~X% of sessions | [S/M/L] | [Measurable target] |
| 2 | [Specific improvement] | ~X% of sessions | [S/M/L] | [Measurable target] |
| 3 | [Specific improvement] | ~X% of sessions | [S/M/L] | [Measurable target] |

## Actions
| Action | Owner | Timeline | Measurement |
|--------|-------|----------|-------------|
| [Action] | [Who] | [When] | [How we verify improvement] |

## Next Analysis: [Date]
```
</Templates>

<Resources>
- Focus on failure PATTERNS, not individual failures. A single weird conversation is noise; the same failure type appearing 30% of the time is signal worth acting on.
- Distinguish between capability gaps (the agent CAN'T do it) and execution errors (the agent SHOULD be able to but doesn't). These require fundamentally different interventions.
- User corrections are the highest-signal feedback. Every time a user reformulates, corrects, or gives up, that's a specific, real-world failure case. Mine these aggressively.
- Include user satisfaction signals alongside task completion metrics. Technically completing a task in 20 turns when the user expected 2 is a user experience failure even if the final output was correct.
- Consider maintaining a "failure case library"; curated examples of each failure type that can be used for prompt engineering, eval development, and regression testing.
- A/B evaluation (before/after a change) is the gold standard for verifying improvements. Without it, you're guessing whether changes helped.
</Resources>
