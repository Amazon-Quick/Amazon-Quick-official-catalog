---
description: "The starter seven-element justification template (WHAT, HOW, WHY, WHO, WHERE, CADENCE, BUDGET) with guidance per element. Read on a first run with no template in the profile and when judging justifications."
last_updated: 2026-11-24
---
# Justification template: starter (WHAT, HOW, WHY, WHO, WHERE, CADENCE, BUDGET)

A starter 7-element template for purchase justifications. Use this as a starting point.
To adopt it, save `justification_template=WHAT,HOW,WHY,WHO,WHERE,CADENCE,BUDGET` in
the finance profile; the reviewer will check that each keyword appears in the text and
the model will judge each element as Present, Weak, or Missing.

This file is ERP-neutral and system-neutral. Organizations may rename or extend elements.

---

| Element | What to address |
|---|---|
| WHAT | What is being bought: item name, service description, and quantity. Be specific: not "supplies" but "24-port network switch, qty 2". |
| HOW | How it will be used or delivered: the work it enables, the process it supports, or the delivery method. |
| WHY | Business need and why now: the problem this solves, the risk of not buying, and why this moment is the right time. |
| WHO | Who is involved: requester name and role, the beneficiary team or end-user group, and the accountable owner. |
| WHERE | Site, location, or system where the item will be deployed or used. For digital services, the system or environment. |
| CADENCE | Whether this is a one-off or recurring purchase, expected frequency, and whether repeat orders are anticipated. |
| BUDGET | Which budget line, cost center, or project funds this, and whether the spend was planned in the current budget cycle. |

## Example using this template (fictional people and figures)

> WHAT: 2 x 24-port managed network switches, model AnyCompany SW-24.
> HOW: Replace end-of-life switches in server rack A, restoring redundant uplinks to 10 GbE.
> WHY: Current switches are out of vendor support as of Jan-2027; failure would take the lab offline.
> WHO: Carlos Salazar (requester, IT Ops), Lab Engineering team (users), Martha Rivera (IT manager, owner).
> WHERE: Building B, server room 2, rack A.
> CADENCE: One-off replacement; no recurring cost unless a unit fails.
> BUDGET: IT Infrastructure opex, cost center 4420, planned in the annual budget; $4,200 of $6,000 annual allowance remains.

---

## First-run offer (model uses this text)

When no `justification_template` is set in the finance profile, the model offers:

> "Does your team use a required justification template? A starter one is WHAT, HOW, WHY,
> WHO, WHERE, CADENCE, BUDGET (see `references/justification-template.md` for guidance on
> each element). Use that, paste yours, or skip. I'll save your choice so you don't get
> asked again."

The template is saved to the profile only after the user confirms it. Until then, the
model judges the justification against the seven elements above and writes the line
"Generic check: no justification template on file, so the seven standard elements were used."
(references/output.md, section 3).
