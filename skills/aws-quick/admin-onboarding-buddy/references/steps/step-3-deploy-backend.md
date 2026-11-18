---
description: "Detailed method for <Workflow - Deploy Backend>: advisory-only guidance to build the MCP image and deploy the backend's CloudFormation template by following its deployment guide."
last_updated: 2026-11-12
origin: original
---

# Step 3: Deploy the Onboarding Buddy backend

**Mode:** agentic, advisory only. **Entry:** from Step 2 when the backend stack
is unknown or not deployed, or on `aob deploy`. **Next:** back to
[Step 2](step-2-configure-connector.md) to configure the connector against the
deployed stack.

## Goal

Help the admin stand up the Quick Admin Buddy backend so the custom MCP
connector has something to talk to. This phase explains the backend, confirms
the prerequisites, and guides the admin through deploying the backend's
CloudFormation template.

## Sources

The backend repository owns every deployment detail. Fetch the deployment guide
at the start of this phase and take commands, parameters, outputs,
troubleshooting, and teardown from it:

- Deployment guide (build and push commands, "Stack parameters" table, "Stack
  outputs" table, updating, logs and debugging, teardown):
  https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/docs/deployment-guide.md
- Template (view): https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/blob/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml
- Template (raw download): https://raw.githubusercontent.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/main/infrastructure/aws-quick-admin-buddy-mcp/infrastructure/template.yaml

If the admin asks what gets created or which permissions the stack needs,
answer from the deployment guide's resource list or from the template, which is
the source of truth for every resource and policy.

## You guide; the admin runs

Follow Rule 11 in `SKILL.md`: the agent never runs a build or deploy command.
Deploying the backend creates billable AWS infrastructure in the admin's own
account under their own credentials, may need change-control approval, and the
agent's environment is not their AWS account. Quote each command from the
deployment guide, explain it, let the admin run it in their own terminal, and
wait for them to report the result (the image URI, `CREATE_COMPLETE`, the stack
Outputs) before continuing. The only backend calls in this phase are the
read-only probes from Steps 1 and 2.

Everywhere a command or URL needs a Region, use the Region of the admin's AWS
Quick account (`<quick-region>`); see <Definition - Backend> in `SKILL.md`. The
deployment guide's examples set `AWS_REGION` to a sample value: tell the admin
to replace it with their AWS Quick Region.

## What the backend is and why it is needed

Explain briefly, from <Definition - Backend> in `SKILL.md`, that the skill does
not configure AWS Quick directly: it calls the Quick Admin Buddy MCP server,
which calls the AWS Quick admin APIs. Without the deployed stack the connector
has no endpoint, so nothing can be configured for real, and Step 2 cannot finish.

## Prerequisites (confirm before deploying)

Confirm the items in the deployment guide's "Prerequisites" section one at a
time. In short:

1. **Docker** that can build a `linux/arm64` image (the AgentCore Runtime
   architecture). The admin clones the backend source
   (https://github.com/aws-samples/sample-amazon-quick-suite-knowledge-hub/tree/main/infrastructure/aws-quick-admin-buddy-mcp)
   and builds from that folder.
2. **AWS permissions** to create the stack's resources, as listed in the
   deployment guide.
3. **The container image pushed to Amazon ECR** in `<quick-region>`, following
   "Step 1: Build and push the container image" in the deployment guide. The
   resulting image URI is the stack's `ContainerImageUri` parameter.

## Deploy the stack

The template is larger than the CloudFormation inline template limit (51,200
bytes), so CloudFormation must read it from Amazon S3. The deployment guide's
CLI path stages it with `--s3-bucket`; both console paths below stage it in S3
too. Offer the admin two console ways to deploy and ask which they prefer:

```
<decision question="How would you like to deploy the backend CloudFormation stack?">
<option description="Download the template file and upload it in the CloudFormation console">Download the template and deploy in the console</option>
<option description="Put the template in your own S3 bucket and get a one-click quick-create link">Generate a one-click deploy link</option>
</decision>
```

If the admin prefers the CLI, point them to "Step 2: Deploy the stack" in the
deployment guide instead.

### Option A: Download the template and deploy in the console

1. Give the admin the template's raw download link (see [Sources](#sources)).
2. Have them open the CloudFormation console in `<quick-region>`, choose
   **Create stack**, **With new resources (standard)**, then **Upload a template
   file** and choose the downloaded file. The console stores the uploaded file
   in an S3 bucket in their account, which satisfies the size limit. Console
   reference:
   https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html
3. On the parameters page, fill the values from the deployment guide's "Stack
   parameters" table. Set `ActionConnectorName` to
   `Admin Onboarding Buddy Endpoint`, so the `ActionConnectorSuggestedName`
   output matches the fixed name this skill expects (the template's default is a
   different name).
4. Acknowledge **`CAPABILITY_NAMED_IAM`** (the template creates named IAM
   roles) and create the stack.

### Option B: One-click quick-create link

A CloudFormation quick-create link opens the console with the template and
parameters pre-filled. Its `templateURL` must be an Amazon S3 URL that the admin
opening the link can read; the object does not need to be public. Reference:
https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stacks-quick-create-links.html

1. Ask the admin to upload the downloaded template to an S3 bucket in their
   account in `<quick-region>`, and to give you the object's HTTPS URL (for
   example `https://<bucket>.s3.<quick-region>.amazonaws.com/template.yaml`).
2. Ask for a value for each parameter in the deployment guide's "Stack
   parameters" table that the admin wants to set, so the link opens ready to
   review.
3. Build the link in this shape and return it:

```
https://<quick-region>.console.aws.amazon.com/cloudformation/home?region=<quick-region>#/stacks/create/review?templateURL=<S3_HTTPS_URL>&stackName=quick-admin-buddy-mcp&param_ContainerImageUri=<IMAGE_URI>&param_CognitoDomainPrefix=<PREFIX>&param_OnboardingStateTableName=OnboardingState&param_TenantId=shared&param_ActionConnectorName=Admin+Onboarding+Buddy+Endpoint
```

- Replace `<quick-region>`, `<S3_HTTPS_URL>`, `<IMAGE_URI>`, and `<PREFIX>` with
  the admin's values. URL-encode the template URL and every parameter value
  (spaces as `+` or `%20`).
- Add `&param_<Name>=<value>` for any other parameter from the deployment
  guide's table the admin set, for example `QuickSetupBuddySharePrincipals`
  (URL-encode its ARNs and commas).
- Remind the admin that the quick-create page still requires them to
  acknowledge `CAPABILITY_NAMED_IAM` before creating the stack.

## After the deploy

- Wait for the admin to report `CREATE_COMPLETE`, then have them open the
  stack's **Outputs** tab. The outputs and their meaning are in the deployment
  guide's "Stack outputs" table; Step 2 says which ones the connector needs.
- If the stack fails, ask for the first failing resource event and troubleshoot
  from the deployment guide (for example its "Redeploying after a teardown"
  section when a retained table or log group already exists).
- For updates, the gateway and connector sync after a container update, and
  teardown, point to the matching sections of the deployment guide.

## Exit criteria

- Image built and pushed, stack deployed to `CREATE_COMPLETE`, and the Outputs
  tab is visible: **return to [Step 2](step-2-configure-connector.md)** to
  configure `Admin Onboarding Buddy Endpoint` using those outputs.
