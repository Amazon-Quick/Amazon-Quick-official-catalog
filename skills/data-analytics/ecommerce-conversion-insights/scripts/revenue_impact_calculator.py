"""
Revenue Impact Calculator.

Identifies friction points and quantifies revenue impact.

Accepts standardized funnel data (from funnel_analyzer.py) and produces:
- Statistical significance testing for each stage transition
- Revenue impact estimates per friction point
- Segment concentration analysis
- Ranked friction point list with root cause hypotheses

Usage:
    python revenue_impact_calculator.py --input funnel_data.json
                                        --aov 85.00
                                        --baseline-file baseline.json
                                        [--significance-threshold 0.05]
                                        [--min-sample 1000]

Output:
    JSON with ranked friction points, revenue impact,
    and recommendations.
"""

import argparse
import json
import math
import sys
from datetime import datetime


def z_score_two_proportions(p1: float, n1: int, p2: float, n2: int) -> float:
    """Calculate Z-score for difference between two proportions."""
    if n1 == 0 or n2 == 0:
        return 0.0

    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)

    if p_pool == 0 or p_pool == 1:
        return 0.0

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))

    if se == 0:
        return 0.0

    return (p1 - p2) / se


def z_to_confidence(z: float) -> float:
    """Convert Z-score to confidence percentage (two-tailed)."""
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1 if z >= 0 else -1
    z_abs = abs(z)

    t = 1.0 / (1.0 + p * z_abs)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(
        -z_abs * z_abs / 2
    )

    cdf = 0.5 * (1.0 + sign * y)
    confidence = (1 - 2 * (1 - cdf)) * 100
    return max(0, min(100, confidence))


def calculate_stage_conversions(data: list[dict], stages: list[str]) -> dict:
    """Calculate conversion rates between consecutive stages."""
    stage_totals = {}
    for record in data:
        stage = record["stage"]
        visitors = record.get("visitors", 0)
        stage_totals[stage] = stage_totals.get(stage, 0) + visitors

    transitions = []
    for i in range(len(stages) - 1):
        from_stage = stages[i]
        to_stage = stages[i + 1]

        from_visitors = stage_totals.get(from_stage, 0)
        to_visitors = stage_totals.get(to_stage, 0)

        conversion_rate = (
            (to_visitors / from_visitors * 100) if from_visitors > 0 else 0
        )
        drop_off_rate = 100 - conversion_rate

        transitions.append(
            {
                "from_stage": from_stage,
                "to_stage": to_stage,
                "from_visitors": from_visitors,
                "to_visitors": to_visitors,
                "conversion_rate": round(conversion_rate, 2),
                "drop_off_rate": round(drop_off_rate, 2),
                "visitors_lost": from_visitors - to_visitors,
            }
        )

    return {
        "stage_totals": stage_totals,
        "transitions": transitions,
    }


def identify_friction_points(
    transitions: list[dict],
    baseline: dict | None,
    aov: float,
    min_sample: int = 1000,
    significance_threshold: float = 0.05,
) -> list[dict]:
    """Identify statistically significant friction points."""
    friction_points = []

    for transition in transitions:
        from_stage = transition["from_stage"]
        to_stage = transition["to_stage"]
        current_rate = transition["conversion_rate"] / 100
        current_n = transition["from_visitors"]

        if current_n < min_sample:
            continue

        if baseline and from_stage in baseline:
            baseline_rate = (
                baseline[from_stage].get("conversion_rate", current_rate * 100) / 100
            )
            baseline_n = baseline[from_stage].get("sample_size", current_n)
        else:
            default_baselines = {
                "Session Start": 0.45,
                "Product View": 0.35,
                "Add to Cart": 0.65,
                "Begin Checkout": 0.75,
                "Payment Info": 0.85,
            }
            baseline_rate = default_baselines.get(from_stage, current_rate)
            baseline_n = current_n

        z = z_score_two_proportions(baseline_rate, baseline_n, current_rate, current_n)
        confidence = z_to_confidence(abs(z))

        absolute_change = (baseline_rate - current_rate) * 100
        is_significant = (
            abs(z) >= 1.96 and absolute_change >= 0.5 and current_n >= min_sample
        )

        if is_significant and absolute_change > 0:
            visitors_recoverable = current_n * (baseline_rate - current_rate)
            downstream_rate = 0.3
            revenue_impact = visitors_recoverable * downstream_rate * aov

            friction_points.append(
                {
                    "from_stage": from_stage,
                    "to_stage": to_stage,
                    "current_rate_pct": round(current_rate * 100, 2),
                    "baseline_rate_pct": round(baseline_rate * 100, 2),
                    "drop_pp": round(absolute_change, 2),
                    "visitors_affected": current_n,
                    "visitors_lost_vs_baseline": int(visitors_recoverable),
                    "z_score": round(z, 3),
                    "confidence_pct": round(confidence, 1),
                    "revenue_impact_daily": round(revenue_impact, 2),
                    "revenue_impact_weekly": round(revenue_impact * 7, 2),
                    "is_significant": True,
                }
            )

    friction_points.sort(key=lambda x: x["revenue_impact_daily"], reverse=True)

    return friction_points[:5]


