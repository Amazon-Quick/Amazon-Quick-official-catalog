"""
description: Aggregate an eval iteration's per-run grading.json and metrics.json files into a benchmark.json summarizing pass rate, duration, and tool-call counts per configuration plus the deltas between them. Run as: python create_benchmark.py <iteration_dir> [--out PATH].
last_updated: 2026-09-13
origin: original

Standard library plus pydantic (in the sandbox manifest). A single self-contained
file: RunReader reads the runs from disk (I/O); BenchmarkAssembler turns injected
runs into the Benchmark model (pure, unit-tested); BenchmarkBuilder is the facade
that reads, assembles, and writes. The benchmark is written as UTF-8 with LF
newlines so output is identical on Windows and macOS.

Layout expected (see references/eval-loop.md):

    <skill>-workspace/iteration-N/
        eval-<case>/
            with_skill/     metrics.json, grading.json
            without_skill/  metrics.json, grading.json   (or old_skill/)
        benchmark.json   <- written here
"""

from __future__ import annotations

import argparse
import logging
import statistics
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger(__name__)


class Config(StrEnum):
    """The run configurations an eval iteration can contain."""

    WITH_SKILL = "with_skill"
    WITHOUT_SKILL = "without_skill"
    OLD_SKILL = "old_skill"


# "without_skill" is the from-scratch baseline; "old_skill" is the prior-version
# baseline used when improving a skill. A run uses one, not both.
BASELINE_CONFIGS = (Config.WITHOUT_SKILL, Config.OLD_SKILL)
CONFIG_ORDER = (Config.WITH_SKILL, Config.WITHOUT_SKILL, Config.OLD_SKILL)
SUMMARIZED_METRICS = ("pass_rate", "tool_calls", "steps", "duration_seconds")
GRADING_FILE = "grading.json"
METRICS_FILE = "metrics.json"
BENCHMARK_FILE = "benchmark.json"
EVAL_PREFIX = "eval-"
ROUNDING = 3


class GradingSummary(BaseModel):
    """The summary block of a grading.json; absent values stay None."""

    model_config = ConfigDict(extra="ignore")

    pass_rate: float | None = None
    passed: int | None = None
    total: int | None = None


class Grading(BaseModel):
    """A run's grading.json. Only the summary is used; other keys are ignored."""

    model_config = ConfigDict(extra="ignore")

    summary: GradingSummary | None = None


class Metrics(BaseModel):
    """A run's metrics.json; every field optional so a gap stays absent."""

    model_config = ConfigDict(extra="ignore")

    total_tool_calls: int | None = None
    total_steps: int | None = None
    duration_seconds: float | None = None


class RunResult(BaseModel):
    """One (eval, configuration) run's metrics. Absent metrics stay None and are
    dropped from the benchmark JSON via exclude_none."""

    eval: str
    configuration: Config
    pass_rate: float | None = None
    passed: int | None = None
    total: int | None = None
    tool_calls: int | None = None
    steps: int | None = None
    duration_seconds: float | None = None

    def has_data(self) -> bool:
        """True when the run recorded at least one metric worth aggregating."""
        return any(
            getattr(self, field) is not None
            for field in (
                "pass_rate",
                "passed",
                "total",
                "tool_calls",
                "steps",
                "duration_seconds",
            )
        )


class RunCollection(BaseModel):
    """The runs read from an iteration directory, with the eval names present."""

    eval_names: list[str]
    runs: list[RunResult]


class MetricSummary(BaseModel):
    """Descriptive statistics for one metric across a configuration's runs."""

    mean: float
    stddev: float
    min: float
    max: float
    n: int

    @classmethod
    def from_values(cls, values: list[float]) -> MetricSummary | None:
        """Summarize numeric values, or return None when there are none."""
        if not values:
            return None
        return cls(
            mean=round(statistics.mean(values), ROUNDING),
            stddev=round(statistics.stdev(values), ROUNDING)
            if len(values) > 1
            else 0.0,
            min=min(values),
            max=max(values),
            n=len(values),
        )


class Benchmark(BaseModel):
    """The aggregated result written to benchmark.json."""

    iteration: str
    evals: list[str]
    configurations: list[Config]
    runs: list[RunResult]
    run_summary: dict[Config, dict[str, MetricSummary]]
    deltas: dict[str, dict[str, float]]


