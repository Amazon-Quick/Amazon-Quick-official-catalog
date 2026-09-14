"""
description: Identifies funnel friction points and quantifies their revenue impact using two-proportion significance testing.
last_updated: 2026-09-13
origin: original

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
    JSON to stdout with ranked friction points, revenue impact,
    and recommendations.

Design:
    FunnelDataFile / BaselineFile (I/O) load JSON inputs. StageConverter,
    TwoProportionTest, FrictionIdentifier, SegmentAnalyzer and
    HypothesisGenerator are pure logic classes; RevenueReportBuilder
    assembles the final model and RevenueImpactAnalysis (facade) wires the
    pure pipeline. RevenueImpactReport is the I/O facade. stdout carries only
    the machine-readable JSON result, so the baseline diagnostic is written
    to stderr to keep that payload uncorrupted.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger(__name__)


class FunnelStage(StrEnum):
    """Standard e-commerce funnel stages used for default baselines and blockers."""

    SESSION_START = "Session Start"
    PRODUCT_VIEW = "Product View"
    ADD_TO_CART = "Add to Cart"
    BEGIN_CHECKOUT = "Begin Checkout"
    PAYMENT_INFO = "Payment Info"
    ORDER_CONFIRMATION = "Order Confirmation"


# Coefficients for the Abramowitz-Stegun error-function approximation used to
# convert a Z-score into a confidence percentage.
_ERF_A1: float = 0.254829592
_ERF_A2: float = -0.284496736
_ERF_A3: float = 1.421413741
_ERF_A4: float = -1.453152027
_ERF_A5: float = 1.061405429
_ERF_P: float = 0.3275911

# Default per-stage baseline conversion rates (used when no historical baseline
# is supplied), keyed by the funnel stage the transition starts from.
_DEFAULT_BASELINES: dict[str, float] = {
    FunnelStage.SESSION_START.value: 0.45,
    FunnelStage.PRODUCT_VIEW.value: 0.35,
    FunnelStage.ADD_TO_CART.value: 0.65,
    FunnelStage.BEGIN_CHECKOUT.value: 0.75,
    FunnelStage.PAYMENT_INFO.value: 0.85,
}

# Candidate root-cause hypotheses per stage, ordered from most to least likely.
_STAGE_BLOCKERS: dict[str, list[str]] = {
    FunnelStage.SESSION_START.value: [
        "High bounce rate due to slow page load (>3s LCP)",
        "Landing page content mismatch with ad/search intent",
        "Above-the-fold content not compelling enough",
        "Pop-ups or interstitials disrupting engagement",
    ],
    FunnelStage.PRODUCT_VIEW.value: [
        "Product listing page UX issues (poor filtering)",
        "Insufficient product imagery or descriptions",
        "Price visibility issues or unexpected pricing",
        "Out-of-stock items shown prominently in listings",
    ],
    FunnelStage.ADD_TO_CART.value: [
        "Add-to-cart button not prominent on mobile",
        "Size/variant selection friction",
        "Missing urgency signals or social proof",
        "Unclear shipping costs or delivery estimates",
    ],
    FunnelStage.BEGIN_CHECKOUT.value: [
        "Cart page showing unexpected costs (tax, shipping)",
        "Required account creation before checkout",
        "Cart abandonment due to price comparison",
        "Missing guest checkout option",
    ],
    FunnelStage.PAYMENT_INFO.value: [
        "Limited payment method options",
        "Form validation errors or UX friction",
        "Security trust signals insufficient",
        "Mobile keyboard/input field issues",
    ],
}

_UNKNOWN_HYPOTHESIS: list[str] = ["Unknown friction pattern"]
_UNKNOWN_SEGMENT: str = "unknown"
_MOBILE_VALUE: str = "mobile"
_DOWNSTREAM_RATE: float = 0.3
_Z_THRESHOLD: float = 1.96
_MIN_ABSOLUTE_CHANGE: float = 0.5
_CONCENTRATION_FACTOR: float = 0.2
_TOP_FRICTION_POINTS: int = 5
_MAX_SEGMENT_ROWS: int = 5
_WEEKLY_MULTIPLIER: int = 7
_SEGMENT_KEY_ARROW: str = " \u2192 "
_DEFAULT_AOV: float = 85.00
_DEFAULT_MIN_SAMPLE: int = 1000
_DEFAULT_SIGNIFICANCE_THRESHOLD: float = 0.05
_DEFAULT_SEGMENTS: tuple[str, ...] = ("device", "geo", "category")


class SignificanceResult(BaseModel):
    """Z-score and matching confidence percentage for a proportion comparison."""

    z_score: float
    confidence: int | float


class Transition(BaseModel):
    """Stage-to-stage conversion figures for one funnel transition."""

    from_stage: str
    to_stage: str
    from_visitors: int
    to_visitors: int
    conversion_rate: int | float
    drop_off_rate: int | float
    visitors_lost: int


class StageConversions(BaseModel):
    """Per-stage visitor totals and the transitions between consecutive stages."""

    stage_totals: dict
    transitions: list[Transition]


class SegmentBreakdown(BaseModel):
    """Conversion figures for one value of a segment dimension."""

    value: str
    visitors: int
    conversion_rate_pct: float
    vs_overall_pp: float
    is_concentrated: bool


class FrictionPoint(BaseModel):
    """A statistically significant drop-off with its quantified revenue impact."""

    from_stage: str
    to_stage: str
    current_rate_pct: float
    baseline_rate_pct: float
    drop_pp: float
    visitors_affected: int
    visitors_lost_vs_baseline: int
    z_score: float
    confidence_pct: int | float
    revenue_impact_daily: float
    revenue_impact_weekly: float
    is_significant: bool


class EnrichedFrictionPoint(BaseModel):
    """A friction point enriched with root-cause hypotheses and segment data."""

    from_stage: str
    to_stage: str
    current_rate_pct: float
    baseline_rate_pct: float
    drop_pp: float
    visitors_affected: int
    visitors_lost_vs_baseline: int
    z_score: float
    confidence_pct: int | float
    revenue_impact_daily: float
    revenue_impact_weekly: float
    is_significant: bool
    hypothesis: str
    alternative_hypotheses: list
    segment_concentration: dict[str, list[SegmentBreakdown]]


class RevenueSummary(BaseModel):
    """Top-level totals for the revenue impact report."""

    total_friction_points: int
    total_daily_revenue_impact: int | float
    total_weekly_revenue_impact: int | float
    analysis_period: dict
    aov_used: float
    analyzed_at: str


class FunnelOverview(BaseModel):
    """Funnel stages, per-stage totals, and stage transitions."""

    stages: list
    stage_totals: dict
    transitions: list[Transition]


class Methodology(BaseModel):
    """Description of the statistical method and revenue formula used."""

    significance_test: str
    confidence_threshold: str
    min_absolute_change: str
    min_sample_size: int
    revenue_formula: str


class RevenueReport(BaseModel):
    """The complete revenue impact analysis emitted as JSON."""

    summary: RevenueSummary
    funnel_overview: FunnelOverview
    friction_points: list[EnrichedFrictionPoint]
    methodology: Methodology


class FunnelData(BaseModel):
    """Standardized funnel input parsed at the boundary (from funnel_analyzer)."""

    stages: list
    data: list[dict]
    metadata: dict = Field(default_factory=dict)


class TwoProportionTest:
    """Two-proportion Z-test and confidence conversion (pure)."""

    def __init__(
        self, baseline_rate: float, baseline_n: int, current_rate: float, current_n: int
    ) -> None:
        self.baseline_rate = baseline_rate
        self.baseline_n = baseline_n
        self.current_rate = current_rate
        self.current_n = current_n

    def test(self) -> SignificanceResult:
        """Return the Z-score and two-tailed confidence for the comparison."""
        z = self._z_score(
            self.baseline_rate, self.baseline_n, self.current_rate, self.current_n
        )
        confidence = self._confidence(abs(z))
        return SignificanceResult(z_score=z, confidence=confidence)

    def _z_score(self, p1: float, n1: int, p2: float, n2: int) -> float:
        """Calculate the Z-score for the difference between two proportions."""
        if n1 == 0 or n2 == 0:
            return 0.0

        p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)

        if p_pool == 0 or p_pool == 1:
            return 0.0

        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))

        if se == 0:
            return 0.0

        return (p1 - p2) / se

    def _confidence(self, z: float) -> int | float:
        """Convert a Z-score to a two-tailed confidence percentage in [0, 100]."""
        sign = 1 if z >= 0 else -1
        z_abs = abs(z)

        t = 1.0 / (1.0 + _ERF_P * z_abs)
        y = 1.0 - (
            ((((_ERF_A5 * t + _ERF_A4) * t) + _ERF_A3) * t + _ERF_A2) * t + _ERF_A1
        ) * t * math.exp(-z_abs * z_abs / 2)

        cdf = 0.5 * (1.0 + sign * y)
        confidence = (1 - 2 * (1 - cdf)) * 100
        return max(0, min(100, confidence))


class StageConverter:
    """Computes stage totals and consecutive-stage transitions (pure)."""

    def __init__(self, data: list[dict], stages: list) -> None:
        self.data = data
        self.stages = stages

    def convert(self) -> StageConversions:
        """Return per-stage visitor totals and the transitions between stages."""
        stage_totals: dict = {}
        for record in self.data:
            stage = record["stage"]
            visitors = record.get("visitors", 0)
            stage_totals[stage] = stage_totals.get(stage, 0) + visitors

        transitions = []
        for i in range(len(self.stages) - 1):
            from_stage = self.stages[i]
            to_stage = self.stages[i + 1]

            from_visitors = stage_totals.get(from_stage, 0)
            to_visitors = stage_totals.get(to_stage, 0)

            conversion_rate = (
                (to_visitors / from_visitors * 100) if from_visitors > 0 else 0
            )
            drop_off_rate = 100 - conversion_rate

            transitions.append(
                Transition(
                    from_stage=from_stage,
                    to_stage=to_stage,
                    from_visitors=from_visitors,
                    to_visitors=to_visitors,
                    conversion_rate=round(conversion_rate, 2),
                    drop_off_rate=round(drop_off_rate, 2),
                    visitors_lost=from_visitors - to_visitors,
                )
            )

        return StageConversions(stage_totals=stage_totals, transitions=transitions)


class FrictionIdentifier:
    """Identifies statistically significant friction points (pure)."""

    def __init__(
        self,
        transitions: list[Transition],
        baseline: dict | None,
        aov: float,
        min_sample: int,
        significance_threshold: float,
    ) -> None:
        self.transitions = transitions
        self.baseline = baseline
        self.aov = aov
        self.min_sample = min_sample
        # Retained to preserve the original signature; not used in the computation.
        self.significance_threshold = significance_threshold

    def identify(self) -> list[FrictionPoint]:
        """Return the top revenue-impacting significant friction points."""
        friction_points = []

        for transition in self.transitions:
            point = self._evaluate(transition)
            if point is not None:
                friction_points.append(point)

        friction_points.sort(key=lambda x: x.revenue_impact_daily, reverse=True)

        return friction_points[:_TOP_FRICTION_POINTS]

    def _evaluate(self, transition: Transition) -> FrictionPoint | None:
        """Return a FrictionPoint for a significant transition, else None."""
        from_stage = transition.from_stage
        to_stage = transition.to_stage
        current_rate = transition.conversion_rate / 100
        current_n = transition.from_visitors

        if current_n < self.min_sample:
            return None

        baseline_rate, baseline_n = self._baseline_for(
            from_stage, current_rate, current_n
        )

        result = TwoProportionTest(
            baseline_rate, baseline_n, current_rate, current_n
        ).test()
        z = result.z_score
        confidence = result.confidence

        absolute_change = (baseline_rate - current_rate) * 100
        is_significant = (
            abs(z) >= _Z_THRESHOLD
            and absolute_change >= _MIN_ABSOLUTE_CHANGE
            and current_n >= self.min_sample
        )

        if not (is_significant and absolute_change > 0):
            return None

        visitors_recoverable = current_n * (baseline_rate - current_rate)
        downstream_rate = _DOWNSTREAM_RATE
        revenue_impact = visitors_recoverable * downstream_rate * self.aov

        return FrictionPoint(
            from_stage=from_stage,
            to_stage=to_stage,
            current_rate_pct=round(current_rate * 100, 2),
            baseline_rate_pct=round(baseline_rate * 100, 2),
            drop_pp=round(absolute_change, 2),
            visitors_affected=current_n,
            visitors_lost_vs_baseline=int(visitors_recoverable),
            z_score=round(z, 3),
            confidence_pct=round(confidence, 1),
            revenue_impact_daily=round(revenue_impact, 2),
            revenue_impact_weekly=round(revenue_impact * _WEEKLY_MULTIPLIER, 2),
            is_significant=True,
        )

    def _baseline_for(
        self, from_stage: str, current_rate: float, current_n: int
    ) -> tuple[float, int]:
        """Return the baseline rate and sample size for a stage."""
        if self.baseline and from_stage in self.baseline:
            baseline_rate = (
                self.baseline[from_stage].get("conversion_rate", current_rate * 100)
                / 100
            )
            baseline_n = self.baseline[from_stage].get("sample_size", current_n)
            return baseline_rate, baseline_n

        baseline_rate = _DEFAULT_BASELINES.get(from_stage, current_rate)
        baseline_n = current_n
        return baseline_rate, baseline_n


class SegmentAnalyzer:
    """Breaks friction points down by segment dimensions (pure)."""

    def __init__(
        self,
        data: list[dict],
        friction_points: list[FrictionPoint],
        segments: list[str],
    ) -> None:
        self.data = data
        self.friction_points = friction_points
        self.segments = segments

    def analyze(self) -> dict[str, dict[str, list[SegmentBreakdown]]]:
        """Return per-friction-point, per-segment conversion breakdowns."""
        segment_analysis: dict[str, dict[str, list[SegmentBreakdown]]] = {}

        for friction_point in self.friction_points:
            from_stage = friction_point.from_stage
            to_stage = friction_point.to_stage
            key = f"{from_stage}{_SEGMENT_KEY_ARROW}{to_stage}"

            segment_analysis[key] = {}

            for segment in self.segments:
                breakdown = self._breakdown_for(friction_point, segment)
                if breakdown is not None:
                    segment_analysis[key][segment] = breakdown

        return segment_analysis

    def _breakdown_for(
        self, friction_point: FrictionPoint, segment: str
    ) -> list[SegmentBreakdown] | None:
        """Return the sorted segment breakdown for one friction point, or None."""
        from_stage = friction_point.from_stage
        to_stage = friction_point.to_stage

        stage_data = [r for r in self.data if r["stage"] == from_stage and segment in r]
        next_stage_data = [
            r for r in self.data if r["stage"] == to_stage and segment in r
        ]

        if not stage_data:
            return None

        # Local scratch accumulator keyed by segment value; does not cross a boundary.
        seg_groups: dict = {}
        for record in stage_data:
            seg_val = record.get(segment, _UNKNOWN_SEGMENT)
            if seg_val not in seg_groups:
                seg_groups[seg_val] = {"from_visitors": 0, "to_visitors": 0}
            seg_groups[seg_val]["from_visitors"] += record["visitors"]

        for record in next_stage_data:
            seg_val = record.get(segment, _UNKNOWN_SEGMENT)
            if seg_val in seg_groups:
                seg_groups[seg_val]["to_visitors"] += record["visitors"]

        segment_breakdown = []
        overall_rate = friction_point.current_rate_pct

        for seg_val, counts in seg_groups.items():
            if counts["from_visitors"] > 0:
                seg_rate = counts["to_visitors"] / counts["from_visitors"] * 100

                segment_breakdown.append(
                    SegmentBreakdown(
                        value=seg_val,
                        visitors=counts["from_visitors"],
                        conversion_rate_pct=round(seg_rate, 2),
                        vs_overall_pp=round(seg_rate - overall_rate, 2),
                        is_concentrated=(
                            abs(seg_rate - overall_rate)
                            > overall_rate * _CONCENTRATION_FACTOR
                        ),
                    )
                )

        segment_breakdown.sort(key=lambda x: x.conversion_rate_pct)
        return segment_breakdown[:_MAX_SEGMENT_ROWS]


class HypothesisGenerator:
    """Enriches friction points with root-cause hypotheses (pure)."""

    def __init__(
        self,
        friction_points: list[FrictionPoint],
        segment_analysis: dict[str, dict[str, list[SegmentBreakdown]]],
    ) -> None:
        self.friction_points = friction_points
        self.segment_analysis = segment_analysis

    def generate(self) -> list[EnrichedFrictionPoint]:
        """Return friction points enriched with hypotheses and segment data."""
        enriched_points = []

        for friction_point in self.friction_points:
            from_stage = friction_point.from_stage
            key = f"{from_stage}{_SEGMENT_KEY_ARROW}{friction_point.to_stage}"

            hypotheses = _STAGE_BLOCKERS.get(from_stage, _UNKNOWN_HYPOTHESIS)

            seg_data = self.segment_analysis.get(key, {})
            device_data = seg_data.get("device", [])

            primary_hypothesis = self._primary_hypothesis(hypotheses, device_data)

            enriched_points.append(
                EnrichedFrictionPoint(
                    **friction_point.model_dump(),
                    hypothesis=primary_hypothesis,
                    alternative_hypotheses=hypotheses[1:3],
                    segment_concentration=seg_data,
                )
            )

        return enriched_points

    def _primary_hypothesis(
        self, hypotheses: list[str], device_data: list[SegmentBreakdown]
    ) -> str:
        """Pick the primary hypothesis, favoring a mobile-specific one if applicable."""
        primary_hypothesis = hypotheses[0]

        if device_data:
            worst_device = device_data[0] if device_data else None
            if worst_device and worst_device.value == _MOBILE_VALUE:
                primary_hypothesis = (
                    f"Mobile-specific: "
                    f"{hypotheses[-1] if len(hypotheses) > 1 else hypotheses[0]}"
                )

        return primary_hypothesis


class RevenueReportBuilder:
    """Assembles the final RevenueReport from computed parts (builder, pure)."""

    def __init__(
        self,
        enriched: list[EnrichedFrictionPoint],
        conversions: StageConversions,
        stages: list,
        aov: float,
        min_sample: int,
        analysis_period: dict,
    ) -> None:
        self.enriched = enriched
        self.conversions = conversions
        self.stages = stages
        self.aov = aov
        self.min_sample = min_sample
        self.analysis_period = analysis_period

    def build(self) -> RevenueReport:
        """Combine summary, funnel overview, friction points, and methodology."""
        total_daily_impact = sum(fp.revenue_impact_daily for fp in self.enriched)
        total_weekly_impact = sum(fp.revenue_impact_weekly for fp in self.enriched)

        return RevenueReport(
            summary=RevenueSummary(
                total_friction_points=len(self.enriched),
                total_daily_revenue_impact=round(total_daily_impact, 2),
                total_weekly_revenue_impact=round(total_weekly_impact, 2),
                analysis_period=self.analysis_period,
                aov_used=self.aov,
                analyzed_at=datetime.now().isoformat(),
            ),
            funnel_overview=FunnelOverview(
                stages=self.stages,
                stage_totals=self.conversions.stage_totals,
                transitions=self.conversions.transitions,
            ),
            friction_points=self.enriched,
            methodology=Methodology(
                significance_test="Two-proportion Z-test",
                confidence_threshold="95% (Z \u2265 1.96)",
                min_absolute_change="0.5 percentage points",
                min_sample_size=self.min_sample,
                revenue_formula=(
                    "Visitors \u00d7 (Baseline% - Actual%) "
                    "\u00d7 Downstream_Rate \u00d7 AOV"
                ),
            ),
        )


class RevenueImpactAnalysis:
    """Facade: turn loaded funnel data into a revenue impact report (pure)."""

    def __init__(
        self,
        funnel_data: FunnelData,
        aov: float,
        baseline: dict | None,
        min_sample: int,
        significance_threshold: float,
    ) -> None:
        self.funnel_data = funnel_data
        self.aov = aov
        self.baseline = baseline
        self.min_sample = min_sample
        self.significance_threshold = significance_threshold

    def analyze(self) -> RevenueReport:
        """Run the full pure pipeline and return the assembled report."""
        stages = self.funnel_data.stages
        data = self.funnel_data.data
        metadata = self.funnel_data.metadata
        segments = metadata.get("segments", list(_DEFAULT_SEGMENTS))
        analysis_period = metadata.get("date_range", {})

        conversions = StageConverter(data, stages).convert()
        friction_points = FrictionIdentifier(
            conversions.transitions,
            self.baseline,
            self.aov,
            self.min_sample,
            self.significance_threshold,
        ).identify()
        segment_analysis = SegmentAnalyzer(data, friction_points, segments).analyze()
        enriched = HypothesisGenerator(friction_points, segment_analysis).generate()

        return RevenueReportBuilder(
            enriched,
            conversions,
            stages,
            self.aov,
            self.min_sample,
            analysis_period,
        ).build()


class FunnelDataFile:
    """Reads standardized funnel JSON into a FunnelData model (I/O)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> FunnelData:
        """Load and parse the funnel data JSON."""
        return FunnelData.model_validate(
            json.loads(self.path.read_text(encoding="utf-8"))
        )


