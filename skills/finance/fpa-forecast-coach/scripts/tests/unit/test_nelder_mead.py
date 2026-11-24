"""
description: Unit test for nelder_mead.minimize on an injected quadratic (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
from nelder_mead import minimize


class TestMinimize(unittest.TestCase):
    def test_finds_the_minimum_of_a_bowl(self) -> None:
        x, v = minimize(
            lambda p: float((p[0] - 3) ** 2 + (p[1] + 1) ** 2),
            np.array([0.0, 0.0]),
            np.array([1.0, 1.0]),
        )
        np.testing.assert_allclose(x, [3.0, -1.0], atol=1e-3)
        self.assertLess(v, 1e-5)


if __name__ == "__main__":
    unittest.main()
