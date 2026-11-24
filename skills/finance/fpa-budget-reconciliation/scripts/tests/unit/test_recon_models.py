"""
description: Unit tests for recon_models: the spec rejects a reporting currency that is not a three-letter code and an unknown date order. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

from pydantic import ValidationError
from recon_models import ReconSpec

BASE = {
    "last_closed_period": "2026-09",
    "grain": ["department"],
    "sources": {"plan": {"path": "plan.csv"}, "actuals": {"path": "gl.csv"}},
}


class TestReconSpec(unittest.TestCase):
    def test_reporting_currency_with_markup_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ReconSpec.model_validate({**BASE, "reporting_currency": "<IMG SRC=X> "})

    def test_reporting_currency_is_normalized_to_upper_case(self) -> None:
        spec = ReconSpec.model_validate({**BASE, "reporting_currency": " eur "})
        self.assertEqual(spec.reporting_currency, "EUR")

    def test_unknown_date_order_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ReconSpec.model_validate({**BASE, "date_order": "year_first"})


if __name__ == "__main__":
    unittest.main()
