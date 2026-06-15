# Chaos Engineering Retrospective

<Metadata>
Name: Chaos Engineering Retrospective
Category: incident
Aliases: Game Day Debrief, Chaos Experiment Review, Resilience Testing Retro, DiRT Review, Failure Injection Debrief
Duration: 45–60 minutes
Team Size: 4–8 (experiment participants); max 12
Best For: Reviewing planned failure injection experiments (game days, chaos tests) to assess system resilience AND team response preparedness
Definition: A retrospective conducted after intentional chaos engineering experiments (game days, failure injection tests, disaster recovery drills) to analyze both system and human response, providing incident learning WITHOUT incident pain by proactively identifying gaps before they manifest in production.
</Metadata>

<Gotchas>
1. Use when: after game days or chaos engineering experiments (failure injection, latency injection, resource exhaustion); after disaster recovery drills or failover tests; when assessing incident readiness and on-call preparedness; after load testing that revealed unexpected behavior; after tabletop exercises or incident simulations; when evaluating whether previous postmortem improvements actually work; after red team or security chaos engineering exercises
2. Do NOT use when: for unplanned production incidents (use Blameless Postmortem or Learning Review); when chaos engineering practice isn't established; non-technical teams without systems to test against; when the experiment didn't actually run; for routine deployments or canary releases that went normally
3. Running experiments without reviewing results. The retro IS the value delivery mechanism; an experiment without a retro is just breaking things for fun. Fix: make the retro a mandatory part of every chaos experiment
4. Only grading system response, ignoring human response. Systems don't exist in isolation; if the team doesn't know the system is auto-healing, they can't trust it or intervene when it fails. Fix: grade both system and human response dimensions separately
5. No hypothesis before the experiment. Without a clear expectation you can't distinguish between "system worked as designed" and "we got lucky." Fix: define expected behavior BEFORE injection in a testable hypothesis format
6. Experiments that are too safe. If every experiment scores 5/5, you're not testing at the edge of capability. Fix: push beyond comfortable boundaries with appropriate safety rails; the goal is to find failures
7. Never re-testing after improvements. Fixing a gap but never re-running the experiment means trusting but not verifying. Fix: schedule the re-test that verifies the fix works as part of the improvement plan
8. Chaos experiments only in staging. Staging environments lie; production is where real behavior lives. Fix: graduate experiments to production with appropriate blast radius controls
9. Not sharing results beyond the team. Findings often reveal systemic patterns affecting other teams. Fix: publish results internally for cross-team learning
</Gotchas>

<Instructions>
<Workflow - Chaos Engineering Retrospective
  description="Facilitation guide for Chaos Engineering Retrospective."
>
1. [Setup] (Before the meeting, immediately after the experiment concludes)
   - Collect experiment data: hypothesis document, monitoring dashboards during experiment, alert records, team communication logs, runbook adherence records, system metrics (latency, error rates, availability)
   - Document the experiment parameters: what was injected, blast radius, duration, abort criteria
   - Identify all participants: experiment runners, on-call responders, observers
   - Prepare the hypothesis-vs-reality comparison: what did we expect to happen vs. what actually happened?
   - Schedule the retro within 24 hours of the experiment while observations are fresh

2. [Open] (5 minutes)
   - Purpose: Frame as a learning opportunity from a controlled experiment with lower stakes than an incident retro
   - Prompt: "We just ran a controlled experiment to test our system's resilience. This is our chance to learn from a planned failure without any of the stress of a real incident. Everything we surface here is valuable, whether the system passed or failed. Finding gaps NOW is the whole point. Let's be thorough and honest."
   - Facilitation tip: The psychological safety bar is lower for chaos retros than incident retros because there's no "at-fault" party; the experiment was intentional. Use this advantage to push for more candor about gaps and concerns.

3. [Stage: Experiment Design Review] (10 minutes)
   - Purpose: Evaluate whether the experiment itself was well-designed and safely executed
   - Prompt: "Let's review our experiment design. Was the hypothesis clear and testable? Was the blast radius appropriate? Were abort criteria defined and respected? Did we have proper observability during the test? Would we change anything about how we ran the experiment?"
   - Facilitation tip: This is meta-learning: improving the practice of chaos engineering itself. If the experiment was poorly designed (unclear hypothesis, too broad blast radius, no monitoring), the results are unreliable. Capture experiment design improvements separately from system improvements.

