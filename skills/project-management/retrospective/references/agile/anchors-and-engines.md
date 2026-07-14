# Anchors & Engines

<Metadata>
Name: Anchors & Engines
Category: agile
Aliases: Anchors and Engines, Drag & Drive, Forces Retrospective
Duration: 25-40 minutes
Team Size: 3-8 (max 12)
Best For: Teams focused on delivery speed and throughput who need to identify what's driving and dragging their velocity
Definition: A dual-force retrospective that identifies what's propelling the team forward (Engines) and what's slowing them down (Anchors), adapted from force field analysis and focused specifically on velocity and throughput optimization.
</Metadata>

<Gotchas>
1. Use when: Velocity/throughput is the primary concern; team feels sluggish and needs to identify blockers; quick, focused format for time-constrained teams; Sailboat is too complex but you want force-analysis; DevOps and delivery-focused teams
2. Do NOT use when: Need to address interpersonal issues (too mechanistic); quality or learning is more important than speed; "speed" metaphor is counterproductive (burnout risk); forward-looking risk assessment is needed (use Sailboat instead)
3. All anchors, no engines: Team only sees problems, and hopelessness sets in. Fix: Insist on balanced contribution. Ask "What IS working? Even something small."
4. Vague anchors: "Communication" isn't actionable. Fix: Press for the specific communication breakdown, such as "daily standup running 30 minutes with 12 people."
5. Speed at all costs: The velocity metaphor justifies cutting corners on quality. Fix: Explicitly note that sustainable speed includes quality. An anchor can be "tech debt from skipping tests."
6. Ignoring engines: Discussing only problems without amplifying strengths. Fix: Engines need attention too. Ask "How do we get MORE of this?"
7. No measurement: "Cut this anchor" without defining how you'll know it's been cut. Fix: Define the expected improvement, such as "reduce standup from 30 to 15 minutes."
</Gotchas>

<Instructions>
<Workflow - Anchors & Engines
  description="Facilitation guide for Anchors & Engines retrospective."
>
1. [Setup] Prepare a board with two sections: "Engines 🚀" (left) and "Anchors ⚓" (right). Optionally draw a boat in the center. Optionally add a third section: "Captain's Compass 🧭." Use green (engines) and red (anchors) sticky notes. Allocate time: 5 min engines, 5 min anchors, 10 min discussion, 5 min actions, 3 min close.
2. [Open] (2 minutes)
   - Read the Prime Directive
   - Frame: "Simple question today: What's driving us forward, our engines? And what's dragging us back, our anchors? Let's figure out how to rev up the engines and cut the anchors."
3. [Stage: Identify Engines] (5 minutes)
   - Purpose: Acknowledge what's giving the team momentum. Always start positive.
   - Prompt: "What's driving us forward? What practices, tools, conditions, or behaviors are giving us speed and momentum? What makes us GO?"
   - Facilitation tip: Start with engines to build energy. Be specific: not "good teamwork" but "pair programming on complex PRs."
4. [Stage: Identify Anchors] (5 minutes)
   - Purpose: Surface what's creating drag and slowing delivery
   - Prompt: "What's dragging us back? What's creating friction, blocking us, or slowing us down? If you could cut one thing loose, what would it be?"
   - Facilitation tip: Push for specificity. "Meetings" is too vague; "daily standup running 30 minutes with 12 people" is actionable.
5. [Stage: Captain's Compass (Optional)] (3 minutes)
   - Purpose: Set direction for where the team should steer
   - Prompt: "If we could steer in any direction next sprint, where should we point? What should we optimize for?"
   - Facilitation tip: Skip this if time is tight. It adds value but isn't essential.
6. [Stage: Discuss & Vote] (10 minutes)
   - Purpose: Prioritize which engines to amplify and which anchors to cut
   - Prompt: "Vote: Which engine can we rev up the most? Which anchor is the heaviest drag? Let's discuss the top-voted items."
   - Facilitation tip: For each anchor, ask: "What's the MINIMUM action that would reduce this drag by 50%?"
7. [Synthesize] Create two types of actions: "Rev Up" (amplify engines) and "Cut Loose" (remove anchors). Each needs a specific, measurable outcome.
8. [Close] (3 minutes)
   - Read actions: "We're revving up X and cutting loose Y."
   - Quick pulse: "Do we feel faster or slower than last sprint?"
   - Thank the team. Keep it brief; this format respects velocity in its own execution.
</Workflow - Anchors & Engines>
</Instructions>

<Templates>
```markdown
# Anchors & Engines Retrospective
**Date:** [YYYY-MM-DD]
**Sprint/Iteration:** [name or number]
**Participants:** [list]

## 🚀 Engines (What's Driving Us Forward)
- [Momentum source]
- [Momentum source]
- [Momentum source]

## ⚓ Anchors (What's Dragging Us Back)
- [Drag force / impediment]
- [Drag force / impediment]
- [Drag force / impediment]

## 🧭 Captain's Compass (Direction, optional)
- [Where we should steer next]

## Velocity Actions
| Action | Type | Impact | Owner | Due Date |
|--------|------|--------|-------|----------|
| [amplify this] | Rev Up | [expected improvement] | [name] | [date] |
| [remove this] | Cut Loose | [expected improvement] | [name] | [date] |

## Velocity Pulse
- Team velocity feeling: [faster / same / slower] than last sprint
```
</Templates>

<Resources>
- This format is the "speed-focused cousin" of Sailboat. Use it when time is short and velocity is the priority
- Always discuss Engines first. It builds energy and reminds the team that things ARE working
- For anchors, the question "Can we cut this TOMORROW?" separates quick wins from systemic issues
- Pairs well with sprint velocity metrics. Bring the actual numbers to ground the discussion
- For DevOps teams, frame as: "What's improving our DORA metrics? What's hurting them?"
- Great format for mid-sprint check-ins: "Quick 15 minutes. Any new anchors since Monday?"
- If you add the Captain's Compass, use it to connect to OKRs or sprint goals
</Resources>
