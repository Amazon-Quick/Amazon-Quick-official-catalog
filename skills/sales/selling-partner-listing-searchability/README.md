---
description: "README for selling-partner-listing-searchability: overview, the required Amazon Selling Partner built-in connector prerequisite, and getting started."
last_updated: 2026-09-15
origin: original
---

# SP-API Listing Searchability Troubleshooter (`selling-partner-listing-searchability`)

Diagnoses why a Selling Partner API (SP-API) listing is not found in search and helps make it more discoverable, optimizing the searchable content with the seller's approval.

## Overview
Checks whether a listing is discoverable at all, then optimizes the content shoppers search on (title, description, bullet points, and generic keywords) with the seller's approval. Discoverability is treated as a spectrum: a listing can be indexed but rank poorly, or fail to index on a content gap. It is the searchability member of the SP-API listing troubleshooter family, alongside `selling-partner-listing-issues`, `selling-partner-listing-buyability`, and the `selling-partner-listing-troubleshooter` router.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the listings operations this skill uses (searching a seller's listing items, and patching a listing item). The connector authenticates as the seller.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot read listings or optimize searchable content.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

Establishing the active seller account and marketplace is handled by the session's account context (the connected Amazon Selling Partner connector); this skill reuses it.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
Ask why a product is not being found, for example "why isn't this showing up in search?" or "how do I improve visibility for SKU 12345?", and the skill will check discoverability and preview content improvements before anything changes.
