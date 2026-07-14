# Phase-Gate Review

<Metadata>
Name: Phase-Gate Review
Category: project
Aliases: Stage-Gate Review, Toll-Gate Review, Phase Review, Gate Review
Duration: 60–120 minutes
Team Size: 5–20
Best For: Formal go/no-go decision points between project phases that combine deliverable evaluation with retrospective learning
Definition: A formal go/no-go decision point between project phases where stakeholders evaluate progress, risks, and business case against predefined criteria.
</Metadata>

<Gotchas>
1. Use when: Waterfall or hybrid project methodologies with distinct phases; High-risk, high-investment projects requiring formal governance; Regulated industries requiring documented review and approval; Portfolio management contexts where resource allocation decisions are made; Product development with distinct stages (concept → design → build → test → launch)
2. Do NOT use when: Pure Agile environments (use sprint reviews and retros instead); Small, low-risk projects where formality adds overhead without value; When the gate would slow time-to-market without meaningful risk reduction; If decision makers lack authority to actually stop or redirect projects
3. Rubber stamp gates: All projects pass all gates automatically. Gates exist on paper but never actually stop or redirect a project. Fix: Decision makers must have authority AND willingness to kill projects. Track kill rate. If it's 0%, gates aren't functioning.
4. Governance without learning: Gates become pure checklist exercises without retrospective reflection. Fix: Always include the phase retrospective stage; it's where organizational learning happens.
5. Criteria drift: Gate criteria are changed mid-project to ensure passage. Fix: Criteria are set at project initiation and only changed through formal change control.
6. Missing decision makers: People in the room can't actually approve/reject/redirect. Fix: Only schedule when actual decision makers are available. Delegate authority explicitly if needed.
7. Phase leakage: Work from the next phase starts before the gate review. Fix: Enforce the gate. No next-phase work begins until the decision is formally made.
</Gotchas>

<Instructions>
<Workflow - Phase-Gate Review
  description="Step-by-step facilitation guide for Phase-Gate Review."
>
1. [Setup] (1 week prior)
   - Define gate criteria for this specific gate (should have been set at project initiation)
   - Prepare deliverable evidence package: completed artifacts, test results, metrics
   - Prepare business case update: market changes, ROI projections, competitive landscape
   - Prepare risk register update: mitigated risks, new risks, residual risks
   - Invite decision makers (must have authority to approve/reject/redirect)
   - Distribute materials 3–5 days in advance for pre-reading
   - Prepare the retrospective component: what was learned in this phase

2. [Open] (10 minutes)
   - State purpose: "We're here to evaluate whether this project should proceed to the next phase, and to capture what we've learned"
   - Review gate criteria (predefined at project start)
   - Clarify decision options: Go, No-Go, Conditional Go, Recycle (redo phase), Kill

3. [Stage: Deliverable Review] (20 minutes)
   - Purpose: Verify that phase deliverables meet predefined quality standards
   - Prompt: "Has each required deliverable been completed to the standard defined at project initiation? Where are there gaps?"
   - Facilitation tip: Use a checklist format. For each deliverable, rate as Complete/Partial/Not Started. Don't debate quality in abstract. Reference specific acceptance criteria defined at the start.

4. [Stage: Business Case Check] (15 minutes)
   - Purpose: Validate that the business rationale for the project remains sound
   - Prompt: "Given what we now know, has anything changed in the market, competitive landscape, or internal priorities that affects the business case?"
   - Facilitation tip: This is where projects get killed appropriately. Present updated ROI, market data, and strategic fit. A project that made sense 6 months ago may not make sense now. This is healthy, not failure.

5. [Stage: Risk Assessment] (15 minutes)
   - Purpose: Evaluate current risk landscape and readiness for next phase
   - Prompt: "What risks have we mitigated? What new risks have emerged? Are residual risks acceptable for proceeding?"
   - Facilitation tip: Walk through the risk register. Highlight any risks that changed severity. Pay special attention to risks that materialized vs. those that were over/under-estimated. This improves future risk assessment.

