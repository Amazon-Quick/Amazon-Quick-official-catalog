"""
description: Unit tests for render_report: sign-off question count, factual verdict text, HTML escaping and safe links, the external stylesheet. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_report as RR  # noqa: E402
import xlsx_capture  # noqa: E402


def setUpModule() -> None:
    xlsx_capture.start()


def tearDownModule() -> None:
    xlsx_capture.stop()


HOSTILE = "<img src=x onerror=alert(1)>'\"&"


def make_scan(
    findings=None, notes=None, sheet="Calc", workbook="model.xlsx", performance=None
):
    return {
        "workbook": workbook,
        "tabs": 1,
        "formulas": 3,
        "filled_cells": 12,
        "findings": findings or [],
        "notes": notes or [],
        "sheets": [
            {
                "sheet": sheet,
                "state": "visible",
                "role": "calculation",
                "rows": 4,
                "formulas": 3,
                "reads_from": [],
                "feeds": [],
            }
        ],
        "excel": {},
        "performance": performance
        or {"verdict": "healthy", "metrics": [], "reds": 0, "yellows": 0},
        "map": {"edges": [], "key_inputs": [], "key_outputs": []},
    }


def finding(**over):
    base = {
        "id": "F-001",
        "check": "hardcoded_in_formula",
        "group": "Hardcodes & consistency",
        "severity": "warning",
        "basis": "verified",
        "sheet": "Calc",
        "cell": "B2",
        "label": "Revenue",
        "description": "A typed number in a formula.",
        "fix": "Move it to an input cell.",
    }
    base.update(over)
    return base


def checklist(page):
    """The Excel download the page just rendered (read from the recorded bytes)."""
    return xlsx_capture.last_workbook()


def signoff(page):
    return {
        r[0]: r[1]
        for r in checklist(page)["Sign-off"].iter_rows(values_only=True)
        if r[0]
    }


class TestSignOffQuestions(unittest.TestCase):
    def test_judgment_saved_with_text_key_counts_as_open_question(self) -> None:
        page = RR.render(
            make_scan(),
            judgments=[{"sheet": "Calc", "cell": "B2", "text": "Is 400 intended?"}],
        )

        self.assertEqual(signoff(page)["Open questions for the owner"], 1)

    def test_judgment_saved_with_observation_key_fills_question_column(self) -> None:
        page = RR.render(
            make_scan(),
            judgments=[
                {"sheet": "Calc", "cell": "B2", "observation": "Q1 looks typed."}
            ],
        )
        rows = list(checklist(page)["Issues"].iter_rows(values_only=True))
        qcol = rows[0].index("Question for the owner")

        self.assertEqual(rows[1][qcol], "Q1 looks typed.")

    def test_scan_judgment_without_question_text_counts_by_basis(self) -> None:
        scan = make_scan([finding(basis="judgment", check="large_input_change")])

        self.assertEqual(signoff(RR.render(scan))["Open questions for the owner"], 1)


class TestVerdictText(unittest.TestCase):
    def test_clean_scan_states_counts_not_reassurance(self) -> None:
        page = RR.render(make_scan())

        self.assertIn(
            "The checks that ran found no open errors or risky formulas.", page
        )
        for phrase in (
            "Looks healthy",
            "all green",
            "Scorecard",
            "Healthy:",
            "should be enough",
        ):
            self.assertNotIn(phrase, page)

    def test_uncached_values_name_the_skipped_checks(self) -> None:
        notes = [
            {
                "note": "values_not_cached",
                "detail": "3 of 3 formulas have no saved result.",
            }
        ]

        page = RR.render(make_scan(notes=notes))

        self.assertIn(RR.VALUE_CHECKS_SKIPPED, page)

    def test_exceeded_performance_limits_are_counted(self) -> None:
        perf = {"verdict": "fixes", "metrics": [], "reds": 1, "yellows": 1}

        page = RR.render(make_scan(performance=perf))

        self.assertIn("2 performance limits exceeded; see the fixes listed.", page)

    def test_disclaimer_scopes_checks_and_rules_out_attestation(self) -> None:
        self.assertIn(
            "test formulas, arithmetic and data in the scanned range", RR.DISCLAIMER
        )
        self.assertIn(
            "not a financial statement audit or an internal-control attestation",
            RR.DISCLAIMER,
        )

    def test_page_makes_no_recalculation_or_product_claims(self) -> None:
        page = RR.render(make_scan([finding()]))

        for phrase in (
            "recalculated outside",
            "Values calculated by",
            "Quick",
            "Ember",
            "e.g.",
        ):
            self.assertNotIn(phrase, page)


class TestEscaping(unittest.TestCase):
    def setUp(self) -> None:
        scan = make_scan(
            [
                finding(
                    sheet=HOSTILE,
                    label=HOSTILE,
                    description=f'Text {HOSTILE} "\\u202e" here',
                    fix=HOSTILE,
                )
            ],
            sheet=HOSTILE,
            workbook=f"{HOSTILE}.xlsx",
        )
        self.page = RR.render(
            scan,
            narrative={
                "summary": HOSTILE,
                "purpose": "<script>alert(1)</script>",
                "impacts": {"F-001": HOSTILE},
            },
            judgments=[
                {
                    "title": "<script>x</script>",
                    "sheet": HOSTILE,
                    "question": "javascript:alert(1)",
                }
            ],
        )

    def test_workbook_and_agent_text_is_escaped(self) -> None:
        self.assertNotIn("<img", self.page)
        self.assertNotIn("<script", self.page)

    def test_only_links_are_data_downloads(self) -> None:
        hrefs = re.findall(r"href=[\"']([^\"']*)", self.page)

        self.assertEqual(len(hrefs), 2)
        self.assertTrue(all(h.startswith("data:") for h in hrefs))

    def test_download_names_cannot_break_out_of_the_attribute(self) -> None:
        names = re.findall(r'download="([^"]*)"', self.page)

        self.assertEqual(len(names), 2)
        self.assertTrue(all("<" not in n and "'" not in n for n in names))

    def test_bidi_control_in_quoted_fragment_stays_escaped(self) -> None:
        self.assertNotIn("\u202e", self.page)


class TestStylesheet(unittest.TestCase):
    def test_css_is_read_from_the_css_fence_only(self) -> None:
        text = "---\ndescription: x\n---\n# Style\n\n```css\n:root{--a:1}\nb{c:d}\n```\nafter\n"

        self.assertEqual(RR._load_css(text), ":root{--a:1}\nb{c:d}\n")

    def test_loaded_css_has_no_external_references(self) -> None:
        self.assertIn(":root{", RR.CSS)
        self.assertNotIn("url(", RR.CSS)
        self.assertNotIn("@import", RR.CSS)
        self.assertNotIn("```", RR.CSS)


if __name__ == "__main__":
    unittest.main()
