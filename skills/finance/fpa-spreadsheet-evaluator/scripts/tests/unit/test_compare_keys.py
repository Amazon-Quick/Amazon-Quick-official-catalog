"""
description: Unit tests for compare_keys: rows keyed by label, columns keyed by header, and finding identity that ignores numbers and addresses. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_keys as CK  # noqa: E402
from workbook_fixtures import load, prepare_finance, workbook_bytes  # noqa: E402


def model(labels):
    def build(ws, _wb):
        ws.title = "Calc"
        ws.append(["Line item", "Budget", "Actual"])
        for i, label in enumerate(labels, start=2):
            ws.append([label, i * 10, i * 11])

    wb = load(workbook_bytes(build))
    prepare_finance(wb)
    return wb.sheets["Calc"]


def key_of(sheet, label):
    keys = CK.row_keys(sheet)
    return next(keys[r] for r in keys if CK.row_label(sheet, r) == label)


class TestRowKeys(unittest.TestCase):
    def test_an_inserted_row_does_not_change_the_other_rows_keys(self) -> None:
        old = model(["Revenue", "Costs", "Profit"])
        new = model(["Revenue", "Marketing", "Costs", "Profit"])
        for label in ("Revenue", "Costs", "Profit"):
            with self.subTest(label=label):
                self.assertEqual(key_of(old, label), key_of(new, label))
        self.assertEqual(key_of(new, "Costs"), ("L", "costs", 1))

    def test_repeated_labels_are_numbered(self) -> None:
        s = model(["Total", "Other", "Total"])
        labels = [k for k in CK.row_keys(s).values() if k[0] == "L" and k[1] == "total"]
        self.assertEqual(labels, [("L", "total", 1), ("L", "total", 2)])


class TestColKeys(unittest.TestCase):
    def test_text_headers_become_header_keys(self) -> None:
        keys = CK.col_keys(model(["Revenue"]))
        self.assertEqual(keys[2], ("H", "budget", 1))
        self.assertEqual(keys[3], ("H", "actual", 1))


class TestFindingKey(unittest.TestCase):
    def test_numbers_in_the_description_do_not_change_identity(self) -> None:
        a = {
            "check": "sign_flip",
            "sheet": "Calc",
            "label": "Revenue",
            "description": "Was 10, now -5",
        }
        b = dict(a, description="Was 12, now -9")
        self.assertEqual(CK._fkey(a), CK._fkey(b))
        tab = {"check": "hidden_sheet", "sheet": "Old", "description": "x"}
        self.assertEqual(CK._fkey(tab, {"Old": "New"}), ("hidden_sheet", "New"))


if __name__ == "__main__":
    unittest.main()
