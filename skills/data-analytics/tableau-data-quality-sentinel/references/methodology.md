---
description: "The metadata-quality rules in six domains, with thresholds and severities, plus escalation, deduplication, scores and grades."
last_updated: 2026-11-22
---
# Metadata quality methodology

Apply a rule only when its required property is present. Each finding has one primary domain and may list other domains for escalation.

## 1. Schema hygiene

- `schema.excessive_fields`: 101–200 fields MEDIUM; >200 HIGH.
- `schema.no_dimensions`: zero dimensions MEDIUM.
- `schema.no_measures`: zero measures LOW; allow lookup-table context.
- `schema.single_table`: one logical table is an observation, not scored.
- `schema.orphan_table`: unconnected table in an observed multi-table graph MEDIUM.
- `schema.calc_ratio`: >60% calculations MEDIUM; >80% HIGH. Use one tier.

## 2. Field naming

Exclude parameters. Reduce one level for explicitly auto-generated fields.

- `naming.system_suffix`: `__c` or `__r` suffix, MEDIUM.
- `naming.snake_case`: at least three lowercase underscore-separated tokens, LOW.
- `naming.camel_case`: lower camel case without spaces, LOW.
- `naming.screaming_case`: at least two uppercase underscore-separated tokens, LOW.
- `naming.cryptic`: fewer than four characters except an explicit allowlist such as `id`, `qty`, `amt`, MEDIUM.
- `naming.generic`: value/field/col/data/info/item with optional digits, MEDIUM.
- `naming.table_qualified`: contains an observed table caption verbatim, LOW.

Aggregate more than ten matches of one pattern into one finding with count and up to five examples.

## 3. Type and role

Use token/word-boundary matching, not arbitrary substrings.

- `type.date_as_string`: date/time/created/updated/timestamp token with STRING type, HIGH.
- `type.numeric_as_string`: count/amount/qty/price/total/rate/pct/percent token with STRING type, HIGH.
- `type.id_as_measure`: id/key/code token with MEASURE role, MEDIUM.
- `type.boolean_as_string`: is/has/flag/active/enabled token with STRING type, LOW.
- `type.category_role_mismatch`: observed category conflicts with role, LOW.

If a calculation clearly performs an intentional conversion, reduce one level and explain. Aggregate more than ten matches. If one mismatch affects more than half of eligible fields, set `systemic: true`.

## 4. Calculation complexity

- `calc.deep_branching`: more than five nested IF/CASE levels, MEDIUM.
- `calc.hardcoded_logic`: more than three string comparisons used as business logic, LOW.
- `calc.cross_table`: references more than two observed logical tables, MEDIUM.
- `calc.nested_lod`: nested LOD expression, MEDIUM.
- `calc.long_formula`: >500 characters LOW; >1000 MEDIUM. Use one tier.

Aggregate when more than five calculations breach one rule; include count and up to three examples.

## 5. Metadata completeness

- `metadata.no_source_description`: description property is observed and empty, HIGH.
- `metadata.no_tags`: tags property is observed and empty, MEDIUM.
- `metadata.field_descriptions`: when exposed, 100% absent HIGH; >90% absent MEDIUM.
- `metadata.parameter_docs`: observed parameters have neither meaningful names nor aliases, LOW.
- `metadata.uncertified`: explicit uncertified status LOW; MEDIUM only with exposed usage >0.

## 6. Freshness and connectivity

- `freshness.live_connection`: explicit live/no-extract status plus observed downstream use, MEDIUM advisory. Without usage data, make it an observation.
- `freshness.stale_proxy`: update timestamp 91–180 days old MEDIUM; >180 HIGH. Label this an activity proxy.
- `freshness.orphan_proxy`: explicit zero downstream connections LOW observation, not scored.
- `freshness.default_project`: explicit project name `default`, LOW.

Use the scan timestamp for age calculations and report it.

## Escalation and deduplication

- Start from the base severity.
- Escalate one level if `systemic` is true or at least two distinct domains are implicated.
- Set CRITICAL for the explicit combined condition: uncertified + no source description + stale proxy.
- Apply at most one general escalation, capped at CRITICAL.
- Deduplicate by `source_id + rule_id + evidence_key`; keep the highest effective severity.
- Assign a finding to its primary domain for domain scoring even when it spans domains.

## Score and grades

Subtract 10/5/2/0.5 for CRITICAL/HIGH/MEDIUM/LOW, then bound to 0–100.

| Score | Grade | Score | Grade |
| ---: | :---: | ---: | :---: |
| 97–100 | A+ | 77–79.5 | C+ |
| 93–96.5 | A | 73–76.5 | C |
| 90–92.5 | A- | 70–72.5 | C- |
| 87–89.5 | B+ | 67–69.5 | D+ |
| 83–86.5 | B | 63–66.5 | D |
| 80–82.5 | B- | 60–62.5 | D- |
| | | 0–59.5 | F |

Average included source scores for the composite. Do not average domain scores. Exclude inaccessible sources; include reused sources only when their baseline uses this methodology version.