4. [Stage: System Response Assessment] (15 minutes)
   - Purpose: Grade how technical systems responded to the injected failure
   - Prompt: "How did our systems respond? Walk through each expected behavior: Did failovers trigger? Did circuit breakers activate? Did auto-scaling respond? Did graceful degradation work as designed? Where did systems behave as expected, and where did they surprise us?"
   - Facilitation tip: Use the hypothesis as your scorecard. For each expected system behavior, grade: ✅ Worked as designed, ⚠️ Partially worked / degraded, ❌ Failed or didn't activate, 🤷 Unknown / not observable. Unknown is a finding; if you can't observe a behavior, you can't rely on it.

5. [Stage: Human Response Assessment] (10 minutes)
   - Purpose: Grade how the team responded: detection, diagnosis, communication, remediation
   - Prompt: "How did the team respond? When did we detect the failure? How long did diagnosis take? Were runbooks followed? Were they helpful? Were alerts actionable? Did escalation work? Where did human response exceed or fall short of expectations?"
   - Facilitation tip: Grade team response separately from system response. A system can fail gracefully (good) while the team panics (bad), or vice versa. Both matter. Be specific: "Time from injection to first human awareness was 7 minutes. Is that acceptable for this failure mode?"

6. [Stage: Surprises and Unexpected Behavior] (10 minutes)
   - Purpose: Surface behaviors that weren't part of the hypothesis, positive or negative
   - Prompt: "What surprised us? What happened that we didn't predict, either system behavior or human behavior? What side effects did the experiment produce that we didn't anticipate? What did we learn that we didn't set out to learn?"
   - Facilitation tip: Surprises are the highest-value findings. They reveal the gap between our mental model of the system and its actual behavior. A chaos experiment that produces no surprises either (a) validated exactly what you expected (good) or (b) wasn't aggressive enough to reveal real behavior (common).

7. [Stage: Gap Identification] (5 minutes)
   - Purpose: Compile all identified weaknesses into an actionable gap list
   - Prompt: "What gaps were exposed? Compile everything: system resilience gaps, monitoring/observability gaps, runbook gaps, team preparedness gaps, communication gaps. For each gap: how critical is it if this failure happened unplanned in production?"
   - Facilitation tip: Categorize gaps by severity: Critical (would cause major customer impact if unplanned), Important (would extend incident duration or complicate response), Nice-to-have (would improve efficiency but not critical). This prioritization drives the improvement backlog.

8. [Synthesize] (5 minutes)
   - Purpose: Grade overall readiness and identify systemic patterns
   - Prompt: "Overall, how ready are we for this failure mode in production? On a scale of 1–5, where 1 is 'would be a major incident' and 5 is 'fully automated recovery, team barely notices.' What systemic patterns do we see across this and previous experiments?"
   - Facilitation tip: Track readiness scores over time across experiments. Improving scores validate your resilience investment. Flat or declining scores indicate systemic issues. Compare this experiment's findings to previous experiment findings and production incident findings; convergence means the experiments are realistic.

9. [Close] (5 minutes)
   - Purpose: Plan improvements and the next experiment
   - Prompt: "What are our top 3 improvements to implement before the next experiment? Who owns each? When will they be done? And what should our NEXT experiment test? What hypothesis are we most uncertain about now?"
   - Facilitation tip: The chaos engineering cycle is: Hypothesize → Experiment → Learn → Improve → Re-test. Close by planning the next iteration. If an improvement addresses a critical gap, don't just add it to the backlog; schedule the re-test that will verify the fix works.
</Workflow - Chaos Engineering Retrospective>
</Instructions>

