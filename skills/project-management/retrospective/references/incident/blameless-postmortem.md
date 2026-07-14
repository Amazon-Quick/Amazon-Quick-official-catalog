# Blameless Post-Mortem

<Metadata>
Name: Blameless Post-Mortem
Category: incident
Aliases: Blameless Postmortem, Incident Retrospective, Incident Review, Learning Review, Post-Incident Review (PIR)
Duration: 60–90 minutes (meeting); 2–4 hours total including document preparation
Team Size: 4–8 (all responders); max 15
Best For: Production incidents where systemic learning matters more than finding someone to blame
Definition: A structured document and facilitated process that examines what happened during a service incident, why it happened, what went well, and what actions to take to prevent recurrence without assigning personal blame, rooted in systems thinking and safety science and formalized by Google's SRE team.
</Metadata>

<Gotchas>
1. Use when: after any service incident above a defined severity threshold (Sev1/Sev2); after near-misses that could have become major incidents; when a pattern of recurring incidents needs breaking; after security incidents or data breaches; when multiple teams/systems were involved; when building an organizational learning culture around reliability
2. Do NOT use when: trivial issues (< 5 min TTR, no customer impact); blame culture is so entrenched that "blameless" would be performative theater; for process/team/interpersonal issues (use sprint retros); when the incident is still ongoing; for planned chaos engineering exercises (use Chaos Engineering Retro)
3. "Human error" as root cause. This is never the answer; the system that allowed the mistake to have impact is. Fix: always ask what system conditions made the error likely, easy, or invisible
4. Action items without owners or deadlines. "Improve monitoring" means nothing. Fix: require named owner, verifiable verb, specific outcome, tracker ticket, and deadline for every action
5. Blame disguised as process. "Why didn't the on-call check the dashboard?" is blame with a question mark. Fix: reframe to "What would make the relevant signal more visible to on-call?"
6. Postmortem never published. It teaches only the people in the room. Fix: publish to the organization; publishing is where organizational learning happens
7. Action items that never complete. This is the most common failure. Fix: track completion rates as an organizational metric; if actions aren't completing, the process is theater
8. Skipping near-misses. Incidents that almost happened often teach more because there's no pressure to find a "fix." Fix: include near-misses in your postmortem criteria
9. Timeline from memory only. Memory is unreliable and biased by outcome knowledge. Fix: use logs, alerts, and chat transcripts as primary sources
</Gotchas>

<Instructions>
<Workflow - Blameless Post-Mortem
  description="Facilitation guide for Blameless Post-Mortem."
>
1. [Setup] (Before the meeting - within 48 hours of incident resolution)
   - Designate a facilitator who was NOT the incident commander (separation of roles reduces defensiveness)
   - Gather artifacts: monitoring dashboards, alert logs, chat transcripts, deployment records, customer reports
   - Pre-build the timeline from automated sources (logs, alerts, deployments)
   - Send pre-read with timeline and invite all incident responders
   - Book 90 minutes; better to end early than rush

2. [Open] (5 minutes)
   - Purpose: Establish psychological safety and blameless framing
   - Prompt: "We are here to understand the system, not judge individuals. Every decision someone made was reasonable given what they knew at the time. Our goal is to make the system safer, not to find someone to punish."
   - Facilitation tip: Read the blameless norm aloud even if the team knows it. Repetition builds culture. If leadership is present, have them affirm it verbally.

3. [Stage: Impact Summary] (5 minutes)
   - Purpose: Align everyone on the severity and scope
   - Prompt: "Let's confirm the impact: duration, affected users/services, financial cost, and SLA implications."
   - Facilitation tip: Use data, not feelings. "50,000 users saw errors for 23 minutes" is better than "it was pretty bad."

4. [Stage: Timeline Walk-Through] (25–35 minutes)
   - Purpose: Build shared understanding of what actually happened in sequence
   - Prompt: "Let's walk through the timeline chronologically. At each point: what happened, what did you observe, and what did you know at that moment?"
   - Facilitation tip: Enforce present-tense narration ("At 14:03, I see the alert fire and I check the dashboard") to combat hindsight bias. Ask "What did you know at that moment?" not "Why didn't you catch it?"