class RunReader:
    """Reads an iteration directory's runs into a RunCollection (I/O)."""

    def __init__(self, iteration_dir: Path) -> None:
        self.iteration_dir = iteration_dir

    def read(self) -> RunCollection:
        """Read every eval-*/config run under the iteration directory."""
        eval_dirs = sorted(
            d
            for d in self.iteration_dir.iterdir()
            if d.is_dir() and d.name.startswith(EVAL_PREFIX)
        )
        runs: list[RunResult] = []
        for eval_dir in eval_dirs:
            eval_name = eval_dir.name[len(EVAL_PREFIX) :]
            for config in CONFIG_ORDER:
                run_dir = eval_dir / config.value
                if not run_dir.is_dir():
                    continue
                run = self._read_run(eval_name, config, run_dir)
                if not run.has_data():
                    logger.warning("No gradable results in %s", run_dir)
                    continue
                runs.append(run)
        return RunCollection(
            eval_names=[d.name[len(EVAL_PREFIX) :] for d in eval_dirs], runs=runs
        )

    def _read_run(self, eval_name: str, config: Config, run_dir: Path) -> RunResult:
        grading = self._parse(run_dir / GRADING_FILE, Grading)
        metrics = self._parse(run_dir / METRICS_FILE, Metrics)
        summary = grading.summary if grading else None
        return RunResult(
            eval=eval_name,
            configuration=config,
            pass_rate=summary.pass_rate if summary else None,
            passed=summary.passed if summary else None,
            total=summary.total if summary else None,
            tool_calls=metrics.total_tool_calls if metrics else None,
            steps=metrics.total_steps if metrics else None,
            duration_seconds=metrics.duration_seconds if metrics else None,
        )

    def _parse(self, path: Path, model: type[BaseModel]) -> BaseModel | None:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            return model.model_validate_json(text)
        except ValidationError as exc:
            logger.warning("%s did not match %s: %s", path, model.__name__, exc)
            return None


class BenchmarkAssembler:
    """Turns an injected RunCollection into a Benchmark (pure)."""

    def __init__(self, iteration_name: str, collection: RunCollection) -> None:
        self.iteration_name = iteration_name
        self.collection = collection

    def assemble(self) -> Benchmark:
        """Build the Benchmark from the collection's runs and eval names."""
        runs = self.collection.runs
        present = [c for c in CONFIG_ORDER if any(r.configuration is c for r in runs)]
        run_summary = {
            config: self._summarize([r for r in runs if r.configuration is config])
            for config in present
        }
        return Benchmark(
            iteration=self.iteration_name,
            evals=self.collection.eval_names,
            configurations=present,
            runs=runs,
            run_summary=run_summary,
            deltas=self._deltas(run_summary),
        )

    def _summarize(self, runs: list[RunResult]) -> dict[str, MetricSummary]:
        summaries = {}
        for metric in SUMMARIZED_METRICS:
            values = [v for r in runs if (v := getattr(r, metric)) is not None]
            summary = MetricSummary.from_values(values)
            if summary is not None:
                summaries[metric] = summary
        return summaries

    def _deltas(
        self, run_summary: dict[Config, dict[str, MetricSummary]]
    ) -> dict[str, dict[str, float]]:
        if Config.WITH_SKILL not in run_summary:
            return {}
        with_summary = run_summary[Config.WITH_SKILL]
        deltas = {}
        for base in BASELINE_CONFIGS:
            if base in run_summary:
                base_summary = run_summary[base]
                deltas[f"with_skill_vs_{base.value}"] = {
                    metric: round(ws.mean - base_summary[metric].mean, ROUNDING)
                    for metric, ws in with_summary.items()
                    if metric in base_summary
                }
        return deltas


class BenchmarkBuilder:
    """Facade: read runs, assemble the benchmark, and write it to disk."""

    def __init__(self, iteration_dir: Path, out_path: Path) -> None:
        self.iteration_dir = iteration_dir
        self.out_path = out_path

    def build(self) -> Benchmark:
        """Read, assemble, and write the benchmark; return it."""
        collection = RunReader(self.iteration_dir).read()
        if not collection.runs:
            raise ValueError("no gradable runs found")
        benchmark = BenchmarkAssembler(self.iteration_dir.name, collection).assemble()
        payload = benchmark.model_dump_json(indent=2, exclude_none=True) + "\n"
        self.out_path.write_text(payload, encoding="utf-8", newline="\n")
        return benchmark


def _log_summary(benchmark: Benchmark) -> None:
    """Log the pass-rate summary and deltas."""
    for config in benchmark.configurations:
        pass_rate = benchmark.run_summary[config].get("pass_rate")
        if pass_rate:
            logger.info(
                "%s: pass_rate mean=%s (n=%d)",
                config.value,
                pass_rate.mean,
                pass_rate.n,
            )
    for label, delta in benchmark.deltas.items():
        if "pass_rate" in delta:
            logger.info("delta %s: pass_rate %+g", label, delta["pass_rate"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate eval runs into a benchmark."
    )
    parser.add_argument("iteration_dir", help="Path to iteration-N directory.")
    parser.add_argument(
        "--out",
        default=None,
        help=f"Output path (default: <iteration_dir>/{BENCHMARK_FILE}).",
    )
    args = parser.parse_args()

    iteration_dir = Path(args.iteration_dir)
    if not iteration_dir.is_dir():
        logger.error("Not a directory: %s", iteration_dir)
        return 1

    out_path = Path(args.out) if args.out else iteration_dir / BENCHMARK_FILE
    logger.info("Aggregating eval runs in %s", iteration_dir)
    try:
        benchmark = BenchmarkBuilder(iteration_dir, out_path).build()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    logger.info("Wrote benchmark for %d runs to %s", len(benchmark.runs), out_path)
    _log_summary(benchmark)
    return 0


if __name__ == "__main__":
    sys.exit(main())
