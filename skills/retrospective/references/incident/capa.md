# Corrective and Preventive Actions (CAPA)

<Metadata>
Name: Corrective and Preventive Actions (CAPA)
Category: incident
Aliases: CAPA Process, Corrective/Preventive Action, Quality Improvement Cycle, CAPA Report
Duration: 60–90 minutes (initial investigation meeting); days to weeks (full CAPA lifecycle)
Team Size: 3–6 (cross-functional investigation team)
Best For: Regulated industries requiring formal root-cause investigation, documented corrective actions, and verified effectiveness - pharma, medical devices, manufacturing, food safety
Definition: A structured quality management process formalized through ISO 9001 and FDA regulations that identifies root causes of nonconformities, implements solutions, and verifies effectiveness, explicitly separating corrective actions (fix the existing problem) from preventive actions (eliminate the potential for the same class of problem to recur).
</Metadata>

<Gotchas>
1. Use when: after quality events, deviations, or nonconformances in regulated environments; when regulatory compliance requires documented root-cause analysis (FDA, ISO 9001, ISO 13485); after customer complaints indicating systemic quality issues; following internal or external audit findings; when a problem has recurred multiple times; proactive risk management for identified risks; after product recalls or field safety notices
2. Do NOT use when: informal team reflection or sprint retrospectives (documentation overhead is disproportionate); Agile software teams without regulatory obligations (use Blameless Postmortem); when speed of resolution matters more than documentation completeness; minor issues resolvable through standard operating procedures; when the organization lacks infrastructure to track CAPAs through their full lifecycle
3. CAPAs that never close. This is the #1 organizational failure; overdue CAPAs are audit red flags. Fix: set deadlines and verification dates; track completion rates as a quality metric
4. Surface-level root cause. "Operator error" guarantees recurrence; auditors know this. Fix: push to "What about the process/design/training allowed the error?" CAPAs built on shallow root causes fail effectiveness verification
5. Corrective without preventive. Fixing this specific batch without preventing the class of failure means you'll write the same CAPA again. Fix: regulators specifically look for this distinction; always include systemic prevention
6. Preventive actions that are just training. "Retrain all operators" is the laziest preventive action. Fix: effective prevention is usually process redesign or automation that makes the error impossible, not just improbable
7. No effectiveness verification criteria defined upfront. This makes it hard to close the CAPA. Fix: define measurable criteria during planning before implementation begins
8. CAPA overload. Opening too many CAPAs without resources to close them creates a backlog regulators view as systemic quality failure. Fix: prioritize ruthlessly
</Gotchas>

<Instructions>
<Workflow - Corrective and Preventive Actions (CAPA)
  description="Facilitation guide for Corrective and Preventive Actions."
>
1. [Setup] (Before the initial investigation meeting)
   - Document the nonconformance/event/deviation in the quality management system
   - Assign a CAPA owner (typically quality engineer or process owner)
   - Assemble a cross-functional investigation team (quality, engineering, operations, subject matter experts)
   - Gather relevant documentation: batch records, test results, customer complaints, SOPs, training records
   - Determine CAPA classification: corrective only, preventive only, or both
   - Assess initial risk level (severity × probability × detectability)

2. [Open] (10 minutes)
   - Purpose: Frame as a systems investigation with compliance requirements, not a blame exercise
   - Prompt: "We are conducting a formal CAPA investigation. Our goal is to identify the root cause, implement effective corrections, and verify that our actions prevent recurrence. This is a systems investigation - we're looking at processes, procedures, equipment, training, and design. Everything we discuss will be documented and may be subject to regulatory review."
   - Facilitation tip: In regulated environments, CAPA documentation can be audited. Remind the team that precision and accuracy in documentation matter. However, maintain the blameless framing; CAPAs that blame individuals fail regulatory scrutiny because they don't demonstrate systemic improvement.

3. [Stage: Problem Description] (10 minutes)
   - Purpose: Document a precise, complete description of the nonconformance
   - Prompt: "What exactly happened? Describe the deviation from the expected outcome. Include: what product/process/service was affected, when it was discovered, who discovered it, what the expected outcome was, and what the actual outcome was."
   - Facilitation tip: Use factual, objective language. "Batch 4521 failed sterility testing" not "someone contaminated the batch." The problem statement will appear on regulatory documents; make it precise.

4. [Stage: Impact Assessment] (10 minutes)
   - Purpose: Quantify severity, scope, and risk to patients/customers/operations
   - Prompt: "What is the impact? How many units/batches/customers are affected? What is the risk to patient safety or product quality? Has this been reported to regulatory authorities? What immediate containment actions have been taken?"
   - Facilitation tip: Use your organization's risk matrix (severity × occurrence × detection). Document containment actions already taken (quarantine, recall, customer notification) separately from long-term corrective actions.

5. [Stage: Root Cause Investigation] (25–35 minutes)
   - Purpose: Identify the true root cause(s) using structured analysis tools
   - Prompt: "Why did this nonconformance occur? Let's use [Five Whys / Fishbone / Fault Tree] to trace from the event back to systemic root cause. Remember: 'human error' is not a root cause; it's the starting point for investigating what system conditions allowed the error."
   - Facilitation tip: Multiple root-cause analysis tools can be used: Five Whys for simple linear causation, Fishbone/Ishikawa for multi-factor analysis (Man, Machine, Method, Material, Measurement, Environment), or Fault Tree for complex technical failures. Document the analysis method used; auditors will evaluate it.

6. [Stage: Corrective Action Planning] (10 minutes)
   - Purpose: Define actions that fix the immediate problem and its direct effects
   - Prompt: "What specific actions will correct the current problem and its immediate effects? For each action: what exactly will be done, who will do it, by when, and how will we verify it was done correctly?"
   - Facilitation tip: Corrective actions are reactive; they address THIS specific nonconformance. They should be immediate and specific. Example: "Retrain operators on SOP-142 within 10 days" or "Repair calibration on equipment EQ-201 by [date]."

