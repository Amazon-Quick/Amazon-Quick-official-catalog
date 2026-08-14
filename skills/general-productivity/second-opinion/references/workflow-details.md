# Workflow Details

Reference material for the Second Opinion Council skill. Loaded on demand during execution, not at activation.

## Diversity Measurement Algorithm (Post-Stage 1)

After all Stage 1 reviews arrive, measure pairwise similarity to detect low-diversity councils.

### Skip Condition

If fewer than 2 reviews completed successfully, skip diversity measurement entirely. Include a notice in the run report: "Diversity measurement skipped, insufficient reviews for comparison (need 2 or more)."

### Procedure

1. **Extract claim sets:** For each reviewer's structured output, collect the `claim` field value from every finding into a set.

2. **Normalize claims:** Before comparison, normalize each claim string:
   - Convert to lowercase
   - Collapse all consecutive whitespace into a single space
   - Trim leading/trailing whitespace

3. **Compute pairwise Jaccard similarity:** For each unique pair of reviewers (A, B):
   ```
   jaccard(A, B) = |claims_A intersection claims_B| / |claims_A union claims_B|
   ```
   - Two normalized claims match if they are identical strings after normalization
   - If both claim sets are empty, the score is 0.0
   - Result is always in [0.0, 1.0]

4. **Threshold check:** If any pair's similarity score exceeds 0.7, emit a warning:
   ```
   WARNING HIGH SIMILARITY: <reviewer_A> to <reviewer_B> = <score> (threshold: 0.7)
   Suggestion: Consider adding an MCP-connected model from a different model family
   to increase perspective diversity.
   ```

5. **Include pairwise matrix in run report:** Always list every pair and their score.

Proceed to Stage 2 regardless of diversity results. The measurement is diagnostic only.

## Stage 6: Capture Lessons (Full Procedure)

### 6a. Generate Run Metadata

1. **Run-ID**: Generate a UUID v4 (8-4-4-4-12 hex format).
2. **Timestamp**: Record current UTC time in ISO 8601 format (e.g., `2026-06-04T14:32:00Z`).

### 6b. Record Per-Stage Timing

Collect wall-clock duration in seconds for each stage (0 through 6). Record `0` for any stage whose timing was lost.

```json
{
  "stage-0": 45,
  "stage-1": 120,
  "stage-2": 90,
  "stage-3": 60,
  "stage-4": 30,
  "stage-5": 15,
  "stage-6": 20
}
```

### 6c. Append Run Record to run-history.jsonl

Append a single JSON object on one line to `scripts/run-history.jsonl` (relative to the skill's installed directory). Create the file if it does not exist.

Record format:
```json
{"run-id":"<uuid>","timestamp":"<iso8601>","council-size":3,"model-tiers-used":["smart","balanced","fast"],"changes-summary":"<max 280 chars>","stage-durations":{"stage-0":45,"stage-1":120,"stage-2":90,"stage-3":60,"stage-4":30,"stage-5":15,"stage-6":20}}
```

### 6d. Growth Cap Check on MODEL-NOTES.md

Before appending new lessons:

1. Count lines in MODEL-NOTES.md
2. Compare against cap (default: 300 lines; minimum: 50)
3. If over cap: identify stale sections (not updated in last 5 runs) and redundant sections. Present pruning proposal to user. If approved, consolidate to 80% of cap or below. If declined, append anyway with a warning.
4. If under cap: proceed directly.

### 6e. Reflect and Propose Updates

Evaluate:
- Which model tier produced the highest-ranked review?
- Any failures or degraded results?
- Briefing quality: did reviewers follow format instructions?
- Update reviewer-reliability table (avg street-cred, confirm-rate)

### 6f. Changelog Entry Format

```
- **YYYY-MM-DD** [run: <uuid> @ <timestamp>] - <description>
```

The uuid and timestamp must match the run-history.jsonl record for traceability.

## Scale-Down Behavior

- **1 reviewer**: Single thorough pass. Cross-review skipped. Orchestrator synthesizes.
- **2 reviewers**: Cross-review runs but ranking is thin (only 2 perspectives).
- **3 reviewers** (default): Full deep council with meaningful cross-review.
- **4-5 reviewers**: Extended council. More diverse but longer runtime.

## Red-Team Briefing Enhancement

When assigning a reviewer the red-team/contrarian role, add to their briefing:

```
ROLE: You are a contrarian reviewer. Your job is to find problems that other
reviewers will MISS because they are being too agreeable. Actively argue against
the material. Look for: hidden assumptions, unstated dependencies, scenarios
where this fails, claims without evidence, and optimistic projections without
downside analysis.
```

## Cross-Review Bundle Construction

- Always shuffle reviewer order to prevent first-position bias.
- Remove any identifying markers from reviews before bundling.
- Keep the bundle clean: just the reviews with letter labels, no meta-commentary.
- Rankings from smart tier tend to be most discriminating.
- Rankings from fast tier sometimes lack differentiation.
- When a ranking is unparseable, ask the judge to clarify rather than guessing.
