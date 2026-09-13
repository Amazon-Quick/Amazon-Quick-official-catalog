"""
description: Unit tests for create_benchmark.py. Filesystem-free: BenchmarkAssembler is fed an injected RunCollection, so aggregation, per-configuration summaries, and deltas are verified without reading any run directory.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from create_benchmark import BenchmarkAssembler, Config, RunCollection, RunResult


class TestBenchmarkAssembler(unittest.TestCase):
    def _collection(self) -> RunCollection:
        return RunCollection(
            eval_names=["alpha", "beta"],
            runs=[
                RunResult(
                    eval="alpha",
                    configuration=Config.WITH_SKILL,
                    pass_rate=1.0,
                    tool_calls=5,
                ),
                RunResult(
                    eval="beta",
                    configuration=Config.WITH_SKILL,
                    pass_rate=0.5,
                    tool_calls=7,
                ),
                RunResult(
                    eval="alpha",
                    configuration=Config.WITHOUT_SKILL,
                    pass_rate=0.5,
                    tool_calls=9,
                ),
                RunResult(
                    eval="beta",
                    configuration=Config.WITHOUT_SKILL,
                    pass_rate=0.5,
                    tool_calls=11,
                ),
            ],
        )

    def test_configurations_in_canonical_order(self) -> None:
        benchmark = BenchmarkAssembler("iteration-1", self._collection()).assemble()
        self.assertEqual(
            benchmark.configurations, [Config.WITH_SKILL, Config.WITHOUT_SKILL]
        )

    def test_pass_rate_mean_per_configuration(self) -> None:
        benchmark = BenchmarkAssembler("iteration-1", self._collection()).assemble()
        self.assertEqual(
            benchmark.run_summary[Config.WITH_SKILL]["pass_rate"].mean, 0.75
        )
        self.assertEqual(
            benchmark.run_summary[Config.WITHOUT_SKILL]["pass_rate"].mean, 0.5
        )

    def test_delta_with_skill_vs_without(self) -> None:
        benchmark = BenchmarkAssembler("iteration-1", self._collection()).assemble()
        self.assertEqual(
            benchmark.deltas["with_skill_vs_without_skill"]["pass_rate"], 0.25
        )

    def test_eval_names_preserved(self) -> None:
        benchmark = BenchmarkAssembler("iteration-1", self._collection()).assemble()
        self.assertEqual(benchmark.evals, ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
