# Model Performance Retrospective

<Metadata>
Name: Model Performance Retrospective
Category: ai-agent
Aliases: ML Model Review, AI Quality Retro, Model Drift Analysis
Duration: 60–90 minutes
Team Size: 2–5 (ML engineers, data scientists, AI product team)
Best For: Periodic review of AI/ML model performance in production; detecting drift, bias, and degradation to determine retraining or replacement needs
Definition: A periodic review of AI/ML model performance in production, examining accuracy trends, drift, bias, and user satisfaction.
</Metadata>

<Gotchas>
1. Use when: Monthly or quarterly production model review cadence; When performance metrics show decline (accuracy, latency, user satisfaction); After significant changes in input data patterns or user behavior; Regulatory compliance reviews requiring documented model assessment; After major world events or market shifts that may invalidate model assumptions; When user feedback suggests quality issues that metrics don't capture
2. Do NOT use when: Models still in development (use dev metrics and eval sets instead); One-off model usage without production persistence; When clear superior alternatives don't exist yet (review is premature); Less than 30 days after deployment (insufficient production data)
3. Only reacting to complaints: Waiting for user complaints before reviewing model performance. Fix: Proactive monthly/quarterly reviews catch degradation before users notice. By the time users complain, the problem is often severe.
4. Optimizing accuracy without considering fairness: Improving overall accuracy while allowing specific user segments to be underserved. Fix: Always slice metrics by available segments. Overall averages can hide significant inequity.
5. No baseline comparison: Reviewing current metrics without comparing to deployment baseline or previous review. Fix: Always show trajectory. "88% accuracy" means nothing without context; was it 90% last month (declining) or 85% last month (improving)?
6. Model as black box: Treating the model as unchangeable/unquestionable and only adjusting everything around it. Fix: Models are tools. If a tool isn't working, evaluate whether to fix, retrain, or replace it. No model is sacred.
7. Ignoring cost: Continuing to run expensive models without evaluating whether cheaper alternatives could provide adequate performance. Fix: Always include cost analysis. A model that's 2% more accurate but 5x more expensive may not be the right choice.
</Gotchas>

<Instructions>
<Workflow - Model Performance Retrospective
  description="Step-by-step facilitation guide for Model Performance Retrospective."
>
1. [Setup] (1 week prior)
   - Pull production metrics for the review period: accuracy, precision, recall, F1, latency, throughput
   - Run drift detection analysis: compare recent input distributions to training data distributions
   - Compile user feedback and satisfaction signals
   - Pull cost data: inference cost, compute usage, cost per prediction
   - Prepare baseline comparison: deployment-time metrics vs. current
   - If bias monitoring exists, pull fairness metrics across user segments

2. [Open] (5 minutes)
   - State purpose: "We're assessing whether our model is still performing as needed; accuracy, fairness, cost, and user experience. Models degrade over time; our job is to detect and respond."
   - Present the model card: what model, when deployed, what it's trained on, what it's designed to do
   - Frame: "We're asking three questions: Is it still accurate? Is it still fair? Is it still cost-effective?"

3. [Stage: Performance Metrics Review] (15 minutes)
   - Purpose: Establish quantitative current state compared to baseline and targets
   - Prompt: "What are our current accuracy metrics? How do they compare to deployment baseline? Are we within acceptable thresholds? Where specifically is performance degrading?"
   - Facilitation tip: Show metrics as trend lines, not just current values. A model at 88% accuracy is fine if it was deployed at 88%. It's alarming if it was deployed at 95% and is declining. Break down by: prediction type/category, time window (recent vs. older), input source. Look for segments where performance differs significantly.

4. [Stage: Drift Detection] (15 minutes)
   - Purpose: Identify whether input data or concept relationships have shifted since training
   - Prompt: "Has our data changed since the model was trained? Are we seeing new input patterns it hasn't seen before? Has the underlying relationship between inputs and outputs shifted?"
   - Facilitation tip: Two types of drift: (a) Data drift - input distributions are different from training data (new user types, new content patterns, seasonal shifts). (b) Concept drift - the relationship between input and correct output has changed (what WAS the right answer no longer is). Both degrade performance but require different responses: data drift → retrain on new data; concept drift → rethink the model design.

5. [Stage: Bias Audit] (15 minutes)
   - Purpose: Assess whether the model performs equitably across user groups and detect disparate outcomes
   - Prompt: "Are there disparate outcomes across user groups? Does the model perform differently for different demographics, geographies, use cases, or input types? Are we measuring fairness?"
   - Facilitation tip: Slice performance metrics by every available dimension: user segment, geography, language, input type, time of day. Any significant performance gap across segments warrants investigation. Even if overall accuracy is high, specific groups may be poorly served. This is both ethical imperative and product quality issue.

6. [Stage: User Feedback Analysis] (10 minutes)
   - Purpose: Complement quantitative metrics with qualitative user experience signals
   - Prompt: "What are users telling us about quality? Where do they override model outputs? Where do they express dissatisfaction? What do they praise?"
   - Facilitation tip: Quantitative metrics can miss quality issues that users feel. A model might be "technically accurate" but produce outputs in a style users dislike, at a latency they find unacceptable, or with confidence that doesn't match user expectations. User overrides are direct signal: when users reject model output, something is wrong that metrics may not capture.

7. [Stage: Cost-Performance Assessment] (10 minutes)
   - Purpose: Evaluate whether the cost of running the model is justified by its performance
   - Prompt: "What does this model cost to run? Has cost changed? Is the performance-to-cost ratio acceptable? Could a simpler/cheaper model achieve acceptable results?"
   - Facilitation tip: Models have ongoing costs: compute, inference APIs, data pipeline, monitoring. As costs increase (more traffic) or performance decreases (drift), the ROI changes. Consider: Would a smaller/faster model provide 95% of the value at 30% of the cost? Is the current model's advantage worth its premium?