class BaselineFile:
    """Reads an optional historical baseline JSON (I/O)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict | None:
        """Load the baseline JSON, or warn and return None if it is missing."""
        try:
            content = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            sys.stderr.write(
                "Warning: Baseline file not found, using industry benchmarks\n"
            )
            return None
        return json.loads(content)


class RevenueImpactReport:
    """I/O facade: read inputs and return the revenue impact report."""

    def __init__(
        self,
        input_path: Path,
        aov: float,
        baseline_path: Path | None,
        min_sample: int,
        significance_threshold: float,
    ) -> None:
        self.input_path = input_path
        self.aov = aov
        self.baseline_path = baseline_path
        self.min_sample = min_sample
        self.significance_threshold = significance_threshold

    def build(self) -> RevenueReport:
        """Load funnel data and baseline, then run the analysis."""
        funnel_data = FunnelDataFile(self.input_path).read()
        baseline = (
            BaselineFile(self.baseline_path).read() if self.baseline_path else None
        )
        return RevenueImpactAnalysis(
            funnel_data,
            self.aov,
            baseline,
            self.min_sample,
            self.significance_threshold,
        ).analyze()


def _build_parser() -> argparse.ArgumentParser:
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
        default=_DEFAULT_AOV,
        help="Average Order Value in dollars",
    )
    parser.add_argument(
        "--baseline-file",
        default=None,
        help="Path to historical baseline JSON",
    )
    parser.add_argument(
        "--significance-threshold", type=float, default=_DEFAULT_SIGNIFICANCE_THRESHOLD
    )
    parser.add_argument("--min-sample", type=int, default=_DEFAULT_MIN_SAMPLE)
    return parser


def main() -> int:
    """Parse arguments, run the analysis, and emit the report JSON to stdout."""
    args = _build_parser().parse_args()

    baseline_path = Path(args.baseline_file) if args.baseline_file else None
    report = RevenueImpactReport(
        Path(args.input),
        args.aov,
        baseline_path,
        args.min_sample,
        args.significance_threshold,
    ).build()

    sys.stdout.write(json.dumps(report.model_dump(), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
