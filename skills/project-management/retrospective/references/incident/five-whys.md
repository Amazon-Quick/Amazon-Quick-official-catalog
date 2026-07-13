# Five Whys

<Metadata>
Name: Five Whys
Category: incident
Aliases: 5 Whys, Root Cause Analysis (RCA), Toyota Method, Why-Why Analysis
Duration: 15–30 minutes per problem thread
Team Size: 3–6; max 8
Best For: Drilling past symptoms to find actionable root causes of incidents and recurring problems
Definition: An iterative interrogation technique originally developed by Sakichi Toyoda for the Toyota Production System where "Why?" is asked repeatedly (approximately five times) to drill down from observable symptoms to systemic root causes, creating a causal chain from effect to origin.
</Metadata>

<Gotchas>
1. Use when: after incidents where the root cause isn't immediately obvious; when recurring problems keep resurfacing despite previous fixes; as the root-cause analysis component within a broader blameless postmortem; when you need to move a team beyond "what happened" to "why did the system allow this"; for simple-to-moderate causal chains with a single primary thread; when time is limited and full timeline reconstruction isn't warranted
2. Do NOT use when: complex multi-causal incidents where multiple independent factors converged (use Timeline or Fishbone); when the "whys" become speculative because there isn't enough data; political situations where each "why" risks becoming accusatory toward a person; when immediate response is still needed (stabilize first); when the root cause is already known and you just need to plan remediation
3. Stopping at "human error". This is the cardinal sin of Five Whys; a person making a mistake is never the root cause. Fix: always ask "Why did the system allow this?" The system that allowed the mistake to have impact is the real target
4. Exactly five, no more, no less. The name is a guideline, not a rule. Fix: stop at 3 if actionable, go to 7 if you haven't reached systemic factors; forcing exactly 5 creates artificial answers
5. Speculative answers. Every answer should be verifiable with data. Fix: if you're guessing, stop and say "We don't have data for this link; we need to investigate"
6. Single-threading a multi-causal incident. Five Whys works best for single causal chains. Fix: if multiple independent factors contributed, run separate chains or use a different format entirely
7. Leading questions. "Why didn't you check the logs?" is blame; "Why was the relevant information not visible?" is systems thinking. Fix: word questions to target the system, never the individual
8. Countermeasures that address symptoms. If your fix targets Why #2 but not Why #5, the same root cause will produce a different symptom next time. Fix: ensure countermeasures target the deepest actionable root cause
</Gotchas>

<Instructions>
<Workflow - Five Whys
  description="Facilitation guide for Five Whys."
>
1. [Setup] (5 minutes before)
   - Gather relevant data: incident logs, alerts, deployment records, monitoring data
   - Identify the right participants: people who were involved in or observed the incident
   - Prepare a whiteboard or shared document with the problem statement space and numbered "Why?" rows
   - Decide if you're analyzing one problem thread or multiple (adjust time accordingly)

2. [Open] (3 minutes)
   - Purpose: Frame as blameless systems inquiry
   - Prompt: "We're going to trace this problem to its systemic root cause. Every 'Why?' targets the system and its conditions, not individuals. We stop when we reach something we can engineer against."
   - Facilitation tip: If this is being done within a broader postmortem, acknowledge that explicitly. If standalone, establish the blameless norm clearly.

3. [Stage: Problem Statement] (5 minutes)
   - Purpose: Agree on a precise, factual problem statement
   - Prompt: "What is the specific problem we're analyzing? State it as an observable fact with impact."
   - Facilitation tip: Spend time here. A vague problem ("the system was slow") leads to vague root causes. A precise problem ("Service X returned 500 errors for 23 minutes affecting 12,000 requests") leads to precise root causes. Get group consensus before proceeding.

4. [Stage: First Why] (3–5 minutes)
   - Purpose: Identify the immediate/proximate cause
   - Prompt: "Why did [problem statement] happen? What was the direct, immediate cause?"
   - Facilitation tip: Stick to facts. If the answer is speculative, pause and ask "How do we know this?" Check logs or data. Multiple answers may emerge; track branches separately.

5. [Stage: Second Why] (3–5 minutes)
   - Purpose: Move one layer deeper from the proximate cause
   - Prompt: "Why did [Answer 1] happen? What caused that condition to exist?"
   - Facilitation tip: Watch for the team wanting to jump ahead. Each step must be verified before moving forward. If the team splits into two causal branches, track both on the board.

