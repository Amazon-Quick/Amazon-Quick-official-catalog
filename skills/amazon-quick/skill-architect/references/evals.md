---
description: "How to evaluate a skill: fixed checks, runs with and without the skill, grading, scoring over time, and reading the results."
last_updated: 2026-10-22
origin: original
---

# Evals

<purpose>

The method the Eval workflow follows, from defining checks to reading the scorecard. A grading task reads only `<step-3-grade>`. The evals.json schema is `<Definition - Evals>` in SKILL.md.

</purpose>

<what-we-measure>

Whether the skill makes the agent do the job right, compared with the same agent without the skill. Every case has pass/fail checks of three kinds: outcome (the result is correct), process (the right steps happened), and triggering (the skill activated when it should and stayed off when it should not).

`scripts/create_benchmark.py` computes these metrics for each eval run and saves them as one line of `evals/results.jsonl`:

- Pass rate with the skill: checks passed divided by checks run, across every with-skill run.
- Pass rate without the skill: the same, for the baseline runs.
- Lift: the with-skill pass rate minus the baseline pass rate, in points, with a 95% margin of error from resampling the checks.
- Regressions: checks that passed on every run last time and do not now. Only compared when the tests are unchanged (same `evals_checksum`); otherwise the scorecard says the runs are not comparable.
- Consistency: the share of cases whose every check passed on every repeat.
- Effort: average tool calls and seconds per run.

The scorecard compares each metric with the user's targets in evals.json and marks it met or not met. It never blocks anything.

</what-we-measure>

<step-1-define>

**Define the cases and checks before any run,** in `evals/evals.json`, and have the user review them. Checks stay fixed between runs so every run measures the same thing. Change a check only on purpose, with a new id if its meaning changes.

Good cases are realistic user messages with real specifics (file paths, field names). Mix casual and precise phrasing, include at least one edge case, and include at least one negative control (`should_trigger: false`). Never name the skill in a prompt, or the run cannot show whether the description triggers it.

Good checks pass when the skill does the job and fail when it does not. A check the agent alone would pass tests the model, not the skill. Leave out what resists pass/fail, such as tone, and note it in the optional summary instead.

When a case would call a connector or Quick data (a space, a knowledge base, a dashboard), put a canned response in `evals/files/` and list it in the case's `files`. The run reads it instead of calling the live service, so results do not drift and nothing real is sent. Check write actions as intent ("prepared a message to #channel"), never as a sent message.

</step-1-define>

<step-2-run>

**Run every case with and without the skill, in two background tasks.** Neither task has seen this conversation, so neither knows the author's intent.

- With-skill task: give it every case's `prompt` and `replies`, never the checks. The skill is installed. For each case, the task treats the prompt as a new conversation, decides from the skill's description alone whether to load it, and carries nothing over from earlier cases.
- Without-skill task: the same prompts, with an instruction not to load the skill. Leave out negative controls. When improving an existing skill, this task uses the prior version and saves under `old_skill/`. The baseline depends only on the prompts, so reuse the last baseline when no prompt or reply has changed.
- Both tasks: pass `tools="all"`, `share_workspace=False`, and `fork=False`, so each has the full toolset, its own workspace, and no conversation history. Set `model` and `thinking_effort` from the skill's frontmatter. `start_task` accepts only `fast`, `balanced`, or `smart`, so a skill set to `auto` runs at `smart`. Start the two tasks one after the other.
- When a case has `replies`, the task uses them in order as the user's answers. When it asks a question with no reply left, that case stops there. The task declines run metrics when asked, so the replies go to the skill's own questions.
- For each case, the task saves its outputs, a short transcript, and a `metrics.json` with `tool_calls` and `duration_seconds` under `eval-<case-id>/<config>/run-1/`. When `settings.repeats` is above 1, run the with-skill task again, saving `run-2/`, `run-3/`.

Later cases in a task have seen earlier ones, so triggering and consistency results are less reliable than fully isolated runs. When one of those checks matters, rerun that case alone in its own task.

Run the whole set before changing the skill. Changing the skill after one case and re-running only that case hides regressions elsewhere.

</step-2-run>

<step-3-grade>

**Grade every run in one background task on `smart`,** never in the authoring session and never on a weaker model. The grading task gets each case's `checks`, and each run's transcript and outputs folder, and does the following for every run:

1. Read the transcript fully, then read every output file a check touches. Inspect a non-text file with the right tool rather than trusting the transcript.
2. Judge each check: `outcome` against the files and final answer, `process` against the steps and tool calls, `triggering` against whether the skill was loaded. Quote the evidence.
3. PASS needs clear evidence that the run did the work. A file with the right name and no content is a FAIL. When unsure, FAIL. There is no partial credit.
4. Note any claim in the output you can check against the inputs, such as a count or a name, and whether it holds.
5. Flag a weak check only when it would also pass for a clearly wrong output, or when something important happened that no check covers.
6. Write `grading.json` next to the outputs folder:

```json
{
  "checks": [
    { "id": "routes-to-plan", "passed": true, "evidence": "Transcript step 2: 'Routing to Plan'" },
    { "id": "suggests-names", "passed": false, "evidence": "Only one name was suggested" }
  ],
  "claims": [{ "claim": "The runbook has 5 steps", "verified": true }],
  "suggestions": [{ "id": "suggests-names", "reason": "Passes for any names; check each is kebab-case" }]
}
```

Every check gets one entry, matched by `id`; a missing entry counts as a FAIL. Omit `claims` or `suggestions` when there is nothing to report.

</step-3-grade>

<step-4-score>

**Score the iteration** with `python scripts/create_benchmark.py <iteration_dir> <skill>/evals --model <tier>`. It appends one line to `evals/results.jsonl` and prints the scorecard.

</step-4-score>

<reading-the-results>

Read the new line of `results.jsonl` and the ones before it. Its `checks` list has every check's result on every repeat, per configuration. Report notes, each tied to a number or a named case and check, and leave fixes to the user:

- Checks that pass with and without the skill test the model, not the skill.
- Checks that fail in both may be broken, or the task is beyond the model.
- Checks that pass without the skill and fail with it mean the skill may be hurting. Say so plainly.
- Checks that pass on some repeats and fail on others are flaky.
- A changed `evals_checksum` means the tests changed, so scores are not directly comparable with the last line.
- State the cost of the gain, for example "lifts pass rate 35 points but adds 6 tool calls per run".
- With few checks, the margin of error is wide; say how many checks a number rests on.

Show the user the scorecard and the notes, and let them decide whether to change the skill, keep it, or add cases.

</reading-the-results>

<workspace-layout>

Run outputs go in a workspace beside the skill, never inside it:

```
skill-name/
└── evals/
    ├── evals.json
    ├── results.jsonl
    └── files/
skill-name-workspace/
└── iteration-1/
    └── eval-<case-id>/
        ├── with_skill/run-1/     (outputs/, transcript, metrics.json, grading.json)
        └── without_skill/run-1/  (or old_skill/run-1/)
```

Delete `skill-name-workspace/` once the result is saved, and never commit it. Only `evals/` is kept: `evals.json`, `results.jsonl`, `evals/files/`, and an optional `eval_result_<date>.md` summary that must not point at workspace paths (Rule 9).

</workspace-layout>

<improving-the-skill>

- Explain why a step matters instead of stacking absolute commands.
- Keep the skill general, not pinned to the tested examples.
- Cut what does not earn its place. A shorter skill the model follows beats a longer one it skims.
- Move repeated mechanical work into a script.
- Change one thing at a time, so the next scorecard shows what caused the change.

</improving-the-skill>
