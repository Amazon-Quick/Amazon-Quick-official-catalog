# Prompt Engineering Retrospective

<Metadata>
Name: Prompt Engineering Retrospective
Category: ai-agent
Aliases: Prompt Optimization Review, Prompt Performance Retro, LLM Prompt Audit
Duration: 30–60 minutes
Team Size: 1–3 (prompt engineers, AI developers)
Best For: Systematic review and iterative improvement of prompt performance using evaluation data rather than trial-and-error
Definition: A structured review of prompt performance over time, analyzing which prompts work well, which fail, and what patterns distinguish effective from ineffective prompts.
</Metadata>

<Gotchas>
1. Use when: Regularly (weekly) during active prompt development; When prompt performance degrades after model updates; After model version changes that may affect prompt interpretation; When expanding an agent to new use cases that stress existing prompts; When evaluation scores plateau and need a breakthrough improvement
2. Do NOT use when: Before having a clear evaluation framework (build evals first); When the issue is fundamental model capability, not prompting; For one-off prompt usage that doesn't justify the investment; When the prompt is performing at 95%+ and marginal gains don't justify effort
3. Vibes-based evaluation: Deciding a prompt is "better" based on a few manual tests without rigorous evaluation. Fix: ALWAYS have an eval set. Run it before AND after. Numbers decide, not feelings.
4. Over-fitting to specific test cases: Optimizing the prompt so perfectly for test cases that it degrades on novel inputs. Fix: Include diverse test cases. Hold out a "validation set" not used during optimization. Test on real production inputs periodically.
5. Changing multiple variables: Modifying system prompt, adding few-shot examples, and changing output format all in one iteration. Fix: One change per cycle. This is scientific method; isolate variables.
6. No version control: Losing track of what was changed when and what the results were. Fix: Version every prompt. Maintain a changelog with not just WHAT changed but WHY and WHAT HAPPENED.
7. Ignoring regressions: Celebrating that 5 cases improved while 3 regressed. Fix: Net improvement is what matters. Every change must be evaluated against the FULL eval set, not just the targeted cases.
</Gotchas>

<Instructions>
<Workflow - Prompt Engineering Retrospective
  description="Step-by-step facilitation guide for Prompt Engineering Retrospective."
>
1. [Setup] (Before session)
   - Run current prompts against evaluation set and record scores
   - Identify which test cases pass and which fail
   - Gather any production failure examples from the past period
   - Have prompt version history accessible (what changed when)
   - Prepare comparison: current version vs. previous version(s) performance

2. [Open] (5 minutes)
   - State purpose: "We're improving prompts through evidence, not vibes. Every change must be measurable and every hypothesis testable."
   - Present current evaluation scores: overall and per-category
   - Compare to previous period: improving, stable, or degrading?
   - Identify focus: which prompt(s) will we work on this session?

3. [Stage: Performance Baseline] (5 minutes)
   - Purpose: Establish exactly where current prompts stand quantitatively
   - Prompt: "What are our current scores? Task completion rate, accuracy, consistency across similar inputs, edge case handling, response quality (human eval)?"
   - Facilitation tip: Use your evaluation framework consistently. Key metrics: task completion rate, output accuracy, consistency (same input → similar output), edge case handling (known difficult cases), and token efficiency. Record these BEFORE making any changes.

4. [Stage: Failure Analysis] (15 minutes)
   - Purpose: Identify specific test cases that fail and understand WHY they fail
   - Prompt: "Which test cases are failing? What patterns distinguish failing cases from passing cases? Is it: ambiguous instructions, missing context, conflicting instructions, edge cases not addressed, or over-constraining?"
   - Facilitation tip: Group failing cases by failure mode: (a) prompt doesn't address this scenario, (b) prompt instructions conflict for this case, (c) prompt wording is ambiguous and model interprets differently than intended, (d) task exceeds model capability regardless of prompt. Each mode suggests a different fix. Look for the ROOT of failure, not just the symptom.

5. [Stage: Hypothesis Generation] (10 minutes)
   - Purpose: Generate specific, testable hypotheses about what changes might improve performance
   - Prompt: "Based on our failure patterns - what specific prompt changes might improve results? Frame as hypotheses: 'If we [change X], then [metric Y] should improve because [reasoning Z].'"
   - Facilitation tip: Be specific and disciplined. BAD: "Make the prompt better." GOOD: "If we add an explicit instruction to handle edge case X by doing Y, then test cases 14, 23, and 31 should pass because they all fail at the same decision point." Each hypothesis should predict specific improvement on specific test cases.

6. [Stage: Implementation] (10 minutes)
   - Purpose: Modify prompts based on top hypothesis, changing ONE thing at a time
   - Prompt: "Let's implement our top hypothesis. What's the minimal change that tests it? Remember: one change at a time so we can attribute results."
   - Facilitation tip: Change ONE variable per iteration. If you change the system prompt, add examples, AND restructure the output format simultaneously, you won't know which helped (or hurt). Version the prompt clearly. Document what changed and why.

