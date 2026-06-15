# Incident Debrief / Learning Review

<Metadata>
Name: Incident Debrief / Learning Review
Category: incident
Aliases: Learning Review, Post-Incident Learning, PIR, Sense-Making Review, Adaptive Capacity Debrief
Duration: 60–90 minutes
Team Size: 4–10; max 15
Best For: Complex incidents where "root cause" is an inadequate framing, when you need to understand how the system behaved, not just what broke
Definition: A facilitated group discussion after an incident focused on extracting organizational learning rather than assigning corrective actions, drawing on safety science and resilience engineering to understand how actions made sense to people in the moment rather than what went wrong.
</Metadata>

<Gotchas>
1. Use when: complex incidents where "root cause" is inadequate (multiple independent factors converged); when blameless postmortems still feel blame-y; organizations wanting to build a genuine learning culture; incidents involving multiple contributing factors and tradeoffs that were reasonable at the time; when the team needs to understand WHY actions made sense; after incidents in complex adaptive systems; when you want to surface tacit knowledge
2. Do NOT use when: simple incidents with clear obvious fixes (overhead isn't warranted); when specific corrective actions are urgently needed (fix first, learn later); teams without facilitators trained in learning-focused inquiry; when the organization's primary need is documentation for compliance (use CAPA or Blameless Postmortem); when participants aren't psychologically safe enough to say "I was confused"
3. Producing action items during the Learning Review. This fundamentally breaks the format; people withhold observations if they fear triggering work. Fix: keep learning and remediation in SEPARATE meetings; the moment you start fixing, people stop exploring
4. "Why did you do that?" questions. This frames the question as though the person should have done differently. Fix: replace with "How did it make sense to you at the time?" or "What were you trying to accomplish?" Same information, radically different psychological effect
5. Rushing to solutions. The facilitator's #1 job is to resist the gravitational pull toward fixing. Fix: acknowledge proposed fixes ("Great thought; let's capture that for the remediation discussion") and redirect to learning
6. Treating the Learning Review as a postmortem with different branding. If you still end with action items, you've done a postmortem with extra steps. Fix: the framing, questions, and outputs must genuinely differ; no action items in the room
7. Insufficient facilitator training. Untrained facilitators default to postmortem patterns. Fix: invest in facilitation development in learning-focused inquiry before adopting this format
8. Participants don't feel safe saying "I was confused". If people can't admit uncertainty, the format fails. Fix: psychological safety is a prerequisite, not a nice-to-have; build safety before attempting this format
</Gotchas>

<Instructions>
<Workflow - Incident Debrief / Learning Review
  description="Facilitation guide for Incident Debrief / Learning Review."
>
1. [Setup] (Before the meeting, 1–7 days after incident resolution)
   - Select a facilitator trained in learning-focused inquiry (not the incident commander, not a manager of the participants)
   - Gather context materials: timeline, monitoring data, communications logs
   - Explicitly communicate to all participants: "This is a learning session. There will be no action items produced during this meeting. Our goal is understanding, not fixing. Fixing happens separately."
   - Invite all participants who were involved, especially those whose perspectives differ or who held different mental models during the incident
   - Consider inviting observers who can learn from the discussion (builds organizational knowledge)

2. [Open] (7–10 minutes)
   - Purpose: Establish the learning frame, explicitly separate from remediation and judgment
   - Prompt: "This is a Learning Review. We are here to understand, not to fix, not to blame, not to assign action items. Those things happen elsewhere. Here, we want to understand: How did the incident unfold? How did it make sense to people in the moment? What did people see, know, and believe at each point? What do we understand now that we didn't before? Every action someone took made sense given their context. Our job is to understand that context."
   - Facilitation tip: This framing is NOT the same as a blameless postmortem opening. The key difference: postmortems say "we won't blame" but still seek what went wrong. Learning Reviews don't ask what went wrong at all; they ask how the world looked to participants in real time. This is a fundamental reframe that takes practice to facilitate.

3. [Stage: Set Context] (5 minutes)
   - Purpose: Briefly establish what systems and services were involved without narrating the full incident
   - Prompt: "Let's briefly name: what systems, services, and teams were involved? What was the operational context (load, recent changes, time of day, staffing)?"
   - Facilitation tip: Keep this brief and factual. You're setting the stage, not telling the story yet. The story will emerge from individual perspectives.

4. [Stage: Reconstructive Inquiry] (20–25 minutes)
   - Purpose: Understand what people saw, knew, and did, from their perspective at the time
   - Prompt: "Walk us through what you experienced. What did you first notice? What did you think was happening? What information did you have? What information were you missing? What actions did you take, and what were you trying to accomplish with them?"
   - Facilitation tip: Ask each participant in turn. The critical technique: ask "How did it make sense to you at the time?" not "Why did you do that?" The former invites self-reflection; the latter triggers defensiveness. Use follow-up prompts: "What were you expecting to see?" "What would have changed your assessment?" "What were you weighing against each other?"

5. [Stage: Multiple Perspectives] (15–20 minutes)
   - Purpose: Surface how different roles experienced the same event simultaneously
   - Prompt: "We've heard individual stories. Now let's layer them: at [specific moment], Person A saw X and Person B saw Y. What was that like? Were you aware of each other's activities? How did your mental models of the situation differ?"
   - Facilitation tip: This is the highest-value stage. When participants realize they held contradictory models of reality simultaneously, that's an organizational insight. Don't judge the contradiction; explore it: "What would have had to be different for these two views to converge earlier?"

6. [Stage: Surprise Exploration] (10 minutes)
   - Purpose: Identify what didn't match expectations; surprises are learning signals
   - Prompt: "What surprised you during this incident? Where did reality diverge from your mental model of how the system works? What did you learn about the system that you didn't know before?"
   - Facilitation tip: Surprises indicate gap between mental model and reality. Each surprise is an organizational learning opportunity. Don't rush past them. "I was surprised the circuit breaker didn't trip" tells you something about shared understanding of system behavior.

7. [Stage: Counterfactual and Resilience Thinking] (10 minutes)
   - Purpose: Explore what prevented worse outcomes and what adaptive actions people took
   - Prompt: "What could have made this worse? What prevented worse outcomes, by design or by luck? What adaptive actions did people take that aren't in any runbook? What expertise or judgment did people apply that we should appreciate?"
   - Facilitation tip: This is Safety-II thinking: studying what goes RIGHT, not just what goes wrong. The actions people take to keep systems running despite imperfect conditions represent adaptive capacity. This is organizational strength to preserve, not take for granted.

8. [Synthesize] (10 minutes)
   - Purpose: Extract organizational learning: what do we now understand that we didn't before?
   - Prompt: "What do we understand now that we didn't understand before this incident? What has this taught us about how our system actually behaves (vs. how we thought it behaved)? What assumptions were revealed as incorrect?"
   - Facilitation tip: Frame learnings as "updated mental models" not "mistakes found." Example: "We learned that Service A's timeout doesn't prevent cascade failures the way we assumed" not "We found that Service A's timeout is misconfigured."

9. [Close] (5 minutes)
   - Purpose: Acknowledge participants, name the learnings, point to next steps
   - Prompt: "Thank you for your candor and reflection. Key learnings from today: [summarize 2-3]. These will be documented and shared. Separately, the team will determine if any remediation actions are warranted based on these learnings. This review stands as a learning artifact."
   - Facilitation tip: Explicitly do NOT assign action items here. The Learning Review's integrity depends on separation from remediation. If participants start proposing fixes, acknowledge them ("Great thought; let's capture that for the remediation discussion") and redirect to learning.
</Workflow - Incident Debrief / Learning Review>
</Instructions>

<Templates>
```markdown
# Learning Review: [Incident Title]

**Date:** YYYY-MM-DD
**Incident Date:** YYYY-MM-DD
**Facilitator:** [Name]
**Participants:** [Names and roles]

## Context
**Systems Involved:** [List]
**Operational Context:** [Load, staffing, recent changes, time of day]
**Duration:** [Incident duration]

## How It Unfolded (Perspectives)

### [Person/Role A]'s Experience
- **First signal noticed:** [What they observed]
- **Initial mental model:** [What they thought was happening]
- **Information available:** [What they knew]
- **Information missing:** [What they didn't know]
- **Actions taken and intent:** [What they did and why it made sense]

### [Person/Role B]'s Experience
[Same structure]

## Multiple Perspectives - Key Divergences
| Moment | Person A's View | Person B's View | Implication |
|--------|----------------|----------------|-------------|
| [Time] | [Their reality] | [Their reality] | [What this reveals] |

## Surprises
- [Surprise 1] - What it reveals about our mental model: [insight]
- [Surprise 2] - What it reveals about our mental model: [insight]

## Adaptive Actions (Things that went right)
- [Action someone took that isn't in a runbook but prevented worse outcomes]
- [Expertise/judgment applied under pressure]
- [Lucky factor we should design resilience around]

## What Could Have Made This Worse
- [Factor 1 - was prevented by design / by luck / by adaptive action]
- [Factor 2]

## Updated Understanding
**What we now know about how our system behaves:**
1. [Updated mental model - e.g., "Service A's circuit breaker does NOT prevent cascading failures under condition X"]
2. [Updated mental model]
3. [Updated mental model]

**Assumptions revealed as incorrect:**
1. [Previous assumption → actual behavior]
2. [Previous assumption → actual behavior]

## Learnings (not action items)
1. [Organizational learning 1]
2. [Organizational learning 2]
3. [Organizational learning 3]

## Areas for Further Investigation
- [Topic that needs deeper exploration]
- [System behavior that warrants monitoring/experimentation]

---
*Note: This is a learning document. Remediation actions will be determined separately based on these learnings.*
```
</Templates>

<Resources>
- **Study Safety-II and resilience engineering** (Hollnagel, Dekker, Woods) before facilitating this format. The theoretical grounding fundamentally changes your question framing and what you listen for.
- **Your most powerful question is "How did it make sense to you at the time?".** This single reframe unlocks candor that "What happened?" never will. Practice it until it's natural.
- **Value surprise above all else.** When a participant says "I was surprised that...", stop and explore it deeply. Surprises indicate the gap between mental model and reality. That gap IS the learning.
- **Explicitly narrate the separation from remediation.** At the start AND any time someone proposes a fix: "Great observation. We'll capture that for the remediation discussion. Right now our job is understanding, not solving."
- **Look for adaptive capacity**, the creative, unscripted things people did to manage the situation. These represent organizational resilience. Document them, celebrate them, and ask: "How do we preserve this capacity?"
- **Silence is valuable.** When you ask "What surprised you?" and no one immediately answers, wait. Don't rescue the silence. Deep reflection takes 5–10 seconds. The best insights come after pauses.
- **Consider having a separate scribe** so the facilitator can focus entirely on guiding the conversation. The quality of inquiry suffers when the facilitator is also taking notes.
- **This format pairs well with Timeline Retrospective** as a preceding step. Do the Timeline first (to build shared facts), then the Learning Review (to extract meaning from those facts).
</Resources>
