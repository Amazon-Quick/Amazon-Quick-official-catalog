---
description: "Sign conventions; ratios; materiality; rate, volume, and mix; FX and volume flex estimates; bridges; and what to check when a number does not reconcile. Read in Workflow - Write Commentary steps 5 to 9."
last_updated: 2026-11-24
---
# Methods

## Sign convention

Variance = actual − comparison. Favorable (F) or unfavorable (U) depends on the line type, not the sign:

| Line type | Higher than comparison | Examples |
|---|---|---|
| revenue | F | net revenue, bookings, recurring revenue |
| profit | F | gross profit, operating income, EBITDA, net income |
| cost | U | cost of goods sold, operating expenses, contractor fees, travel |
| ratio | depends: margins higher = F; cost ratios higher = U | gross margin %, cost per unit |
| metric | ask | headcount, units, tickets, customers |

State the convention once in the output. Use (F) and (U) on every material line. When costs are stored as negative numbers, confirm before labeling.

## Ratios and rates

- Compare ratios in percentage points (pp) or basis points (1 pp = 100 bps). "Margin rose 0.5 pp to 57.9%", not "margin rose 0.9%".
- A ratio across lines is a ratio of sums: total gross profit ÷ total revenue, never the average of line margins.
- When a ratio's base is tiny or zero, show the % change as n/m (not meaningful).

## Materiality

Default: a money line is material when its variance is at least 2% of its comparison value and at least 1% of the largest revenue, profit, or cost line. A ratio line is material at 10 bps or more. An amount-per-unit line or a metric line is material at 2% or more. A user's own threshold (for example, over $100K or over 10%) replaces the default. Scale the length of a comment with the size of the variance: one clause for a small material line, a full sentence with the owner's stated next step for the largest.

## Rate, volume, and mix

For a segment table with units and rates (price per unit, cost per unit):

- **Volume** = (total actual units − total comparison units) × the segment's comparison share × its comparison rate. More units at the planned mix and rates.
- **Mix** = (actual share − comparison share) × total actual units × the segment's comparison rate. Selling relatively more of a high-rate segment is favorable for revenue.
- **Rate** = (actual rate − comparison rate) × actual units. Call it a price effect only when an owner confirms a price change; otherwise it's an average-rate effect, because averages also move with what customers bought.
- Volume + mix + rate = the total variance, per segment and in total. The script checks this.

`mix_vs_avg` values each segment's share shift against the average comparison rate, which makes the sign easier to read (a shift toward an above-average segment is positive). Its total equals the total mix.

## FX

If the share of sales in a currency and the comparison and actual rates are known, size the foreign exchange (FX) effect. It is the difference between converting this period's foreign-currency sales at the actual rate and at the comparison rate: reported sales × currency share × (1 - comparison rate / actual rate). Example: $57.4M × 30% × (1 - 1.10 / 1.06) = -$0.65M. Rates are quoted as reporting currency per unit of foreign currency. A context note with no named person (for example an FX rate in a briefing) is data, not an owner statement. The result is a Data-supported estimate, and the commentary says "about" or "estimated".

## Volume flex

If units are known, split each variable cost into the part explained by volume (comparison cost per unit × actual units) and the rest (rate or efficiency). Treat materials, direct labor, freight, hosting, and other usage-based costs as variable unless the user says otherwise, and confirm the list once. A cost under budget only because volume was lower is not a saving. The result is a Data-supported estimate.

## Bridges

A bridge (walk) goes from the comparison value to the actual value through named drivers. The drivers must sum exactly to the change. Keep any remainder as its own Unexplained bar. A remainder over the rounding tolerance is an open item with an owner and a due date.

## When a number doesn't reconcile

Check in this order; the first one that explains the gap is usually the answer:

1. Units: $K where $M was expected, or a scaled column.
2. Signs: costs stored as negatives, or a contra line.
3. Calendar: fiscal periods mixed with calendar periods, cut-off dates, a 53-week year.
4. Scenario: the wrong budget or forecast version.
5. Grain: duplicate rows from a join.
6. Filters: an exclusion applied on one side only.
7. FX: different rate dates for actuals and comparison.
8. Timing: a late adjustment after the extract.
9. Rounding: rounded components that don't add to the rounded total.
