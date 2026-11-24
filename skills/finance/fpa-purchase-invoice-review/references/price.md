---
description: "Module 4 price and competition checks: quotes required, sole-source reasons, price history, and cost-saving evidence. Read when the price module runs."
last_updated: 2026-11-24
---
# Module 4: Price and competition

Goal: the business pays a fair price, has the competition its policy requires, and knows of cheaper ways to the same outcome when evidence shows one.

Arguments (pass them as a list to `pir_run`, for example `pir_run(["price", ...])`; add `--input <saved message>` to use a pasted message): `price --lines L.csv [--history H.csv] [--quotes Q.csv] [--quote-threshold <profile>] [--quotes-required <profile>] [--tolerance <profile>] --window-days 365 --as-of <date>`

If `--tolerance` is omitted, PRC-1 reports NOT RUN. If `--quote-threshold` is omitted, PRC-2 reports NOT RUN; pass `--quotes-required` from the profile too (it is 2 when not given; label that ASSUMPTION). PRC-3 (expired quotes) and PRC-4 (not lowest quote) always run when quote data is present.

## Script rules
| Rule | Hit when | Severity |
|---|---|---|
| PRC-1 above history median | unit price > median of the last window-days of buys of the same item by more than tolerance; $ = (unit - median) x qty | CONDITION |
| PRC-2 quotes below policy | total >= quote threshold, fewer valid quotes than required, no sole-source reason | SEND_BACK |
| PRC-2 sole source - reason to test | as above but a sole-source reason is given | CONDITION |
| PRC-3 quote expired | quote valid-until before as-of date | SEND_BACK (requote) |
| PRC-4 not lowest quote | chosen total above the lowest valid quote; $ = difference | CONDITION |

## Judgment rules
- Pareto: spend effort on the 1-3 lines that carry most of the value.
- Test "only vendor that can" claims against the quotes and history in hand; ask for the technical reason when none is given.
- Repairs: compare to the price of new and of refurbished units when the user has them; a repair close to the price of new deserves a question.
- Flag lines high against their own context (delivery cost close to the item's value).
- Single quote at list price with no discount: ask for a second quote or a volume discount.
- Cost-saving suggestions need evidence: a lower quote, a history row, or a published price the user supplied. Otherwise write "none evidenced". Never invent a benchmark.
- Lifecycle: for equipment, compare the 3-year cost (price + consumables + service) when the data allows; ask about constraints rather than assuming an alternative works.
- Who should pay: warranty failures, vendor demo returns, and vendor-caused rework are normally the vendor's cost; ask before the business funds them.

## Not checked when
No quote_policy in profile: PRC-2 reports NOT RUN; ask above what $ competitive quotes are required and how many.
No price_variance_tolerance in profile: PRC-1 reports NOT RUN; ask what % above history median triggers a finding.
No history and no quotes: PRC-1 and PRC-3/4 report "not tested - no data supplied".
