# Pattern Examples

Before-and-after examples for each pattern category in the ruleset. Consult these when a rule's application to a specific sentence is unclear.

## Specificity Gaps

The transplant test detects them. If a sentence could appear unchanged in a document about a different subject, it is too vague.

Before: The team made significant progress on several key initiatives this quarter.
After: The payments team cut checkout latency from 900ms to 320ms and shipped the refund API on May 28.

Before: This tool offers powerful features that can dramatically improve your workflow.
After: The tool batches image exports, so a 40-file export that took 20 minutes by hand finishes in 2.

Before: Many users have reported issues with the new update.
After: Since the 3.2 release on June 2, 47 users have filed tickets about the login timeout.

## Punctuation

Before: The deploy failed — the config was missing — so we rolled back.
After: The deploy failed because the config was missing, so we rolled back.

Before: The fix is simple; update the dependency and rerun the build.
After: The fix is simple. Update the dependency and rerun the build.

Before: There is one blocker: the API key has expired.
After: The only blocker is an expired API key.

## Formulaic Transitions

Before: The cache reduces load times. Moreover, it cuts database costs. Furthermore, it simplifies the retry logic.
After: The cache reduces load times. It also cuts database costs, and because reads no longer hit the database, the retry logic got simpler too.

Before: In conclusion, the migration should be scheduled for Q3.
After: Schedule the migration for Q3.

## The Triple Beat

Before: The new system is fast, scalable, and reliable.
After: The new system handles 12,000 requests per second, four times the old peak.

Before: This approach saves time, reduces errors, and improves morale.
After: This approach saves each reviewer about an hour a day, mostly by eliminating the manual diff step.

## Parallel Construction Scaffolding

Before: It's not just a refactor, it's a redesign of the entire data layer.
After: This goes beyond a refactor. The entire data layer is redesigned.

Before: Not only does the script validate the input, but it also normalizes the output.
After: The script validates the input and normalizes the output.

## Copula Stacking

A run of more than two consecutive sentences with is, are, was, or were as the main verb reads like a series of definitions. Break it with subordination, active verbs, or inversion.

Before: Kubernetes is a container orchestration platform. It is widely adopted. The learning curve is steep. The community is active.
After: Kubernetes took over container orchestration because nothing else handled multi-node scheduling without a PhD in YAML. Most teams adopt it, suffer through the learning curve for about six months, then wonder how they lived without it.

Before: The cache is a Redis cluster. It is shared across services. The eviction policy is LRU. The hit rate is around 90 percent.
After: A shared Redis cluster backs the cache. Because eviction is LRU and the working set fits in memory, the hit rate stays around 90 percent.

## Sentence-Level Patterns

Before: Revenue grew 40% this quarter, highlighting the importance of the new pricing model.
After: Revenue grew 40% this quarter. Most of that growth traces to the new pricing model.

Before: The library serves as a bridge between the two systems.
After: The library translates events from the old queue format to the new one.

## Openings

Before: Thank you for your question about database indexing. Indexing is an important topic that many developers encounter. Let me explain how it works.
After: An index speeds up reads by letting the database skip rows that cannot match the query.

Before: In today's competitive job market, a strong resume is more important than ever.
After: Recruiters spend about seven seconds on a first resume scan, so the top third of the page decides whether they keep reading.

## Closings

Before: In summary, we covered the three main causes of the outage and the steps to prevent recurrence. I hope this analysis proves helpful for future incidents!
After: (Delete entirely. The analysis ended at the last finding.)

Before: Ultimately, the choice depends on your specific needs and circumstances.
After: Choose Postgres if you need transactions across tables. Choose DynamoDB if your access patterns are fixed and traffic is spiky.

## Hedging Stacks

Before: This change might potentially cause some issues with older clients in certain situations.
After: This change breaks clients on SDK versions below 2.4.

Before: It could arguably be suggested that the test coverage may be insufficient.
After: Test coverage is 41%, and the retry path has no tests at all.

## Bullet Abuse

Before:
- **Performance:** The system is faster.
- **Reliability:** It fails less often.
- **Cost:** It is cheaper to run.

After: The rewrite cut p99 latency from 2.1s to 400ms and halved the error rate. Hosting costs dropped about $3,000 a month because the old cluster was retired.

## Tone Calibration

Before: We're thrilled to announce an exciting new feature that will revolutionize how you manage your tasks!
After: Task lists now sync across devices. Changes appear on your other devices within a few seconds.

## Knowledge Tells

Before: There are several factors to consider when choosing a database, including performance, cost, scalability, and ease of use. Each option has its own advantages and disadvantages. It's recommended to consult with a database specialist before making a final decision.
After: For this workload, the deciding factor is the cross-table transaction in the checkout flow. That rules out the key-value options and points to Postgres.

## Assistant Patterns

Before: Great question! I'd be happy to help you with that. The function fails because the input is undefined. I hope this helps! Let me know if you have any questions.
After: The function fails because the input is undefined. The caller on line 42 passes the result of getUser, which returns undefined when the session has expired.
