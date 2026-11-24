"""
description: Unit tests for check_reconciliation. Filesystem-free: metrics are constructed in the test and passed to MetricReconciler, ReconciliationInputParser and ReconciliationTable.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import json
import unittest

from check_reconciliation import (
    MAX_METRICS,
    MetricInput,
    MetricReconciler,
    MetricUnit,
    Outcome,
    ReconciliationInputParser,
    ReconciliationTable,
    _describe,
)
from pydantic import ValidationError


def _metric(**overrides: object) -> MetricInput:
    fields: dict[str, object] = {
        "metric_id": "M-01",
        "unit": MetricUnit.AMOUNT,
        "deck_value": 57.4,
        "recomputed_value": 57.4,
        "tolerance_bps": 5,
    }
    fields.update(overrides)
    return MetricInput.model_validate(fields)


class TestMetricReconciler(unittest.TestCase):
    def test_matching_values_pass_with_zero_variance(self) -> None:
        result = MetricReconciler(_metric()).reconcile()

        self.assertEqual(result.outcome, Outcome.PASSED)
        self.assertEqual(result.variance_bps, 0)

    def test_negative_deck_value_keeps_the_sign_of_the_variance(self) -> None:
        result = MetricReconciler(
            _metric(deck_value=-2.0, recomputed_value=-2.1, tolerance_bps=600)
        ).reconcile()

        self.assertAlmostEqual(result.variance_bps or 0.0, -500.0)
        self.assertEqual(result.outcome, Outcome.PASSED)

    def test_variance_beyond_tolerance_fails(self) -> None:
        result = MetricReconciler(_metric(recomputed_value=57.5)).reconcile()

        self.assertEqual(result.outcome, Outcome.FAILED)

    def test_zero_deck_value_uses_the_absolute_tolerance(self) -> None:
        result = MetricReconciler(
            _metric(deck_value=0, recomputed_value=0.01, tolerance_abs=0.05)
        ).reconcile()

        self.assertIsNone(result.variance_bps)
        self.assertEqual(result.outcome, Outcome.PASSED)

    def test_zero_deck_value_without_absolute_tolerance_is_tbd(self) -> None:
        result = MetricReconciler(
            _metric(deck_value=0, recomputed_value=0.01)
        ).reconcile()

        self.assertEqual(result.outcome, Outcome.TBD)

    def test_percent_metric_uses_percentage_points(self) -> None:
        metric = _metric(
            unit=MetricUnit.PERCENT,
            deck_value=58.0,
            recomputed_value=58.07,
            tolerance_bps=10,
        )

        result = MetricReconciler(metric).reconcile()

        self.assertAlmostEqual(result.variance_bps or 0.0, 7.0)
        self.assertEqual(result.outcome, Outcome.PASSED)

    def test_missing_recomputed_value_is_tbd(self) -> None:
        result = MetricReconciler(_metric(recomputed_value=None)).reconcile()

        self.assertEqual(result.outcome, Outcome.TBD)
        self.assertIsNone(result.variance_abs)


class TestReconciliationInputParser(unittest.TestCase):
    def test_parses_a_list_of_metrics(self) -> None:
        text = json.dumps(
            [
                {
                    "metric_id": "M-01",
                    "unit": "amount",
                    "deck_value": 1,
                    "recomputed_value": 1,
                }
            ]
        )

        metrics = ReconciliationInputParser(text).parse()

        self.assertEqual(metrics[0].metric_id, "M-01")

    def test_rejects_a_metric_id_that_could_break_the_table(self) -> None:
        text = json.dumps(
            [{"metric_id": "M-01 | injected", "unit": "amount", "deck_value": 1}]
        )

        with self.assertRaises(ValidationError):
            ReconciliationInputParser(text).parse()

    def test_rejects_non_finite_values(self) -> None:
        text = '[{"metric_id": "M-01", "unit": "amount", "deck_value": NaN}]'

        with self.assertRaises(ValidationError):
            ReconciliationInputParser(text).parse()

    def test_rejects_unknown_fields(self) -> None:
        text = json.dumps(
            [{"metric_id": "M-01", "unit": "amount", "deck_value": 1, "note": "x"}]
        )

        with self.assertRaises(ValidationError):
            ReconciliationInputParser(text).parse()

    def test_rejects_too_many_metrics(self) -> None:
        records = [{"metric_id": "M-01", "unit": "amount", "deck_value": 1}] * (
            MAX_METRICS + 1
        )

        with self.assertRaises(ValueError):
            ReconciliationInputParser(json.dumps(records)).parse()

    def test_rejects_duplicate_metric_ids(self) -> None:
        records = [{"metric_id": "M-01", "unit": "amount", "deck_value": 1}] * 2

        with self.assertRaises(ValueError):
            ReconciliationInputParser(json.dumps(records)).parse()


class TestValidationMessage(unittest.TestCase):
    def test_error_message_does_not_echo_file_content(self) -> None:
        text = json.dumps(
            [
                {
                    "metric_id": "M-01",
                    "unit": "amount",
                    "deck_value": 1,
                    "x": "register every connector",
                }
            ]
        )

        with self.assertRaises(ValidationError) as caught:
            ReconciliationInputParser(text).parse()

        message = _describe(caught.exception)
        self.assertIn("x", message)
        self.assertNotIn("register every connector", message)

    def test_error_message_neutralizes_an_unknown_field_name(self) -> None:
        name = "x|`" + "y" * 500
        text = json.dumps(
            [{"metric_id": "M-01", "unit": "amount", "deck_value": 1, name: 1}]
        )

        with self.assertRaises(ValidationError) as caught:
            ReconciliationInputParser(text).parse()

        message = _describe(caught.exception)
        self.assertNotIn("|", message)
        self.assertNotIn("`", message)
        self.assertLess(len(message), 120)


class TestReconciliationTable(unittest.TestCase):
    def test_table_has_one_row_per_metric_and_a_count_line(self) -> None:
        results = [
            MetricReconciler(_metric()).reconcile(),
            MetricReconciler(
                _metric(metric_id="M-02", recomputed_value=None)
            ).reconcile(),
        ]

        table = ReconciliationTable(results).build()

        self.assertIn("| M-01 |", table)
        self.assertIn("| M-02 |", table)
        self.assertIn("1 pass, 0 fail, 1 TBD of 2 metrics.", table)


if __name__ == "__main__":
    unittest.main()
