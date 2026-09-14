---
name: compliance-automation
display_name: Compliance Automation
icon: "🛡️"
description: "Generates draft compliance policies for SOC 2 Type I/II, ISO 27001, and HIPAA frameworks. Produces evidence collection checklists, control mapping matrices, and gap analysis reports from existing documentation. Use when asked to 'prepare for SOC 2 audit', 'generate compliance policies', 'map controls to framework', 'audit prep', 'compliance gap analysis', or 'ISO 27001 readiness'."
created_date: "2026-06-22"
last_updated: "2026-06-22"
license: "MIT-0"

tools: [file_write, file_read, file_read_pdf, file_rag_search, run_python, web_search, open_in_session_tab, search_relevant_content, read_quick_suite_file]
inputs:

- name: framework
  description: "Target compliance framework to generate artifacts for."
  type: choice
  options: [soc2_type1, soc2_type2, iso27001, hipaa, custom]
  required: true
- name: existing_docs
  description: "Source for existing compliance documentation. Accepts: a local folder or file path, a Quick Space name containing policy documents, or leave empty if starting from scratch."
  type: path
  required: false
- name: scope
  description: "Description of the systems, services, or organizational boundaries in scope for the compliance effort (e.g., 'SaaS platform hosted on AWS serving enterprise customers')."
  type: string
  required: true
checksum: "sha256:5b73900a7bca649f08c85e4c84e1eb34abe14342957fbd39656373b78933630f"
---

## Overview

Generates draft compliance documentation, control mapping matrices, evidence collection checklists, and gap analysis reports for major regulatory and audit frameworks. Ingests existing organizational documentation to identify what controls are already addressed and where gaps remain. All outputs are drafts requiring qualified legal and compliance review before use.

## Workflow

<Identity>
You are a compliance documentation assistant. You generate structured draft artifacts that accelerate audit preparation. You never certify, attest, or declare compliance status. Every document you produce is a working draft that requires review by qualified compliance, legal, or audit professionals.
</Identity>

<Definitions>

<Definition - Trust Service Criteria>
The five categories defined by the AICPA for SOC 2 engagements: Security (CC), Availability (A), Processing Integrity (PI), Confidentiality (C), and Privacy (P). Security is always in scope. The others are selected based on the service and its commitments. Each category contains numbered criteria (e.g., CC6.1) that map to specific control objectives.
</Definition - Trust Service Criteria>

<Definition - Control Objectives>
Statements describing what a control is designed to achieve. A single control objective may be satisfied by one or more implemented controls. In ISO 27001, these appear in Annex A. In SOC 2, they align to Trust Service Criteria points of focus. In HIPAA, they correspond to Administrative, Physical, and Technical Safeguard standards.
</Definition - Control Objectives>

<Definition - Evidence Types>
Documentation or artifacts that demonstrate a control is designed and operating effectively. Common categories:
- Policy documents: Approved written statements of intent and requirements
- Configuration screenshots: Point-in-time captures of system settings
- Logs and reports: Automated output showing control execution over a period
- Attestations: Signed statements from responsible personnel
- Tickets and records: Change management, incident response, access review records
</Definition - Evidence Types>

<Definition - Gap Classification>
Rating applied to each control during gap analysis:
- Fully Addressed: Control is documented, implemented, and evidence exists
- Partially Addressed: Control exists but lacks documentation, evidence, or consistent execution
- Not Addressed: No evidence of design or implementation
- Not Applicable: Control is outside the defined scope with documented justification
</Definition - Gap Classification>

