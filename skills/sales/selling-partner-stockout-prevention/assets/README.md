---
description: "README for selling-partner-stockout-prevention: overview, the required Amazon Selling Partner built-in connector prerequisite, and getting started."
last_updated: 2026-09-15
origin: original
---

# SP-API Stockout Prevention (`selling-partner-stockout-prevention`)

Monitors Selling Partner API (SP-API) Fulfillment by Amazon (FBA) inventory health, finds stockout risk from sales velocity, and previews any price change before it goes live.

## Overview
Pulls current FBA inventory, derives sales velocity, computes days of cover per SKU, checks whether inbound shipments arrive in time, and proposes prevention actions. Diagnosis is read-only; the one write action, a temporary demand-slowing price change, is always previewed and approved before it goes live. It is the inventory-health member of the SP-API seller family, alongside `selling-partner-fba-inbound-management` for creating and placing inbound shipments.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the operations this skill uses (inventory summaries, order metrics, inbound plans, and patching a listing item for a price change). The connector authenticates as the seller and resolves the merchant account and marketplace(s) at the start of the session.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot read inventory or sales or draft a price change.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

## Installation
1. In Amazon Quick on desktop, go to Customize > Skills, choose Browse all, select the Official tab, and search for the skill by name. Choose Install. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. Connect and authenticate the Amazon Selling Partner connector. Under Customize > Connectors, find Amazon Selling Partner and choose Install.

## Getting started
Ask about inventory health, for example "am I going to run out of anything?" or "check days of cover for my FBA stock", and the skill will assess inventory, quantify stockout risk against the inbound pipeline, and preview any price change before anything goes live.
