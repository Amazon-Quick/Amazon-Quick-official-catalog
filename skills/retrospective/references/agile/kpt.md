# Keep/Problem/Try (KPT)

<Metadata>
Name: Keep/Problem/Try (KPT)
Category: agile
Aliases: KPT Framework, Keep-Problem-Try
Duration: 30-45 minutes
Team Size: 3-8 (max 10)
Best For: Teams embracing continuous improvement (Kaizen) where changes are framed as experiments to reduce resistance
Definition: A three-column Japanese retrospective format (Keep, Problem, Try) where the distinctive "Try" column frames actions as time-boxed experiments rather than permanent commitments, reflecting Kaizen philosophy that makes it safe to fail and reduces resistance to change.
</Metadata>

<Gotchas>
1. Use when: Team is resistant to process changes (framing as experiments reduces resistance); continuous improvement culture (Kaizen mindset); previous action items never get completed (Try = smaller, lower-commitment); teams practicing Kaizen or Lean methodologies; team needs permission to fail, experiments can end without shame
2. Do NOT use when: Urgent problems requiring decisive, permanent action (not experiments); "Try" becomes an excuse for non-commitment to necessary changes; permanent process changes are clearly needed and well-understood; team is already running too many experiments simultaneously
3. Too many Tries: Selecting 4-5 experiments dilutes attention and guarantees none will be properly evaluated. Fix: Limit to 1-2 per sprint; this is the hardest discipline but the most important.
4. Try without criteria: "Try pair programming" means nothing without measurement. Fix: Define hypothesis, duration, and success criteria: "for 1 sprint, measuring PR review time."
5. Try as avoidance: Using "let's try" to avoid committing to clearly needed permanent changes. Fix: If the answer is obvious and well-understood, just do it; don't hide behind "experimentation."
6. Never evaluating experiments: Running Tries without ever assessing results at the next retro. Fix: ALWAYS evaluate previous Tries at the start of the next KPT retro; this creates the feedback loop.
7. Problems without connected Tries: Identifying problems but not generating experiments to address them. Fix: Connect Problems to Tries explicitly; draw lines on the board from each selected Try back to its Problem.
</Gotchas>

<Instructions>
<Workflow - KPT
  description="Facilitation guide for Keep/Problem/Try retrospective."
>
1. [Setup] Prepare a board with three columns: "Keep ✅," "Problem ⚠️," and "Try 🧪." The "Try" column should visually emphasize its experimental nature (add a beaker icon, "experiment" subtitle). Allocate time: 5 min reflection, 10 min sharing, 10 min discussion, 10 min experiment design, 5 min close.
2. [Open] (3 minutes)
   - Read the Prime Directive
   - Frame: "Three questions today. What should we KEEP doing? What PROBLEMS did we encounter? And what should we TRY next? Note: Try means EXPERIMENT: not a permanent commitment. We'll try it for one sprint and evaluate."
   - Emphasize: "Try ≠ commit forever. Try = run a time-boxed experiment. If it doesn't work, we stop, no shame."
3. [Stage: Individual Reflection] (5 minutes)
   - Purpose: Generate items across all three dimensions
   - Prompt: "KEEP: What practices worked well and should continue? What's worth preserving? PROBLEM: What problems did we encounter? What frustrated us? What got in our way? TRY: What experiments could we run? What new approach might address a problem? What's worth testing?"
   - Facilitation tip: Encourage connecting Problems to Tries; each Try should ideally address a Problem.
4. [Stage: Share Keep Items] (3 minutes)
   - Purpose: Celebrate what's working; start positive
   - Prompt: "What should we keep? These are our proven practices: what's working."
   - Facilitation tip: Quick celebration. These are stable; acknowledge and move on.
5. [Stage: Share Problems] (5 minutes)
   - Purpose: Surface pain points without blame
   - Prompt: "What problems did we face? No blame, just honest identification of what's not working. What got in our way?"
   - Facilitation tip: Listen without immediately jumping to solutions. Understand the problem space before proposing Tries.
6. [Stage: Generate Tries] (5 minutes)
   - Purpose: Design experiments to address problems
   - Prompt: "What experiments could we try? For each Problem: What's one small thing we could TEST next sprint to see if it helps? Frame it as: 'Let's try [X] for [duration] and see if [outcome].'"
   - Facilitation tip: Push for the experimental frame: "What's the hypothesis? What would success look like? How will we know if it worked?"
7. [Stage: Select Experiments] (5 minutes)
   - Purpose: Choose 1-2 experiments with clear success criteria
   - Prompt: "We can only run 1-2 experiments well. Which Tries have the most potential? Vote on which to run. For each selected: What's the hypothesis? What's the success criteria? How long do we try?"
   - Facilitation tip: LIMIT to 1-2 Tries maximum. Quality over quantity. More experiments = diluted attention.
8. [Synthesize] Document: Keeps (preserve), Problems (awareness), and 1-2 selected Tries with hypothesis, duration, and success criteria.
9. [Close] (5 minutes)
   - Read the experiment design: "We're trying [X] for [Y duration]. We'll know it worked if [Z]."
   - Ask: "What Problem are you most hopeful we can solve with this Try?"
   - Commit: "Next retro, we'll evaluate, did the experiment work?"
   - Thank the team for experimental thinking
</Workflow - KPT>
</Instructions>

<Templates>
```markdown
# KPT Retrospective
**Date:** [YYYY-MM-DD]
**Sprint/Iteration:** [name or number]
**Participants:** [list]

## ✅ Keep (Practices to preserve)
- [Working practice to continue]
- [Working practice to continue]
- [Working practice to continue]

## ⚠️ Problem (Issues encountered)
- [Problem identified]
- [Problem identified]
- [Problem identified]

## 🧪 Try (Experiments to run)
### All Proposed Tries
- Try [idea] to address [problem]
- Try [idea] to address [problem]
- Try [idea] to address [problem]

### Selected Experiments (1-2 max)
| Experiment | Addresses | Hypothesis | Duration | Success Criteria | Owner |
|-----------|-----------|-----------|----------|-----------------|-------|
| Try [X] | [Problem Y] | If we [X], then [expected outcome] | [1-2 sprints] | [measurable criteria] | [name] |

## Experiment Evaluation (from previous retro)
| Previous Try | Result | Verdict |
|-------------|--------|---------|
| [last sprint's experiment] | [what happened] | [Keep / Drop / Extend] |

## Notes
[Additional context or observations]
```
</Templates>

<Resources>
- The "Try" framing is psychologically powerful. It reduces resistance to change by making it SAFE to fail
- ALWAYS evaluate previous Tries at the start of the next KPT retro. This creates the feedback loop
- Connect Problems to Tries explicitly: draw lines on the board from each selected Try back to its Problem
- Limit Tries to 1-2 per sprint. This is the hardest discipline but the most important
- The experimental mindset is from Japanese Kaizen; small, continuous, evaluated improvements
- For teams that "don't have time" to try new things: frame as "this IS the smallest possible investment"
- Success criteria transform vague intentions into measurable experiments; insist on them
- KPT pairs beautifully with hypothesis-driven development teams who already think in experiments
</Resources>
