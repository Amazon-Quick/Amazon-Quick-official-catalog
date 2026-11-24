"""
description: Unit tests for scenario_report.build and check_page on a result built in code: cap labels without rewriting user text, braces in user text, escaping, layout order, file name only, and the units check. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import math
import unittest

import scenario_engine as sa
import scenario_report
from _fixtures import REVENUE_COLMAP, UNITS, revenue_table


def cap_result() -> dict:
    df = sa.prepare(revenue_table(), REVENUE_COLMAP)
    df.attrs["input_audit"]["source"] = "plan.xlsx"
    drivers = [
        {
            "name": "Bullock Ranch contract",
            "value": 20,
            "prob": 0.5,
            "date": "2026-11-01",
        }
    ]
    context = [
        {
            "source": "Bearden memo <b>2026-09</b>",
            "claim": "Bearings cost {{rises}} in Q4",
            "affects": "measure",
            "direction": "down",
        }
    ]
    return sa.run(
        df,
        {**UNITS, "target_direction": "at_most", "target": 1250},
        drivers=drivers,
        context_findings=context,
    )


class TestBuild(unittest.TestCase):
    def setUp(self) -> None:
        self.page = scenario_report.build(cap_result())

    def test_cap_labels_do_not_rewrite_user_text(self) -> None:
        self.assertIn("Bullock Ranch contract", self.page)
        self.assertNotIn("High caseock", self.page)
        self.assertIn("Median P50", self.page)

    def test_braces_in_user_text_are_kept(self) -> None:
        self.assertIn("{{rises}}", self.page)

    def test_user_markup_is_escaped(self) -> None:
        self.assertIn("&lt;b&gt;2026-09&lt;/b&gt;", self.page)
        self.assertNotIn("<b>2026-09</b>", self.page)

    def test_limitations_come_before_the_probability(self) -> None:
        self.assertLess(
            self.page.index("Data limitations"), self.page.index('class="hero"')
        )

    def test_no_against_benchmark_shorthand(self) -> None:
        self.assertNotIn(" vs ", self.page)

    def test_units_check_finds_every_place(self) -> None:
        found = scenario_report.check_page(self.page, "USD thousands")
        self.assertTrue(
            all(
                found[k]
                for k in (
                    "title",
                    "target_headline",
                    "scenario_metrics",
                    "basis_of_review",
                )
            )
        )
        self.assertFalse(found["units_missing_fallback"])


class TestTicks(unittest.TestCase):
    def test_range_narrower_than_a_float_step_still_ends(self) -> None:
        ticks = scenario_report._ticks(1e6, math.nextafter(1e6, 2e6), 6)
        self.assertLessEqual(len(ticks), scenario_report.MAX_TICKS)

    def test_non_finite_range_has_no_ticks(self) -> None:
        self.assertEqual(scenario_report._ticks(float("nan"), 1.0), [])


class TestWording(unittest.TestCase):
    def test_hero_and_disclaimer_call_the_figures_estimates(self) -> None:
        page = scenario_report.build(cap_result())
        self.assertIn("not a prediction", page)
        self.assertIn("not accounting or financial advice", page)


class TestNoBenchmark(unittest.TestCase):
    def test_missing_benchmark_kpi_has_no_unit(self) -> None:
        table = revenue_table().drop(columns=["Budget"])
        df = sa.prepare(table, {"period": "Month", "measure": "Revenue"})
        page = scenario_report.build(sa.run(df, {**UNITS, "target": 1260}))
        self.assertIn("No full-year benchmark", page)
        self.assertNotIn('>none</div><div class="d">USD thousands', page)


if __name__ == "__main__":
    unittest.main()
