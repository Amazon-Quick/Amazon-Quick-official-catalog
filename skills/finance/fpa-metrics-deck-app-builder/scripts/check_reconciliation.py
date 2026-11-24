"""
description: Reconcile each deck value to its recomputed value. Reads a JSON list of metrics, computes the absolute variance, the variance in basis points (bps) and pass, fail or TBD against each metric's tolerance, and prints a Markdown table for 04-reconciliation.md.
last_updated: 2026-11-24
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

BPS_PER_UNIT = 10_000
BPS_PER_PERCENTAGE_POINT = 100
BPS_DECIMALS = 6
MAX_INPUT_BYTES = 1_000_000
MAX_METRICS = 500
METRIC_ID_PATTERN = r"^M-[0-9]{2,4}$"
MAX_REPORTED_ERRORS = 10
MAX_NAME_CHARS = 40
UNSAFE_CHARS = frozenset("|`<>#*[]")


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


class MetricUnit(str, Enum):  # noqa: UP042 (str, Enum) keeps Python 3.10 support
    """How a metric's values are expressed."""

    AMOUNT = "amount"
    PERCENT = "percent"


class Outcome(str, Enum):  # noqa: UP042 (str, Enum) keeps Python 3.10 support
    """The result of reconciling one metric."""

    PASSED = "Pass"
    FAILED = "Fail"
    TBD = "TBD"


