"""
description: Unit tests for variance_check.check and summarize: the October table passes, a bad total fails, rounding within the summed lines warns instead of failing, negative costs and stated variances flip together, NaN totals are not footed, and a zero comparison base still flags a large variance. Filesystem-free.
last_updated: 2026-11-24
"""

import json
import unittest

from variance_check import check, summarize

OCTOBER = (
    "line,type,parent,actual,comparison\n"
    "Revenue,revenue,Gross profit,57.4,54.7\n"
    "Cost of goods sold,cost,Gross profit,24.1,23.0\n"
    "Gross profit,profit,Operating income,33.3,31.7\n"
    "Contractor fees,cost,Operating expenses,2.9,2.2\n"
    "Travel,cost,Operating expenses,1.1,0.8\n"
    "Software licenses,cost,Operating expenses,1.6,1.9\n"
    "Salaries,cost,Operating expenses,12.4,12.4\n"
    "Operating expenses,cost,Operating income,18.0,17.3\n"
    "Operating income,profit,,15.3,14.4\n"
)
ROUNDED = (
    "line,type,parent,actual,comparison\n"
    "Hosting,cost,Total costs,1.0,1.0\nSupport,cost,Total costs,1.0,1.0\n"
    "Licenses,cost,Total costs,1.0,1.0\nTotal costs,cost,,3.1,3.0\n"
)


def _negate_costs(text: str) -> str:
    lines = text.strip().splitlines()
    out = [lines[0]]
    for line in lines[1:]:
        cells = line.split(",")
        if cells[1] == "cost":
            cells[3], cells[4] = str(-float(cells[3])), str(-float(cells[4]))
        out.append(",".join(cells))
    return "\n".join(out) + "\n"


class TestFooting(unittest.TestCase):
    def test_october_table_passes(self) -> None:
        report = check(OCTOBER, unit="M")
        self.assertEqual(report["status"], "PASS")
        by_line = {r["line"]: r for r in report["rows"]}
        self.assertEqual(by_line["Operating income"]["direction"], "F")
        self.assertEqual(by_line["Travel"]["direction"], "U")
        self.assertFalse(by_line["Travel"]["material"])

    def test_bad_total_fails_on_operating_expenses(self) -> None:
        bad = OCTOBER.replace(
            "Operating expenses,cost,Operating income,18.0",
            "Operating expenses,cost,Operating income,19.0",
        )
        report = check(bad, unit="M")
        self.assertTrue(report["status"].startswith("FAIL"))
        self.assertTrue(
            any("'Operating expenses' actual is 19" in f for f in report["faults"])
        )

    def test_rounding_across_summed_lines_warns_instead_of_failing(self) -> None:
        report = check(ROUNDED, unit="M")
        self.assertEqual(report["status"], "PASS with warnings")
        self.assertIn("within the rounding", report["warnings"][0])

    def test_explicit_rounding_is_strict(self) -> None:
        self.assertTrue(check(ROUNDED, rounding=0.05)["status"].startswith("FAIL"))

    def test_nan_total_is_missing_not_footed(self) -> None:
        text = "line,type,parent,actual,comparison\nRevenue,revenue,,nan,100\nA,revenue,Revenue,50,50\nB,revenue,Revenue,40,50\n"
        report = check(text)
        self.assertIn("missing actual or comparison", report["warnings"][0])
        self.assertIsNone(report["rows"][0]["variance"])


class TestSigns(unittest.TestCase):
    def test_negative_costs_warn_then_pass_with_costs_negative(self) -> None:
        negative = _negate_costs(OCTOBER)
        first = check(negative, unit="M")
        self.assertTrue(any("costs_negative=True" in w for w in first["warnings"]))
        self.assertEqual(
            check(negative, unit="M", costs_negative=True)["status"], "PASS"
        )

    def test_stated_variance_flips_with_negative_costs(self) -> None:
        text = "line,type,actual,budget,variance\nRent,cost,-120,-100,-20\n"
        self.assertEqual(check(text, costs_negative=True)["faults"], [])


class TestMateriality(unittest.TestCase):
    def test_zero_base_large_variance_is_material_and_warned(self) -> None:
        text = "line,type,actual,budget\nNew product revenue,revenue,5000000,0\nCore revenue,revenue,100000000,100000000\n"
        report = check(text)
        self.assertTrue(report["rows"][0]["material"])
        self.assertTrue(any("no comparison base" in w for w in report["warnings"]))

    def test_missing_required_column_fails(self) -> None:
        self.assertEqual(check("line,actual\nRevenue,1\n")["status"], "FAIL")


class TestSummarize(unittest.TestCase):
    def test_summary_keeps_only_workflow_fields(self) -> None:
        summary = json.loads(summarize(check(OCTOBER, unit="M")))
        self.assertEqual(summary["status"], "PASS")
        self.assertNotIn("variance_stated", summary["rows"][0])
        self.assertEqual(summary["rows"][0]["line"], "Revenue")


if __name__ == "__main__":
    unittest.main()
