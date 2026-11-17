"""
description: Score one eval iteration. Reads every run's grading.json and metrics.json, compares them with the last saved result, appends one line to evals/results.jsonl, and prints a plain-language scorecard. Run as: python create_benchmark.py <iteration_dir> <evals_dir> --model TIER.
last_updated: 2026-10-22
origin: original

Standard library plus pydantic (in the sandbox manifest). A single self-contained
file. Readers (I/O) load evals.json, the graded runs, and the previous result;
pure calculators turn them into scores; ResultRecordBuilder assembles the record;
ScorecardRenderer prints it; BenchmarkBuilder is the facade main() calls. Output
is UTF-8 with LF newlines so it is identical on Windows and macOS.

Layout expected (see references/evals.md):

    <skill>-workspace/iteration-N/
        eval-<case-id>/
            with_skill/run-1/     grading.json, metrics.json
            without_skill/run-1/  grading.json, metrics.json   (or old_skill/)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import logging
import random
import re
import statistics
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError


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
# The scorecard is printed without timestamps so it reads as one clean block.
scorecard_logger = logging.getLogger(f"{__name__}.scorecard")
_scorecard_handler = logging.StreamHandler(_PrintStream())
_scorecard_handler.setFormatter(logging.Formatter("%(message)s"))
scorecard_logger.addHandler(_scorecard_handler)
scorecard_logger.propagate = False

EVALS_FILE = "evals.json"
RESULTS_FILE = "results.jsonl"
SKILL_FILE = "SKILL.md"
GRADING_FILE = "grading.json"
METRICS_FILE = "metrics.json"
EVAL_PREFIX = "eval-"
RUN_PREFIX = "run-"
BOOTSTRAP_SAMPLES = 1000
# Fixed so the same runs always give the same margin of error.
BOOTSTRAP_SEED = 0
LOWER_PERCENTILE = 0.025
UPPER_PERCENTILE = 0.975
PERCENT = 100
ROUNDING = 3
CHECKSUM_RE = re.compile(r'^checksum\s*:\s*"?(sha256:[0-9a-f]{64})"?', re.M)
EXIT_BAD_INPUT = 2


class Config(StrEnum):
    """The run configurations an eval iteration can contain."""

    WITH_SKILL = "with_skill"
    WITHOUT_SKILL = "without_skill"
    OLD_SKILL = "old_skill"


# A run compares the skill against one baseline: no skill, or the prior version.
BASELINE_CONFIGS = (Config.WITHOUT_SKILL, Config.OLD_SKILL)


class CheckType(StrEnum):
    """What a check verifies."""

    OUTCOME = "outcome"
    PROCESS = "process"
    TRIGGERING = "triggering"


class Settings(BaseModel):
    """How the eval runs."""

    model_config = ConfigDict(extra="forbid")

    repeats: int = Field(default=3, ge=1)


class Targets(BaseModel):
    """The bars the scorecard reports against. Nothing blocks on them."""

    model_config = ConfigDict(extra="forbid")

    pass_rate: float = Field(default=0.9, ge=0, le=1)
    min_lift: float = 0.0
    max_regressions: int = Field(default=0, ge=0)
    consistency: float = Field(default=1.0, ge=0, le=1)


class CheckSpec(BaseModel):
    """One pass/fail check in evals.json."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: CheckType
    check: str = Field(min_length=1)


class CaseSpec(BaseModel):
    """One test case in evals.json."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    should_trigger: bool = True
    replies: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    checks: list[CheckSpec] = Field(min_length=1)


class EvalSuite(BaseModel):
    """The whole evals.json file."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str = Field(min_length=1)
    settings: Settings = Field(default_factory=Settings)
    targets: Targets = Field(default_factory=Targets)
    cases: list[CaseSpec] = Field(min_length=1)


class CheckGrade(BaseModel):
    """One check's verdict in a run's grading.json."""

    model_config = ConfigDict(extra="ignore")

    id: str
    passed: bool


class Grading(BaseModel):
    """A run's grading.json. Only the check verdicts are scored."""

    model_config = ConfigDict(extra="ignore")

    checks: list[CheckGrade]


class RunCost(BaseModel):
    """A run's metrics.json; a missing value stays absent."""

    model_config = ConfigDict(extra="ignore")

    tool_calls: int | None = None
    duration_seconds: float | None = None


class RunRecord(BaseModel):
    """One graded run of one case in one configuration."""

    case_id: str
    config: Config
    run: int
    grades: dict[str, bool]
    cost: RunCost