5. [Stage: What Went Well] (10 minutes)
   - Purpose: Acknowledge effective response actions and systems that prevented worse outcomes
   - Prompt: "What worked during the response? What prevented this from being worse? What should we preserve or amplify?"
   - Facilitation tip: Start here before failures; it's not just positivity theater. Resilience factors are critical learnings.

6. [Stage: What Went Wrong] (10 minutes)
   - Purpose: Identify process and system failures (not human failures)
   - Prompt: "What processes, systems, or conditions failed us? Where did the system not support good decision-making?"
   - Facilitation tip: If someone says "I should have..." redirect to "What would have made the right action easier/obvious?"

7. [Stage: Where We Got Lucky] (5 minutes)
   - Purpose: Surface factors that prevented worse outcomes by chance rather than design
   - Prompt: "What could have made this much worse? What lucky coincidences limited the blast radius?"
   - Facilitation tip: This is the highest-value category. Lucky factors reveal unprotected risks.

8. [Synthesize] (10 minutes)
   - Purpose: Identify root causes and systemic patterns
   - Prompt: "Looking across our timeline, what systemic conditions allowed this incident? What class of failure does this represent?"
   - Facilitation tip: Use 5 Whys on 1–2 key failure points. Push past "human error" to the system conditions that made errors likely. A good root cause is something you can engineer against.

9. [Close] (10 minutes)
   - Purpose: Define corrective actions with clear ownership
   - Prompt: "What specific actions will we take? Each action item needs: a named owner, a verifiable verb, a specific outcome, a ticket in our tracker, and a deadline."
   - Facilitation tip: Limit to 3–5 high-quality action items. Distinguish between corrective (fix this specific issue) and preventive (prevent this class of issue). Schedule a follow-up to verify completion.
</Workflow - Blameless Post-Mortem>
</Instructions>

<Templates>
```markdown
# Post-Mortem: [Incident Title]

**Date:** YYYY-MM-DD
**Severity:** Sev[1-4]
**Duration:** HH:MM (detection to resolution)
**Facilitator:** [Name]
**Attendees:** [Names]

## Summary
[One-paragraph description of what happened and its impact]

## Impact
- **Duration:** [X minutes/hours]
- **Users affected:** [Number and segment]
- **Revenue impact:** [If applicable]
- **SLA impact:** [Breaches, credits owed]

## Timeline
| Time (UTC) | Event | Actor/System |
|------------|-------|--------------|
| HH:MM | [Event description] | [Who/what] |
| ... | ... | ... |

## Root Cause Analysis
[Systemic root cause - not "human error"]

### Contributing Factors
1. [Factor 1]
2. [Factor 2]
3. [Factor 3]

## What Went Well
- [Effective response action 1]
- [System that prevented worse outcome]

## What Went Wrong
- [Process/system failure 1]
- [Missing safeguard]

## Where We Got Lucky
- [Coincidence that limited blast radius]

## Action Items
| Action | Owner | Ticket | Deadline | Type |
|--------|-------|--------|----------|------|
| [Specific, verifiable action] | [Name] | [TICKET-123] | [Date] | Corrective |
| [Preventive systemic fix] | [Name] | [TICKET-456] | [Date] | Preventive |

## Lessons Learned
- [Broader organizational insight 1]
- [Pattern this incident reveals]
```
</Templates>

<Resources>
- **Separate facilitation from incident command.** The IC has emotional investment in their decisions. An external facilitator can probe without defensiveness.
- **Pre-build the timeline from automated sources** before the meeting. This saves 30–60 minutes of "archaeological digging" and lets the meeting focus on analysis, not reconstruction.
- **Use the "substitution test" (Dekker):** Would another competent person in the same situation, with the same information, have done the same thing? If yes, it's a system issue, not a person issue.
- **Watch for "counterfactual" language.** "If only they had..." is hindsight. Redirect to "Given what was known at that moment..."
- **The facilitator's hardest job is protecting the blameless space** when leadership is present. Brief leaders beforehand: their job is to listen and affirm the blameless norm, not to interrogate.
- **End with a round of appreciation.** Incident response is stressful. Acknowledge the humans who showed up at 3am.
- **Track your postmortem action item completion rate** as an organizational metric. Below 70% completion means the process needs fixing.
</Resources>