7. [Stage: Evaluation] (10 minutes)
   - Purpose: Run modified prompt against the same evaluation set and compare
   - Prompt: "Run the modified prompt against our eval set. Compare: which cases improved? Which stayed the same? Did anything REGRESS?"
   - Facilitation tip: Watch for regressions; fixing one failure mode while introducing another is a net-zero (or negative) change. Compare overall score AND per-case scores. An improvement that fixes 5 cases but breaks 3 is only a net +2. If regression occurs, understand why before iterating.

8. [Stage: Documentation] (5 minutes)
   - Purpose: Record what was tried, what worked, and what was learned about this prompt
   - Prompt: "Document: what hypothesis did we test? What was the change? What was the result? What did we learn about how this prompt/model behaves?"
   - Facilitation tip: Maintain a prompt changelog that's richer than just version diffs. Record the reasoning: "We tried X because we hypothesized Y. Result: Z. Learning: the model is/isn't sensitive to [factor]." This institutional knowledge prevents repeating failed experiments and accelerates future optimization.

9. [Synthesize] (5 minutes)
   - Record new baseline scores (post-change)
   - Update prompt version if improvement confirmed
   - Queue next hypotheses for future sessions
   - Note any evaluation gaps discovered (cases not covered)

10. [Close] (3 minutes)
    - Confirm: Did this session produce a measurably better prompt? (Yes/No)
    - If yes: deploy updated version. If no: revert and try different hypothesis next time.
    - Schedule next prompt engineering retro
</Workflow - Prompt Engineering Retrospective>
</Instructions>

<Templates>
```markdown
# Prompt Engineering Retrospective: [Prompt/Agent Name] - [Date]

**Date:** [Date]
**Prompt:** [Which prompt was reviewed]
**Version Before:** [v X.Y]
**Version After:** [v X.Z (if improved)]
**Participants:** [Names]

## Evaluation Baseline
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Overall accuracy | X% | Y% | +/-Z% |
| Task completion | X% | Y% | +/-Z% |
| Consistency | X% | Y% | +/-Z% |
| Edge case handling | X/Y passing | X/Y | +/-Z |
| Token efficiency | X avg | Y avg | +/-Z |

## Failing Cases Analysis
| Test Case | Failure Mode | Root Cause | Addressed? |
|-----------|-------------|------------|------------|
| [Case ID] | [Mode] | [Why it fails] | Yes/No |
| [Case ID] | [Mode] | [Why it fails] | Yes/No |

## Failure Mode Distribution
| Mode | Count | % of Failures |
|------|-------|---------------|
| Ambiguous instruction | X | Y% |
| Missing scenario coverage | X | Y% |
| Conflicting instructions | X | Y% |
| Model capability limit | X | Y% |

## Hypothesis Tested
- **Hypothesis:** "If we [change], then [cases X,Y,Z] should pass because [reasoning]"
- **Change made:** [Specific prompt modification]
- **Result:** [Confirmed / Partially confirmed / Rejected]
- **Cases improved:** [Which ones]
- **Regressions:** [Any that got worse]

## Prompt Changelog Entry
```
Version: X.Z
Date: [Date]
Change: [What was modified]
Rationale: [Why; linked to hypothesis]
Impact: +X cases passing, -Y regressions, net +Z
Learning: [What we learned about model behavior]
```

## Queued Hypotheses (Next Session)
1. [Next hypothesis to test]
2. [Next hypothesis to test]

## Evaluation Gaps Discovered
- [Test cases we should add to our eval set]
- [Scenarios not currently covered]

## Decision
- [ ] Deploy v X.Z (improvement confirmed)
- [ ] Revert to v X.Y (no improvement or regression)
- [ ] Further testing needed

## Next Session: [Date]
```
</Templates>

<Resources>
- The evaluation set is the foundation. Without it, prompt engineering is superstition. Build your eval set FIRST, then optimize against it. A prompt is only "better" if the eval says so.
- Change one thing at a time. This is non-negotiable for learning. If you change two things and scores improve, you don't know which helped. If scores degrade, you don't know which hurt. Scientific discipline is the difference between prompt engineering and prompt guessing.
- Document learnings about model behavior, not just prompt changes. "This model is sensitive to instruction ordering" or "Few-shot examples help for classification but hurt for creative tasks"; these meta-learnings accelerate all future work.
- Regularly refresh your eval set with real production failures. Eval sets become stale as the prompt improves; the remaining failures are the new frontier for the eval.
- Token efficiency matters for cost and latency. Track it. A prompt that's 20% better but 3x longer may not be worth it. Always evaluate the cost-performance ratio alongside accuracy.
- Consider maintaining a "prompt patterns library"; recurring structures and techniques that work well across different prompts. These become building blocks for new prompt development.
</Resources>
