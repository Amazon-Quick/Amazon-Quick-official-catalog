"""
description: Unit tests for create_benchmark.py. Filesystem-free: the pure calculators and the record builder get injected suites, runs, and history, so pass rates, lift, regressions, consistency, targets, and the scorecard are verified without reading any run directory.
last_updated: 2026-10-22
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime
import unittest

from create_benchmark import (
    CheckOutcome,
    Config,
    EvalSuite,
    Fingerprint,
    LiftEstimator,
    RegressionFinder,
    ResultRecordBuilder,
    RunCost,
    RunRecord,
    ScorecardRenderer,
)

SUITE = EvalSuite.model_validate(
    {
        "skill_name": "demo",
        "settings": {"repeats": 2},
        "cases": [
            {
                "id": "case-a",
                "prompt": "p",
                "checks": [
                    {"id": "c1", "type": "outcome", "check": "x"},
                    {"id": "c2", "type": "process", "check": "y"},
                ],
            },
            {
                "id": "case-b",
                "prompt": "q",
                "should_trigger": False,
                "checks": [{"id": "c1", "type": "triggering", "check": "z"}],
            },
        ],
    }
)
FINGERPRINT = Fingerprint(skill_checksum="sha256:a", evals_checksum="sha256:b")
TODAY = datetime.date(2026, 10, 22)


def _run(case: str, config: Config, run: int, grades: dict[str, bool]) -> RunRecord:
    return RunRecord(
        case_id=case, config=config, run=run, grades=grades, cost=RunCost(tool_calls=4)
    )


RUNS = [
    _run("case-a", Config.WITH_SKILL, 1, {"c1": True, "c2": True}),
    _run("case-a", Config.WITH_SKILL, 2, {"c1": True, "c2": False}),
    _run("case-a", Config.WITHOUT_SKILL, 1, {"c1": False, "c2": False}),
    _run("case-a", Config.WITHOUT_SKILL, 2, {"c1": False, "c2": True}),
    _run("case-b", Config.WITH_SKILL, 1, {"c1": True}),
    _run("case-b", Config.WITH_SKILL, 2, {"c1": True}),
]


def _build(previous=None):
    return ResultRecordBuilder(
        SUITE, RUNS, previous, FINGERPRINT, "smart", TODAY
    ).build()


class TestResultRecordBuilder(unittest.TestCase):
    def test_build_counts_every_with_skill_verdict(self) -> None:
        score = _build().scores.with_skill
        self.assertEqual((score.passed, score.total), (5, 6))

    def test_build_scores_baseline_without_negative_controls(self) -> None:
        score = _build().scores.baseline
        self.assertEqual((score.passed, score.total), (1, 4))

    def test_build_consistency_counts_only_fully_passing_cases(self) -> None:
        self.assertEqual(_build().scores.consistency, 0.5)

    def test_missing_grade_counts_as_fail(self) -> None:
        runs = [_run("case-a", Config.WITH_SKILL, 1, {"c1": True})]
        record = ResultRecordBuilder(
            SUITE, runs, None, FINGERPRINT, "smart", TODAY
        ).build()
        self.assertEqual(record.scores.with_skill.passed, 1)
        self.assertEqual(record.scores.with_skill.total, 2)

    def test_targets_report_not_met_below_pass_rate(self) -> None:
        self.assertFalse(_build().targets_met.pass_rate)


class TestLiftEstimator(unittest.TestCase):
    def test_estimate_pairs_checks_and_reports_points(self) -> None:
        outcomes = [
            CheckOutcome(
                case_id="a", check_id="c", config=Config.WITH_SKILL, runs=[True]
            ),
            CheckOutcome(
                case_id="a", check_id="c", config=Config.WITHOUT_SKILL, runs=[False]
            ),
        ]
        lift = LiftEstimator(outcomes, Config.WITHOUT_SKILL).estimate()
        self.assertEqual((lift.points, lift.margin), (100.0, 0.0))

    def test_estimate_is_repeatable(self) -> None:
        first = _build().scores.lift
        second = _build().scores.lift
        self.assertEqual(first, second)

    def test_estimate_without_pairs_is_none(self) -> None:
        outcomes = [
            CheckOutcome(
                case_id="a", check_id="c", config=Config.WITH_SKILL, runs=[True]
            )
        ]
        self.assertIsNone(LiftEstimator(outcomes, Config.WITHOUT_SKILL).estimate())


class TestRegressionFinder(unittest.TestCase):
    def test_find_lists_checks_that_stopped_passing(self) -> None:
        previous = _build()
        previous.checks = [
            CheckOutcome(
                case_id="case-a",
                check_id="c2",
                config=Config.WITH_SKILL,
                runs=[True, True],
            )
        ]
        current = _build().checks
        self.assertEqual(RegressionFinder(current, previous).find(), ["case-a/c2"])

    def test_find_on_first_run_is_empty(self) -> None:
        self.assertEqual(RegressionFinder(_build().checks, None).find(), [])


class TestChangedTests(unittest.TestCase):
    def _previous_with_other_tests(self):
        previous = _build()
        previous.evals_checksum = "sha256:other"
        previous.checks = [
            CheckOutcome(
                case_id="case-a", check_id="c2", config=Config.WITH_SKILL, runs=[True]
            )
        ]
        return previous

    def test_changed_tests_report_no_regressions(self) -> None:
        record = _build(previous=self._previous_with_other_tests())
        self.assertTrue(record.scores.tests_changed)
        self.assertEqual(record.scores.regressions, [])

    def test_changed_tests_say_not_comparable(self) -> None:
        text = ScorecardRenderer(
            _build(previous=self._previous_with_other_tests())
        ).render()
        self.assertIn("tests changed since last run, not comparable", text)

    def test_same_tests_compare_with_last_run(self) -> None:
        text = ScorecardRenderer(_build(previous=_build())).render()
        self.assertIn("(was 83%)", text)


class TestScorecardRenderer(unittest.TestCase):
    def test_render_shows_counts_and_target_verdicts(self) -> None:
        text = ScorecardRenderer(_build()).render()
        self.assertIn("Checks passed with the skill:", text)
        self.assertIn("5 of 6 (83%)", text)
        self.assertIn("target 90%: not met", text)
        self.assertIn("first saved run", text)


if __name__ == "__main__":
    unittest.main()
