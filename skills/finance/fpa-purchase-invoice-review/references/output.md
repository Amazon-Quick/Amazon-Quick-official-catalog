---
description: "The exact four-section report template, status words, column rules, and a worked example. Read before writing the first report in a conversation."
last_updated: 2026-11-24
---
# Output format: purchase and invoice review (strict)

Every response is a professional review report with exactly these four sections, with these headings, in this order:

1. Verdict
2. Summary (with the findings in detail under it)
3. 7 Justifications Summary
4. 3-Way Match Summary

Don't add, rename, merge, or reorder sections. Nothing goes before section 1 or after section 4: no title banner, greeting, preamble, "Prepared by", skill version, or sign-off. If a section has nothing to report, keep its heading and write one line saying why. A column that doesn't apply to a batch (for example Quotes when the price check didn't run) may be dropped from a table, but the section stays.

## Style rules

- **No emoji, icons, or symbols** anywhere in the report: no check marks, crosses, warning signs, traffic lights, arrows, or decorative bullets. Use the text status words below.
- No em dashes. Separate fields with a vertical bar ( | ), a comma, or a colon.
- Neutral, factual wording. Write "item to confirm", "possible duplicate", "possible split". Never "fraud", "overbilled", "suspicious" or any word that states intent.
- Amounts are X,XXX.XX with two decimals, written with the profile currency's symbol or code (`$4,800.00`, `EUR 4,800.00`), and the currency is stated once in Review context. The engine's sentences use `$`; when the currency isn't USD, replace the `$` with the currency code when you copy them. Percentages to one decimal place.
- Dates are YYYY-MM-DD.
- Every number in the report comes from the script output or from the documents, or is labeled MODEL-COMPUTED. The script's sentences (`bottom_line`, `totals_line`) and status cells (`match_rows`) are already in report form: copy them as they are.
- Cite sources the way the reader knows them: the document and the row ID ("Invoices table, row 4502"; "PO lines table, PO-7720 line 2"; "the message, PO paragraph"). Don't show the script's internal references such as `pir_input.txt(parsed):6`.

## Status words

| Word | Meaning | Use in |
|---|---|---|
| Pass | Checked and no issue | Check cells |
| Confirm | Checked; needs a named confirmation before it can pass | Check cells |
| Fail | Checked and breaks a rule | Check cells |
| Not checked | The check didn't run; the reason is under "Not checked" | Check cells |
| n/a | The check doesn't apply to this item type | Check cells |
| Present / Weak / Missing | One justification element | Section 3 only |
| Hold / Send back / Approve with conditions / Ready to approve | The item's recommendation | Verdict column and finding headers |

A short reason may follow a status in parentheses, for example `Fail (over ceiling)` or `Confirm (1 of 2 quotes)`.

A check cell shows Fail or Confirm when the item has a finding from that check; with two findings, give both reasons separated by a semicolon, worst first: `Fail (billed more than received; possible duplicate)`. An out-of-period invoice line (INV-7) with no other issue shows `Confirm (out of period)` in Match. It shows Pass only when every rule of that check ran for the item. When some rules ran and others didn't, write `Pass (partial: <rules not run>)`, for example `Pass (partial: APR-1 not run)`. When none ran, write `Not checked (<reason>)`.

---

## Template

```
## 1. Verdict
<bottom-line sentence, verbatim from the script>

- Hold (N): **$X,XXX.XX**
- Send back (N): **$X,XXX.XX**
- Approve with conditions (N): **$X,XXX.XX**
- Ready to approve (N): **$X,XXX.XX**

## 2. Summary
**Totals:** <totals_line from the script, without its leading "Totals: ">

### Items reviewed
| Item | Supplier | Amount | Verdict | CC / Project | Category / Account | Justification | Quotes | Budget | Coding | Approval | Match |
|---|---|---|---|---|---|---|---|---|---|---|---|

### Review context
| Field | Value |
|---|---|
| Review date | YYYY-MM-DD |
| Checks run | Coding, Budget, Approval, Invoice ... |
| Status | N pending / N approved / N closed |
| Budget line | ... |
| Cost center | ... |
| Currency | ... |
| Payment terms | ... |

### Findings in detail
**<Item> | <Supplier> | $X,XXX.XX | <Verdict>**
- <RULE ID> <rule name>: <what was found> | <the number> | <source document, row, or field> | $X,XXX.XX at stake
- Condition: <only for Approve with conditions: the exact condition that clears it>

### Questions for the requester
1. <Item>: <one copy-paste-ready question>

### To finish this review
- <input needed> (<check it unlocks>)

### Not checked
- <check>: <reason>

### Basis of review
- Profile: <saved profile name, or "none on file, defaults labeled ASSUMPTION">
- Inputs: <file or "pasted message">, <rows>, sha256 <first 12 characters>
- Parameters: <value and where it came from; ASSUMPTION where not provided>
- Arithmetic: <group subtotals sum to the total: yes / no>
- Excluded rows: <by ID and reason, or "none">
- Method: script-computed (re-run if any input changes)

## 3. 7 Justifications Summary
| Item | WHAT | HOW | WHY | WHO | WHERE | CADENCE | BUDGET | Score | Read from |
|---|---|---|---|---|---|---|---|---|---|

## 4. 3-Way Match Summary
| Invoice | PO line | Ordered qty | Received qty | Invoiced qty | PO price | Invoice price | Qty match | Price match | Duplicate check | Result |
|---|---|---|---|---|---|---|---|---|---|---|

PO burn: <PO> value $X,XXX.XX | billed $X,XXX.XX | remaining $X,XXX.XX | N.N% used
```

---

## Section rules

### 1. Verdict
- The first line is the script's `bottom_line`, verbatim. When some checks didn't run it ends with `Not run, so not covered by "ready to approve": <checks> (see not_run).` Keep that sentence.
- Then one bullet per non-empty verdict group, worst first (Hold, Send back, Approve with conditions, Ready to approve), with the count and the bold $ subtotal from `groups[]` (`display`, `count`, `amount`). Skip empty groups.
- If you changed a verdict in judgment (step 11 of the skill: stricter with a reason, or softer only on evidence such as justification text that clears a literal JUS-2 finding), the group counts change: show the recomputed bullets, say so in one sentence after them ("REQ-310 moved from Ready to approve to Send back on review of the justification; subtotals are MODEL-COMPUTED."), and keep the script's sentence above them. The Totals line then carries the same note.
- For a single item, the single-item line replaces the bottom-line sentence and the group bullets: `<Supplier> <item type> <ID> ($X,XXX.XX): <Verdict>.` followed by the one reason that decides it, in one sentence. A verdict you changed is stated in the next sentence with its reason. When the script's `bottom_line` ends with `Not run, so not covered by "ready to approve": ...`, keep that clause after the single-item line.

### 2. Summary
- **Totals** come from `totals_line`, on one line. `check_sum_ok` must be `true`; if it isn't, label the totals MODEL-COMPUTED and show the difference.
- **Items reviewed**: one row per item, every item including Ready ones, sorted Hold, Send back, Approve with conditions, then Ready to approve, and by amount (largest first) within each group.

  | Column | When included | Cell values |
  |---|---|---|
  | Item, Supplier, Amount, Verdict | Always | text, $X,XXX.XX, verdict word |
  | CC / Project, Category / Account | Always | text, or "Not provided" |
  | Justification | Always | `n/7` from section 3 (the generic seven elements when no template is on file), or `Missing` when the text is blank |
  | Quotes | Price check ran | Pass / Confirm / Fail / Not checked |
  | Budget | Budget check ran | Pass / Confirm / Fail / Not checked |
  | Coding | Coding check ran | Pass / Confirm / Fail / Not checked |
  | Approval | Requisitions and POs | Pass / Confirm / Fail / Not checked (APR-1 and APR-3 need approval tiers) |
  | Contract | Contract in scope | Pass / Confirm / Fail / Not checked |
  | Match | Batch has invoices | Pass / Confirm / Fail / Not checked, or n/a for requisitions and POs (detail in section 4) |

- **Review context**: omit rows with no data, and add the missing field under "To finish this review" only if a check needs it.
- **Findings in detail**: one block per item that isn't Ready to approve, in the same order as the table. A finding on a document that isn't itself an item in this review (for example CON-1 on the PO an invoice bills) goes in the block of the item it affects, marked `(on PO 88120)`; decide in step 11 whether it changes that item's verdict. Every finding line carries the rule ID, what was found, the number, the source and the $ at stake. Judgment findings (step 11) use the rule ID `REVIEW` and quote the text they rest on. If every item is Ready to approve, write "No findings: every item is ready to approve." Ready items with an informational note (for example a check that didn't run) don't get a block; the note goes under "Not checked".
- **Questions for the requester**: numbered, one question per line, each starting with the item ID, written so the reviewer can paste it into an email unchanged. No questions: "None."
- **To finish this review**: one line per `not_run` entry and per missing input, naming the check it unlocks. Nothing missing: "None."
- **Not checked**: every check that didn't run and why, including `ignored_tables` and unreadable periods. Nothing skipped: "None."
- **Basis of review**: always present, in the order shown. Inputs give the first 12 characters of the input's `sha256` from the script's `inputs` (one value per pasted message). List every value you transcribed from prose as model-extracted, and every earlier message reused.

