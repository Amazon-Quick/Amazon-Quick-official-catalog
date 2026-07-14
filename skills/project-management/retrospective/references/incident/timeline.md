# Timeline Retrospective

<Metadata>
Name: Timeline Retrospective
Category: incident
Aliases: Timeline Reconstruction, Incident Timeline, Event Reconstruction, Chronological Debrief
Duration: 60–120 minutes (scales with incident complexity)
Team Size: 5–10 (all involved parties); max 20
Best For: Complex incidents involving multiple teams/systems where shared understanding of "what actually happened" must precede root-cause analysis
Definition: A chronological reconstruction of events during an incident where participants collaboratively build a shared timeline from individual perspectives, then analyze key decision points, information gaps, and system behaviors, adapted from accident investigation methodologies used in aviation and nuclear safety.
</Metadata>

<Gotchas>
1. Use when: complex incidents involving multiple teams, systems, or handoffs where no single person has the full picture; when there's disagreement or confusion about "what happened"; long-running incidents (hours to days) where sequence matters; multi-day outages requiring detailed reconstruction; when information asymmetry contributed to the incident; as input to a broader blameless postmortem or after-action review; when hindsight bias is likely to distort memory
2. Do NOT use when: simple clear-cut incidents with obvious single cause and short duration; when detailed timestamps aren't available or meaningful; quick pulse-check retrospectives where depth isn't needed; when the incident is still active (reconstruct after resolution); for team process issues unrelated to time-sequenced events
3. Relying solely on memory. Human memory is unreliable under stress and biased by knowing the outcome. Fix: always verify with artifacts (logs, chat transcripts, alert records, deployment pipelines)
4. Skipping the timeline and jumping to root cause. Without shared context, root-cause analysis becomes argument. Fix: build the shared timeline FIRST; "what actually happened in sequence" resolves conflicting theories
5. Hindsight bias. "They should have noticed the alert" is Monday-morning quarterbacking. Fix: ask "At that moment, with those 47 other alerts also firing, what made this one non-obvious?"
6. Single narrator. One person telling the story gives one perspective; the value is revealing what different people experienced simultaneously. Fix: actively pull in quiet participants; require multiple narrators
7. Too granular or too coarse. Minute-by-minute for a week-long incident is impossible; hour-by-hour for a 10-minute incident misses everything. Fix: match granularity to incident duration
8. Mixing "what" with "why" too early. "The deployment failed because the config was wrong" conflates timeline and analysis. Fix: capture "what" (the deployment failed) and "why" (config was wrong) separately
</Gotchas>

<Instructions>
<Workflow - Timeline Retrospective
  description="Facilitation guide for Timeline Retrospective."
>
1. [Setup] (30–60 minutes before the meeting)
   - Define the time window: exact start time (first anomaly or trigger) and end time (resolution confirmed)
   - Gather automated data: monitoring alerts, deployment logs, chat transcripts (Slack/Teams), PagerDuty records, CI/CD pipeline events, customer reports
   - Create a shared timeline canvas with a horizontal axis and time markers at appropriate intervals (minutes for short incidents, hours for long ones)
   - Create "swim lanes" for each team/system/person involved
   - Pre-populate the timeline with automated/objective events (alerts fired, deployments, escalations) before the meeting
   - Invite ALL responders and observers; each person holds a piece of the puzzle

2. [Open] (5 minutes)
   - Purpose: Establish blameless framing and explain the separation of "what" from "why"
   - Prompt: "Our goal today is to build a complete, shared picture of what happened: the sequence of events, decisions, and information flow. We are NOT analyzing root causes yet. We're reconstructing. Every action someone took made sense given what they knew at that moment. There are no wrong answers about what you observed."
   - Facilitation tip: Emphasize that different perspectives seeing different things is expected and valuable; that's why we're doing this together. Disagreements about what happened are gold mines, not conflicts.

3. [Stage: Individual Reconstruction] (10–15 minutes)
   - Purpose: Each person captures their own experience before group discussion influences memory
   - Prompt: "Write down what you saw, did, and knew, with timestamps as best you can recall. Include: alerts you received, actions you took, information you learned, communications you sent/received, and your emotional state or confusion level."
   - Facilitation tip: Silent individual work first is critical. Group discussion before individual recall causes memory conformity. Provide sticky notes or a digital equivalent. Encourage using chat logs and dashboards to verify timestamps.

4. [Stage: Collaborative Assembly] (20–35 minutes)
   - Purpose: Merge individual timelines into a single shared narrative
   - Prompt: "Let's walk through chronologically. Starting at [time], who saw the first signal? Walk us through what happened next from your perspective."
   - Facilitation tip: Go person by person through each time segment. Place events in swim lanes. When different people have different observations at the same time, capture both; this reveals information asymmetry. Use present tense: "At 14:03, I see the alert and I open the dashboard."

5. [Stage: Mark Key Moments] (10–15 minutes)
   - Purpose: Identify decision points, escalations, information arrivals, and turning points
   - Prompt: "Looking at our timeline, let's mark: (1) decision points where someone chose a path, (2) moments where new information arrived, (3) escalation points, (4) the moment things started improving, and (5) any moment where information existed but wasn't visible to someone who needed it."
   - Facilitation tip: Use colored markers or tags to distinguish decision points (blue), information arrivals (green), escalations (red), and information gaps (yellow). The gaps are often the most valuable finding.