class MetricInput(BaseModel):
    """One metric to reconcile. A missing recomputed value or tolerance gives TBD."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_id: str = Field(pattern=METRIC_ID_PATTERN)
    unit: MetricUnit
    deck_value: float
    recomputed_value: float | None = None
    tolerance_bps: float | None = Field(default=None, ge=0)
    tolerance_abs: float | None = Field(default=None, ge=0)

    @field_validator("deck_value", "recomputed_value", "tolerance_bps", "tolerance_abs")
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("must be a finite number")
        return value


class MetricResult(BaseModel):
    """The reconciliation of one metric, one row of the table."""

    model_config = ConfigDict(frozen=True)

    metric_id: str
    deck_value: float
    recomputed_value: float | None
    variance_abs: float | None
    variance_bps: float | None
    tolerance: str
    outcome: Outcome
    note: str


class MetricReconciler:
    """Reconciles one metric against its tolerance."""

    def __init__(self, metric: MetricInput) -> None:
        self.metric = metric

    def reconcile(self) -> MetricResult:
        metric = self.metric
        if metric.recomputed_value is None:
            return self._result(None, None, Outcome.TBD, "no recomputed value")
        variance_abs = metric.recomputed_value - metric.deck_value
        if metric.unit is MetricUnit.PERCENT:
            variance_bps = round(variance_abs * BPS_PER_PERCENTAGE_POINT, BPS_DECIMALS)
            return self._against_bps(variance_abs, variance_bps)
        if metric.deck_value == 0:
            return self._against_abs(
                variance_abs, None, "deck value is 0, bps undefined"
            )
        variance_bps = round(
            variance_abs / abs(metric.deck_value) * BPS_PER_UNIT, BPS_DECIMALS
        )
        if metric.tolerance_bps is None and metric.tolerance_abs is not None:
            return self._against_abs(variance_abs, variance_bps, "")
        return self._against_bps(variance_abs, variance_bps)

    def _against_bps(self, variance_abs: float, variance_bps: float) -> MetricResult:
        if self.metric.tolerance_bps is None:
            return self._result(
                variance_abs, variance_bps, Outcome.TBD, "tolerance in bps TBD"
            )
        passed = abs(variance_bps) <= self.metric.tolerance_bps
        return self._result(
            variance_abs, variance_bps, Outcome.PASSED if passed else Outcome.FAILED, ""
        )

    def _against_abs(
        self, variance_abs: float, variance_bps: float | None, note: str
    ) -> MetricResult:
        if self.metric.tolerance_abs is None:
            return self._result(
                variance_abs,
                variance_bps,
                Outcome.TBD,
                _join(note, "absolute tolerance TBD"),
            )
        passed = abs(variance_abs) <= self.metric.tolerance_abs
        return self._result(
            variance_abs,
            variance_bps,
            Outcome.PASSED if passed else Outcome.FAILED,
            note,
        )

    def _result(
        self,
        variance_abs: float | None,
        variance_bps: float | None,
        outcome: Outcome,
        note: str,
    ) -> MetricResult:
        return MetricResult(
            metric_id=self.metric.metric_id,
            deck_value=self.metric.deck_value,
            recomputed_value=self.metric.recomputed_value,
            variance_abs=variance_abs,
            variance_bps=variance_bps,
            tolerance=_tolerance_text(self.metric),
            outcome=outcome,
            note=note,
        )


class ReconciliationInputParser:
    """Parses the JSON input text into validated metrics."""

    def __init__(self, text: str) -> None:
        self.text = text

    def parse(self) -> list[MetricInput]:
        if len(self.text.encode("utf-8")) > MAX_INPUT_BYTES:
            raise ValueError(f"input is larger than {MAX_INPUT_BYTES} bytes")
        records = json.loads(self.text)
        if not isinstance(records, list) or not records:
            raise ValueError("input must be a non-empty JSON list of metrics")
        if len(records) > MAX_METRICS:
            raise ValueError(f"input has more than {MAX_METRICS} metrics")
        metrics = [MetricInput.model_validate(record) for record in records]
        ids = [metric.metric_id for metric in metrics]
        if len(set(ids)) != len(ids):
            raise ValueError("each metric_id must appear once")
        return metrics


class ReconciliationTable:
    """Builds the Markdown reconciliation table from the results."""

    def __init__(self, results: list[MetricResult]) -> None:
        self.results = results

    def build(self) -> str:
        lines = [
            "| Metric ID | Deck value | Recomputed value | Variance (abs) | Variance (bps) | Tolerance | Pass? | Note |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for result in self.results:
            cells = [
                result.metric_id,
                _number(result.deck_value),
                _number(result.recomputed_value),
                _number(result.variance_abs),
                _bps(result.variance_bps),
                result.tolerance,
                result.outcome.value,
                result.note,
            ]
            lines.append("| " + " | ".join(cells) + " |")
        counts = {
            outcome: sum(1 for r in self.results if r.outcome is outcome)
            for outcome in Outcome
        }
        lines.append("")
        lines.append(
            f"{counts[Outcome.PASSED]} pass, {counts[Outcome.FAILED]} fail, {counts[Outcome.TBD]} TBD"
            f" of {len(self.results)} metrics."
        )
        return "\n".join(lines)


class Reconciliation:
    """Reads the input file, reconciles every metric and returns the table."""

    def __init__(self, input_path: Path) -> None:
        self.input_path = input_path

    def run(self) -> str:
        if self.input_path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError(f"input is larger than {MAX_INPUT_BYTES} bytes")
        text = self.input_path.read_text(encoding="utf-8")
        metrics = ReconciliationInputParser(text).parse()
        results = [MetricReconciler(metric).reconcile() for metric in metrics]
        return ReconciliationTable(results).build()


def _join(first: str, second: str) -> str:
    return f"{first}; {second}" if first else second


def _number(value: float | None) -> str:
    return "TBD" if value is None else f"{value:,.6g}"


def _bps(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.1f}"


def _describe(error: ValidationError) -> str:
    """Name each invalid field without echoing its value, which is file content."""
    problems = [
        f"{'.'.join(_safe_text(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors(include_input=False, include_url=False)
    ]
    return "; ".join(problems[:MAX_REPORTED_ERRORS])


def _safe_text(part: object) -> str:
    """A field name can come from the file: keep it printable, plain and short."""
    text = "".join(
        ch if ch.isprintable() and ch not in UNSAFE_CHARS else "?" for ch in str(part)
    )
    return text[:MAX_NAME_CHARS]


def _tolerance_text(metric: MetricInput) -> str:
    parts = []
    if metric.tolerance_bps is not None:
        parts.append(f"{metric.tolerance_bps:g} bps")
    if metric.tolerance_abs is not None:
        parts.append(f"{metric.tolerance_abs:g} abs")
    return ", ".join(parts) if parts else "TBD"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile deck values to recomputed values."
    )
    parser.add_argument("input", help="Path to the JSON list of metrics to reconcile.")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        logger.error("Not found: %s", _safe_text(input_path.name))
        return 2
    try:
        table = Reconciliation(input_path).run()
    except ValidationError as error:
        logger.error(
            "Cannot reconcile %s: %s", _safe_text(input_path.name), _describe(error)
        )
        return 2
    except OSError as error:
        logger.error(
            "Cannot reconcile %s: the file could not be read (%s)",
            _safe_text(input_path.name),
            type(error).__name__,
        )
        return 2
    except ValueError as error:
        # Raised by the parser with fixed text, or by json with a position only.
        logger.error("Cannot reconcile %s: %s", _safe_text(input_path.name), error)
        return 2
    logger.info("Reconciliation\n%s", table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