7. [Stage: Preventive Action Planning] (10 minutes)
   - Purpose: Define actions that prevent the same class of problem from recurring
   - Prompt: "What systemic changes will prevent this root cause from producing ANY nonconformance in the future? Think: process design, automation, error-proofing (poka-yoke), training programs, equipment upgrades, SOP revisions."
   - Facilitation tip: Preventive actions are proactive; they address the CLASS of failure, not just this instance. They often involve process redesign, automation, or systemic controls. Example: "Add automated parameter verification to batch recipe system, eliminating possibility of manual entry error."

8. [Synthesize] (5 minutes)
   - Purpose: Define verification method and effectiveness criteria
   - Prompt: "How will we verify that our corrective and preventive actions actually worked? What specific, measurable criteria will demonstrate effectiveness? When will we check?"
   - Facilitation tip: This is where most CAPAs fail. Define the effectiveness check upfront: "After 90 days, review for zero recurrences of this nonconformance type" or "Audit 50 batch records to confirm new control is functioning." Without verification, CAPAs are wishes.

9. [Close] (5 minutes)
   - Purpose: Assign ownership, confirm timelines, schedule verification
   - Prompt: "Let's confirm: CAPA owner is [Name]. Corrective actions due by [Date]. Preventive actions due by [Date]. Effectiveness verification on [Date]. Who needs to approve this CAPA plan?"
   - Facilitation tip: In regulated environments, CAPA plans typically require management review and approval before implementation. Schedule this. Also schedule the effectiveness verification date in calendars NOW; it's too easy to forget.
</Workflow - Corrective and Preventive Actions (CAPA)>
</Instructions>

<Templates>
```markdown
# CAPA Report: [CAPA-XXXX]

**CAPA Number:** [Tracking ID]
**Date Opened:** YYYY-MM-DD
**CAPA Owner:** [Name, Title]
**Classification:** Corrective / Preventive / Both
**Priority:** Critical / Major / Minor
**Source:** [Customer Complaint / Audit Finding / Deviation / Internal Investigation]

## 1. Problem Description
**Event/Nonconformance:** [Factual description]
**Date Discovered:** YYYY-MM-DD
**Discovered By:** [Name/Role]
**Product/Process Affected:** [Specific identification]

## 2. Impact Assessment
**Scope:** [Units/batches/customers affected]
**Severity:** [Risk level per matrix]
**Patient/Customer Safety Impact:** [Assessment]
**Regulatory Notification Required:** Yes / No
**Immediate Containment Actions Taken:**
- [Action 1 - date completed]
- [Action 2 - date completed]

## 3. Root Cause Investigation
**Method Used:** [Five Whys / Fishbone / Fault Tree / Other]

### Root Cause Analysis
[Detailed analysis documentation - attach diagrams if Fishbone/Fault Tree]

### Root Cause Statement
[Clear, systemic root cause - not "human error"]

### Contributing Factors
1. [Factor 1]
2. [Factor 2]

## 4. Corrective Actions
| # | Action | Owner | Due Date | Completion Date | Verification |
|---|--------|-------|----------|-----------------|--------------|
| CA-1 | [Specific action] | [Name] | [Date] | | [How verified] |
| CA-2 | [Specific action] | [Name] | [Date] | | [How verified] |

## 5. Preventive Actions
| # | Action | Owner | Due Date | Completion Date | Verification |
|---|--------|-------|----------|-----------------|--------------|
| PA-1 | [Systemic change] | [Name] | [Date] | | [How verified] |
| PA-2 | [Systemic change] | [Name] | [Date] | | [How verified] |

## 6. Effectiveness Verification
**Verification Method:** [Specific criteria and measurement]
**Verification Date:** YYYY-MM-DD
**Verified By:** [Name]
**Result:** [Effective / Not Effective - requires escalation]
**Evidence:** [Reference to data/records]

## 7. CAPA Closure
**Closure Date:** YYYY-MM-DD
**Approved By:** [Name, Title]
**Final Status:** Closed - Effective / Closed - Escalated / Open

## Revision History
| Date | Change | By |
|------|--------|-----|
| YYYY-MM-DD | CAPA opened | [Name] |
| YYYY-MM-DD | Investigation complete | [Name] |
| YYYY-MM-DD | Actions implemented | [Name] |
| YYYY-MM-DD | Effectiveness verified | [Name] |
```
</Templates>

<Resources>
- **Know your regulatory context.** FDA-regulated vs ISO-only vs internal-only CAPAs have different documentation requirements. Match rigor to regulatory obligation.
- **Separate the investigation meeting from the action-planning meeting** if the root cause isn't immediately clear. Better to take 3 days investigating than to plan actions against the wrong root cause.
- **Use multiple root-cause tools together.** Fishbone diagram to brainstorm potential causes, then Five Whys to drill into the most likely branch. Document both.
- **Link CAPAs to training records, SOP revisions, and design changes.** Auditors trace these connections. If your CAPA says "revise SOP-142" but there's no revised SOP-142, the CAPA isn't closed.
- **Maintain a CAPA trending report.** If the same root cause category appears repeatedly across CAPAs, you have a systemic issue that individual CAPAs aren't solving. Escalate to management review.
- **For effectiveness verification**, define both the criteria AND the timeline. A common approach: "Zero recurrences of this nonconformance type within 90 days of implementation, verified by [specific audit or data review]."
- **In the meeting, keep language precise and documented.** CAPA records are legal documents in regulated industries. Everything discussed should be captured accurately. Assign a scribe separate from the facilitator.
</Resources>
