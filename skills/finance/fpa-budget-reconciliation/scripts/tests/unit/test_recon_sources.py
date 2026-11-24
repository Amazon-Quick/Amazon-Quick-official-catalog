"""
description: Unit tests for recon_sources.SourceNormalizer on tables built in the test: amounts with currency codes are read, unreadable amounts are reported and left out, and missing columns are quoted as file data. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

import pandas as pd
from recon_models import Finding, SourceSpec, SpecError
from recon_parsing import PeriodParser
from recon_sources import SourceNormalizer

COLUMNS = {"department": "Dept", "period": "Month", "amount": "Amount"}


def normalize(rows: list[dict], findings: list[Finding]) -> pd.DataFrame:
    spec = SourceSpec(path="gl.csv", columns=COLUMNS)
    normalizer = SourceNormalizer("actuals", spec, PeriodParser(1, "end"), findings)
    return normalizer.normalize(pd.DataFrame(rows, dtype=object))


class TestSourceNormalizer(unittest.TestCase):
    def test_amount_with_currency_code_is_counted(self) -> None:
        findings: list[Finding] = []
        out = normalize(
            [
                {"Dept": "Eng", "Month": "2026-01", "Amount": "500 EUR"},
                {"Dept": "Eng", "Month": "2026-01", "Amount": "1,000"},
            ],
            findings,
        )
        self.assertEqual(float(out["amount"].sum()), 1500.0)
        self.assertEqual(findings, [])

    def test_unreadable_amount_is_reported_not_zeroed(self) -> None:
        findings: list[Finding] = []
        out = normalize(
            [
                {"Dept": "Eng", "Month": "2026-01", "Amount": "n/a"},
                {"Dept": "Eng", "Month": "2026-01", "Amount": "10"},
            ],
            findings,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(findings[0].code, "actuals_number_unreadable")
        self.assertEqual(findings[0].count, 1)

    def test_missing_column_message_marks_file_text_as_data(self) -> None:
        with self.assertRaises(SpecError) as caught:
            normalize([{"Dept": "Eng", "Month": "2026-01"}], [])
        self.assertIn("DATA (untrusted, from file)", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
