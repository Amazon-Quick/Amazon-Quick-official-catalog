"""
description: Unit tests for run_reconciliation: the inspect count treats a line with several flags as one item, spec errors are reported without the submitted values, and a bad argument list returns 2. Filesystem-free.
last_updated: 2026-11-24
"""

import contextlib
import io
import unittest

from pydantic import ValidationError
from recon_models import FlagItem, ReconResult, ReconSpec, Tier
from result_factory import line, result
from run_reconciliation import describe_spec_problem, inspect_items, main


def flag(key: str, view: str, tier: Tier = Tier.INSPECT) -> FlagItem:
    return FlagItem(
        id="F",
        tier=tier,
        kind="overspend",
        view=view,
        key=key,
        keys={},
        amount=1.0,
        tests=["material"],
        reason="r",
        priority=1.0,
    )


class TestInspectItems(unittest.TestCase):
    def test_line_with_two_flags_counts_once(self) -> None:
        data = result(
            [line("Eng | 6200", 100.0, 200.0)],
            flags=[
                flag("Eng | 6200", "ytd"),
                flag("Eng | 6200", "current"),
                flag("Eng | 6200", "ytd", Tier.WATCH),
            ],
        )
        self.assertEqual(inspect_items(ReconResult.model_validate(data)), 1)


class TestDescribeSpecProblem(unittest.TestCase):
    def test_validation_error_does_not_echo_the_submitted_value(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            ReconSpec.model_validate({"grain": ["SUBMITTED-VALUE-123"], "sources": {}})
        text = describe_spec_problem(caught.exception)
        self.assertIn("last_closed_period: Field required", text)
        self.assertNotIn("SUBMITTED-VALUE-123", text)
        self.assertNotIn("https://", text)


class TestMain(unittest.TestCase):
    def test_missing_arguments_return_two(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
