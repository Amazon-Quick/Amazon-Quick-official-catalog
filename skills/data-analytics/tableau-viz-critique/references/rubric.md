---
description: "The seven-domain scoring rubric: score anchors, weights, the criteria for each domain, excellence adjustments, overall caps and tiers."
last_updated: 2026-11-22
---
# Viz Critique Pro rubric

Use this reference for every scored review. Scores are 0–10 and may use one decimal place before weighting.

## Score anchors

| Score | Meaning |
| ---: | --- |
| 9–10 | Exceptional execution with specific, visible strengths and no material defect in the domain |
| 8–8.9 | Strong and polished; only minor opportunities |
| 7–7.9 | Competent and useful with noticeable but non-blocking gaps |
| 5–6.9 | Mixed execution; important friction or ambiguity affects use |
| 3–4.9 | Serious problems interfere with interpretation or action |
| 1–2.9 | Fundamentally ineffective or misleading in the domain |
| 0 | Domain cannot function as presented |

Use **not assessed** rather than inventing a score when the evidence is genuinely unavailable. Do not calculate an overall score until all seven domains have evidence. A complete visual review normally has evidence for all seven domains.

## Weights

| ID | Domain | Weight |
| --- | --- | ---: |
| D1 | Audience Adaptation | 15% |
| D2 | Message Alignment | 10% |
| D3 | Optimal Chart Usage | 20% |
| D4 | Strategic Layout and Storytelling | 25% |
| D5 | Effective Color | 15% |
| D6 | Textual Elements | 10% |
| D7 | Typography and Readability | 5% |

These weights total 100%. This edition assigns D6 10% to correct the source framework's 95% total while preserving the other domain weights.

## D1 — Audience Adaptation

Assess complexity, information density, decision support, visible control count, and time-to-insight for the intended audience. Executive and operational views should reveal status quickly; analyst views may favor richer exploration. Do not infer an audience solely from an attractive design.

Static interactivity observations belong here when they affect audience fit. Keep any explicit interactivity adjustment between -0.5 and +0.5 and do not also count the same evidence in the base score.

## D2 — Message Alignment

Assess whether the title, hierarchy, chart selection, comparisons, and annotations support a coherent primary question. A weak title does not erase strong structural alignment, but an unclear primary question caps D2 at 5.5 and D1 at 6.0.

## D3 — Optimal Chart Usage

Assess whether each chart answers its apparent question with appropriate encodings, scales, ordering, baselines, and comparison structure.

Document only clearly observed penalties, with a cumulative D3 anti-pattern adjustment no lower than -2.0:

- 3D or perspective distortion: -0.5
- pie/donut with more than five hard-to-compare slices: -0.5
- unjustified dual axes: -0.5
- missing axis unit needed for interpretation: -0.3
- inconsistent scales across directly comparable charts: -0.3
- gauge-heavy multi-KPI summary: -0.2
- overcrowded line chart, typically more than six to eight indistinguishable series: -0.3
- alphabetical order where rank or magnitude is the task: -0.3
- chaotic encoding that prevents comparison: up to -2.0

Do not penalize an unconventional chart merely for being uncommon; penalize impaired comprehension.

## D4 — Strategic Layout and Storytelling

Assess focal point, scan path, grid, spacing, grouping, overview-to-detail progression, filter placement, navigation, and disclosure model.

When all four conditions are visible—no quick focal point, several equally weighted charts, no overview-to-detail progression, and controls competing with content—cap D4 at 5.0 and the overall score at 6.2. Apply the cap only when every condition is evidenced.

Any explicit interactivity adjustment is limited to ±0.5 and must not duplicate the base score.

## D5 — Effective Color

Inspect the whole view before scoring: KPI tiles, status cues, chart fills, conditional formatting, text, controls, and containers. Credit semantic color wherever it communicates meaning, not only on KPI cards.

Assess palette harmony, consistency, color economy, contrast, and redundant non-color cues. Do not claim WCAG conformance from appearance alone unless colors and sizes were measured. A monochromatic analytical chart can be entirely appropriate.

## D6 — Textual Elements

Assess title usefulness, units, time range, axis and mark labels, legends, annotations, definitions, source notes, and call-to-action clarity. Missing context should be weighted by its effect on interpretation, not treated as a ceremonial checklist failure.

## D7 — Typography and Readability

Assess legibility at the intended display size, hierarchy, consistency, line length, density, truncation, and contrast. Do not impose a universal pixel minimum without knowing render scale and viewing context.

## Excellence adjustments

Bonuses recognize exceptional evidence not already credited in the base scores. Apply each at most once and cap cumulative positive bonuses at +0.8:

- aesthetic excellence, +0.5 to D4 when at least three exceptional qualities are clearly evidenced: cohesive identity, harmonic palette, consistent sizing, rhythmic spacing, professional restraint, typographic care, or exact alignment;
- accessible redundancy, +0.3 to D5 or D6 when measured contrast or clearly visible non-color cues materially exceed ordinary competence;
- innovative clarity, +0.3 to D3 when a novel encoding improves understanding;
- exceptional annotations, +0.2 to D6 when callouts materially guide interpretation.

Do not use a bonus to double-count evidence already responsible for a high base score.

## Overall caps

Add a `kind: safety` overall cap at 7.9 when a clearly observed issue creates a material ethical or interpretive risk:

- a truncated quantitative axis presented without a visible break or sufficient context and likely to mislead;
- 3D/perspective distortion that changes perceived magnitude;
- exposed PII, PHI, credentials, or comparable sensitive information;
- severe legibility or contrast failure that blocks a meaningful audience segment;
- missing unit, time range, or metric definition when the omission makes the conclusion materially ambiguous.

State the evidence, consequence, and repair. Use a direct, non-humorous tone. A safety cap suppresses the ordinary tier and produces `Safety remediation required`, even when the uncapped quality score was already below 7.9. Do not apply the cap for a merely imperfect title or minor omitted annotation.

## Tiers

| Score | Tier |
| ---: | --- |
| 8.6–10.0 | Iron Viz Ready |
| 7.5–8.5 | Would Publish to Public |
| 6.5–7.4 | Data With Its Shirt Tucked In |
| 5.0–6.4 | Can You See It on Your End? |
| 3.0–4.9 | Drag It Back to the Shelf |
| 0.0–2.9 | Tableau Public…ly Concerning |

The scoring helper applies decimal half-even rounding to one decimal before tier assignment.
