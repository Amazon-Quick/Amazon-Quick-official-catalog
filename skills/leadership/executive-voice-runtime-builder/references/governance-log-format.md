# Governance Log Format Reference

## Entry Template

Each entry in the Governance Log file (`[FirstName]_Governance_Log.md` in the user's chosen output directory) follows this template:

```markdown
### [ISO-8601 timestamp] - [EVENT_TYPE]

**Decision:** [What was decided]
**Evidence:** [What supported the decision]
**Actor:** [user | agent]
**Gate:** [Which gate this relates to, if any]
**Outcome:** [PASS | FAIL | SKIP | N/A]
**Notes:** [Additional context]

---
```

## Valid EVENT_TYPEs

| Event Type | When to Use |
|---|---|
| `SESSION_START` | Beginning of any workflow run |
| `SOURCE_DISCOVERED` | A writing source was found and available |
| `SOURCE_EXCLUDED` | A sample failed the Authorship Confidence Gate |
| `SOURCE_INCLUDED` | A sample passed and was added to the analysis set |
| `CONTAMINATION_CHECK` | AI contamination assessment completed |
| `CALIBRATION_ATTEMPT` | A calibration draft was presented to user |
| `CALIBRATION_PASS` | The calibration gate threshold was met |
| `CALIBRATION_FAIL` | The calibration gate threshold was NOT met |
| `ENGRAM_SAVED` | The engram file was written |
| `ENGRAM_VERIFIED` | Reading the engram file back confirmed persistence |
| `ENGRAM_SAVE_FAILED` | The engram file could not be confirmed after writing |
| `STATUS_UPGRADE` | Engram promoted (e.g. DRAFT to PRODUCTION) |
| `STATUS_DOWNGRADE` | Engram demoted |
| `USER_OVERRIDE` | User explicitly overrode a default decision |
| `TOOL_FAILURE` | A source lookup or file operation failed (error, timeout) |
| `GATE_HALT` | A required gate was not met, workflow halted |

## Example Entries

```markdown
### 2026-07-17T14:30:00Z - SESSION_START

**Decision:** Initialize Fast Track build for Elizabeth MacMaster
**Evidence:** 22 sent emails discovered, messaging connected, role: IC - Sales
**Actor:** agent
**Gate:** Entry Gate (Step 0)
**Outcome:** PASS
**Notes:** Sources: email (22), messaging (available), indexed folders (3). Governance weight: Light.

---

### 2026-07-17T14:31:15Z - CONTAMINATION_CHECK

**Decision:** Proceed without Native Voice Calibration Prompts
**Evidence:** 4/22 samples (18%) scored H2 or lower, below 40% threshold
**Actor:** agent
**Gate:** AI Contamination Gate
**Outcome:** PASS
**Notes:** 18 samples scored H4-H5, 4 scored H2-H3. Acceptable distribution.

---

### 2026-07-17T14:45:00Z - TOOL_FAILURE

**Decision:** Continue without messaging source
**Evidence:** Messaging search returned a timeout after 30s
**Actor:** agent
**Gate:** N/A
**Outcome:** SKIP
**Notes:** Proceeding with email sources only. Messaging unavailable this session.

---

### 2026-07-17T15:10:00Z - CALIBRATION_PASS

**Decision:** Upgrade engram from DRAFT to PRODUCTION
**Evidence:** User approved 3/3 test drafts (email: APPROVE, escalation: APPROVE, quick reply: APPROVE)
**Actor:** user
**Gate:** Fast Track Calibration (2/3 required)
**Outcome:** PASS
**Notes:** All three drafts accepted without revision. Strong signal.

---
```
