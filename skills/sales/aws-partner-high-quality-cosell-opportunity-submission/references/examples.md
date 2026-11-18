---
description: "Anonymized high-scoring Customer Business Problem examples to use as patterns for structure and specificity."
last_updated: 2026-11-16
origin: original
---

# High-scoring Customer Business Problem examples

Each example is a Customer Business Problem that scores high. Names are removed and dollar amounts are shown as X. Use them as patterns for structure and specificity, not as text to copy.

## A migration from another cloud

> A regulated digital insurer runs back-office, data, and AI workloads on AWS across 16 accounts (USD X per month). Its front office still runs on another cloud provider at USD X per month, with database licensing alone at 31% of that bill. Why now: the CTO approved consolidating the front office onto AWS with an extended zero-downtime migration window starting now; identity federation is already in place. Incumbent: the other cloud provider. Evaluation criteria: 1/ zero-downtime migration in waves; 2/ disaster recovery in a second AWS Region; 3/ IOPS-guaranteed transactional SQL; 4/ reuse of Security Hub, GuardDuty, and Security Lake already in operation. Contracting: our Professional Services for the migration, with run absorbed into the existing Managed Services contract. Budget authority: the CTO.

## An AI build on an existing AWS estate

> An agroindustrial cooperative (USD X per month on AWS, 7 accounts) manages fleet maintenance across three plants through manual ERP queries and spreadsheets. Why now: during harvest season, unplanned downtime costs X per day, and the CEO has mandated an AI operations platform by Q3 to cut unplanned stops by 30%. Competition: the customer evaluated a competing cloud AI service under an existing enterprise agreement but chose AWS because its data lake is already on S3 and Glue and Amazon Bedrock AgentCore integrates natively. Evaluation criteria: 1/ sub-3-second natural-language queries; 2/ ERP REST API integration; 3/ multi-agent orchestration across scheduling, maintenance, and parts; 4/ data residency in sa-east-1. Contracting: POC credit approved; production through our Managed Services subscription.

## A security product evaluated against a written baseline

> A large energy company protects an API estate of roughly 5 billion requests per month on EKS, Amazon API Gateway, and EC2. AWS WAF covers the web perimeter, but the customer cannot inventory exposed APIs or detect authorization-logic abuse. Why now: suspected API probing triggered a chartered program to add API-layer detection, and an audit commitment requires per-API violation reporting mapped to NIST CSF 2.0 and the OWASP API Top 10. Evaluation criteria: a written vendor baseline covering OWASP API Top 10 coverage, continuous API discovery, a quotable false-positive rate, RBAC per application, and SIEM integration. Hard constraint: the data plane must run inside the customer's own AWS VPC and Region.

## A regulated SaaS replacing in-house tooling

> A UK fintech under FCA supervision runs anti-money-laundering monitoring in-house with SQL rules, a homegrown risk model, and a ticketing board, plus a third-party screening service that has produced false matches. Why now: the COO's monthly operating review shows the financial crime function red every month, the ten-person operations team is outside SLA, and the only alternative on the table is doubling headcount. The MLRO has open audit findings to close. Requirements: AWS London hosting for UK data residency; monitoring at 9M transactions per year ramping to 12M across 500,000 customers; no-code rule authoring; AI governance controls for our first-line alert review agent, validated on the same 1,000-customer sample as the incumbent.

## A services engagement delivered directly

> The customer is exiting two data centers and migrating roughly 400 workloads to AWS over 18 months, and we are the delivery partner for the migration and the managed-services run. A data-center lease expiration sets a hard deadline, and the VP of Infrastructure is the sponsor. Success is measured on migration pace and post-migration run cost. Our landing-zone and migration-factory practice is scoped to the first wave.