6. [Stage: Third Why] (3–5 minutes)
   - Purpose: Push past the "comfortable" explanations into systemic territory
   - Prompt: "Why did [Answer 2] happen? What process, system, or condition allowed that?"
   - Facilitation tip: This is often where "human error" appears. Redirect: "OK, a person made an error. Why did the system allow that error to have this impact? What guardrails were missing?"

7. [Stage: Fourth Why] (3–5 minutes)
   - Purpose: Approach organizational/systemic factors
   - Prompt: "Why did [Answer 3] exist? Why wasn't there a safeguard, process, or control?"
   - Facilitation tip: You're now usually at the level of missing processes, design decisions, resource constraints, or organizational priorities. This is fertile ground for actionable fixes.

8. [Stage: Fifth Why (or more)] (3–5 minutes)
   - Purpose: Reach an actionable root cause
   - Prompt: "Why did [Answer 4] happen? Is this the root cause we can act on, or do we need to go deeper?"
   - Facilitation tip: The magic number is NOT always 5. Stop when you reach a cause that is (a) systemic, (b) actionable, and (c) within your team's influence. Going too deep leads to "because the universe exists" territory. Going too shallow leaves you treating symptoms.

9. [Synthesize] (5 minutes)
   - Purpose: Confirm root cause and identify the class of failure
   - Prompt: "Reading our chain back from bottom to top: does this root cause explain the problem? Is this a single instance or does it represent a class of failures? Where else might this same root cause manifest?"
   - Facilitation tip: Read the chain aloud. If any link feels speculative, mark it. If the root cause applies to other systems/services, note the broader implication.

10. [Close] (5 minutes)
    - Purpose: Define specific countermeasures targeting the root cause
    - Prompt: "What specific countermeasure will address this root cause? Who owns it, and by when?"
    - Facilitation tip: A good countermeasure addresses the root cause, not an intermediate symptom. If your fix addresses Why #2 but not Why #5, you'll see the problem recur in a different form.
</Workflow - Five Whys>
</Instructions>

<Templates>
```markdown
# Five Whys Analysis: [Problem Title]

**Date:** YYYY-MM-DD
**Facilitator:** [Name]
**Participants:** [Names]
**Related Incident:** [Link to postmortem if applicable]

## Problem Statement
[Precise, factual, observable problem with impact quantified]

## Causal Chain

| Level | Question | Answer | Evidence |
|-------|----------|--------|----------|
| Why 1 | Why did [problem] happen? | [Proximate cause] | [Log/data reference] |
| Why 2 | Why did [answer 1] happen? | [Deeper cause] | [Evidence] |
| Why 3 | Why did [answer 2] happen? | [Systemic factor] | [Evidence] |
| Why 4 | Why did [answer 3] exist? | [Process/design gap] | [Evidence] |
| Why 5 | Why did [answer 4] happen? | [Root cause] | [Evidence] |

## Root Cause
[Clear statement of the systemic root cause]

## Class of Failure
[What broader category does this represent? Where else might it manifest?]

## Countermeasures
| Action | Addresses | Owner | Deadline | Ticket |
|--------|-----------|-------|----------|--------|
| [Specific fix] | Root cause | [Name] | [Date] | [Link] |
| [Preventive measure] | Class of failure | [Name] | [Date] | [Link] |

## Branch Analysis (if applicable)
[Document any alternative causal branches explored]
```
</Templates>

<Resources>
- **Draw the chain visually.** Arrows from problem → why1 → why2 → ... → root cause. Visual chains make logical gaps obvious.
- **Branch when needed.** If a "Why?" has two legitimate answers, draw two branches and follow both. Converging branches often reveal the true systemic issue.
- **Use the "Five Whys for success" variant.** Apply the same technique to understand why something went right. "Why did the failover work?" is just as valuable for learning.
- **Pair with Timeline.** Five Whys is most powerful when applied to specific decision points identified during a timeline reconstruction. The timeline gives context; Five Whys gives depth.
- **Watch for "infinite regress".** If you've passed 7 Whys and answers are getting more abstract ("Why don't we have infinite budget?"), you've gone too far. Back up to the last actionable layer.
- **Timebox each Why to 3–5 minutes.** If the team debates an answer for 10 minutes, the answer probably needs data you don't have. Mark it as "needs investigation" and move on.
- **For remote teams**, use a shared document where everyone can see the chain building in real-time. The visual progression creates momentum and clarity.
</Resources>
