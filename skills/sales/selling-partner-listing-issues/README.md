---
description: "README for selling-partner-listing-issues: overview, the required Amazon Selling Partner built-in connector prerequisite, and getting started."
last_updated: 2026-09-15
origin: original
---

# SP-API Listing Issue Fixer (`selling-partner-listing-issues`)

Diagnoses and fixes Selling Partner API (SP-API) listing problems that surface as reported issues on a listing, with every change previewed and approved before it goes live.

## Overview
Reads a listing's reported issues (severity and enforcement), prioritizes them by impact, and fixes the blocking ones through previewed, approved attribute patches. Diagnosis is read-only; nothing changes without the seller's explicit approval. It is the issue-fixing member of the SP-API listing troubleshooter family, alongside `selling-partner-listing-buyability`, `selling-partner-listing-searchability`, and the `selling-partner-listing-troubleshooter` router.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the listings operations this skill uses (searching a seller's listing items, and patching a listing item). The connector authenticates as the seller.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot read or fix listings.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

Establishing the active seller account and marketplace is handled by the session's account context (the connected Amazon Selling Partner connector); this skill reuses it.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
Ask about a listing problem, for example "what's wrong with this listing?" or "fix the errors on SKU 12345", and the skill will scan, triage, and preview fixes before anything changes.
