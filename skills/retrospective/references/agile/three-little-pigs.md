# Three Little Pigs

<Metadata>
Name: Three Little Pigs
Category: agile
Aliases: 3 Pigs Retrospective, Straw-Sticks-Bricks
Duration: 30-45 minutes
Team Size: 4-8 (max 10)
Best For: Assessing the robustness and maturity of team processes using a playful, engaging metaphor
Definition: A storytelling-based retrospective using the fairy tale of the Three Little Pigs where team members categorize their work practices by resilience (Straw for fragile, Sticks for partial, and Bricks for solid) to identify what needs strengthening to withstand pressure.
</Metadata>

<Gotchas>
1. Use when: Assessing the robustness/maturity of processes; technical debt discussions; after experiencing a failure that exposed fragility; team needs energy injection into retrospectives; teams that enjoy creative or playful formats
2. Do NOT use when: Very serious or sensitive situations (metaphor may feel inappropriate); team finds metaphors condescending or childish; deep interpersonal issues to address; team is too large for playful engagement (>10)
3. Everything in Bricks: Team isn't being honest about vulnerabilities. Fix: Challenge directly. Ask "Really? What happens when [wolf scenario] hits?"
4. Forgetting the Wolf: Without naming the pressure, the exercise is abstract. Fix: Always identify what's testing the houses. Make the threat specific and real.
5. No upgrade path: Identifying straw without planning how to strengthen it produces awareness without action. Fix: Focus on the upgrade PATH: Straw → Sticks → Bricks with specific next steps.
6. Metaphor fatigue: Some teams find this childish. Fix: Read the room; if engagement drops, pivot to straightforward language (fragile/partial/solid).
7. Binary thinking: Items are ONLY straw or bricks. Sticks is the nuanced middle where most real practices live. Fix: Emphasize Sticks as the important middle ground.
</Gotchas>

<Instructions>
<Workflow - Three Little Pigs
  description="Facilitation guide for Three Little Pigs retrospective."
>
1. [Setup] Draw three houses on the board: a straw house (wobbling), a stick house (standing but shaky), and a brick house (solid). Add a wolf on one side. Provide colored sticky notes (yellow=straw, brown=sticks, red=bricks). Allocate time: 3 min framing, 7 min categorization, 15 min discussion, 10 min upgrade planning, 5 min close.
2. [Open] (3 minutes)
   - Read the Prime Directive
   - Frame: "Everyone knows the story. Three pigs, three houses, and a wolf who huffs and puffs. Today, our practices are the houses. Some are straw, and they'll blow over under pressure. Some are sticks, OK but won't survive a real storm. And some are bricks, solid and reliable. Let's figure out which is which."
   - Optionally ask: "And who's our wolf? What pressures are testing our houses?"
3. [Stage: Categorize Practices] (7 minutes)
   - Purpose: Honestly assess the resilience of current team practices
   - Prompt: "Think about our processes, tools, and practices. Which are STRAW, fragile, temporary, held together with tape? Which are STICKS, working for now but wouldn't survive real pressure? Which are BRICKS, solid, proven, reliable under stress?"
   - Facilitation tip: Give concrete examples to get started: "Is our deployment process straw, sticks, or bricks? What about our documentation? Our testing?"
4. [Stage: Identify the Wolf] (3 minutes)
   - Purpose: Name the external pressures testing the team's practices
   - Prompt: "What's our wolf? What pressures, deadlines, or challenges are huffing and puffing at our houses? What could blow things down?"
   - Facilitation tip: The wolf adds urgency. It's not abstract, it's specific: "The Q4 scaling challenge" or "losing two team members next month."
5. [Stage: Share & Discuss] (10 minutes)
   - Purpose: Build shared understanding of practice maturity
   - Prompt: "Let's walk through each house. What did you put in Straw? Do others agree? What about Sticks? What's genuinely Brick-solid?"
   - Facilitation tip: Challenge everything in Bricks. Ask "Would this REALLY survive the wolf?" Teams tend to overestimate their brick items.
6. [Stage: Upgrade Planning] (10 minutes)
   - Purpose: Create a plan to strengthen fragile practices
   - Prompt: "Pick the most critical Straw item. What would it take to upgrade it to Sticks? To Bricks? What's the smallest investment for the biggest resilience gain?"
   - Facilitation tip: Focus on the upgrade PATH: Straw → Sticks → Bricks. Not everything needs to be Bricks immediately. What's the next step?
7. [Synthesize] Prioritize: Which straw items are most endangered by the wolf? Create an upgrade plan with specific next steps for 2-3 items.
8. [Close] (5 minutes)
   - Celebrate the Bricks: "These are our strengths. They've withstood the test."
   - Read the upgrade plan
   - Ask: "When the wolf comes next, which house are we standing in?"
   - Thank the team for honest assessment
</Workflow - Three Little Pigs>
</Instructions>

<Templates>
```markdown
# Three Little Pigs Retrospective
**Date:** [YYYY-MM-DD]
**Sprint/Iteration:** [name or number]
**Participants:** [list]

## 🐺 The Wolf (Pressures Testing Us)
- [External pressure or challenge]
- [External pressure or challenge]

## 🏚️ House of Straw (Fragile - won't survive pressure)
- [Fragile practice/process]
- [Fragile practice/process]
- [Fragile practice/process]

## 🏠 House of Sticks (Partial - needs reinforcement)
- [Partially strong practice]
- [Partially strong practice]
- [Partially strong practice]

## 🧱 House of Bricks (Solid - withstands challenges)
- [Proven, reliable practice]
- [Proven, reliable practice]
- [Proven, reliable practice]

## Upgrade Plan
| Practice | Current | Target | Next Step | Owner | Due Date |
|----------|---------|--------|-----------|-------|----------|
| [practice] | Straw | Sticks | [specific action] | [name] | [date] |
| [practice] | Sticks | Bricks | [specific action] | [name] | [date] |

## Resilience Assessment
- Overall maturity: [mostly straw / mixed / mostly bricks]
- Most endangered by wolf: [which straw item]
- Strongest asset: [which brick item]
```
</Templates>

<Resources>
- The wolf is KEY to making this actionable. Without named pressure, it's just a categorization exercise
- For technical teams, translate: "Straw = it works on my machine. Sticks = it works in CI. Bricks = it works in production at scale."
- Focus upgrade planning on Straw items that are MOST exposed to the wolf. Not all straw items are equally risky
- This format is excellent for tech debt discussions: "our test coverage is straw, our monitoring is sticks"
- Fun variant: After categorization, have the facilitator "huff and puff" by naming a specific scenario, then ask which houses survived
- For remote teams, use visual templates with three house images. The playful visuals maintain energy
</Resources>
