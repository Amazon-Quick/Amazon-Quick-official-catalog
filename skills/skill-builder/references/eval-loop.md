# Eval Methodology

<purpose>
The eval-driven loop the Eval workflow runs. Read this when evaluating a skill. Grading detail is in `eval-grading.md`. Cross-run analysis is in `eval-analysis.md`.
</purpose>

<principle>
A skill that works on one prompt is not tested. Evals answer whether it works across varied prompts, on edge cases, and better than no skill at all. That last point matters most: if the model produces the same result without the skill, the skill is not earning its context.

Loop: write prompts, run the skill and a baseline on each, write assertions from what came back, grade, aggregate, read for patterns, improve. Assertions come after the first run, because you rarely know what good looks like until the skill has produced something.
</principle>

<phase_1>
**Write prompts.** Start with 2-3 test cases. Do not over-invest before the first results show what the skill does.

Each case is a realistic user message paired with a description of what success looks like. Vary them: mix casual and precise phrasing, cover at least one edge case (malformed input, unusual request, ambiguous instruction), and use real specifics (file paths, field names). "Process this data" tests nothing.

Write the prompts and `expected_output` into the existing `evals/evals.json`. Leave assertions out for now. Schema is in `<Definition - Evals>` in SKILL.md.
</phase_1>

<phase_2>
**Run baseline and skill.** Run each case twice: once with the skill, once without. The without-skill run is the baseline that shows what the skill adds.

Each run is its own background task, starting from clean context. A run that inherits the authoring conversation is not a real test, because the agent already knows the intent. Only an isolated run gives a trustworthy result.

1. `get_current_time` to mark the start.
2. `create_task_group` for the run.
3. For each case, `start_task` twice on the `smart` model with an isolated workspace: one told to load the skill, one told not to. Point each at its own output directory in the layout below. Instruct each task to write a `metrics.json` recording its tool-call counts and step count, and a short transcript of what it did.
4. `get_task_group_result` when the group resolves. `get_current_time` again to bound duration.
</phase_2>

<phase_3>
**Write assertions from outputs.** Now that runs produced real output, write assertions into `evals/evals.json` using the typed schema: each is `{type, check}` where type is `output`, `tool_call`, or `behavior`.

Strong assertions are specific and checkable: "file at outputs/report.md is valid", "search_messages was called with the escalation keyword", "user was asked to confirm before writing". Weak ones are vague ("output is good") or brittle (an exact phrase a correct output worded differently would fail).

Aim for discriminating assertions: pass when the skill genuinely succeeds, fail when it does not. One that passes for both the skill run and the baseline is testing the model, not the skill. Replace those.

Skip assertions for what resists pass/fail: writing style, visual polish, whether output feels right. Judge those by reading.
</phase_3>

<phase_4>
**Grade and aggregate.** Grade each run against its assertions, PASS or FAIL with cited evidence, as an isolated background task following `eval-grading.md`. Do not grade in the authoring session, where knowing the intent biases the verdict.

Once graded, run `scripts/eval_benchmark.py` over the grading files to build `benchmark.json`: pass rate, duration, and tool-call counts for each configuration, plus deltas.

Pass rate is the primary signal. Duration and tool-call counts are the cost proxies, since a skill that lifts pass rate but doubles the steps is a different trade-off from one that is better and leaner.
</phase_4>

<phase_5>
**Analyze and iterate.** Read `benchmark.json` for patterns the aggregates hide, following `eval-analysis.md`: assertions that never discriminate, evals that fail everywhere, high-variance evals, cost outliers.

Improve the skill based on the runs, the analysis, and the user's read of the outputs. Rerun, comparing against the prior version as baseline. Repeat until results satisfy you and the user, then expand the test set and run again at scale.

Show results each round and let the user steer. If they would rather judge by eye than run a full benchmark, do that.
</phase_5>

<workspace_layout>
Eval results go in a workspace beside the skill, never inside it. Each pass gets its own iteration folder:

```
skill-name/
├── SKILL.md
└── evals/evals.json
skill-name-workspace/
└── iteration-1/
    ├── eval-<case-name>/
    │   ├── with_skill/     (outputs/, metrics.json, grading.json)
    │   └── without_skill/  (outputs/, metrics.json, grading.json)
    └── benchmark.json
```

When improving an existing skill, snapshot the current version first and point the baseline at the snapshot, saving to `old_skill/` instead of `without_skill/`. That measures the new version against the real prior one, not against nothing.
</workspace_layout>

<improvement_principles>
When rewriting between iterations:

- Explain why a step matters instead of stacking absolute commands. A model that understands the reason handles cases the rules did not foresee.
- Keep the skill general, not pinned to the examples you tested.
- Cut what does not earn its place. A shorter skill the model follows beats a longer one it skims.
- Move repeated mechanical work into a script the skill calls, so it is deterministic and cheap rather than re-reasoned each run.
- Change one thing at a time, so the next benchmark attributes the effect to the right cause.
</improvement_principles>