class CheckOutcome(BaseModel):
    """One check's verdict across all repeats of one configuration."""

    case_id: str
    check_id: str
    config: Config
    runs: list[bool]

    @property
    def key(self) -> str:
        return f"{self.case_id}/{self.check_id}"

    @property
    def passed_every_run(self) -> bool:
        return bool(self.runs) and all(self.runs)


class Effort(BaseModel):
    """Average cost of one run."""

    tool_calls: float | None = None
    duration_seconds: float | None = None


class ConfigScore(BaseModel):
    """Checks passed by one configuration, across every run."""

    passed: int
    total: int
    pass_rate: float | None
    effort: Effort


class Lift(BaseModel):
    """Points the skill adds over the baseline, with a 95% margin of error."""

    points: float
    margin: float

    @property
    def lower_bound(self) -> float:
        return self.points - self.margin


class Scores(BaseModel):
    """Every metric the scorecard reports."""

    with_skill: ConfigScore
    baseline_config: Config | None = None
    baseline: ConfigScore | None = None
    lift: Lift | None = None
    regressions: list[str]
    consistency: float | None
    previous_pass_rate: float | None = None
    tests_changed: bool = False


class TargetResults(BaseModel):
    """Whether each target was met; None when it could not be measured."""

    pass_rate: bool | None
    lift: bool | None
    regressions: bool
    consistency: bool | None


class Fingerprint(BaseModel):
    """What was tested: the skill version and the eval definitions."""

    skill_checksum: str | None
    evals_checksum: str


class ResultRecord(BaseModel):
    """One line of results.jsonl."""

    date: str
    skill: str
    skill_checksum: str | None
    evals_checksum: str
    model: str
    repeats: int
    scores: Scores
    targets: Targets
    targets_met: TargetResults
    checks: list[CheckOutcome]


class SuiteReader:
    """Reads and validates evals.json (I/O)."""

    def __init__(self, evals_path: Path) -> None:
        self.evals_path = evals_path

    def read(self) -> EvalSuite:
        """Return the parsed eval suite."""
        return EvalSuite.model_validate_json(
            self.evals_path.read_text(encoding="utf-8")
        )


class FingerprintReader:
    """Reads the skill checksum and hashes evals.json (I/O)."""

    def __init__(self, evals_dir: Path) -> None:
        self.evals_dir = evals_dir

    def read(self) -> Fingerprint:
        """Return the skill's stored checksum and a hash of evals.json."""
        skill_text = (self.evals_dir.parent / SKILL_FILE).read_text(encoding="utf-8")
        match = CHECKSUM_RE.search(skill_text)
        evals_bytes = (self.evals_dir / EVALS_FILE).read_bytes()
        return Fingerprint(
            skill_checksum=match.group(1) if match else None,
            evals_checksum=f"sha256:{hashlib.sha256(evals_bytes).hexdigest()}",
        )


class RunReader:
    """Reads every graded run under an iteration directory (I/O)."""

    def __init__(self, iteration_dir: Path) -> None:
        self.iteration_dir = iteration_dir

    def read(self) -> list[RunRecord]:
        """Return one record per run directory that has a grading.json."""
        records: list[RunRecord] = []
        for case_dir in sorted(self.iteration_dir.glob(f"{EVAL_PREFIX}*")):
            case_id = case_dir.name.removeprefix(EVAL_PREFIX)
            for config in Config:
                for run_dir in sorted((case_dir / config.value).glob(f"{RUN_PREFIX}*")):
                    record = self._read_run(case_id, config, run_dir)
                    if record is not None:
                        records.append(record)
        return records

    def _read_run(
        self, case_id: str, config: Config, run_dir: Path
    ) -> RunRecord | None:
        grading_path = run_dir / GRADING_FILE
        if not grading_path.is_file():
            logger.warning("No %s in %s", GRADING_FILE, run_dir)
            return None
        grading = Grading.model_validate_json(grading_path.read_text(encoding="utf-8"))
        metrics_path = run_dir / METRICS_FILE
        cost = (
            RunCost.model_validate_json(metrics_path.read_text(encoding="utf-8"))
            if metrics_path.is_file()
            else RunCost()
        )
        return RunRecord(
            case_id=case_id,
            config=config,
            run=int(run_dir.name.removeprefix(RUN_PREFIX)),
            grades={grade.id: grade.passed for grade in grading.checks},
            cost=cost,
        )