8. [Stage: Remediation Decision] (15 minutes)
   - Purpose: Decide on specific actions based on the assessment findings
   - Prompt: "Based on what we've found - what's the right intervention? Options: No action (fine), retrain on new data, fine-tune for specific segments, adjust thresholds, replace model, or add post-processing?"
   - Facilitation tip: Decision framework:
     - Performance stable, no bias → No action (next review in [cadence])
     - Data drift detected → Retrain on recent data
     - Concept drift detected → Reassess model design and training approach
     - Bias detected → Investigate root cause, adjust training data or add fairness constraints
     - Cost too high → Evaluate model compression, distillation, or simpler alternatives
     - Performance catastrophically degraded → Immediate intervention or rollback

9. [Synthesize] (10 minutes)
   - Document findings, decisions, and action items
   - Update model card with current performance state
   - Set alerting thresholds if not already in place
   - Define criteria for emergency review (what triggers off-cycle review)

10. [Close] (5 minutes)
    - Confirm actions, owners, and timelines
    - Schedule next model performance review
    - Note any monitoring improvements needed
</Workflow - Model Performance Retrospective>
</Instructions>

<Templates>
```markdown
# Model Performance Retrospective: [Model Name] - [Date]

**Date:** [Date]
**Model:** [Name, version, deployment date]
**Period Reviewed:** [Dates]
**Predictions in Period:** [Count]
**Participants:** [Names and roles]

## Performance Summary
| Metric | Baseline (Deploy) | Last Review | Current | Target | Status |
|--------|-------------------|-------------|---------|--------|--------|
| Accuracy | X% | X% | X% | >Y% | ✅/⚠️/❌ |
| Precision | X% | X% | X% | >Y% | ✅/⚠️/❌ |
| Recall | X% | X% | X% | >Y% | ✅/⚠️/❌ |
| F1 Score | X | X | X | >Y | ✅/⚠️/❌ |
| Latency (p50) | Xms | Xms | Xms | <Yms | ✅/⚠️/❌ |
| Latency (p99) | Xms | Xms | Xms | <Yms | ✅/⚠️/❌ |

## Performance Trend
[Describe trend: stable, gradual decline, sudden drop, improvement]
- **Trajectory:** [Stable / Declining at X%/month / Degrading]
- **Time to threshold breach (if declining):** [Estimated date]

## Drift Analysis
### Data Drift
- **Detected:** [Yes/No]
- **Dimensions affected:** [Which input features have shifted]
- **Severity:** [Mild / Moderate / Severe]
- **Evidence:** [Statistical test results or distribution comparisons]

### Concept Drift
- **Detected:** [Yes/No]
- **Nature:** [What relationship has changed]
- **Severity:** [Mild / Moderate / Severe]
- **Evidence:** [Performance degradation pattern]

## Bias Audit
| Segment | Accuracy | Precision | Recall | Gap vs. Overall |
|---------|----------|-----------|--------|-----------------|
| [Segment A] | X% | X% | X% | +/-Y% |
| [Segment B] | X% | X% | X% | +/-Y% |
| [Segment C] | X% | X% | X% | +/-Y% |

**Bias Assessment:** [No significant bias / Concerning gap in segment X / Action needed]

## User Feedback
- **Override rate:** X% (users rejecting model output)
- **Satisfaction signals:** [Summary]
- **Common complaints:** [Themes]
- **Praise:** [What users appreciate]

## Cost Analysis
| Metric | Value | Trend | Acceptable? |
|--------|-------|-------|-------------|
| Cost per prediction | $X | ↑↓→ | Yes/No |
| Monthly total cost | $X | ↑↓→ | Yes/No |
| Cost vs. value delivered | Ratio X | ↑↓→ | Yes/No |

## Decision
**Action:** [No action / Retrain / Fine-tune / Adjust thresholds / Replace / Rollback]
**Rationale:** [Why this action was chosen]
**Timeline:** [When action will be taken]
**Success Criteria:** [How we'll verify the action worked]

## Updated Model Card
- **Current performance state:** [Summary]
- **Known limitations:** [Updated]
- **Recommended use conditions:** [Updated]

## Monitoring & Alerting
- **Current alerts:** [What's monitored]
- **Gaps:** [What should be monitored but isn't]
- **Emergency review trigger:** [Conditions that trigger off-cycle review]

## Next Review: [Date]
```
</Templates>

<Resources>
- Schedule this review on a fixed cadence BEFORE problems emerge. Models degrade silently; by the time humans notice quality issues, the model may have been underperforming for weeks. Monthly minimum for production models.
- The drift detection stage is technical but critical. Data drift means the world changed (new user types, new content); concept drift means the rules changed (what WAS correct no longer is). Both require different responses. If your monitoring doesn't distinguish between them, fix that first.
- Bias auditing should not be optional. Even well-intentioned models can develop disparate impacts as usage grows and diversifies. Slice performance by every available dimension and investigate significant gaps.
- The "emergency review trigger" is important to define in advance. What performance level triggers immediate review? What user feedback pattern? What drift severity? Having predefined triggers means you don't have to wait for the scheduled review when things go wrong fast.
- Consider maintaining a "model health dashboard" that's always visible - not just reviewed at these sessions. The dashboard provides continuous monitoring; the retro provides deeper analysis and decision-making.
- When the decision is "retrain," define exactly: retrain on what data, with what configuration, and how you'll verify the retrained model is better before deploying. "Retrain" without a plan is wishful thinking.
</Resources>