### 3. 7 Justifications Summary
- One row per item, every item including Ready ones, in the same order as the Items reviewed table.
- Each element cell is `Present`, `Weak (<a few words>)` or `Missing (<a few words>)`, for example `Missing (no cost center)` or `Weak (says "ongoing", no frequency)`.
- Judge each element on content, not on whether the label word appears. A justification that says "replaces the two failed switches in the Lisbon office" covers WHAT and WHERE even without the words "WHAT" or "WHERE".
- Score is the count of Present elements out of 7, written `n/7`. A Weak element doesn't count.
- Read from comes from `justification_rows`: `Request` for a requisition, `PO` for a PO reviewed as its own item, `PO line <PO>/<line>` for an invoice (it reads the justification on the PO line it bills). Call a justification Missing only when the text is empty or still the blank template; then every element cell reads `Missing` and Read from adds `(blank)`.
- For an invoice-only review, report a weak PO justification here without changing the invoice matching verdict. Explain that justification quality is outside this review's matching scope. Do not say the PO was already approved unless the input includes evidence of that approval; otherwise mark approval status Not checked.
- With no justification template on file, add one line under the heading: "Generic check: no justification template on file, so the seven standard elements were used."

### 4. 3-Way Match Summary
- One row per entry in `match_rows`, in the same order as the Items reviewed table. Copy `qty_match`, `price_match` and `duplicate_check` as they are. Qty match compares cumulative invoiced quantity with received (INV-5) and with ordered (INV-6). Price match compares the invoice price with the PO price within the tolerance (INV-4). Duplicate check reflects INV-9. Result is the item's verdict word.
- In Invoiced qty, when `invoiced_qty_cumulative` is larger than `invoiced_qty` (earlier invoices on the same PO line), write both: `20 (40 cumulative)`.
- An out-of-period line (INV-7) shows in Findings in detail and in Result, not in the match columns.
- Where a check couldn't run, write `Not checked (no receipt data)` or `Not checked (no price tolerance)`, and add one line after the table saying whether a 2-way match (PO against invoice) was done instead.
- After the table, one line per PO from `po_burn`. A projected run-out date may be added only when labeled "inference".
- With no invoices in the batch: "No invoices in this review, so no 3-way match was run." and nothing else.

