# What is a Skill?

A skill is a folder with a `SKILL.md` file in it. That file contains step-by-step instructions that tell Amazon Quick how to do a specific task. You can think of it as domain expertise packaged up for the agent.

You can have dozens of skills installed without slowing anything down. Quick only reads the full instructions when it decides a skill is relevant to what you asked.

## What's inside a skill?

1. **Instructions** - The `SKILL.md` file. This is the brain. It tells Quick what to do, step by step.
1. **Tools** - Callable capabilities the skill makes available (sending a message, creating a file, hitting an API, etc.).
1. **Reference files** - Supporting docs, templates, or configs that the skill pulls in during execution.

## How does Quick decide when to use a skill?

Quick uses [progressive disclosure](https://agentskills.io/home#where-can-i-use-agent-skills). It does NOT load every skill into context at once.

1. **Discovery** - At startup, Quick reads only the `name` and `description` from each installed skill. That's all it needs to know what's available.
1. **Activation** - When your request matches a skill's description, Quick loads the full `SKILL.md` into the conversation. The skill's tools become callable.
1. **Execution** - Quick follows the workflow steps and calls tools. Reference files get read on demand, not all at once.

The `description` field is the single most important line in a skill. It's the only signal Quick uses to decide whether to activate a skill for a given request.

## Prerequisites

You need [Amazon Quick on desktop](https://docs.aws.amazon.com/quick/latest/userguide/amazon-quick-desktop.html) installed and signed in. If a skill depends on integrations (Outlook, Slack, etc.), connect those under **Settings > Capabilities > Connections** first.