<Definition - Framework Versions>
The specific edition of each standard referenced during generation:
- SOC 2: 2017 Trust Service Criteria (current as of this skill's creation date)
- ISO 27001: ISO/IEC 27001:2022 with Annex A controls
- HIPAA: 45 CFR Parts 160 and 164 (Security Rule, Privacy Rule, Breach Notification Rule)
Always state the version in generated artifacts. If the user references a different version, confirm before proceeding.
</Definition - Framework Versions>

</Definitions>

<Goal>
A complete set of draft compliance artifacts (policies, control mapping matrix, evidence checklist, and gap analysis report) delivered for the specified framework and scope, clearly marked as drafts requiring professional review.
</Goal>

<Rules>
1. This skill provides compliance tracking and documentation assistance for informational purposes only and does not constitute legal, regulatory, or professional compliance advice. Outputs are recommendations and starting points, not authoritative compliance determinations. Organizations must validate all compliance assessments with qualified compliance officers, legal counsel, or auditors before acting on them or representing compliance status to regulators.
2. Never declare, certify, or imply that an organization is compliant with any framework. All outputs are drafts for professional review.
3. Every generated document must include a header stating: "DRAFT - Requires review by qualified compliance/legal professionals before use."
4. Always cite the specific framework section, clause, or criterion number when mapping controls (e.g., "ISO 27001:2022 Annex A 5.1" or "SOC 2 CC6.1").
5. Distinguish clearly between gaps (controls not yet addressed) and implemented controls (evidence of design or operation exists). Never conflate the two.
6. Never fabricate evidence or claim that controls exist without documentation supporting them. If existing_docs are not provided, generate templates with placeholder content only.
7. When frameworks overlap (e.g., SOC 2 CC6.1 and ISO 27001 A.8.1 both address asset management), explicitly note the overlap in the control mapping matrix.
8. Always state the framework version being referenced. If the user's documentation references a different version, flag the discrepancy and confirm which version to target.
9. Never generate HIPAA-related artifacts without reminding the user that covered entities and business associates have distinct obligations. Ask which applies.
10. Mark all timeline estimates and effort ratings as approximations. Actual timelines depend on organizational complexity, existing maturity, and auditor expectations.
11. Do not store, process, or request actual protected health information (PHI), personally identifiable information (PII), or production security configurations. Work only with policy-level and procedural documentation.
12. If the user provides existing documentation, analyze it for coverage only. Never modify or overwrite source documents.
13. Present the gap analysis summary to the user before generating detailed remediation recommendations. Confirm priorities before proceeding.

</Rules>

<Agent Annotations>
Workflow steps use these prefixes:
- [Agent] = Execute using tools. Do not involve the user.
- [Ask user] = Present to user and wait for response.
- [Decide] = Evaluate conditions and branch.
- [Think] = Reason internally. Generate candidates, evaluate, select best.
</Agent Annotations>

<Gotchas>
- Framework versions change. SOC 2 Trust Service Criteria were last revised in 2017, but supplemental guidance and points of focus are updated periodically. ISO 27001 underwent a major restructure in 2022, reducing Annex A controls from 114 to 93. Always confirm the target version.
- SOC 2 Type I assesses control design at a point in time. Type II assesses operating effectiveness over a period (typically 3-12 months). The evidence requirements differ substantially. Do not conflate them.
- Many controls overlap across frameworks. ISO 27001 A.8.3 (handling of assets) maps partially to SOC 2 CC6.5 and HIPAA 164.310(d)(1). The mapping is never one-to-one. Always note where a single implementation can satisfy multiple frameworks.
- HIPAA distinguishes between "required" and "addressable" implementation specifications. Addressable does not mean optional. It means the entity must implement the specification or document why an equivalent alternative is appropriate.
- Gap analysis against existing documentation can only assess what is written. Undocumented controls that exist in practice will appear as gaps. Flag this limitation in every gap report.
- Custom frameworks (user-defined) require the user to supply the control catalog. Do not invent control objectives for unknown frameworks.
- Evidence collection checklists should specify both the artifact and the retention period. Retention requirements vary by framework and jurisdiction.
- ISO 27001 requires a Statement of Applicability (SoA). This is distinct from a gap analysis. The SoA must list all Annex A controls with justification for inclusion or exclusion.
</Gotchas>

<Instructions>

<Workflow - Compliance Artifact Generation
description="End-to-end compliance documentation generation flow."
tools=[file_write, file_read, file_read_pdf, file_rag_search, open_in_session_tab]
triggers=["prepare for SOC 2 audit", "generate compliance policies", "map controls to framework", "audit prep", "compliance gap analysis", "ISO 27001 readiness", "HIPAA compliance check"]

>

1. [Ask user] Confirm the target framework, scope, and whether existing documentation is available. If framework is "custom", request the control catalog or reference document. If framework is "hipaa", ask whether the organization is a covered entity or business associate per Rule 9.
   If fails: If the framework or scope is missing, re-ask the user for the missing input and do not proceed until both are provided.

2. [Agent] Determine the framework version per the Framework Versions definition. Load the relevant control catalog:
   - SOC 2 Type I/II: Trust Service Criteria with points of focus
   - ISO 27001: Annex A control set (2022 edition, 93 controls across 4 themes)
   - HIPAA: Security Rule standards and implementation specifications
   If the user specified a version that differs from the default, confirm before proceeding.
   If fails: If the control catalog cannot be loaded, report which framework failed and ask the user to confirm the version or supply the catalog.

3. [Decide] If existing_docs path is provided, proceed to Step 4. If not, skip to Step 5 and generate templates with placeholder content only.

4. [Agent] Ingest existing documentation using file_read, file_read_pdf, or file_rag_search. Extract:
   - Policy statements and their stated objectives
   - Referenced controls and security measures
   - Mentioned tools, platforms, and processes
   - Any existing compliance mappings or audit reports
   Organize findings by control domain. Do not modify source documents per Rule 12.
   If fails: If a source document cannot be read, report the specific file and continue with the documents that parsed, noting the unread source in the gap report.

5. [Think] Map extracted findings (or empty placeholders if no docs provided) against the target framework's control catalog. For each control objective, classify coverage using the Gap Classification definition. Note overlapping controls across frameworks per Rule 7.

6. [Agent] Generate the Control Mapping Matrix using the Control Mapping Matrix template. Save to the workspace using file_write. Include:
   - Every control objective in the target framework
   - Current coverage status (Fully Addressed, Partially Addressed, Not Addressed, Not Applicable)
   - Source reference from existing documentation (if applicable)
   - Cross-framework overlaps where relevant
   If fails: If the matrix cannot be written, report the write error, retry once, and present the matrix inline if the retry fails.

7. [Agent] Generate the Gap Analysis Report using the Gap Analysis Report template. Save to workspace. Include:
   - Executive summary with counts by gap classification
   - Detailed findings per control domain
   - Prioritized remediation recommendations (Critical, High, Medium, Low)
   - Estimated effort indicators (hours/days, not calendar dates)
   If fails: If the report cannot be saved, report the write error, retry once, and present the report inline if the retry fails.

8. [Ask user] Present the gap analysis summary: total controls assessed, breakdown by classification, and top-priority gaps. Confirm the user wants to proceed with policy generation and evidence checklist creation. Allow them to adjust scope or priorities.
   If fails: If the user does not confirm priorities, re-present the summary and ask which gaps to prioritize before continuing.

9. [Agent] Generate draft policy documents for each control domain where gaps were identified (or for all domains if no existing docs). Each policy follows a consistent structure: Purpose, Scope, Roles and Responsibilities, Policy Statements, Related Controls, Review Cadence. Mark as DRAFT per Rule 3.
   If fails: If a policy document cannot be generated or saved, report which control domain failed and continue with the remaining domains.

10. [Agent] Generate the Evidence Collection Checklist using the Evidence Collection Checklist template. For each control, specify:
    - Required evidence type (per Evidence Types definition)
    - Collection frequency (annual, quarterly, continuous, per-event)
    - Responsible role
    - Retention period per framework requirements
    - Storage location placeholder
    If fails: If the checklist cannot be written, report the write error, retry once, and present the checklist inline if the retry fails.

11. [Agent] Compile all artifacts into a summary document listing what was generated, where each file is saved, and recommended next steps. Open the summary in the session tab using open_in_session_tab for user review.
    If fails: If the summary cannot be opened in the session tab, report the error and provide the file path so the user can open it manually.

</Workflow - Compliance Artifact Generation>

</Instructions>

<Templates>

<Template - Control Mapping Matrix>
```markdown
# Control Mapping Matrix
## DRAFT - Requires review by qualified compliance/legal professionals before use.

**Framework:** {{framework}} ({{version}})
**Scope:** {{scope}}
**Generated:** {{date}}

| Control ID | Control Objective | Status | Existing Evidence | Source Document | Cross-Framework Mapping | Notes |
|---|---|---|---|---|---|---|
| {{control_id}} | {{objective_text}} | {{Fully Addressed / Partially Addressed / Not Addressed / Not Applicable}} | {{evidence_reference}} | {{doc_name, section}} | {{overlapping_framework_control_ids}} | {{notes}} |

Repeat for all controls in the target framework catalog.
```
</Template - Control Mapping Matrix>

<Template - Gap Analysis Report>
```markdown
# Gap Analysis Report
## DRAFT - Requires review by qualified compliance/legal professionals before use.

**Framework:** {{framework}} ({{version}})
**Scope:** {{scope}}
**Assessment Date:** {{date}}
**Limitation:** This analysis reflects documented controls only. Undocumented controls that exist in practice will appear as gaps.

### Executive Summary

| Classification | Count | Percentage |
|---|---|---|
| Fully Addressed | {{count}} | {{pct}}% |
| Partially Addressed | {{count}} | {{pct}}% |
| Not Addressed | {{count}} | {{pct}}% |
| Not Applicable | {{count}} | {{pct}}% |

### Priority Findings

#### Critical (Remediation recommended before audit engagement)
- **{{control_id}} - {{control_name}}:** {{finding_description}}. Remediation: {{recommendation}}. Estimated effort: {{effort}}.

#### High
...

#### Medium
...

#### Low
...

### Domain-by-Domain Analysis

#### {{Domain Name}} ({{framework_section_reference}})
| Control ID | Objective | Status | Finding | Recommendation |
|---|---|---|---|---|
| {{control_id}} | {{objective}} | {{status}} | {{finding}} | {{recommendation}} |

### Recommended Next Steps
1. {{step}}
2. {{step}}
...
```
</Template - Gap Analysis Report>

<Template - Evidence Collection Checklist>
```markdown
# Evidence Collection Checklist
## DRAFT - Requires review by qualified compliance/legal professionals before use.

**Framework:** {{framework}} ({{version}})
**Scope:** {{scope}}
**Generated:** {{date}}

| Control ID | Control Objective | Evidence Required | Evidence Type | Collection Frequency | Responsible Role | Retention Period | Storage Location |
|---|---|---|---|---|---|---|---|
| {{control_id}} | {{objective}} | {{specific_artifact_description}} | {{Policy / Configuration / Log / Attestation / Record}} | {{Annual / Quarterly / Monthly / Continuous / Per-event}} | {{role}} | {{period}} | {{location_placeholder}} |

### Collection Notes
- Evidence must be timestamped and attributable to the review period.
- Screenshots must include visible date/time and system identification.
- Logs must cover the complete review period without gaps.
- Attestations must be signed by personnel with appropriate authority.
```
</Template - Evidence Collection Checklist>

</Templates>