---

## Spreadsheet (on request only)

Four sheets that mirror the sections: Verdict (groups and totals), Summary (items table and findings, one row per finding with item, rule, severity, number, source, and $ at stake), Justifications, 3-Way Match. Don't create a file unless the user asks for one.

---

## Example (3 items: 2 requisitions and 1 invoice; fictional data)

> ## 1. Verdict
> Hold: 1 of 3 items, $4,800.00; 1 send back, $5,000.00; 1 ready to approve, $3,000.00.
>
> - Hold (1): **$4,800.00**
> - Send back (1): **$5,000.00**
> - Ready to approve (1): **$3,000.00**
>
> ## 2. Summary
> **Totals:** All 3: $12,800.00 | 1 ready now: $3,000.00
>
> ### Items reviewed
> | Item | Supplier | Amount | Verdict | CC / Project | Category / Account | Justification | Budget | Match |
> |---|---|---|---|---|---|---|---|---|
> | INV-9001 | Vendor E | $4,800.00 | Hold | CC-4420 | IT services | 7/7 | Pass | Fail (billed more than received) |
> | REQ-300 | Vendor A | $5,000.00 | Send back | CC-4420 | Equipment | Missing | Pass | n/a |
> | REQ-301 | Vendor B | $3,000.00 | Ready to approve | CC-4420 | IT hardware | 7/7 | Pass | n/a |
>
> ### Review context
> | Field | Value |
> |---|---|
> | Review date | 2026-11-11 |
> | Checks run | Coding, Budget, Invoice, Justification |
> | Status | 3 pending |
> | Currency | USD |
>
> ### Findings in detail
> **INV-9001 | Vendor E | $4,800.00 | Hold**
> - INV-5 billed more than received: invoiced 12 h, received 8 h | 4 h over receipt | Invoices table, row INV-9001; receipt GR-77 | $1,600.00 at stake
>
> **REQ-300 | Vendor A | $5,000.00 | Send back**
> - JUS-1 justification missing: justification field is blank | 0 of 7 elements | Requisitions table, row REQ-300 | $0.00 at stake
>
> ### Questions for the requester
> 1. INV-9001: Can you confirm who accepted the 4 hours that are on the invoice but not on receipt GR-77?
> 2. REQ-300: What is being purchased, why is it needed now, and which cost center funds it?
>
> ### To finish this review
> - Approval tiers (unlocks APR-1 and APR-3)
>
> ### Not checked
> - Price and competition: no quotes provided
> - Approval tier: no approval tiers on file
>
> ### Basis of review
> - Profile: none on file, defaults labeled ASSUMPTION
> - Inputs: pasted message, 3 items, sha256 4f1c09a2be77
> - Parameters: quantity tolerance 0 (ASSUMPTION); price tolerance not provided
> - Arithmetic: group subtotals sum to the total: yes
> - Excluded rows: none
> - Method: script-computed (re-run if any input changes)
>
> ## 3. 7 Justifications Summary
> | Item | WHAT | HOW | WHY | WHO | WHERE | CADENCE | BUDGET | Score | Read from |
> |---|---|---|---|---|---|---|---|---|---|
> | INV-9001 | Present | Present | Present | Present | Present | Present | Present | 7/7 | PO line PO-55/1 |
> | REQ-300 | Missing | Missing | Missing | Missing | Missing | Missing | Missing | 0/7 | Request (blank) |
> | REQ-301 | Present | Present | Present | Present | Present | Present | Present | 7/7 | Request |
>
> ## 4. 3-Way Match Summary
> | Invoice | PO line | Ordered qty | Received qty | Invoiced qty | PO price | Invoice price | Qty match | Price match | Duplicate check | Result |
> |---|---|---|---|---|---|---|---|---|---|---|
> | INV-9001 | PO-55/1 | 40 h | 8 h | 12 h | $400.00 | $400.00 | Fail (billed more than received) | Not checked (no price tolerance); equal to PO price | Pass | Hold |
>
> No price tolerance on file, so prices were compared for equality only; the invoice price equals the PO price.
>
> PO burn: PO-55 value $16,000.00 | billed $4,800.00 | remaining $11,200.00 | 30.0% used

## Engine fields and where they go

What `all` returns, and where it goes in the report:

| Field | Used for |
|---|---|
| `bottom_line`, `groups`, `totals_line`, `check_sum_ok` | Section 1 and the Totals line |
| `items` | Items reviewed table (supplier, amount, cost center, account per item) |
| `findings`, `overall_verdict` | Verdict column and Findings in detail |
| `not_run`, `ignored_tables`, `unreadable_periods`, `notes` | To finish this review and Not checked (a `notes` line starting `ASSUMPTION:` also goes in Basis of review, Parameters) |
| `over_invoiced_commitments` | Questions for the requester: confirm each overage is in actuals |
| `policy_candidates` | Not in the report. Amounts found in prose outside the tables; ask the user before using one as a threshold (Rule 20) |
| `justification_rows` | Section 3: the text to judge for every item (an invoice reads the justification on the PO line it bills) |
| `match_rows`, `po_burn` | Section 4: one row per invoice line, with the status words already set |
| `inputs`, `mapped_columns`, `excluded_rows` | Basis of review |