6. [Stage: Analyze Gaps and Asymmetry] (15–20 minutes)
   - Purpose: Identify where information wasn't flowing or where different actors had different pictures of reality
   - Prompt: "Where did information exist that wasn't visible to someone who needed it? Where were people working with different mental models of the situation? Where did coordination break down?"
   - Facilitation tip: This is the highest-value stage. Information asymmetry during incidents is rarely "someone's fault"; it's a system design issue (alert routing, communication channels, dashboard access). Focus on systemic remedies.

7. [Synthesize] (10 minutes)
   - Purpose: Identify systemic patterns and select points for deeper analysis
   - Prompt: "Looking at the full timeline, what patterns do we see? What 2–3 key moments would benefit from deeper root-cause analysis (Five Whys)? What systemic themes recur?"
   - Facilitation tip: Common patterns: delayed detection, escalation hesitation, information hoarding, parallel troubleshooting without coordination, alert fatigue. Name the patterns explicitly.

8. [Close] (5 minutes)
   - Purpose: Confirm the shared timeline as a reference artifact and assign follow-up analysis
   - Prompt: "This timeline is now our shared source of truth. Who will clean it up and publish it? Which key moments will we take into deeper analysis, and who will facilitate that?"
   - Facilitation tip: The timeline itself is the primary artifact; ensure it gets documented and published. Assign 1–3 key moments for Five Whys analysis in a follow-up session or within the broader postmortem.
</Workflow - Timeline Retrospective>
</Instructions>

<Templates>
```markdown
# Incident Timeline: [Incident Title]

**Date:** YYYY-MM-DD
**Time Window:** HH:MM – HH:MM (UTC)
**Duration:** [Total incident duration]
**Facilitator:** [Name]
**Participants:** [Names and roles]

## Summary
[One paragraph: what happened from first signal to resolution]

## Timeline

| Time (UTC) | Event | Actor/System | Category |
|------------|-------|--------------|----------|
| HH:MM | [First anomaly/trigger] | [System] | Detection |
| HH:MM | [Alert fired] | [Monitoring] | Alert |
| HH:MM | [On-call acknowledged] | [Person] | Response |
| HH:MM | [Action taken] | [Person] | Decision |
| HH:MM | [Escalation] | [Person] | Escalation |
| HH:MM | [Information discovered] | [Person] | Information |
| HH:MM | [Fix applied] | [Person] | Remediation |
| HH:MM | [Resolution confirmed] | [System] | Resolution |

## Swim Lanes
### Team/System A
[Events specific to this actor]

### Team/System B
[Events specific to this actor]

## Key Moments (for deeper analysis)
### Moment 1: [Description] @ HH:MM
- **What happened:** [Facts]
- **Who knew what:** [Information state of each actor]
- **Decision made:** [What was chosen and why it seemed reasonable]
- **Information gap:** [What was unknown or invisible]

### Moment 2: [Description] @ HH:MM
[Same structure]

## Information Asymmetry Map
| Time | Person/Team A knew | Person/Team B knew | Gap Impact |
|------|-------------------|-------------------|------------|
| HH:MM | [Their view] | [Their view] | [Consequence] |

## Systemic Patterns Identified
1. [Pattern - e.g., "Detection delay due to alert threshold too high"]
2. [Pattern - e.g., "Parallel troubleshooting without shared channel"]
3. [Pattern - e.g., "Escalation delayed by unclear severity criteria"]

## Follow-Up Analysis Needed
- [ ] Five Whys on [Key Moment X] - Owner: [Name]
- [ ] Five Whys on [Key Moment Y] - Owner: [Name]
- [ ] Review of [process/system] - Owner: [Name]
```
</Templates>

<Resources>
- **Pre-populate automated events before the meeting.** Use monitoring tools, deployment logs, and PagerDuty to build a skeleton timeline. This saves 20–40 minutes and grounds the discussion in verifiable data.
- **Use present tense narration** to combat hindsight bias. "At 14:03, I see the alert fire. I check the dashboard and CPU looks normal, so I think it's a false positive." This reconstructs the mental model at the time, not the knowledge they have now.
- **Create physical (or digital) swim lanes** for each team or system. When events stack vertically across lanes at the same timestamp, you can see parallel activities, coordination moments, and gaps.
- **Mark "what I didn't know" explicitly.** The absence of information is just as important as its presence. If Person A had information at 14:05 that Person B didn't learn until 14:25, that 20-minute gap is a finding.
- **For incidents spanning many hours or days**, break the timeline into phases (Detection → Diagnosis → Remediation → Verification) and allocate meeting time proportionally to complexity, not duration.
- **If participants disagree about what happened**, don't resolve it in the moment; capture both versions and note "conflicting accounts." Check artifacts later. Disagreements often reveal the most interesting information gaps.
- **Remote facilitation**: Use Miro, FigJam, or a shared Google Doc with a table. The visual progression of the timeline must be visible to all participants simultaneously.
</Resources>