class PreviousResultReader:
    """Reads the last line of results.jsonl, if any (I/O)."""

    def __init__(self, results_path: Path) -> None:
        self.results_path = results_path

    def read(self) -> ResultRecord | None:
        """Return the most recent saved result, or None on the first run."""
        if not self.results_path.is_file():
            return None
        lines = [
            line
            for line in self.results_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return ResultRecord.model_validate_json(lines[-1]) if lines else None


class ResultAppender:
    """Appends one result as a line of results.jsonl (I/O)."""

    def __init__(self, results_path: Path, record: ResultRecord) -> None:
        self.results_path = results_path
        self.record = record

    def append(self) -> None:
        """Write the record as one JSON line at the end of the file."""
        with self.results_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(self.record.model_dump_json(exclude_none=True) + "\n")


class OutcomeCollector:
    """Groups run verdicts into one outcome per case, check, and configuration
    (pure). A check a run's grading leaves out counts as a fail."""

    def __init__(self, suite: EvalSuite, records: list[RunRecord]) -> None:
        self.suite = suite
        self.records = records

    def collect(self) -> list[CheckOutcome]:
        """Return the outcomes for every check that has at least one run."""
        outcomes: list[CheckOutcome] = []
        for case in self.suite.cases:
            for config in Config:
                runs = sorted(
                    (
                        r
                        for r in self.records
                        if r.case_id == case.id and r.config is config
                    ),
                    key=lambda record: record.run,
                )
                if not runs:
                    continue
                outcomes.extend(
                    CheckOutcome(
                        case_id=case.id,
                        check_id=check.id,
                        config=config,
                        runs=[run.grades.get(check.id, False) for run in runs],
                    )
                    for check in case.checks
                )
        return outcomes


class ConfigScorer:
    """Scores one configuration: checks passed and average effort (pure)."""

    def __init__(
        self, outcomes: list[CheckOutcome], records: list[RunRecord], config: Config
    ) -> None:
        self.outcomes = outcomes
        self.records = records
        self.config = config

    def score(self) -> ConfigScore:
        """Return passed and total check verdicts and average run cost."""
        verdicts = [v for o in self.outcomes if o.config is self.config for v in o.runs]
        runs = [r for r in self.records if r.config is self.config]
        return ConfigScore(
            passed=sum(verdicts),
            total=len(verdicts),
            pass_rate=round(sum(verdicts) / len(verdicts), ROUNDING)
            if verdicts
            else None,
            effort=Effort(
                tool_calls=self._mean([r.cost.tool_calls for r in runs]),
                duration_seconds=self._mean([r.cost.duration_seconds for r in runs]),
            ),
        )

    def _mean(self, values: list[float | None]) -> float | None:
        present = [v for v in values if v is not None]
        return round(statistics.mean(present), 1) if present else None


class LiftEstimator:
    """Estimates the points the skill adds over the baseline (pure).

    Pairs each check's with-skill pass share with its baseline pass share, takes
    the mean difference, and gets a 95% margin of error by resampling the checks
    BOOTSTRAP_SAMPLES times with a fixed seed.
    """

    def __init__(self, outcomes: list[CheckOutcome], baseline: Config) -> None:
        self.outcomes = outcomes
        self.baseline = baseline

    def estimate(self) -> Lift | None:
        """Return the lift, or None when no check ran in both configurations."""
        differences = self._paired_differences()
        if not differences:
            return None
        rng = random.Random(BOOTSTRAP_SEED)  # nosec B311  # statistics, not security
        means = sorted(
            statistics.mean(rng.choices(differences, k=len(differences)))
            for _ in range(BOOTSTRAP_SAMPLES)
        )
        low = means[int(LOWER_PERCENTILE * BOOTSTRAP_SAMPLES)]
        high = means[int(UPPER_PERCENTILE * BOOTSTRAP_SAMPLES) - 1]
        return Lift(
            points=round(statistics.mean(differences) * PERCENT, 1),
            margin=round((high - low) / 2 * PERCENT, 1),
        )

    def _paired_differences(self) -> list[float]:
        with_skill = self._shares(Config.WITH_SKILL)
        baseline = self._shares(self.baseline)
        return [
            with_skill[key] - baseline[key] for key in with_skill if key in baseline
        ]

    def _shares(self, config: Config) -> dict[str, float]:
        return {
            o.key: sum(o.runs) / len(o.runs)
            for o in self.outcomes
            if o.config is config and o.runs
        }


class RegressionFinder:
    """Lists checks that passed every run last time and do not now (pure)."""

    def __init__(
        self, outcomes: list[CheckOutcome], previous: ResultRecord | None
    ) -> None:
        self.outcomes = outcomes
        self.previous = previous

    def find(self) -> list[str]:
        """Return the case/check keys that got worse, sorted."""
        if self.previous is None:
            return []
        passed_before = {
            o.key
            for o in self.previous.checks
            if o.config is Config.WITH_SKILL and o.passed_every_run
        }
        return sorted(
            o.key
            for o in self.outcomes
            if o.config is Config.WITH_SKILL
            and o.key in passed_before
            and not o.passed_every_run
        )


class ConsistencyCalculator:
    """Share of cases whose every check passed on every with-skill run (pure)."""

    def __init__(self, outcomes: list[CheckOutcome]) -> None:
        self.outcomes = outcomes

    def calculate(self) -> float | None:
        """Return the consistent share of cases, or None with no runs."""
        cases: dict[str, bool] = {}
        for o in self.outcomes:
            if o.config is Config.WITH_SKILL:
                cases[o.case_id] = cases.get(o.case_id, True) and o.passed_every_run
        if not cases:
            return None
        return round(sum(cases.values()) / len(cases), ROUNDING)


class TargetJudge:
    """Marks each target met or not met (pure)."""

    def __init__(self, scores: Scores, targets: Targets) -> None:
        self.scores = scores
        self.targets = targets

    def judge(self) -> TargetResults:
        """Return met, not met, or None (not measurable) per target."""
        scores, targets = self.scores, self.targets
        pass_rate = scores.with_skill.pass_rate
        return TargetResults(
            pass_rate=None if pass_rate is None else pass_rate >= targets.pass_rate,
            lift=None
            if scores.lift is None
            else scores.lift.lower_bound > targets.min_lift,
            regressions=len(scores.regressions) <= targets.max_regressions,
            consistency=None
            if scores.consistency is None
            else scores.consistency >= targets.consistency,
        )


class ResultRecordBuilder:
    """Assembles the result record from the suite, runs, and history (pure)."""

    def __init__(
        self,
        suite: EvalSuite,
        records: list[RunRecord],
        previous: ResultRecord | None,
        fingerprint: Fingerprint,
        model: str,
        today: datetime.date,
    ) -> None:
        self.suite = suite
        self.records = records
        self.previous = previous
        self.fingerprint = fingerprint
        self.model = model
        self.today = today

    def build(self) -> ResultRecord:
        """Return the finished record."""
        outcomes = OutcomeCollector(self.suite, self.records).collect()
        scores = self._scores(outcomes)
        return ResultRecord(
            date=self.today.isoformat(),
            skill=self.suite.skill_name,
            skill_checksum=self.fingerprint.skill_checksum,
            evals_checksum=self.fingerprint.evals_checksum,
            model=self.model,
            repeats=max(record.run for record in self.records),
            scores=scores,
            targets=self.suite.targets,
            targets_met=TargetJudge(scores, self.suite.targets).judge(),
            checks=outcomes,
        )

    def _scores(self, outcomes: list[CheckOutcome]) -> Scores:
        baseline = next(
            (c for c in BASELINE_CONFIGS if any(o.config is c for o in outcomes)), None
        )
        tests_changed = (
            self.previous is not None
            and self.previous.evals_checksum != self.fingerprint.evals_checksum
        )
        # A run with different tests is not a fair comparison, so it is ignored.
        comparable = None if tests_changed else self.previous
        return Scores(
            with_skill=ConfigScorer(outcomes, self.records, Config.WITH_SKILL).score(),
            baseline_config=baseline,
            baseline=ConfigScorer(outcomes, self.records, baseline).score()
            if baseline
            else None,
            lift=LiftEstimator(outcomes, baseline).estimate() if baseline else None,
            regressions=RegressionFinder(outcomes, comparable).find(),
            consistency=ConsistencyCalculator(outcomes).calculate(),
            previous_pass_rate=comparable.scores.with_skill.pass_rate
            if comparable
            else None,
            tests_changed=tests_changed,
        )


class ScorecardRenderer:
    """Renders a result record as a plain-language scorecard (pure)."""

    def __init__(self, record: ResultRecord) -> None:
        self.record = record

    def render(self) -> str:
        """Return the scorecard text."""
        record, scores, met = self.record, self.record.scores, self.record.targets_met
        lines = [
            f"{record.skill} scorecard, {record.date} "
            f"(model {record.model}, {record.repeats} "
            f"{'repeat' if record.repeats == 1 else 'repeats'})",
            self._row(
                "Checks passed with the skill",
                self._share(scores.with_skill),
                f"target {self._percent(record.targets.pass_rate)}",
                met.pass_rate,
            ),
        ]
        if scores.baseline is not None:
            lines.append(
                self._row(
                    "Checks passed without the skill", self._share(scores.baseline)
                )
            )
        if scores.lift is not None:
            lines.append(
                self._row(
                    "Value the skill adds",
                    f"{scores.lift.points:+.0f} points (±{scores.lift.margin:.0f})",
                    f"target above {record.targets.min_lift:g}",
                    met.lift,
                )
            )
        lines.append(self._change_row())
        lines.append(
            self._row(
                "Got worse since last run",
                f"{len(scores.regressions)} checks",
                f"target {record.targets.max_regressions} or fewer",
                met.regressions,
            )
        )
        lines.extend(f"  - {key}" for key in scores.regressions)
        lines.append(
            self._row(
                "Cases that pass every repeat",
                self._percent(scores.consistency),
                f"target {self._percent(record.targets.consistency)}",
                met.consistency,
            )
        )
        lines.append(self._row("Effort per run", self._effort()))
        return "\n".join(lines)

    def _change_row(self) -> str:
        if self.record.scores.tests_changed:
            return self._row(
                "Change since last run", "tests changed since last run, not comparable"
            )
        previous = self.record.scores.previous_pass_rate
        current = self.record.scores.with_skill.pass_rate
        if previous is None or current is None:
            return self._row("Change since last run", "first saved run")
        change = (current - previous) * PERCENT
        return self._row(
            "Change since last run",
            f"{change:+.0f} points (was {self._percent(previous)})",
        )

    def _effort(self) -> str:
        parts = [f"{self._cost(self.record.scores.with_skill)} with the skill"]
        if self.record.scores.baseline is not None:
            parts.append(f"{self._cost(self.record.scores.baseline)} without")
        return "; ".join(parts)

    def _cost(self, score: ConfigScore) -> str:
        calls = score.effort.tool_calls
        seconds = score.effort.duration_seconds
        calls_text = "unknown tool calls" if calls is None else f"{calls:g} tool calls"
        seconds_text = "unknown time" if seconds is None else f"{seconds:g} s"
        return f"{calls_text}, {seconds_text}"

    def _share(self, score: ConfigScore) -> str:
        return f"{score.passed} of {score.total} ({self._percent(score.pass_rate)})"

    def _percent(self, value: float | None) -> str:
        return "n/a" if value is None else f"{value * PERCENT:.0f}%"

    def _row(
        self, label: str, value: str, target: str = "", met: bool | None = None
    ) -> str:
        verdict = {True: "met", False: "not met", None: "not measured"}[met]
        suffix = f"   {target}: {verdict}" if target else ""
        return f"{label + ':':<34}{value}{suffix}"


class BenchmarkBuilder:
    """Facade: read the runs and history, score them, save, and return the record."""

    def __init__(self, iteration_dir: Path, evals_dir: Path, model: str) -> None:
        self.iteration_dir = iteration_dir
        self.evals_dir = evals_dir
        self.model = model

    def build(self) -> ResultRecord:
        """Score the iteration, append it to results.jsonl, and return it."""
        records = RunReader(self.iteration_dir).read()
        if not records:
            raise ValueError(f"no graded runs found in {self.iteration_dir}")
        results_path = self.evals_dir / RESULTS_FILE
        record = ResultRecordBuilder(
            suite=SuiteReader(self.evals_dir / EVALS_FILE).read(),
            records=records,
            previous=PreviousResultReader(results_path).read(),
            fingerprint=FingerprintReader(self.evals_dir).read(),
            model=self.model,
            today=datetime.datetime.now(datetime.UTC).date(),
        ).build()
        ResultAppender(results_path, record).append()
        return record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score an eval iteration and append it to results.jsonl."
    )
    parser.add_argument("iteration_dir", help="Path to the iteration-N directory.")
    parser.add_argument("evals_dir", help="Path to the skill's evals/ directory.")
    parser.add_argument("--model", required=True, help="Model tier the runs used.")
    args = parser.parse_args()

    iteration_dir, evals_dir = Path(args.iteration_dir), Path(args.evals_dir)
    if not iteration_dir.is_dir() or not (evals_dir / EVALS_FILE).is_file():
        logger.error("Need an iteration directory and an evals/ folder with evals.json")
        return EXIT_BAD_INPUT

    try:
        record = BenchmarkBuilder(iteration_dir, evals_dir, args.model).build()
    except (ValueError, ValidationError) as exc:
        logger.error("%s", exc)
        return EXIT_BAD_INPUT

    logger.info("Appended result to %s", evals_dir / RESULTS_FILE)
    scorecard_logger.info("%s", ScorecardRenderer(record).render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