def analyze_segments(
    data: list[dict],
    friction_points: list[dict],
    segments: list[str],
) -> dict:
    """Break down friction points by segment dimensions."""
    segment_analysis = {}

    for fp in friction_points:
        from_stage = fp["from_stage"]
        to_stage = fp["to_stage"]
        key = f"{from_stage} \u2192 {to_stage}"

        segment_analysis[key] = {}

        for segment in segments:
            stage_data = [r for r in data if r["stage"] == from_stage and segment in r]
            next_stage_data = [
                r for r in data if r["stage"] == to_stage and segment in r
            ]

            if not stage_data:
                continue

            seg_groups = {}
            for record in stage_data:
                seg_val = record.get(segment, "unknown")
                if seg_val not in seg_groups:
                    seg_groups[seg_val] = {
                        "from_visitors": 0,
                        "to_visitors": 0,
                    }
                seg_groups[seg_val]["from_visitors"] += record["visitors"]

            for record in next_stage_data:
                seg_val = record.get(segment, "unknown")
                if seg_val in seg_groups:
                    seg_groups[seg_val]["to_visitors"] += record["visitors"]

            segment_breakdown = []
            overall_rate = fp["current_rate_pct"]

            for seg_val, counts in seg_groups.items():
                if counts["from_visitors"] > 0:
                    seg_rate = counts["to_visitors"] / counts["from_visitors"] * 100

                    segment_breakdown.append(
                        {
                            "value": seg_val,
                            "visitors": counts["from_visitors"],
                            "conversion_rate_pct": round(seg_rate, 2),
                            "vs_overall_pp": round(seg_rate - overall_rate, 2),
                            "is_concentrated": (
                                abs(seg_rate - overall_rate) > overall_rate * 0.2
                            ),
                        }
                    )

            segment_breakdown.sort(key=lambda x: x["conversion_rate_pct"])
            segment_analysis[key][segment] = segment_breakdown[:5]

    return segment_analysis


