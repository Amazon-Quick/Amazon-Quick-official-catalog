#!/usr/bin/env python3
"""Aggregate eval run results into a benchmark.

Reads the per-run grading.json and metrics.json files produced by an eval
iteration and writes a benchmark.json summarizing pass rate, duration, and
tool-call counts for each configuration, plus the deltas between them.

Standard library only. No third-party packages.

Layout expected (see references/eval-loop.md):

    <skill>-workspace/iteration-N/
        eval-<case>/
            with_skill/     outputs/, metrics.json, grading.json
            without_skill/  outputs/, metrics.json, grading.json   (or old_skill/)
        benchmark.json   <- written here

Per-run inputs:
    grading.json  -> summary.pass_rate, summary.passed, summary.total
    metrics.json  -> total_tool_calls, total_steps, duration_seconds
                     (metrics.json is optional; missing fields count as absent,
                      never as zero, so they do not skew the means)

Usage:
    python eval_benchmark.py <iteration_dir>
    python eval_benchmark.py <iteration_dir> --out <path/to/benchmark.json>
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

# Configuration subdirectory names, in the order they should appear.
# "without_skill" is the from-scratch baseline; "old_skill" is the prior
# version baseline used when improving an existing skill. A given run uses
# one or the other, not both.
BASELINE_CONFIGS = ("without_skill", "old_skill")
CONFIG_ORDER = ("with_skill", "without_skill", "old_skill")


def load_json(path) -> dict | list | None:
    """Load a JSON file, returning None if it is missing or unparseable."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  warning: could not read {path}: {exc}", file=sys.stderr)
        return None


def collect_run(run_dir) -> dict:
    """Pull the metrics one run contributes from its grading and metrics files.

    Returns a dict with whatever is available. Missing values are left out
    rather than defaulted, so absent metrics do not distort the aggregates.
    """
    run = {}
    grading = load_json(run_dir / "grading.json")
    if grading and isinstance(grading.get("summary"), dict):
        summary = grading["summary"]
        if "pass_rate" in summary:
            run["pass_rate"] = summary["pass_rate"]
        if "passed" in summary:
            run["passed"] = summary["passed"]
        if "total" in summary:
            run["total"] = summary["total"]

    metrics = load_json(run_dir / "metrics.json")
    if metrics:
        if "total_tool_calls" in metrics:
            run["tool_calls"] = metrics["total_tool_calls"]
        if "total_steps" in metrics:
            run["steps"] = metrics["total_steps"]
        if "duration_seconds" in metrics:
            run["duration_seconds"] = metrics["duration_seconds"]

    return run


def summarize(values: list) -> dict | None:
    """Return mean/stddev/min/max for a list of numbers, or None if empty."""
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return {
        "mean": round(statistics.mean(nums), 3),
        "stddev": round(statistics.stdev(nums), 3) if len(nums) > 1 else 0.0,
        "min": min(nums),
        "max": max(nums),
        "n": len(nums),
    }


def summarize_config(runs: list) -> dict:
    """Summarize every metric across all runs of one configuration."""
    out = {}
    for metric in ("pass_rate", "tool_calls", "steps", "duration_seconds"):
        summary = summarize([r.get(metric) for r in runs])
        if summary is not None:
            out[metric] = summary
    return out


def delta(with_summary: dict, base_summary: dict) -> dict:
    """Signed mean differences (with_skill minus baseline) per metric."""
    out = {}
    for metric, ws in with_summary.items():
        bs = base_summary.get(metric)
        if bs is not None:
            out[metric] = round(ws["mean"] - bs["mean"], 3)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate eval runs into a benchmark."
    )
    parser.add_argument("iteration_dir", help="Path to iteration-N directory.")
    parser.add_argument(
        "--out",
        default=None,
        help="Output path (default: <iteration_dir>/benchmark.json).",
    )
    args = parser.parse_args()

    iteration_dir = Path(args.iteration_dir)
    if not iteration_dir.is_dir():
        print(f"error: not a directory: {iteration_dir}", file=sys.stderr)
        return 1

    eval_dirs = sorted(
        d for d in iteration_dir.iterdir() if d.is_dir() and d.name.startswith("eval-")
    )
    if not eval_dirs:
        print(f"error: no eval-* directories found in {iteration_dir}", file=sys.stderr)
        return 1

    runs = []  # flat list of every run, tagged by eval and config
    by_config = {}  # config name -> list of run metric dicts

    for eval_dir in eval_dirs:
        eval_name = eval_dir.name[len("eval-") :]
        for config in CONFIG_ORDER:
            run_dir = eval_dir / config
            if not run_dir.is_dir():
                continue
            metrics = collect_run(run_dir)
            if not metrics:
                print(f"  warning: no results in {run_dir}", file=sys.stderr)
                continue
            record = {"eval": eval_name, "configuration": config, **metrics}
            runs.append(record)
            by_config.setdefault(config, []).append(metrics)

    if not runs:
        print("error: no gradable runs found", file=sys.stderr)
        return 1

    run_summary = {
        config: summarize_config(rlist) for config, rlist in by_config.items()
    }

    # Delta compares with_skill against whichever baseline is present.
    deltas = {}
    if "with_skill" in run_summary:
        for base in BASELINE_CONFIGS:
            if base in run_summary:
                deltas[f"with_skill_vs_{base}"] = delta(
                    run_summary["with_skill"], run_summary[base]
                )

    benchmark = {
        "iteration": iteration_dir.name,
        "evals": [d.name[len("eval-") :] for d in eval_dirs],
        "configurations": [c for c in CONFIG_ORDER if c in by_config],
        "runs": runs,
        "run_summary": run_summary,
        "deltas": deltas,
    }

    out_path = Path(args.out) if args.out else iteration_dir / "benchmark.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(benchmark, handle, indent=2)
        handle.write("\n")

    # Console summary so the caller sees the headline without opening the file.
    print(f"Wrote {out_path}")
    for config in benchmark["configurations"]:
        pr = run_summary[config].get("pass_rate")
        if pr:
            print(f"  {config}: pass_rate mean={pr['mean']} (n={pr['n']})")
    for label, d in deltas.items():
        if "pass_rate" in d:
            print(f"  delta {label}: pass_rate {d['pass_rate']:+}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