<Templates>
```markdown
# Chaos Engineering Retrospective: [Experiment Name]

**Date:** YYYY-MM-DD
**Experiment Type:** [Failure injection / Latency injection / Resource exhaustion / DR drill / Game day]
**Facilitator:** [Name]
**Participants:** [Names and roles]
**Related System:** [Service/system tested]

## Experiment Parameters
**Hypothesis:** "We believe that when [failure condition], [system/service] will [expected behavior], and the team will [expected response]."
**Injection Type:** [What was injected]
**Blast Radius:** [What was affected / scope limitation]
**Duration:** [How long the injection lasted]
**Abort Criteria:** [Conditions that would trigger experiment halt]
**Abort Triggered:** Yes / No

## Results Summary
**Overall Readiness Score:** [1-5] (1=major incident, 5=full automated recovery)
**Hypothesis Validated:** Yes / Partially / No

## System Response Scorecard
| Expected Behavior | Result | Notes |
|------------------|--------|-------|
| [Failover triggers within X seconds] | ✅ / ⚠️ / ❌ / 🤷 | [Details] |
| [Circuit breaker activates] | ✅ / ⚠️ / ❌ / 🤷 | [Details] |
| [Graceful degradation engages] | ✅ / ⚠️ / ❌ / 🤷 | [Details] |
| [Auto-scaling responds] | ✅ / ⚠️ / ❌ / 🤷 | [Details] |
| [Data integrity maintained] | ✅ / ⚠️ / ❌ / 🤷 | [Details] |

## Human Response Scorecard
| Metric | Expected | Actual | Grade |
|--------|----------|--------|-------|
| Detection time | [Target] | [Actual] | ✅ / ⚠️ / ❌ |
| Diagnosis time | [Target] | [Actual] | ✅ / ⚠️ / ❌ |
| Communication initiated | [Target] | [Actual] | ✅ / ⚠️ / ❌ |
| Escalation (if needed) | [Target] | [Actual] | ✅ / ⚠️ / ❌ |
| Resolution time | [Target] | [Actual] | ✅ / ⚠️ / ❌ |
| Runbook followed | Yes / No / Partial | - | ✅ / ⚠️ / ❌ |

## Surprises
- [Unexpected behavior 1 - what it reveals]
- [Unexpected behavior 2 - what it reveals]
- [Unexpected behavior 3 - what it reveals]

## Gaps Identified
### Critical (would cause major customer impact if unplanned)
- [Gap 1] - Improvement: [What to fix]
- [Gap 2] - Improvement: [What to fix]

### Important (would extend incident or complicate response)
- [Gap 3] - Improvement: [What to fix]
- [Gap 4] - Improvement: [What to fix]

### Nice-to-Have (efficiency improvement)
- [Gap 5] - Improvement: [What to fix]

## Improvement Actions
| # | Action | Priority | Owner | Deadline | Verification |
|---|--------|----------|-------|----------|--------------|
| 1 | [Specific fix] | Critical | [Name] | [Date] | [Re-test method] |
| 2 | [Specific fix] | Important | [Name] | [Date] | [Re-test method] |
| 3 | [Specific fix] | Nice-to-have | [Name] | [Date] | [Re-test method] |

## Runbook Updates Needed
- [ ] [Runbook X] - [What to add/change]
- [ ] [Runbook Y] - [What to add/change]

## Alert/Monitoring Updates Needed
- [ ] [Alert to add/modify]
- [ ] [Dashboard to create/update]

## Next Experiment
**Hypothesis:** "[Next thing to test based on today's learnings]"
**Tentative Date:** [When]
**Focus Area:** [What we're most uncertain about]

## Experiment Design Improvements
- [How to improve the experiment process itself for next time]
```
</Templates>

<Resources>
- **Keep the scorecard visual.** A grid of ✅/⚠️/❌ is immediately comprehensible and tracks progress over repeated experiments. Put it on a dashboard that the team sees regularly.
- **Compare against previous experiments.** "Last quarter, detection time was 12 minutes. This quarter it's 4 minutes. The new alerting rule is working." Progress visibility motivates continued investment in resilience.
- **Grade the experiment design too.** If the experiment revealed nothing surprising, ask: Was the hypothesis too conservative? Was the blast radius too small? Was the duration too short? Improve the experiments, not just the systems.
- **Connect findings to real incidents.** "This gap we found in our chaos experiment? That's exactly what caused the Sev1 in March." This connection justifies ongoing chaos engineering investment to leadership.
- **Track the ratio of "found in chaos experiment" vs "found in production incident."** The goal is to shift discoveries left, finding gaps proactively rather than reactively. A healthy ratio improves over time.
- **Include observers from adjacent teams** who share similar architecture or failure modes. Their systems likely have similar gaps. One experiment can produce learning for multiple teams.
- **For the first few experiments, be explicit that "the experiment failing (revealing gaps) is success."** Teams new to chaos engineering feel pressure for systems to pass. Reframe: we're here to learn, not to score well.
</Resources>
