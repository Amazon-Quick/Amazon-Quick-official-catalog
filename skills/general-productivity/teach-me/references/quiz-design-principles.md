# Quiz Design Principles

Lookup data for the Generate workflow. The agent reads this file to select stem patterns and distractor strategies appropriate to the depth level and question type.

## Depth Levels

| Level | Label | Bloom's Tier | Tests |
|-------|-------|-------------|-------|
| L100 | Foundational | Remember | Recall of key terms, definitions, and basic facts. Vocabulary-level. Suitable for someone encountering the topic for the first time. |
| L200 | Practitioner | Understand / Apply | Understanding of how concepts relate, when to apply them, and common patterns. Requires comprehension beyond definitions. |
| L300 | Advanced | Analyze | Ability to analyze scenarios, compare approaches, identify trade-offs, and apply principles to novel situations. |
| L400 | Expert | Evaluate / Create | Synthesis across multiple concepts, edge cases, failure modes, architectural decisions, and the ability to evaluate competing solutions. |

## Question Writing Constraints

These constraints apply to ALL generated questions regardless of depth level:

1. **Positive phrasing only.** No double negatives, no "which is NOT" formulations, no trick questions.
2. **Single-claim T/F.** True/false questions must test exactly one factual claim. The statement must be unambiguous — no compound assertions joined by "and" or "or."
3. **MC structure.** Multiple choice questions must have exactly 4 options: one correct answer and three plausible distractors. No joke answers, no obviously wrong options, no "all of the above."
4. **No trivia at L200+.** Do not test dates, names, or isolated facts unless the depth level is L100. Higher levels test understanding, application, and analysis.
5. **T/F balance.** Aim for roughly 50/50 true vs. false correct answers. Avoid a bias toward "True" statements.
6. **Option consistency.** All options for a given question must be roughly the same length and grammatical structure. The correct answer must not be distinguishable by formatting alone.
7. **Stem independence.** The question stem should make sense on its own without requiring the reader to scan options for context. Avoid "Which of the following..." unless the options genuinely add value.

## Stem Patterns by Depth Level

Use these as structural templates. Replace bracketed terms with concepts from the source material.

### L100 (Remember)

| Pattern | Example |
|---------|---------|
| What is the definition of [term]? | What is the definition of a VPC? |
| [Term] refers to _____. | Elasticity refers to _____. |
| Which of the following best describes [concept]? | Which best describes eventual consistency? |
| [Statement about a fact]. True or False? | S3 provides unlimited storage capacity. True or False? |

### L200 (Understand / Apply)

| Pattern | Example |
|---------|---------|
| When would you use [X] instead of [Y]? | When would you use SQS instead of SNS? |
| What is the relationship between [A] and [B]? | What is the relationship between subnets and availability zones? |
| In which situation is [approach] most appropriate? | In which situation is read-replica scaling most appropriate? |
| [Scenario]. Which service applies here? | You need async decoupling between microservices. Which service applies? |

### L300 (Analyze)

| Pattern | Example |
|---------|---------|
| Given [scenario with constraints], which approach best addresses [concern]? | Given a multi-region app needing sub-100ms reads, which DB approach best addresses latency? |
| What trade-off does [decision] introduce? | What trade-off does choosing eventual consistency introduce? |
| Compare [A] and [B] in the context of [constraint]. Which is preferable? | Compare step functions and SQS for long-running orchestration. Which is preferable? |
| [Scenario]. What is the most likely failure mode? | A Lambda hits its concurrency limit during a traffic spike. What is the most likely failure mode? |

### L400 (Evaluate / Create)

| Pattern | Example |
|---------|---------|
| Which architectural decision simultaneously satisfies [constraint A], [B], and [C]? | Which decision satisfies low-latency, strong consistency, and multi-region availability? |
| [Complex scenario with multiple interacting systems]. What is the root cause of [symptom]? | An event-driven pipeline shows duplicate processing after a rebalance. What is the root cause? |
| Evaluate whether [proposed solution] is appropriate given [edge case]. Why or why not? | Is CQRS appropriate when the read model must reflect writes within 50ms? Why or why not? |
| [Design with a subtle flaw]. Identify the architectural issue. | A saga orchestrator calls all services synchronously and retries on timeout. Identify the issue. |

## Distractor Generation Strategies

Use these techniques to create plausible wrong answers. Select the strategy that matches the question's domain.

| Strategy | Description | When to use |
|----------|-------------|-------------|
| Adjacent concept | Use a related term from the same category | L100-L200: testing whether the user knows which specific term applies |
| Common misconception | Use what people commonly believe but is wrong | L200-L300: testing depth of understanding |
| Partial truth | State something that is true in a different context | L300-L400: testing precise applicability |
| Over-generalization | Broaden a specific claim to make it incorrect | L200-L400: testing boundary awareness |
| Reversed relationship | Swap cause and effect, or swap two related concepts | L200-L300: testing directional understanding |
| Outdated practice | Use something that was once correct but no longer is | L300-L400: testing current best practice knowledge |

## Hint Generation Patterns

Hints must help recall without revealing the answer. Use these patterns:

| Pattern | Example |
|---------|---------|
| Point to the concept area | "Think about how [topic] relates to [adjacent topic]." |
| Narrow the domain | "This is about [broad category], specifically the [sub-area]." |
| Provide a contrasting clue | "It's not about [common confusion] - focus on [correct direction]." |
| Reference the source context | "The source discusses this in the context of [section theme]." |
| Give a partial frame | "Consider what happens when [condition] is true." |

## Feedback Quality Checklist

When the agent writes explanations, each must satisfy:

1. States WHY the correct answer is right (not just "A is correct")
2. References the underlying principle or mechanism
3. For MC: explains why the most tempting distractor is wrong (one sentence)
4. Uses language from the source material where possible
5. Adds educational value beyond what the question itself tests
