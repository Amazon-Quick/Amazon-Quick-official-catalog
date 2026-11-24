---
description: "The assessment JSON that scripts/score_viz.py scores: seven domains with base scores, adjustments and optional caps."
last_updated: 2026-11-22
---
# Assessment JSON schema

The scoring helper requires exactly seven domain entries under `domains`. Each domain has a numeric `base` score from 0–10 and an `adjustments` list. Empty `caps` are optional.

## Minimal assessment

```json
{
  "domains": {
    "D1": {"base": 7.5, "adjustments": []},
    "D2": {"base": 7.0, "adjustments": []},
    "D3": {"base": 8.0, "adjustments": []},
    "D4": {"base": 7.5, "adjustments": []},
    "D5": {"base": 8.0, "adjustments": []},
    "D6": {"base": 7.0, "adjustments": []},
    "D7": {"base": 7.5, "adjustments": []}
  }
}
```

## Adjustments

Every adjustment requires `label`, `value`, and `kind`. Bonuses also require a supported `id`.

```json
{
  "base": 8.0,
  "adjustments": [
    {"id": "innovative-clarity", "label": "Small multiples improve comparison", "value": 0.3, "kind": "bonus"},
    {"label": "Inconsistent comparable scales", "value": -0.3, "kind": "anti-pattern"}
  ]
}
```

Allowed kinds:

| Kind | Domain | Range or rule |
| --- | --- | --- |
| `bonus` | Defined below | Positive; per-bonus maximum and cumulative +0.8 |
| `interactivity` | D1 or D4 | Combined adjustment within each domain must be between -0.5 and +0.5 |
| `anti-pattern` | D3 | Non-positive; cumulative minimum -2.0 |
| `other` | Any | Non-positive evidence-based deduction |

Supported bonuses:

| ID | Allowed domain | Maximum |
| --- | --- | ---: |
| `aesthetic-excellence` | D4 | +0.5 |
| `accessible-redundancy` | D5 or D6 | +0.3 |
| `innovative-clarity` | D3 | +0.3 |
| `exceptional-annotations` | D6 | +0.2 |

Each bonus ID may appear once. Do not encode ordinary strengths as bonuses.

## Caps

Domain caps map a domain ID to a maximum score. Overall caps are objects with `label`, numeric `value`, and `kind` (`quality` or `safety`).

```json
{
  "caps": {
    "domains": {"D1": 6.0, "D2": 5.5},
    "overall": [
      {"label": "Primary question is unclear", "value": 6.2, "kind": "quality"},
      {"label": "Exposed sensitive information", "value": 7.9, "kind": "safety"}
    ]
  }
}
```

Any declared safety cap sets `safety_status` to `blocked`, suppresses the normal score tier, and returns `Safety remediation required`. It does so even when the cap does not numerically lower an already-low score.
