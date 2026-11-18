---
description: "Human-facing overview of the Quick Admin Onboarding Buddy skill: disclaimer, pre-requisites the agent verifies before running, the Region rule, installation pointers, skill layout, and where the backend lives."
last_updated: 2026-11-12
origin: original
---

# Quick Admin Onboarding Buddy

> **Disclaimer: shared "as is."** This content is provided on an "as is" basis,
> without warranties or conditions of any kind, express or implied. It is shared
> as a reference example only. You are solely responsible for reviewing,
> validating, testing, securing, and adapting it to your own environment,
> requirements, and policies before any use. Review all account/region values,
> secret names, IAM permissions, and other configuration referenced by the
> backend before deploying.
>
> Licensed under the MIT No Attribution license (MIT-0). See the `LICENSE` file
> at the root of the catalog repository.

An agent skill that guides an AWS Quick administrator end to end through
setting up knowledge bases, action connectors, and client-side extensions. It
runs as an ordered, phased workflow and applies every state-changing choice for
real through the Quick Admin Buddy MCP server backend.

The backend, an MCP server deployed to Amazon Bedrock AgentCore Runtime, lives
in a separate project, `aws-quick-admin-buddy-mcp`, in the
[AWS Quick knowledge hub](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/tree/main/infrastructure/aws-quick-admin-buddy-mcp).
Besides the MCP backend, its CloudFormation stack creates a published AWS Quick
chat agent, "Quick Setup Buddy", that answers setup questions and points admins
to this skill (see `<Definition - Backend>` in `SKILL.md`).

## Pre-requisites

The agent checks these before its main work. Required items block the
workflow, except that a missing Admin Onboarding Buddy Endpoint connector or
backend is set up by the skill's own workflows. Optional items only gate
specific phases.

| Dependency | Type | Connector | Runs | Required | Notes |
|---|---|---|---|---|---|
| AWS Quick admin access | Account role | None | Cloud | Required | You must be an administrator of the target AWS Quick account. |
| Admin Onboarding Buddy Endpoint | AWS Quick action connector (custom remote MCP, user-based OAuth) | `Admin Onboarding Buddy Endpoint` | Cloud | Required | The skill reaches the backend only through this connector, which must also be added to the AWS Quick desktop application. The skill verifies it first and, if it is missing, walks you through creating it. |
| Quick Admin Buddy MCP backend | Custom remote MCP server on Amazon Bedrock AgentCore Runtime, behind an AgentCore Gateway with a Cognito authorizer and DynamoDB state | Reached through `Admin Onboarding Buddy Endpoint` | Cloud (your AWS account, in `<quick-region>`) | Required | Source: the [backend project](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/tree/main/infrastructure/aws-quick-admin-buddy-mcp). If it is not deployed, the skill guides you through its deployment guide. |
| AWS permissions to deploy the backend | AWS permissions | None | Cloud | Required only if the backend is not deployed | Permission to create, through CloudFormation, the resources listed in the backend's template and deployment guide (IAM named roles, Cognito, DynamoDB, Amazon Bedrock AgentCore Runtime and Gateway, Lambda, ECR, KMS, Secrets Manager, and the AWS Quick chat agent). |
| Docker | Local tool | None | Your local machine | Required only for backend deploy | Builds and pushes the MCP server image (`linux/arm64`) to ECR before the stack is created. You run it; the skill never does. |
| Productivity integration tools (Gmail, Outlook, Drive, and so on) | AWS Quick action connectors | The action connectors you enable during onboarding | Cloud | Optional | Needed only for the read-only integration test at the end, which covers action connectors only. A missing tool is reported as blocked, with instructions to add it in the desktop application. |

### One Region

The backend stack, its Secrets Manager secrets, and any KMS keys must be in the
Region of your AWS Quick account. This skill's files write that Region as
`<quick-region>`. Use the same Region in OAuth `redirect_url` values
(`https://<quick-region>.quicksight.aws.amazon.com/sn/oauthcallback`).

When a connector uses a Secrets Manager secret, give the skill the secret's
name, not its ARN (Rule 9 in `SKILL.md`).

## Installation

- **Skill:** install it from the official catalog in the AWS Quick desktop
  application (see [Skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html)
  in the AWS Quick User Guide).
- **Backend:** build the image and deploy the stack by following the backend's
  [deployment guide](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/docs/deployment-guide.md),
  using its
  [CloudFormation template](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml)
  ([raw download](https://raw.githubusercontent.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml)).
  The skill's `aob deploy` command walks you through it; you run every command.
- **Connector:** create `Admin Onboarding Buddy Endpoint` from the stack
  outputs (the skill's Step 2), following the AWS Quick
  [MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html)
  guide, then add it in the desktop application
  ([connections](https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html)).
- **Tools and results:** the backend's
  [tool reference](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/docs/tool-reference.md)
  documents every tool, parameter, and result.

If the connector shows healthy but its actions fail, follow
`<Definition - Stale Connector Actions>` in `SKILL.md`.

## Layout

```
admin-onboarding-buddy/
├── SKILL.md                     # orchestrator: rules, definitions, workflows
├── assets/
│   ├── README.md                # this file
│   ├── help-menu.md             # the aob command menu
│   ├── user-cog.svg             # skill icon (Lucide)
│   ├── productivity-tool-auth-methods.md
│   ├── auth-secret-contract.md
│   └── knowledge-base-auth-and-acl.md
├── references/
│   ├── README.md                # connector capability matrix
│   ├── connectors/*.md          # one reference per connector and capability
│   └── steps/step-1..7-*.md     # detailed method for each workflow phase
└── evals/                       # eval cases, fixtures, and results
```

## Usage

Install the skill in the AWS Quick desktop application and ask, for example,
"help me set up Quick connectors", or type `aob help` for the command menu. The
skill starts by checking that the Admin Onboarding Buddy Endpoint connector is
available, then walks through the suite, action connectors, knowledge bases,
extensions, and an optional read-only integration test with a Word report.

## Backend

The backend MCP server, its CloudFormation template, and its deployment guide
are published only in the
[backend project](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/tree/main/infrastructure/aws-quick-admin-buddy-mcp);
this skill bundles no copy of them. The skill fetches the
[deployment guide](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/docs/deployment-guide.md)
and links the
[template](https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml)
when it walks an admin through deployment.