def generate_hypotheses(
    friction_points: list[dict], segment_analysis: dict
) -> list[dict]:
    """Generate root cause hypotheses for each friction point."""
    stage_blockers = {
        "Session Start": [
            "High bounce rate due to slow page load (>3s LCP)",
            "Landing page content mismatch with ad/search intent",
            "Above-the-fold content not compelling enough",
            "Pop-ups or interstitials disrupting engagement",
        ],
        "Product View": [
            "Product listing page UX issues (poor filtering)",
            "Insufficient product imagery or descriptions",
            "Price visibility issues or unexpected pricing",
            "Out-of-stock items shown prominently in listings",
        ],
        "Add to Cart": [
            "Add-to-cart button not prominent on mobile",
            "Size/variant selection friction",
            "Missing urgency signals or social proof",
            "Unclear shipping costs or delivery estimates",
        ],
        "Begin Checkout": [
            "Cart page showing unexpected costs (tax, shipping)",
            "Required account creation before checkout",
            "Cart abandonment due to price comparison",
            "Missing guest checkout option",
        ],
        "Payment Info": [
            "Limited payment method options",
            "Form validation errors or UX friction",
            "Security trust signals insufficient",
            "Mobile keyboard/input field issues",
        ],
    }

    enriched_points = []

    for fp in friction_points:
        from_stage = fp["from_stage"]
        key = f"{from_stage} \u2192 {fp['to_stage']}"

        hypotheses = stage_blockers.get(from_stage, ["Unknown friction pattern"])

        seg_data = segment_analysis.get(key, {})
        device_data = seg_data.get("device", [])

        primary_hypothesis = hypotheses[0]

        if device_data:
            worst_device = device_data[0] if device_data else None
            if worst_device and worst_device.get("value") == "mobile":
                primary_hypothesis = (
                    f"Mobile-specific: "
                    f"{hypotheses[-1] if len(hypotheses) > 1 else hypotheses[0]}"
                )

        fp_enriched = {**fp}
        fp_enriched["hypothesis"] = primary_hypothesis
        fp_enriched["alternative_hypotheses"] = hypotheses[1:3]
        fp_enriched["segment_concentration"] = seg_data

        enriched_points.append(fp_enriched)

    return enriched_points


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=("Calculate revenue impact of funnel friction points")
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to funnel data JSON (from funnel_analyzer.py)",
    )
    parser.add_argument(
        "--aov",
        type=float,
        default=85.00,
        help="Average Order Value in dollars",
    )
    parser.add_argument(
        "--baseline-file",
        default=None,
        help="Path to historical baseline JSON",
    )
    parser.add_argument("--significance-threshold", type=float, default=0.05)
    parser.add_argument("--min-sample", type=int, default=1000)

    args = parser.parse_args()

    with open(args.input) as f:
        funnel_data = json.load(f)

    baseline = None
    if args.baseline_file:
        try:
            with open(args.baseline_file) as f:
                baseline = json.load(f)
        except FileNotFoundError:
            print(
                "Warning: Baseline file not found, using industry benchmarks",
                file=sys.stderr,
            )

    stages = funnel_data["stages"]
    data = funnel_data["data"]
    segments = funnel_data.get("metadata", {}).get(
        "segments", ["device", "geo", "category"]
    )

    stage_analysis = calculate_stage_conversions(data, stages)

    friction_points = identify_friction_points(
        stage_analysis["transitions"],
        baseline,
        args.aov,
        args.min_sample,
        args.significance_threshold,
    )

    segment_analysis = analyze_segments(data, friction_points, segments)

    enriched_friction_points = generate_hypotheses(friction_points, segment_analysis)

    total_daily_impact = sum(
        fp["revenue_impact_daily"] for fp in enriched_friction_points
    )
    total_weekly_impact = sum(
        fp["revenue_impact_weekly"] for fp in enriched_friction_points
    )

    output = {
        "summary": {
            "total_friction_points": len(enriched_friction_points),
            "total_daily_revenue_impact": round(total_daily_impact, 2),
            "total_weekly_revenue_impact": round(total_weekly_impact, 2),
            "analysis_period": funnel_data.get("metadata", {}).get("date_range", {}),
            "aov_used": args.aov,
            "analyzed_at": datetime.now().isoformat(),
        },
        "funnel_overview": {
            "stages": stages,
            "stage_totals": stage_analysis["stage_totals"],
            "transitions": stage_analysis["transitions"],
        },
        "friction_points": enriched_friction_points,
        "methodology": {
            "significance_test": "Two-proportion Z-test",
            "confidence_threshold": "95% (Z \u2265 1.96)",
            "min_absolute_change": "0.5 percentage points",
            "min_sample_size": args.min_sample,
            "revenue_formula": (
                "Visitors \u00d7 (Baseline% - Actual%) "
                "\u00d7 Downstream_Rate \u00d7 AOV"
            ),
        },
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
