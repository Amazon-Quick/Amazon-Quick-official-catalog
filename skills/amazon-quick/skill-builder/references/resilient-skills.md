# Resilient Skills

<purpose>
How to author a skill that survives the conditions it will actually run under: a long conversation where the agent starts skipping or repeating steps, a weaker model tier than the author assumed, and execution limits that cut long operations short. Read this when building or reviewing any multi-step skill.
</purpose>

<failure_modes>
Three conditions can degrade a skill at runtime. Design against each rather than assuming ideal conditions.

**Losing the thread in a long conversation.** As a conversation grows, an agent running a long workflow can start skipping steps, repeating them, or losing track of what it already finished. This environment provides a summarize_context tool precisely because sessions fill up. A skill cannot control how much conversation precedes it, so build it to be re-entered partway through.

**Model tier.** Background tasks accept a model tier (fast, balanced, or smart) through the start_task model parameter, so a skill sets the tier on the tasks it spawns. Do not assume the skill itself runs on a strong tier. A skill written to rely on smart-level inference can miss unstated rules when run on a weaker tier, so author steps explicitly enough that a fast-tier model could follow them.

**Execution limits.** Some operations run under a time limit (see the run_python Gotcha in SKILL.md). A step that batches all its work and writes only at the end loses everything if it hits a limit or is interrupted; a step that writes as it goes keeps what it finished.
</failure_modes>

<patterns>
Each pattern counters one or more of the failure modes. Design for them from the start, because retrofitting resilience into a finished skill is harder than building it in.

**Checkpoint to disk.** Write progress to a file as the workflow advances, not only at the end. A run that is interrupted, or a fresh session resuming after context got too long, can read the checkpoint and see what is done. The eval loop's per-iteration directories and incremental `metrics.json` are an example: each run's result lands on disk the moment it finishes.

**Make steps idempotent and resumable.** Begin a step by checking whether its output already exists. If it does, skip to the next. This lets a re-run or a new session pick up exactly where the last one stopped, instead of redoing work or double-writing. State the resume check explicitly in the step rather than assuming the model will infer it.

**Write incrementally.** Emit output per unit (per page, per record, per test case) rather than batching everything into a final write. Writing as you go enables checkpointing. It also holds the loss from any single interruption to one unit.

**Break long work into units.** Split a large operation into pieces small enough to each finish well inside any execution limit. This applies to code (long loops belong in bounded chunks) and to workflows (a self-contained step that finishes and checkpoints beats one sprawling step that may be cut off).

**Author for the weakest likely model.** Apply the explicitness the standard already requires (explicit actions, no reliance on unstated rules, and the validation and failure paths from Rule 12). When a step genuinely needs smart-level judgment, spawn it as a background task with the model set to smart via start_task's model parameter.

**Re-anchor in long workflows.** For a workflow with many steps, have the agent restate where it is and what remains at natural checkpoints. A brief "completed steps 1 to 4, now on step 5" keeps a long run from losing its place.
</patterns>

<when_to_apply>
Weigh resilience against a skill's shape. A short, single-shot skill needs little of this. The patterns earn their place as a skill gets longer, spawns background tasks, processes many items, or risks an execution limit. A fifty-step pipeline needs checkpointing and resumability; a three-step formatter does not.
</when_to_apply>
