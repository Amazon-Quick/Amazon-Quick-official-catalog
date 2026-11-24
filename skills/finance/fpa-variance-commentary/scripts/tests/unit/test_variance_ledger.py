"""
description: Unit tests for variance_ledger.check_ledger: pieces must add up to each line's variance, an Unexplained piece over the tolerance needs a named owner and a due date, every component line over the tolerance needs ledger rows, and the gross unexplained share is computed from material component lines. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

from variance_check import check
from variance_ledger import check_ledger

TABLE = (
    "line,type,parent,actual,comparison\n"
    "Contractor fees,cost,Operating expenses,2.9,2.2\n"
    "Travel,cost,Operating expenses,1.1,0.8\n"
    "Software licenses,cost,Operating expenses,1.6,1.9\n"
    "Salaries,cost,Operating expenses,12.4,12.4\n"
    "Operating expenses,cost,,18.0,17.3\n"
)
HEADER = "line,piece,amount,tag,evidence,outlook,owner,due\n"
GOOD = (
    HEADER
    + "Contractor fees,Contract overrun,0.7,Owner-stated,PMO lead 2026-11-03,one-time,PMO lead,2026-11-19\n"
    + "Travel,Travel overrun,0.3,Unexplained,Expense reports,unknown,Finance ops,2026-11-19\n"
    + "Software licenses,Renewal timing,-0.3,Unexplained,Renewal invoice,unknown,IT procurement,2026-11-19\n"
    + "Operating expenses,Total,0.7,Owner-stated,Sum of lines,unknown,Finance ops,2026-11-19\n"
)


class TestCheckLedger(unittest.TestCase):
    def setUp(self) -> None:
        self.report = check(TABLE, unit="M", materiality_abs=0.5)

    def test_good_ledger_passes_and_totals_material_lines(self) -> None:
        result = check_ledger(GOOD, self.report)
        self.assertEqual(result["status"], "PASS", result["faults"])
        self.assertAlmostEqual(result["gross_by_tag"]["Owner-stated"], 0.7)
        # Travel and licenses are material (over 2% of budget and 1% of the largest line).
        self.assertAlmostEqual(result["gross_by_tag"]["Unexplained"], 0.6)
        self.assertEqual(result["unexplained_share_pct"], 46.2)

    def test_pieces_that_do_not_add_up_fail(self) -> None:
        result = check_ledger(
            GOOD.replace("Contract overrun,0.7", "Contract overrun,0.6"), self.report
        )
        self.assertTrue(any("add up to 0.6" in f for f in result["faults"]))

    def test_placeholder_owner_fails(self) -> None:
        text = GOOD.replace(
            "Finance ops,2026-11-19\nSoftware",
            "[to confirm with requester],2026-11-19\nSoftware",
        )
        result = check_ledger(text, self.report)
        self.assertTrue(any("named owner" in f for f in result["faults"]))

    def test_netted_lines_are_caught(self) -> None:
        lines = GOOD.splitlines()
        netted = (
            "\n".join(
                [
                    lines[0],
                    lines[1],
                    lines[4],
                    "Other lines,Net of travel and licenses,0.0,Rounding,,unknown,,",
                ]
            )
            + "\n"
        )
        result = check_ledger(netted, self.report)
        self.assertTrue(
            any("'Travel'" in f and "no ledger rows" in f for f in result["faults"])
        )

    def test_bad_tag_and_outlook_fail(self) -> None:
        text = GOOD.replace("Owner-stated,PMO", "Guess,PMO").replace("one-time", "soon")
        self.assertEqual(len(check_ledger(text, self.report)["faults"]), 2)


if __name__ == "__main__":
    unittest.main()
