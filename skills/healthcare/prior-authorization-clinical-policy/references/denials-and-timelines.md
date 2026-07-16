# Denial Codes, Turnaround Times, and PA Reform

Reference data for denial reason categories, turnaround requirements, quantity limits,
site-of-care logic, and regulatory milestones. Apply internally; present the conclusion
with the specific code or threshold that supports it.

## Denial Reason Categories

| Category | CARC Code Range | Example | Recommended Action |
|----------|-----------------|---------|--------------------|
| Medical necessity not met | 50, 56 | Diagnosis does not support service | Appeal with clinical evidence |
| Step therapy not completed | 149 | Required prior drug not tried | Document prior treatments |
| Not a covered benefit | 96, 97 | Service excluded from plan | Formulary exception or plan change |
| Documentation insufficient | 16, 252 | Missing clinical notes | Resubmit with complete records |
| Experimental/investigational | 56 | Off-label use not approved | Cite peer-reviewed evidence |
| Out of network | 151 | Provider not in network | Network exception or referral |
| Duplicate authorization | 18 | PA already exists for service | Verify existing PA status |

## PA Turnaround Time Requirements

| Request Type | Commercial (typical) | Medicare Part C | Medicare Part D |
|--------------|----------------------|-----------------|-----------------|
| Standard (non-urgent) | 15 calendar days | 14 calendar days | 72 hours (standard) |
| Expedited (urgent) | 72 hours | 72 hours | 24 hours |
| Retrospective | 30 calendar days | 30 calendar days | N/A |
| Extension (pend for info) | plus 14 days (one extension) | plus 14 days | plus 14 days |

### Urgency Determination Rules

A request qualifies as expedited when:

1. Applying the standard timeframe could seriously jeopardize the patient's life or health.
2. Applying the standard timeframe could jeopardize the patient's ability to regain maximum function.
3. A physician indicates the request is urgent (physician attestation).
4. The patient is currently undergoing treatment that would be interrupted.

## Quantity Limits

| Limit Type | Description | Example |
|------------|-------------|---------|
| Per-fill limit | Maximum units per prescription fill | 30-day supply for controlled substances |
| Per-period limit | Maximum units over a time period | 9 fills per year for triptan medications |
| Lifetime limit | Maximum total units ever | Gene therapy, single administration |
| Diagnosis-based limit | Quantity varies by condition | Higher opioid limits for cancer pain |

## Site-of-Care Optimization

Payers increasingly require lower-cost sites for infusion and injection therapies:

```
Is the drug available for home infusion?
- YES -> Home infusion preferred (lowest cost).
  - Patient clinically stable?     -> Approve home infusion.
  - Patient requires monitoring?   -> Approve outpatient infusion center.
- NO  -> Is an outpatient infusion center available?
  - YES -> Outpatient preferred over hospital outpatient.
  - NO  -> Hospital outpatient department approved.
```

## Regulatory Timeline: Key PA Reform Dates

| Date | Regulation | Impact |
|------|-----------|--------|
| Jan 2024 | CMS Interoperability Rule (CMS-0057-F) finalized | Payers must implement FHIR PAS API |
| Jan 2026 | FHIR PAS API mandate effective | Payers must accept electronic PA via Da Vinci PAS |
| Jan 2026 | PA decision transparency | Payers must provide specific denial reasons and applicable criteria |

### Gold Carding Programs

Several states require payers to exempt providers from PA if they demonstrate at least a
90% approval rate for a specific service over 12 months. Exemption lasts 12 months,
is subject to audit, and is revoked if the approval rate drops below the threshold.
