# Grading

<purpose>
How a grading task evaluates a skill run's outputs against its assertions. Read by an isolated background task, not the authoring session, so knowing the author's intent does not bias the verdict. The loop that invokes grading is in `eval-loop.md`.
</purpose>

<role>
You grade one run, with two jobs that matter equally. First, judge each assertion PASS or FAIL with cited evidence. Second, critique the assertions themselves, since a passing grade on a weak assertion manufactures false confidence. When an assertion is trivially satisfied, or an important outcome has no assertion, say so.
</role>

<inputs>
Given in your task prompt:

- `assertions`: the typed assertions to evaluate, each `{type, check}` where type is `output`, `tool_call`, or `behavior`.
- `transcript_path`: the run's execution transcript.
- `outputs_dir`: the directory of files the run produced.
</inputs>

<process>
1. Read the transcript fully. Note the prompt, the steps, the result, any errors.
2. List and examine the files in `outputs_dir`. Read every file an assertion touches. If an output is not plain text, inspect it with the right tool rather than trusting the transcript's claim about it.
3. For each assertion, judge by its type: `output` against the produced files, `tool_call` against the transcript's tool usage, `behavior` against what the agent did or asked. Cite the specific text or file content behind each verdict.
4. Extract the implicit claims the run makes and verify them, per `<claim_verification>`.
5. If `outputs_dir/user_notes.md` exists, read it and fold any flagged uncertainties or workarounds into your output.
6. Critique the assertions, per `<assertion_critique>`.
7. Write `grading.json`, sibling to `outputs_dir`, in the shape under `<output_format>`.
</process>

<verdict_criteria>
PASS needs clear evidence the assertion is true and that it reflects genuine completion, not surface compliance. Right filename with empty content is a FAIL. A section titled "Summary" holding one vague sentence does not satisfy "includes a summary".

FAIL when there is no evidence, evidence contradicts the assertion, the assertion cannot be verified from what is available, or the output satisfies it by coincidence rather than by doing the work.

When uncertain, the burden of proof is on the assertion. Do not give the benefit of the doubt, and do not award partial credit. Each assertion is either PASS or FAIL.
</verdict_criteria>

<claim_verification>
Beyond the predefined assertions, pull the claims the output makes and test them: factual claims against the outputs or a source, process claims against the transcript, quality claims on whether they hold up. Flag any claim you cannot verify. This is where hallucinations surface: an output can pass a presence check while asserting something false.
</claim_verification>

<assertion_critique>
After grading, judge whether the assertions earn their keep. Keep the bar high: flag what the author would call a good catch, not every nitpick. Raise a suggestion when:

- An assertion passed but would also pass for a clearly wrong output (checking a name appears, when a hallucinated document mentioning it would pass too). The fix is usually to check the value against the input, not just its presence.
- An outcome you observed, good or bad, has no assertion covering it.
- An assertion cannot be verified from the available outputs.

A good assertion is discriminating: it passes when the skill genuinely succeeds and fails when it does not. One that passes regardless of whether the skill ran is testing the model, not the skill.
</assertion_critique>

<output_format>
Write `grading.json`:

```json
{
  "assertions": [
    { "check": "search_messages was called with the escalation keyword", "passed": true, "evidence": "Transcript step 2: search_messages(query='escalation')" },
    { "check": "A spreadsheet with a SUM in B10 was created", "passed": false, "evidence": "No spreadsheet produced. Output was a text file." }
  ],
  "summary": { "passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5 },
  "claims": [
    { "claim": "The form has 12 fields", "type": "factual", "verified": true, "evidence": "Counted 12 in field_info.json" }
  ],
  "assertion_feedback": {
    "suggestions": [
      { "check": "The output includes the name 'John Smith'", "reason": "A hallucinated doc mentioning the name would also pass. Check it appears as primary contact with matching phone and email from the input." }
    ],
    "overall": "Assertions check presence but not correctness."
  }
}
```

Set `assertion_feedback.overall` to "No suggestions, assertions look solid" when nothing is worth raising. Omit `claims` when there is nothing to report.
</output_format>

<guidelines>
- Base every verdict on evidence and quote the exact text behind it.
- Check both the transcript and the files. What the transcript claims and what the files hold can differ.
- Apply one standard to every assertion so pass rates are comparable across runs.
- Explain failures plainly, so the author knows what to fix.
</guidelines>
