---
description: "Each dependency type a skill's README can list, what it is, and the AWS Quick User Guide page to link it to."
last_updated: 2026-11-18
sources:
  - https://docs.aws.amazon.com/quick/latest/userguide/toc-contents.json
  - https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html
  - https://docs.aws.amazon.com/quick/latest/userguide/working-with-spaces.html
---

# Dependencies

<purpose>
The README's Pre-requisites table gives each dependency one of these types and a link to its page, so the user knows what to set up and where to read how. Plan uses this file to record each dependency, and Audit checks the README against it.
</purpose>

<types>
Each Type value, what it is, and the page to link when no more specific page exists:

| Type | What it is | Link |
| --- | --- | --- |
| `SPACE` | A collection of files and AWS Quick resources: dashboards, datasets, Dataset Q&A, knowledge bases, and action connectors | [Spaces](https://docs.aws.amazon.com/quick/latest/userguide/working-with-spaces.html) |
| `DATASET` | A Quick Sight dataset, reached directly or through a space | [Datasets](https://docs.aws.amazon.com/quick/latest/userguide/working-with-datasets.html) |
| `TOPIC` | A legacy Topic, a semantic model over datasets. Only for a skill that already uses one: a new skill asks questions of its datasets through a space | [Topics](https://docs.aws.amazon.com/quick/latest/userguide/topics.html) |
| `DASHBOARD` | A Quick Sight dashboard | [Dashboards](https://docs.aws.amazon.com/quick/latest/userguide/working-with-dashboards.html) |
| `KNOWLEDGE_BASE` | Content brought in from an outside source for retrieval | [Knowledge bases](https://docs.aws.amazon.com/quick/latest/userguide/knowledge-base-integrations.html) |
| *ConnectorType value*, such as `SLACK` | A built-in connector from the catalog, reachable from web, mobile, and desktop. Use the exact value from references/connector-types.json, the same one a plugin's connector slot uses | That entry's `docs` link |
| `CLOUD_CONNECTOR_CUSTOM_MCP` | A remote MCP server an owner sets up as a cloud connector | [MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html) |
| `CLOUD_CONNECTOR_CUSTOM_OPENAPI` | An API set up as a connector from an OpenAPI specification | [OpenAPI integration](https://docs.aws.amazon.com/quick/latest/userguide/openapi-integration.html) |
| `LOCAL_CONNECTOR_MCP_LOCAL` | An MCP server that runs as a command on the user's machine | [Local connectors](https://docs.aws.amazon.com/quick/latest/userguide/local-connectors.html) |
| `LOCAL_CONNECTOR_MCP_REMOTE` | An MCP server at a URL that only this user connects to from desktop | [Local connectors](https://docs.aws.amazon.com/quick/latest/userguide/local-connectors.html) |
| `LOCAL_CONNECTOR_ACP` | A coding agent, such as Kiro, connected through the Agent Client Protocol (ACP) | [Coding agents](https://docs.aws.amazon.com/quick/latest/userguide/coding-agents.html) |
| `SYSTEM_TOOL` | A built-in tool, such as code execution, which a user or administrator can turn off | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |
| `SKILL` | Another skill the workflows load | [Skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html) |
</types>

<links>
Link each dependency to the most specific page that tells the user how to set it up:

- For a built-in cloud connector, use the `docs` link for its type in references/connector-types.json.
- For a custom MCP server or API, link the server's own setup or deployment guide, and add that link to `<Resources>`. Never copy its steps into the skill, because copies drift from the server they describe.
- Otherwise, link the page in the table above.
</links>