6. [Stage: Phase Retrospective] (20 minutes)
   - Purpose: Extract learning from the completed phase before moving forward
   - Prompt: "What did we learn during this phase that the team needs to carry forward? What would we do differently if we repeated this phase?"
   - Facilitation tip: This is the retrospective heart of the gate review. Don't skip it in favor of pure governance. Use silent writing (5 min) then discussion. Capture insights about process, collaboration, and technical approach.

7. [Stage: Go/No-Go Decision] (15 minutes)
   - Purpose: Make a clear, documented decision about project continuation
   - Prompt: "Based on deliverable status, business case validity, risk profile, and lessons learned, what is our decision?"
   - Facilitation tip: Decision options: Go (proceed as planned), Conditional Go (proceed with conditions), Recycle (redo part of the phase), Hold (pause pending external input), Kill (terminate project). Document the decision and rationale explicitly.

8. [Synthesize] (10 minutes)
   - Document the decision with rationale
   - Capture conditions (if Conditional Go)
   - Confirm next phase plan: resources, timeline, success criteria for next gate
   - Assign action items from lessons learned

9. [Close] (5 minutes)
   - Confirm documentation ownership and distribution
   - Thank participants
   - Confirm next gate date and criteria
</Workflow - Phase-Gate Review>
</Instructions>

<Templates>
```markdown
# Phase-Gate Review: [Project Name] - Gate [#]

**Date:** [Date]
**Phase Completed:** [Phase name]
**Next Phase:** [Phase name]
**Decision Makers:** [Names and roles]
**Facilitator:** [Name]

## Gate Decision
**Decision:** [Go | Conditional Go | Recycle | Hold | Kill]
**Rationale:** [2-3 sentences explaining the decision]
**Conditions (if applicable):** [What must happen before proceeding]

## Deliverable Assessment
| Deliverable | Status | Notes |
|-------------|--------|-------|
| [Deliverable 1] | ✅ Complete | [Notes] |
| [Deliverable 2] | ⚠️ Partial | [What's missing] |
| [Deliverable 3] | ✅ Complete | [Notes] |

## Business Case Status
- **Original ROI projection:** [X]
- **Updated ROI projection:** [Y]
- **Market changes:** [Summary]
- **Strategic alignment:** [Still aligned / Shifted]

## Risk Register Update
| Risk | Previous Severity | Current Severity | Trend | Mitigation |
|------|-------------------|------------------|-------|------------|
| [Risk 1] | High | Medium | ↓ | [Mitigated by...] |
| [Risk 2] | Low | High | ↑ | [Plan needed] |

## Phase Retrospective Findings
### What we learned:
1. [Key learning]
2. [Key learning]
3. [Key learning]

### What to carry forward:
1. [Practice/approach to continue]
2. [Adjustment for next phase]

## Next Phase Plan
- **Duration:** [Expected timeline]
- **Resources:** [Team changes, if any]
- **Key deliverables:** [What gate N+1 requires]
- **Next gate date:** [Date]
- **Next gate criteria:** [Summary]

## Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| [Action] | [Name] | [Date] |
```
</Templates>

<Resources>
- Gate criteria must be predefined at project initiation, not invented at review time. If criteria don't exist, the first action item is establishing them for the next gate.
- The business case check is the most valuable and most often skipped stage. Projects develop momentum ("sunk cost") that makes stakeholders reluctant to question viability. Challenge this explicitly.
- For the retrospective component, separate it slightly from the governance discussion. People are more honest about what they learned when it's not immediately followed by a pass/fail judgment.
- Conditional Go is the most common and most dangerous decision. Conditions must be specific, measurable, time-bound, and actively tracked. Vague conditions ("improve quality") are meaningless.
- Consider having a "devil's advocate" role assigned to one participant whose explicit job is to argue for No-Go. This counterbalances organizational optimism bias.
</Resources>
