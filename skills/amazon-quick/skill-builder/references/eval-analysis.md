# Benchmark Analysis

<purpose>
How an analysis task reads a completed benchmark and surfaces patterns the aggregate numbers hide. Read by an isolated background task after grading and aggregation. The loop that invokes analysis is in `eval-loop.md`.
</purpose>

<role>
You read all runs in a benchmark and produce grounded observations. Notice patterns, do not fix them. Do not suggest skill edits. A pass rate of 0.7 says how often the skill succeeded. It does not say that one assertion never discriminates, that one eval is flaky, or that the skill doubled the tool calls for a small gain. Those are yours to surface.
</role>

<inputs>
Given in your task prompt:

- `benchmark_path`: the aggregated `benchmark.json` with every run result.
- `skill_path`: the skill under test, for context on what the runs were checking.
- `output_path`: where to write notes, as a JSON array of strings.
</inputs>

<what_to_look_for>
Read every run, not just the summary. Then work four lenses.

Per-assertion, across configurations:
- Passes in both with-skill and without-skill: testing the model, not the skill. Does not show value.
- Fails in both: the assertion may be broken, or the task beyond the model regardless of the skill.
- Passes with, fails without: the assertion earning its keep. Clear skill value.
- Passes without, fails with: the skill may be hurting on this dimension. Flag it plainly.
- Swings run to run in one configuration: flaky. The pass rate is not trustworthy yet.

Cross-eval:
- Some evals consistently harder or easier.
- Some stable, some swinging widely.
- Results that contradict what the skill's design predicts.

Cost, reading duration and tool-call counts:
- The skill materially increases duration or the number of tool calls.
- High variance across runs of one configuration.
- Outlier runs that skew the means.

The trade-off:
- State the quality gain against its cost plainly, so the user can weigh it. "Lifts pass rate from 35% to 85% but adds 6 tool calls per run" is the kind of sentence that lets someone decide.
</what_to_look_for>

<output_format>
Write `{output_path}` as a JSON array of strings. Each note is one specific observation grounded in a number or a concrete comparison. Do not speculate, and do not offer advice.

```json
[
  "Assertion 'output is valid JSON' passes 100% in both configurations, so it does not differentiate skill value.",
  "Eval 3 swings 50% plus or minus 40%: run 2 failed where 1 and 3 passed, so it may be flaky.",
  "Without-skill runs fail every tool_call assertion (0%) while with-skill runs pass all of them.",
  "The skill lifts pass rate 35% to 85% while adding 6 tool calls and 12s per run on average.",
  "All three without-skill runs for eval 1 produced empty output."
]
```
</output_format>

<guidelines>
- Ground every note in the data. If you cannot point to a number or a specific run, do not write it.
- Report what happened. Do not make a plan. Improvement decisions happen later, in the authoring session, informed by your notes.
- Prefer the non-obvious. The user can read the headline pass rate. Tell them what they would miss.
- One observation per note, so the user can act on them individually.
</guidelines>
