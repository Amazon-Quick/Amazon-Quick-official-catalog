"""
description: Unit tests for scan_model_map: tab roles and links, key inputs and outputs, and the time horizon read from period headers. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_model_map import model_map, sheet_map  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


def _two_tab_model(ws, wb):
    ws.title = "Inputs"
    ws["A1"], ws["B1"] = "Growth", 0.05
    calc = wb.create_sheet("Calc")
    for c, text in enumerate(("Item", "Jan", "Feb", "Mar"), 1):
        calc.cell(1, c, text)
    calc["A2"], calc["A3"] = "Revenue", "Total"
    for c in "BCD":
        calc[f"{c}2"] = "=100*(1+Inputs!$B$1)"
    calc["B3"] = "=SUM(B2:D2)"


class TestModelMap(unittest.TestCase):
    def setUp(self):
        self.wb = load(workbook_bytes(_two_tab_model))

    def test_sheet_map_gives_each_tab_a_role_and_its_links(self):
        roles = {t["sheet"]: t for t in sheet_map(self.wb)}
        self.assertEqual(roles["Inputs"]["role"], "inputs")
        self.assertEqual(roles["Inputs"]["feeds"], ["Calc"])
        self.assertEqual(roles["Calc"]["role"], "output")
        self.assertEqual(roles["Calc"]["reads_from"], ["Inputs"])

    def test_model_map_finds_links_key_cells_and_horizon(self):
        result = model_map(self.wb)
        self.assertEqual(result["edges"], [{"from": "Inputs", "to": "Calc", "refs": 3}])
        first_input = result["key_inputs"][0]
        self.assertEqual(
            (first_input["sheet"], first_input["cell"], first_input["used_by"]),
            ("Inputs", "B1", 3),
        )
        self.assertEqual(first_input["label"], "Growth")
        outputs = [(o["sheet"], o["cell"], o["label"]) for o in result["key_outputs"]]
        self.assertEqual(outputs, [("Calc", "B3", "Total")])
        self.assertTrue(result["time_horizon"].startswith("Monthly, Jan - Mar"))


if __name__ == "__main__":
    unittest.main()
