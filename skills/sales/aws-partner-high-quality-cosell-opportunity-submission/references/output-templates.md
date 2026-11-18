---
description: "Output formats for the full opportunity draft and the follow-up questions."
last_updated: 2026-11-16
origin: original
---

# Output templates

## Full draft output

Return the full draft first, then the questions, in this format:

```
CUSTOMER BUSINESS PROBLEM ([n] / 2,000 characters)
[drafted text with short labels]

NEXT STEPS ([n] / 255 characters)
MM/DD/YY: [customer meeting and outcome]. Owner: [name]. Customer: [name, title]. MM/DD/YY: [action]. Owner: [name]. Customer: [name, title].

PARTNER PRIMARY NEED FROM AWS
[value from the Partner Primary Need values table] | Why: [one sentence]

SOLUTION AND AWS PRODUCTS
Solution: [registered solution or AWS Marketplace product, Limited or Public status] | AWS Products: [AWS services the customer will adopt]

CUSTOMER DETAILS
Company name: [ ] | Website: https://[ ] | Industry: [ ]
Address: [street], [city], [state or region], [postal code], [country code]
National security: [Yes/No, Government only]
Customer contacts (required): [champion: name, business title, email, phone] | [approver: name, business title, email, phone]

PROJECT DETAILS
Title: [ ] ([n] / 255 characters)
Use case: [exact picklist value] | Delivery model: [ ] | Opportunity type: [ ]
Target stage: [ ] (opportunity is created at Prospect; set after AWS approval) | Target close date: [YYYY-MM-DD]
Sales activities: [ ]
Expected AWS monthly revenue: [amount, currency] | Pricing Calculator link: [ ] (or TCV: [amount, currency], duration: [months])
Marketing development funds: [Yes/No, only if sourced from AWS marketing]

RECOMMENDED FIELDS
Customer AWS account ID: [ ]
Partner contacts: [name, title] (OpportunityTeam; up to two in the console, up to ten via API or MCP)
Competitor name: [ ]

CHANGES MADE FOR YOU
- [what was removed, moved, shortened, or corrected, and why]

OPTIONAL IMPROVEMENTS
- [element that would strengthen the submission, such as contracting path or milestone dates]

QUESTIONS BEFORE SUBMITTING (up to five, most important first)
1. [question for the partner]

CONFIRM DELIVERY MODEL
Suggested: [value]. Pick one or more: SaaS or PaaS | BYOL or AMI | Managed Services | Professional Services | Resell | Other
```

## Review findings output

When reviewing an existing submission, return `REVIEW FINDINGS`: one line per failed check, in the form `Field: problem | Fix: change or question`.

## Score diagnosis output

When the partner asks why an opportunity scored low, return `SCORE DIAGNOSIS`: a table with one row per element in references/scoring.md, columns `Component | Element | Status (Present / Weak / Missing) | Edit that raises it`, with Weak and Missing rows first. Do not state or estimate a numeric score; only AWS Partner Central shows it, after approval. If the partner recently shortened or reworded a scored field, name that as a likely cause (Do not 10 in references/best-practices.md) and ask what the field said before the edit. Offer to redraft the Weak and Missing fields.
