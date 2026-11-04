# Canonical pipeline-review 2b request

This is a mechanically checked construction copy of the inline 2b call in `../SKILL.md`.
The inline call remains authoritative. This file authorizes no additional Salesforce call, field,
endpoint, retry, or fallback.

## Exact call

```text
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, first: 40, orderBy: { Amount: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } NextStep { value } LastActivityDate { value } Type { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Id } } } } } } } aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```
